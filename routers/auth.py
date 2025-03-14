from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
import logging
from utils.dependencies import get_auth_service
from services.auth_service import AuthService
from core.models import UserCreate, UserLogin, Token
from config import get_settings
from fastapi import APIRouter, Depends, Request, HTTPException, Response
from fastapi.responses import RedirectResponse
from utils.dependencies import get_auth_service

logger = logging.getLogger("auth_router")
settings = get_settings()

# Создаем роутер
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={401: {"description": "Unauthorized"}},
)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Регистрация нового пользователя.
    """
    logger.info(f"Регистрация нового пользователя: {user_data.username}")

    try:
        user = await auth_service.register_user(
            username=user_data.username,
            password=user_data.password,
            email=user_data.email,
            roles=user_data.roles
        )

        return {"message": "User registered successfully", "username": user.get("username")}
    except ValueError as e:
        logger.warning(f"Ошибка при регистрации пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Получение токена доступа.
    """
    logger.info(f"Запрос токена для пользователя: {form_data.username}")

    try:
        user = await auth_service.authenticate_user(
            username=form_data.username,
            password=form_data.password
        )

        if not user:
            logger.warning(f"Неудачная попытка аутентификации для пользователя: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": user.get("username"), "roles": user.get("roles", [])},
            expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при аутентификации пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/google/login")
async def google_login(auth_service: AuthService = Depends(get_auth_service)):
    """Генерирует URL для авторизации через Google и перенаправляет на него."""
    auth_url = await auth_service.get_google_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
        code: str,
        auth_service: AuthService = Depends(get_auth_service),
        response: Response = None
):
    """Обрабатывает callback от Google OAuth."""
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided")

    # Аутентификация через Google
    auth_result = await auth_service.authenticate_with_google(code)

    # Установка cookies с токенами (опционально)
    if response:
        response.set_cookie(
            key="access_token",
            value=auth_result["access_token"],
            httponly=True,
            max_age=1800,  # 30 минут
            secure=True,
            samesite="lax"
        )
        response.set_cookie(
            key="refresh_token",
            value=auth_result["refresh_token"],
            httponly=True,
            max_age=604800,  # 7 дней
            secure=True,
            samesite="lax"
        )

    # Возвращаем токены и информацию о пользователе
    return {
        "access_token": auth_result["access_token"],
        "refresh_token": auth_result["refresh_token"],
        "user": auth_result["user"]
    }