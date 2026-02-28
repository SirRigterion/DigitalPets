import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
import random
from datetime import datetime, timedelta

from src.pet.services import get_pet_service
from src.utils.email import EmailService
from src.db.models import Pet, User, PetCharacter, PetFeature, UserStatus, Chat, Message, MessageType, PetState
from src.core.config_log import logger
from src.core.config_app import settings
from src.db.database import db_helper
from src.weather.routes import _fetch_weather
from src.ai.yandex_service import ai_service


# Таблица множителей для характера питомца
CHARACTER_MULTIPLIERS: Dict[PetCharacter, Dict[str, float]] = {
    PetCharacter.PLAYFUL: {"hunger": 1.0, "energy": 0.6, "happiness": 0.8},
    PetCharacter.LAZY: {"hunger": 0.8, "energy": 1.3, "happiness": 1.0},
    PetCharacter.ENERGETIC: {"hunger": 1.3, "energy": 0.5, "happiness": 0.7},
    PetCharacter.CURIOUS: {"hunger": 1.0, "energy": 0.9, "happiness": 0.9},
    PetCharacter.SHY: {"hunger": 0.9, "energy": 1.0, "happiness": 1.2},
}

# Таблица множителей для погоды и особенностей питомца
WEATHER_FEATURE_MULTIPLIERS: Dict[str, Dict[PetFeature, float]] = {
    "rain": {
        PetFeature.RAIN_LOVER: 0.7,      # Любит дождь - меньше штрафа
        PetFeature.RAIN_HATER: 1.5,      # Ненавидит дождь - больше штрафа
        PetFeature.NORMAL: 1.0,
        PetFeature.COLD_LOVER: 1.0,
        PetFeature.DAY_LOVER: 1.0,
        PetFeature.HOT_HATER: 1.0,
        PetFeature.SUN_HATER: 1.0,
    },
    "cold": {
        PetFeature.COLD_LOVER: 0.7,
        PetFeature.HOT_HATER: 0.8,
        PetFeature.NORMAL: 1.0,
        PetFeature.RAIN_LOVER: 1.0,
        PetFeature.RAIN_HATER: 1.0,
        PetFeature.DAY_LOVER: 1.0,
        PetFeature.SUN_HATER: 1.0,
    },
    "clear": {
        PetFeature.DAY_LOVER: 0.8,
        PetFeature.SUN_HATER: 1.3,
        PetFeature.HOT_HATER: 1.0,
        PetFeature.NORMAL: 1.0,
        PetFeature.RAIN_LOVER: 1.0,
        PetFeature.RAIN_HATER: 1.0,
        PetFeature.COLD_LOVER: 1.0,
    },
    "hot": {
        PetFeature.HOT_HATER: 1.5,
        PetFeature.COLD_LOVER: 1.2,
        PetFeature.NORMAL: 1.0,
        PetFeature.RAIN_LOVER: 1.0,
        PetFeature.RAIN_HATER: 1.0,
        PetFeature.DAY_LOVER: 1.0,
        PetFeature.SUN_HATER: 1.0,
    },
}


def _categorize_weather(description: str) -> str:
    """Категоризирует погоду в 4 типа: rain, cold, clear, hot."""
    desc_lower = description.lower()
    
    if any(word in desc_lower for word in ["rain", "дождь", "thunderstorm", "гроза"]):
        return "rain"
    elif any(word in desc_lower for word in ["snow", "снег", "cold", "холодно"]):
        return "cold"
    elif any(word in desc_lower for word in ["clear", "sunny", "ясно", "солнечно"]):
        return "clear"
    elif any(word in desc_lower for word in ["hot", "warm", "жарко", "тепло"]):
        return "hot"
    
    return "clear"  # По умолчанию


def _calculate_stat_reduction(
    base_reduction: float,
    character: PetCharacter,
    feature: PetFeature,
    weather_type: str,
    stat_name: str,
    pet_state: Optional[PetState] = None,
    pet_cleanliness: Optional[float] = None,
) -> float:
    """
    Рассчитывает снижение характеристики с учетом характера и погоды.
    
    Args:
        base_reduction: базовое снижение (обычно 1.0)
        character: характер питомца
        feature: особенность питомца
        weather_type: тип погоды (rain, cold, clear, hot)
        stat_name: название статистики (hunger, energy, happiness)
    
    Returns:
        Значение снижения с учетом всех множителей
    """
    # Множитель от характера питомца
    char_mult = CHARACTER_MULTIPLIERS.get(character, {}).get(stat_name, 1.0)
    # Множитель от состояния питомца (сон/игра/боль/грусть/нейтрал)
    state_mult = 1.0
    if pet_state is not None:
        state_mults = _get_stat_multipliers_by_state(pet_state)
        state_mult = state_mults.get(stat_name, 1.0)
    
    # Множитель от погоды и особенности
    weather_mults = WEATHER_FEATURE_MULTIPLIERS.get(weather_type, {})
    weather_mult = weather_mults.get(feature, 1.0)
    
    # Итоговое снижение
    reduction = base_reduction * char_mult * weather_mult * state_mult

    # Влияние чистоты питомца: грязный питомец теряет параметры сильнее,
    # чистый — медленнее. pet_cleanliness в 0..100, 50 — нейтрально.
    if pet_cleanliness is not None:
        try:
            clean = float(pet_cleanliness)
        except Exception:
            clean = 50.0
        # фактор: cleanliness=50 -> 1.0; cleanliness=0 -> 1.5; cleanliness=100 -> 0.5
        cleanliness_factor = 1.0 + (50.0 - max(0.0, min(100.0, clean))) / 100.0
        reduction = reduction * cleanliness_factor
    
    logger.debug(
        f"Расчет снижения {stat_name}: "
        f"базовое={base_reduction}, "
        f"char_mult={char_mult}, "
        f"state_mult={state_mult}, "
        f"weather_mult={weather_mult}, "
        f"cleanliness_factor={locals().get('cleanliness_factor', 1.0):.2f}, "
        f"итого={reduction:.2f}"
    )
    
    return reduction


async def _get_weather_for_user(db: AsyncSession, user_id: int) -> Optional[str]:
    """Получает описание погоды по локации пользователя."""
    try:
        user = await db.get(User, user_id)
        if not user or not user.location_lat or not user.location_lon:
            return None
        
        weather_data = await _fetch_weather(user.location_lat, user.location_lon)
        if weather_data:
            # WeatherResponse — pydantic object, используем атрибуты
            return getattr(weather_data, "description", "clear")
        return None
    except Exception as e:
        logger.error(f"Ошибка получения погоды для user_id={user_id}: {e}")
        return None


def _get_current_pet_state(current_hour: int) -> PetState:
    """
    Определяет состояние питомца на основе времени суток.
    22:00–8:00 → SLEEP
    16:00–19:00 → PLAY
    Остальное → NEUTRAL
    Timezone UTC
    """
    if 19 <= current_hour or current_hour < 5:
        return PetState.SLEEP
    elif 13 <= current_hour < 16:
        return PetState.PLAY
    else:
        return PetState.NEUTRAL


def _get_stat_multipliers_by_state(state: PetState) -> Dict[str, float]:
    """
    Возвращает множители снижения для каждого состояния.
    Формат: {"hunger": mult, "energy": mult, "happiness": mult, "health": mult}
    """
    multipliers = {
        PetState.SLEEP: {
            "hunger": 0.5,      # медленнее теряет голод
            "energy": -0.5,     # восстанавливает энергию (отрицательное значение)
            "happiness": 0.3,   # медленнее теряет счастье
            "health": 0.0,      # не теряет здоровье во сне
        },
        PetState.PLAY: {
            "hunger": 1.0,      # обычно теряет голод
            "energy": 1.5,      # быстрее теряет энергию
            "happiness": 0.5,   # медленнее теряет счастье (восстанавливается от игры)
            "health": 0.0,      # не теряет здоровье при игре
        },
        PetState.NEUTRAL: {
            "hunger": 1.0,      # обычное снижение
            "energy": 1.0,      # обычное снижение
            "happiness": 1.0,   # обычное снижение
            "health": 0.0,      # не теряет здоровье в нормальном состоянии
        },
        PetState.SAD: {
            "hunger": 1.0,      # обычно теряет
            "energy": 1.0,      # обычно теряет
            "happiness": 1.5,   # быстрее теряет счастье
            "health": 0.5,      # слегка теряет здоровье
        },
        PetState.SICK1: {
            "hunger": 0.5,      # медленнее теряет голод
            "energy": 0.5,      # медленнее теряет энергию
            "happiness": 1.2,   # быстрее теряет счастье (болезнь угнетает)
            "health": 0.5,      # +0.5 потери здоровья за интервал
        },
        PetState.SICK2: {
            "hunger": 0.5,      # медленнее теряет голод
            "energy": 0.5,      # медленнее теряет энергию
            "happiness": 1.2,   # быстрее теряет счастье
            "health": 1.0,      # +1.0 потери здоровья за интервал
        },
        PetState.SICK3: {
            "hunger": 0.5,      # медленнее теряет голод
            "energy": 0.5,      # медленнее теряет энергию
            "happiness": 1.2,   # быстрее теряет счастье
            "health": 2.0,      # +2.0 потери здоровья за интервал
        },
    }
    return multipliers.get(state, multipliers[PetState.NEUTRAL])

async def process_pet_stats_decay(db: AsyncSession) -> None:
    """
    Основная функция рассчитывает периодическое снижение характеристик питомцев (голод, энергия, счастье, здоровье).

    Логика работы:
    1. Определяет базовое состояние (Sleep/Play) по текущему времени суток.
    2. Проверяет и обновляет статусы болезней.
    3. Учитывает внешние модификаторы: погоду, характер и особенности питомца.
    4. Применяет дельту снижения к характеристикам в диапазоне [0.0, 100.0].
    5. Группирует уведомления: если показатели критичны, формирует список имен и отправляет владельцу одно суммарное Email-оповещение.
    """
    try:
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        base_pet_state = _get_current_pet_state(current_hour)
        
        logger.info(f"Обработка снижения характеристик: текущий час {current_hour}, базовое состояние {base_pet_state.value}")
        
        # Получаем всех активных питомцев
        query = select(Pet).where(Pet.is_deleted == False)
        result = await db.execute(query)
        pets = result.scalars().all()
        
        logger.info(f"Обработка {len(pets)} питомцев")
        
        # Словарь для группировки уведомлений. 
        # Ключ: owner_id, Значение: список имен (или ID) проблемных питомцев
        users_to_notify = {}
        
        for pet in pets:
            try:
                # Пропускаем удаленных или потерянных питомцев для обновления статуса
                if not (pet.is_deleted or pet.is_lost):
                    # Обновляем статус питомца на основе времени (если не болен и не грустит)
                    if pet.pet_state not in (PetState.SICK1, PetState.SICK2, PetState.SICK3, PetState.SAD):
                        pet.pet_state = base_pet_state
                    
                    # Проверяем условия болезни и грусти
                    service = get_pet_service(db)
                    service._check_and_update_pet_state(pet)
                
                # Получаем погоду
                weather_desc = await _get_weather_for_user(db, pet.owner_id)
                weather_type = _categorize_weather(weather_desc) if weather_desc else "clear"
                
                # Получаем множители для текущего состояния
                state_mults = _get_stat_multipliers_by_state(pet.pet_state)
                
                # Рассчитываем базовое снижение с учётом погоды и характера
                hunger_base = _calculate_stat_reduction(
                    base_reduction=1.0, character=pet.pet_character, feature=pet.pet_feature,
                    weather_type=weather_type, stat_name="hunger", pet_state=pet.pet_state,
                    pet_cleanliness=getattr(pet, 'pet_cleanliness', 50.0)
                )
                energy_base = _calculate_stat_reduction(
                    base_reduction=1.0, character=pet.pet_character, feature=pet.pet_feature,
                    weather_type=weather_type, stat_name="energy", pet_state=pet.pet_state,
                    pet_cleanliness=getattr(pet, 'pet_cleanliness', 50.0)
                )
                happiness_base = _calculate_stat_reduction(
                    base_reduction=1.0, character=pet.pet_character, feature=pet.pet_feature,
                    weather_type=weather_type, stat_name="happiness", pet_state=pet.pet_state,
                    pet_cleanliness=getattr(pet, 'pet_cleanliness', 50.0)
                )
                
                # Применяем множители состояния
                hunger_delta = hunger_base * state_mults["hunger"]
                energy_delta = energy_base * state_mults["energy"]
                happiness_delta = happiness_base * state_mults["happiness"]
                health_delta = state_mults["health"]
                
                # Обновляем характеристики
                pet.pet_hunger = round(max(0.0, min(100.0, pet.pet_hunger - hunger_delta)), 1)
                pet.pet_energy = round(max(0.0, min(100.0, pet.pet_energy - energy_delta)), 1)
                pet.pet_happiness = round(max(0.0, min(100.0, pet.pet_happiness - happiness_delta)), 1)
                pet.pet_health = round(max(0.0, min(100.0, pet.pet_health - health_delta)), 1)
                
                pet.last_updated = func.now()
                
                # Проверяем условия для отправки оповещения
                should_notify = (
                    pet.pet_hunger == 0 or 
                    pet.pet_energy == 0 or 
                    pet.pet_happiness == 0 or 
                    pet.pet_health < 50
                )
                
                if should_notify:
                    if pet.owner_id not in users_to_notify:
                        users_to_notify[pet.owner_id] = []
                    pet_name = getattr(pet, 'pet_name', f"Питомец #{pet.pet_id}")
                    users_to_notify[pet.owner_id].append(pet_name)
                
                logger.debug(
                    f"Питомец {pet.pet_id} ({pet.pet_state.value}): "
                    f"Голод={pet.pet_hunger}, Энергия={pet.pet_energy}, "
                    f"Счастье={pet.pet_happiness}, Здоровье={pet.pet_health}"
                )
            
            except Exception as e:
                logger.error(f"Ошибка обработки питомца {pet.pet_id}: {e}")
                continue
        
        await db.commit()
        
        if users_to_notify:
            logger.info(f"Отправка уведомлений {len(users_to_notify)} пользователям")
            for owner_id, bad_pets_list in users_to_notify.items():
                try:
                    user = await db.get(User, owner_id)
                    if user:
                        await EmailService.send_bad_pet_email(user.user_email, user.user_full_name, bad_pets_list)
                except Exception as e:
                    logger.error(f"Ошибка отправки email пользователю {owner_id}: {e}")

        logger.info("Снижение характеристик питомцев завершено")
    
    except Exception as e:
        logger.error(f"Ошибка в процессе decay: {e}")
        await db.rollback()

async def _count_consecutive_ai_messages(db: AsyncSession, chat_id: int) -> int:
    """
    Подсчитывает количество подряд идущих AI сообщений от последнего HUMAN сообщения.
    """
    try:
        # Получаем последние сообщения в чате
        query = select(Message).where(
            Message.chat_id == chat_id,
            Message.is_deleted == False
        ).order_by(Message.created_at.desc()).limit(10)
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Подсчитываем подряд идущие AI сообщения с конца
        ai_count = 0
        for msg in messages:
            if msg.message_type == MessageType.AI:
                ai_count += 1
            else:
                # Встретили HUMAN сообщение, прекращаем подсчет
                break
        
        return ai_count
    except Exception as e:
        logger.error(f"Ошибка подсчета AI сообщений в чате {chat_id}: {e}")
        return 0


async def _get_chat_context_messages(db: AsyncSession, chat_id: int, limit: int = 10):
    """Получает последние сообщения чата для контекста."""
    try:
        query = select(Message).where(
            Message.chat_id == chat_id,
            Message.is_deleted == False
        ).order_by(Message.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        messages = list(reversed(result.scalars().all()))  # Порядок от старого к новому
        return messages
    except Exception as e:
        logger.error(f"Ошибка получения контекста чата {chat_id}: {e}")
        return []


async def process_pet_auto_messages(db: AsyncSession) -> None:
    """
    Отправляет автоматические сообщения от питомца через час молчания.
    - Если прошло > 1 часа с последнего сообщения
    - С вероятностью 20%
    - Но максимум 2 AI сообщения подряд
    """
    try:
        # Получаем все активные чаты
        query = select(Chat).where()
        result = await db.execute(query)
        chats = result.scalars().all()
        
        logger.info(f"Проверка автоматических сообщений для {len(chats)} чатов")
        
        for chat in chats:
            try:
                # Проверяем время последнего сообщения
                last_msg_query = select(Message).where(
                    Message.chat_id == chat.chat_id,
                    Message.is_deleted == False
                ).order_by(Message.created_at.desc()).limit(1)
                
                last_msg_result = await db.execute(last_msg_query)
                last_message = last_msg_result.scalars().first()
                
                if not last_message:
                    continue  # Нет сообщений в чате
                
                # Проверяем прошло ли более 1 часа
                time_passed = datetime.now(timezone.utc) - last_message.created_at
                if time_passed < timedelta(hours=1):
                    continue  # Еще не прошел час
                
                # Проверяем количество подряд идущих AI сообщений
                ai_consecutive = await _count_consecutive_ai_messages(db, chat.chat_id)
                if ai_consecutive >= 2:
                    logger.debug(f"Чат {chat.chat_id}: уже {ai_consecutive} AI сообщений подряд, пропускаем")
                    continue
                
                # С 20% вероятностью отправляем сообщение
                if random.random() > 0.2:  # 80% = не отправляем
                    continue
                
                # Получаем питомца и хозяина
                pet = await db.get(Pet, chat.pet_id)
                user = await db.get(User, chat.user_id)
                
                if not pet or not user:
                    continue
                
                # Получаем контекст сообщений
                context_messages = await _get_chat_context_messages(db, chat.chat_id, limit=10)
                
                # Генерируем ответ от питомца (хозяин написал, значит is_owner=True)
                ai_response = await ai_service.generate_response(
                    pet, 
                    context_messages, 
                    is_owner=True
                )
                
                if not ai_response:
                    logger.warning(f"Не удалось сгенерировать ответ для чата {chat.chat_id}")
                    continue
                
                # Сохраняем сообщение в БД
                new_message = Message(
                    chat_id=chat.chat_id,
                    sender_id=None,  # AI сообщение
                    message_type=MessageType.AI,
                    content=ai_response,
                    created_at=datetime.now(timezone.utc),
                    is_deleted=False,
                    is_edited=False
                )
                db.add(new_message)
                chat.last_message_at = datetime.now(timezone.utc)
                
                logger.info(
                    f"Питомец {pet.pet_id} ({pet.pet_name}) отправил автоматическое сообщение в чате {chat.chat_id}: "
                    f"{ai_response[:50]}..."
                )
            
            except Exception as e:
                logger.error(f"Ошибка обработки автоматического сообщения для чата {chat.chat_id}: {e}")
                continue
        
        # Сохраняем все изменения
        await db.commit()
        logger.info("Проверка автоматических сообщений завершена")
    
    except Exception as e:
        logger.error(f"Ошибка в процессе проверки автоматических сообщений: {e}")
        await db.rollback()


async def run_pet_decay_task() -> None:
    """
    Фоновая задача для постоянного снижения характеристик питомцев.
    Интервал можно менять в PET_DECAY_INTERVAL_SECONDS (по умолчанию 30 минут).
    """
    logger.info(f"Запущена фоновая задача снижения характеристик питомцев (интервал: {settings.PET_DECAY_INTERVAL_SECONDS} сек)")
    
    while True:
        try:
            # Используем интервал из конфига
            await asyncio.sleep(settings.PET_DECAY_INTERVAL_SECONDS)
            
            async with db_helper.session_factory() as db:
                await process_pet_stats_decay(db)
        
        except asyncio.CancelledError:
            logger.warning("Фоновая задача снижения характеристик отменена")
            break
        
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче снижения характеристик: {e}")
            # Продолжаем работу несмотря на ошибку
            await asyncio.sleep(60)


async def run_pet_auto_messages_task() -> None:
    """
    Фоновая задача для отправки автоматических сообщений от питомца.
    
    Интервал можно менять в PET_ATTRACTION_INTERVAL_SECONDS (по умолчанию 60 минут).
    Проверяет - если прошло > 1 часа с последнего сообщения,
    то с 20% вероятностью отправляет сообщение (максимум 2 подряд).
    """
    logger.info(f"Запущена фоновая задача автоматических сообщений от питомца  (интервал: {settings.PET_ATTRACTION_INTERVAL_SECONDS} сек)")
    
    while True:
        try:
            # Проверяем каждый час
            await asyncio.sleep(settings.PET_ATTRACTION_INTERVAL_SECONDS)
            async with db_helper.session_factory() as db:
                await process_pet_auto_messages(db)
        
        except asyncio.CancelledError:
            logger.warning("Фоновая задача автоматических сообщений отменена")
            break
        
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче автоматических сообщений: {e}")
            # Продолжаем работу несмотря на ошибку
            await asyncio.sleep(60)
