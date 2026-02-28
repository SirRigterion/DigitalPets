from typing import Any, Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, BeforeValidator

from src.db.models import MessageType


def normalize_id(v: Any) -> Optional[int]:
    """Универсальный нормализатор для ID: чистит строки, 0 и None."""
    if v is None or v == "" or v == 0:
        return None
    try:
        val = int(v)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None

PositiveInt = Annotated[int, BeforeValidator(normalize_id)]


class BaseSchemaChat(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ChatRoomCreate(BaseSchemaChat):
    pet_id: int = Field(..., description="ID питомца для общения")

    @field_validator('pet_id', mode='before')
    @classmethod
    def clean_pet_id(cls, v: Any) -> Optional[int]:
        return normalize_id(v)
    
class ChatRoomSchema(BaseSchemaChat):
    chat_id: int
    user_id: int
    pet_id: int
    created_at: datetime
    last_message_at: Optional[datetime] = None
    is_unread: bool = False

class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=3000, description="Текст сообщения")

class ChatMessageSchema(BaseSchemaChat):
    message_id: int
    chat_id: int
    message_type: MessageType
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_edited: bool = False
    is_deleted: bool = False