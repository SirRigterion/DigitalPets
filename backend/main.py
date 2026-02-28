import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config_app import settings
from src.core.config_log import logger
from src.core.exceptions import setup_exception_handlers
from src.users.routes import profile_router, public_router, admin_router, moder_router
from src.auth.routes import router as auth_router
from src.images.routes import router as img_router
from src.chat.routes import chat_router
from src.chat.routes import message_router
from src.pet.routes import pet_router
from src.weather.routes import weather_router
from src.chat.ws_routes import ws_router
from src.pet.background_tasks import run_pet_decay_task, run_pet_auto_messages_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    logger.info("Запуск приложения")
    
    try:
        from src.db.database import db_helper
        await db_helper.check_connection()
        logger.info("БД подключена")
    except Exception as e:
        logger.error(f"Ошибка подключения БД: {e}")
        raise

    try:
        from src.cache.redis_service import redis_service
        await redis_service.connect()
        if redis_service.is_connected:
            logger.info("Redis подключен")
        else:
            logger.warning("Redis недоступен, кэширование отключено")
    except Exception as e:
        logger.warning(f"Redis ошибка: {e}")

    try:
        from src.core.lifespan import seed_initial_data
        await seed_initial_data()
        logger.info("Начальные данные загружены")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        raise
    
    # Запускаем фоновые задачи
    pet_decay_task = asyncio.create_task(run_pet_decay_task())
    pet_auto_msg_task = asyncio.create_task(run_pet_auto_messages_task())
    logger.info("Фоновые задачи управления питомцами запущены")
    
    try:
        yield  # Приложение работает здесь
    finally:
        logger.info("Остановка приложения")
        
        # Отменяем фоновые задачи
        pet_decay_task.cancel()
        pet_auto_msg_task.cancel()
        try:
            await pet_decay_task
        except asyncio.CancelledError:
            logger.info("Задача снижения характеристик отменена")
        try:
            await pet_auto_msg_task
        except asyncio.CancelledError:
            logger.info("Задача автоматических сообщений отменена")
            
        try:
            await redis_service.close()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии Redis: {e}")

        try:
            await db_helper.dispose()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии БД: {e}")
        
        logger.info("Приложение остановлено")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_exception_handlers(app)

try:
    # Аутентификация
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

    # Пользователи
    app.include_router(profile_router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(public_router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(moder_router, prefix="/api/v1/moder", tags=["Moderator"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
    
    app.include_router(chat_router, prefix="/api/v1/chats", tags=["Chats"])
    app.include_router(message_router, prefix="/api/v1/chats/messages", tags=["Messages"])
    app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

    # Изображения
    app.include_router(img_router, prefix="/api/v1/images", tags=["Images"])
    
    # Питомцы
    app.include_router(pet_router, prefix="/api/v1/pets", tags=["Pets"])
    
    # Погода
    app.include_router(weather_router, prefix="/api/v1/weather", tags=["Weather"])
except Exception as e:
    logger.warning(f"Ошибка подключения routes: {e}")


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Проверка здоровья приложения."""
    return {
        "status": "ok",
        "version": settings.PROJECT_VERSION,
        "service": settings.PROJECT_NAME
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1,
        log_level="info"
    )