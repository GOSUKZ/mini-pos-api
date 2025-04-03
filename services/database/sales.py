import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import OrderStatus, SaleItem

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
        self,
        user_id: int,
        items: List[SaleItem],
        currency: str,
        payment_method: str,
        status: OrderStatus,
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
                        status.value,
                    )

                    for item in items:
                        await conn.execute(
                            """INSERT INTO sales_items (sale_id, product_id, quantity, price, cost_price, total, product_name, barcode) VALUES ((SELECT id FROM sales WHERE order_id = $1), $2, $3, $4, $5, $6, $7, $8)""",
                            order_id,
                            item.product_id,
                            item.quantity,
                            item.price,
                            item.cost_price,
                            item.price * item.quantity,
                            item.product_name,
                            item.barcode,
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

    async def update_sale_status(self, order_id: str, status: OrderStatus) -> bool:
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
                    SELECT si.*, 
                        COALESCE(p.sku_name, si.product_name) AS product_name, 
                        COALESCE(p.barcode, si.barcode) AS barcode
                    FROM sales_items si
                    LEFT JOIN local_products p ON si.product_id = p.id
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

    async def get_sales_analytics(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        try:
            query = """
                WITH
                    sales_summary AS (
                        SELECT
                            COUNT(*) AS total_sales_count,
                            COALESCE(SUM(total_amount), 0) AS total_sales_sum,
                            COUNT(*) FILTER (WHERE created_at >= NOW()::DATE) AS sales_today
                        FROM sales
                        WHERE user_id = $1
                            AND created_at BETWEEN $2 AND $3
                    ),
                    paid_unpaid_summary AS (
                        SELECT
                            COALESCE(SUM(CASE WHEN status = 'paid' THEN total_amount ELSE 0 END), 0) AS total_paid_sum,
                            COALESCE(SUM(CASE WHEN status = 'unpaid' THEN total_amount ELSE 0 END), 0) AS total_unpaid_sum
                        FROM sales
                        WHERE user_id = $1
                            AND created_at BETWEEN $2 AND $3
                    ),
                    latest_orders_base AS ( -- Базовый CTE для последних заказов
                        SELECT
                            order_id, status, total_amount, created_at
                        FROM sales
                        WHERE user_id = $1
                            AND created_at BETWEEN $2 AND $3
                        ORDER BY created_at DESC
                        LIMIT 5
                    ),
                    top_products_base AS ( -- Базовый CTE для топ продуктов
                        SELECT
                            si.product_id,
                            lp.sku_name AS product_name,
                            lp.price AS product_price,
                            SUM(si.quantity) AS total_sold
                        FROM sales_items si
                        JOIN local_products lp ON si.product_id = lp.id
                        JOIN sales s ON si.sale_id = s.id
                        WHERE s.user_id = $1
                            AND s.created_at BETWEEN $2 AND $3
                        GROUP BY si.product_id, lp.sku_name, lp.price
                        ORDER BY total_sold DESC
                        LIMIT 5
                    ),
                    avg_invoice AS (
                        SELECT
                            COALESCE(AVG(total_amount), 0) AS average_invoice
                        FROM sales
                        WHERE user_id = $1
                            AND created_at BETWEEN $2 AND $3
                    ),
                    profit_calc AS (
                        SELECT
                            COALESCE(SUM(si.price * si.quantity) - SUM(si.cost_price * si.quantity), 0) AS profit
                        FROM sales_items si
                        JOIN sales s ON si.sale_id = s.id
                        WHERE s.user_id = $1
                            AND s.created_at BETWEEN $2 AND $3
                    )
                SELECT
                    ss.total_sales_count,
                    ss.total_sales_sum,
                    ss.sales_today,
                    pus.total_paid_sum,
                    ROUND(COALESCE((pus.total_paid_sum / NULLIF(ss.total_sales_sum, 0)) * 100, 0), 2) AS paid_percentage,
                    pus.total_unpaid_sum,
                    ROUND(COALESCE((pus.total_unpaid_sum / NULLIF(ss.total_sales_sum, 0)) * 100, 0), 2) AS unpaid_percentage,
                    ai.average_invoice,
                    pc.profit,
                    -- Скалярный подзапрос для latest_orders с явной сортировкой внутри jsonb_agg
                    (SELECT COALESCE(jsonb_agg(lo ORDER BY lo.created_at DESC), '[]'::jsonb)
                    FROM latest_orders_base lo
                    ) AS latest_orders,
                    -- Скалярный подзапрос для top_products с явной сортировкой внутри jsonb_agg
                    (SELECT COALESCE(jsonb_agg(tp ORDER BY tp.total_sold DESC), '[]'::jsonb)
                    FROM top_products_base tp
                    ) AS top_products
                FROM sales_summary ss
                -- Используем CROSS JOIN, так как все эти CTE возвращают ровно одну строку
                CROSS JOIN paid_unpaid_summary pus
                CROSS JOIN avg_invoice ai
                CROSS JOIN profit_calc pc;
            """
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, user_id, start_date, end_date)
                return dict(row)
        except Exception as e:
            logger.error("Ошибка при получении аналитики: %s", e)
            raise
