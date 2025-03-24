"""
This module contains the router for the warehouses.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi_cache.decorator import cache

from config import clear_warehouse_cache
from core.dtos.warehouse_response_dto import WarehouseResponseDTO
from core.models import User, Warehouse, WarehouseCreate
from utils.dependencies import can_manage_warehouse, can_read_warehouses, get_services
from utils.service_factory import ServiceFactory

logger = logging.getLogger("warehouse_router")

# Создаем роутер
router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=WarehouseResponseDTO)
# @cache(namespace="warehouses")
async def get_warehouses(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_warehouses),
):
    """
    Получение списка складов с учетом параметров фильтрации и сортировки.
    """
    logger.info(
        "Получение списка складов пользователем %s, %s", current_user.username, current_user.id
    )

    try:
        warehouses = await services.get_warehouses(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return warehouses
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при получении списка складов: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    warehouse: WarehouseCreate,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_warehouses),
):
    """
    Создание нового склада.
    Требуются права администратора или менеджера.
    """

    logger.info("Создание склада пользователем %s", current_user.username)

    try:
        created_warehouse = await services.create_warehouse(
            warehouse.model_dump(), user_id=current_user.id
        )

        await clear_warehouse_cache()

        return created_warehouse
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при создании склада: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post(
    "/{warehouse_id}/add-product/{product_id}/{quantity}",
    status_code=status.HTTP_201_CREATED,
)
async def add_product_to_warehouse(
    warehouse_id: int = Path(..., ge=1),
    product_id: int = Path(..., ge=1),
    quantity: int = Path(..., ge=1),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_manage_warehouse),
):
    """
    Добавление товара в склад.
    """

    logger.info(
        "Добавление товара в склад %s пользователем %s", warehouse_id, current_user.username
    )
    try:
        warehouse = await services.add_product_to_warehouse(warehouse_id, product_id, quantity)
        return {"message": "Product added"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при добавлении товара в склад %s: %s", warehouse_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.get("/{warehouse_id}", response_model=Warehouse)
async def read_warehouse(
    warehouse_id: int = Path(..., ge=1),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_manage_warehouse),
):
    """
    Получение склада по ID.
    """
    logger.info("Получение склада с ID %s пользователем %s", warehouse_id, current_user.username)

    try:
        warehouse = await services.get_warehouse_by_id(warehouse_id)

        if warehouse is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

        if warehouse.get("user_id") != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return warehouse
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Ошибка при получении склада с ID %s: %s", warehouse_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении склада с ID {warehouse_id}: {str(e)}",
        )


@router.put("/{warehouse_id}", response_model=Warehouse)
async def update_warehouse(
    warehouse_id: int = Path(..., ge=1),
    warehouse_update: WarehouseCreate = ...,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_manage_warehouse),
):
    """
    Обновление склада по ID.
    """
    logger.info("Обновление склада с ID %s пользователем %s", warehouse_id, current_user.username)

    try:
        warehouse = await services.get_warehouse_by_id(warehouse_id)

        if not warehouse:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

        if warehouse.get("user_id") != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        updated_warehouse = await services.update_warehouse(
            warehouse_id=warehouse_id,
            warehouse_data=warehouse_update.model_dump(exclude_unset=True),
        )

        if not updated_warehouse:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

        await clear_warehouse_cache()

        return updated_warehouse
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Ошибка при обновлении склада с ID %s: %s", warehouse_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.delete(
    "/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_warehouse(
    warehouse_id: int = Path(..., ge=1),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_manage_warehouse),
):
    """
    Удаление склада по ID.
    Требуются права администратора.
    """
    logger.info("Удаление склада с ID %s пользователем %s", warehouse_id, current_user.username)

    try:
        result = await services.delete_warehouse(warehouse_id)

        if not result:  # Если склад не удалось
            logger.info("Не удалось удалить склад с ID %s, возможно, он уже удален", warehouse_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

        await clear_warehouse_cache()

    except Exception as e:
        logger.error("Ошибка при удалении склада с ID %s: %s", warehouse_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
