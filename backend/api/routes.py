import pandas as pd
import io
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.db import get_db, SessionLocal
from database.models import Business
from database.schemas import SearchRequest, SearchResponse, BusinessOut, BusinessCreate
from services.data_pipeline import run_pipeline
from database.redis_client import get_cache, set_cache, get_task_status, set_task_status

router = APIRouter()

# ── Background Task Wrapper ──────────────────────────────────────────────────
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
            # If data pipeline already updated task status to completed (no data), do nothing else
            return

        # ── Upsert into DB ─────────────────────────────────────────────────────
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

            if existing:
                existing.phone        = validated.phone
                existing.rating       = validated.rating
                existing.review_count = validated.review_count
                existing.website      = validated.website
                existing.latitude     = validated.latitude
                existing.longitude    = validated.longitude
                existing.ai_score     = validated.ai_score
                existing.ai_reason    = validated.ai_reason
                saved.append(existing)
            else:
                new_biz = Business(**validated.model_dump())
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
        
        # 5. Lưu vào cache trước khi trả về
        set_cache(cache_key, response_data.model_dump())
        set_task_status(task_id, "completed", 100, "Hoàn tất!", response_data.model_dump())
    except Exception as exc:
        set_task_status(task_id, "failed", 0, f"Lỗi xử lý background: {str(exc)}")
    finally:
        db.close()


# ── POST /search ──────────────────────────────────────────────────────────────
@router.post("/search", status_code=status.HTTP_202_ACCEPTED)
def search_businesses(payload: SearchRequest, background_tasks: BackgroundTasks):
    """
    Start the pipeline endpoint asynchronously:
      1. Returns a task_id immediately.
      2. Runs SerpAPI + Data Pipeline + Groq AI Scoring in the background.
    """
    task_id = str(uuid.uuid4())
    
    # 1. Tạo cache_key duy nhất (chuyển về lowercase)
    cache_key = f"search:{payload.keyword}_{payload.location}_{payload.min_rating}_{payload.result_limit}".lower()
    
    # 2. Kiểm tra cache
    cached_data = get_cache(cache_key)
    
    # 3. Xử lý khi Hit Cache
    if cached_data:
        print("⚡ Hit Redis Cache!")
        set_task_status(task_id, "completed", 100, "Hoàn tất! (Từ cache)", cached_data)
        return {"task_id": task_id, "message": "Task completed from cache"}

    # 4. Xử lý khi Miss Cache
    print(f"🐌 Miss Cache, starting background task {task_id}...")
    set_task_status(task_id, "processing", 0, "Task started")
    background_tasks.add_task(background_pipeline_task, task_id, payload, cache_key)

    return {"task_id": task_id, "message": "Task started"}

# ── GET /tasks/{task_id} ──────────────────────────────────────────────────────
@router.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
def get_task(task_id: str):
    """
    Retrieve the status of a background task from Redis.
    """
    task_data = get_task_status(task_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_data


# ── GET /export ───────────────────────────────────────────────────────────────
@router.get("/export", status_code=status.HTTP_200_OK)
def export_businesses(
    format: str = Query(default="csv", pattern="^(csv|excel)$"),
    db: Session = Depends(get_db),
):
    """
    Fetch all businesses from DB and return CSV or Excel download.
    """
    businesses = db.query(Business).all()
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


# ── GET /businesses (Optional utility) ────────────────────────────────────────
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
        insights=[] # Insights are usually generated per search, so return empty here.
    )


# ── DELETE /businesses ────────────────────────────────────────────────────────
@router.delete("/businesses", status_code=status.HTTP_200_OK)
def clear_all_businesses(db: Session = Depends(get_db)):
    deleted_count = db.query(Business).delete()
    db.commit()
    return {"message": f"Deleted {deleted_count} business records."}