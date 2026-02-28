import asyncio
from typing import Dict, Set
from fastapi import WebSocket

from src.core.config_log import logger


class ConnectionManager:
    """Управление WebSocket подключениями к чатам."""
    
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self.user_chats: Dict[int, Set[int]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int) -> None:
        """Подключить клиента к чату."""
        
        await websocket.accept()
        
        async with self._lock:
            if chat_id not in self.active_connections:
                self.active_connections[chat_id] = set()
            self.active_connections[chat_id].add(websocket)
            
            if user_id not in self.user_chats:
                self.user_chats[user_id] = set()
            self.user_chats[user_id].add(chat_id)
        
        logger.info(f"WebSocket подключен: user={user_id}, chat={chat_id}")
    
    async def disconnect(self, websocket: WebSocket, chat_id: int, user_id: int) -> None:
        """Отключить клиента от чата."""
        
        async with self._lock:
            if chat_id in self.active_connections:
                self.active_connections[chat_id].discard(websocket)
                if not self.active_connections[chat_id]:
                    del self.active_connections[chat_id]
            
            if user_id in self.user_chats:
                self.user_chats[user_id].discard(chat_id)
                if not self.user_chats[user_id]:
                    del self.user_chats[user_id]
        
        logger.info(f"WebSocket отключен: user={user_id}, chat={chat_id}")
    
    async def broadcast_to_chat(self, chat_id: int, message: dict) -> None:
        """Отправить сообщение всем подключенным клиентам в чате."""
        
        async with self._lock:
            connections = self.active_connections.get(chat_id, set()).copy()
        
        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Ошибка отправки WebSocket: {e}")
                disconnected.append(connection)
        
        if disconnected:
            async with self._lock:
                if chat_id in self.active_connections:
                    for conn in disconnected:
                        self.active_connections[chat_id].discard(conn)
    
    async def broadcast_to_user(self, user_id: int, message: dict) -> None:
        """Отправить сообщение всем чатам пользователя."""
        
        async with self._lock:
            chat_ids = self.user_chats.get(user_id, set()).copy()
        
        for chat_id in chat_ids:
            await self.broadcast_to_chat(chat_id, message)
    
    def get_chat_connections_count(self, chat_id: int) -> int:
        """Получить количество подключений к чату."""
        
        return len(self.active_connections.get(chat_id, set()))

ws_manager = ConnectionManager()

