import os
from pathlib import Path
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "GradeMIND Backend"
    PROJECT_VERSION: str = "1.0.0"
    DATABASE_URL: str
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # default to 60 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEBUG: bool = False
    AUTH_ENABLED: bool = False
    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3001"
    )
    CORS_ALLOWED_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"

    # Gemini API Configuration (optional secondary/cross-check evaluator;
    # core grading works with zero LLM keys via the local autonomous evaluator)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_env(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "development", "dev", "true", "1", "yes", "on"}:
                return True
        return value

    # Configure Pydantic settings to load from .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instantiate the singleton settings object
settings = Settings()


def get_cors_allowed_origins() -> list[str]:
    return [
        origin.strip().rstrip("/")
        for origin in settings.CORS_ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
