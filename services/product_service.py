from typing import Dict, List, Optional, Any
import logging
from core.database import DatabaseService

logger = logging.getLogger("product_service")


class ProductService:
    """
    Сервисный слой для работы с товарами.
    Реализует бизнес-логику и валидацию.
    """

    def __init__(self, db_service: DatabaseService):
        """
        Инициализирует сервис с сервисом базы данных.

        Args:
            db_service: Сервис базы данных
        """
        self.db_service = db_service

    async def get_product_by_barcode(self, barcode: str, current_user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Получение товара по штрих-коду.

        Args:
            barcode: Штрих-код товара для поиска
            current_user: Информация о текущем пользователе

        Returns:
            Информация о товаре или None, если товар не найден
        """
        try:
            product = await self.db_service.get_product_by_barcode(barcode)

            if not product:
                return None

            # Добавляем аудит
            await self.db_service.add_audit_log(
                action="read",
                entity="product",
                entity_id=str(product.get("id", "")),
                user_id=current_user.get("username", ""),
                details=f"Get product by barcode: {barcode}",
            )

            return product
        except Exception as e:
            logger.error(f"Ошибка при получении товара по штрих-коду {barcode}: {str(e)}")
            raise

    async def get_products(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        department: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        current_user: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Получает список товаров с учетом параметров фильтрации и сортировки.
        Добавляет запись в лог аудита.

        Args:
            Параметры аналогичны DatabaseService.get_products
            current_user: Данные текущего пользователя для аудита

        Returns:
            Словарь с метаинформацией и списком товаров
        """
        try:
            total_count = await self.db_service.get_products_count(
                search=search, department=department, min_price=min_price, max_price=max_price
            )

            products = await self.db_service.get_products(
                skip=skip,
                limit=limit,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
                department=department,
                min_price=min_price,
                max_price=max_price,
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
                "content": products,
            }

            # Добавляем аудит
            if current_user:
                await self.db_service.add_audit_log(
                    action="read",
                    entity="products",
                    entity_id="list",
                    user_id=current_user.get("username", "unknown"),
                    details=f"Retrieved products list with params: limit={limit}, skip={skip}",
                )

            return response

        except Exception as e:
            logger.error(f"Ошибка при получении списка товаров: {str(e)}")
            raise

    async def get_product(self, product_id: int, current_user: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Получает товар по ID.
        Добавляет запись в лог аудита.

        Args:
            product_id: ID товара
            current_user: Данные текущего пользователя для аудита

        Returns:
            Словарь с данными товара или None, если товар не найден
        """
        try:
            product = await self.db_service.get_product_by_id(product_id)

            if product and current_user:
                await self.db_service.add_audit_log(
                    action="read",
                    entity="product",
                    entity_id=str(product_id),
                    user_id=current_user.get("username", "unknown"),
                    details=f"Retrieved product: {product.get('sku_name', '')}",
                )

            return product
        except Exception as e:
            logger.error(f"Ошибка при получении товара с ID {product_id}: {str(e)}")
            raise

    async def create_product(self, product_data: Dict[str, Any], current_user: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Создает новый товар с проверкой бизнес-правил.
        Добавляет запись в лог аудита.

        Args:
            product_data: Словарь с данными товара
            current_user: Данные текущего пользователя для аудита

        Returns:
            Словарь с данными созданного товара, включая ID
        """
        try:
            # Проверяем уникальность SKU
            existing_product = await self.db_service.get_product_by_sku(product_data.get("sku_code", ""))
            if existing_product:
                raise ValueError(f"Product with SKU code '{product_data.get('sku_code')}' already exists")

            # Проверяем бизнес-правила
            self._validate_product_data(product_data)

            # Создаем товар
            product = await self.db_service.create_product(product_data)

            # Добавляем аудит
            if current_user:
                await self.db_service.add_audit_log(
                    action="create",
                    entity="product",
                    entity_id=str(product.get("id", "")),
                    user_id=current_user.get("username", "unknown"),
                    details=f"Created product: {product.get('sku_name', '')}",
                )

            return product
        except Exception as e:
            logger.error(f"Ошибка при создании товара: {str(e)}")
            raise

    async def update_product(
        self, product_id: int, product_data: Dict[str, Any], current_user: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные товара с проверкой бизнес-правил.
        Добавляет запись в лог аудита.

        Args:
            product_id: ID товара
            product_data: Словарь с обновляемыми данными товара
            current_user: Данные текущего пользователя для аудита

        Returns:
            Словарь с обновленными данными товара или None, если товар не найден
        """
        try:
            # Получаем текущие данные товара
            existing_product = await self.db_service.get_product_by_id(product_id)
            if not existing_product:
                return None

            # Проверяем уникальность SKU, если он изменяется
            if "sku_code" in product_data and product_data["sku_code"] != existing_product["sku_code"]:
                sku_product = await self.db_service.get_product_by_sku(product_data["sku_code"])
                if sku_product and sku_product["id"] != product_id:
                    raise ValueError(f"Product with SKU code '{product_data['sku_code']}' already exists")

            # Объединяем существующие и новые данные для валидации
            merged_data = {**existing_product, **product_data}

            # Проверяем бизнес-правила
            self._validate_product_data(merged_data)

            # Обновляем товар
            updated_product = await self.db_service.update_product(product_id, product_data)

            # Добавляем аудит
            if updated_product and current_user:
                await self.db_service.add_audit_log(
                    action="update",
                    entity="product",
                    entity_id=str(product_id),
                    user_id=current_user.get("username", "unknown"),
                    details=f"Updated product: {updated_product.get('sku_name', '')}, fields: {', '.join(product_data.keys())}",
                )

            return updated_product
        except Exception as e:
            logger.error(f"Ошибка при обновлении товара с ID {product_id}: {str(e)}")
            raise

    async def delete_product(self, product_id: int, current_user: Dict[str, Any] = None) -> bool:
        """
        Удаляет товар.
        Добавляет запись в лог аудита.

        Args:
            product_id: ID товара
            current_user: Данные текущего пользователя для аудита

        Returns:
            True, если товар успешно удален, иначе False
        """
        try:
            # Получаем данные товара для аудита
            product = await self.db_service.get_product_by_id(product_id)
            if not product:
                return False

            product_name = product.get("sku_name", "")

            # Удаляем товар
            result = await self.db_service.delete_product(product_id)

            # Добавляем аудит
            if result and current_user:
                await self.db_service.add_audit_log(
                    action="delete",
                    entity="product",
                    entity_id=str(product_id),
                    user_id=current_user.get("username", "unknown"),
                    details=f"Deleted product: {product_name}",
                )

            return result
        except Exception as e:
            logger.error(f"Ошибка при удалении товара с ID {product_id}: {str(e)}")
            raise

    def _validate_product_data(self, product_data: Dict[str, Any]) -> None:
        """
        Проверяет данные товара на соответствие бизнес-правилам.

        Args:
            product_data: Словарь с данными товара

        Raises:
            ValueError: Если данные не соответствуют бизнес-правилам
        """
        # Проверяем, что цена продажи не ниже себестоимости
        if "price" in product_data and "cost_price" in product_data:
            if product_data["price"] < product_data["cost_price"]:
                raise ValueError("Price cannot be lower than cost price")

        # Проверяем правильность кодов и наименований
        if "sku_code" in product_data and not product_data["sku_code"]:
            raise ValueError("SKU code cannot be empty")

        if "sku_name" in product_data and not product_data["sku_name"]:
            raise ValueError("Product name cannot be empty")
