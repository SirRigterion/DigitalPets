import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config_log import logger
from src.users.schemas import UserRestoreRequest
from src.db.models import User, UserStatus
from src.utils.password import pwd_manager
from src.cache.redis_service import redis_service


class UserService:
    """Сервис для управления пользователями"""

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int, user_is_deleted: bool = False) -> User:
        """Получить пользователя по ID."""
        result = await db.execute(
            select(User).where(User.user_id == user_id, User.is_deleted == user_is_deleted)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("Пользователь не найден или недоступен")
        return user

    @staticmethod
    async def validate_user_management(
        target_user: User,
        current_user: User,
        allow_self: bool = False,
        allow_admin: bool = False
    ) -> None:
        """Централизованная валидация прав доступа."""
        
        if target_user.user_id == 1:
            raise ValueError("Действия над главным администратором (ID=1) запрещены")

        if not allow_self and target_user.user_id == current_user.user_id:
            raise ValueError("Выполнять действие над собой в данном контексте запрещено")

        if not allow_admin and target_user.role_id == 1:
            raise ValueError("Недостаточно прав для управления администраторами")

    @staticmethod
    async def _update_and_sync_cache(db: AsyncSession, user_id: int, values: dict, is_deleted: bool = False) -> None:
        """Внутренний метод для обновления БД и инвалидации кэша."""
        
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(**values)
        )
        await db.commit()
        
        updated_user = await UserService.get_user_by_id(db, user_id, user_is_deleted=is_deleted)
        await redis_service.cache_user_profile(user_obj=updated_user, force=True)
     
    @staticmethod
    async def change_user_role(db: AsyncSession, target_id: int, new_role_id: int, current_id: int) -> None:
        """Изменить роль пользователя."""
        
        if new_role_id not in (1, 2, 3):
            raise ValueError("Указана несуществующая роль")

        target, current = await asyncio.gather(
            UserService.get_user_by_id(db, target_id),
            UserService.get_user_by_id(db, current_id)
        )

        await UserService.validate_user_management(target, current, allow_admin=True)
        await UserService._update_and_sync_cache(db, target_id, {"role_id": new_role_id})
        logger.info(f"Администратор {current_id} изменил роль пользователя {target_id} на {new_role_id}")

    @staticmethod
    async def ban_user(db: AsyncSession, target_id: int, current_id: int, reason: str = None, is_admin: bool = False) -> None:
        """Заблокировать пользователя."""
        
        target, current = await asyncio.gather(
            UserService.get_user_by_id(db, target_id),
            UserService.get_user_by_id(db, current_id)
        )

        if target.status == UserStatus.BANNED:
            raise ValueError("Пользователь уже заблокирован")

        if not is_admin and target.role_id != 3:
            raise ValueError("Модераторы могут блокировать только рядовых пользователей")

        await UserService.validate_user_management(target, current, allow_admin=is_admin)

        updates = {
            "status": UserStatus.BANNED,
            "ban_reason": reason,
            "banned_at": datetime.now(timezone.utc)
        }
        await UserService._update_and_sync_cache(db, target_id, updates)
        logger.info(f"User {current_id} banned {target_id}")

    @staticmethod
    async def unban_user(db: AsyncSession, target_id: int, current_id: int, is_admin: bool = False) -> None:
        """Разблокировать пользователя."""
        
        target, current = await asyncio.gather(
            UserService.get_user_by_id(db, target_id),
            UserService.get_user_by_id(db, current_id)
        )

        if target.status != UserStatus.BANNED:
            raise ValueError("Пользователь не находится в черном списке")

        if not is_admin and target.role_id != 3:
            raise ValueError("Ограничение прав модератора")

        await UserService.validate_user_management(target, current, allow_admin=is_admin)
        await UserService._update_and_sync_cache(db, target_id, {"status": UserStatus.ACTIVE})
        logger.info(f"User {current_id} unbanned {target_id}")

    @staticmethod
    async def delete_user(db: AsyncSession, target_id: int, current_id: int, is_admin: bool = False) -> None:
        """Мягкое удаление пользователя."""
        
        target, current = await asyncio.gather(
            UserService.get_user_by_id(db, target_id),
            UserService.get_user_by_id(db, current_id)
        )

        if not is_admin and target.role_id != 3:
            raise ValueError("Недостаточно прав для удаления")

        await UserService.validate_user_management(target, current, allow_admin=is_admin)
        await UserService._update_and_sync_cache(db, target_id, {"is_deleted": True}, is_deleted=True)
        logger.info(f"Пользователь {current_id} удалил пользователя {target_id}")

    @staticmethod
    async def restore_user(db: AsyncSession, target_id: int, current_id: int, is_admin: bool = False) -> None:
        """Восстановить удаленного пользователя."""
        
        target = await UserService.get_user_by_id(db, target_id, user_is_deleted=True)
        current = await UserService.get_user_by_id(db, current_id)

        if not is_admin and target.role_id != 3:
            raise ValueError("Недостаточно прав для восстановления")

        await UserService.validate_user_management(target, current, allow_admin=is_admin)
        await UserService._update_and_sync_cache(db, target_id, {"is_deleted": False}, is_deleted=False)
        logger.info(f"User {current_id} restored {target_id}")

    @staticmethod
    async def checking_moder_data(db: AsyncSession, target_id: int, data: UserRestoreRequest, is_deleted: bool = False) -> User:
        """Верификация данных пользователя (для процедур восстановления)."""
        
        target = await UserService.get_user_by_id(db, target_id, is_deleted)

        if target.user_full_name != data.full_name or target.user_login != data.login:
            raise ValueError("Персональные данные не совпадают")

        if not pwd_manager.verify_password(data.password, target.user_password_hash):
            raise ValueError("Указан неверный пароль")
        
        return target

    @staticmethod
    async def update_location(db: AsyncSession, user_id: int, latitude: float, longitude: float) -> User:
        """Обновить локацию пользователя (latitude, longitude)."""
        
        lat = float(latitude)
        lon = float(longitude)
        await db.execute(
            update(User).where(User.user_id == user_id).values(
                location_lat=lat,
                location_lon=lon,
                location_updated_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()
        updated = await UserService.get_user_by_id(db, user_id)
        await redis_service.cache_user_profile(user_obj=updated, force=True)
        return updated