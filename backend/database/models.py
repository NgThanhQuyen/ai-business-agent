import json
from sqlalchemy import Column, Integer, String, Float, DateTime, func, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.sql import text
from database.db import engine, Base

# Check pgvector availability in both python packages and PostgreSQL database
has_pgvector = False
try:
    from pgvector.sqlalchemy import Vector
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector';")).fetchone()
        if res:
            has_pgvector = True
except Exception:
    pass

if has_pgvector:
    embedding_type = Vector(768)
else:
    # Custom type decorator that acts as a Vector serializer/deserializer to TEXT
    class SafeVector(TypeDecorator):
        impl = Text
        cache_ok = True

        def __init__(self, dim):
            super().__init__()
            self.dim = dim

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, list):
                return json.dumps(value)
            return value

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

    embedding_type = SafeVector(768)

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
    review_summary= Column(String, nullable=True)
    embedding     = Column(embedding_type, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())