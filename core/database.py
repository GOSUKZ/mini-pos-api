from typing import Dict, List, Optional, Any, Tuple
import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger("database_service")

class DatabaseService:
    """
    Сервисный слой для работы с базой данных.
    Реализует паттерн Repository для отделения логики доступа к данным.
    """

    def __init__(self, db_connection):
        """
        Инициализирует сервис с соединением с базой данных.

        Args:
            db_connection: Объект соединения с базой данных
        """
        self.db = db_connection

    async def get_products(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        department: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список товаров с учетом параметров фильтрации и сортировки.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            search: Строка поиска
            sort_by: Поле для сортировки
            sort_order: Порядок сортировки (asc или desc)
            department: Фильтр по отделу
            min_price: Минимальная цена
            max_price: Максимальная цена

        Returns:
            Список словарей с данными товаров
        """
        query_parts = ["SELECT * FROM products WHERE 1=1"]
        params = []

        if search:
            query_parts.append("AND (sku_name LIKE ? OR sku_code LIKE ? OR barcode LIKE ?)")
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])

        if department:
            query_parts.append("AND department = ?")
            params.append(department)

        if min_price is not None:
            query_parts.append("AND price >= ?")
            params.append(min_price)

        if max_price is not None:
            query_parts.append("AND price <= ?")
            params.append(max_price)

        if sort_by:
            valid_columns = ["id", "sku_code", "sku_name", "price", "cost_price", "supplier", "department"]
            if sort_by in valid_columns:
                query_parts.append(f"ORDER BY {sort_by} {sort_order}")
            else:
                raise ValueError(f"Invalid sort_by parameter. Valid options: {', '.join(valid_columns)}")
        else:
            query_parts.append("ORDER BY id ASC")

        query_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, skip])

        query = " ".join(query_parts)

        try:
            async with self.db.execute(query, params) as cursor:
                products = [dict(row) for row in await cursor.fetchall()]

            return products
        except Exception as e:
            logger.error(f"Ошибка при получении списка товаров: {str(e)}")
            raise

    async def get_product_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Получение товара по штрих-коду.

        Args:
            barcode: Штрих-код товара

        Returns:
            Информация о товаре или None, если товар не найден
        """
        try:
            async with self.db.execute(
                    "SELECT * FROM products WHERE barcode = ?",
                    (barcode,)
            ) as cursor:
                result = await cursor.fetchone()

                if result:
                    return dict(result)

                return None
        except Exception as e:
            logger.error(f"Ошибка при получении товара по штрих-коду из БД: {str(e)}")
            raise
    async def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает товар по ID.

        Args:
            product_id: ID товара

        Returns:
            Словарь с данными товара или None, если товар не найден
        """
        try:
            async with self.db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
                product = await cursor.fetchone()

            return dict(product) if product else None
        except Exception as e:
            logger.error(f"Ошибка при получении товара по ID {product_id}: {str(e)}")
            raise

    async def get_product_by_sku(self, sku_code: str) -> Optional[Dict[str, Any]]:
        """
        Получает товар по SKU коду.

        Args:
            sku_code: SKU код товара

        Returns:
            Словарь с данными товара или None, если товар не найден
        """
        try:
            async with self.db.execute("SELECT * FROM products WHERE sku_code = ?", (sku_code,)) as cursor:
                product = await cursor.fetchone()

            return dict(product) if product else None
        except Exception as e:
            logger.error(f"Ошибка при получении товара по SKU {sku_code}: {str(e)}")
            raise

    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новый товар.

        Args:
            product_data: Словарь с данными товара

        Returns:
            Словарь с данными созданного товара, включая ID
        """
        fields = product_data.keys()
        placeholders = ", ".join(["?"] * len(fields))
        fields_str = ", ".join(fields)

        query = f"INSERT INTO products ({fields_str}) VALUES ({placeholders})"

        try:
            await self.db.execute(query, list(product_data.values()))
            await self.db.commit()

            # Получаем ID созданного товара
            async with self.db.execute("SELECT last_insert_rowid() as id") as cursor:
                result = await cursor.fetchone()
                product_id = result["id"]

            # Получаем полные данные продукта
            async with self.db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
                product_data = await cursor.fetchone()

            return dict(product_data)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании товара: {str(e)}")
            raise

    async def update_product(self, product_id: int, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные товара.

        Args:
            product_id: ID товара
            product_data: Словарь с обновляемыми данными товара

        Returns:
            Словарь с обновленными данными товара или None, если товар не найден
        """
        if not product_data:
            return await self.get_product_by_id(product_id)

        set_parts = []
        params = []

        for key, value in product_data.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        params.append(product_id)
        query = f"UPDATE products SET {', '.join(set_parts)} WHERE id = ?"

        try:
            result = await self.db.execute(query, params)
            await self.db.commit()

            if result.rowcount == 0:
                return None

            # Получаем обновленные данные
            async with self.db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
                updated_product = await cursor.fetchone()

            return dict(updated_product) if updated_product else None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при обновлении товара с ID {product_id}: {str(e)}")
            raise

    async def delete_product(self, product_id: int) -> bool:
        """
        Удаляет товар.

        Args:
            product_id: ID товара

        Returns:
            True, если товар успешно удален, иначе False
        """
        try:
            result = await self.db.execute("DELETE FROM products WHERE id = ?", (product_id,))
            await self.db.commit()

            return result.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при удалении товара с ID {product_id}: {str(e)}")
            raise

    async def add_audit_log(
        self,
        action: str,
        entity: str,
        entity_id: str,
        user_id: str,
        details: str = ""
    ) -> int:
        """
        Добавляет запись в лог аудита.

        Args:
            action: Тип действия (create, update, delete, read)
            entity: Тип сущности (product, user)
            entity_id: ID сущности
            user_id: ID пользователя
            details: Дополнительные детали

        Returns:
            ID созданной записи
        """
        query = """
        INSERT INTO audit_log (action, entity, entity_id, user_id, timestamp, details)
        VALUES (?, ?, ?, ?, ?, ?)
        """

        try:
            await self.db.execute(query, (action, entity, entity_id, user_id, datetime.utcnow(), details))
            await self.db.commit()

            # Получаем ID созданной записи
            async with self.db.execute("SELECT last_insert_rowid() as id") as cursor:
                result = await cursor.fetchone()
                log_id = result["id"]

            return log_id
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при добавлении записи в аудит: {str(e)}")
            raise

    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        entity: Optional[str] = None,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает записи из лога аудита с учетом параметров фильтрации.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            entity: Фильтр по типу сущности
            action: Фильтр по типу действия
            user_id: Фильтр по ID пользователя
            from_date: Фильтр по начальной дате
            to_date: Фильтр по конечной дате

        Returns:
            Список словарей с данными записей аудита
        """
        query_parts = ["SELECT * FROM audit_log WHERE 1=1"]
        params = []

        if entity:
            query_parts.append("AND entity = ?")
            params.append(entity)

        if action:
            query_parts.append("AND action = ?")
            params.append(action)

        if user_id:
            query_parts.append("AND user_id = ?")
            params.append(user_id)

        if from_date:
            query_parts.append("AND timestamp >= ?")
            params.append(from_date)

        if to_date:
            query_parts.append("AND timestamp <= ?")
            params.append(to_date)

        query_parts.append("ORDER BY timestamp DESC LIMIT ? OFFSET ?")
        params.extend([limit, skip])

        query = " ".join(query_parts)

        try:
            async with self.db.execute(query, params) as cursor:
                logs = [dict(row) for row in await cursor.fetchall()]

            return logs
        except Exception as e:
            logger.error(f"Ошибка при получении записей аудита: {str(e)}")
            raise

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по имени пользователя.

        Args:
            username: Имя пользователя

        Returns:
            Словарь с данными пользователя или None, если пользователь не найден
        """
        try:
            async with self.db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
                user = await cursor.fetchone()

            if user:
                user_dict = dict(user)
                user_dict["roles"] = user_dict["roles"].split(",") if user_dict["roles"] else []
                return user_dict

            return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {username}: {str(e)}")
            raise

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает нового пользователя.

        Args:
            user_data: Словарь с данными пользователя

        Returns:
            Словарь с данными созданного пользователя, включая ID
        """
        # Преобразуем список ролей в строку
        if "roles" in user_data and isinstance(user_data["roles"], list):
            user_data["roles"] = ",".join(user_data["roles"])

        fields = user_data.keys()
        placeholders = ", ".join(["?"] * len(fields))
        fields_str = ", ".join(fields)

        query = f"INSERT INTO users ({fields_str}) VALUES ({placeholders})"

        try:
            await self.db.execute(query, list(user_data.values()))
            await self.db.commit()

            # Получаем созданного пользователя
            user = await self.get_user_by_username(user_data["username"])

            return user
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании пользователя: {str(e)}")
            raise

    async def update_user(self, username: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные пользователя.

        Args:
            username: Имя пользователя
            user_data: Словарь с обновляемыми данными пользователя

        Returns:
            Словарь с обновленными данными пользователя или None, если пользователь не найден
        """
        if not user_data:
            return await self.get_user_by_username(username)

        # Преобразуем список ролей в строку
        if "roles" in user_data and isinstance(user_data["roles"], list):
            user_data["roles"] = ",".join(user_data["roles"])

        set_parts = []
        params = []

        for key, value in user_data.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        params.append(username)
        query = f"UPDATE users SET {', '.join(set_parts)} WHERE username = ?"

        try:
            result = await self.db.execute(query, params)
            await self.db.commit()

            if result.rowcount == 0:
                return None

            # Получаем обновленные данные
            return await self.get_user_by_username(username)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при обновлении пользователя {username}: {str(e)}")
            raise

    """
        Дополнительные методы для DatabaseService для работы с OAuth и платежами.
        Скопируйте эти методы в существующий класс DatabaseService.
        """

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по email.

        Args:
            email: Email пользователя

        Returns:
            Словарь с данными пользователя или None, если пользователь не найден
        """
        try:
            async with self.db.execute("SELECT * FROM users WHERE email = ?", (email,)) as cursor:
                user = await cursor.fetchone()

            if user:
                user_dict = dict(user)
                user_dict["roles"] = user_dict["roles"].split(",") if user_dict["roles"] else []
                return user_dict

            return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя по email {email}: {str(e)}")
            raise

    async def get_oauth_account(self, provider: str, provider_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает OAuth аккаунт пользователя.

        Args:
            provider: Провайдер OAuth (например, 'google')
            provider_user_id: ID пользователя в системе провайдера

        Returns:
            Словарь с данными OAuth аккаунта или None, если аккаунт не найден
        """
        try:
            query = "SELECT * FROM oauth_accounts WHERE provider = ? AND provider_user_id = ?"
            async with self.db.execute(query, (provider, provider_user_id)) as cursor:
                account = await cursor.fetchone()

            return dict(account) if account else None
        except Exception as e:
            logger.error(f"Ошибка при получении OAuth аккаунта: {str(e)}")
            raise

    async def create_oauth_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает OAuth аккаунт для пользователя.

        Args:
            account_data: Словарь с данными OAuth аккаунта

        Returns:
            Словарь с данными созданного OAuth аккаунта
        """
        fields = account_data.keys()
        placeholders = ", ".join(["?"] * len(fields))
        fields_str = ", ".join(fields)

        query = f"INSERT INTO oauth_accounts ({fields_str}) VALUES ({placeholders})"

        try:
            await self.db.execute(query, list(account_data.values()))
            await self.db.commit()

            # Получаем ID созданной записи
            async with self.db.execute("SELECT last_insert_rowid() as id") as cursor:
                result = await cursor.fetchone()
                account_id = result["id"]

            # Получаем полные данные OAuth аккаунта
            async with self.db.execute("SELECT * FROM oauth_accounts WHERE id = ?", (account_id,)) as cursor:
                account = await cursor.fetchone()

            return dict(account)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании OAuth аккаунта: {str(e)}")
            raise

    async def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новую запись о платеже.

        Args:
            payment_data: Словарь с данными платежа

        Returns:
            Словарь с данными созданного платежа, включая ID
        """
        fields = payment_data.keys()
        placeholders = ", ".join(["?"] * len(fields))
        fields_str = ", ".join(fields)

        query = f"INSERT INTO payments ({fields_str}) VALUES ({placeholders})"

        try:
            await self.db.execute(query, list(payment_data.values()))
            await self.db.commit()

            # Получаем ID созданного платежа
            async with self.db.execute("SELECT last_insert_rowid() as id") as cursor:
                result = await cursor.fetchone()
                payment_id = result["id"]

            # Получаем полные данные платежа
            async with self.db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)) as cursor:
                payment = await cursor.fetchone()

            return dict(payment)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании платежа: {str(e)}")
            raise

    async def update_payment(self, payment_id: str, payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные платежа.

        Args:
            payment_id: ID платежа в системе PayPal
            payment_data: Словарь с обновляемыми данными платежа

        Returns:
            Словарь с обновленными данными платежа или None, если платеж не найден
        """
        if not payment_data:
            return None

        set_parts = []
        params = []

        for key, value in payment_data.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        params.append(payment_id)
        query = f"UPDATE payments SET {', '.join(set_parts)}, updated_at = ? WHERE payment_id = ?"

        # Добавляем текущий timestamp
        current_time = datetime.utcnow()
        params.insert(-1, current_time)

        try:
            result = await self.db.execute(query, params)
            await self.db.commit()

            if result.rowcount == 0:
                return None

            # Получаем обновленные данные
            async with self.db.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)) as cursor:
                updated_payment = await cursor.fetchone()

            return dict(updated_payment) if updated_payment else None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при обновлении платежа с ID {payment_id}: {str(e)}")
            raise

    async def get_payment_by_id(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает платеж по ID в системе PayPal.

        Args:
            payment_id: ID платежа в системе PayPal

        Returns:
            Словарь с данными платежа или None, если платеж не найден
        """
        try:
            async with self.db.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)) as cursor:
                payment = await cursor.fetchone()

            return dict(payment) if payment else None
        except Exception as e:
            logger.error(f"Ошибка при получении платежа по ID {payment_id}: {str(e)}")
            raise

    async def get_payments(
            self,
            skip: int = 0,
            limit: int = 100,
            status: Optional[str] = None,
            payment_provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список платежей с учетом параметров фильтрации.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            status: Фильтр по статусу платежа
            payment_provider: Фильтр по платежной системе

        Returns:
            Список словарей с данными платежей
        """
        query_parts = ["SELECT * FROM payments WHERE 1=1"]
        params = []

        if status:
            query_parts.append("AND status = ?")
            params.append(status)

        if payment_provider:
            query_parts.append("AND payment_provider = ?")
            params.append(payment_provider)

        query_parts.append("ORDER BY created_at DESC LIMIT ? OFFSET ?")
        params.extend([limit, skip])

        query = " ".join(query_parts)

        try:
            async with self.db.execute(query, params) as cursor:
                payments = [dict(row) for row in await cursor.fetchall()]

            return payments
        except Exception as e:
            logger.error(f"Ошибка при получении списка платежей: {str(e)}")
            raise

    # Добавьте эти методы в класс DatabaseService

    # --- Методы для работы с планами подписок ---

    async def get_subscription_plans(
            self,
            skip: int = 0,
            limit: int = 100,
            active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получает список планов подписок.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей для возврата
            active_only: Показывать только активные планы

        Returns:
            Список словарей с данными планов подписок
        """
        query_parts = ["SELECT * FROM subscription_plans WHERE 1=1"]
        params = []

        if active_only:
            query_parts.append("AND is_active = ?")
            params.append(True)

        query_parts.append("ORDER BY price ASC LIMIT ? OFFSET ?")
        params.extend([limit, skip])

        query = " ".join(query_parts)

        try:
            async with self.db.execute(query, params) as cursor:
                plans = [dict(row) for row in await cursor.fetchall()]

            return plans
        except Exception as e:
            logger.error(f"Ошибка при получении списка планов подписок: {str(e)}")
            raise

    async def get_subscription_plan_by_id(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает план подписки по ID.

        Args:
            plan_id: ID плана подписки

        Returns:
            Словарь с данными плана подписки или None, если план не найден
        """
        try:
            async with self.db.execute("SELECT * FROM subscription_plans WHERE id = ?", (plan_id,)) as cursor:
                plan = await cursor.fetchone()

            return dict(plan) if plan else None
        except Exception as e:
            logger.error(f"Ошибка при получении плана подписки по ID {plan_id}: {str(e)}")
            raise

    async def create_subscription_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новый план подписки.

        Args:
            plan_data: Словарь с данными плана подписки

        Returns:
            Словарь с данными созданного плана подписки, включая ID
        """
        fields = plan_data.keys()
        placeholders = ", ".join(["?"] * len(fields))
        fields_str = ", ".join(fields)

        query = f"INSERT INTO subscription_plans ({fields_str}) VALUES ({placeholders})"

        try:
            await self.db.execute(query, list(plan_data.values()))
            await self.db.commit()

            # Получаем ID созданного плана
            async with self.db.execute("SELECT last_insert_rowid() as id") as cursor:
                result = await cursor.fetchone()
                plan_id = result["id"]

            # Получаем полные данные плана
            async with self.db.execute("SELECT * FROM subscription_plans WHERE id = ?", (plan_id,)) as cursor:
                plan_data = await cursor.fetchone()

            return dict(plan_data)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании плана подписки: {str(e)}")
            raise

    async def update_subscription_plan(self, plan_id: int, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обновляет данные плана подписки.

        Args:
            plan_id: ID плана подписки
            plan_data: Словарь с обновляемыми данными плана подписки

        Returns:
            Словарь с обновленными данными плана подписки или None, если план не найден
        """
        if not plan_data:
            return await self.get_subscription_plan_by_id(plan_id)

        set_parts = []
        params = []

        for key, value in plan_data.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        # Добавляем обновление updated_at
        set_parts.append("updated_at = ?")
        params.append(datetime.utcnow())

        params.append(plan_id)
        query = f"UPDATE subscription_plans SET {', '.join(set_parts)} WHERE id = ?"

        try:
            result = await self.db.execute(query, params)
            await self.db.commit()

            if result.rowcount == 0:
                return None

            # Получаем обновленные данные
            return await self.get_subscription_plan_by_id(plan_id)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при обновлении плана подписки с ID {plan_id}: {str(e)}")
            raise

    # --- Методы для работы с подписками пользователей ---

    async def create_subscription(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новую подписку для пользователя.

        Args:
            subscription_data: Словарь с данными подписки

        Returns:
            Словарь с данными созданной подписки, включая ID
        """
        fields = subscription_data.keys()
        placeholders = ", ".join(["?"] * len(fields))
        fields_str = ", ".join(fields)

        query = f"INSERT INTO subscriptions ({fields_str}) VALUES ({placeholders})"

        try:
            await self.db.execute(query, list(subscription_data.values()))
            await self.db.commit()

            # Получаем ID созданной подписки
            async with self.db.execute("SELECT last_insert_rowid() as id") as cursor:
                result = await cursor.fetchone()
                subscription_id = result["id"]

            # Получаем полные данные подписки
            async with self.db.execute("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,)) as cursor:
                subscription_data = await cursor.fetchone()

            return dict(subscription_data)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании подписки: {str(e)}")
            raise

    async def get_subscription_by_id(self, subscription_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает подписку по ID.

        Args:
            subscription_id: ID подписки

        Returns:
            Словарь с данными подписки или None, если подписка не найдена
        """
        try:
            async with self.db.execute("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,)) as cursor:
                subscription = await cursor.fetchone()

            return dict(subscription) if subscription else None
        except Exception as e:
            logger.error(f"Ошибка при получении подписки по ID {subscription_id}: {str(e)}")
            raise

    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает активную подписку пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Словарь с данными подписки или None, если активная подписка не найдена
        """
        try:
            # Получаем самую последнюю активную подписку пользователя
            query = """
            SELECT * FROM subscriptions 
            WHERE user_id = ? AND status = 'active' 
            ORDER BY end_date DESC LIMIT 1
            """

            async with self.db.execute(query, (user_id,)) as cursor:
                subscription = await cursor.fetchone()

            return dict(subscription) if subscription else None
        except Exception as e:
            logger.error(f"Ошибка при получении подписки пользователя {user_id}: {str(e)}")
            raise

    async def update_subscription(self, subscription_id: int, subscription_data: Dict[str, Any]) -> Optional[
        Dict[str, Any]]:
        """
        Обновляет данные подписки.

        Args:
            subscription_id: ID подписки
            subscription_data: Словарь с обновляемыми данными подписки

        Returns:
            Словарь с обновленными данными подписки или None, если подписка не найдена
        """
        if not subscription_data:
            return await self.get_subscription_by_id(subscription_id)

        set_parts = []
        params = []

        for key, value in subscription_data.items():
            set_parts.append(f"{key} = ?")
            params.append(value)

        # Добавляем обновление updated_at
        set_parts.append("updated_at = ?")
        params.append(datetime.utcnow())

        params.append(subscription_id)
        query = f"UPDATE subscriptions SET {', '.join(set_parts)} WHERE id = ?"

        try:
            result = await self.db.execute(query, params)
            await self.db.commit()

            if result.rowcount == 0:
                return None

            # Получаем обновленные данные
            return await self.get_subscription_by_id(subscription_id)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при обновлении подписки с ID {subscription_id}: {str(e)}")
            raise

    async def get_expiring_subscriptions(self, days_threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Получает подписки, срок действия которых истекает в ближайшие дни.

        Args:
            days_threshold: Количество дней до истечения срока

        Returns:
            Список словарей с данными подписок
        """
        try:
            # Вычисляем дату через days_threshold дней
            from datetime import timedelta
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)

            query = """
            SELECT * FROM subscriptions 
            WHERE status = 'active' AND end_date <= ? AND end_date >= ?
            ORDER BY end_date ASC
            """

            current_date = datetime.utcnow()

            async with self.db.execute(query, (threshold_date, current_date)) as cursor:
                subscriptions = [dict(row) for row in await cursor.fetchall()]

            return subscriptions
        except Exception as e:
            logger.error(f"Ошибка при получении истекающих подписок: {str(e)}")
            raise

    async def get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """
        Получает подписки, срок действия которых истек, но статус все еще 'active'.

        Returns:
            Список словарей с данными подписок
        """
        try:
            current_date = datetime.utcnow()

            query = """
            SELECT * FROM subscriptions 
            WHERE status = 'active' AND end_date < ?
            ORDER BY end_date ASC
            """

            async with self.db.execute(query, (current_date,)) as cursor:
                subscriptions = [dict(row) for row in await cursor.fetchall()]

            return subscriptions
        except Exception as e:
            logger.error(f"Ошибка при получении истекших подписок: {str(e)}")
            raise

    async def get_subscriptions_for_renewal(self, days_threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Получает подписки с автопродлением, требующие продления в ближайшие дни.

        Args:
            days_threshold: Количество дней до истечения срока

        Returns:
            Список словарей с данными подписок
        """
        try:
            # Вычисляем дату через days_threshold дней
            from datetime import timedelta
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
            current_date = datetime.utcnow()

            query = """
            SELECT * FROM subscriptions 
            WHERE status = 'active' AND auto_renew = ? AND end_date <= ? AND end_date >= ?
            ORDER BY end_date ASC
            """

            async with self.db.execute(query, (True, threshold_date, current_date)) as cursor:
                subscriptions = [dict(row) for row in await cursor.fetchall()]

            return subscriptions
        except Exception as e:
            logger.error(f"Ошибка при получении подписок для продления: {str(e)}")
            raise

    async def get_user_subscriptions_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает историю подписок пользователя.

        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей

        Returns:
            Список словарей с данными подписок
        """
        try:
            query = """
            SELECT * FROM subscriptions 
            WHERE user_id = ? 
            ORDER BY created_at DESC
            LIMIT ?
            """

            async with self.db.execute(query, (user_id, limit)) as cursor:
                subscriptions = [dict(row) for row in await cursor.fetchall()]

            return subscriptions
        except Exception as e:
            logger.error(f"Ошибка при получении истории подписок пользователя {user_id}: {str(e)}")
            raise