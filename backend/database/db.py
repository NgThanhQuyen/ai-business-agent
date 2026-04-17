from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

engine = create_engine(settings.DB_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency injector: yields a DB session and ensures it closes after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()