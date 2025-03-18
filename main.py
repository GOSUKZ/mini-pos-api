import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Импортируем настройки
from config import get_settings, init_redis
from core.init_db import create_database

# Импортируем роутеры
from routers import audit, auth, global_product, local_product, metrics, user
from routers.metrics import increment_metric
from routers.payment import router as payment_router

# Инициализируем настройки
settings = get_settings()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[logging.FileHandler(settings.LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("main")


# Контекстный менеджер жизненного цикла приложения
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Manages the application lifespan, handling setup and teardown operations.

    Args:
        app: The FastAPI application instance.
    """
    # Code executed during application startup
    logger.info("Initializing application")
    await init_redis(_app)  # Initialize Redis connection
    logger.info("Redis connection established")

    # Create and initialize the database
    _app.db_pool = await create_database()

    logger.info("Database initialized")

    yield  # Yield control back to the _application

    # Code executed during _application shutdown
    await _app.db_pool.close()  # Close the database connection
    logger.info("Database connection closed")


# Создаем экземпляр приложения
app = FastAPI(
    title=settings.APP_NAME,
    description="API для управления товарами с использованием FastAPI и Pydantic 2",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)


# Middleware для измерения времени выполнения запросов
@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    """Миддлвар для подсчета вызовов API и измерения времени обработки запроса."""
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    await increment_metric(request.url.path)  # Увеличиваем счетчик вызовов

    return response


# Обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        error_details.append(
            {
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
        )

    logger.warning(f"Ошибка валидации: {error_details}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": error_details}
    )


# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Настройка доверенных хостов - отключаем в тестовом режиме
# Это одна из ключевых причин ошибок 400 Bad Request в тестах
if not settings.DEBUG:
    # В тестовом режиме мы не ограничиваем хосты
    # В боевом режиме ограничиваем доступными хостами
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "testserver"],  # Добавляем testserver для тестов
    )

# Подключаем роутеры
app.include_router(auth.router)
app.include_router(global_product.router)
app.include_router(local_product.router)
app.include_router(audit.router)
app.include_router(user.router)
app.include_router(payment_router)
app.include_router(metrics.router)


# Корневой эндпоинт
@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Welcome to the Products API",
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


# Запуск приложения (для разработки)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
