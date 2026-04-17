import json
from groq import Groq
from core.config import settings

AI_DISABLED_REASON = ""


def _build_client() -> Groq | None:
    global AI_DISABLED_REASON

    if not settings.GROQ_API_KEY:
        AI_DISABLED_REASON = "Missing GROQ_API_KEY in backend/.env"
        return None

    try:
        return Groq(api_key=settings.GROQ_API_KEY)
    except Exception as e:
        # Keep API startup alive even if Groq/httpx dependencies are mismatched.
        AI_DISABLED_REASON = f"Groq client init failed: {e}"
        print(f"Failed to initialize Groq client: {e}")
        return None


client = _build_client()

def score_lead(business: dict) -> dict:
    """
    Score this business (0–100) based on:
    - rating
    - review count
    - missing website
    """
    if not client:
        # Mock default response if AI is disabled
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
        completion = client.chat.completions.create(
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
    Analyze dataset of businesses.
    Find patterns, opportunities, best leads.
    Return concise bullet points.
    """
    if not business_list:
        return []
        
    if not client:
        return [f"Phân tích AI đã tắt ({AI_DISABLED_REASON})."]
        
    # We only send a subset of data to avoid exceeding context window
    compact_list = []
    for b in business_list[:20]: # Limit to top 20 for analysis
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
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"} # Require JSON to robustly parse the array
        )
        response = json.loads(completion.choices[0].message.content)
        return response.get("insights", [])
    except Exception as e:
        print(f"Error generating insights: {e}")
        return ["Không thể tạo phân tích AI vào lúc này."]
