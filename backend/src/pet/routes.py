from fastapi import APIRouter, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union, Dict

from src.utils.decorators import rate_limit, security_headers_check, active_user_required
from src.core.exceptions import InternalServerError, ValidationError
from src.pet.services import get_pet_service
from src.core.config_log import logger
from src.db.database import get_db
from src.auth import get_current_user
from src.db.models import User
from src.pet.schemas import (
    PetCreate, PetSchema, PetSchemaPublic,
    PetUpdateStats, PetRename, PetUpdateWithChances,
    PetRatingItem, MAX_PET_XP
)


pet_router = APIRouter()

@pet_router.post("", response_model=PetSchema, status_code=201)
@security_headers_check
@rate_limit(limit=10, period=60)
@active_user_required
async def create_pet(
    request: Request,
    pet_data: PetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создание питомца"""
    
    try:
        service = get_pet_service(db)
        pet = await service.create_pet(current_user.user_id, pet_data)
        return PetSchema.model_validate(pet)
    except Exception as e:
        logger.error(f"Ошибка создания питомца: {e}")
        raise InternalServerError("Не удалось создать питомца")


@pet_router.get("", response_model=List[PetSchemaPublic])
@security_headers_check
@rate_limit(limit=20, period=60)
@active_user_required
async def list_pets(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    pet_name: Optional[str] = None,
    pet_species: Optional[str] = None,
    pet_color: Optional[str] = None,
    min_xp: Optional[int] = None,
    max_xp: Optional[int] = None,
    include_lost: bool = False,
    limit: int = 10,
    offset: int = 0,
):
    """Получить список питомцев"""
    
    if not (1 <= limit <= 100):
        raise ValidationError("Лимит должен быть в диапазоне 1-100", field="limit")
    if offset < 0:
        raise ValidationError("Offset не может быть отрицательным", field="offset")

    if min_xp is not None:
        if min_xp < 0 or min_xp > MAX_PET_XP:
            raise ValidationError(f"min_xp должен быть в диапазоне 0-{MAX_PET_XP}", field="min_xp")
    if max_xp is not None:
        if max_xp < 0 or max_xp > MAX_PET_XP:
            raise ValidationError(f"max_xp должен быть в диапазоне 0-{MAX_PET_XP}", field="max_xp")
    if min_xp is not None and max_xp is not None and min_xp > max_xp:
        raise ValidationError("min_xp не может быть больше max_xp")

    service = get_pet_service(db)
    pets = await service.list_pets(
        owner_id=None,
        pet_name=pet_name,
        pet_species=pet_species,
        pet_color=pet_color,
        min_xp=min_xp,
        max_xp=max_xp,
        include_lost=include_lost,
        limit=limit,
        offset=offset,
    )
    return [PetSchemaPublic.model_validate(p) for p in pets]


@pet_router.get("/my", response_model=List[PetSchema])
@security_headers_check
@rate_limit(limit=20, period=60)
@active_user_required
async def list_my_pets(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    pet_name: Optional[str] = None,
    pet_species: Optional[str] = None,
    pet_color: Optional[str] = None,
    min_xp: Optional[int] = None,
    max_xp: Optional[int] = None,
    include_lost: bool = False,
    limit: int = 10,
    offset: int = 0,
):
    """Получить своих список питомцев"""
    
    if not (1 <= limit <= 100):
        raise ValidationError("Лимит должен быть в диапазоне 1-100", field="limit")
    if offset < 0:
        raise ValidationError("Offset не может быть отрицательным", field="offset")
    if min_xp is not None:
        if min_xp < 0 or min_xp > MAX_PET_XP:
            raise ValidationError(f"min_xp должен быть в диапазоне 0-{MAX_PET_XP}", field="min_xp")
    if max_xp is not None:
        if max_xp < 0 or max_xp > MAX_PET_XP:
            raise ValidationError(f"max_xp должен быть в диапазоне 0-{MAX_PET_XP}", field="max_xp")
    if min_xp is not None and max_xp is not None and min_xp > max_xp:
        raise ValidationError("min_xp не может быть больше max_xp")

    service = get_pet_service(db)
    pets = await service.list_pets(
        owner_id=current_user.user_id,
        pet_name=pet_name,
        pet_species=pet_species,
        pet_color=pet_color,
        min_xp=min_xp,
        max_xp=max_xp,
        include_lost=include_lost,
        limit=limit,
        offset=offset,
    )
    return [PetSchema.model_validate(p) for p in pets]


@pet_router.get("/rating", response_model=List[PetRatingItem])
@rate_limit(limit=10, period=60)
@active_user_required
async def get_pet_rating(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    pet_id: Optional[int] = None
):
    """Получить рейтинг питомца и топ 5 питомцев по xp"""
    
    service = get_pet_service(db)

    if not pet_id:
        pets = await service.list_pets(owner_id=current_user.user_id)
        if pets:
            pet_id = pets[0].pet_id

    rating = await service.get_pet_rating(current_user.user_id, pet_id)
    return rating


@pet_router.get("/{pet_id}", response_model=Union[PetSchema, PetSchemaPublic])
@rate_limit(limit=30, period=60)
@active_user_required
async def get_pet(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить питомца по ID. Если питомец принадлежит текущему пользователю, возвращается полная информация, иначе только публичная."""
    service = get_pet_service(db)
    pet = await service.get_pet(pet_id)
    if not pet or pet.is_deleted:
        raise ValidationError("Питомец не найден")
    
    if pet.owner_id == current_user.user_id:
        return PetSchema.model_validate(pet)
    
    return PetSchemaPublic.model_validate(pet)


@pet_router.patch("/{pet_id}", response_model=PetSchema)
@security_headers_check
@rate_limit(limit=10, period=60)
@active_user_required
async def update_pet_stats(
    request: Request,
    pet_id: int,
    pet_hunger: Optional[float] = Form(None),
    pet_energy: Optional[float] = Form(None),
    pet_happiness: Optional[float] = Form(None),
    pet_cleanliness: Optional[float] = Form(None),
    pet_health: Optional[float] = Form(None),
    pet_xp: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление характеристик питомца (delta прибавляется к текущему значению)."""
    
    service = get_pet_service(db)
    
    stats = PetUpdateStats(
        pet_hunger=pet_hunger,
        pet_energy=pet_energy,
        pet_happiness=pet_happiness,
        pet_cleanliness=pet_cleanliness,
        pet_health=pet_health,
        pet_xp=pet_xp
    )
    
    pet = await service.update_stats(pet_id, current_user.user_id, stats)
    if not pet:
        raise ValidationError("Питомец не найден или доступ запрещен")
    return PetSchema.model_validate(pet)


@pet_router.patch("/{pet_id}/chances", response_model=PetSchema)
@security_headers_check
@rate_limit(limit=10, period=60)
@active_user_required
async def update_pet_stats_with_chances(
    request: Request,
    pet_id: int,
    stats: PetUpdateWithChances,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновление характеристик питомца с вероятностями.
    
    Пример JSON:
    {
        "pet_health_delta": 25,
        "pet_happiness_delta": -15,
        "pet_happiness_chance": 60,
        "pet_happiness_variant": 15
    }
    
    С 60% вероятностью счастье повышается на 15, иначе понижается на 15.
    Здоровье в любом случае повышается на 25.
    """
    
    service = get_pet_service(db)
    
    pet = await service.update_stats_with_chances(pet_id, current_user.user_id, stats)
    if not pet:
        raise ValidationError("Питомец не найден или доступ запрещен")
    return PetSchema.model_validate(pet)


@pet_router.put("/{pet_id}/name", response_model=PetSchema)
@security_headers_check
@rate_limit(limit=5, period=60)
@active_user_required
async def rename_pet(
    request: Request,
    pet_id: int,
    payload: PetRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Переименовать питомца."""
    
    service = get_pet_service(db)
    pet = await service.rename_pet(pet_id, current_user.user_id, payload.pet_name)
    if not pet:
        raise ValidationError("Питомец не найден или доступ запрещен или имя некорректно")
    return PetSchema.model_validate(pet)


@pet_router.get("/{pet_id}/find", response_model=Dict)
@rate_limit(limit=5, period=60)
@active_user_required
async def find_lost_pet(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Начать поиск потеянного питомца. Нужно дождаться 5 часов перед восстановлением."""
    
    service = get_pet_service(db)
    result = await service.find_pet(pet_id, current_user.user_id)
    if not result.get("success"):
        raise ValidationError(result.get("message", "Не удалось начать поиск питомца"))
    return result


@pet_router.post("/{pet_id}/restore", response_model=PetSchema)
@rate_limit(limit=5, period=60)
@active_user_required
async def restore_lost_pet(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Попытаться восстановить потеянного питомца (75% успех, 25% неудача).
    Возможно только через 5 часов после начала поиска.
    """
    
    service = get_pet_service(db)
    result = await service.restore_pet(pet_id, current_user.user_id)
    
    if not result.get("success"):
        raise ValidationError(result.get("message", "Не удалось восстановить питомца"))
    
    pet = result.get("pet")
    if not pet:
        raise InternalServerError("Ошибка восстановления питомца")
    
    return PetSchema.model_validate(pet)

@pet_router.delete("/{pet_id}", response_model=dict, status_code=200)
@security_headers_check
@rate_limit(limit=5, period=60)
@active_user_required
async def delete_pet(
    pet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить питомца (мягкое удаление)."""
    
    service = get_pet_service(db)
    pet = await service.delete_pet(pet_id, current_user.user_id)
    if not pet:
        raise ValidationError("Питомец не найден или доступ запрещен")
    return {"message": "Питомец удален", "pet_id": pet_id}