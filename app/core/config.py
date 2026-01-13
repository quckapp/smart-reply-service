"""Configuration settings for the Smart Reply Service."""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "smart-reply-service"
    DEBUG: bool = False
    PORT: int = 5019

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # Cache TTL (seconds)
    CACHE_TTL: int = 3600  # 1 hour

    # ML Models
    REPLY_MODEL: str = "microsoft/DialoGPT-medium"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Reply Settings
    MAX_REPLY_LENGTH: int = 100
    NUM_SUGGESTIONS: int = 3
    MIN_CONFIDENCE: float = 0.3
    MAX_CONTEXT_MESSAGES: int = 5

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
