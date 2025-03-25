# import pytest
# from httpx import AsyncClient


# @pytest.mark.asyncio
# async def test_redis_get(mock_redis):
#     result = await mock_redis.get("some_key")
#     assert result is None


# @pytest.mark.asyncio
# async def test_register_success(async_client: AsyncClient, clear_users_table):
#     """
#     Test successful user registration.

#     This test sends a POST request to the /auth/register endpoint with valid user data.
#     It asserts that the response status code is 201 and the response message indicates
#     successful registration.
#     """

#     response = await async_client.post(
#         "/auth/register",
#         json={
#             "username": "makkenzo",
#             "email": "nekgo2009@gmail.com",
#             "is_active": True,
#             "roles": ["user"],
#             "password": "Qwerty123!",
#         },
#     )
#     assert response.status_code == 201
#     assert response.json()["message"] == "User registered successfully"


# @pytest.mark.asyncio
# async def test_login_success(async_client: AsyncClient):
#     """
#     Test successful user login.

#     This test sends a POST request to the /auth/register endpoint with valid user data,
#     then sends a POST request to the /auth/login endpoint with the same user data.
#     It asserts that the response status code is 200 and the response message contains
#     the access token and token type.
#     """

#     # Логин
#     response = await async_client.post(
#         "/auth/token", json={"username": "makkenzo", "password": "Qwerty123!"}
#     )

#     assert response.status_code == 200
#     response_data = response.json()
#     assert "access_token" in response_data
#     assert "token_type" in response_data


# @pytest.mark.asyncio
# async def test_login_wrong_password(async_client: AsyncClient):
#     """Тест неудачного входа (неправильный пароль)."""
#     response = await async_client.post(
#         "/auth/token", json={"username": "makkenzo", "password": "WrongPassword!"}
#     )

#     assert response.status_code == 401


# @pytest.mark.asyncio
# async def test_get_global_products_success(async_client: AsyncClient, auth_headers):
#     """Тест успешного получения списка товаров."""
#     response = await async_client.get("/products/global", headers=auth_headers)

#     assert response.status_code == 200
#     assert "content" in response.json()
