"""
роутер для обработки платежей
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_cache.decorator import cache

from core.dtos.sale_response_dto import SaleResponseDTO
from core.dtos.sales import CreateSaleResponseDTO
from core.models import Currency, PaymentMethod, Sale, SaleItem, User
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
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    # warehouse_id: Optional[int] = None,
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
        sales = await services.get_sales_service().get_sales(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            start_date=start_date,
            end_date=end_date,
            # warehouse_id=warehouse_id,
        )

        return sales
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Ошибка при получении списка товаров: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=CreateSaleResponseDTO)
async def create_payment(
    items: List[SaleItem],
    currency: Currency = Currency.KZT,
    payment_method: PaymentMethod = PaymentMethod.CASH,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(get_current_active_user),
):
    """Создание продажи и чека"""
    try:
        order_id = await services.get_sales_service().create_sale(
            user_id=current_user.id, items=items, currency=currency, payment_method=payment_method
        )

        return {"order_id": order_id}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.post("/confirm")
async def confirm_payment(order_id: str, services: ServiceFactory = Depends(get_services)):
    """
    Подтверждает оплату и создаёт чек.
    """
    success = await services.get_sales_service().confirm_payment(order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось подтвердить оплату"
        )

    return {"order_id": order_id, "message": "Оплата подтверждена"}


@router.delete(
    "/cancel", status_code=status.HTTP_202_ACCEPTED, response_model=CreateSaleResponseDTO
)
async def cancel_sale(order_id: str, services: ServiceFactory = Depends(get_services)):
    """
    Отменяет продажу.
    """
    success = await services.get_sales_service().cancel_sale(order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Не удалось отменить продажу"
        )

    return {"order_id": order_id}


@router.get("/{order_id}", response_model=Sale)
async def get_sale_info(order_id: str, services: ServiceFactory = Depends(get_services)):
    """
    Получает информацию о продаже.
    """
    sale_info = await services.get_sales_service().get_sale_info(order_id)
    if not sale_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Продажа не найдена")

    return sale_info
