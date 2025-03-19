"""
Модуль сервиса продаж
"""

import logging
from typing import Any, Dict, List, Optional

from core.database import DatabaseService
from core.models import SaleItem

logger = logging.getLogger("sales_service")


class SalesService:
    """
    Сервис продаж
    """

    def __init__(self, db_service: DatabaseService):
        """
        Инициализирует сервис с сервисом базы данных.

        Args:
            db_service: Сервис базы данных
        """
        self.db_service = db_service

    async def create_sale(
        self, user_id: int, items: List[SaleItem], currency: str, payment_method: str
    ) -> str:
        """Создание продажи и чека"""
        try:
            order_id = await self.db_service.create_sale(
                currency=currency, items=items, payment_method=payment_method, user_id=user_id
            )
            return order_id
        except Exception as e:
            logger.error("Ошибка при создании продажи: %s", str(e))
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
        sale_details = await self.db_service.get_sale_details(order_id)
        if not sale_details or sale_details["status"] in ["paid", "cancelled"]:
            return False  # Нельзя отменить уже оплаченное или отменённое

        success = await self.db_service.update_sale_status(order_id, "cancelled")

        return success

    async def get_sale_info(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает детали заказа.
        """
        return await self.db_service.get_sale_details(order_id)
