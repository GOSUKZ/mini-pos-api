"""
роутер для обработки платежей
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_cache.decorator import cache

from core.dtos.sale_response_dto import SaleResponseDTO
from core.models import Currency, PaymentMethod, SaleItem, User
from utils.dependencies import can_read_sales, get_current_active_user, get_services
from utils.service_factory import ServiceFactory

router = APIRouter(prefix="/sales", tags=["Sales"])


logger = logging.getLogger("sales_router")


@router.get("/", response_model=SaleResponseDTO)
@cache(namespace="sales")
async def read_sales(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    warehouse_id: Optional[int] = None,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_sales),
):
    """
    Получение списка заказов с фильтрацией и сортировкой.
    """
    logger.info(
        "Получение списка товаров пользователем %s, %s", current_user.username, current_user.id
    )

    try:
        sales = await services.get_sales(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            warehouse_id=warehouse_id,
        )

        return sales
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при получении списка товаров: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post("/create")
async def create_payment(
    items: List[SaleItem],
    currency: Currency = Currency.KZT,
    payment_method: PaymentMethod = PaymentMethod.CASH,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(get_current_active_user),
):
    """Создание продажи и чека"""
    try:
        order_id = await services.create_sale(
            user_id=current_user.id, items=items, currency=currency, payment_method=payment_method
        )

        return {"order_id": order_id, "message": "Продажа успешно создана"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post("/confirm")
async def confirm_payment(order_id: str, services: ServiceFactory = Depends(get_services)):
    """
    Подтверждает оплату и создаёт чек.
    """
    success = await services.confirm_payment(order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось подтвердить оплату"
        )

    return {"order_id": order_id, "message": "Оплата подтверждена"}


@router.post("/cancel")
async def cancel_sale(order_id: str, services: ServiceFactory = Depends(get_services)):
    """
    Отменяет продажу.
    """
    success = await services.cancel_sale(order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось отменить продажу"
        )

    return {"order_id": order_id, "message": "Продажа отменена"}


@router.get("/{order_id}")
async def get_sale_info(order_id: str, services: ServiceFactory = Depends(get_services)):
    """
    Получает информацию о продаже.
    """
    sale_info = await services.get_sale_info(order_id)
    if not sale_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Продажа не найдена")

    return sale_info
