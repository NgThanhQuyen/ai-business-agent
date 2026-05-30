import pandas as pd
import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.db import get_db, SessionLocal
from database.models import Business
from database.schemas import (
    SearchRequest,
    SearchResponse,
    BusinessOut,
    BusinessCreate,
    ChatAgentRequest,
    SmartChatResponse,
)
import logging
from services.data_pipeline import run_pipeline
from services.smart_chat_service import process_smart_chat
from database.redis_client import get_cache, set_cache, get_task_status, set_task_status
from services.semantic_agent import run_semantic_search

logger = logging.getLogger(__name__)

router = APIRouter()

# Hàm chạy tiến trình ngầm (Background Task Wrapper)
def background_pipeline_task(task_id: str, payload: SearchRequest, cache_key: str):
    db = SessionLocal()
    try:
        clean_records, insights = run_pipeline(
            payload.keyword,
            payload.location,
            min_rating=payload.min_rating,
            result_limit=payload.result_limit,
            task_id=task_id,
        )

        if not clean_records:
            # Nếu pipeline dữ liệu đã cập nhật trạng thái tác vụ thành hoàn thành (không có dữ liệu), không làm gì thêm
            return

        # Thực hiện cập nhật hoặc thêm mới dữ liệu vào database (Upsert)
        from services.serpapi_service import fetch_reviews_for_place
        from services.semantic_agent import generate_embedding

        saved = []
        for record in clean_records:
            try:
                validated = BusinessCreate(**record)
            except Exception:
                continue                             
                
            existing = (
                db.query(Business)
                .filter(
                    Business.name    == validated.name,
                    Business.address == validated.address,
                )
                .first()
            )

            # Lấy review_summary và embedding nếu cần thiết
            review_summary = None
            embedding = None
            if not existing or not existing.review_summary:
                place_id = record.get("place_id")
                data_id = record.get("data_id")
                # Giới hạn việc lấy review cho top 15 kết quả để quản lý rate limit của API
                if len(saved) < 15:
                    logger.info(f"Fetching reviews for scraped business: {validated.name}")
                    reviews = fetch_reviews_for_place(data_id, place_id)
                    if reviews:
                        review_summary = " | ".join(reviews)
                        try:
                            embedding = generate_embedding(review_summary)
                        except Exception as emb_err:
                            logger.error(f"Failed to generate embedding for {validated.name}: {emb_err}")

            if existing:
                existing.phone        = validated.phone
                existing.rating       = validated.rating
                existing.review_count = validated.review_count
                existing.website      = validated.website
                existing.latitude     = validated.latitude
                existing.longitude    = validated.longitude
                existing.ai_score     = validated.ai_score
                existing.ai_reason    = validated.ai_reason
                if review_summary:
                    existing.review_summary = review_summary
                    existing.embedding = embedding
                saved.append(existing)
            else:
                new_biz = Business(**validated.model_dump())
                if review_summary:
                    new_biz.review_summary = review_summary
                    new_biz.embedding = embedding
                db.add(new_biz)
                saved.append(new_biz)

        try:
            db.commit()
            for biz in saved:
                db.refresh(biz)
        except Exception as exc:
            db.rollback()
            set_task_status(task_id, "failed", 0, f"Lỗi cơ sở dữ liệu: {str(exc)}")
            return

        response_data = SearchResponse(
            businesses=[BusinessOut.model_validate(b) for b in saved],
            insights=insights
        )
        
        # 5. Lưu kết quả vào bộ nhớ đệm cache trước khi trả về
        set_cache(cache_key, response_data.model_dump())
        set_task_status(task_id, "completed", 100, "Hoàn tất!", response_data.model_dump())
    except Exception as exc:
        set_task_status(task_id, "failed", 0, f"Lỗi xử lý background: {str(exc)}")
    finally:
        db.close()


# Endpoint POST /search - Khởi chạy tiến trình tìm kiếm dữ liệu và chấm điểm
@router.post("/search", status_code=status.HTTP_202_ACCEPTED)
def search_businesses(payload: SearchRequest, background_tasks: BackgroundTasks):
    """
    Start the pipeline endpoint asynchronously:
      1. Returns a task_id immediately.
      2. Runs SerpAPI + Data Pipeline + Groq AI Scoring in the background.
    """
    task_id = str(uuid.uuid4())
    
    # 1. Tạo khóa cache (cache key) duy nhất từ tham số tìm kiếm và chuyển về chữ thường
    cache_key = f"search:{payload.keyword}_{payload.location}_{payload.min_rating}_{payload.result_limit}".lower()
    
    # 2. Kiểm tra dữ liệu trong bộ nhớ cache Redis
    cached_data = get_cache(cache_key)
    
    # 3. Xử lý khi dữ liệu đã có sẵn trong cache (Hit Cache)
    if cached_data:
        logger.info("Hit Redis Cache!")
        set_task_status(task_id, "completed", 100, "Hoàn tất! (Từ cache)", cached_data)
        return {"task_id": task_id, "message": "Task completed from cache"}

    # 4. Xử lý khi chưa có dữ liệu trong cache (Miss Cache)
    logger.info(f"Miss Cache, starting background task {task_id}...")
    set_task_status(task_id, "processing", 0, "Task started")
    background_tasks.add_task(background_pipeline_task, task_id, payload, cache_key)

    return {"task_id": task_id, "message": "Task started"}

# Endpoint GET /tasks/{task_id} - Lấy trạng thái tiến trình chạy ngầm
@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def get_task(task_id: str):
    """
    Retrieve the status of a background task from Redis.
    """
    task_data = get_task_status(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_data


# Endpoint GET /export - Xuất danh sách doanh nghiệp ra file CSV hoặc Excel
@router.get("/export", status_code=status.HTTP_200_OK)
def export_businesses(
    format: str = Query(default="csv", pattern="^(csv|excel)$"),
    ids: str = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Fetch all businesses from DB (or filtered by list of IDs) and return CSV or Excel download.
    """
    query = db.query(Business)
    if ids:
        try:
            id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
            if id_list:
                query = query.filter(Business.id.in_(id_list))
        except Exception:
            pass
            
    businesses = query.all()
    if not businesses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không có dữ liệu để xuất file.")
        
    data = []
    for b in businesses:
        data.append({
            "name": b.name,
            "address": b.address,
            "phone": b.phone,
            "rating": b.rating,
            "review_count": b.review_count,
            "website": b.website,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "ai_score": b.ai_score,
            "ai_reason": b.ai_reason
        })
        
    df = pd.DataFrame(data)

    if format == "excel":
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Businesses")
        stream.seek(0)
        response = StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response.headers["Content-Disposition"] = "attachment; filename=export.xlsx"
        return response

    stream = io.StringIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
    )
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"
    return response


# Endpoint GET /businesses - Lấy danh sách doanh nghiệp tiện ích
@router.get("/businesses", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def get_all_businesses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    businesses = (
        db.query(Business)
        .order_by(Business.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return SearchResponse(
        businesses=[BusinessOut.model_validate(b) for b in businesses],
        insights=[] # Các thông tin chi tiết (insights) thường được tạo theo từng lượt tìm kiếm, nên trả về danh sách rỗng ở đây.
    )


# Endpoint DELETE /businesses - Xoá toàn bộ dữ liệu doanh nghiệp trong cơ sở dữ liệu
@router.delete("/businesses", status_code=status.HTTP_200_OK)
def clear_all_businesses(db: Session = Depends(get_db)):
    deleted_count = db.query(Business).delete()
    db.commit()
    return {"message": f"Deleted {deleted_count} business records."}


# Endpoint POST /chat-agent - Trò chuyện thông minh và phân tích dữ liệu
@router.post("/chat-agent", response_model=SmartChatResponse, status_code=status.HTTP_200_OK)
def chat_agent(request: ChatAgentRequest, db: Session = Depends(get_db)):
    try:
        # Kiểm tra xem câu hỏi có phải là yêu cầu tìm kiếm ngữ nghĩa bắt đầu bằng "/ai" hay không
        cleaned_question = request.question.strip() if request.question else ""
        if cleaned_question.startswith("/ai"):
            # Trích xuất nội dung truy vấn thực tế sau ký tự "/ai"
            if cleaned_question.startswith("/ai "):
                query = cleaned_question[4:].strip()
            else:
                query = cleaned_question[3:].strip()
            
            logger.info(f"Triggering Semantic Vector Search with query: '{query}'")
            try:
                result = run_semantic_search(query, db)
                return result
            except Exception as semantic_err:
                logger.warning(
                    f"Semantic Search failed: {semantic_err}. Falling back to standard Text-to-SQL agent.",
                    exc_info=True
                )
                # Chuyển hướng dự phòng sang Text-to-SQL tiêu chuẩn
                return process_smart_chat(request.question, db, context=request.context)
        
        # Luồng xử lý Text-to-SQL tiêu chuẩn
        result = process_smart_chat(request.question, db, context=request.context)
        return result
    except Exception as e:
        logger.exception("Chat agent endpoint failed")
        raise HTTPException(status_code=500, detail="Internal Server Error")


# Các endpoint phục vụ so sánh và tạo báo cáo phân tích thị trường
from pydantic import BaseModel
from typing import List

class CompareRequest(BaseModel):
    id1: int
    id2: int

class ReportRequest(BaseModel):
    ids: List[int]

@router.post("/compare", status_code=status.HTTP_200_OK)
def compare_businesses_route(payload: CompareRequest, db: Session = Depends(get_db)):
    biz1 = db.query(Business).filter(Business.id == payload.id1).first()
    biz2 = db.query(Business).filter(Business.id == payload.id2).first()
    
    if not biz1 or not biz2:
        raise HTTPException(status_code=404, detail="Không tìm thấy một hoặc cả hai doanh nghiệp để so sánh.")
        
    from services.serpapi_service import search_businesses, fetch_reviews_for_place
    from services.semantic_agent import generate_embedding
    
    db_updated = False
    for biz in [biz1, biz2]:
        if not biz.review_summary:
            try:
                logger.info(f"Fetching missing reviews on-the-fly for: {biz.name}")
                search_results = search_businesses(biz.name, biz.address or "", max_results=1)
                if search_results:
                    first = search_results[0]
                    reviews = fetch_reviews_for_place(first.get("data_id"), first.get("place_id"))
                    if reviews:
                        biz.review_summary = " | ".join(reviews)
                        try:
                            biz.embedding = generate_embedding(biz.review_summary)
                        except Exception as emb_err:
                            logger.error(f"Failed to generate embedding on-the-fly for {biz.name}: {emb_err}")
                        db.add(biz)
                        db_updated = True
            except Exception as e:
                logger.error(f"Failed to fetch on-the-fly reviews for {biz.name}: {e}")
                
    if db_updated:
        try:
            db.commit()
            db.refresh(biz1)
            db.refresh(biz2)
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to save on-the-fly reviews: {exc}")
            
    from services.groq_service import compare_leads
    result = compare_leads(biz1, biz2)
    return result

@router.post("/report-insights", status_code=status.HTTP_200_OK)
def report_insights_route(payload: ReportRequest, db: Session = Depends(get_db)):
    if not payload.ids:
        raise HTTPException(status_code=400, detail="Danh sách ID không được để trống.")
        
    businesses = db.query(Business).filter(Business.id.in_(payload.ids)).all()
    if not businesses:
        raise HTTPException(status_code=404, detail="Không tìm thấy các doanh nghiệp yêu cầu.")
        
    from services.groq_service import generate_report_insights
    result = generate_report_insights(businesses)
    return result

