"""
Module for working with products in the database.

This module provides a service for working with products in the database.
The service provides methods for creating, reading, updating and deleting products.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import DatabaseService

logger = logging.getLogger("products_data_service")


class ProductsDataService(DatabaseService):
    async def get_products(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        department: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получает список товаров с учетом параметров фильтрации и сортировки.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            search: Строка поиска
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            department: Фильтр по отделу
            min_price: Минимальная цена
            max_price: Максимальная цена

        Returns:
            Список словарей с данными товаров
        """
        query_parts = ["SELECT * FROM products WHERE TRUE"]
        params = []
        param_index = 1  # PostgreSQL использует $1, $2...

        if search:
            query_parts.append(
                f"AND (sku_name ILIKE ${param_index} OR sku_code ILIKE ${param_index + 1} OR barcode ILIKE ${param_index + 2})"
            )
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
            param_index += 3

        if department:
            query_parts.append(f"AND department = ${param_index}")
            params.append(department)
            param_index += 1

        if min_price is not None:
            query_parts.append(f"AND price >= ${param_index}")
            params.append(min_price)
            param_index += 1

        if max_price is not None:
            query_parts.append(f"AND price <= ${param_index}")
            params.append(max_price)
            param_index += 1

        valid_columns = [
            "id",
            "sku_code",
            "sku_name",
            "barcode",
            "price",
            "cost_price",
            "supplier",
            "department",
        ]

        if sort_by and sort_by in valid_columns:
            sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"
            query_parts.append(f"ORDER BY {sort_by} {sort_order}")
        else:
            query_parts.append("ORDER BY id ASC")

        query_parts.append(f"LIMIT ${param_index} OFFSET ${param_index + 1}")
        params.extend([limit, skip])

        query = " ".join(query_parts)

        logger.info("Query: %s", query)

        try:
            return await self.fetch_all(query, *params)
        except Exception as e:
            logger.error("Ошибка при получении списка товаров: %s", e)
            raise

    async def get_all_local_products(
        self, user_id: int, sort_by: Optional[str] = None, sort_order: str = "asc"
    ) -> List[Dict[str, Any]]:
        """
        Получает все локальные продукты пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Список словарей с данными локальных продуктов
        """
        query_parts = ["SELECT * FROM local_products WHERE user_id = $1"]
        params = [user_id]

        valid_columns = [
            "id",
            "sku_code",
            "sku_name",
            "price",
            "barcode",
            "cost_price",
            "quantity",
            "created_at",
        ]

        if sort_by and sort_by in valid_columns:
            sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"
            query_parts.append(f"ORDER BY {sort_by} {sort_order}")
        else:
            query_parts.append("ORDER BY id ASC")

        query = " ".join(query_parts)

        logger.info("Query: %s", query)

        try:
            return await self.fetch_all(query, *params)
        except Exception as e:
            logger.error("Ошибка при получении локальных продуктов: %s", e)
            raise

    async def get_local_products(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        department: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        warehouse_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получает список локальных товаров пользователя с фильтрами и сортировкой.

        Args:
            user_id: ID пользователя
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            search: Строка поиска
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            department: Фильтр по отделу
            min_price: Минимальная цена
            max_price: Максимальная цена

        Returns:
            Список словарей с данными товаров
        """
        query_parts = ["SELECT * FROM local_products WHERE user_id = $1"]
        params = [user_id]
        param_index = 2  # PostgreSQL использует $1, $2, $3...

        if search:
            query_parts.append(
                f"AND (sku_name ILIKE ${param_index} OR sku_code ILIKE ${param_index + 1} OR barcode ILIKE ${param_index + 2})"
            )
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
            param_index += 3

        if department:
            query_parts.append(f"AND department = ${param_index}")
            params.append(department)
            param_index += 1

        if min_price is not None:
            query_parts.append(f"AND price >= ${param_index}")
            params.append(min_price)
            param_index += 1

        if max_price is not None:
            query_parts.append(f"AND price <= ${param_index}")
            params.append(max_price)
            param_index += 1

        if warehouse_id is not None:
            query_parts.append(
                f"""AND id IN (SELECT product_id FROM warehouse_products WHERE warehouse_id = ${param_index})"""
            )
            params.append(warehouse_id)
            param_index += 1

        valid_columns = [
            "id",
            "sku_code",
            "sku_name",
            "barcode",
            "price",
            "cost_price",
            "supplier",
            "department",
        ]

        if sort_by and sort_by in valid_columns:
            sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"
            query_parts.append(f"ORDER BY {sort_by} {sort_order}")
        else:
            query_parts.append("ORDER BY id ASC")

        query_parts.append(f"LIMIT ${param_index} OFFSET ${param_index + 1}")
        params.extend([limit, skip])

        query = " ".join(query_parts)

        try:
            return await self.fetch_all(query, *params)
        except Exception as e:
            logger.error("Ошибка при получении списка товаров: %s", e)
            raise

    async def get_products_count(
        self,
        search: Optional[str] = None,
        department: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> int:
        """
        Получает общее количество товаров с учетом фильтрации.

        Args:
            search: Строка поиска
            department: Фильтр по отделу
            min_price: Минимальная цена
            max_price: Максимальная цена

        Returns:
            Общее количество товаров
        """
        query_parts = ["SELECT COUNT(*) FROM products WHERE 1=1"]
        params = []
        param_index = 1  # PostgreSQL использует $1, $2, $3...

        if search:
            query_parts.append(
                f"AND (sku_name ILIKE ${param_index} OR sku_code ILIKE ${param_index + 1} OR barcode ILIKE ${param_index + 2})"
            )
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
            param_index += 3

        if department:
            query_parts.append(f"AND department = ${param_index}")
            params.append(department)
            param_index += 1

        if min_price is not None:
            query_parts.append(f"AND price >= ${param_index}")
            params.append(min_price)
            param_index += 1

        if max_price is not None:
            query_parts.append(f"AND price <= ${param_index}")
            params.append(max_price)
            param_index += 1

        query = " ".join(query_parts)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(query, *params)
            return result if result else 0
        except Exception as e:
            logger.error("Ошибка при получении количества товаров: %s", e)
            raise

    async def get_local_products_count(
        self,
        user_id: int,
        search: Optional[str] = None,
        department: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        warehouse_id: Optional[int] = None,
    ) -> int:
        """
        Получает общее количество товаров пользователя с учетом фильтрации.

        Args:
            user_id: ID пользователя
            search: Строка поиска
            department: Фильтр по отделу
            min_price: Минимальная цена
            max_price: Максимальная цена

        Returns:
            Общее количество товаров
        """
        query_parts = ["SELECT COUNT(*) FROM local_products WHERE user_id = $1"]
        params = [user_id]
        param_index = 2  # PostgreSQL использует $1, $2, $3...

        if search:
            query_parts.append(
                f"AND (sku_name ILIKE ${param_index} OR sku_code ILIKE ${param_index + 1} OR barcode ILIKE ${param_index + 2})"
            )
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])
            param_index += 3

        if department:
            query_parts.append(f"AND department = ${param_index}")
            params.append(department)
            param_index += 1

        if min_price is not None:
            query_parts.append(f"AND price >= ${param_index}")
            params.append(min_price)
            param_index += 1

        if max_price is not None:
            query_parts.append(f"AND price <= ${param_index}")
            params.append(max_price)
            param_index += 1

        if warehouse_id is not None:
            query_parts.append(
                f"""AND id IN (SELECT product_id FROM warehouse_products WHERE warehouse_id = ${param_index})"""
            )
            params.append(warehouse_id)
            param_index += 1

        query = " ".join(query_parts)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(query, *params)
            return result if result else 0
        except Exception as e:
            logger.error("Ошибка при получении количества товаров: %s", e)
            raise

    async def get_product_by_barcode(self, barcode: str, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение товара по штрих-коду.

        Args:
            barcode: Штрих-код товара

        Returns:
            Информация о товаре или None, если товар не найден
        """
        try:
            local_product = await self.fetch_one(
                "SELECT * FROM local_products WHERE barcode = $1 AND user_id = $2", barcode, user_id
            )

            if local_product:
                return local_product

            product = await self.fetch_one("SELECT * FROM products WHERE barcode = $1", barcode)

            if not product:
                return None

            return product
        except Exception as e:
            logger.error("Ошибка при получении товара по штрих-коду из БД: %s", str(e))
            raise

    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает товар по ID.

        Args:
            product_id: ID товара

        Returns:
            Словарь с данными товара или None, если товар не найден
        """
        try:
            return await self.fetch_one("SELECT * FROM products WHERE id = $1", product_id)
        except Exception as e:
            logger.error("Ошибка при получении товара по ID %s: %s", product_id, str(e))
            raise

    async def get_local_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает товар по ID.

        Args:
            product_id: ID товара

        Returns:
            Словарь с данными товара или None, если товар не найден
        """
        try:
            return await self.fetch_one("SELECT * FROM local_products WHERE id = $1", product_id)
        except Exception as e:
            logger.error("Ошибка при получении товара по ID %s: %s", product_id, str(e))
            raise

    async def get_product_by_sku(self, sku_code: str) -> Optional[Dict[str, Any]]:
        """
        Получает товар по SKU коду.

        Args:
            sku_code: SKU код товара

        Returns:
            Словарь с данными товара или None, если товар не найден
        """
        try:
            return await self.fetch_one("SELECT * FROM products WHERE sku_code = $1", sku_code)
        except Exception as e:
            logger.error("Ошибка при получении товара по SKU %s: %s", sku_code, str(e))
            raise

    async def get_local_product_by_barcode(
        self, barcode: str, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Получает товар по BARCODE коду.

        Args:
            barcode: BARCODE код товара

        Returns:
            Словарь с данными товара или None, если товар не найден
        """
        try:
            return await self.fetch_one(
                "SELECT * FROM local_products WHERE user_id = $1 AND barcode = $2",
                user_id,
                barcode,
            )
        except Exception as e:
            logger.error("Ошибка при получении товара по BARCODE %s: %s", barcode, str(e))
            raise

    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новый товар.

        Args:
            product_data: Словарь с данными товара

        Returns:
            Словарь с данными созданного товара, включая ID
        """
        fields = product_data.keys()
        placeholders = ", ".join([f"${i+1}" for i in range(len(fields))])  # Используем $1, $2, ...
        fields_str = ", ".join(fields)

        try:
            return await self.fetch_one(
                f"INSERT INTO products ({fields_str}) VALUES ({placeholders}) RETURNING *",
                *product_data.values(),
            )
        except Exception as e:
            logger.error("Ошибка при создании товара: %s", str(e))
            raise

    async def create_local_product(
        self, product_data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """
        Создает новый локальный товар.

        Args:
            product_data: Словарь с данными товара
            user_id: ID пользователя

        Returns:
            Словарь с данными созданного товара, включая ID
        """
        product_data["user_id"] = user_id
        fields = list(product_data.keys())
        placeholders = ", ".join([f"${i+1}" for i in range(len(fields))])  # Используем $1, $2, ...
        fields_str = ", ".join(fields)

        query = f"""
            INSERT INTO local_products ({fields_str})
            VALUES ({placeholders})
            RETURNING *
        """

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():  # Используем транзакцию
                    row = await conn.fetchrow(
                        query, *product_data.values()
                    )  # fetchrow() сразу возвращает данные

            return dict(row) if row else None
        except Exception as e:
            logger.error("Ошибка при создании локального товара: %s", str(e))
            raise

    async def update_product(
        self, product_id: int, product_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные товара.

        Args:
            product_id: ID товара
            product_data: Словарь с обновляемыми данными товара

        Returns:
            Словарь с обновленными данными товара или None, если товар не найден
        """
        if not product_data:
            return await self.get_product_by_id(product_id)

        set_parts = []
        params = []

        for i, (key, value) in enumerate(product_data.items(), start=1):
            set_parts.append(f"{key} = ${i}")
            params.append(value)

        params.append(product_id)
        query = f"UPDATE products SET {', '.join(set_parts)} WHERE id = ${len(params)} RETURNING *"

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    row = await conn.fetchrow(
                        query, *params
                    )  # fetchrow() сразу возвращает обновленные данные

            return dict(row) if row else None
        except Exception as e:
            logger.error("Ошибка при обновлении товара с ID %s: %s", product_id, str(e))
            raise

    async def update_local_product(
        self, product_id: int, product_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные локального товара.

        Args:
            product_id: ID товара
            product_data: Словарь с обновляемыми данными товара

        Returns:
            Словарь с обновленными данными товара или None, если товар не найден
        """
        if not product_data:
            return await self.get_local_product_by_id(product_id)

        set_parts = []
        params = []

        for i, (key, value) in enumerate(product_data.items(), start=1):
            set_parts.append(f"{key} = ${i}")
            params.append(value)

        params.append(product_id)
        query = f"UPDATE local_products SET {', '.join(set_parts)} WHERE id = ${len(params)} RETURNING *"

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    row = await conn.fetchrow(
                        query, *params
                    )  # fetchrow() сразу возвращает обновленные данные

            return dict(row) if row else None
        except Exception as e:
            logger.error("Ошибка при обновлении локального товара с ID %s: %s", product_id, e)
            raise

    async def delete_product(self, product_id: int) -> bool:
        """
        Удаляет товар.

        Args:
            product_id: ID товара

        Returns:
            True, если товар успешно удален, иначе False
        """
        query = "DELETE FROM products WHERE id = $1"

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(query, product_id)

            return result.startswith("DELETE")  # asyncpg возвращает строку 'DELETE <количество>'
        except Exception as e:
            logger.error("Ошибка при удалении товара с ID %s: %s", product_id, e)
            raise

    async def delete_local_product(self, product_id: int) -> bool:
        """
        Удаляет локальный товар.

        Args:
            product_id: ID товара

        Returns:
            True, если товар успешно удален, иначе False
        """
        query = "DELETE FROM local_products WHERE id = $1"

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(query, product_id)

            return result.startswith("DELETE")  # asyncpg возвращает строку 'DELETE <количество>'
        except Exception as e:
            logger.error("Ошибка при удалении локального товара с ID %s: %s", product_id, e)
            raise
