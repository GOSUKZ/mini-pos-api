from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path
import logging
from utils.dependencies import get_db_service, get_auth_service, has_role, get_current_active_user
from core.database import DatabaseService
from services.auth_service import AuthService
from core.models import User, UserUpdate

logger = logging.getLogger("user_router")

# Создаем роутер
router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=User)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Получение информации о текущем пользователе.
    """
    return current_user

@router.put("/me", response_model=User)
async def update_user_me(
    user_update: UserUpdate,
    db_service: DatabaseService = Depends(get_db_service),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Обновление данных текущего пользователя.
    """
    logger.info(f"Обновление данных пользователя {current_user.username}")

    try:
        update_data = user_update.model_dump(exclude_unset=True)

        # Не позволяем пользователю менять свои роли
        if "roles" in update_data:
            del update_data["roles"]

        # Хешируем пароль, если он изменяется
        if "password" in update_data:
            update_data["hashed_password"] = auth_service.get_password_hash(update_data.pop("password"))

        updated_user = await db_service.update_user(
            username=current_user.username,
            user_data=update_data
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Записываем в аудит
        await db_service.add_audit_log(
            action="update",
            entity="user",
            entity_id=current_user.username,
            user_id=current_user.username,
            details=f"Updated own profile, fields: {', '.join(update_data.keys())}"
        )

        return User(**updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя {current_user.username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/", response_model=List[User])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db_service: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(has_role(["admin"]))
):
    """
    Получение списка пользователей.
    Требуются права администратора.
    """
    # В этой реализации API отсутствует метод получения всех пользователей,
    # но можно добавить этот функционал
    # Пример реализации:

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This endpoint is not implemented yet"
    )

@router.put("/{username}", response_model=User)
async def update_user(
    username: str = Path(..., min_length=3),
    user_update: UserUpdate = ...,
    db_service: DatabaseService = Depends(get_db_service),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(has_role(["admin"]))
):
    """
    Обновление данных пользователя администратором.
    Требуются права администратора.
    """
    logger.info(f"Обновление пользователя {username} администратором {current_user.username}")

    try:
        # Проверяем существование пользователя
        user = await db_service.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        update_data = user_update.model_dump(exclude_unset=True)

        # Хешируем пароль, если он изменяется
        if "password" in update_data:
            update_data["hashed_password"] = auth_service.get_password_hash(update_data.pop("password"))

        updated_user = await db_service.update_user(
            username=username,
            user_data=update_data
        )

        # Записываем в аудит
        await db_service.add_audit_log(
            action="update",
            entity="user",
            entity_id=username,
            user_id=current_user.username,
            details=f"Admin updated user {username}, fields: {', '.join(update_data.keys())}"
        )

        return User(**updated_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя {username}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )