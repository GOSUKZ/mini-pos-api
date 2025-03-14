from typing import List, Callable, Awaitable
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from core.database import DatabaseService
from services.product_service import ProductService
from core.models import User
from fastapi.security import OAuth2PasswordBearer
import logging
from config import get_settings
from services.auth_service import AuthService
from services.payment_service import PaymentService

logger = logging.getLogger("dependencies")

# Инициализация заголовка API-ключа
api_key_header = APIKeyHeader(name="X-API-Key")
# Существующие зависимости
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
settings = get_settings()

# Функции зависимостей для FastAPI
def get_db():
    """
    Получает соединение с базой данных из состояния приложения.
    Используется как зависимость.
    """
    from main import app
    return app.db

def get_db_service(db = Depends(get_db)):
    """
    Создает и возвращает сервис базы данных.
    Используется как зависимость.
    """
    return DatabaseService(db)

def get_product_service(db_service = Depends(get_db_service)):
    """
    Создает и возвращает сервис товаров.
    Используется как зависимость.
    """
    return ProductService(db_service)

def get_sync_auth_service(db_service = Depends(get_db_service)):
    """
    Создает и возвращает сервис аутентификации (синхронная версия).
    Используется как зависимость.
    """
    return AuthService(db_service)

async def get_auth_service(db_service = Depends(get_db_service)):
    """
    Создает и возвращает сервис аутентификации (асинхронная версия).
    Используется как зависимость.
    """
    return AuthService(db_service)

async def get_current_user(
    token: str = Security(api_key_header),
    auth_service: AuthService = Depends(get_sync_auth_service)
) -> User:
    """
    Получает текущего пользователя по токену.
    Используется как зависимость.

    Raises:
        HTTPException: Если токен недействителен или истек
    """
    user = await auth_service.get_current_user(token)

    if not user:
        logger.warning(f"Недействительные учетные данные: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return User(**user)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Проверяет, что текущий пользователь активен.
    Используется как зависимость.

    Raises:
        HTTPException: Если пользователь неактивен
    """
    if not current_user.is_active:
        logger.warning(f"Попытка доступа неактивного пользователя: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return current_user

def has_role(required_roles: List[str]) -> Callable[[User], Awaitable[User]]:
    """
    Создает зависимость для проверки ролей пользователя.

    Args:
        required_roles: Список необходимых ролей

    Returns:
        Функция зависимости, которая проверяет роли пользователя

    Raises:
        HTTPException: Если у пользователя нет необходимых ролей
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        for role in required_roles:
            if role in current_user.roles:
                return current_user

        logger.warning(f"Отказ в доступе пользователю {current_user.username}. Требуемые роли: {required_roles}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    return role_checker

def get_payment_service():
    """Dependency для получения экземпляра PaymentService."""
    return PaymentService()

# Удалите вызов get_auth_service() в конце файла
async def can_read_products(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Проверяет, что пользователь может читать данные о товарах.
    Любой активный и аутентифицированный пользователь имеет право на чтение.
    """
    return current_user