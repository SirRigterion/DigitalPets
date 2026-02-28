import uuid
import hashlib
from jose import JWTError, jwt
from sqlalchemy import select, update
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config_app import settings
from src.core.config_log import logger
from src.db.models import UserToken


class TokenManager:
    """Менеджер для низкоуровневой работы с JWT и Opaque токенами."""

    @staticmethod
    def generate_token() -> str:
        """Генерирует случайный токен (UUID4)."""
        
        return str(uuid.uuid4())

    @staticmethod
    def hash_token(token: str) -> str:
        """SHA-256 hex хеш."""
        
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
 
    @staticmethod
    async def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Декодирует JWT токен и проверяет метаданные."""
        
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                audience="user-api",
                issuer=settings.PROJECT_NAME,
            )
            if payload.get("token_type") != "bearer":
                return None
            return payload
        except JWTError as e:
            logger.warning(f"Ошибка JWT декодирования: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при декодировании JWT: {e}")
            return None
        
    @staticmethod
    async def get_token_by_hash(
        db: AsyncSession, 
        token_hash: str, 
        token_type: str
    ) -> Optional[UserToken]:
        """Найти токен в базе данных по его хэшу и типу."""
        
        query = select(UserToken).where(
            UserToken.token_hash == token_hash, 
            UserToken.token_type == token_type
        )
        result = await db.execute(query)
        return result.scalars().first()
        
    @staticmethod
    async def is_token_valid(token: Optional[UserToken]) -> Tuple[bool, str]:
        """Проверяет валидность токена (существование, срок действия, отзыв)."""
        
        if token is None:
            return False, "Token not found"

        now = datetime.now(timezone.utc)

        if token.expires_at < now:
            return False, "Token expired"

        if token.consumed_at is not None:
            return False, "Token revoked"

        return True, "OK"

    @staticmethod
    async def consume_token(db: AsyncSession, token: UserToken) -> None:
        """Отметить токен как использованный (ревокация)."""
        
        now = datetime.now(timezone.utc)
        await db.execute(
            update(UserToken)
            .where(UserToken.token_id == token.token_id)
            .values(consumed_at=now)
        )
        await db.commit()
        
    @staticmethod
    async def create_user_token(
        db: AsyncSession,
        user_id: int,
        token_type: str,
        ttl: int
    ) -> str:
        """
        Создаёт запись UserToken, возвращает raw_token
        """
        
        raw = TokenManager.generate_token()
        token_hash = TokenManager.hash_token(raw)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        token = UserToken(
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            requested_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            consumed_at=None
        )
        db.add(token)
        await db.commit()
        await db.refresh(token)
        return raw
