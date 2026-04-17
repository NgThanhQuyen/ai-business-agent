import pandas as pd
import io
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Business
from database.schemas import SearchRequest, SearchResponse, BusinessOut, BusinessCreate
from services.data_pipeline import run_pipeline

router = APIRouter()


# ── POST /search ──────────────────────────────────────────────────────────────
@router.post("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def search_businesses(payload: SearchRequest, db: Session = Depends(get_db)):
    """
    Full pipeline endpoint:
      1. Call SerpAPI + Data Pipeline + Groq AI Scoring
      2. Upsert results into PostgreSQL
      3. Return the processed list and AI insights
    """
    
    try:
        clean_records, insights = run_pipeline(
            payload.keyword,
            payload.location,
            min_rating=payload.min_rating,
            result_limit=payload.result_limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý pipeline: {str(exc)}",
        )

    if not clean_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy doanh nghiệp phù hợp với điều kiện tìm kiếm đã nhập.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi cơ sở dữ liệu: {str(exc)}",
        )

    return SearchResponse(
        businesses=[BusinessOut.model_validate(b) for b in saved],
        insights=insights
    )


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