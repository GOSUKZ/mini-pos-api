import logging
from typing import Any, Dict, Optional

from .base import DatabaseService

logger = logging.getLogger("users_data_service")


class UsersDataService(DatabaseService):
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по имени пользователя.

        Args:
            username: Имя пользователя

        Returns:
            Словарь с данными пользователя или None, если пользователь не найден
        """
        query = "SELECT * FROM users WHERE username = $1"

        try:
            user = await self.fetch_one(query, username)

            if user:
                user_dict = dict(user)
                user_dict["roles"] = user_dict["roles"].split(",") if user_dict["roles"] else []
                return user_dict

            return None
        except Exception as e:
            logger.error("Ошибка при получении пользователя %s: %s", username, e)
            raise

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает нового пользователя.

        Args:
            user_data: Словарь с данными пользователя

        Returns:
            Словарь с данными созданного пользователя, включая ID
        """
        if "roles" in user_data and isinstance(user_data["roles"], list):
            user_data["roles"] = ",".join(user_data["roles"])

        fields = user_data.keys()
        placeholders = ", ".join(f"${i+1}" for i in range(len(fields)))
        fields_str = ", ".join(fields)

        query = f"INSERT INTO users ({fields_str}) VALUES ({placeholders}) RETURNING username"

        try:
            async with self.pool.acquire() as conn:
                username = await conn.fetchval(query, *user_data.values())

            return await self.get_user_by_username(username)
        except Exception as e:
            logger.error("Ошибка при создании пользователя: %s", e)
            raise

    async def update_user(
        self, username: str, user_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные пользователя.

        Args:
            username: Имя пользователя
            user_data: Словарь с обновляемыми данными пользователя

        Returns:
            Словарь с обновленными данными пользователя или None, если пользователь не найден
        """
        if not user_data:
            return await self.get_user_by_username(username)

        # Преобразуем список ролей в строку
        if "roles" in user_data and isinstance(user_data["roles"], list):
            user_data["roles"] = ",".join(user_data["roles"])

        set_parts = [f"{key} = ${i+1}" for i, key in enumerate(user_data.keys())]
        query = f"UPDATE users SET {', '.join(set_parts)} WHERE username = ${len(user_data) + 1} RETURNING username"

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(query, *user_data.values(), username)

            if not result:
                return None

            return await self.get_user_by_username(username)
        except Exception as e:
            logger.error("Ошибка при обновлении пользователя %s: %s", username, e)
            raise

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по email.

        Args:
            email: Email пользователя

        Returns:
            Словарь с данными пользователя или None, если пользователь не найден
        """
        try:
            user = await self.fetch_one("SELECT * FROM users WHERE email = $1", email)

            if user:
                user_dict = dict(user)
                user_dict["roles"] = user_dict["roles"].split(",") if user_dict["roles"] else []
                return user_dict

            return None
        except Exception as e:
            logger.error("Ошибка при получении пользователя по email %s: %s", email, e)
            raise
