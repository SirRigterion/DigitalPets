
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query

from src.auth import get_current_user
from src.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat.websocket_manager import ws_manager
from src.chat.repository import ChatRepository


ws_router = APIRouter()

@ws_router.websocket("/ws/chats/{chat_id}")
async def chat_websocket(
    websocket: WebSocket,
    chat_id: int,
    token: str = Query(..., description="JWT токен авторизации"),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket подключение к чату для получения сообщений в реальном времени.
    
    Клиент подключается:
    wss://localhost/ws/chats/{chatId}?token={jwt_token}
    """
    try:
        current_user = await get_current_user(token=token, db=db)
    except Exception as e:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    chat_repo = ChatRepository(db)
    is_member = await chat_repo.is_member(chat_id, current_user.user_id)
    
    if not is_member:
        await websocket.close(code=4003, reason="Access denied to this chat")
        return
    
    await ws_manager.connect(websocket, chat_id, current_user.user_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "chat_id": chat_id,
            "user_id": current_user.user_id
        })
        
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket, chat_id, current_user.user_id)

