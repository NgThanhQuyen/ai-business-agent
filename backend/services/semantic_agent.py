import logging
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional

from core.config import settings
from database.models import Business
from database.schemas import BusinessOut, SmartChatResponse
from groq import Groq
from services.groq_service import safe_groq_chat_completion

logger = logging.getLogger(__name__)

# Mô hình nhúng dữ liệu (embedding) được tải chậm (lazy load)
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        model_name = "keepitreal/vietnamese-sbert"
        logger.info(f"Loading SentenceTransformer model '{model_name}'...")
        _embedding_model = SentenceTransformer(model_name)
        logger.info("SentenceTransformer model loaded successfully.")
    return _embedding_model

def generate_embedding(text: str) -> List[float]:
    if not text:
        return [0.0] * 768
    model = get_embedding_model()
    embedding = model.encode(text)
    return embedding.tolist()

def get_db_location_terms(location_str: str) -> list[str]:
    if not location_str:
        return []
    loc_lower = location_str.lower().strip()
    
    tphcm_aliases = {"tphcm", "tp.hcm", "tp hcm", "sai gon", "saigon", "ho chi minh", "hồ chí minh", "thành phố hồ chí minh"}
    if loc_lower in tphcm_aliases:
        return ["Hồ Chí Minh", "Ho Chi Minh", "Sài Gòn", "Saigon"]
        
    hcm_districts = {
        "quan 1": ["Quận 1", "Quan 1", "Q.1", "Q1", "District 1"],
        "quan 2": ["Quận 2", "Quan 2", "Q.2", "Q2", "District 2"],
        "quan 3": ["Quận 3", "Quan 3", "Q.3", "Q3", "District 3"],
        "quan 4": ["Quận 4", "Quan 4", "Q.4", "Q4", "District 4"],
        "quan 5": ["Quận 5", "Quan 5", "Q.5", "Q5", "District 5"],
        "quan 6": ["Quận 6", "Quan 6", "Q.6", "Q6", "District 6"],
        "quan 7": ["Quận 7", "Quan 7", "Q.7", "Q7", "District 7"],
        "quan 8": ["Quận 8", "Quan 8", "Q.8", "Q8", "District 8"],
        "quan 9": ["Quận 9", "Quan 9", "Q.9", "Q9", "District 9"],
        "quan 10": ["Quận 10", "Quan 10", "Q.10", "Q10", "District 10"],
        "quan 11": ["Quận 11", "Quan 11", "Q.11", "Q11", "District 11"],
        "quan 12": ["Quận 12", "Quan 12", "Q.12", "Q12", "District 12"],
        "binh tan": ["Bình Tân", "Binh Tan"],
        "binh thanh": ["Bình Thạnh", "Binh Thanh"],
        "go vap": ["Gò Vấp", "Go Vap"],
        "phu nhuan": ["Phú Nhuận", "Phu Nhuan"],
        "tan binh": ["Tân Bình", "Tan Binh"],
        "tan phu": ["Tân Phú", "Tan Phu"],
        "thu duc": ["Thủ Đức", "Thu Duc"],
        "binh chanh": ["Bình Chánh", "Binh Chanh"],
        "can gio": ["Cần Giờ", "Can Gio"],
        "cu chi": ["Củ Chi", "Cu Chi"],
        "hoc mon": ["Hóc Môn", "Hoc Mon"],
        "nha be": ["Nhà Bè", "Nha Be"]
    }
    
    for key, terms in hcm_districts.items():
        if key in loc_lower or any(t.lower() in loc_lower for t in terms):
            return terms
            
    from services.smart_chat_service import _normalize_text
    normalized_loc = _normalize_text(location_str)
    return [location_str, normalized_loc]

def extract_semantic_params(query: str) -> dict:
    """
    Extract keyword and location from query using Groq LLM.
    """
    client = Groq(api_key=settings.GROQ_API_KEY)
    prompt = f"""
Bạn là AI phân tích yêu cầu tìm kiếm của người dùng và trích xuất thông tin.
Đọc yêu cầu tìm kiếm của người dùng và trả về DUY NHẤT 1 đối tượng JSON, không markdown.
Yêu cầu: "{query}"

Schema JSON bắt buộc:
{{
  "keyword": "từ khóa về loại hình/ngành nghề/dịch vụ, ví dụ: 'cà phê', 'đồng hồ', 'tiệm vàng', 'ăn uống'; để trống \"\" nếu không có",
  "location": "khu vực cụ thể được nhắc đến. Hãy nhận diện chính xác các địa điểm tại TPHCM như: Quận 1, Quận 2, Quận 3, Quận 4, Quận 5, Quận 6, Quận 7, Quận 8, Quận 9, Quận 10, Quận 11, Quận 12, Bình Tân, Bình Thạnh, Gò Vấp, Phú Nhuận, Tân Bình, Tân Phú, Thủ Đức, Bình Chánh, Cần Giờ, Củ Chi, Hóc Môn, Nhà Bè hoặc TPHCM/Sài Gòn; để trống \"\" nếu không có"
}}
"""
    try:
        completion = safe_groq_chat_completion(
            client=client,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        import json
        res = json.loads(completion.choices[0].message.content)
        return res
    except Exception as e:
        logger.warning(f"Failed to extract semantic params: {e}")
        return {"keyword": "", "location": ""}

def run_semantic_search(query: str, db: Session) -> dict:
    """
    Perform semantic search:
    1. Extract keyword and location parameters from query.
    2. Filter businesses by location and ensure review_summary is present (cleared mock reviews).
    3. If database matching count is too low (< 3), prompt online scraping via Google Maps.
    4. Run vector cosine similarity search on the filtered subset.
    5. Generate a summarized recommendation using Groq LLM citing actual reviews.
    """
    try:
        # 1. Extract search intent
        params = extract_semantic_params(query)
        keyword = params.get("keyword") or ""
        location = params.get("location") or ""
        logger.info(f"Extracted search parameters -> Keyword: '{keyword}', Location: '{location}'")
        
        # 2. Filter query by reviews and location
        filtered_query = db.query(Business).filter(Business.review_summary.isnot(None))
        if location:
            db_terms = get_db_location_terms(location)
            or_filters = [Business.address.ilike(f"%{term}%") for term in db_terms]
            filtered_query = filtered_query.filter(sa.or_(*or_filters))
            
        total_found = filtered_query.count()
        logger.info(f"Found {total_found} businesses with reviews in CSDL for location '{location}'")
        
        # 3. Check if we need to trigger Google Maps scraping online
        if location and total_found < 3:
            extracted_params = {
                "type": "list_data",
                "keyword": keyword or "cà phê",
                "location": location,
                "min_rating": 0.0,
                "limit": 10,
                "search_payload": {
                    "keyword": keyword or "cà phê",
                    "location": location,
                    "min_rating": 0.0,
                    "result_limit": 10,
                }
            }
            return {
                "ai_message": f"Dạ trong kho dữ liệu của em hiện chưa có đủ dữ liệu review cho '{keyword or 'doanh nghiệp'}' tại '{location}'. Bạn bấm tìm kiếm bên dưới để em cào thêm dữ liệu từ Google Maps nhé!",
                "status": "need_more_data",
                "data": [],
                "extracted_params": extracted_params
            }
            
        # 4. Generate query embedding
        query_vector = generate_embedding(query)
        
        # 5. Retrieve top businesses
        matched_businesses = []
        
        # Thử nghiệm tìm kiếm độ tương đồng cosine ở cấp độ cơ sở dữ liệu nếu pgvector được cài đặt
        try:
            # Sử dụng toán tử <=> của pgvector (khoảng cách cosine)
            top_businesses = (
                filtered_query
                .order_by(Business.embedding.op('<=>')(query_vector))
                .limit(5)
                .all()
            )
            matched_businesses = top_businesses
            logger.info("Vector Search executed at DB-level via pgvector!")
            
        except Exception as db_err:
            # Phương án dự phòng: tính toán độ tương đồng cosine bằng Python thuần trong bộ nhớ
            logger.warning(f"Database-level vector search failed or pgvector not available: {db_err}. Falling back to Python-native search.")
            db.rollback()
            
            # Lấy danh sách tất cả doanh nghiệp thỏa điều kiện
            all_businesses = filtered_query.all()
            
            candidates = []
            for biz in all_businesses:
                emb = biz.embedding
                if emb is None:
                    continue
                
                # Nếu embedding được lưu dưới dạng chuỗi văn bản (chế độ dự phòng), thực hiện giải mã
                if isinstance(emb, str):
                    import json
                    try:
                        emb = json.loads(emb)
                    except Exception:
                        continue
                
                if isinstance(emb, np.ndarray):
                    emb_list = emb.tolist()
                elif isinstance(emb, list):
                    emb_list = emb
                else:
                    continue
                
                if len(emb_list) != 768:
                    continue
                
                # Tính toán độ tương đồng Cosine
                u = np.array(query_vector)
                v = np.array(emb_list)
                dot_product = np.dot(u, v)
                norm_u = np.linalg.norm(u)
                norm_v = np.linalg.norm(v)
                
                if norm_u == 0 or norm_v == 0:
                    similarity = 0.0
                else:
                    similarity = dot_product / (norm_u * norm_v)
                
                candidates.append((biz, similarity))
            
            # Sắp xếp các ứng viên theo độ tương đồng giảm dần và lấy 5 kết quả cao nhất
            candidates.sort(key=lambda x: x[1], reverse=True)
            matched_businesses = [c[0] for c in candidates[:5]]
            logger.info(f"Vector Search executed at Python-level (Python-native fallback)! Found {len(matched_businesses)} matches.")
            
        if not matched_businesses:
            return {
                "ai_message": "Dạ hiện tại tôi không tìm thấy doanh nghiệp nào có thông tin review trong cơ sở dữ liệu để thực hiện tìm kiếm ngữ nghĩa.",
                "status": "success_enough_data",
                "data": []
            }
            
        # 3. Formulate Prompt for Groq LLM
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        # Build prompt context
        businesses_context = []
        for idx, biz in enumerate(matched_businesses):
            rating_desc = f"{biz.rating} sao" if biz.rating else "chưa có đánh giá"
            reviews_desc = f"({biz.review_count} review)" if biz.review_count else ""
            businesses_context.append(
                f"{idx + 1}. Tên quán: {biz.name}\n"
                f"   Địa chỉ: {biz.address or 'Chưa có'}\n"
                f"   Đánh giá: {rating_desc} {reviews_desc}\n"
                f"   Tóm tắt Review: {biz.review_summary or 'Chưa có review'}"
            )
        
        context_str = "\n\n".join(businesses_context)
        
        prompt = f"""
Bạn là Chuyên gia tư vấn & Phân tích dữ liệu doanh nghiệp (AI Analyst) cho người dùng của mình.
Người dùng muốn tìm kiếm các doanh nghiệp dựa trên cảm nhận/nhu cầu ngữ nghĩa sau:
"{query}"

Dưới đây là danh sách Top {len(matched_businesses)} doanh nghiệp phù hợp nhất từ kho dữ liệu, kèm theo tóm tắt review thực tế:

{context_str}

Nhiệm vụ của bạn là viết một bài phản hồi tư vấn bằng tiếng Việt cho người dùng. Hãy tuân thủ nghiêm ngặt các quy tắc sau:
1. TRẢ LỜI NGẮN GỌN, VÀO THẲNG VẤN ĐỀ. Không dùng các từ sáo rỗng như "Trước hết, tôi muốn nói rằng...", "Tiếp theo tôi giới thiệu...", "Tóm lại, tôi tin rằng...".
2. BẮT BUỘC trình bày theo định dạng Markdown sau:
Chào bạn, dựa trên dữ liệu hiện có, em tìm được các quán phù hợp với yêu cầu:
1. **[Tên Quán]** - [Số sao] ([Số đánh giá] đánh giá)
   * Địa chỉ: [Địa chỉ]
   * Lý do đề xuất: [Phân tích ngắn gọn vì sao khớp với nhu cầu, trích dẫn review "..."].

2. **[Tên Quán]**...

3. CHỨNG MINH THUYẾT PHỤC: Tập trung bám sát vào yêu cầu đặc biệt của người dùng (như "hoàng hôn", "yên tĩnh", "view đẹp", v.v.).
4. QUY TẮC SỰ THẬT: CHỈ ĐƯỢC trích dẫn những gì có thật trong phần tóm tắt review được cung cấp ở trên. Tuyệt đối KHÔNG TỰ BỊA (hallucinate) thêm ưu điểm hoặc chi tiết cho quán nếu dữ liệu không nhắc đến. Trích dẫn review bằng dấu ngoặc kép "". Nếu dữ liệu review của quán không nhắc đến yêu cầu đặc biệt của người dùng (ví dụ: không nhắc đến từ "hoàng hôn"), hãy thành thật nói rõ là dữ liệu review hiện tại chưa đề cập đến yếu tố đó.
"""
        
        completion = safe_groq_chat_completion(
            client=client,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        ai_message = completion.choices[0].message.content or ""
        
        # Trả về định dạng phản hồi chuẩn khớp với SmartChatResponse
        return {
            "ai_message": ai_message,
            "status": "success_enough_data",
            "data": [BusinessOut.model_validate(b) for b in matched_businesses]
        }
        
    except Exception as e:
        logger.exception("Semantic Search failed")
        raise e
