import json
import logging
import re
import time
import unicodedata
from typing import Any

import sqlalchemy as sa
from groq import Groq, RateLimitError
from langchain_community.agent_toolkits import SQLDatabaseToolkit, create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq

from core.config import settings
from database.db import engine
from database.models import Business
from database.schemas import BusinessOut, SmartChatResponse
from services.groq_service import safe_groq_chat_completion


logger = logging.getLogger(__name__)

INTENT_PROMPT = """
Bạn là AI Data Router cho kho dữ liệu doanh nghiệp.
Đọc câu hỏi user và trả về DUY NHẤT 1 object JSON, không markdown.

Schema:
{
  "type": "list_data" hoặc "count_or_analyze",
  "keyword": "loại hình/tên quán/ngành, ví dụ cà phê, phở, nhà hàng; rỗng nếu không có",
  "location": "khu vực, ví dụ Gò Vấp, TPHCM, Hà Nội; rỗng nếu không có",
  "min_rating": số float, mặc định 0.0,
  "limit": số nguyên user muốn, mặc định 100 nếu user không nói số
}

Phân loại:
- list_data: user muốn tìm/liệt kê/lấy danh sách để xem bảng, biểu đồ. Ví dụ: "Tìm cho tôi 20 quán cà phê trên 4.5 sao ở Gò Vấp".
- count_or_analyze: user hỏi đếm, trung bình, so sánh, phân tích, cao nhất/thấp nhất. Ví dụ: "Có bao nhiêu quán cà phê ở Gò Vấp?".

Quy tắc bắt buộc:
- Nếu câu có "trên 4.5 sao", ">= 4 sao", "từ 4 sao" thì min_rating phải là số tương ứng.
- Nếu câu có số lượng như "20 quán", limit phải là 20.
- TPHCM/HCM/Sài Gòn là location.
""".strip()

PREFIX = """Bạn là một chuyên gia phân tích dữ liệu AI.
LƯU Ý QUAN TRỌNG KHI VIẾT SQL:
1. Các trường địa chỉ (address), tên (name) là tiếng Việt. Hãy luôn dùng toán tử `ILIKE` thay vì `LIKE` hoặc `=`.
2. Nếu tìm không ra kết quả tiếng Việt có dấu (ví dụ: 'Gò Vấp'), hãy thử truy vấn bằng tiếng Việt không dấu (ví dụ: 'Go Vap').
3. Nếu kết quả là 0, hãy chấp nhận đó là câu trả lời cuối cùng, KHÔNG thử lại nhiều lần."""

LOCATION_ALIASES = {
    "tphcm": "ho chi minh",
    "tp hcm": "ho chi minh",
    "tp.hcm": "ho chi minh",
    "hcm": "ho chi minh",
    "sai gon": "ho chi minh",
    "sài gòn": "ho chi minh",
    "sg": "ho chi minh",
    "hn": "ha noi",
    "hà nội": "ha noi",
}

DISPLAY_LOCATION_ALIASES = {
    "ho chi minh": "Hồ Chí Minh",
    "ha noi": "Hà Nội",
}


def _get_groq_client() -> Groq:
    return Groq(api_key=settings.GROQ_API_KEY)


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?|```", "", raw_text or "", flags=re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(match.group(0))


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D")


def _normalize_text(value: str) -> str:
    value = _strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9\s.]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _normalize_location_for_match(location: str) -> str:
    normalized = _normalize_text(location)
    for alias, canonical in LOCATION_ALIASES.items():
        normalized_alias = _normalize_text(alias)
        normalized = re.sub(rf"\b{re.escape(normalized_alias)}\b", canonical, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _display_location(location: str) -> str:
    normalized = _normalize_location_for_match(location)
    if normalized in DISPLAY_LOCATION_ALIASES:
        return DISPLAY_LOCATION_ALIASES[normalized]
    return (location or "").strip()


def _safe_int(value: Any, default: int = 100) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, 1), 100)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, 0.0), 5.0)


def _fallback_keyword(question: str) -> str:
    normalized_question = _normalize_text(question)
    keyword_aliases = {
        "cà phê": ("ca phe", "cafe", "coffee"),
        "phở": ("pho",),
        "nhà hàng": ("nha hang", "restaurant"),
        "quán ăn": ("quan an",),
        "trà sữa": ("tra sua", "milk tea"),
        "đồng hồ": ("dong ho", "watch", "watches"),
        "vàng": ("vang", "gold", "jewelry", "jewellery"),
    }
    for keyword, aliases in keyword_aliases.items():
        if any(alias in normalized_question for alias in aliases):
            return keyword
    return ""


def _keyword_match_terms(keyword: str) -> list[str]:
    normalized_keyword = _normalize_text(keyword)
    alias_map = {
        "ca phe": ["ca phe", "cafe", "coffee"],
        "quan ca phe": ["ca phe", "cafe", "coffee"],
        "tiem ca phe": ["ca phe", "cafe", "coffee"],
        "pho": ["pho"],
        "nha hang": ["nha hang", "restaurant"],
        "quan an": ["quan an"],
        "tra sua": ["tra sua", "milk tea", "milktea"],
        "dong ho": ["dong ho", "watch", "watches"],
        "tiem dong ho": ["dong ho", "watch", "watches"],
        "cua hang dong ho": ["dong ho", "watch", "watches"],
        "vang": ["vang", "gold", "jewelry", "jewellery"],
        "tiem vang": ["vang", "gold", "jewelry", "jewellery"],
        "cua hang vang": ["vang", "gold", "jewelry", "jewellery"],
    }
    return alias_map.get(normalized_keyword, [normalized_keyword])


def _fallback_location(question: str) -> str:
    normalized_question = _normalize_location_for_match(question)
    known_locations = {
        "quan 1": "Quận 1",
        "quan 2": "Quận 2",
        "quan 3": "Quận 3",
        "quan 4": "Quận 4",
        "quan 5": "Quận 5",
        "quan 6": "Quận 6",
        "quan 7": "Quận 7",
        "quan 8": "Quận 8",
        "quan 9": "Quận 9",
        "quan 10": "Quận 10",
        "quan 11": "Quận 11",
        "quan 12": "Quận 12",
        "binh tan": "Bình Tân",
        "binh thanh": "Bình Thạnh",
        "go vap": "Gò Vấp",
        "phu nhuan": "Phú Nhuận",
        "tan binh": "Tân Bình",
        "tan phu": "Tân Phú",
        "thu duc": "Thủ Đức",
        "binh chanh": "Bình Chánh",
        "can gio": "Cần Giờ",
        "cu chi": "Củ Chi",
        "hoc mon": "Hóc Môn",
        "nha be": "Nhà Bè",
        "ho chi minh": "Hồ Chí Minh",
        "ha noi": "Hà Nội",
    }
    for normalized_location, display_location in known_locations.items():
        if normalized_location in normalized_question:
            return display_location
    return ""


def _requested_limit_from_question(question: str) -> int | None:
    normalized_question = _normalize_text(question)
    limit_patterns = (
        r"\b(\d{1,3})\s*(?:quan|tiem|cua hang|shop|store|ket qua|dia diem|dia chi|doanh nghiep|lead)\b",
        r"\b(?:top|lay|tim|liet ke|hien thi|can)\s+(\d{1,3})\b",
    )
    for pattern in limit_patterns:
        match = re.search(pattern, normalized_question)
        if match:
            return _safe_int(match.group(1), default=100)
    return None


def _fallback_limit(question: str) -> int:
    requested_limit = _requested_limit_from_question(question)
    if requested_limit is not None:
        return requested_limit
    return 100


def _fallback_min_rating(question: str) -> float:
    normalized_question = _normalize_text(question).replace(",", ".")
    rating_patterns = (
        r"(?:tren|tu|>=|hon)\s*(\d(?:\.\d)?)\s*(?:sao|star|rating)?",
        r"(\d(?:\.\d)?)\s*(?:sao|star)\s*(?:tro len|up|plus)?",
    )
    for pattern in rating_patterns:
        match = re.search(pattern, normalized_question)
        if match:
            return _safe_float(match.group(1))
    return 0.0


def _fallback_intent(question: str) -> dict[str, Any]:
    normalized_question = _normalize_text(question)
    count_patterns = (
        "bao nhieu",
        "dem",
        "trung binh",
        "phan tich",
        "cao nhat",
        "thap nhat",
        "tot nhat",
        "kem nhat",
    )
    intent_type = "count_or_analyze" if any(pattern in normalized_question for pattern in count_patterns) else "list_data"
    return {
        "type": intent_type,
        "keyword": _fallback_keyword(question),
        "location": _fallback_location(question),
        "min_rating": _fallback_min_rating(question),
        "limit": _fallback_limit(question),
    }


def _is_followup_question(question: str) -> bool:
    normalized_question = _normalize_text(question)
    followup_patterns = (
        "do",
        "do ra",
        "cac quan do",
        "nhung quan do",
        "danh sach do",
        "liet ke ra",
        "liet ke",
        "hien thi",
        "hien thi ra",
        "hien ra",
        "xem nao",
        "cho xem",
        "cho toi xem",
        "xem di",
        "ra di",
        "o tren",
        "vua roi",
        "luc nay",
        "ket qua tren",
        "danh sach tren",
        "danh sach",
        "show",
        "list",
    )
    return any(pattern in normalized_question for pattern in followup_patterns)


def _is_term_in_question(term: str, question: str) -> bool:
    if not term:
        return False
    norm_term = _normalize_text(term)
    norm_question = _normalize_text(question)
    if not norm_term or not norm_question:
        return False
    
    # 1. Direct substring check
    if norm_term in norm_question:
        return True
        
    # 2. Location aliases check
    norm_loc_term = _normalize_location_for_match(term)
    norm_loc_question = _normalize_location_for_match(question)
    if norm_loc_term in norm_loc_question:
        return True
        
    # 3. Keyword matching terms check
    for matching_term in _keyword_match_terms(term):
        if _normalize_text(matching_term) in norm_question:
            return True
            
    return False


def _context_search_params(context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(context, dict):
        return {}
    search_payload = context.get("search_payload")
    if isinstance(search_payload, dict):
        return {**context, **search_payload}
    return context


def _merge_followup_context(intent: dict[str, Any], question: str, context: dict[str, Any] | None) -> dict[str, Any]:
    if not _is_followup_question(question):
        return intent

    context_params = _context_search_params(context)
    if not context_params:
        return intent

    merged = {**intent}

    # Clean hallucinated keywords or locations that are not actually in the user's follow-up question
    for key in ("keyword", "location"):
        val = merged.get(key)
        if val and not _is_term_in_question(val, question):
            merged[key] = ""

    for key in ("keyword", "location"):
        if not merged.get(key) and context_params.get(key):
            merged[key] = context_params[key]

    if _safe_float(merged.get("min_rating")) == 0 and context_params.get("min_rating") is not None:
        merged["min_rating"] = _safe_float(context_params.get("min_rating"))

    requested_limit = _requested_limit_from_question(question)
    if requested_limit is not None:
        merged["limit"] = requested_limit
    elif merged.get("type") == "list_data":
        context_total = context_params.get("total_found")
        if context_total is not None:
            merged["limit"] = _safe_int(context_total, default=_safe_int(context_params.get("limit"), default=100))
        elif context_params.get("limit") is not None:
            merged["limit"] = _safe_int(context_params.get("limit"), default=100)

    merged["followup_from_context"] = True
    return merged


def _classify_intent(question: str) -> dict[str, Any]:
    fallback = _fallback_intent(question)
    try:
        completion = safe_groq_chat_completion(
            client=_get_groq_client(),
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": f"{INTENT_PROMPT}\n\nCâu hỏi: {question}"}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        intent = _extract_json_object(completion.choices[0].message.content or "{}")
    except Exception:
        logger.exception("Smart chat intent classification failed")
        intent = fallback

    intent_type = intent.get("type")
    if intent_type not in {"count_or_analyze", "list_data"}:
        intent_type = fallback["type"]

    keyword = str(intent.get("keyword") or "").strip() or fallback["keyword"]
    location = str(intent.get("location") or "").strip() or fallback["location"]
    min_rating = _safe_float(intent.get("min_rating"), default=fallback["min_rating"])
    if min_rating == 0 and fallback["min_rating"] > 0:
        min_rating = fallback["min_rating"]

    if intent_type == "list_data":
        # Use deterministic parsing for requested list size. LLMs often mistake
        # district numbers like "Quận 1" for "limit = 1".
        limit = fallback["limit"]
    else:
        limit = 100

    return {
        "type": intent_type,
        "keyword": keyword,
        "location": _display_location(location) if location else "",
        "min_rating": min_rating,
        "limit": limit,
    }


def _build_sql_agent_answer(question: str) -> str:
    db = SQLDatabase(engine)
    primary_llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.GROQ_API_KEY,
        disable_streaming=True,
    )
    fallback_llm_1 = ChatGroq(
        model_name="llama-3.1-8b-instant",
        temperature=0,
        api_key=settings.GROQ_API_KEY,
        disable_streaming=True,
    )
    llm = primary_llm.with_fallbacks([fallback_llm_1])
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent_executor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent_type="tool-calling",
        prefix=PREFIX,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=10,
        top_k=10,
    )

    analyst_question = f"""
Trả lời bằng tiếng Việt ngắn gọn, tập trung vào số liệu.
Alias địa chỉ: TPHCM/HCM/Sài Gòn/SG = Hồ Chí Minh; HN = Hà Nội.
Câu hỏi user: {question}
""".strip()

    last_error = None
    for attempt in range(2):
        try:
            response = agent_executor.invoke({"input": analyst_question})
            output = str(response.get("output", "")).strip()
            if "Agent stopped due to max iterations" in output:
                raise RuntimeError(output)
            return output
        except RateLimitError as exc:
            last_error = exc
            logger.warning("Groq rate limit in SQL agent, retrying", exc_info=True)
            time.sleep(2 + attempt)

    raise last_error if last_error else RuntimeError("SQL agent failed")


def _rough_sqlalchemy_candidates(db_session, keyword: str, location: str) -> list[Business]:
    query = db_session.query(Business)
    conditions = []

    if keyword:
        conditions.append(Business.name.ilike(f"%{keyword}%"))
        for term in _keyword_match_terms(keyword):
            conditions.append(Business.name.ilike(f"%{term}%"))
        if hasattr(Business, "tags"):
            conditions.append(Business.tags.ilike(f"%{keyword}%"))
            for term in _keyword_match_terms(keyword):
                conditions.append(Business.tags.ilike(f"%{term}%"))

    if location:
        normalized_location = _normalize_location_for_match(location)
        location_variants = {
            location,
            _display_location(location),
            normalized_location,
            "Hồ Chí Minh" if normalized_location == "ho chi minh" else "",
            "Hà Nội" if normalized_location == "ha noi" else "",
        }
        for variant in {item for item in location_variants if item}:
            conditions.append(Business.address.ilike(f"%{variant}%"))

    if conditions:
        rough_matches = query.filter(sa.or_(*conditions)).all()
        if rough_matches:
            return rough_matches

    return query.all()


def _business_matches_query(business: Business, keyword: str, location: str, min_rating: float) -> bool:
    if min_rating and (business.rating is None or business.rating < min_rating):
        return False

    if keyword:
        keyword_terms = _keyword_match_terms(keyword)
        searchable_name = _normalize_text(business.name or "")
        searchable_tags = _normalize_text(getattr(business, "tags", "") or "")
        if not any(term in searchable_name or term in searchable_tags for term in keyword_terms):
            return False

    if location:
        normalized_location = _normalize_location_for_match(location)
        searchable_address = _normalize_location_for_match(business.address or "")
        location_terms = [term for term in normalized_location.split(" ") if term]
        if location_terms and not all(term in searchable_address for term in location_terms):
            return False

    return True


def _matching_businesses(intent: dict[str, Any], question: str, db_session) -> list[Business]:
    keyword = intent.get("keyword") or _fallback_keyword(question)
    location = intent.get("location") or _fallback_location(question)
    min_rating = _safe_float(intent.get("min_rating"))
    candidates = _rough_sqlalchemy_candidates(db_session, keyword, location)
    return [
        business
        for business in candidates
        if _business_matches_query(business, keyword, location, min_rating)
    ]


def _search_payload(intent: dict[str, Any], question: str, total_found: int) -> dict[str, Any]:
    keyword = intent.get("keyword") or _fallback_keyword(question)
    location = intent.get("location") or _fallback_location(question)
    min_rating = _safe_float(intent.get("min_rating"))
    limit = _safe_int(intent.get("limit"), default=100)
    return {
        "type": "list_data",
        "keyword": keyword,
        "location": _display_location(location) if location else "",
        "min_rating": min_rating,
        "limit": limit,
        "result_limit": limit,
        "total_found": total_found,
        "search_payload": {
            "keyword": keyword,
            "location": _display_location(location) if location else "",
            "min_rating": min_rating,
            "result_limit": limit,
        },
    }


def _local_analysis_answer(question: str, intent: dict[str, Any], db_session) -> str:
    businesses = _matching_businesses(intent, question, db_session)
    normalized_question = _normalize_text(question)
    total = len(businesses)

    keyword = intent.get("keyword") or _fallback_keyword(question)
    location = intent.get("location") or _fallback_location(question)
    scope = " ".join(part for part in [keyword, _display_location(location) if location else ""] if part) or "doanh nghiệp"

    if total == 0:
        return f"Dạ trong kho hiện chưa có dữ liệu phù hợp cho {scope}."

    if "trung binh" in normalized_question or "average" in normalized_question:
        ratings = [business.rating for business in businesses if business.rating is not None]
        if not ratings:
            return f"Dạ tôi tìm thấy {total} kết quả cho {scope}, nhưng chưa có dữ liệu rating để tính trung bình."
        avg_rating = sum(ratings) / len(ratings)
        return f"Dạ có {total} kết quả phù hợp. Rating trung bình hiện là {avg_rating:.2f}/5."

    top_score_patterns = ("cao diem", "diem cao", "ai score", "score cao", "tot nhat")
    if any(pattern in normalized_question for pattern in top_score_patterns):
        scored = [business for business in businesses if business.ai_score is not None]
        if scored:
            best = max(scored, key=lambda business: business.ai_score or 0)
            return f"Dạ quán có AI score cao nhất là {best.name} với {best.ai_score} điểm."

    top_rating_patterns = ("rating cao", "danh gia cao", "sao cao", "cao nhat")
    if any(pattern in normalized_question for pattern in top_rating_patterns):
        rated = [business for business in businesses if business.rating is not None]
        if rated:
            best = max(rated, key=lambda business: (business.rating or 0, business.review_count or 0))
            return f"Dạ quán có rating cao nhất là {best.name} với {best.rating}/5 sao."

    return f"Dạ trong kho dữ liệu hiện có {total} kết quả phù hợp cho {scope}."


def _should_answer_locally(question: str) -> bool:
    normalized_question = _normalize_text(question)
    local_patterns = (
        "bao nhieu",
        "dem",
        "co may",
        "trung binh",
        "average",
        "cao nhat",
        "thap nhat",
        "tot nhat",
        "kem nhat",
        "rating cao",
        "danh gia cao",
        "sao cao",
        "ai score",
    )
    return any(pattern in normalized_question for pattern in local_patterns)


def _answer_count_or_analyze(question: str, intent: dict[str, Any], db_session) -> str:
    if _should_answer_locally(question):
        return _local_analysis_answer(question, intent, db_session)

    try:
        return _build_sql_agent_answer(question)
    except RateLimitError:
        logger.warning("Groq rate limit persisted; using local SQLAlchemy analysis fallback", exc_info=True)
        return _local_analysis_answer(question, intent, db_session)
    except Exception:
        logger.exception("SQL agent failed; using local SQLAlchemy analysis fallback")
        return _local_analysis_answer(question, intent, db_session)


def _process_list_data(intent: dict[str, Any], question: str, db_session) -> dict:
    limit = _safe_int(intent.get("limit"), default=100)
    requested_limit = _requested_limit_from_question(question)
    matching_businesses = _matching_businesses(intent, question, db_session)
    total_found = len(matching_businesses)
    extracted_params = _search_payload(intent, question, total_found)
    extracted_params["requested_limit_explicit"] = requested_limit is not None

    if requested_limit is None or total_found >= limit:
        selected_businesses = matching_businesses[:limit]
        if requested_limit is None:
            ai_message = f"Dạ trong kho hiện có {total_found} kết quả phù hợp. Tôi hiển thị toàn bộ dữ liệu đang có:"
        else:
            ai_message = (
                f"Dạ trong kho hiện có {total_found} kết quả phù hợp. "
                f"Đủ yêu cầu {limit} kết quả của bạn, tôi hiển thị dashboard ngay:"
            )
        response = SmartChatResponse(
            ai_message=ai_message,
            status="success_enough_data",
            data=[BusinessOut.model_validate(business) for business in selected_businesses],
            extracted_params=extracted_params,
        )
        return response.model_dump()

    response = SmartChatResponse(
        ai_message=(
            f"Dạ trong kho hiện chỉ có {total_found} kết quả phù hợp, "
            f"chưa đủ {limit} kết quả bạn yêu cầu. Tôi đã điền sẵn form bên dưới, "
            "bạn bấm tìm kiếm để cào thêm từ Google Maps nhé!"
        ),
        status="need_more_data",
        data=[],
        extracted_params=extracted_params,
    )
    return response.model_dump()

    if requested_limit is None or total_found >= limit:
        selected_businesses = matching_businesses[:limit]
        response = SmartChatResponse(
            ai_message=(
                f"Dạ trong kho hiện có {total_found} kết quả phù hợp. "
                f"Đủ yêu cầu {limit} kết quả của bạn, tôi hiển thị dashboard ngay:"
            ),
            status="success_enough_data",
            data=[BusinessOut.model_validate(business) for business in selected_businesses],
            extracted_params=extracted_params,
        )
    else:
        response = SmartChatResponse(
            ai_message=(
                f"Dạ trong kho hiện chỉ có {total_found} kết quả phù hợp, "
                f"chưa đủ {limit} kết quả bạn yêu cầu. Tôi đã điền sẵn form bên dưới, "
                "bạn bấm tìm kiếm để cào thêm từ Google Maps nhé!"
            ),
            status="need_more_data",
            data=[],
            extracted_params=extracted_params,
        )

    return response.model_dump()


def _is_request_to_open_search(question: str) -> bool:
    normalized_question = _normalize_text(question)
    open_patterns = (
        "mo giao dien",
        "mo form",
        "mo tim kiem",
        "tim kiem qua google map",
        "tim kiem qua gg map",
        "tim kiem google map",
        "tim kiem gg map",
        "mo trang tim",
        "cao them",
        "cao du lieu",
        "cao data",
        "mo giao dien cao",
        "hien thi form",
        "hien thi giao dien",
        "mo google map",
        "mo gg map",
        "mo cong cu",
        "crawl",
        "scrape",
        "lay them",
        "nap them",
        "bo sung du lieu",
        "bo sung lead",
        "bo sung o"
    )
    return any(pattern in normalized_question for pattern in open_patterns)


def process_smart_chat(question: str, db_session, context: dict[str, Any] | None = None) -> dict:
    try:
        intent = _classify_intent(question)
        intent = _merge_followup_context(intent, question, context)

        if _is_request_to_open_search(question):
            keyword = intent.get("keyword") or ""
            location = intent.get("location") or ""
            
            context_params = _context_search_params(context)
            if not keyword and context_params.get("keyword"):
                keyword = context_params["keyword"]
            if not location and context_params.get("location"):
                location = context_params["location"]

            extracted_params = {
                "type": "list_data",
                "keyword": keyword,
                "location": location,
                "min_rating": _safe_float(intent.get("min_rating"), default=0.0),
                "limit": _safe_int(intent.get("limit"), default=100),
                "search_payload": {
                    "keyword": keyword,
                    "location": location,
                    "min_rating": _safe_float(intent.get("min_rating"), default=0.0),
                    "result_limit": _safe_int(intent.get("limit"), default=100),
                }
            }
            response = SmartChatResponse(
                ai_message="Dạ bạn, tôi mở giao diện tìm kiếm và cào thêm dữ liệu từ Google Maps ngay bên dưới nhé!",
                status="need_more_data",
                data=[],
                extracted_params=extracted_params
            )
            return response.model_dump()

        if intent["type"] == "count_or_analyze":
            answer = _answer_count_or_analyze(question, intent, db_session)
            response = SmartChatResponse(
                ai_message=answer,
                status="success_enough_data",
                data=[],
                extracted_params=intent,
            )
            return response.model_dump()

        return _process_list_data(intent, question, db_session)

    except Exception as exc:
        logger.exception("Smart chat processing failed")
        response = SmartChatResponse(
            ai_message="Xin lỗi bạn, tôi gặp sự cố khi xử lý Smart Chat. Vui lòng thử lại sau.",
            status="need_more_data",
            data=[],
            extracted_params={"error": str(exc)},
        )
        return response.model_dump()
