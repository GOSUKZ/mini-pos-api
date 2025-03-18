import redis.asyncio as redis
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict, List, Optional, Any, ClassVar
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend


class Settings(BaseSettings):
    """
    Настройки приложения, загружаемые из переменных окружения.
    """

    # Базовые настройки приложения
    APP_NAME: str = "Products API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True  # Включаем DEBUG режим по умолчанию для упрощения тестирования

    # Настройки базы данных
    DATABASE_NAME: str = "core/products.db"

    # Настройки безопасности
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS настройки
    CORS_ORIGINS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    CORS_METHODS: List[str] = ["*"]

    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS: int = 100
    RATE_LIMIT_TIME_WINDOW: int = 60  # в секундах

    # google
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI")
    GOOGLE_AUTH_URL: Optional[str] = os.getenv("GOOGLE_AUTH_URL")
    GOOGLE_TOKEN_URL: Optional[str] = os.getenv("GOOGLE_TOKEN_URL")
    GOOGLE_USER_INFO_URL: Optional[str] = os.getenv("GOOGLE_USER_INFO_URL")

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "api.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Возвращает настройки приложения с кешированием.

    Returns:
        Экземпляр настроек
    """
    return Settings()


async def init_redis(app: FastAPI):
    settings = get_settings()
    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
    redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
