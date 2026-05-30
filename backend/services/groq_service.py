import json
from typing import Any
from groq import Groq
from core.config import settings

AI_DISABLED_REASON = ""


def get_all_api_keys() -> list[str]:
    keys = []
    # 1. Thử lấy danh sách API keys từ settings.GROQ_API_KEYS (ngăn cách bằng dấu phẩy)
    if hasattr(settings, "GROQ_API_KEYS") and settings.GROQ_API_KEYS:
        for k in settings.GROQ_API_KEYS.split(","):
            val = k.strip()
            if val and val not in keys:
                keys.append(val)
                
    # 2. Thử lấy từ settings.GROQ_API_KEY
    if settings.GROQ_API_KEY:
        for k in settings.GROQ_API_KEY.split(","):
            val = k.strip()
            if val and val not in keys:
                keys.append(val)
        
    return keys


def _build_clients() -> list[Groq]:
    global AI_DISABLED_REASON
    keys = get_all_api_keys()
    clients_list = []
    for k in keys:
        try:
            clients_list.append(Groq(api_key=k))
        except Exception as e:
            print(f"Failed to initialize Groq client for key: {k[:15]}... Error: {e}")
            
    if not clients_list:
        AI_DISABLED_REASON = "Missing GROQ_API_KEY or GROQ_API_KEYS in backend/.env"
        
    return clients_list


clients = _build_clients()
client = clients[0] if clients else None


def safe_groq_chat_completion(client_param: Groq = None, **kwargs) -> Any:
    """
    Thực hiện gọi API chat completion của Groq với cơ chế tự động quay vòng API keys và hạ cấp mô hình dự phòng.
    """
    client_param = client_param or kwargs.pop("client", None)
    import logging
    logger = logging.getLogger(__name__)
    
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    requested_model = kwargs.pop("model", "llama-3.3-70b-versatile")
    if requested_model in models:
        models.remove(requested_model)
    models.insert(0, requested_model)
    
    # Danh sách client để thử: bắt đầu bằng client được truyền vào nếu hợp lệ,
    # sau đó chuyển sang các client khác trong danh sách đã cấu hình của chúng ta
    clients_to_try = []
    if client_param:
        clients_to_try.append(client_param)
        
    for c in clients:
        if c not in clients_to_try:
            clients_to_try.append(c)
            
    if not clients_to_try:
        raise RuntimeError("No Groq clients available. Please configure GROQ_API_KEY or GROQ_API_KEYS.")
        
    last_exc = None
    for model in models:
        for active_client in clients_to_try:
            try:
                # Ẩn bớt ký tự API key để đảm bảo bảo mật khi ghi log
                masked_key = active_client.api_key[:10] + "..." if active_client.api_key else "None"
                logger.info(f"Attempting Groq completion with model: {model} using key: {masked_key}")
                kwargs["model"] = model
                return active_client.chat.completions.create(**kwargs)
            except Exception as exc:
                masked_key = active_client.api_key[:10] + "..." if active_client.api_key else "None"
                logger.warning(f"Groq API call failed with model {model} using key {masked_key}: {exc}")
                last_exc = exc
                continue
            
    if last_exc:
        raise last_exc
    raise RuntimeError("All Groq models failed to execute completion.")

def score_lead(business: dict) -> dict:
    """
    Chấm điểm doanh nghiệp (từ 0 đến 100) dựa trên các tiêu chí: điểm đánh giá (rating),
    số lượng đánh giá (review count) và sự hiện diện của website.
    """
    if not client:
        # Trả về kết quả mặc định giả lập nếu tính năng chấm điểm AI bị tắt
        return {"score": 0, "reason": f"Chấm điểm AI đã tắt ({AI_DISABLED_REASON})."}
        
    prompt = f"""
    Bạn là chuyên gia phân tích doanh nghiệp.
    Hãy chấm điểm doanh nghiệp này trong khoảng 0-100 dựa trên:
    - rating
    - review_count
    - có/không có website
    
    Viết lý do ngắn gọn bằng tiếng Việt.

    Dữ liệu doanh nghiệp:
    {json.dumps(business, indent=2, ensure_ascii=False)}

    Trả về CHÍNH XÁC một chuỗi JSON theo cấu trúc sau, không thêm văn bản khác:
    {{"score": int, "reason": "string"}}
    """
    
    try:
        completion = safe_groq_chat_completion(
            client=client,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        response_content = completion.choices[0].message.content
        return json.loads(response_content)
    except Exception as e:
        print(f"Error scoring lead: {e}")
        return {"score": 0, "reason": "Không thể phân tích dữ liệu lúc này."}

def generate_insights(business_list: list[dict]) -> list[str]:
    """
    Phân tích tập dữ liệu của các doanh nghiệp.
    Tìm kiếm quy luật, cơ hội tiếp tiếp cận thị trường và các khách hàng tiềm năng nhất.
    Trả về các nhận xét dạng gạch đầu dòng ngắn gọn.
    """
    if not business_list:
        return []
        
    if not client:
        return [f"Phân tích AI đã tắt ({AI_DISABLED_REASON})."]
        
    # Chỉ gửi một tập hợp con dữ liệu để tránh vượt quá giới hạn cửa sổ ngữ cảnh (context window) của mô hình
    compact_list = []
    for b in business_list[:20]: # Giới hạn tối đa 20 doanh nghiệp để phân tích
        compact_list.append({
            "name": b.get("name"),
            "rating": b.get("rating"),
            "reviews": b.get("review_count"),
            "website": b.get("website"),
            "score": b.get("ai_score")
        })
        
    prompt = f"""
    Hãy phân tích danh sách doanh nghiệp sau.
    Tìm các mẫu nổi bật, cơ hội tiếp cận và các lead tiềm năng nhất.
    Trả về các gạch đầu dòng ngắn gọn bằng tiếng Việt.

    Dataset:
    {json.dumps(compact_list, indent=2, ensure_ascii=False)}

    Trả về CHÍNH XÁC một chuỗi JSON theo cấu trúc sau, không thêm văn bản khác:
    {{"insights": ["ý 1", "ý 2", "ý 3"]}}
    """
    
    try:
        completion = safe_groq_chat_completion(
            client=client,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"} # Yêu cầu định dạng JSON để phân tích cú pháp mảng một cách ổn định
        )
        response = json.loads(completion.choices[0].message.content)
        return response.get("insights", [])
    except Exception as e:
        print(f"Error generating insights: {e}")
        return ["Không thể tạo phân tích AI vào lúc này."]


def compare_leads(biz1: Any, biz2: Any) -> dict:
    """
    So sánh chi tiết hai doanh nghiệp cạnh tranh trực tiếp.
    Chỉ ra các điểm mạnh, điểm yếu nổi bật và đưa ra phán quyết khuyên chọn quán nào tốt hơn.
    """
    if not client:
        return {
            "biz1": {"name": biz1.name, "strengths": ["Chấm điểm AI đang tắt"], "weaknesses": []},
            "biz2": {"name": biz2.name, "strengths": ["Chấm điểm AI đang tắt"], "weaknesses": []},
            "analysis": "Chấm điểm AI đang tắt do thiếu GROQ_API_KEY.",
            "verdict": "Chưa thể kết luận."
        }
        
    prompt = f"""
    Bạn là một chuyên gia phân tích kinh doanh hàng đầu.
    Hãy so sánh chi tiết hai doanh nghiệp sau đây dựa trên thông tin cơ bản và tóm tắt đánh giá của khách hàng.
    
    Doanh nghiệp 1:
    - Tên: {biz1.name}
    - Địa chỉ: {biz1.address or 'Chưa có'}
    - Điện thoại: {biz1.phone or 'Chưa có'}
    - Rating: {biz1.rating or 'Chưa có'}
    - Số reviews: {biz1.review_count or 'Chưa có'}
    - Website: {biz1.website or 'Chưa có'}
    - AI Score hiện tại: {biz1.ai_score or 'Chưa có'}
    - Tóm tắt reviews: {biz1.review_summary or "Chưa có review"}
    
    Doanh nghiệp 2:
    - Tên: {biz2.name}
    - Địa chỉ: {biz2.address or 'Chưa có'}
    - Điện thoại: {biz2.phone or 'Chưa có'}
    - Rating: {biz2.rating or 'Chưa có'}
    - Số reviews: {biz2.review_count or 'Chưa có'}
    - Website: {biz2.website or 'Chưa có'}
    - AI Score hiện tại: {biz2.ai_score or 'Chưa có'}
    - Tóm tắt reviews: {biz2.review_summary or "Chưa có review"}
    
    Nhiệm vụ của bạn:
    1. Chỉ ra tối đa 3 Điểm mạnh (strengths) và 3 Điểm yếu (weaknesses) nổi bật nhất của từng quán dựa trên dữ liệu.
    2. Đưa ra phân tích so sánh chiến lược (ngắn gọn, trực diện, không sáo rỗng).
    3. Đưa ra phán quyết (verdict) quán nào tốt hơn và lý do cụ thể.
    4. Trả về kết quả dưới định dạng JSON chính xác.
    
    Cấu trúc JSON phản hồi bắt buộc:
    {{
      "biz1": {{
        "name": "Tên quán 1",
        "strengths": ["điểm mạnh 1", "điểm mạnh 2"],
        "weaknesses": ["điểm yếu 1", "điểm yếu 2"]
      }},
      "biz2": {{
        "name": "Tên quán 2",
        "strengths": ["điểm mạnh 1", "điểm mạnh 2"],
        "weaknesses": ["điểm yếu 1", "điểm yếu 2"]
      }},
      "analysis": "Phân tích so sánh tổng quan ngắn gọn bằng tiếng Việt",
      "verdict": "Kết luận quán nào tốt hơn kèm theo lý do thuyết phục ngắn gọn bằng tiếng Việt"
    }}
    """
    
    try:
        completion = safe_groq_chat_completion(
            client=client,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error comparing leads: {e}")
        return {
            "biz1": {"name": biz1.name, "strengths": ["Không thể phân tích lúc này"], "weaknesses": []},
            "biz2": {"name": biz2.name, "strengths": ["Không thể phân tích lúc này"], "weaknesses": []},
            "analysis": f"Không thể hoàn tất việc phân tích so sánh bằng AI: {e}",
            "verdict": "Chưa thể đưa ra kết luận quán nào tốt hơn."
        }


def generate_report_insights(businesses: list) -> dict:
    """
    Tạo các nhận xét và insights báo cáo thị trường cho danh sách doanh nghiệp được chọn.
    """
    if not client:
        return {
            "market_overview": "Phân tích AI đang tắt.",
            "market_gaps": "Phân tích AI đang tắt.",
            "sales_strategy": "Phân tích AI đang tắt."
        }
        
    compact_list = []
    for b in businesses[:30]:
        compact_list.append({
            "name": b.name,
            "rating": b.rating,
            "reviews": b.review_count,
            "website": b.website,
            "phone": b.phone,
            "ai_score": b.ai_score
        })
        
    prompt = f"""
    Bạn là một chuyên gia tư vấn chiến lược kinh doanh và phân tích thị trường.
    Hãy phân tích danh sách {len(compact_list)} doanh nghiệp sau và lập một báo cáo phân tích thị trường sâu sắc bằng tiếng Việt.
    
    Dữ liệu danh sách doanh nghiệp:
    {json.dumps(compact_list, indent=2, ensure_ascii=False)}
    
    Nhiệm vụ của bạn là lập báo cáo trả về đối tượng JSON chính xác với cấu trúc sau:
    {{
      "market_overview": "Phân tích tổng quan ngắn gọn về sự phân bổ rating, quy mô của các cửa hàng trong khu vực này.",
      "market_gaps": "Chỉ ra các khoảng trống thị trường hoặc cơ hội (ví dụ: bao nhiêu % thiếu website, những quán nào rating thấp nhưng có số lượng reviews lớn cần hỗ trợ marketing/chăm sóc khách hàng).",
      "sales_strategy": "Đề xuất 3 kịch bản telesales/sales trực tiếp cụ thể phù hợp nhất để tiếp cận tập khách hàng tiềm năng này."
    }}
    """
    try:
        completion = safe_groq_chat_completion(
            client=client,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error generating report_insights: {e}")
        return {
            "market_overview": f"Không thể phân tích tổng quan thị trường lúc này: {e}",
            "market_gaps": "Không thể phân tích khoảng trống thị trường lúc này.",
            "sales_strategy": "Không thể gợi ý chiến lược tiếp cận lúc này."
        }


