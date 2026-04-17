from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from database.db import Base, engine
from api.routes import router


# ── Create tables on startup (simple approach — use Alembic for production) ──
Base.metadata.create_all(bind=engine)


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Business Lead Generation API",
    description="Search businesses via Google Places, clean & store results.",
    version="1.0.0",
)


# ── CORS ──────────────────────────────────────────────────────────────────────
# In production, replace "*" with your actual frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api", tags=["Businesses"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "API is running."}