import json
import logging
import re
from typing import Any

import sqlalchemy as sa
from groq import Groq

from core.config import settings
from database.models import Business
from database.schemas import BusinessOut, SmartChatResponse


logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = (
    "Trích xuất thông tin tìm kiếm từ câu hỏi. Trả về DUY NHẤT 1 object JSON "
    "với các key: 'keyword' (loại hình/tên quán, vd: 'cà phê', 'phở', 'nhà hàng'. "
    "BẮT BUỘC lấy nếu có, không được để rỗng), 'location' (khu vực, mặc định ''), "
    "'min_rating' (số float, mặc định 0.0), 'limit' (số nguyên, mặc định 10). "
    "KHÔNG markdown."
)


def _get_groq_client() -> Groq:
    return Groq(api_key=settings.GROQ_API_KEY)


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    """Extract the first JSON object from an LLM response."""
    cleaned = re.sub(r"```(?:json)?|```", "", raw_text or "", flags=re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(match.group(0))


def _normalize_params(params: dict[str, Any]) -> dict[str, Any]:
    keyword = str(params.get("keyword") or "").strip()
    location = str(params.get("location") or "").strip()

    try:
        min_rating = float(params.get("min_rating") or 0.0)
    except (TypeError, ValueError):
        min_rating = 0.0

    try:
        limit = int(params.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10

    return {
        "keyword": keyword,
        "location": location,
        "min_rating": max(min_rating, 0.0),
        "limit": max(limit, 1),
    }


def _question_has_explicit_limit(question: str) -> bool:
    return bool(re.search(r"\d+", question or ""))


def _fallback_keyword_from_question(question: str) -> str:
    normalized_question = (question or "").lower()
    keyword_aliases = {
        "cà phê": ["cà phê", "cafe", "coffee"],
        "phở": ["phở", "pho"],
        "nhà hàng": ["nhà hàng", "restaurant"],
        "quán ăn": ["quán ăn", "quan an"],
        "trà sữa": ["trà sữa", "tra sua", "milk tea"],
    }

    for keyword, aliases in keyword_aliases.items():
        if any(alias in normalized_question for alias in aliases):
            return keyword
    return ""


def _normalize_location_for_query(location: str) -> str:
    normalized_location = (location or "").strip()
    lowered_location = normalized_location.lower()

    if any(alias in lowered_location for alias in ("tphcm", "hcm", "sài gòn", "sai gon")):
        return "Hồ Chí Minh"

    if re.search(r"\bhn\b", lowered_location) or "hà nội" in lowered_location or "ha noi" in lowered_location:
        return "Hà Nội"

    return normalized_location


def _fallback_location_from_question(question: str) -> str:
    return _normalize_location_for_query(question)


def process_smart_chat(question: str, db_session) -> dict:
    extracted_params: dict[str, Any] = {
        "keyword": "",
        "location": "",
        "min_rating": 0.0,
        "limit": 10,
    }

    try:
        client = _get_groq_client()
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": f"{EXTRACTION_PROMPT}\n\nCâu hỏi: {question}",
                }
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        raw_content = completion.choices[0].message.content or "{}"
        extracted_params = _normalize_params(_extract_json_object(raw_content))

        keyword = extracted_params["keyword"]
        location = extracted_params["location"]
        min_rating = extracted_params["min_rating"]
        limit = extracted_params["limit"]

        if keyword == "":
            keyword = _fallback_keyword_from_question(question)

        if location == "":
            location = _fallback_location_from_question(question)

        location = _normalize_location_for_query(location)
        extracted_params["keyword"] = keyword
        extracted_params["location"] = location

        query = db_session.query(Business)

        if keyword != "":
            keyword_filter = Business.name.ilike(f"%{keyword}%")
            if hasattr(Business, "tags"):
                keyword_filter = sa.or_(keyword_filter, Business.tags.ilike(f"%{keyword}%"))
            query = query.filter(keyword_filter)

        if location != "":
            query = query.filter(Business.address.ilike(f"%{location}%"))

        query = query.filter(Business.rating >= min_rating)

        total_found = query.count()
        businesses = query.limit(limit).all()
        limit_is_clear = _question_has_explicit_limit(question)

        if total_found >= limit or (not limit_is_clear and total_found > 0):
            response = SmartChatResponse(
                ai_message=(
                    f"Tuyệt vời! Trong kho dữ liệu đang có {total_found} kết quả "
                    "phù hợp với yêu cầu của sếp. Đây là danh sách chi tiết:"
                ),
                status="success_enough_data",
                data=[BusinessOut.model_validate(business) for business in businesses],
                extracted_params=extracted_params,
            )
        else:
            response = SmartChatResponse(
                ai_message=(
                    f"Sếp ơi, trong kho hiện tại chỉ có {total_found} kết quả, "
                    f"không đủ yêu cầu '{limit}' của sếp. Sếp vui lòng dùng công cụ "
                    "bên dưới để tôi ra ngoài Internet thu thập thêm data mới nhé!"
                ),
                status="need_more_data",
                data=[],
                extracted_params=extracted_params,
            )

        return response.model_dump()

    except Exception as exc:
        logger.exception("Smart chat processing failed")
        response = SmartChatResponse(
            ai_message=(
                "Xin lỗi sếp, tôi gặp sự cố khi xử lý Smart Chat. "
                "Vui lòng thử lại sau."
            ),
            status="need_more_data",
            data=[],
            extracted_params={
                **extracted_params,
                "error": str(exc),
            },
        )
        return response.model_dump()
