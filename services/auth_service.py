from datetime import datetime, timedelta
from http.client import HTTPException
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
from config import get_settings
import httpx
import jwt
from passlib.context import CryptContext
import logging
import os
from core.database import DatabaseService

logger = logging.getLogger("auth_service")
settings = get_settings()
# Константы
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI
GOOGLE_AUTH_URL = settings.GOOGLE_AUTH_URL
GOOGLE_TOKEN_URL = settings.GOOGLE_TOKEN_URL
GOOGLE_USER_INFO_URL = settings.GOOGLE_USER_INFO_URL
# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """
    Сервис для аутентификации и авторизации пользователей.
    """

    def __init__(self, db_service: DatabaseService):
        """
        Инициализирует сервис с сервисом базы данных.

        Args:
            db_service: Сервис базы данных
        """
        self.db_service = db_service

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверяет соответствие пароля его хешу.

        Args:
            plain_password: Пароль в открытом виде
            hashed_password: Хеш пароля

        Returns:
            True, если пароль соответствует хешу, иначе False
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Создает хеш пароля.

        Args:
            password: Пароль в открытом виде

        Returns:
            Хеш пароля
        """
        return pwd_context.hash(password)

    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Аутентифицирует пользователя по имени пользователя и паролю.

        Args:
            username: Имя пользователя
            password: Пароль в открытом виде

        Returns:
            Словарь с данными пользователя или None, если аутентификация не удалась
        """
        try:
            user = await self.db_service.get_user_by_username(username)

            if not user:
                logger.warning(f"Попытка аутентификации несуществующего пользователя: {username}")
                return None

            if not user.get("is_active", False):
                logger.warning(f"Попытка аутентификации неактивного пользователя: {username}")
                return None

            if not self.verify_password(password, user.get("hashed_password", "")):
                logger.warning(f"Неверный пароль для пользователя: {username}")
                return None

            # Записываем в аудит успешный вход
            await self.db_service.add_audit_log(
                action="login",
                entity="user",
                entity_id=username,
                user_id=username,
                details="Successful login"
            )

            return user
        except Exception as e:
            logger.error(f"Ошибка при аутентификации пользователя {username}: {str(e)}")
            raise

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Создает JWT токен доступа.

        Args:
            data: Данные для включения в токен
            expires_delta: Срок действия токена

        Returns:
            JWT токен
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})

        try:
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"Ошибка при создании токена: {str(e)}")
            raise

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Декодирует и проверяет JWT токен.

        Args:
            token: JWT токен

        Returns:
            Декодированные данные из токена или None при ошибке
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Токен с истекшим сроком действия")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Недействительный токен")
            return None
        except Exception as e:
            logger.error(f"Ошибка при декодировании токена: {str(e)}")
            return None

    async def get_current_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получает текущего пользователя по токену.

        Args:
            token: JWT токен

        Returns:
            Словарь с данными текущего пользователя или None, если токен недействителен
        """
        payload = self.decode_token(token)

        if not payload:
            return None

        username = payload.get("sub")

        if not username:
            return None

        try:
            user = await self.db_service.get_user_by_username(username)
            return user
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя по токену: {str(e)}")
            return None

    def check_permissions(
        self,
        user: Dict[str, Any],
        required_roles: List[str]
    ) -> bool:
        """
        Проверяет, имеет ли пользователь необходимые роли.

        Args:
            user: Словарь с данными пользователя
            required_roles: Список необходимых ролей

        Returns:
            True, если пользователь имеет необходимые роли, иначе False
        """
        if not user:
            return False

        if not user.get("is_active", False):
            return False

        user_roles = user.get("roles", [])

        for role in required_roles:
            if role in user_roles:
                return True

        return False

    async def register_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        roles: List[str] = ["user"]
    ) -> Dict[str, Any]:
        """
        Регистрирует нового пользователя.

        Args:
            username: Имя пользователя
            password: Пароль в открытом виде
            email: Email пользователя
            roles: Список ролей пользователя

        Returns:
            Словарь с данными зарегистрированного пользователя

        Raises:
            ValueError: Если пользователь с таким именем уже существует
        """
        try:
            # Проверяем, существует ли пользователь
            existing_user = await self.db_service.get_user_by_username(username)

            if existing_user:
                raise ValueError(f"User with username '{username}' already exists")

            # Создаем хеш пароля
            hashed_password = self.get_password_hash(password)

            # Создаем пользователя
            user_data = {
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
                "is_active": True,
                "roles": roles
            }

            user = await self.db_service.create_user(user_data)

            # Записываем в аудит
            await self.db_service.add_audit_log(
                action="create",
                entity="user",
                entity_id=username,
                user_id="system",
                details="User registration"
            )

            return user
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя {username}: {str(e)}")
            raise

    async def get_google_auth_url(self) -> str:
        """Генерирует URL для авторизации через Google."""
        params = {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
            "response_type": "code",
            "scope": "email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{os.getenv("GOOGLE_AUTH_URL")}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """Обменивает код авторизации на токен доступа."""
        data = {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get token from Google")

        return response.json()

    async def get_user_info(self, token: str) -> Dict:
        """Получает информацию о пользователе из Google API."""
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(GOOGLE_USER_INFO_URL, headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        return response.json()

    async def authenticate_with_google(self, code: str) -> Dict:
        """Полный процесс аутентификации через Google."""
        # Получение токена
        token_data = await self.exchange_code_for_token(code)
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")

        # Получение информации о пользователе
        user_info = await self.get_user_info(access_token)

        # Проверка наличия email
        email = user_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        # Найти пользователя в базе данных или создать нового
        user = await self.get_user_by_email(email)

        if not user:
            # Создаем нового пользователя
            new_user_data = {
                "email": email,
                "name": user_info.get("name", ""),
                "picture": user_info.get("picture", ""),
                "is_verified": user_info.get("email_verified", False),
                "auth_provider": "google"
            }
            user = await self.create_user(new_user_data)

        # Генерация JWT токена
        tokens = self.create_tokens({"user_id": str(user["id"]), "email": user["email"]})

        return {
            "user": user,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"]
        }