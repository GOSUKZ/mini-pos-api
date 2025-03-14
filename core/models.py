from typing import Dict, List, Optional, Any, Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
import re
from datetime import datetime

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

    @field_validator('sku_code')
    @classmethod
    def validate_sku_code(cls, v: str) -> str:
        if not re.match(r'^[A-Za-z0-9-_]+$', v):
            raise ValueError('SKU код должен содержать только буквы, цифры, дефисы и подчеркивания')
        return v.upper()

    @field_validator('price', 'cost_price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        return round(v, 2)

    @model_validator(mode='after')
    def validate_prices(self) -> 'ProductBase':
        if self.price < self.cost_price:
            raise ValueError('Цена продажи не может быть ниже себестоимости')
        return self

class ProductCreate(ProductBase):
    """Модель создания товара"""
    pass

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

    @field_validator('sku_code')
    @classmethod
    def validate_sku_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^[A-Za-z0-9-_]+$', v):
                raise ValueError('SKU код должен содержать только буквы, цифры, дефисы и подчеркивания')
            return v.upper()
        return v

    @field_validator('cost_price', 'price')
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v < 0:
                raise ValueError('Цена не может быть отрицательной')
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

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError('Имя пользователя должно содержать только буквы, цифры, дефисы и подчеркивания')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Неверный формат email')
        return v

class UserCreate(UserBase):
    """Модель создания пользователя с паролем"""
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not re.search(r'[0-9]', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
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

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Неверный формат email')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) < 8:
                raise ValueError('Пароль должен содержать минимум 8 символов')
            if not re.search(r'[A-Z]', v):
                raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
            if not re.search(r'[a-z]', v):
                raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
            if not re.search(r'[0-9]', v):
                raise ValueError('Пароль должен содержать хотя бы одну цифру')
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
    user_id: str
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


from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime


# --- Модели OAuth аккаунтов ---

class OAuthAccountBase(BaseModel):
    """Базовая модель OAuth аккаунта"""
    provider: str
    provider_user_id: str
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

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Сумма платежа должна быть положительной')
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

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Сумма платежа должна быть положительной')
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
    plan_type: Literal['monthly', 'annual']
    price: float
    description: Optional[str] = None
    features: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Цена не может быть отрицательной')
        return round(v, 2)

class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Модель создания плана подписки"""
    pass

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

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v < 0:
                raise ValueError('Цена не может быть отрицательной')
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
    plan_type: Literal['monthly', 'annual']
    status: Literal['active', 'expired', 'cancelled', 'pending']
    start_date: datetime
    end_date: datetime
    auto_renew: bool = True
    amount: float

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_default=True,
    )

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Сумма не может быть отрицательной')
        return round(v, 2)

class SubscriptionCreate(SubscriptionBase):
    """Модель создания подписки"""
    last_payment_id: Optional[str] = None
    next_payment_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SubscriptionUpdate(BaseModel):
    """Модель обновления подписки"""
    status: Optional[Literal['active', 'expired', 'cancelled', 'pending']] = None
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

# --- Модели запросов на подписку ---

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