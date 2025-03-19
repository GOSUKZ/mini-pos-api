"""
роутер для обработки платежей
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from core.models import Currency, PaymentMethod, SaleItem
from services.sales_service import SalesService
from utils.dependencies import get_current_active_user, get_sales_service

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post("/create")
async def create_payment(
    items: List[SaleItem],
    currency: Currency = Currency.KZT,
    payment_method: PaymentMethod = PaymentMethod.CASH,
    sales_service: SalesService = Depends(get_sales_service),
    current_user=Depends(get_current_active_user),
):
    """Создание продажи и чека"""
    try:
        order_id = await sales_service.create_sale(
            user_id=current_user.id, items=items, currency=currency, payment_method=payment_method
        )

        return {"order_id": order_id, "message": "Продажа успешно создана"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm")
async def confirm_payment(order_id: str, sales_service: SalesService = Depends(get_sales_service)):
    """
    Подтверждает оплату и создаёт чек.
    """
    success = await sales_service.confirm_payment(order_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось подтвердить оплату")

    return {"order_id": order_id, "message": "Оплата подтверждена"}


@router.post("/cancel")
async def cancel_sale(order_id: str, sales_service: SalesService = Depends(get_sales_service)):
    """
    Отменяет продажу.
    """
    success = await sales_service.cancel_sale(order_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось отменить продажу")

    return {"order_id": order_id, "message": "Продажа отменена"}


@router.get("/{order_id}")
async def get_sale_info(order_id: str, sales_service: SalesService = Depends(get_sales_service)):
    """
    Получает информацию о продаже.
    """
    sale_info = await sales_service.get_sale_info(order_id)
    if not sale_info:
        raise HTTPException(status_code=404, detail="Продажа не найдена")

    return sale_info
