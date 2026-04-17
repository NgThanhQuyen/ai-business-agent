from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    DB_URL: str
    SERPAPI_KEY: str
    GROQ_API_KEY: Optional[str] = None

    # Always load backend/.env regardless of where uvicorn is launched.
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"))


settings = Settings()