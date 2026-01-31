"""Configuration settings for FastAPI service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    FASTAPI_PORT: int = 8058
    DEBUG: bool = True
    DATA_DIR: str = "data"
    REDIS_URL: str | None = None
    USE_REDIS: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
