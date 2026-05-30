from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


# ---------- Request ----------
class SearchRequest(BaseModel):
    keyword: str
    location: str
    min_rating: Optional[float] = Field(default=None, ge=0, le=5)
    result_limit: Optional[int] = Field(default=None, ge=1, le=100)


# ---------- Response ----------
class BusinessBase(BaseModel):
    name:         str
    address:      Optional[str] = None
    phone:        Optional[str] = None
    rating:       Optional[float] = None
    review_count: Optional[int] = None
    website:      Optional[str] = None
    latitude:     Optional[float] = None
    longitude:    Optional[float] = None
    ai_score:     Optional[int] = None
    ai_reason:    Optional[str] = None


class BusinessCreate(BusinessBase):
    """Schema used when inserting into the DB (no id / created_at yet)."""
    pass


class BusinessOut(BusinessBase):
    """Schema returned to the client — includes DB-generated fields."""
    id:         int
    created_at: datetime

    class Config:
        from_attributes = True  # replaces orm_mode in Pydantic v2


# ---------- Search response wrapper ----------
class SearchResponse(BaseModel):
    businesses: list[BusinessOut]
    insights: list[str]


# ---------- Chat agent ----------
class ChatAgentRequest(BaseModel):
    question: str
    context: Optional[dict] = None


class ChatAgentResponse(BaseModel):
    answer: str


class SmartChatResponse(BaseModel):
    ai_message: str
    status: Literal["success_enough_data", "need_more_data"]
    data: List[BusinessOut]
    extracted_params: Optional[dict] = None
