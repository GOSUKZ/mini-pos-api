"""
Модуль маршрутов для управления локальными товарами.

Этот модуль определяет API-эндпоинты для работы с локальными товарами,
включая их получение, создание, обновление и удаление.
Реализована поддержка фильтрации, сортировки и пагинации.

Маршруты:
- `GET /products/local/` — получение списка товаров с фильтрацией и сортировкой.
- `POST /products/local/` — создание нового товара (требуются права администратора или менеджера).
- `GET /products/local/{product_id}` — получение товара по ID.
- `PUT /products/local/{product_id}` — обновление товара по ID (требуются права администратора или менеджера).
- `DELETE /products/local/{product_id}` — удаление товара по ID (требуются права администратора).

Авторизация:
- Для выполнения большинства операций требуется проверка прав доступа (через зависимости `can_read_products` и `has_role`).

Зависимости:
- `ProductService` — сервис для работы с товарами.
- `User` — модель пользователя, извлекаемая через зависимости.

Логирование:
- Включено логирование всех ключевых операций с товарами.
- Используется именованный логгер `local_product_router`.

Ошибки:
- `400 Bad Request` — некорректные параметры запроса.
- `404 Not Found` — товар не найден.
- `500 Internal Server Error` — внутренняя ошибка сервера.

"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi_cache.decorator import cache

from core.dtos.local_product_response_dto import LocalProductResponseDTO
from core.models import LocalProductCreate, LocalProductDTO, LocalProductUpdate, User
from utils.dependencies import can_read_products, get_services
from utils.service_factory import ServiceFactory

logger = logging.getLogger("local_product_router")


router = APIRouter(
    prefix="/products/local",
    tags=["Local products"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=LocalProductResponseDTO)
@cache(namespace="local-products")
async def read_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    department: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    # warehouse_id: Optional[int] = None,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_products),
):
    """
    Получение списка товаров с фильтрацией и сортировкой.
    """
    logger.info(
        "Получение списка товаров пользователем %s, %s", current_user.username, current_user.id
    )

    try:
        products = await services.get_product_service().get_local_products(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            department=department,
            min_price=min_price,
            max_price=max_price,
            # warehouse_id=warehouse_id,
        )

        return products
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Ошибка при получении списка товаров: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.get("/all", response_model=List[LocalProductDTO])
# @cache(namespace="all-local-products")
async def read_all_products(
    sort_by: Optional[str] = None,
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_products),
):
    """
    Получение списка товаров с фильтрацией и сортировкой.
    """
    logger.info(
        "Получение списка всех товаров пользователем %s, %s", current_user.username, current_user.id
    )

    try:
        products = await services.get_product_service().get_all_local_products(
            user_id=current_user.id,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return products
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Ошибка при получении списка товаров: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.post("/", response_model=LocalProductDTO, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: LocalProductCreate,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_products),
):
    """
    Создание нового товара.
    Требуются права администратора или менеджера.
    """
    logger.info("Создание товара пользователем %s", current_user.username)

    try:
        created_product = await services.get_product_service().create_local_product(
            product_data=product.model_dump(), user_id=current_user.id
        )

        return created_product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Ошибка при создании товара: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.get("/{product_id}", response_model=LocalProductDTO)
async def read_product(
    product_id: int = Path(..., ge=1),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_products),
):
    """
    Получение товара по ID.
    """
    logger.info("Получение товара с ID %s пользователем %s", product_id, current_user.username)

    try:
        product = await services.get_product_service().get_local_product(product_id=product_id)

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        if product.get("user_id") != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return product
    except HTTPException:
        raise  # Пробрасываем, чтобы FastAPI сам обработал 404 и 403
    except Exception as e:
        logger.error("Ошибка при получении товара с ID %s: %s", product_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.put("/{product_id}", response_model=LocalProductDTO)
async def update_product(
    product_id: int = Path(..., ge=1),
    product_update: LocalProductUpdate = ...,
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_products),
):
    """
    Обновление товара по ID.
    """
    logger.info("Обновление товара с ID %s пользователем %s", product_id, current_user.username)

    try:
        product = await services.get_product_service().get_local_product(product_id=product_id)

        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        if product.get("user_id") != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        updated_product = await services.get_product_service().update_local_product(
            product_id=product_id,
            product_data=product_update.model_dump(exclude_unset=True),
            current_user=current_user.model_dump(),
        )

        if not updated_product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return updated_product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("Ошибка при обновлении товара с ID %s: %s", product_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product(
    product_id: int = Path(..., ge=1),
    services: ServiceFactory = Depends(get_services),
    current_user: User = Depends(can_read_products),
):
    """
    Удаление товара по ID.
    Требуются права администратора.
    """
    logger.info("Удаление товара с ID %s пользователем %s", product_id, current_user.username)

    try:
        product = await services.get_product_service().get_local_product(product_id=product_id)
    except Exception as e:
        logger.error("Ошибка при поиске товара с ID %s: %s", product_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error"
        ) from e

    if not product:
        logger.info("Товар с ID %s не найден", product_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if product.get("user_id") != current_user.id:
        logger.warning("Попытка удалить чужой товар: %s", product_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        result = await services.get_product_service().delete_local_product(product_id=product_id)

        if not result:
            logger.info("Не удалось удалить товар с ID %s, возможно, он уже удален", product_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        return None
    except Exception as e:
        logger.error("Ошибка при удалении товара с ID %s: %s", product_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        ) from e
