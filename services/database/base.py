import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import asyncpg

logger = logging.getLogger("database_service")


class DatabaseService:
    def __init__(self, db_pool: Optional[asyncpg.Pool]):
        if db_pool is None:
            raise ValueError("db_pool не инициализирован!")
        self.pool = db_pool

    async def fetch_one(self, query: str, *params) -> Optional[Dict[str, Any]]:
        """
        Выполняет запрос к БД, возвращая только одну строку.

        Args:
            query: SQL-запрос
            *params: Параметры для запроса

        Returns:
            Словарь с полученными данными, если строка найдена, иначе None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            return dict(row) if row else None

    async def fetch_all(self, query: str, *params) -> List[Dict[str, Any]]:
        """
        Выполняет запрос к БД, возвращая все найденные строки.

        Args:
            query: SQL-запрос
            *params: Параметры для запроса

        Returns:
            Список словарей с данными всех найденных строк
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def execute(self, query: str, *params) -> None:
        """
        Выполняет запрос к БД, не возвращая результат.

        Args:
            query: SQL-запрос
            *params: Параметры для запроса
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, *params)

    async def add_audit_log(
        self, action: str, entity: str, entity_id: str, user_id: int, details: str = ""
    ) -> int:
        """
        Добавляет запись в лог аудита.

        Args:
            action: Тип действия (create, update, delete, read)
            entity: Тип сущности (product, user)
            entity_id: ID сущности
            user_id: ID пользователя
            details: Дополнительные детали

        Returns:
            ID созданной записи
        """
        query = """
        INSERT INTO audit_log (action, entity, entity_id, user_id, timestamp, details)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.fetchval(
                        query, action, entity, entity_id, user_id, datetime.utcnow(), details
                    )

            return result
        except Exception as e:
            logger.error("Ошибка при добавлении записи в аудит: %s", e)
            raise

    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        entity: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получает записи из лога аудита с учетом параметров фильтрации.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            entity: Фильтр по типу сущности
            action: Фильтр по типу действия
            user_id: Фильтр по ID пользователя
            from_date: Фильтр по начальной дате
            to_date: Фильтр по конечной дате

        Returns:
            Список словарей с данными записей аудита
        """
        query_parts = ["SELECT * FROM audit_log WHERE 1=1"]
        params = []

        if entity:
            query_parts.append("AND entity = $1")
            params.append(entity)

        if action:
            query_parts.append(f"AND action = ${len(params) + 1}")
            params.append(action)

        if user_id:
            query_parts.append(f"AND user_id = ${len(params) + 1}")
            params.append(user_id)

        if from_date:
            query_parts.append(f"AND timestamp >= ${len(params) + 1}")
            params.append(from_date)

        if to_date:
            query_parts.append(f"AND timestamp <= ${len(params) + 1}")
            params.append(to_date)

        query_parts.append(
            f"ORDER BY timestamp DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        )
        params.extend([limit, skip])

        query = " ".join(query_parts)

        try:
            return await self.fetch_all(query, *params)
        except Exception as e:
            logger.error("Ошибка при получении записей аудита: %s", e)
            raise
