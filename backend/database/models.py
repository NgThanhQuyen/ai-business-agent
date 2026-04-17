from sqlalchemy import Column, Integer, String, Float, DateTime, func
from database.db import Base

class Business(Base):
    __tablename__ = "businesses"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String, nullable=False)
    address       = Column(String, nullable=True)
    phone         = Column(String, nullable=True)
    rating        = Column(Float, nullable=True)
    review_count  = Column(Integer, nullable=True)
    website       = Column(String, nullable=True)
    latitude      = Column(Float, nullable=True)
    longitude     = Column(Float, nullable=True)
    ai_score      = Column(Integer, nullable=True)
    ai_reason     = Column(String, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())