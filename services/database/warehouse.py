import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import Warehouse, WarehouseCreate

from .base import DatabaseService

logger = logging.getLogger("warehouses_data_service")


class WarehousesDataService(DatabaseService):
    async def get_warehouses_count(self, user_id: int, search: Optional[str] = None) -> int:
        """
        Получает общее количество складов пользователя с учетом параметров фильтрации.

        Args:
            user_id: ID пользователя
            search: Строка поиска

        Returns:
            Общее количество складов
        """
        query_parts = ["SELECT COUNT(*) FROM warehouses WHERE user_id = $1"]
        params = [user_id]
        param_index = 1  # PostgreSQL использует $1, $2, $3...

        if search:
            query_parts.append(
                f"AND (name ILIKE ${param_index} OR location ILIKE ${param_index + 1})"
            )
            search_term = f"%{search}%"
            params.extend([search_term, search_term])
            param_index += 2

        query = " ".join(query_parts)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(query, *params)
            return result if result else 0
        except Exception as e:
            logger.error("Ошибка при получении количества складов: %s", e)
            raise

    async def get_warehouse_by_name(self, name: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает склад по имени.

        Args:
            name: Имя склада
            user_id: ID пользователя

        Returns:
            Словарь с данными склада или None, если склад не найден
        """
        try:
            return await self.fetch_one(
                "SELECT * FROM warehouses WHERE name = $1 AND user_id = $2", name, user_id
            )
        except Exception as e:
            logger.error("Ошибка при получении склада по имени %s: %s", name, str(e))

    async def create_warehouse(self, user_id: int, warehouse_data: WarehouseCreate) -> Warehouse:
        """
        Создает новый склад.

        Args:
            user_id: ID пользователя
            warehouse_data: Данные склада

        Returns:
            Объект склада

        Raises:
            Exception: Ошибка при создании склада
        """
        try:
            query = """
            INSERT INTO warehouses (user_id, name, location)
            VALUES ($1, $2, $3)
            RETURNING id, user_id, name, location
            """

            async with self.pool.acquire() as conn:
                logger.debug("Попытка создать склад")
                row = await conn.fetchrow(
                    query, user_id, warehouse_data.name, warehouse_data.location
                )
                logger.debug("Создан склад: %s", row)

                return Warehouse(**dict(row))
        except Exception as e:
            logger.error("Ошибка при создании склада: %s", e)
            raise

    async def get_warehouses(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> List[Warehouse]:
        """
        Получает список складов пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список объектов складов

        Raises:
            Exception: Ошибка при получении списка складов
        """

        try:
            query_parts = ["SELECT * FROM warehouses WHERE user_id = $1"]
            params = [user_id]
            param_index = 2  # PostgreSQL использует $1, $2, $3...

            if search:
                query_parts.append(
                    f"AND (name ILIKE ${param_index} OR location ILIKE ${param_index + 1})"
                )
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])
                param_index += 3

            valid_columns = [
                "id",
                "name",
                "location",
            ]

            if sort_by and sort_by in valid_columns:
                sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"
                query_parts.append(f"ORDER BY {sort_by} {sort_order}")
            else:
                query_parts.append("ORDER BY id ASC")

            query_parts.append(f"LIMIT ${param_index} OFFSET ${param_index + 1}")
            params.extend([limit, skip])

            query = " ".join(query_parts)

            return await self.fetch_all(query, *params)
        except Exception as e:
            logger.error("Ошибка при получении списка складов: %s", e)
            raise

    async def get_warehouse_by_id(self, warehouse_id: int) -> Warehouse:
        """
        Получает склад по ID и ID пользователя.

        Args:
            user_id: ID пользователя
            warehouse_id: ID склада

        Returns:
            Объект склада

        Raises:
            Exception: Ошибка при получении склада
        """
        try:
            return await self.fetch_one("SELECT * FROM warehouses WHERE id = $1", warehouse_id)
        except Exception as e:
            logger.error("Ошибка при получении склада: %s", e)
            raise

    async def update_warehouse(
        self, warehouse_id: int, warehouse_data: WarehouseCreate
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные склада.

        Args:
            warehouse_id: ID склада
            warehouse_data: Словарь с обновляемыми данными склада

        Returns:
            Словарь с обновленными данными склада или None, если склад не найден
        """
        if not warehouse_data:
            return await self.get_warehouse_by_id(warehouse_id)

        set_parts = []
        params = []

        warehouse_dict = warehouse_data.model_dump()

        for i, (key, value) in enumerate(warehouse_dict.items(), start=1):
            set_parts.append(f"{key} = ${i}")
            params.append(value)

        # Добавляем обновление `updated_at`
        params.append(datetime.utcnow())
        set_parts.append(f"updated_at = ${len(params)}")

        # Добавляем `warehouse_id` в параметры
        params.append(warehouse_id)
        query = (
            f"UPDATE warehouses SET {', '.join(set_parts)} WHERE id = ${len(params)} RETURNING *"
        )

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    row = await conn.fetchrow(
                        query, *params
                    )  # fetchrow() сразу возвращает обновленные данные

            return dict(row) if row else None
        except Exception as e:
            logger.error("Ошибка при обновлении склада с ID %s: %s", warehouse_id, e)
            raise

    async def delete_warehouse(self, warehouse_id: int) -> bool:
        """
        Удаляет склад.

        Args:
            warehouse_id: ID склада

        Returns:
            True, если склад успешно удален, иначе False
        """
        query = "DELETE FROM warehouses WHERE id = $1"

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(query, warehouse_id)

            return result.startswith("DELETE")  # asyncpg возвращает строку 'DELETE <количество>'
        except Exception as e:
            logger.error("Ошибка при удалении склада с ID %s: %s", warehouse_id, e)
            raise

    async def add_product_to_warehouse(
        self, warehouse_id: int, product_id: int, quantity: int
    ) -> bool:
        """
        Добавляет продукт в склад.

        Args:
            warehouse_id: ID склада
            product_id: ID продукта

        Returns:
            True, если продукт успешно добавлен, иначе False
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Проверяем, есть ли уже этот товар на складе
                    existing_quantity = await conn.fetchval(
                        """
                        SELECT quantity FROM warehouse_products 
                        WHERE warehouse_id = $1 AND product_id = $2
                        """,
                        warehouse_id,
                        product_id,
                    )

                    if existing_quantity is not None:
                        # Если товар уже есть, обновляем количество
                        await conn.execute(
                            """
                            UPDATE warehouse_products 
                            SET quantity = $1 
                            WHERE warehouse_id = $2 AND product_id = $3
                            """,
                            quantity,
                            warehouse_id,
                            product_id,
                        )
                    else:
                        # Если товара нет, создаем новую запись
                        await conn.execute(
                            """
                            INSERT INTO warehouse_products (warehouse_id, product_id, quantity) 
                            VALUES ($1, $2, $3)
                            """,
                            warehouse_id,
                            product_id,
                            quantity,
                        )

            logger.info(
                "Продукт %s успешно добавлен/обновлен на складе %s", product_id, warehouse_id
            )
            return True

        except Exception as e:
            logger.error("Ошибка при добавлении продукта в склад с ID %s: %s", warehouse_id, e)
            return False
