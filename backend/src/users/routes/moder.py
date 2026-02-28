from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.email import EmailService
from src.users.services import UserService
from src.db.database import get_db
from src.db.models import User
from src.users.schemas import UserRestoreRequest
from src.utils.decorators import rate_limit, security_headers_check, moder_required, active_user_required
from src.auth import get_current_user
from src.core.config_log import logger


router = APIRouter()

@router.post("/restore/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@rate_limit(limit=5, period=60)
@moder_required
@active_user_required
async def restore_user_moder(
    request: Request,
    user_id: int,
    data: UserRestoreRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Восстанавливает восстановить пользователя (is_deleted=True). Нужны данные пользователя."""
    
    try:
        target_user = await UserService.get_user_by_id(db, user_id, user_is_deleted=True)
        if target_user.role_id != 3:
            raise ValueError("Модераторы могут восстанавливать только обычных пользователей")
        
        await UserService.checking_moder_data(db, user_id, data, is_deleted=True)
        await UserService.restore_user(db, user_id, current_user.user_id, is_admin=False)
        logger.info(f"[MODER] Пользователь {current_user.user_id} восстановил пользователя {user_id}")
        return {"detail": "Пользователь восстановлен"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[MODER] Неожиданная ошибка при восстановлении: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/delete/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@rate_limit(limit=5, period=60)
@moder_required
@active_user_required
async def delete_user_moder(
    request: Request,
    user_id: int,
    data: UserRestoreRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Помечает пользователя как удалённого (is_deleted=True). Требует данные пользователя."""
    
    try:
        target_user = await UserService.get_user_by_id(db, user_id)
        if target_user.role_id != 3:
            raise ValueError("Модераторы могут удалять только обычных пользователей")

        await UserService.checking_moder_data(db, user_id, data)
        await UserService.delete_user(db, user_id, current_user.user_id, is_admin=False)
        logger.info(f"[MODER] Пользователь {current_user.user_id} удалил пользователя {user_id}")
        if current_user.user_email:
            await EmailService.send_delete_email(
                current_user.user_email, 
                current_user.user_full_name
            )
        return {"detail": "Пользователь удалён"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[MODER] Неожиданная ошибка при удалении: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/ban/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@rate_limit(limit=5, period=60)
@moder_required
@active_user_required
async def ban_user(
        request: Request,
        user_id: int,
        data: UserRestoreRequest = Body(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        reason: str = None,
):
    """Заблокировать пользователя. Требует обязательную проверку данных (логин, пароль, почта)."""
    
    try:
        target_user = await UserService.get_user_by_id(db, user_id)
        if target_user.role_id != 3:
            raise ValueError("Модераторы могут блокировать только обычных пользователей")

        await UserService.checking_moder_data(db, user_id, data)
        await UserService.ban_user(db, user_id, current_user.user_id, reason, is_admin=False)
        logger.info(f"[MODER] Пользователь {current_user.user_id} заблокировал пользователя {user_id}")
        return {"detail": "Пользователь заблокирован"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[MODER] Неожиданная ошибка при блокировке: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/unban/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@rate_limit(limit=5, period=60)
@moder_required
@active_user_required
async def unban_user(
    request: Request,
    user_id: int,
    data: UserRestoreRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Разблокирует пользователя. Требует обязательную проверку данных (логин, пароль, почта)."""

    try:
        target_user = await UserService.get_user_by_id(db, user_id)
        
        if target_user.role_id != 3:
            raise ValueError("Модераторы могут разблокировать только обычных пользователей")

        await UserService.checking_moder_data(db, user_id, data)
        await UserService.unban_user(db, user_id, current_user.user_id, is_admin=False)
        logger.info(f"[MODER] Пользователь {current_user.user_id} разблокировал пользователя {user_id}")
        return {"detail": "Пользователь разблокирован."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[MODER] Неожиданная ошибка при разблокировке: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
