"""
This module contains the router for the global products.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi_cache.decorator import cache

from core.dtos.product_response_dto import ProductResponseDTO
from core.models import Product, ProductCreate, ProductUpdate, User
from utils.dependencies import get_current_active_user, get_services, has_role
from utils.service_factory import ServiceFactory

logger = logging.getLogger("product_router")

# Создаем роутер
router = APIRouter(
    prefix="/products/global",
    tags=["Global products"],
    responses={404: {"description": "Not found"}},
)


@router.get("/by-barcode/{barcode}", response_model=Product)
async def read_product_by_barcode(
    barcode: str,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(get_current_active_user),
):
    """
    Получение товара по штрих-коду.
    """
    logger.info("Поиск товара по штрих-коду %s пользователем %s", barcode, current_user.username)

    try:
        product = await services.get_product_service().get_product_by_barcode(
            barcode=barcode, current_user=current_user.model_dump()
        )

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при поиске товара по штрих-коду %s: %s", barcode, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.get("/", response_model=ProductResponseDTO)
@cache(namespace="global-products")
async def read_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    department: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(has_role(["admin", "manager"])),
):
    """
    Получение списка товаров с фильтрацией и сортировкой.
    """
    logger.info("Получение списка товаров пользователем %s", current_user.username)

    try:
        products = await services.get_product_service().get_products(
            skip=skip,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            department=department,
            min_price=min_price,
            max_price=max_price,
            current_user=current_user.model_dump(),
        )

        return products
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при получении списка товаров: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(has_role(["admin", "manager"])),
):
    """
    Создание нового товара.
    Требуются права администратора или менеджера.
    """
    logger.info("Creating product by user %s", current_user.username)

    try:
        created_product = await services.get_product_service().create_product(
            product_data=product.model_dump(), current_user=current_user.model_dump()
        )

        return created_product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при создании товара: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get("/{product_id}", response_model=Product)
async def read_product(
    product_id: int = Path(..., ge=1),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(has_role(["admin", "manager"])),
):
    """
    Получение товара по ID.
    """
    logger.info("Получение товара с ID %s пользователем %s", product_id, current_user.username)

    try:
        product = await services.get_product_service().get_product(
            product_id=product_id, current_user=current_user.model_dump()
        )

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return product
    except Exception as e:
        logger.error("Ошибка при получении товара с ID %s: %s", product_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: int = Path(..., ge=1),
    product_update: ProductUpdate = ...,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(has_role(["admin", "manager"])),
):
    """
    Обновление товара по ID.
    Требуются права администратора или менеджера.
    """
    logger.info("Обновление товара с ID %s пользователем %s", product_id, current_user.username)

    try:
        updated_product = await services.get_product_service().update_product(
            product_id=product_id,
            product_data=product_update.model_dump(exclude_unset=True),
            current_user=current_user.model_dump(),
        )

        if not updated_product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return updated_product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при обновлении товара с ID %s: %s", product_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int = Path(..., ge=1),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(has_role(["admin"])),
):
    """
    Удаление товара по ID.
    Требуются права администратора.
    """
    logger.info("Удаление товара с ID %s пользователем %s", product_id, current_user.username)

    try:
        result = await services.get_product_service().delete_product(
            product_id=product_id, current_user=current_user.model_dump()
        )

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return None
    except Exception as e:
        logger.error("Ошибка при удалении товара с ID %s: %s", product_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
