import re
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Модель для регистрации нового пользователя с расширенной валидацией полей."""
    user_login: str = Field(min_length=3, max_length=50, strip_whitespace=True, description="Уникальный логин пользователя")
    user_full_name: str = Field(min_length=2, max_length=100, strip_whitespace=True, description="Полное имя пользователя")
    user_email: EmailStr = Field(min_length=3, max_length=100, description="Электронная почта пользователя")
    user_password: str = Field(min_length=8, max_length=128, description="Пароль пользователя")

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
    
    @field_validator("user_password")
    def validate_password(cls, value: str) -> str:
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$', value):
            raise ValueError("Пароль должен содержать минимум 8 символов, включая заглавную букву, строчную букву, цифру и спецсимвол (!@#$%^&*)")
        return value

class UserLogin(BaseModel):
    """Модель для входа пользователя, допускает логин или email в качестве идентификатора."""
    user_identifier: str = Field(min_length=3, max_length=50, description="Логин или email пользователя")
    password: str = Field(min_length=8, max_length=255, description="Пароль пользователя")


class TokenResponse(BaseModel):
    """Ответ с access token и refresh token"""
    detail: str = Field(description="Сообщение для пользователя")
    refresh_token: str = Field(description="Refresh token для обновления access token")


class RefreshTokenRequest(BaseModel):
    """Запрос на обновление access token"""
    refresh_token: str = Field(description="Refresh token для получения нового access token")