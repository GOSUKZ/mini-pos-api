"""
Configuration module.

This module provides a class for configuration values.
"""

import os
from functools import lru_cache
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

load_dotenv()


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

    # REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    # REDIS_PORT: str = os.getenv("REDIS_PORT", "6379")

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "api.log"

    POSTGRES_HOST: Optional[str] = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: Optional[str] = os.getenv("POSTGRES_PORT")
    POSTGRES_USER: Optional[str] = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: Optional[str] = os.getenv("POSTGRES_DB")

    DATABASE_URL: Optional[str] = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensetive=True, extra="allow"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Возвращает настройки приложения с кешированием.

    Returns:
        Экземпляр настроек
    """
    return Settings()


# async def custom_key_builder(
#     func,
#     namespace: str,
#     *,
#     request: Optional[Request] = None,
#     response: Optional[Response] = None,
#     args: Tuple[Any, ...],
#     kwargs: Dict[str, Any],
# ) -> str:
#     """Кастомный генератор ключа кэша."""
#     query_params = tuple(sorted(request.query_params.items())) if request else ()
#     return f"{namespace}:{request.url.path}:{query_params}"


# async def init_redis(app: FastAPI):
#     settings = get_settings()
#     redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
#     redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
#     FastAPICache.init(
#         RedisBackend(redis_client), prefix="fastapi-cache", key_builder=custom_key_builder
#     )


# async def clear_warehouse_cache():
#     """
#     Clears all cached warehouse data from Redis.

#     This function retrieves all keys related to cached warehouse data
#     from Redis using the prefix 'fastapi-cache:warehouses:' and deletes
#     them to ensure that the cache is cleared. It is useful for maintaining
#     data consistency by removing stale cache entries.
#     """

#     redis_backend: RedisBackend = FastAPICache.get_backend()
#     redis_client: redis.Redis = redis_backend.redis

#     keys = await redis_client.keys("fastapi-cache:warehouses:*")  # Найти все ключи складов
#     if keys:
#         await redis_client.delete(*keys)  # Удалить их
