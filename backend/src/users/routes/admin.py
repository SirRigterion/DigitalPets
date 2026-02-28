from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.email import EmailService
from src.users.services import UserService
from src.db.models import User
from src.db.database import get_db
from src.utils.decorators import active_user_required, admin_required, security_headers_check
from src.auth import get_current_user
from src.core.config_log import logger

router = APIRouter()


@router.post("/promote/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@admin_required
@active_user_required
async def promote(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Повышает указанного пользователя до роли администратора (role_id=1)."""
    
    try:
        result = await db.execute(select(User).where(User.user_id == user_id))
        target_user = result.scalar_one_or_none()
        if not target_user:
            raise ValueError("Пользователь не найден")
        if target_user.user_id == current_user.user_id:
            raise ValueError("Нельзя изменять собственные права")
        if target_user.user_id == 1:
            raise ValueError("С пользователем с id=1 нельзя выполнять это действие")

        await db.execute(update(User).where(User.user_id == target_user.user_id).values(role_id=1))
        await db.commit()

        logger.info(f"[ADMIN] {current_user.user_id} повысил пользователя {target_user.user_id} до админа")
        return {"detail": "Пользователь повышен до админа"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADMIN] Неожиданная ошибка при повышении: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/set-role/{user_id}/{role_id}", response_model=dict,  status_code=200)
@security_headers_check
@admin_required
@active_user_required
async def set_role(
    request: Request,
    user_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Устанавливает произвольную роль пользователю."""
    
    try:
        result = await db.execute(select(User).where(User.user_id == user_id))
        target_user = result.scalar_one_or_none()
        if not target_user:
            raise ValueError("Пользователь не найден")
        if target_user.user_id == current_user.user_id:
            raise ValueError("Нельзя изменять собственные права")
        if target_user.user_id == 1:
            raise ValueError("С пользователем с id=1 нельзя выполнять это действие")
        if role_id not in (1, 2, 3):
            raise ValueError("Неверная роль")

        await db.execute(update(User).where(User.user_id == target_user.user_id).values(role_id=role_id))
        await db.commit()

        if target_user.role_id == 1:
            role_name = 'администратор'
        elif target_user.role_id == 2:
            role_name = 'модератор'
        elif target_user.role_id == 3:
            role_name = 'пользователь'
        else:
            role_name = 'ошибка'
                
        logger.info(f"[ADMIN] Роль пользователя (id = {target_user.user_id}) установлена: {role_name} ({role_id})")
        return {"detail": f"Роль пользователя (id = {target_user.user_id}) установлена: {role_name} ({role_id})"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADMIN] Неожиданная ошибка при установке роли: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/restore/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@admin_required
@active_user_required
async def restore_user_admin(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Восстанавливает восстановить пользователя (is_deleted=True)."""
    
    try:
        await UserService.restore_user(db, user_id, current_user.user_id, is_admin=True)
        logger.info(f"[ADMIN] Пользователь {current_user.user_id} восстановил пользователя {user_id}")
        return {"detail": "Пользователь восстановлен"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADMIN] Неожиданная ошибка при восстановлении: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.delete("/delete/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@admin_required
@active_user_required
async def delete_user_admin(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Помечает пользователя как удалённого (is_deleted=True)."""
    
    try:
        await UserService.delete_user(db, user_id, current_user.user_id, is_admin=True)
        logger.info(f"[ADMIN] Пользователь {current_user.user_id} удалил пользователя {user_id}")
        if current_user.user_email:
            await EmailService.send_delete_email(
                current_user.user_email, 
                current_user.user_full_name
            )
        return {"detail": "Пользователь удалён"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADMIN] Неожиданная ошибка при удалении: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/ban/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@admin_required
@active_user_required
async def ban_user(
        request: Request,
        user_id: int,
        reason: str = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Заблокировать пользователя"""
    
    try:
        await UserService.ban_user(db, user_id, current_user.user_id, reason, is_admin=True)
        logger.info(f"[ADMIN] Пользователь {current_user.user_id} заблокировал пользователя {user_id}")
        return {"detail": "Пользователь заблокирован"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADMIN] Неожиданная ошибка при блокировке: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")

@router.post("/unban/{user_id}", response_model=dict,  status_code=200)
@security_headers_check
@admin_required
@active_user_required
async def unban_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Разблокирует пользователя."""

    try:
        await UserService.unban_user(db, user_id, current_user.user_id, is_admin=True)
        logger.info(f"[ADMIN] Пользователь {current_user.user_id} разблокировал пользователя {user_id}")
        return {"detail": "Пользователь разблокирован."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ADMIN] Неожиданная ошибка при разблокировке: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
