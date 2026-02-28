from fastapi import APIRouter, HTTPException, Depends, Request, Response
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config_app import settings
from src.core.config_log import logger
from src.db.models import User, UserStatus
from src.db.database import get_db
from src.cache.redis_service import redis_service
from src.auth.schemas import UserCreate, UserLogin, TokenResponse, RefreshTokenRequest
from src.auth.auth import UserAuthenticator, get_current_user
from src.utils.password import pwd_manager
from src.utils.token import TokenManager
from src.utils.decorators import rate_limit, security_headers_check
from src.utils.email import EmailService

router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=201)
@security_headers_check
@rate_limit(limit=3, period=60)
async def register(
    request: Request,
    user: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Регистрирует нового пользователя"""
    result = await db.execute(
        select(User).where(
            (User.user_email == user.user_email) | (User.user_login == user.user_login)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Электронная почта или логин уже зарегистрированы.")

    try:
        new_user = User(
            user_login=user.user_login,
            user_full_name=user.user_full_name,
            user_email=user.user_email,
            user_password_hash=pwd_manager.hash_password(user.user_password),
            role_id=3,
            status=UserStatus.REGISTERED,
            is_deleted=False,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        logger.error(f"Ошибка при сохранении пользователя: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера.")

    raw_refresh_token = None
    try:
        raw_token = await TokenManager.create_user_token(db, new_user.user_id, "email_verification", settings.TOKEN_TTL_SECONDS )
        await EmailService.send_verification_email(new_user.user_email, new_user.user_full_name, raw_token)
    except Exception as e:
        logger.error(f"Ошибка отправки письма на {new_user.user_email}: {e}.")

    try:
        await redis_service.cache_user_profile(user_obj=new_user, force=False)
    except Exception as e:
        logger.debug(f"Исключение при записи в Redis для user_id={new_user.user_id}: {e}.")

    try:
        access_token = await UserAuthenticator.create_access_token(subject=str(new_user.user_id), roles=[new_user.role_id])
        raw_refresh_token, _ = await UserAuthenticator.create_refresh_token(new_user.user_id, db)
        await UserAuthenticator.set_auth_cookie(response, access_token, cookie_name="access_token")
        await UserAuthenticator.set_auth_cookie(response, raw_refresh_token, cookie_name="refresh_token")
    except Exception as e:
        logger.error(f"Ошибка при создании/установке токенов для user_id={new_user.user_id}: {e}")

    logger.debug(f"Пользователь {user.user_login} успешно зарегистрирован.")
    return TokenResponse(
        detail="Подтвердите почту",
        refresh_token=raw_refresh_token or "",
    )


@router.get("/verify-email", response_model=dict,  status_code=200)
@security_headers_check
@rate_limit(limit=3, period=300)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Подтверждает email пользователя по токену из письма"""
    token_hash_val = TokenManager.hash_token(token)

    db_token = await TokenManager.get_token_by_hash(db, token_hash_val, "email_verification")
    
    is_valid, validation_reason = await TokenManager.is_token_valid(db_token)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Ошибка токена: {validation_reason}")

    result = await db.execute(select(User).where(User.user_id == db_token.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=400, detail="Пользователь не найден для данного токена.")

    db_user.status = UserStatus.ACTIVE
    await db.commit()
    await db.refresh(db_user)

    await TokenManager.consume_token(db, db_token)

    try:
        await redis_service.cache_user_profile(user_obj=db_user, force=True)
    except Exception as e:
        logger.debug(f"Исключение при записи в Redis для user_id={db_user.user_id}: {e}.")

    return {"detail": "Email успешно подтвержден."}


@router.post("/resend-verification", response_model=dict,  status_code=200)
@security_headers_check
@rate_limit(limit=3, period=180)
async def resend_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Повторный запрос на отправку письма с подтверждением email."""
    if current_user.status == UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Аккаунт уже подтверждён")

    max_retries = settings.TOKEN_RESEND_MAX
    window = settings.TOKEN_RESEND_WINDOW_SECONDS
    key = f"verif:resend:{current_user.user_id}"

    try:
        new_val = await redis_service.incr(key, amount=1, ttl=window)
    except Exception as e:
        logger.warning(f"Redis error during incr: {e}")
        new_val = None

    if new_val is None:
        logger.debug(f"Redis недоступен, пропускаем rate-limit для user_id={current_user.user_id}")
    else:
        if int(new_val) > max_retries:
            raise HTTPException(status_code=429, detail="Слишком много запросов, попробуйте позже.")

    try:
        raw_token = await TokenManager.create_user_token(db, current_user.user_id, "email_verification", settings.TOKEN_TTL_SECONDS)
    except Exception as e:
        logger.error(f"Ошибка создания токена подтверждения user_id={current_user.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Не удалось создать токен подтверждения")

    try:
        await EmailService.send_verification_email(current_user.user_email, current_user.user_full_name, raw_token)
    except Exception as e:
        logger.error(f"Не удалось отправить письмо подтверждения user_id={current_user.user_id}: {e}")

    return {"detail": "Письмо с подтверждением отправлено."}


@router.post("/login", response_model=TokenResponse, status_code=200)
@security_headers_check
@rate_limit(limit=5, period=60)
async def login(
    request: Request,
    user: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Аутентифицирует пользователя и выдаёт access + refresh токены.
    
    Access token живёт 15 минут и используется для всех запросов к API.
    Refresh token живёт 7 дней и используется для получения нового access token.
    """
    q = select(User).where(
        or_(
            User.user_login == user.user_identifier,
            User.user_email == user.user_identifier
        )
    )
    result = await db.execute(q)
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    if not pwd_manager.verify_password(user.password, db_user.user_password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    if db_user.status == UserStatus.REGISTERED:
        raise HTTPException(status_code=403, detail="Подтвердите email перед входом")
    elif db_user.status == UserStatus.BANNED:
        raise HTTPException(status_code=403, detail="Ваш аккаунт заблокирован")
    elif db_user.is_deleted:
        raise HTTPException(status_code=403, detail="Аккаунт удалён")

    try:
        access_token = await UserAuthenticator.create_access_token(
            subject=str(db_user.user_id), 
            roles=[db_user.role_id]
        )
        raw_refresh_token, _ = await UserAuthenticator.create_refresh_token(db_user.user_id, db)
        await UserAuthenticator.set_auth_cookie(response, access_token, cookie_name="access_token")
        await UserAuthenticator.set_auth_cookie(response, raw_refresh_token, cookie_name="refresh_token")

        try:
            await redis_service.cache_user_profile(user_obj=db_user, force=True)
        except Exception as e:
            logger.debug(f"Исключение при записи в Redis для user_id={db_user.user_id}: {e}")

        logger.info(f"Пользователь {db_user.user_login} успешно вошел в систему")
        
        return TokenResponse(
            detail="Вход выполнен успешно",
            refresh_token=raw_refresh_token,
        )

    except Exception as e:
        logger.error(f"Ошибка входа пользователя: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/refresh", response_model=TokenResponse, status_code=200)
@security_headers_check
@rate_limit(limit=10, period=60)
async def refresh_access_token(
    request: Request,
    refresh_req: RefreshTokenRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновляет access token используя refresh token.
    """

    refresh_token = refresh_req.refresh_token or request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token не предоставлен")
    
    db_token = await UserAuthenticator.verify_refresh_token(refresh_token, db)
    if not db_token:
        raise HTTPException(
            status_code=401, 
            detail="Refresh token истёк или отозван. Требуется повторная аутентификация."
        )
    
    result = await db.execute(select(User).where(User.user_id == db_token.user_id))
    user = result.scalar_one_or_none()
    
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="Пользователь не найден или удалён")
    
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Аккаунт неактивен")
    
    try:
        new_access_token = await UserAuthenticator.create_access_token(
            subject=str(user.user_id),
            roles=[user.role_id]
        )
        
        new_refresh_token, _ = await UserAuthenticator.create_refresh_token(user.user_id, db)
        
        from datetime import datetime, timezone
        db_token.consumed_at = datetime.now(timezone.utc)
        await db.commit()
        
        await UserAuthenticator.set_auth_cookie(response, new_access_token, cookie_name="access_token")
        await UserAuthenticator.set_auth_cookie(response, new_refresh_token, cookie_name="refresh_token")
        
        logger.debug(f"Access token обновлен для user_id={user.user_id}")
        
        return TokenResponse(
            detail="Токен успешно обновлён",
            refresh_token=new_refresh_token,
        )
        
    except Exception as e:
        logger.error(f"Ошибка обновления access token: {e}")
        raise HTTPException(status_code=500, detail="Не удалось обновить токен")


@router.post("/logout", response_model=dict, status_code=200)
@security_headers_check
@rate_limit(limit=10, period=60)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Выполняет logout пользователя:
    """
    from datetime import datetime, timezone
    from src.db.models import UserToken
    
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_MODE
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_MODE
    )
    
    try:
        stmt = select(UserToken).where(
            (UserToken.user_id == current_user.user_id) &
            (UserToken.token_type == "refresh") &
            (UserToken.consumed_at.is_(None))
        )
        result = await db.execute(stmt)
        tokens_to_revoke = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        for token in tokens_to_revoke:
            token.consumed_at = now
        
        await db.commit()
        logger.debug(f"Отозваны {len(tokens_to_revoke)} refresh токенов для user_id={current_user.user_id}")
    except Exception as e:
        logger.warning(f"Ошибка при отзыве refresh токенов user_id={current_user.user_id}: {e}")

    try:
        ok = await redis_service.delete(f"user:profile:{current_user.user_id}")
        if not ok:
            logger.debug(f"Не удалось удалить кэш для user_id={current_user.user_id} или Redis недоступен")
    except Exception as e:
        logger.debug(f"Исключение при удалении кэша для user_id={current_user.user_id}: {e}")

    logger.info(f"Пользователь {current_user.user_id} успешно вышел из системы")
    return {"detail": "Выход выполнен успешно"}
