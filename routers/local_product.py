from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
import logging
from utils.dependencies import get_product_service, get_current_active_user, has_role, can_read_products
from services.product_service import ProductService
from core.models import Product, ProductCreate, ProductUpdate, User

logger = logging.getLogger("local_product_router")


router = APIRouter(
    prefix="/products/local",
    tags=["Local products"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[Product])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    department: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(can_read_products),
):
    """
    Получение списка товаров с фильтрацией и сортировкой.
    """
    logger.info(f"Получение списка товаров пользователем {current_user.username}")

    try:
        products = await product_service.get_products(
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
        logger.error(f"Ошибка при получении списка товаров: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/", response_model=Product, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(has_role(["admin", "manager"])),
):
    """
    Создание нового товара.
    Требуются права администратора или менеджера.
    """
    logger.info(f"Создание товара пользователем {current_user.username}")

    try:
        created_product = await product_service.create_product(
            product_data=product.model_dump(), current_user=current_user.model_dump()
        )

        return created_product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при создании товара: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{product_id}", response_model=Product)
async def read_product(
    product_id: int = Path(..., ge=1),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(get_current_active_user),
):
    """
    Получение товара по ID.
    """
    logger.info(f"Получение товара с ID {product_id} пользователем {current_user.username}")

    try:
        product = await product_service.get_product(product_id=product_id, current_user=current_user.model_dump())

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return product
    except Exception as e:
        logger.error(f"Ошибка при получении товара с ID {product_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: int = Path(..., ge=1),
    product_update: ProductUpdate = ...,
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(has_role(["admin", "manager"])),
):
    """
    Обновление товара по ID.
    Требуются права администратора или менеджера.
    """
    logger.info(f"Обновление товара с ID {product_id} пользователем {current_user.username}")

    try:
        updated_product = await product_service.update_product(
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
        logger.error(f"Ошибка при обновлении товара с ID {product_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int = Path(..., ge=1),
    product_service: ProductService = Depends(get_product_service),
    current_user: User = Depends(has_role(["admin"])),
):
    """
    Удаление товара по ID.
    Требуются права администратора.
    """
    logger.info(f"Удаление товара с ID {product_id} пользователем {current_user.username}")

    try:
        result = await product_service.delete_product(product_id=product_id, current_user=current_user.model_dump())

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return None
    except Exception as e:
        logger.error(f"Ошибка при удалении товара с ID {product_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
