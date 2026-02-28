from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from fastapi import HTTPException, Depends, Request, Response
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config_app import settings
from src.core.config_log import logger
from src.db.models import User, UserToken
from src.db.database import get_db
from src.utils.token import TokenManager


class UserAuthenticator:
    """Сервис аутентификации User"""
    
    @staticmethod
    async def create_access_token(
        subject: str, 
        roles: list[str], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Создаёт JWT токен для пользователя."""
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        
        try:
            user_id = int(subject)
        except (ValueError, TypeError):
            raise ValueError("Subject должен быть числовым ID пользователя")

        payload = {
            "sub": str(user_id),
            "roles": roles,
            "iat": now,
            "exp": expire,
            "token_type": "bearer",
            "iss": settings.PROJECT_NAME,
            "aud": "user-api",
            "type": "access"
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    async def create_refresh_token(user_id: int, db: AsyncSession) -> tuple[str, str]:
        """
        Создаёт refresh token и сохраняет его в БД.
        Возвращает (raw_token, token_hash)
        """
        # Генерируем RAW refresh token
        raw_token = TokenManager.generate_token()
        token_hash = TokenManager.hash_token(raw_token)
        
        # Определяем время истечения
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        db_token = UserToken(
            user_id=user_id,
            token_hash=token_hash,
            token_type="refresh",
            expires_at=expires_at
        )
        db.add(db_token)
        await db.commit()
        
        logger.debug(f"Refresh token создан для user_id={user_id}")
        return raw_token, token_hash

    @staticmethod
    async def verify_refresh_token(token: str, db: AsyncSession) -> Optional[UserToken]:
        """
        Проверяет refresh token:
        1. Хеширует его и ищет в БД
        2. Проверяет срок действия
        3. Проверяет что не был использован
        """
        token_hash = TokenManager.hash_token(token)
        
        result = await db.execute(
            select(UserToken).where(
                (UserToken.token_hash == token_hash) &
                (UserToken.token_type == "refresh") &
                (UserToken.consumed_at.is_(None))
            )
        )
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            logger.warning(f"Refresh token не найден или уже использован")
            return None
        
        now = datetime.now(timezone.utc)
        if db_token.expires_at < now:
            logger.warning(f"Refresh token истёк для user_id={db_token.user_id}")
            return None
        
        return db_token

    @staticmethod
    async def set_auth_cookie(response: Response, token: str, cookie_name: str = "access_token") -> None:
        """Устанавливает куку авторизации"""
        print(settings.COOKIE_MODE)
        response.set_cookie(
            key=cookie_name,
            value=token,
            # Запрещает доступ к куке через JavaScript (защита от XSS-атак)
            httponly=True, 
            # Если True: разрешает передачу куки только через HTTPS. 
            # Важно: по HTTP кука может быть установлена браузером (через Set-Cookie), 
            # но не будет отправляться в последующих запросах (кроме исключения для localhost).
            secure=settings.COOKIE_MODE, 
            # Ограничивает передачу куки в сторонних запросах (защита от CSRF-атак)
            # "lax" — баланс безопасности и удобства (кука передается при переходе по ссылке)
            samesite="lax", 
            # Срок жизни куки в секундах
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 if cookie_name == "access_token" else settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
            # Дублирует срок жизни для старых браузеров
            expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 if cookie_name == "access_token" else settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

    @staticmethod
    async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
        credentials_exception = HTTPException(
            status_code=401,
            detail="Не удалось проверить учетные данные авторизации",
            headers={"WWW-Authenticate": "Bearer"}
        )
        # Извлекаем access token (Header -> Cookie)
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = request.cookies.get("access_token")

        if not token:
            raise credentials_exception

        payload = await TokenManager.decode_token(token)
        if not payload:
            raise credentials_exception

        token_type = payload.get("type")
        if token_type != "access":
            logger.warning(f"Использован неверный тип токена: {token_type}")
            raise credentials_exception

        user_id_str = payload.get("sub")
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise credentials_exception

        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user or user.is_deleted:
            logger.warning(f"Доступ запрещен для ID {user_id}")
            raise HTTPException(status_code=403, detail="Пользователь не найден или удален")

        return user
    
get_current_user =  UserAuthenticator.get_current_user