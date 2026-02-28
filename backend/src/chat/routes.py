import asyncio
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.core.config_log import logger
from src.core.exceptions import ValidationError, AuthorizationError, NotFoundError, InternalServerError
from src.db.models import User, MessageType
from src.db.database import get_db
from src.cache import redis_service
from src.utils.decorators import cache, rate_limit, active_user_required, security_headers_check
from src.auth import get_current_user
from src.chat.services import get_chat_service, get_message_service
from src.chat.schemas import ChatRoomCreate, ChatRoomSchema, ChatMessageCreate, ChatMessageSchema


# Роуты для управления чатами и сообщениями
chat_router = APIRouter()

@chat_router.post("", response_model=ChatRoomSchema, status_code=201)
@security_headers_check
@rate_limit(limit=10, period=60)
@active_user_required
async def create_chat(
    request: Request,
    create_data: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать новый чат."""
    try:
        service = get_chat_service(db)
        chat = await service.create_chat(current_user.user_id, create_data)

        await redis_service.delete(f"user_chats:{current_user.user_id}")

        return ChatRoomSchema.model_validate(chat)
    except Exception as e:
        logger.error(f"Ошибка создания чата: {e}")
        raise InternalServerError("Не удалось создать чат")


@chat_router.get("", response_model=List[ChatRoomSchema], status_code=200)
@security_headers_check
@rate_limit(limit=20, period=60)
@active_user_required
@cache(ttl=30, key_prefix="user_chats")
async def get_user_chats(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить список чатов пользователя."""
    service = get_chat_service(db)
   
    chats, _ = await service.get_user_chats(current_user.user_id, limit, offset)
    return [ChatRoomSchema.model_validate(chat) for chat in chats]


@chat_router.get("/{chat_id}", response_model=ChatRoomSchema, status_code=200)
@rate_limit(limit=30, period=60)
@active_user_required
@cache(ttl=60, key_prefix="chat_detail")
async def get_chat(
    request: Request,
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить детальную информацию о чате."""
    service = get_chat_service(db)
    chat = await service.get_chat(chat_id, current_user.user_id, include_messages=False)
    if not chat:
        raise NotFoundError("Чат не найден или доступ ограничен")
    
    return ChatRoomSchema.model_validate(chat)

# Роуты для управления сообщениями в чатах
message_router = APIRouter()

@message_router.post("/chats/{chat_id}/messages", response_model=ChatMessageSchema, status_code=201)
@security_headers_check
@rate_limit(limit=15, period=60)
@active_user_required
async def send_message(
    request: Request,
    chat_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Отправить сообщение и получить ответ от ИИ (или fallback)."""
    if chat_id <= 0:
        raise ValidationError("Некорректный ID чата", field="chat_id")

    from src.chat.moderation import ContentFilter
    moderator = ContentFilter()
    validation = await moderator.validate_content(message_data.content)
    if not validation.get("is_allowed"):
        raise ValidationError("Сообщение не прошло авто модерацию", field="Контент сообщения", details=validation.get("violations", []))

    try:
        service = get_message_service(db)
        result = await service.send_message(chat_id, current_user.user_id, message_data)
        if not result:
            raise AuthorizationError("Доступ к чату запрещен")

        await asyncio.gather(
            redis_service.delete(f"chat_history:{chat_id}"),
            redis_service.delete("user_chats")
        )

        return ChatMessageSchema.model_validate(result["human_message"])
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        raise e if isinstance(e, (ValidationError, AuthorizationError)) else InternalServerError()


@message_router.get("/chats/{chat_id}/messages", response_model=List[ChatMessageSchema])
@security_headers_check
@rate_limit(limit=20, period=60)
@active_user_required
@cache(ttl=60, key_prefix="chat_history")
async def get_chat_messages(
    request: Request,
    chat_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить историю сообщений."""
    service = get_message_service(db)
    messages = await service.get_chat_history(
        chat_id, current_user.user_id, limit, offset
    )
    if messages is None:
        raise AuthorizationError("Нет доступа к истории этого чата")
    await redis_service.delete(f"chat_history:{chat_id}")
    await redis_service.delete("user_chats")
    return [ChatMessageSchema.model_validate(m) for m in messages]

@message_router.put("/messages/{message_id}", response_model=ChatMessageSchema)
@rate_limit(limit=10, period=60)
@active_user_required
async def edit_message(
    request: Request,
    message_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Редактирование сообщения (обновляет и перегенерирует ответ ИИ в фоне)."""
    service = get_message_service(db)
    result = await service.edit_message(
        message_id, current_user.user_id, message_data.content
    )
    
    if not result:
        raise NotFoundError("Сообщение не найдено или вы не автор")

    human_msg = result["human_message"]
    await redis_service.delete(f"chat_history:{human_msg.chat_id}")
    
    return ChatMessageSchema.model_validate(result["human_message"])


@message_router.delete("/messages/{message_id}")
@rate_limit(limit=10, period=60)
@active_user_required
async def delete_message(
    request: Request,
    message_id: int,
    delete_ai_response: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление сообщения.
    """
    service_msg = get_message_service(db)
    
    message = await service_msg.message_repo.get_message_by_id(message_id)
    if not message:
        raise NotFoundError("Сообщение не найдено")
    
    chat_id = message.chat_id
    
    success = await service_msg.delete_message(message_id, current_user.user_id)
    if not success:
        raise NotFoundError("Не удалось удалить сообщение")

    # Если параметр delete_ai_response=True И это HUMAN сообщение, то удалим и AI ответ
    if delete_ai_response and message.message_type == MessageType.HUMAN:
        ai_response = await service_msg.message_repo.get_next_ai_message(chat_id, message_id, for_sender_id=message.sender_id)
        if ai_response:
            await service_msg.message_repo.delete_message(ai_response.message_id)
            logger.info(f"AI ответ {ai_response.message_id} удален вместе с user сообщением {message_id}")

    if chat_id:
        await redis_service.delete(f"chat_history:{chat_id}")

    return {"success": True, "message": "Удалено"}
