"""
Module for authentication service.

This module provides a service for authentication operations.
"""

import logging
import os
from http.client import HTTPException
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import jwt
from passlib.context import CryptContext

from config import get_settings
from services.database.user import UsersDataService

logger = logging.getLogger("auth_service")
settings = get_settings()
# Константы
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Сервис для аутентификации и авторизации пользователей.
    """

    def __init__(self, db_service: UsersDataService):
        """
        Инициализирует сервис с сервисом базы данных.

        Args:
            db_service: Сервис базы данных
        """
        self.db_service = db_service

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверяет соответствие пароля его хешу.

        Args:
            plain_password: Пароль в открытом виде
            hashed_password: Хеш пароля

        Returns:
            True, если пароль соответствует хешу, иначе False
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Создает хеш пароля.

        Args:
            password: Пароль в открытом виде

        Returns:
            Хеш пароля
        """
        return pwd_context.hash(password)

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Аутентифицирует пользователя по имени пользователя и паролю.

        Args:
            username: Имя пользователя
            password: Пароль в открытом виде

        Returns:
            Словарь с данными пользователя или None, если аутентификация не удалась
        """
        try:
            user = await self.db_service.get_user_by_username(username)

            if not user:
                logger.warning("Попытка аутентификации несуществующего пользователя: %s", username)
                return None

            if not user.get("is_active", False):
                logger.warning("Попытка аутентификации неактивного пользователя: %s", username)
                return None

            if not self.verify_password(password, user.get("hashed_password", "")):
                logger.warning("Неверный пароль для пользователя: %s", username)
                return None

            # Записываем в аудит успешный вход
            await self.db_service.add_audit_log(
                action="login",
                entity="user",
                entity_id=username,
                user_id=str(username),
                details="Successful login",
            )

            return user
        except Exception as e:
            logger.error("Ошибка при аутентификации пользователя %s: %s", username, str(e))
            raise

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """
        Создает JWT токен доступа.

        Args:
            data: Данные для включения в токен
            expires_delta: Срок действия токена

        Returns:
            JWT токен
        """
        to_encode = data.copy()

        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error("Ошибка при создании токена: %s", str(e))
            raise

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Декодирует и проверяет JWT токен.

        Args:
            token: JWT токен

        Returns:
            Декодированные данные из токена или None при ошибке
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Токен с истекшим сроком действия")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Недействительный токен")
            return None
        except Exception as e:
            logger.error("Ошибка при декодировании токена: %s", str(e))
            return None

    async def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получает текущего пользователя по токену.

        Args:
            token: JWT токен

        Returns:
            Словарь с данными текущего пользователя или None, если токен недействителен
        """
        payload = self.decode_token(token)

        if not payload:
            return None

        username = payload.get("sub")

        if not username:
            return None

        try:
            user = await self.db_service.get_user_by_username(username)
            return user
        except Exception as e:
            logger.error("Ошибка при получении пользователя по токену: %s", str(e))
            return None

    def check_permissions(self, user: Dict[str, Any], required_roles: List[str]) -> bool:
        """
        Проверяет, имеет ли пользователь необходимые роли.

        Args:
            user: Словарь с данными пользователя
            required_roles: Список необходимых ролей

        Returns:
            True, если пользователь имеет необходимые роли, иначе False
        """
        if not user:
            return False

        if not user.get("is_active", False):
            return False

        user_roles = user.get("roles", [])

        for role in required_roles:
            if role in user_roles:
                return True

        return False

    async def register_user(
        self, username: str, password: str, email: Optional[str] = None, roles: List[str] = ["user"]
    ) -> Dict[str, Any]:
        """
        Регистрирует нового пользователя.

        Args:
            username: Имя пользователя
            password: Пароль в открытом виде
            email: Email пользователя
            roles: Список ролей пользователя

        Returns:
            Словарь с данными зарегистрированного пользователя

        Raises:
            ValueError: Если пользователь с таким именем уже существует
        """
        try:
            # Проверяем, существует ли пользователь
            existing_user = await self.db_service.get_user_by_username(username)

            if existing_user:
                raise ValueError(f"User with username '{username}' already exists")

            # Создаем хеш пароля
            hashed_password = self.get_password_hash(password)

            # Создаем пользователя
            user_data = {
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
                "is_active": True,
                "roles": roles,
            }

            user = await self.db_service.create_user(user_data)

            # Записываем в аудит
            await self.db_service.add_audit_log(
                action="create",
                entity="user",
                entity_id=str(username),
                user_id="system",
                details="User registration",
            )

            return user
        except Exception as e:
            logger.error("Ошибка при регистрации пользователя %s: %s", username, str(e))
            raise
