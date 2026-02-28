from typing import List, Optional
from datetime import datetime
import enum
from sqlalchemy import ForeignKey, String, Integer, Boolean, TIMESTAMP, Enum as SQLEnum, UniqueConstraint, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.database import Base


class UserStatus(str, enum.Enum):
    """Статусы пользователя в системе"""
    REGISTERED = "registered"  # Пользователь зарегистрирован, но не подтвердил почту
    ACTIVE = "active"          # Пользователь зарегистрирован и подтвердил почту
    BANNED = "banned"          # Пользователь заблокирован

class MessageType(str, enum.Enum):
    """Чье сообщение"""
    HUMAN = "human"      # Человек
    AI = "ai"            # ИИ 

class PetCharacter(str, enum.Enum):
    """Характеры питомцев"""

    PLAYFUL = "playful"     # Игривый
    LAZY = "lazy"           # Ленивый
    ENERGETIC = "energetic" # Энергичный
    CURIOUS = "curious"     # Любопытный
    SHY = "shy"             # Застенчивый

class PetFeature(str, enum.Enum):
    """Особенность питомца"""
    NORMAL = "normal"           # Нормальный без особенностей
    RAIN_LOVER = "rain_lover"   # Любитель дождя
    COLD_LOVER = "cold_lover"   # Любитель холода
    DAY_LOVER = "day_lover"     # Любитель день
    HOT_HATER = "hot_hater"     # Ненавидит жару
    SUN_HATER = "sun_hater"     # Ненавидит солнце
    RAIN_HATER = "rain_hater"   # Ненавидит дождь

class PetState(str, enum.Enum):
    """Состояние питомца"""
    NEUTRAL = "neutral"   # Нейтральный, счастье > 25
    SAD = "sad"           # Грустный, счастье < 25
    SICK1 = "sick1"       # Болезнь I: все статы < 20, потеря здоровья +0.5
    SICK2 = "sick2"       # Болезнь II: хоть одна стата = 0, потеря здоровья +1.0
    SICK3 = "sick3"       # Болезнь III: все статы < 5, потеря здоровья +2.0
    SLEEP = "sleep"       # Питомец спит
    PLAY = "play"         # Питомец играет
    

class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(50), nullable=False)
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    user_full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    user_password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_avatar: Mapped[str] = mapped_column(String(255), nullable=True, default="user-standart.jpg")
    
    registered_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.role_id", ondelete="RESTRICT"), default=1)
    status: Mapped[UserStatus] = mapped_column(SQLEnum(UserStatus), default=UserStatus.REGISTERED, nullable=False)

    banned_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    location_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    pets: Mapped[List["Pet"]] = relationship("Pet", back_populates="owner", cascade="all, delete-orphan")
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")
    role = relationship("Role", back_populates="users")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")

class UserToken(Base):
    __tablename__ = "user_tokens"

    token_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(32), nullable=False)

    requested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    user = relationship("User", back_populates="tokens")

class Pet(Base):
    __tablename__ = "pets"
    
    pet_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pet_name: Mapped[str] = mapped_column(String(20), nullable=False)
    pet_species: Mapped[str] = mapped_column(String(50), nullable=False, default="cat")
    pet_color: Mapped[str] = mapped_column(String(50), nullable=False, default="#D1A243")
    pet_character: Mapped[PetCharacter] = mapped_column(SQLEnum(PetCharacter), default=PetCharacter.PLAYFUL, nullable=False)
    pet_feature: Mapped[PetFeature] = mapped_column(SQLEnum(PetFeature), default=PetFeature.NORMAL, nullable=False)
    pet_state: Mapped[PetState] = mapped_column(SQLEnum(PetState), default=PetState.NEUTRAL, nullable=False)

    pet_hunger: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    pet_energy: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    pet_happiness: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    pet_cleanliness: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    pet_health: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    pet_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_updated: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lost_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    search_token_created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    
    owner = relationship("User", back_populates="pets")
    chats = relationship("Chat", back_populates="pet", cascade="all, delete-orphan")

class Chat(Base):
    __tablename__ = "chats"

    chat_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.pet_id", ondelete="CASCADE"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_unread: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "pet_id", name="uq_user_pet_chat"),
    )

    user = relationship("User", back_populates="chats")
    pet = relationship("Pet", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")
    
class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    message_type: Mapped[MessageType] = mapped_column(SQLEnum(MessageType), nullable=False)

    content: Mapped[str] = mapped_column(String(3000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    next_run: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payload: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)
    last_completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class EmailQueue(Base):
    __tablename__ = "email_queue"

    email_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(String(4000), nullable=False)
    is_html: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    next_try: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)
    
    