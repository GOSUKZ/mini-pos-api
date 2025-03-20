import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import SaleItem

from .base import DatabaseService

logger = logging.getLogger("sales_data_service")


class SalesDataService(DatabaseService):
    async def generate_order_id(self) -> str:
        """Генерирует уникальный order_id с инкрементом и префиксом ORD-."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                last_number = await conn.fetchval(
                    "UPDATE order_counter SET last_number = last_number + 1 RETURNING last_number"
                )
                return f"ORD-{last_number}"

    async def create_sale(
        self, user_id: int, items: List[SaleItem], currency: str, payment_method: str
    ) -> str:
        """Создание продажу и возвращает order_id"""
        try:
            order_id = await self.generate_order_id()
            total_amount = sum(item.price * item.quantity for item in items)

            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """INSERT INTO sales (order_id, user_id, total_amount, currency, status) VALUES ($1, $2, $3, $4, $5)""",
                        order_id,
                        user_id,
                        total_amount,
                        currency,
                        "pending",
                    )

                    for item in items:
                        await conn.execute(
                            """INSERT INTO sales_items (sale_id, product_id, quantity, price, cost_price, total) VALUES ((SELECT id FROM sales WHERE order_id = $1), $2, $3, $4, $5, $6)""",
                            order_id,
                            item.product_id,
                            item.quantity,
                            item.price,
                            item.cost_price,
                            item.price * item.quantity,
                        )

                    await conn.execute(
                        """INSERT INTO receipts (order_id, user_id, total_amount, payment_method) VALUES ($1, $2, $3, $4)""",
                        order_id,
                        user_id,
                        total_amount,
                        payment_method,
                    )

            return order_id
        except Exception as e:
            logger.error("Ошибка при создании записи о продаже %s: %s", order_id, str(e))
            return False

    async def update_sale_status(self, order_id: str, status: str) -> bool:
        """Обновляет статус продажи"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    "UPDATE sales SET status = $1 WHERE order_id = $2", status, order_id
                )
            return result == "UPDATE 1"
        except Exception as e:
            logger.error("Ошибка при обновлении статуса продажи %s: %s", order_id, str(e))
            return False

    async def cancel_sale(self, order_id: str) -> bool:
        """Отменяет продажу"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute("DELETE FROM sales WHERE order_id = $1", order_id)
            return result == "DELETE 1"
        except Exception as e:
            logger.error("Ошибка при отмене продажи %s: %s", order_id, str(e))
            return False

    async def get_sale_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Получает детали заказа и товаров в нём, включая sku_name."""
        async with self.pool.acquire() as conn:
            sale = await conn.fetchrow("SELECT * FROM sales WHERE order_id = $1", order_id)

            if not sale:
                return None

            query = """
                SELECT si.*, p.sku_name
                FROM sales_items si
                LEFT JOIN local_products p ON si.product_id = p.id
                WHERE si.sale_id = $1
            """
            items = await conn.fetch(query, sale["id"])

            return {
                "order_id": sale["order_id"],
                "user_id": sale["user_id"],
                "total_amount": sale["total_amount"],
                "currency": sale["currency"],
                "status": sale["status"],
                "created_at": sale["created_at"],
                "updated_at": sale["updated_at"],
                "items": [dict(item) for item in items],  # Теперь в каждом товаре есть sku_name
            }

    async def get_sales_count(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> int:
        """
        Получает общее количество продаж пользователя с учетом фильтрации.

        Args:
            user_id: ID пользователя
            search: Строка поиска, используется для фильтрации по идентификатору заказа

        Returns:
            Общее количество продаж
        """

        query_parts = ["SELECT COUNT(*) FROM sales WHERE user_id = $1"]
        params = [user_id]
        param_index = 2  # PostgreSQL использует $1, $2, $3...

        if search:
            query_parts.append(f"AND (order_id ILIKE ${param_index})")
            search_term = f"%{search}%"
            params.append(search_term)
            param_index += 1

        if start_date:
            query_parts.append(f"AND created_at >= ${param_index}::timestamp")
            params.append(start_date.replace(tzinfo=None))  # Убираем таймзону
            param_index += 1

        if end_date:
            query_parts.append(f"AND created_at <= ${param_index}::timestamp")
            params.append(end_date.replace(tzinfo=None))  # Убираем таймзону
            param_index += 1

        # if warehouse_id is not None:
        #     query_parts.append(
        #         f"""AND id IN (SELECT product_id FROM sales_items WHERE warehouse_id = ${param_index})"""
        #     )
        #     params.append(warehouse_id)
        #     param_index += 1

        query = " ".join(query_parts)

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(query, *params)
            return result if result else 0
        except Exception as e:
            logger.error("Ошибка при получении количества товаров: %s", e)
            raise

    async def get_sales(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        # warehouse_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получает список продаж пользователя с учетом параметров фильтрации и сортировки.

        Args:
            user_id: ID пользователя
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            search: Строка поиска
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)

        Returns:
            Список словарей с данными продаж
        """
        query_parts = ["SELECT * FROM sales WHERE user_id = $1"]
        params = [user_id]
        param_index = 2  # PostgreSQL использует $1, $2, $3...

        if search:
            query_parts.append(f"AND (order_id ILIKE ${param_index})")
            search_term = f"%{search}%"
            params.append(search_term)
            param_index += 1

        if start_date:
            query_parts.append(f"AND created_at >= ${param_index}::timestamp")
            params.append(start_date.replace(tzinfo=None))  # Убираем таймзону
            param_index += 1

        if end_date:
            query_parts.append(f"AND created_at <= ${param_index}::timestamp")
            params.append(end_date.replace(tzinfo=None))  # Убираем таймзону
            param_index += 1

        # if warehouse_id is not None:
        #     query_parts.append(
        #         f"""AND id IN (SELECT product_id FROM sales_items WHERE warehouse_id = ${param_index})"""
        #     )
        #     params.append(warehouse_id)
        #     param_index += 1

        valid_columns = ["id", "order_id", "total_amount", "currency", "status", "created_at"]

        if sort_by and sort_by in valid_columns:
            sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"
            query_parts.append(f"ORDER BY {sort_by} {sort_order}")
        else:
            query_parts.append("ORDER BY id ASC")

        query_parts.append(f"LIMIT ${param_index} OFFSET ${param_index + 1}")
        params.extend([limit, skip])

        query = " ".join(query_parts)

        try:
            sales = await self.fetch_all(query, *params)

            order_ids = [sale["order_id"] for sale in sales]

            if not order_ids:
                return sales

            async with self.pool.acquire() as conn:
                items_query = """
                    SELECT si.*, p.sku_name 
                    FROM sales_items si
                    JOIN local_products p ON si.product_id = p.id
                    WHERE si.sale_id IN (SELECT id FROM sales WHERE order_id = ANY($1))
                """
                item_rows = await conn.fetch(items_query, order_ids)
                items = [dict(row) for row in item_rows]

                items_map = {}
                for item in items:
                    sale_id = item["sale_id"]
                    if sale_id not in items_map:
                        items_map[sale_id] = []
                    items_map[sale_id].append(item)

                for sale in sales:
                    sale["items"] = items_map.get(sale["id"], [])

            return sales
        except Exception as e:
            logger.error("Ошибка при получении списка товаров: %s", e)
            raise
