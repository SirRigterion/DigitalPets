from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from src.db.models import Pet, User, PetCharacter, PetState
from src.pet.schemas import PetCreate, MAX_PET_XP
from src.core.config_log import logger
from src.core.exceptions import NotFoundError
from typing import List, Optional, Dict, Tuple, Union
from datetime import timedelta, datetime, timezone
import random


# Начальные значения параметров в зависимости от характера
# (hunger, energy, happiness, cleanliness, health, xp)
INITIAL_STATS: Dict[str, Tuple[float, float, float, float, float, float]] = {
    "playful": (40.0, 80.0, 70.0, 60.0, 100.0, 0.0),
    "lazy": (50.0, 90.0, 50.0, 40.0, 100.0, 0.0),
    "energetic": (30.0, 100.0, 60.0, 70.0, 100.0, 0.0),
    "curious": (60.0, 60.0, 60.0, 50.0, 100.0, 0.0),
    "shy": (70.0, 40.0, 40.0, 45.0, 100.0, 0.0),
}


class PetService:
    """Сервис для управления питомцами: создание, получение, обновление характеристик, поиск и восстановление потерянных питомцев."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pet(self, owner_id: int, data: PetCreate) -> Pet:
        owner = await self.session.get(User, owner_id)
        if not owner:
            raise NotFoundError("User")

        # Определяем начальные значения параметров на основе характера
        pet_char = data.pet_character or PetCharacter.PLAYFUL
        char_str = pet_char.value if hasattr(pet_char, 'value') else str(pet_char).lower()
        initial_hunger, initial_energy, initial_happiness, initial_cleanliness, initial_health, initial_xp = INITIAL_STATS.get(
            char_str, (50.0, 50.0, 50.0, 50.0, 100.0, 0.0)
        )

        pet = Pet(
            pet_name=data.pet_name.strip(),
            pet_species=data.pet_species,
            pet_color=data.pet_color,
            pet_character=pet_char,
            pet_feature=data.pet_feature,
            pet_hunger=initial_hunger,
            pet_energy=initial_energy,
            pet_happiness=initial_happiness,
            pet_cleanliness=initial_cleanliness,
            pet_health=initial_health,
            pet_state=None,
            pet_xp=initial_xp,
            owner_id=owner_id
        )

        self.session.add(pet)
        await self.session.commit()
        await self.session.refresh(pet)
        logger.info(f"Создан питомец {pet.pet_id} (характер: {char_str}) для пользователя {owner_id}")
        return pet

    async def get_pet(self, pet_id: int) -> Optional[Pet]:
        """
        Получает питомца по ID из базы данных.
        """
        
        query = select(Pet).where(Pet.pet_id == pet_id, Pet.is_deleted == False)
        result = await self.session.execute(query)
        pet = result.scalars().first()
        
        if pet:
            self._check_and_update_pet_state(pet)
            await self.check_and_mark_lost(pet)
            logger.info(
                f"Питомец {pet.pet_id}: характеристики обновлены (delta), "
                f"состояние: {pet.pet_state.value if pet.pet_state else 'None'}"
            )
        
        return pet
    
    def _check_and_update_pet_state(self, pet: Pet) -> None:
        """
        Проверяет состояние питомца на основе текущих характеристик.
        
        Приоритет проверок (от критичного к нормальному):
        1. Если все характеристики < 5 → SICK3 (экстремальное)
        2. Если хоть одна характеристика = 0 → SICK2 (критическое)
        3. Если все характеристики < 20 → SICK1 (серьёзное)
        4. Если счастье < 25 → SAD (грусть)
        5. Иначе → NEUTRAL (здоров)
        
        Характеристики: hunger, energy, happiness, cleanliness
        """
        
        # Не трогаем удаленных или потерянных питомцев
        if getattr(pet, 'is_deleted', False) or getattr(pet, 'is_lost', False):
            return

        stats = [pet.pet_hunger, pet.pet_energy, pet.pet_happiness, pet.pet_cleanliness]

        # 1. Проверка экстремальной болезни (все < 5, приоритет выше)
        if all(stat < 5.0 for stat in stats):
            if pet.pet_state != PetState.SICK3:
                pet.pet_state = PetState.SICK3
                logger.error(f"Питомец {pet.pet_id} в экстремальном состоянии SICK3: {stats}")
        # 2. Проверка критической болезни (хоть одна = 0, но не все < 5)
        elif any(stat == 0.0 for stat in stats):
            if pet.pet_state != PetState.SICK2:
                pet.pet_state = PetState.SICK2
                logger.warning(f"Питомец {pet.pet_id} в критическом состоянии SICK2: {stats}")
        # 3. Проверка серьезной болезни (все < 20)
        elif all(stat < 20.0 for stat in stats):
            if pet.pet_state != PetState.SICK1:
                pet.pet_state = PetState.SICK1
                logger.warning(f"Питомец {pet.pet_id} в состоянии SICK1: {stats}")
        # 4. Проверка грусти (счастье < 25, не болен)
        elif pet.pet_happiness < 25.0:
            if pet.pet_state not in (PetState.SAD, PetState.SLEEP, PetState.PLAY):
                pet.pet_state = PetState.SAD
                logger.info(f"Питомец {pet.pet_id} грустит (счастье: {pet.pet_happiness})")
        # 5. Выздоровление или нормальное состояние
        else:
            # не менять на NEUTRAL, если уже в специальных состояниях
            if pet.pet_state not in (PetState.NEUTRAL, PetState.SLEEP, PetState.PLAY):
                if pet.pet_state != PetState.NEUTRAL:
                    logger.info(f"Питомец {pet.pet_id} выздоровел! Состояние: NEUTRAL")
                pet.pet_state = PetState.NEUTRAL

            # Дополнительная логика: в зависимости от времени суток показываем
            # более подходящее состояние: `SLEEP` или `PLAY` вместо чистого `NEUTRAL`.
            # Правила (настроим простые диапазоны):
            # - Sleep: 22:00-05:59 UTC
            # - Play: 09:00-20:59 UTC
            if pet.pet_state in (PetState.NEUTRAL, None):
                current_hour = int(datetime.now(timezone.utc).hour)
                from src.pet.background_tasks import _get_current_pet_state
                pet.pet_state = _get_current_pet_state(current_hour)

    async def update_stats(self, pet_id: int, owner_id: int, data) -> Optional[Pet]:
        """Обновляет характеристики питомца, добавляя/вычитая значения (delta)."""
        
        pet = await self.get_pet(pet_id)
        if not pet or pet.owner_id != owner_id or pet.is_deleted:
            return None

        # Применяем delta (прибавляем/отнимаем) к каждому полю
        if getattr(data, 'pet_hunger', None) is not None:
            pet.pet_hunger = round(max(0.0, min(100.0, pet.pet_hunger + data.pet_hunger)), 1)
        if getattr(data, 'pet_energy', None) is not None:
            pet.pet_energy = round(max(0.0, min(100.0, pet.pet_energy + data.pet_energy)), 1)
        if getattr(data, 'pet_happiness', None) is not None:
            pet.pet_happiness = round(max(0.0, min(100.0, pet.pet_happiness + data.pet_happiness)), 1)
        if getattr(data, 'pet_cleanliness', None) is not None:
            pet.pet_cleanliness = round(max(0.0, min(100.0, pet.pet_cleanliness + data.pet_cleanliness)), 1)
        if getattr(data, 'pet_health', None) is not None:
            pet.pet_health = round(max(0.0, min(100.0, pet.pet_health + data.pet_health)), 1)
        if getattr(data, 'pet_xp', None) is not None:
            new_xp = pet.pet_xp + data.pet_xp
            pet.pet_xp = int(max(0, min(MAX_PET_XP, new_xp)))

        self._check_and_update_pet_state(pet)
        
        await self.check_and_mark_lost(pet)
        
        pet.last_updated = func.now()
        await self.session.commit()
        await self.session.refresh(pet)
        logger.info(f"Питомец {pet.pet_id}: характеристики обновлены (delta), состояние: {pet.pet_state.value if pet.pet_state else 'None'}")
        return pet

    async def update_stats_with_chances(self, pet_id: int, owner_id: int, data) -> Optional[Pet]:
        """
        Обновляет характеристики с вероятностями.
        
        Для каждой характеристики:
        - Если chance сработала - используется вариант с шансом (variant)
        - Если не сработала - используется базовое значение (delta)
        """
        
        pet = await self.get_pet(pet_id)
        if not pet or pet.owner_id != owner_id or pet.is_deleted:
            return None

        if getattr(data, 'pet_hunger_delta', None) is not None:
            chance = getattr(data, 'pet_hunger_chance', None) or 0
            variant = getattr(data, 'pet_hunger_variant', None)
            
            if variant is not None and random.random() * 100 < chance:
                delta = variant
            else:
                delta = data.pet_hunger_delta
            
            pet.pet_hunger = round(max(0.0, min(100.0, pet.pet_hunger + delta)), 1)

        if getattr(data, 'pet_energy_delta', None) is not None:
            chance = getattr(data, 'pet_energy_chance', None) or 0
            variant = getattr(data, 'pet_energy_variant', None)
            
            if variant is not None and random.random() * 100 < chance:
                delta = variant
            else:
                delta = data.pet_energy_delta
            
            pet.pet_energy = round(max(0.0, min(100.0, pet.pet_energy + delta)), 1)

        if getattr(data, 'pet_happiness_delta', None) is not None:
            chance = getattr(data, 'pet_happiness_chance', None) or 0
            variant = getattr(data, 'pet_happiness_variant', None)
            
            if variant is not None and random.random() * 100 < chance:
                delta = variant
            else:
                delta = data.pet_happiness_delta
            
            pet.pet_happiness = round(max(0.0, min(100.0, pet.pet_happiness + delta)), 1)

        if getattr(data, 'pet_cleanliness_delta', None) is not None:
            chance = getattr(data, 'pet_cleanliness_chance', None) or 0
            variant = getattr(data, 'pet_cleanliness_variant', None)
            
            if variant is not None and random.random() * 100 < chance:
                delta = variant
            else:
                delta = data.pet_cleanliness_delta
            
            pet.pet_cleanliness = round(max(0.0, min(100.0, pet.pet_cleanliness + delta)), 1)

        if getattr(data, 'pet_health_delta', None) is not None:
            chance = getattr(data, 'pet_health_chance', None) or 0
            variant = getattr(data, 'pet_health_variant', None)
            
            if variant is not None and random.random() * 100 < chance:
                delta = variant
            else:
                delta = data.pet_health_delta
            
            pet.pet_health = round(max(0.0, min(100.0, pet.pet_health + delta)), 1)

        if getattr(data, 'pet_xp_delta', None) is not None:
            chance = getattr(data, 'pet_xp_chance', None) or 0
            variant = getattr(data, 'pet_xp_variant', None)
            
            if variant is not None and random.random() * 100 < chance:
                delta = variant
            else:
                delta = data.pet_xp_delta
            
            new_xp = pet.pet_xp + delta
            pet.pet_xp = int(max(0, min(MAX_PET_XP, new_xp)))

        self._check_and_update_pet_state(pet)
        
        await self.check_and_mark_lost(pet)
        
        pet.last_updated = func.now()
        await self.session.commit()
        await self.session.refresh(pet)
        logger.info(f"Питомец {pet.pet_id}: характеристики обновлены с шансами, состояние: {pet.pet_state.value if pet.pet_state else 'None'}")
        return pet

    async def rename_pet(self, pet_id: int, owner_id: int, new_name: str) -> Optional[Pet]:
        """Переименовать питомца, если он принадлежит пользователю."""
        
        pet = await self.get_pet(pet_id)
        if not pet or pet.owner_id != owner_id or pet.is_deleted:
            return None
        pet.pet_name = new_name.strip()
        pet.last_updated = func.now()
        await self.session.commit()
        await self.session.refresh(pet)
        return pet

    async def rename_pet_force(self, pet_id: int, new_name: str) -> Optional[Pet]:
        """
        Переименовать питомца без проверки владельца (для модерации/админов).
        """
        
        pet = await self.get_pet(pet_id)
        if not pet or pet.is_deleted:
            return None
        pet.pet_name = new_name.strip()
        pet.last_updated = func.now()
        await self.session.commit()
        await self.session.refresh(pet)
        logger.info(f"Питомец {pet.pet_id} переименован модератором/админом в '{pet.pet_name}'")
        return pet

    async def list_pets(
        self,
        owner_id: Optional[int] = None,
        pet_name: Optional[str] = None,
        pet_species: Optional[str] = None,
        pet_color: Optional[str] = None,
        min_xp: Optional[int] = None,
        max_xp: Optional[int] = None,
        include_lost: bool = False,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Pet]:
        """Возвращает питомцев.

        Если owner_id задан, фильтруем по владельцу (используется в /pets/my).
        По умолчанию исключаем удалённых питомцев; если include_lost=True,
        возвращаются и потерянные (is_lost=True) также.
        """
        
        quere = select(Pet).where(Pet.is_deleted == False)
        if owner_id is not None:
            quere = quere.where(Pet.owner_id == owner_id)
        if not include_lost:
            quere = quere.where(Pet.is_lost == False)

        if pet_name:
            quere = quere.filter(Pet.pet_name.ilike(f"%{pet_name.strip()}%"))
        if pet_species:
            quere = quere.filter(Pet.pet_species.ilike(f"%{pet_species.strip()}%"))
        if pet_color:
            quere = quere.filter(Pet.pet_color.ilike(f"%{pet_color.strip()}%"))
        if min_xp is not None:
            min_xp = max(0, min(MAX_PET_XP, min_xp))
            quere = quere.filter(Pet.pet_xp >= min_xp)
        if max_xp is not None:
            max_xp = max(0, min(MAX_PET_XP, max_xp))
            quere = quere.filter(Pet.pet_xp <= max_xp)

        quere = quere.order_by(Pet.pet_id)

        quere = quere.limit(limit).offset(offset)

        res = await self.session.execute(quere)
        return res.scalars().all()

    async def get_pet_rating(self, owner_id: int, pet_id: Optional[int] = None) -> List[Dict]:
        """
        Возвращает массив питомцев: сначала питомец пользователя (если указан), затем топ-5.
        Место рассчитывается по XP (больше выше), затем по времени создания (раньше выше).
        """
        
        ranking: List[Dict] = []

        if pet_id:
            user_pet = await self.get_pet(pet_id)
            if user_pet and not user_pet.is_deleted:
                count_query = select(func.count(Pet.pet_id)).where(
                    Pet.is_deleted == False,
                    (
                        (Pet.pet_xp > user_pet.pet_xp) |
                        ((Pet.pet_xp == user_pet.pet_xp) & (Pet.created_at < user_pet.created_at))
                    )
                )
                count_result = await self.session.execute(count_query)
                position = count_result.scalar() + 1
                user_item = {
                    "ranking_place": position,
                    "pet_id": user_pet.pet_id,
                    "pet_name": user_pet.pet_name,
                    "pet_species": user_pet.pet_species,
                    "pet_color": user_pet.pet_color,
                    "owner_id": user_pet.owner_id,
                    "pet_xp": user_pet.pet_xp,
                    "owner_login": user_pet.owner.user_login if user_pet.owner else "Unknown",
                }
                ranking.append(user_item)

        top_query = select(Pet).options(selectinload(Pet.owner)).where(Pet.is_deleted == False)
        top_query = top_query.order_by(desc(Pet.pet_xp), Pet.created_at).limit(5)
        top_result = await self.session.execute(top_query)
        top_pets = top_result.scalars().all()

        for pet in top_pets:
            count_query = select(func.count(Pet.pet_id)).where(
                Pet.is_deleted == False,
                (
                    (Pet.pet_xp > pet.pet_xp) |
                    ((Pet.pet_xp == pet.pet_xp) & (Pet.created_at < pet.created_at))
                )
            )
            count_result = await self.session.execute(count_query)
            position = count_result.scalar() + 1
            
            ranking.append({
                "ranking_place": position,
                "pet_id": pet.pet_id,
                "pet_name": pet.pet_name,
                "pet_species": pet.pet_species,
                "pet_color": pet.pet_color,
                "owner_id": pet.owner_id,
                "pet_xp": pet.pet_xp,
                "owner_login": pet.owner.user_login if pet.owner else "Unknown",
            })

        if pet_id and ranking:
            first = ranking[0]
            rest = ranking[1:]
            rest.sort(key=lambda item: item["ranking_place"])
            ranking = [first] + rest

        return ranking

    async def check_and_mark_lost(self, pet: Pet) -> bool:
        """
        Проверяет, убежал ли питомец (здоровье=0 более 24 часов).
        Если да — отмечает как потерянный и удаленный.
        Возвращает True если питомец был отмечен потерянным.
        """
        
        if pet.pet_health == 0.0:
            check_time = pet.last_updated or pet.created_at
            time_since = func.now() - check_time
            
            if time_since > timedelta(hours=24):
                if not pet.is_lost:
                    pet.is_lost = True
                    pet.is_deleted = True
                    pet.lost_at = func.now()
                    await self.session.commit()
                    await self.session.refresh(pet)
                    logger.warning(f"Питомец {pet.pet_id} убежал! Отмечен как потерянный.")
                    return True
        return False

    async def find_pet(self, pet_id: int, owner_id: int) -> Dict[str, Union[bool, str, Optional[Pet]]]:
        """
        Начинает поиск потеянного питомца.
        Создает токен поиска и устанавливает время для восстановления через 5 часов.
        Если питомец не потерян, возвращает сообщение кось.
        """
        
        pet = await self.get_pet(pet_id)
        if not pet or pet.owner_id != owner_id:
            return {"success": False, "message": "Питомец не найден или доступ запрещен", "pet": None}
        
        if not pet.is_lost:
            return {"success": False, "message": "Питомец на месте, он не сбежал.", "pet": pet}
        
        pet.search_token_created_at = func.now()
        pet.last_updated = func.now()
        await self.session.commit()
        await self.session.refresh(pet)
        logger.info(f"Начато восстановление питомца {pet.pet_id}, поиск стартовал")
        return {"success": True, "message": "Поиск питомца начат", "pet": pet}

    async def restore_pet(self, pet_id: int, owner_id: int) -> Dict[str, Union[bool, str, Optional[Pet]]]:
        """
        Попытка восстановления потеянного питомца.
        - Если прошло < 5 часов с начала поиска → ошибка
        - Если прошло >= 5 часов → попытка восстановления:
          * 75% успех → питомец восстановлен (is_lost=False, is_deleted=False)
          * 25% неудача → питомец потерян навсегда (is_deleted=True, is_lost=False)
        Возвращает словарь с результатом.
        """
        
        pet = await self.get_pet(pet_id)
        if not pet or pet.owner_id != owner_id or not pet.is_lost:
            return {"success": False, "message": "Питомец не найден или не потерян", "pet": None}
        
        if pet.search_token_created_at is None:
            return {"success": False, "message": "Сначала нужно нажать найти (поиск не начат)", "pet": None}
        
        now = datetime.now(pet.search_token_created_at.tzinfo) if pet.search_token_created_at.tzinfo else datetime.now(timezone.utc)
        search_duration = now - pet.search_token_created_at
        
        if search_duration < timedelta(hours=5):
            hours_left = 5 - search_duration.total_seconds() / 3600
            return {
                "success": False,
                "message": f"Поиск еще не закончен. Осталось {hours_left:.1f} часов",
                "pet": None
            }
        
        restore_chance = random.random() * 100
        
        if restore_chance < 75: 
            pet.is_lost = False
            pet.is_deleted = False
            pet.lost_at = None
            pet.search_token_created_at = None
            pet.pet_health = max(1, pet.pet_health)
            pet.last_updated = func.now()
            await self.session.commit()
            await self.session.refresh(pet)
            logger.info(f"Питомец {pet.pet_id} успешно восстановлен!")
            return {
                "success": True,
                "message": "Питомец найден и восстановлен!",
                "pet": pet
            }
        else:
            pet.is_deleted = True
            pet.is_lost = False
            pet.lost_at = func.now()
            pet.search_token_created_at = None
            pet.last_updated = func.now()
            await self.session.commit()
            await self.session.refresh(pet)
            logger.warning(f"Попытка восстановления питомца {pet.pet_id} не удалась. Питомец потерян навсегда.")
            return {
                "success": False,
                "message": "К сожалению, питомец потерялся навсегда...",
                "pet": pet
            }

    async def delete_pet(self, pet_id: int, owner_id: int) -> Optional[Pet]:
        """Удалить питомца (мягкое удаление). Устанавливает is_deleted=True и is_lost=False."""
        
        pet = await self.get_pet(pet_id)
        if not pet or pet.owner_id != owner_id:
            return None
        
        pet.is_deleted = True
        pet.is_lost = False
        pet.last_updated = func.now()
        await self.session.commit()
        await self.session.refresh(pet)
        logger.info(f"Питомец {pet.pet_id} удален пользователем {owner_id}")
        return pet


def get_pet_service(session: AsyncSession) -> PetService:
    return PetService(session)
