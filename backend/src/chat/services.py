
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.core.config_log import logger
from src.db.models import Chat, Message, MessageType, Pet, User
from src.db.database import db_helper
from src.chat.repository import ChatRepository, MessageRepository
from src.chat.schemas import ChatRoomCreate, ChatMessageCreate
from src.ai import ai_service
from src.chat.websocket_manager import ws_manager


class ChatService:
    """Сервис для работы с прямыми чатами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.chat_repo = ChatRepository(session)
        self.message_repo = MessageRepository(session)

    async def create_chat(self, creator_id: int, create_data: ChatRoomCreate) -> Chat:
        """Создание нового чата (user <-> pet)."""
        pet_id = getattr(create_data, 'pet_id', None)
        if not pet_id:
            raise ValueError("pet_id обязательный параметр для создания чата.")
        chat = await self.chat_repo.create_direct_chat(creator_id, pet_id)
        return chat

    async def get_chat(self, chat_id: int, user_id: int, include_messages: bool = False) -> Optional[Chat]:
        """Получение чата с проверкой прав доступа."""
        chat = await self.chat_repo.get_chat_by_id(chat_id, include_messages=include_messages)
        
        if not chat:
            return None
        
        is_member = await self.chat_repo.is_member(chat_id, user_id)
        if not is_member:
            logger.warning(f"Попытка доступа к чату {chat_id} от пользователя {user_id}")
            return None
        
        return chat

    async def get_user_chats(self, user_id: int, limit: int = 50, offset: int = 0) -> tuple[List[Chat], int]:
        """Получение всех чатов пользователя."""
        return await self.chat_repo.get_user_chats(user_id, limit, offset)


class MessageService:
    """Сервис для работы с сообщениями."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.chat_repo = ChatRepository(session)
        self.message_repo = MessageRepository(session)

    async def send_message(self, chat_id: int, sender_id: int, create_data: ChatMessageCreate) -> Optional[Dict]:
        """
        Отправка сообщения пользователя в чат и генерация ответа от ИИ.
        Любой пользователь может писать любому питомцу.
        """
        chat = await self.chat_repo.get_chat_by_id(chat_id)
        if not chat:
            logger.warning(f"Чат {chat_id} не найден")
            return None

        pet = await self.session.get(Pet, chat.pet_id)
        if not pet or pet.is_deleted:
            logger.error(f"Питомец {chat.pet_id} не найден или удален")
            return None
        
        msg_type = MessageType.HUMAN
        human_message = await self.message_repo.create_message(
            chat_id, msg_type, create_data, sender_id=sender_id
        )
        
        chat.last_message_at = datetime.now(timezone.utc)
        await self.session.commit()

        async def _bg_generate_and_store_ai(chat_id: int, original_sender_id: int):
            try:
                async with db_helper.session_factory() as bg_session:
                    bg_chat_repo = ChatRepository(bg_session)
                    bg_msg_repo = MessageRepository(bg_session)
                    
                    bg_chat = await bg_chat_repo.get_chat_by_id(chat_id)
                    if not bg_chat:
                        logger.warning(f"Чат {chat_id} не найден")
                        return
                    
                    bg_pet = await bg_session.get(Pet, bg_chat.pet_id)
                    if not bg_pet or bg_pet.is_deleted:
                        logger.warning(f"Питомец {bg_chat.pet_id} не найден")
                        return

                    context = await bg_msg_repo.get_recent_messages_for_context(chat_id, limit=10)
                    is_owner_bg = (original_sender_id == bg_pet.owner_id)

                    ai_text = await ai_service.generate_response(bg_pet, context, is_owner=is_owner_bg)
                    if not ai_text:
                        ai_text = ai_service._get_fallback_response(is_owner=is_owner_bg)

                    ai_create = ChatMessageCreate(content=ai_text)
                    ai_message = await bg_msg_repo.create_message(
                        chat_id, MessageType.AI, ai_create, sender_id=original_sender_id
                    )

                    bg_chat.last_message_at = datetime.now(timezone.utc)
                    await bg_session.commit()
                    
                    # 🔥 ОТПРАВКА AI ОТВЕТА ЧЕРЕЗ WEBSOCKET
                    await self._send_ai_message_via_ws(ai_message, chat_id)
                    
                    try:
                        from src.cache import redis_service as _redis
                        await _redis.delete(f"chat_history:{chat_id}")
                        await _redis.delete("user_chats")
                    except Exception:
                        pass
                    
                    logger.info(f"Создан ответ ИИ для чата {chat_id}")
            except Exception as e:
                logger.exception(f"Ошибка при генерации: {e}")

        asyncio.create_task(_bg_generate_and_store_ai(chat.chat_id, sender_id))

        return {"human_message": human_message}

    async def _send_ai_message_via_ws(self, ai_message: Message, chat_id: int) -> None:
        """Отправить AI сообщение через WebSocket всем подключенным клиентам."""
        try:
            ws_message = {
                "type": "new_message",
                "message_id": ai_message.message_id,
                "chat_id": chat_id,
                "message_type": "ai",
                "content": ai_message.content,
                "created_at": ai_message.created_at.isoformat() if ai_message.created_at else None,
                "updated_at": ai_message.updated_at.isoformat() if ai_message.updated_at else None,
                "is_edited": ai_message.is_edited,
                "is_deleted": ai_message.is_deleted,
                "sender_id": ai_message.sender_id
            }
            await ws_manager.broadcast_to_chat(chat_id, ws_message)
            logger.debug(f"AI сообщение отправлено через WebSocket: chat={chat_id}, msg={ai_message.message_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки WebSocket: {e}")

    async def get_message(self, message_id: int) -> Optional[Message]:
        """Получение сообщения."""
        return await self.message_repo.get_message_by_id(message_id)

    async def get_chat_history(
        self, chat_id: int, user_id: int, 
        limit: int = 50, offset: int = 0
    ) -> Optional[List[Message]]:
        """Получение истории сообщений."""
        is_member = await self.chat_repo.is_member(chat_id, user_id)
        if not is_member:
            return None
        
        return await self.message_repo.get_chat_messages_for_user(chat_id, user_id, limit, offset)

    async def edit_message(
        self, message_id: int, editor_id: int, 
        content: str
    ) -> Optional[Dict]:
        """
        Редактирование сообщения (обновляет сообщение пользователя, перегенерация ответа ИИ в фоне).
        """
        message = await self.message_repo.get_message_by_id(message_id)
        if not message:
            return None
        
        chat = await self.chat_repo.get_chat_by_id(message.chat_id)
        if not chat:
            return None
        
        query = select(User).where(User.user_id == editor_id)
        editor = (await self.session.execute(query)).scalars().first()
        is_admin = bool(editor and getattr(editor, 'role_id', None) == 1)
        
        if not is_admin and getattr(message, 'sender_id', None) != editor_id:
            return None
        
        if message.message_type != MessageType.HUMAN:
            logger.warning(f"Попытка редактировать AI сообщение {message_id}")
            return None
        
        updated_human_message = await self.message_repo.update_message(message_id, content)
        
        async def _bg_regenerate_ai(chat_id: int, human_msg_id: int, editor_id: int):
            try:
                async with db_helper.session_factory() as bg_session:
                    bg_chat_repo = ChatRepository(bg_session)
                    bg_msg_repo = MessageRepository(bg_session)

                    ai_response = await bg_msg_repo.get_next_ai_message(
                        chat_id, human_msg_id, for_sender_id=editor_id
                    )
                    if not ai_response:
                        logger.debug(f"Нет AI ответа на сообщение {human_msg_id}")
                        return

                    context_messages = await bg_msg_repo.get_recent_messages_for_context(
                        chat_id, limit=10
                    )
                    
                    bg_chat = await bg_chat_repo.get_chat_by_id(chat_id)
                    if not bg_chat:
                        return
                    
                    bg_pet = await bg_session.get(Pet, bg_chat.pet_id)
                    if not bg_pet or bg_pet.is_deleted:
                        return

                    is_owner = editor_id == bg_pet.owner_id
                    ai_response_text = await ai_service.generate_response(
                        bg_pet, context_messages, is_owner=is_owner
                    )
                    
                    if ai_response_text:
                        await bg_msg_repo.update_message_direct(
                            ai_response.message_id, ai_response_text
                        )
                        
                        ai_response.content = ai_response_text
                        ai_response.updated_at = datetime.now(timezone.utc)
                        ai_response.is_edited = True
                        await self._send_ai_message_via_ws(ai_response, chat_id)
                        
                        logger.info(f"AI ответ перегенерирован для отредактированного сообщения {human_msg_id}")
                    
                    try:
                        from src.cache import redis_service as _redis
                        await _redis.delete(f"chat_history:{chat_id}")
                        await _redis.delete("user_chats")
                    except Exception:
                        pass
            except Exception as e:
                logger.exception(f"Ошибка при перегенерации AI: {e}")

        asyncio.create_task(_bg_regenerate_ai(message.chat_id, message_id, editor_id))

        return {"human_message": updated_human_message}

    async def delete_message(self, message_id: int, requester_id: int) -> bool:
        """
        Удаление сообщения.
        """
        message = await self.message_repo.get_message_by_id(message_id)
        if not message:
            return False
        
        query = select(User).where(User.user_id == requester_id)
        requester = (await self.session.execute(query)).scalars().first()
        is_admin = bool(requester and getattr(requester, 'role_id', None) == 1)
        
        if not is_admin and getattr(message, 'sender_id', None) != requester_id:
            return False

        result = await self.message_repo.delete_message(message_id)
        
        if result:
            ws_message = {
                "type": "message_deleted",
                "message_id": message_id,
                "chat_id": message.chat_id
            }
            await ws_manager.broadcast_to_chat(message.chat_id, ws_message)
        
        return result


def get_chat_service(session: AsyncSession) -> ChatService:
    """Получить экземпляр ChatService."""
    return ChatService(session)


def get_message_service(session: AsyncSession) -> MessageService:
    """Получить экземпляр MessageService."""
    return MessageService(session)
