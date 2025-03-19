"""
Module for metrics-related endpoints.

This module contains endpoints for retrieving metrics about API usage.
Currently, it only provides an endpoint for retrieving the number of calls
to each endpoint.
"""

from fastapi import APIRouter
from fastapi_cache import FastAPICache

router = APIRouter(
    tags=["Metrics"],
)


async def increment_metric(endpoint: str):
    """Увеличивает счетчик вызовов API в Redis."""
    redis_client = FastAPICache.get_backend().redis
    await redis_client.incr(f"metrics:{endpoint}")


async def get_metrics():
    """Получает метрики вызовов API из Redis."""
    redis_client = FastAPICache.get_backend().redis
    keys = await redis_client.keys("metrics:*")
    metrics = {}
    for key in keys:
        if isinstance(key, bytes):
            endpoint = key.decode().split(":")[1]
        else:
            endpoint = key.split(":")[1]
        metrics[endpoint] = int(await redis_client.get(key))
    return metrics


@router.get("/metrics")
async def metrics():
    """Возвращает количество вызовов каждого API-эндпоинта."""
    return await get_metrics()
