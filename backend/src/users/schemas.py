from datetime import datetime
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from src.db.models import UserStatus


class UserProfile(BaseModel):
    """Модель для отображения профиля пользователя."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: int
    user_login: str
    user_full_name: str
    user_email: EmailStr
    user_avatar: Optional[str] = Field(default="user-standart.jpg")
    role_id: int
    registered_at: datetime
    is_deleted: bool
    status: UserStatus
    ban_reason: Optional[str]
    banned_at: Optional[datetime]

    @field_validator("user_login")
    def validate_login(cls, value: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValueError("Логин пользователя может содержать только английские буквы, цифры и подчеркивание")
        return value

    @field_validator("user_full_name")
    def validate_full_name(cls, value: str) -> str:
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', value):
            raise ValueError("Полное имя может содержать только русские или английские буквы, пробелы и дефис")
        return value

    @field_validator("user_email", mode="before")
    @classmethod
    def validate_email_format(cls, value: EmailStr) -> EmailStr:
        if isinstance(value, str):
            if "@" not in value or "." not in value:
                raise ValueError("Введите корректный адрес электронной почты (например, example@mail.ru)")
        return value


class UserUpdate(BaseModel):
    """Модель для обновления профиля пользователя."""
    user_login: Optional[str] = Field(default=None, min_length=3, max_length=50)
    user_full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    user_email: Optional[EmailStr] = Field(default=None)

    @field_validator("user_login")
    def validate_login(cls, value: str) -> str:
        if value is not None and not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValueError("Логин пользователя может содержать только английские буквы, цифры и подчеркивание")
        return value

    @field_validator("user_full_name")
    def validate_full_name(cls, value: str) -> str:
        if value is not None and not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', value):
            raise ValueError("Полное имя может содержать только русские или английские буквы, пробелы и дефис")
        return value

    @field_validator("user_email", mode="before")
    @classmethod
    def validate_email_format(cls, value: EmailStr) -> EmailStr:
        if isinstance(value, str):
            if "@" not in value or "." not in value:
                raise ValueError("Введите корректный адрес электронной почты (например, example@mail.ru)")
        return value


class UserRestoreRequest(BaseModel):
    """"Модель для запроса восстановления пароля."""
    full_name: str
    login: str
    password: str

    @field_validator("login")
    def validate_login(cls, value: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValueError("Логин пользователя может содержать только английские буквы, цифры и подчеркивание")
        return value

    @field_validator("full_name")
    def validate_full_name(cls, value: str) -> str:
        if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s\-]+$', value):
            raise ValueError("Полное имя может содержать только русские или английские буквы, пробелы и дефис")
        return value

    @field_validator("password")
    def validate_password(cls, value: str) -> str:
        # Регулярка требует: 1 заглавную, 1 строчную, 1 цифру, 1 спецсимвол, минимум 8 символов
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$', value):
            raise ValueError("Пароль должен содержать минимум 8 символов, включая заглавную букву, строчную букву, цифру и спецсимвол (!@#$%^&*)")
        return value

class UserLocationUpdate(BaseModel):
    """Модель для обновления геолокации пользователя."""
    latitude: float
    longitude: float


class ResetPasswordConfirm(BaseModel):
    """Модель для подтверждения сброса пароля."""
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    def validate_password(cls, value: str) -> str:
        # Регулярка требует: 1 заглавную, 1 строчную, 1 цифру, 1 спецсимвол, минимум 8 символов
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$'
        if not re.match(pattern, value):
            raise ValueError("Пароль должен содержать минимум 8 символов, включая заглавную букву, строчную букву, цифру и спецсимвол (!@#$%^&*)")
        return value