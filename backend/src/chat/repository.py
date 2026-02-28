from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config_log import logger
from src.db.models import Chat, Message, User, Pet, MessageType
from src.chat.schemas import ChatMessageCreate


class ChatRepository:
    """Репозиторий для чатов user <-> pet."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_direct_chat(self, creator_id: int, pet_id: int) -> Chat:
        user_query = select(User).where(User.user_id == creator_id)
        pet_query = select(Pet).where(Pet.pet_id == pet_id)

        user = (await self.session.execute(user_query)).scalars().first()
        pet = (await self.session.execute(pet_query)).scalars().first()
        if not user:
            raise ValueError("Пользователь не найден")
        if not pet:
            raise ValueError("Питомец не найден")

        exist_query = select(Chat).where(Chat.user_id == creator_id, Chat.pet_id == pet_id)
        existing = (await self.session.execute(exist_query)).scalars().first()
        if existing:
            return existing

        chat = Chat(user_id=creator_id, pet_id=pet_id)
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        logger.info(f"Создан чат {chat.chat_id} user={creator_id} pet={pet_id}")
        return chat

    async def get_chat_by_id(self, chat_id: int, include_messages: bool = False) -> Optional[Chat]:
        query = select(Chat).where(Chat.chat_id == chat_id)
        if include_messages:
            query = query.options(selectinload(Chat.messages))
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_user_chats(self, user_id: int, limit: int = 50, offset: int = 0) -> tuple[List[Chat], int]:
        query = select(Chat).where(Chat.user_id == user_id).order_by(desc(Chat.last_message_at))
        count_query = select(func.count(Chat.chat_id)).where(Chat.user_id == user_id)
        total = await self.session.scalar(count_query)
        result = await self.session.execute(query.limit(limit).offset(offset))
        chats = result.scalars().all()

        for chat in chats:
            setattr(chat, 'is_unread', getattr(chat, 'is_unread', False))

        return chats, total or 0

    async def is_member(self, chat_id: int, user_id: int) -> bool:
        query = select(Chat).where(Chat.chat_id == chat_id, Chat.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().first() is not None


class MessageRepository:
    """Репозиторий для сообщений."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        """Получить объект чата по идентификатору."""
        query = select(Chat).where(Chat.chat_id == chat_id)
        result = await self.session.execute(query)
        return result.scalars().first()
    
    async def create_message(self, chat_id: int, msg_type: MessageType, create_data: ChatMessageCreate, sender_id: Optional[int] = None) -> Message:
        """Создать сообщение в чате."""
        message = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            message_type=msg_type,
            content=create_data.content,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)

        # если это ответ ИИ, отмечаем чат как непрочитанный
        if msg_type == MessageType.AI:
            chat = await self.get_chat_by_id(chat_id)
            if chat:
                chat.is_unread = True
                await self.session.commit()

        logger.info(f"Создано сообщение {message.message_id} в чате {chat_id}")
        return message

    async def get_message_by_id(self, message_id: int) -> Optional[Message]:
        """Получить сообщение по ID, включая удаленные (для админов)."""
        query = select(Message).where(Message.message_id == message_id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_chat_messages(self, chat_id: int, limit: int = 50, offset: int = 0) -> List[Message]:
        """Получить сообщения чата в хронологическом порядке, исключая удаленные."""
        query = select(Message).where(Message.chat_id == chat_id, Message.is_deleted == False)
        query = query.order_by(desc(Message.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        messages = result.scalars().all()
        return list(reversed(messages))

    async def get_chat_messages_for_user(self, chat_id: int, user_id: int, limit: int = 50, offset: int = 0) -> List[Message]:
        """
        Получить сообщения чата для конкретного пользователя.
        """
        query = select(Message).where(Message.chat_id == chat_id, Message.is_deleted == False)
        query = query.order_by(desc(Message.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        messages = result.scalars().all()
        messages = list(reversed(messages))

        # помечаем чат как прочитанный
        chat = await self.get_chat_by_id(chat_id)
        if chat and chat.is_unread:
            chat.is_unread = False
            await self.session.commit()

        return messages

    async def update_message(self, message_id: int, content: str) -> Optional[Message]:
        """Обновить сообщение с переполучением объекта (медленнее, но возвращает обновленный объект)."""
        message = await self.get_message_by_id(message_id)
        if not message or message.is_deleted:
            return None
        message.content = content
        message.updated_at = datetime.now(timezone.utc)
        message.is_edited = True
        await self.session.commit()
        await self.session.refresh(message)
        return message
    
    async def update_message_direct(self, message_id: int, content: str) -> None:
        """Обновить сообщение БД без переполучения объекта (быстрое обновление)."""
        stmt = update(Message).where(Message.message_id == message_id).values(
            content=content,
            updated_at=datetime.now(timezone.utc),
            is_edited=True
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_message(self, message_id: int) -> bool:
        """
        Удалить ТОЛЬКО это сообщение.
        На сообщение устанавливается флаг is_deleted=True.
        """
        message = await self.get_message_by_id(message_id)
        if not message:
            return False
        message.is_deleted = True
        message.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        logger.debug(f"Сообщение {message_id} отмечено как удаленное (type={message.message_type})")
        return True

    async def get_recent_messages_for_context(self, chat_id: int, limit: int = 10) -> List[Message]:
        """
        Получить последние N сообщений для контекста при генерации ответа.
        Возвращает неудаленные сообщения в хронологическом порядке.
        """
        query = select(Message).where(
            Message.chat_id == chat_id, 
            Message.is_deleted == False
        )
        query = query.order_by(Message.created_at.desc()).limit(limit)
        res = await self.session.execute(query)
        messages = res.scalars().all()
        # Возвращаем в прямом порядке (старые -> новые)
        return list(reversed(messages))
    
    async def get_next_ai_message(self, chat_id: int, after_message_id: int, for_sender_id: Optional[int] = None) -> Optional[Message]:
        """Получить первое сообщение ИИ после указанного сообщения."""
        conditions = [
            Message.chat_id == chat_id,
            Message.message_id > after_message_id,
            Message.message_type == MessageType.AI,
            Message.is_deleted == False,
        ]
        if for_sender_id is not None:
            conditions.append(Message.sender_id == for_sender_id)

        query = select(Message).where(*conditions)
        query = query.order_by(Message.created_at.asc()).limit(1)
        res = await self.session.execute(query)
        return res.scalars().first()