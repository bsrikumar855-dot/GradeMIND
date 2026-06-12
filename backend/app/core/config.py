import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory of the backend project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "GradeMIND Backend"
    PROJECT_VERSION: str = "1.0.0"
    DATABASE_URL: str
    SECRET_KEY: str
    DEBUG: bool = True

    # Configure Pydantic settings to load from .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(BASE_DIR, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Instantiate the singleton settings object
settings = Settings()
