"""
Модуль для определения моделей данных, используемых в приложении.

Этот модуль предоставляет различные модели данных, которые описывают структуры объектов,
используемых в приложении, включая модели продуктов, пользователей, токенов и аудита.
Модели основаны на Pydantic и используются для валидации и преобразования данных.

Содержимое:
- Модели продуктов (ProductBase, LocalProduct, ProductCreate и т.д.)
- Модели пользователей (UserBase, UserCreate, UserUpdate и т.д.)
- Модели токенов (Token, TokenData)
- Модели аудита (AuditLog, AuditLogFilter)
- Модели OAuth аккаунтов (OAuthAccountBase)
"""

import re
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --- Модели данных продуктов ---


class ProductBase(BaseModel):
    """Базовая модель товара с общими полями"""

    sku_code: str = Field(..., description="Уникальный код товара")
    barcode: Optional[str] = Field(None, description="Штрих-код товара")
    unit: str = Field(..., description="Единица измерения")
    sku_name: str = Field(..., description="Наименование товара")
    status_1c: str = Field(..., description="Статус в 1C")
    department: str = Field(..., description="Отдел")
    group_name: str = Field(..., description="Группа товаров")
    subgroup: Optional[str] = Field(None, description="Подгруппа товаров")
    supplier: str = Field(..., description="Поставщик")
    cost_price: float = Field(..., ge=0, description="Себестоимость")
    price: float = Field(..., ge=0, description="Цена продажи")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        validate_assignment=True,
    )

    @field_validator("sku_code")
    @classmethod
    def validate_sku_code(cls, v: str) -> str:
        """
        Validate and transform the SKU code.

        This method ensures that the SKU code contains only valid characters
        (letters, numbers, hyphens, and underscores) and converts it to uppercase.

        Args:
            v (str): The SKU code to validate.

        Returns:
            str: The validated and transformed SKU code in uppercase.

        Raises:
            ValueError: If the SKU code contains invalid characters.
        """
        if not re.match(r"^[A-Za-z0-9-_]+$", v):
            raise ValueError("SKU код должен содержать только буквы, цифры, дефисы и подчеркивания")
        return v.upper()

    @field_validator("price", "cost_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """
        Validate and transform the price and cost price.

        This method ensures that the price and cost price are rounded to two decimal places.

        Args:
            v (float): The price or cost price to validate.

        Returns:
            float: The validated and transformed price or cost price.
        """
        return round(v, 2)

    @model_validator(mode="after")
    def validate_prices(self) -> "ProductBase":
        """
        Validate that the selling price is not lower than the cost price.

        This method is called after the model has been created and validated.
        It checks that the selling price is not lower than the cost price.
        If the condition is not met, it raises a ValueError.

        Returns:
            ProductBase: The validated model.
        """
        # Check that the selling price is not lower than the cost price
        if self.price < self.cost_price:
            raise ValueError("Цена продажи не может быть ниже себестоимости")
        return self


class LocalProduct(ProductBase):
    """Модель локального продукта"""

    user_id: int = Field(..., description="ID пользователя, которому принадлежит локальный продукт")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocalProductCreate(ProductBase):
    """Модель для создания локального продукта"""


class LocalProductUpdate(ProductBase):
    """Модель для обновления локального продукта с опциональными полями"""

    sku_code: Optional[str] = None
    barcode: Optional[str] = None
    unit: Optional[str] = None
    sku_name: Optional[str] = None
    status_1c: Optional[str] = None
    department: Optional[str] = None
    group_name: Optional[str] = None
    subgroup: Optional[str] = None
    supplier: Optional[str] = None
    cost_price: Optional[float] = None
    price: Optional[float] = None


class ProductCreate(ProductBase):
    """Модель создания товара"""


class ProductUpdate(BaseModel):
    """Модель обновления товара с опциональными полями"""

    sku_code: Optional[str] = None
    barcode: Optional[str] = None
    unit: Optional[str] = None
    sku_name: Optional[str] = None
    status_1c: Optional[str] = None
    department: Optional[str] = None
    group_name: Optional[str] = None
    subgroup: Optional[str] = None
    supplier: Optional[str] = None
    cost_price: Optional[float] = None
    price: Optional[float] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
        validate_assignment=True,
    )

    @field_validator("sku_code")
    @classmethod
    def validate_sku_code(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate and transform the SKU code.

        This method ensures that the SKU code contains only valid characters
        (letters, numbers, hyphens, and underscores) and converts it to uppercase.

        Args:
            v (str): The SKU code to validate.

        Returns:
            str: The validated and transformed SKU code in uppercase.

        Raises:
            ValueError: If the SKU code contains invalid characters.
        """
        if v is not None:
            if not re.match(r"^[A-Za-z0-9-_]+$", v):
                raise ValueError(
                    "SKU код должен содержать только буквы, цифры, дефисы и подчеркивания"
                )
            return v.upper()
        return v

    @field_validator("cost_price", "price")
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate the price and cost price fields.

        This method ensures that the price and cost price are non-negative
        and rounded to two decimal places.

        Args:
            v (Optional[float]): The price or cost price to validate.

        Returns:
            Optional[float]: The validated and transformed price or cost price.

        Raises:
            ValueError: If the price or cost price is negative.
        """
        if v is not None:
            if v < 0:
                raise ValueError("Цена не может быть отрицательной")
            # Round the value to two decimal places
            return round(v, 2)
        return v


class Product(ProductBase):
    """Полная модель товара с ID"""

    id: int

    model_config = ConfigDict(from_attributes=True)


# --- Модели данных пользователей ---


class UserBase(BaseModel):
    """Базовая модель пользователя"""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    is_active: bool = True
    roles: List[str] = ["user"]

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        Validate the username.

        The username should contain only letters, numbers, hyphens, and underscores.

        Args:
            v (str): The username to validate.

        Returns:
            str: The validated username.

        Raises:
            ValueError: If the username contains invalid characters.
        """
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError(
                "Имя пользователя должно содержать только буквы, цифры, дефисы и подчеркивания"
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate the email format.

        This method checks if the provided email has a valid format.

        Args:
            v (Optional[str]): The email address to validate.

        Returns:
            Optional[str]: The validated email if valid, otherwise raises an error.

        Raises:
            ValueError: If the email format is invalid.
        """
        if v is not None:
            # Regex to match a standard email format
            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
                raise ValueError("Неверный формат email")
        return v


class UserCreate(UserBase):
    """Модель создания пользователя с паролем"""

    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate the password.

        This method ensures that the password meets the security requirements,
        including a minimum length of 8 characters, at least one uppercase letter,
        one lowercase letter, and one digit.

        Args:
            v (str): The password to validate.

        Returns:
            str: The validated password.

        Raises:
            ValueError: If the password does not meet the security requirements.
        """
        # Check if the password length is at least 8 characters
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")

        # Check if the password contains at least one uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")

        # Check if the password contains at least one lowercase letter
        if not re.search(r"[a-z]", v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")

        # Check if the password contains at least one digit
        if not re.search(r"[0-9]", v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")

        return v


class UserLogin(BaseModel):
    """Модель входа в систему"""

    username: str
    password: str


class UserUpdate(BaseModel):
    """Модель обновления пользователя"""

    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate the email.

        This method checks if the provided email has a valid format.

        Args:
            v (Optional[str]): The email address to validate.

        Returns:
            Optional[str]: The validated email if valid, otherwise raises an error.

        Raises:
            ValueError: If the email format is invalid.
        """
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
                raise ValueError("Неверный формат email")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate the password.

        This method checks if the provided password has a valid format.

        Args:
            v (Optional[str]): The password to validate.

        Returns:
            Optional[str]: The validated password if valid, otherwise raises an error.

        Raises:
            ValueError: If the password does not meet the requirements.
        """
        if v is not None:
            # Check if the password length is at least 8 characters
            if len(v) < 8:
                raise ValueError("Пароль должен содержать минимум 8 символов")

            # Check if the password contains at least one uppercase letter
            if not re.search(r"[A-Z]", v):
                raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")

            # Check if the password contains at least one lowercase letter
            if not re.search(r"[a-z]", v):
                raise ValueError("Пароль должен содержать хотя бы одну строчную букву")

            # Check if the password contains at least one digit
            if not re.search(r"[0-9]", v):
                raise ValueError("Пароль должен содержать хотя бы одну цифру")
        return v


class User(UserBase):
    """Полная модель пользователя"""

    id: int

    model_config = ConfigDict(from_attributes=True)


class UserInDB(User):
    """Модель пользователя в базе данных с хешем пароля"""

    hashed_password: str


# --- Модели токенов ---


class Token(BaseModel):
    """Модель токена доступа"""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Данные, хранящиеся в токене"""

    sub: Optional[str] = None
    roles: List[str] = []
    exp: datetime


# --- Модели аудита ---


class AuditLog(BaseModel):
    """Модель записи в логе аудита"""

    id: int
    action: str
    entity: str
    entity_id: str
    user_id: int
    timestamp: datetime
    details: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogFilter(BaseModel):
    """Модель фильтра для записей аудита"""

    entity: Optional[str] = None
    action: Optional[str] = None
    user_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    skip: int = 0
    limit: int = 100


class OAuthAccountBase(BaseModel):
    """Базовая модель OAuth аккаунта"""

    provider: str
    provider_user_id: int
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )


class OAuthAccountCreate(OAuthAccountBase):
    """Модель создания OAuth аккаунта"""

    user_id: int


class OAuthAccount(OAuthAccountBase):
    """Полная модель OAuth аккаунта с ID"""

    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


# --- Модели платежей ---


class PaymentBase(BaseModel):
    """Базовая модель платежа"""

    order_id: str
    payment_provider: str = "paypal"
    payment_id: str
    amount: float
    currency: str = "USD"
    status: str
    details: Optional[str] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """
        Validate the amount of the payment.

        This method ensures that the amount of the payment is positive.

        Args:
            v (float): The amount of the payment to validate.

        Returns:
            float: The validated amount of the payment.

        Raises:
            ValueError: If the amount is not positive.
        """
        if v <= 0:
            raise ValueError("Сумма платежа должна быть положительной")
        return round(v, 2)


class PaymentCreate(PaymentBase):
    """Модель создания платежа"""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentUpdate(BaseModel):
    """Модель обновления платежа"""

    status: Optional[str] = None
    details: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )


class Payment(PaymentBase):
    """Полная модель платежа с ID"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Модель запроса на создание платежа ---


class CreatePaymentRequest(BaseModel):
    """Модель запроса на создание платежа"""

    amount: float
    currency: str = "USD"
    description: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """
        Validate the amount.

        This method ensures that the amount is positive and rounds it to two decimal places.

        Args:
            v (float): The amount to validate.

        Returns:
            float: The validated and rounded amount.

        Raises:
            ValueError: If the amount is not positive.
        """
        if v <= 0:
            raise ValueError("Сумма платежа должна быть положительной")
        return round(v, 2)


class PaymentResponse(BaseModel):
    """Модель ответа с информацией о созданном платеже"""

    order_id: str
    approve_url: str


# --- Модификация существующих моделей пользователя ---


class GoogleUserInfo(BaseModel):
    """Модель данных пользователя от Google OAuth"""

    email: str
    email_verified: bool = False
    name: Optional[str] = None
    picture: Optional[str] = None
    sub: str  # ID пользователя в Google


class SubscriptionPlanBase(BaseModel):
    """Базовая модель плана подписки"""

    name: str
    plan_type: Literal["monthly", "annual"]
    price: float
    description: Optional[str] = None
    features: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """
        Validate the price of the subscription plan.

        This method ensures that the price of the subscription plan is not negative.
        If the condition is not met, it raises a ValueError.

        Args:
            v (float): The price of the subscription plan to validate.

        Returns:
            float: The validated and rounded price of the subscription plan.
        """
        if v < 0:
            raise ValueError("Цена не может быть отрицательной")
        return round(v, 2)


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Модель создания плана подписки"""


class SubscriptionPlanUpdate(BaseModel):
    """Модель обновления плана подписки"""

    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    features: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate the price of the subscription plan.

        This method ensures that the price of the subscription plan is not negative.
        If the condition is not met, it raises a ValueError.

        Args:
            v (Optional[float]): The price of the subscription plan to validate.

        Returns:
            Optional[float]: The validated and rounded price of the subscription plan.
        """
        if v is not None:
            # Check if the price is negative
            if v < 0:
                raise ValueError("Цена не может быть отрицательной")
            # Round the price to two decimal places
            return round(v, 2)
        return v


class SubscriptionPlan(SubscriptionPlanBase):
    """Полная модель плана подписки с ID"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Модели подписок ---


class SubscriptionBase(BaseModel):
    """Базовая модель подписки"""

    user_id: int
    plan_type: Literal["monthly", "annual"]
    status: Literal["active", "expired", "cancelled", "pending"]
    start_date: datetime
    end_date: datetime
    auto_renew: bool = True
    amount: float

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """
        Validate the amount of the subscription.

        This method ensures that the amount of the subscription is not negative.
        If the condition is not met, it raises a ValueError.

        Args:
            v (float): The amount of the subscription to validate.

        Returns:
            float: The validated and rounded amount of the subscription.
        """
        if v < 0:
            raise ValueError("Сумма не может быть отрицательной")
        # Round the amount to two decimal places
        return round(v, 2)


class SubscriptionCreate(SubscriptionBase):
    """Модель создания подписки"""

    last_payment_id: Optional[str] = None
    next_payment_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SubscriptionUpdate(BaseModel):
    """Модель обновления подписки"""

    status: Optional[Literal["active", "expired", "cancelled", "pending"]] = None
    end_date: Optional[datetime] = None
    last_payment_id: Optional[str] = None
    next_payment_date: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )


class Subscription(SubscriptionBase):
    """Полная модель подписки с ID"""

    id: int
    last_payment_id: Optional[str] = None
    next_payment_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionRequest(BaseModel):
    """Модель запроса на создание подписки"""

    plan_id: int
    auto_renew: bool = True


class SubscriptionResponse(BaseModel):
    """Модель ответа с информацией о подписке и ссылкой на оплату"""

    subscription_id: int
    plan_name: str
    amount: float
    start_date: datetime
    end_date: datetime
    payment_url: str


class Warehouse(BaseModel):
    """Модель склада с ID"""

    id: Optional[int] = None
    user_id: int
    name: str
    location: str


class WarehouseCreate(BaseModel):
    """Модель создания склада"""

    name: str
    location: str
