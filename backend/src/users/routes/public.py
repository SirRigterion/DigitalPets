from typing import Optional, List
from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.db.database import get_db
from src.db.models import User
from src.users.schemas import UserProfile
from src.core.config_log import logger
from src.utils.decorators import active_user_required, rate_limit, security_headers_check, cache
from src.core.exceptions import ValidationError, AuthorizationError, NotFoundError, InternalServerError


router = APIRouter()

@router.get("/search", response_model=List[UserProfile])
@security_headers_check
@rate_limit(limit=10, period=60)
@active_user_required
@cache(ttl=300, key_prefix="user_search")
async def search_users(
    request: Request,
    user_login: Optional[str] = None,
    user_full_name: Optional[str] = None,
    user_email: Optional[str] = None,
    role_id: Optional[int] = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Поиск пользователей с динамическими фильтрами и кэшированием результатов."""
    
    if not (1 <= limit <= 100):
        raise ValidationError("Лимит должен быть в диапазоне 1-100", field="limit")
    if offset < 0:
        raise ValidationError("Offset не может быть отрицательным", field="offset")

    query = select(User).where(User.is_deleted == False)

    if user_login:
        login_val = user_login.strip()[:50]
        if len(login_val) < 2:
            raise ValidationError("Минимум 2 символа для поиска по логину", field="user_login")
        query = query.filter(User.user_login.ilike(f"%{login_val}%"))

    if user_full_name:
        name_val = user_full_name.strip()[:100]
        if len(name_val) < 2:
            raise ValidationError("Минимум 2 символа для поиска по имени", field="user_full_name")
        query = query.filter(User.user_full_name.ilike(f"%{name_val}%"))

    is_privileged = current_user.role_id in (1, 2)

    if user_email:
        if not is_privileged:
            raise AuthorizationError("Поиск по email доступен только администрации")
        email_val = user_email.strip()[:100]
        if len(email_val) < 3:
            raise ValidationError("Минимум 3 символа для поиска по email", field="user_email")
        query = query.filter(User.user_email.ilike(f"%{email_val}%"))

    if role_id:
        if not is_privileged:
            raise AuthorizationError("Фильтр по роли доступен только администрации")
        if role_id not in (1, 2, 3):
            raise ValidationError("Некорректный ID роли", field="role_id")
        query = query.filter(User.role_id == role_id)

    try:
        result = await db.execute(query.order_by(User.user_login).limit(limit).offset(offset))
        users = result.scalars().all()
        return [UserProfile.model_validate(u) for u in users]
    except Exception as e:
        logger.error(f"Ошибка поиска пользователей: {e}")
        raise InternalServerError("Ошибка при выполнении поиска")


@router.get("/{user_id}", response_model=UserProfile)
@security_headers_check
@rate_limit(limit=20, period=60)
@active_user_required
@cache(ttl=600, key_prefix="user_profile_view")
async def get_user_profile(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получение профиля любого пользователя по ID с кэшированием."""

    if user_id <= 0:
        raise ValidationError("ID должен быть положительным числом", field="user_id")

    try:
        query = select(User).where(User.user_id == user_id, User.is_deleted == False)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("Пользователь не найден")

        return UserProfile.model_validate(user)
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise e
        logger.error(f"Ошибка получения профиля пользователя (ID {user_id}): {e}")
        raise InternalServerError("Ошибка при получении профиля")