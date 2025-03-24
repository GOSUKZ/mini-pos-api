"""
Модуль сервиса продаж
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models import OrderStatus, SaleItem
from services.database.sales import SalesDataService

logger = logging.getLogger("sales_service")


class SalesService:
    """
    Сервис продаж
    """

    def __init__(self, db_service: SalesDataService):
        """
        Инициализирует сервис с сервисом базы данных.

        Args:
            db_service: Сервис базы данных
        """
        self.db_service = db_service

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
    ) -> Dict[str, Any]:
        try:
            total_count = await self.db_service.get_sales_count(
                user_id=user_id,
                search=search,
                start_date=start_date,
                end_date=end_date,
                # warehouse_id=warehouse_id
            )

            sales = await self.db_service.get_sales(
                user_id=user_id,
                skip=skip,
                limit=limit,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
                start_date=start_date,
                end_date=end_date,
                # warehouse_id=warehouse_id,
            )

            current_page = (skip // limit) + 1 if limit > 0 else 1
            total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
            is_last = current_page >= total_pages

            response = {
                "total_count": total_count,
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "skip": skip,
                "is_last": is_last,
                "content": sales,
            }

            return response

        except Exception as e:
            logger.error("Ошибка при получении списка товаров: %s", str(e))
            raise

    async def create_sale(
        self,
        user_id: int,
        items: List[SaleItem],
        currency: str,
        payment_method: str,
        status: OrderStatus,
    ) -> str:
        """Создание продажи и чека"""
        try:
            order_id = await self.db_service.create_sale(
                currency=currency,
                items=items,
                payment_method=payment_method,
                user_id=user_id,
                status=status,
            )
            return order_id
        except Exception as e:
            logger.error("Ошибка при создании продажи: %s", str(e))
            raise

    async def change_status(self, order_id: str, status: OrderStatus) -> bool:
        """
        Изменяет статус продажи на status
        """
        try:
            await self.db_service.update_sale_status(order_id, status.value)
            return True
        except Exception as e:
            logger.error("Ошибка при изменении статуса продажи: %s", str(e))
            raise

    async def confirm_payment(self, order_id: str) -> bool:
        """
        Подтверждает оплату, обновляет статус и создаёт чек, если он ещё не был создан.
        """
        sale_details = await self.db_service.get_sale_details(order_id)
        if not sale_details:
            return False

        if sale_details["status"] == "paid":
            return True  # Уже оплачен

        success = await self.db_service.update_sale_status(order_id, "paid")

        return success

    async def cancel_sale(self, order_id: str) -> bool:
        """
        Отмена продажи, обновляет статус на "cancelled".
        """
        success = await self.db_service.cancel_sale(order_id)

        return success

    async def get_sale_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает детали заказа.
        """
        return await self.db_service.get_sale_details(order_id)

    async def get_sales_analytics(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        try:
            return await self.db_service.get_sales_analytics(user_id, start_date, end_date)
        except Exception as e:
            logger.error("Ошибка при получении аналитики: %s", str(e))
            raise
