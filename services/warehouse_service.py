import logging
from typing import Any, Dict, Optional

from core.database import DatabaseService
from core.models import Warehouse, WarehouseCreate

logger = logging.getLogger("warehouse_service")


class WarehouseService:
    """
    Сервисный слой для работы со складами.

    Этот класс предоставляет методы для управления складами, включая получение
    списка складов с фильтрацией и сортировкой. Использует DatabaseService
    для доступа к данным.
    """

    def __init__(self, db_service: DatabaseService):
        """
        Инициализирует сервис с сервисом базы данных.

        Args:
            db_service: Сервис базы данных
        """
        self.db_service = db_service

    async def get_warehouses(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Dict[str, Any]:
        """
        Получает список складов с учетом параметров фильтрации и сортировки.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            search: Строка поиска
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)"
        """
        try:
            total_count = await self.db_service.get_warehouses_count(
                user_id=user_id,
                search=search,
            )

            warehouses = await self.db_service.get_warehouses(
                user_id=user_id,
                skip=skip,
                limit=limit,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order,
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
                "content": warehouses,
            }

            return response
        except Exception as e:
            logger.error("Ошибка при получении списка складов: %s", str(e))
            raise

    async def get_warehouse_by_id(self, warehouse_id: int) -> Warehouse | None:
        """
        Получает склад по ID.

        Args:
            warehouse_id: ID склада

        Returns:
            Словарь с данными склада или None, если склад не найден
        """
        try:
            warehouse = await self.db_service.get_warehouse_by_id(warehouse_id)
            return warehouse
        except Exception as e:
            logger.error("Ошибка при получении склада с ID %s: %s", warehouse_id, str(e))
            return None

    async def create_warehouse(
        self, warehouse_data: WarehouseCreate, user_id: int
    ) -> Dict[str, Any]:
        """
        Создает новый склад.

        Args:
            warehouse_data: Словарь с данными склада

        Returns:
            Словарь с данными созданного склада, включая ID
        """
        try:
            if isinstance(warehouse_data, dict):
                warehouse_data = WarehouseCreate(**warehouse_data)

            existing_warehouse = await self.db_service.get_warehouse_by_name(
                warehouse_data.name, user_id=user_id
            )
            if existing_warehouse:
                raise ValueError(f"Склад с названием '{warehouse_data.name}' уже существует")

            # Проверяем бизнес-правила
            self._validate_warehouse_data(warehouse_data)

            # Создаем склад
            logger.info("Попытка создать склад в сервисе")

            warehouse = await self.db_service.create_warehouse(user_id, warehouse_data)

            # Добавляем аудит
            await self.db_service.add_audit_log(
                action="create",
                entity="warehouse",
                entity_id=str(warehouse.id),
                user_id=str(user_id),
                details=f"Created warehouse: {warehouse.name}",
            )

            return warehouse
        except Exception as e:
            logger.error("Ошибка при создании склада: %s", str(e))
            raise

    async def update_warehouse(
        self, warehouse_id: int, warehouse_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные склада.

        Args:
            warehouse_id: ID склада
            warehouse_data: Словарь с обновляемыми данными склада

        Returns:
            Словарь с обновленными данными склада или None, если склад не найден
        """
        try:
            existing_warehouse = await self.db_service.get_warehouse_by_id(warehouse_id)
            if not existing_warehouse:
                return None

            merged_data = {**existing_warehouse, **warehouse_data}

            # Проверяем бизнес-правила
            self._validate_warehouse_data(WarehouseCreate(**merged_data))

            # Обновляем склад
            updated_warehouse = await self.db_service.update_warehouse(
                warehouse_id, WarehouseCreate(**merged_data)
            )

            # Добавляем аудит
            await self.db_service.add_audit_log(
                action="update",
                entity="warehouse",
                entity_id=str(warehouse_id),
                user_id=warehouse_data.get("user_id", ""),
                details=f"Updated warehouse: {updated_warehouse.get('name', '')}, fields: {', '.join(warehouse_data.keys())}",
            )

            return updated_warehouse
        except Exception as e:
            logger.error("Ошибка при обновлении склада с ID %s: %s", warehouse_id, str(e))
            raise

    async def delete_warehouse(self, warehouse_id: int) -> bool:
        """
        Удаляет склад.

        Args:
            warehouse_id: ID склада

        Returns:
            True, если склад успешно удален, иначе False
        """
        try:
            # Получаем данные склада для аудита
            warehouse = await self.db_service.get_warehouse_by_id(warehouse_id)
            if not warehouse:
                return False

            result = await self.db_service.delete_warehouse(warehouse_id)

            # Добавляем аудит
            await self.db_service.add_audit_log(
                action="delete",
                entity="warehouse",
                entity_id=str(warehouse_id),
                user_id=str(warehouse.get("user_id", "")),
                details=f"Deleted warehouse: {warehouse.get('name', '')}",
            )

            return result
        except Exception as e:
            logger.error("Ошибка при удалении склада с ID %s: %s", warehouse_id, str(e))
            raise

    async def add_product_to_warehouse(
        self, warehouse_id: int, product_id: int, quantity: int
    ) -> bool:
        """
        Добавляет продукт в склад.
        """

        try:
            result = await self.db_service.add_product_to_warehouse(
                warehouse_id, product_id, quantity
            )
            return result
        except Exception as e:
            logger.error("Ошибка при добавлении продукта в склад с ID %s: %s", warehouse_id, str(e))
            raise

    def _validate_warehouse_data(self, warehouse_data: WarehouseCreate) -> None:
        """
        Проверяет данные склада на соответствие бизнес-правилам.

        Args:
            warehouse_data: Словарь с данными склада

        Raises:
            ValueError: Если данные не соответствуют бизнес-правилам
        """
        if warehouse_data.name is None:
            raise ValueError("Необходимо указать имя склада")
