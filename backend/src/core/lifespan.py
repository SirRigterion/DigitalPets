from sqlalchemy import select, text
from contextlib import asynccontextmanager
import asyncio

from src.core.config_app import settings
from src.core.config_log import logger
from src.db.models import Role, User, UserStatus
from src.db.database import db_helper
from src.utils.password import pwd_manager


async def seed_initial_data():
    """Создает необходимые роли и администратора при старте."""
    async with db_helper.session_factory() as session:
        # РОЛИ
        desired_roles = [
            {"role_id": 1, "role_name": "администратор"},
            {"role_id": 2, "role_name": "модератор"},
            {"role_id": 3, "role_name": "пользователь"},
        ]
        
        res = await session.execute(select(Role.role_id))
        existing_role_ids = set(res.scalars().all())

        for role_data in desired_roles:
            if role_data["role_id"] not in existing_role_ids:
                new_role = Role(**role_data)
                session.add(new_role)
                logger.info(f"Подготовлена к созданию роль: {role_data['role_name']}")

        # АДМИНИСТРАТОР
        res = await session.execute(select(User).where(User.user_id == 1))
        existing_admin = res.scalars().first()

        if not existing_admin:
            if not settings.ADMIN_PASSWORD:
                logger.warning("ADMIN_PASSWORD не задан в settings! Админ не будет создан.")
            else:
                hashed = pwd_manager.hash_password(settings.ADMIN_PASSWORD)
                
                admin_user = User(
                    user_id=1,
                    user_login="admin",
                    user_full_name="Админ Админов",
                    user_email=settings.ADMIN_EMAIL,
                    user_password_hash=hashed,
                    user_avatar=settings.ADMIN_IMAGES,
                    role_id=1,
                    status=UserStatus.ACTIVE,
                    is_deleted=False
                )
                session.add(admin_user)
                logger.info("Администратор (admin) подготовлен к созданию")
        
        await session.commit()
        await session.execute(text("""
            SELECT setval(
                pg_get_serial_sequence('users', 'user_id'),
                (SELECT COALESCE(MAX(user_id), 1) FROM users)
            );
        """))

        await session.execute(text("""
            SELECT setval(
                pg_get_serial_sequence('roles', 'role_id'),
                (SELECT COALESCE(MAX(role_id), 1) FROM roles)
            );
        """))

        await session.commit()