"""
This module provides a router for handling authentication-related endpoints.

The endpoints are:
- `/auth/register`: Registers a new user.
- `/auth/login`: Logs in an existing user.
- `/auth/logout`: Logs out the current user.
- `/auth/token`: Generates a new token for the current user.

The module uses the `get_auth_service` dependency to create an instance of the
`AuthService` class, which provides the actual authentication logic.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from config import get_settings
from core.models import Token, UserCreate, UserLogin
from utils.dependencies import get_services
from utils.service_factory import ServiceFactory

logger = logging.getLogger("auth_router")
settings = get_settings()

# Создаем роутер
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
    responses={401: {"description": "Unauthorized"}},
)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    services: ServiceFactory = Depends(get_services),
):
    """
    Регистрация нового пользователя.
    """
    logger.info("Регистрация нового пользователя: %s", user_data.username)

    try:
        user = await services.get_auth_service().register_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            roles=user_data.roles,
        )

        return {"message": "User registered successfully", "username": user.get("username")}
    except ValueError as e:
        logger.warning("Ошибка при регистрации пользователя: %s", str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Ошибка при регистрации пользователя: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: UserLogin,
    services: ServiceFactory = Depends(get_services),
):
    """
    Получение токена доступа.
    """
    logger.info("Запрос токена для пользователя: %s", form_data.username)

    try:
        user = await services.get_auth_service().authenticate_user(
            username=form_data.username, password=form_data.password
        )

        if not user:
            logger.warning(
                "Неудачная попытка аутентификации для пользователя: %s", form_data.username
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = services.get_auth_service().create_access_token(
            data={"sub": user.get("username"), "roles": user.get("roles", [])},
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при аутентификации пользователя: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
