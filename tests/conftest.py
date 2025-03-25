# import asyncio
# from unittest.mock import AsyncMock

# import asyncpg
# import pytest
# import pytest_asyncio
# from asgi_lifespan import LifespanManager
# from httpx import ASGITransport, AsyncClient

# from main import app

# pytest_plugins = "pytest_asyncio"

# TEST_DATABASE_URL = "postgresql://makkenzo:qwerty@localhost:5432/claude_data_shop"


# @pytest.fixture(scope="session")
# def event_loop():
#     """Создаёт новый событийный цикл для тестов."""
#     loop = asyncio.new_event_loop()
#     yield loop
#     loop.close()


# @pytest_asyncio.fixture
# async def clear_users_table(db_pool):
#     """Очищает таблицу пользователей перед тестом."""
#     async with db_pool.acquire() as conn:
#         await conn.execute("DELETE FROM users WHERE username LIKE 'makkenzo%'")


# @pytest_asyncio.fixture
# async def db_pool():
#     """Фикстура для создания пула соединений."""
#     pool = await asyncpg.create_pool(TEST_DATABASE_URL)
#     app.db_pool = pool  # Подменяем продакшен-базу на тестовую

#     yield pool  # Передаём управление тестам

#     await pool.close()


# @pytest_asyncio.fixture
# async def async_client(db_pool):
#     """Фикстура для тестового HTTP-клиента."""
#     async with LifespanManager(app):  # Запускаем приложение с on_startup
#         async with AsyncClient(
#             transport=ASGITransport(app=app), base_url="http://127.0.0.1:8000"
#         ) as client:
#             yield client


# @pytest_asyncio.fixture
# async def mock_redis():
#     redis_mock = AsyncMock()
#     redis_mock.get.return_value = None
#     return redis_mock


# @pytest.fixture
# async def auth_headers(async_client: AsyncClient):
#     """Фикстура для получения заголовков с авторизацией."""

#     response = await async_client.post(
#         "/auth/token",
#         json={"username": "makkenzo", "password": "Qwerty123!"},
#     )

#     assert response.status_code == 200
#     token = response.json()["access_token"]

#     return {"Authorization": f"Bearer {token}"}
