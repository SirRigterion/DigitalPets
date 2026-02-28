import asyncio
import json
import time
from typing import Optional, Any, Union
import redis.asyncio as redis

from src.core.config_app import settings
from src.core.config_log import logger


class RedisService:
    """Сервис redis кэширования"""
    
    def __init__(self, url: str):
        self._url = url
        self._client: Optional[redis.Redis] = None
        self._last_ping_time = 0

    async def connect(self, max_attempts: int = 3) -> None:
        """Инициализация подключения к Redis (вызывается при старте приложения)."""
        attempt = 1
        while attempt <= max_attempts:
            try:
                client = redis.from_url(
                    self._url, 
                    decode_responses=False,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0
                )
                await asyncio.wait_for(client.ping(), timeout=5.0)
                self._client = client
                logger.info("Подключение успешно")
                return
            except Exception as e:
                logger.warning(f"Попытка {attempt}/{max_attempts} не удалась: {e}")
                self._client = None
                if attempt == max_attempts:
                    logger.error("Не удалось подключиться, работаем без кэша.")
                    return
                await asyncio.sleep(2)
                attempt += 1

    async def close(self):
        """Закрывает соединение корректно."""
        if self._client:
            try:
                await self._client.close()
                await self._client.connection_pool.disconnect()
            except Exception:
                pass
            finally:
                self._client = None
                logger.info("Соединение закрыто")

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def get_redis(self) -> Optional[redis.Redis]:
        """Возвращает живой клиент или None."""
        if self._client is None:
            return None
            
        now = time.time()
        if now - self._last_ping_time < 5:
            return self._client
    
        try:
            await asyncio.wait_for(self._client.ping(), timeout=1.0)
            self._last_ping_time = now
            return self._client
        except Exception as e:
            logger.error(f"Соединение потеряно: {e}")
            self._client = None
            return None

    # Низкоуровневые операции
    async def get_bytes(self, key: str) -> Optional[bytes]:
        client = await self.get_redis()
        if not client: return None
        try:
            return await client.get(key)
        except Exception as e:
            logger.error(f"Ошибка GET {key}: {e}")
            return None

    async def set_bytes(self, key: str, data: bytes, ttl: int) -> bool:
        client = await self.get_redis()
        if not client: return False
        try:
            await client.setex(key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"Ошибка SETEX {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        client = await self.get_redis()
        if not client: return False
        try:
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Ошибка DELETE {key}: {e}")
            return False

    async def incr(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
        client = await self.get_redis()
        if not client: return None
        try:
            async with client.pipeline(transaction=True) as pipe:
                pipe.incrby(key, amount)
                if ttl is not None:
                    pipe.expire(key, ttl)
                res = await pipe.execute()
                return int(res[0])
            return int(new_value)
        except Exception as e:
            logger.error(f"Ошибка INCR {key}: {e}")
            return None

    # Высокоуровневые операции
    async def get_json(self, key: str) -> Optional[Any]:
        """Получает и десериализует JSON."""
        raw = await self.get_bytes(key)
        if raw is None:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            logger.error(f"Ошибка десериализирования JSON {key}: {e}")
            return None

    async def set_json(self, key: str, obj: Any, ttl: int) -> bool:
        """Сериализует в JSON и сохраняет."""
        try:
            raw = json.dumps(obj, default=str, ensure_ascii=False).encode("utf-8")
            return await self.set_bytes(key, raw, ttl)
        except Exception as e:
            logger.error(f"Ошибка сериализирования JSON для {key}: {e}")
            return False

    async def set_nx(self, key: str, value: Union[bytes, str], ttl: int) -> bool:
        """Устанавливается если не существует (с TTL)."""
        client = await self.get_redis()
        if not client: return False
        try:
            res = await client.set(key, value, ex=int(ttl), nx=True)
            return bool(res)
        except Exception as e:
            logger.error(f"Ошибка SET NX {key}: {e}")
            return False


    async def cache_user_profile(
        self,
        user_obj: Any,
        cache_key: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """Кэширует профиль пользователя (NX по умолчанию, или Force update)."""
        from src.users.schemas import UserProfile
        
        try:
            profile = UserProfile.model_validate(user_obj)
            user_id = getattr(user_obj, "user_id")
            final_key = cache_key or f"user:profile:{user_id}"
            
            payload = json.dumps(profile.model_dump(by_alias=True), default=str).encode("utf-8")
            
            if force:
                return await self.set_bytes(final_key, payload, settings.REDIS_TTL)
            
            return await self.set_nx(final_key, payload, settings.REDIS_TTL)
            
        except Exception as e:
            logger.error(f"Ошибка кэширования профиля: {e}")
            return False
        

redis_service = RedisService(settings.REDIS_URL)
get_redis = redis_service.get_redis