from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from src.db.models import PetCharacter, PetFeature, PetState


MAX_PET_XP = 2_147_483_647

class BasePetSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PetCreate(BasePetSchema):
    """Схема для создания питомца."""
    pet_name: str = Field(..., max_length=100, description="Имя питомца")
    pet_species: str = Field("cat", max_length=50, description="Вид питомца")
    pet_color: str = Field("#FF0000", max_length=50, description="Цвет питомца")
    pet_character: PetCharacter = None
    pet_feature: PetFeature = None


class PetSchema(BasePetSchema):
    """Полная схема питомца с характеристиками и состоянием."""
    pet_id: int
    pet_name: str
    pet_species: str
    pet_color: str
    pet_character: Optional[PetCharacter]
    pet_feature: Optional[PetFeature]
    pet_state: Optional[PetState]
    pet_hunger: float
    pet_energy: float
    pet_happiness: float
    pet_cleanliness: float
    pet_health: float
    pet_xp: int = Field(0, ge=0, le=MAX_PET_XP)
    created_at: datetime
    last_updated: Optional[datetime]
    owner_id: int
    is_deleted: bool
    is_lost: bool = False
    lost_at: Optional[datetime] = None
    search_token_created_at: Optional[datetime] = None


class PetSchemaPublic(BasePetSchema):
    """Публичная схема питомца (без приватных stat полей)."""
    pet_id: int
    pet_name: str
    pet_species: str
    pet_color: str
    pet_character: Optional[PetCharacter]
    pet_feature: Optional[PetFeature]
    pet_state: Optional[PetState]
    pet_xp: int = Field(0, ge=0, le=MAX_PET_XP)
    created_at: datetime
    owner_id: int
    is_deleted: bool
    is_lost: bool = False


class PetUpdateStats(BasePetSchema):
    """Delta (прибавка/вычитание) к текущим характеристикам питомца."""
    pet_hunger: Optional[float] = Field(None, description="+/- к голоду")
    pet_energy: Optional[float] = Field(None, description="+/- к энергии")
    pet_happiness: Optional[float] = Field(None, description="+/- к счастью")
    pet_cleanliness: Optional[float] = Field(None, description="+/- к чистоте")
    pet_health: Optional[float] = Field(None, description="+/- к здоровью")
    pet_xp: Optional[int] = Field(None, description="+/- к опыту")


class PetUpdateWithChances(BasePetSchema):
    """Обновление характеристик с вероятностями.
    
    Пример: лечим 25 здоровья, но с шансом 50% может изменить настроение +/- 15.
    """
    pet_hunger_delta: Optional[float] = Field(None, description="+/- к голоду (базовое значение)")
    pet_hunger_chance: Optional[float] = Field(None, ge=0, le=100, description="Шанс в %")
    pet_hunger_variant: Optional[float] = Field(None, description="Альтернативное значение при срабатывании шанса")
    
    pet_energy_delta: Optional[float] = Field(None, description="+/- к энергии (базовое значение)")
    pet_energy_chance: Optional[float] = Field(None, ge=0, le=100, description="Шанс в %")
    pet_energy_variant: Optional[float] = Field(None, description="Альтернативное значение при срабатывании шанса")
    
    pet_happiness_delta: Optional[float] = Field(None, description="+/- к счастью (базовое значение)")
    pet_happiness_chance: Optional[float] = Field(None, ge=0, le=100, description="Шанс в %")
    pet_happiness_variant: Optional[float] = Field(None, description="Альтернативное значение при срабатывании шанса")
    
    pet_cleanliness_delta: Optional[float] = Field(None, description="+/- к чистоте (базовое значение)")
    pet_cleanliness_chance: Optional[float] = Field(None, ge=0, le=100, description="Шанс в %")
    pet_cleanliness_variant: Optional[float] = Field(None, description="Альтернативное значение при срабатывании шанса")
    
    pet_health_delta: Optional[float] = Field(None, description="+/- к здоровью (базовое значение)")
    pet_health_chance: Optional[float] = Field(None, ge=0, le=100, description="Шанс в %")
    pet_health_variant: Optional[float] = Field(None, description="Альтернативное значение при срабатывании шанса")
    
    pet_xp_delta: Optional[int] = Field(None, description="+/- к опыту (базовое значение)")
    pet_xp_chance: Optional[float] = Field(None, ge=0, le=100, description="Шанс в %")
    pet_xp_variant: Optional[int] = Field(None, description="Альтернативное значение при срабатывании шанса")


class PetRename(BasePetSchema):
    """Смена имени питомца"""
    pet_name: str = Field(..., max_length=100)


class PetRatingItem(BasePetSchema):
    """Питомец в рейтинге"""
    pet_id: int
    pet_name: str
    pet_species: str
    pet_color: str
    owner_id: int
    owner_login: str
    pet_xp: int = Field(..., ge=0, le=MAX_PET_XP)
    ranking_place: int

