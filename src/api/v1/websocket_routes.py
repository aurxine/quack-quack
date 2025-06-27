from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.core.redis import redis_client
from src.services.chat_manager import process_message
from src.utils.connection_manager import manager
from src.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)):
    logger.set_context(request_id=token)
    logger.debug(f"WebSocket connection attempt with token: {token}")
    user_id = redis_client.get(f"session:{token}")
    if not user_id:
        logger.warning(f"Invalid or expired token: {token}. Closing connection.")
        await websocket.close(code=1008)
        return

    # Get username for the user
    username = redis_client.get(f"user:{user_id}:username")
    if not username:
        username = user_id  # Fallback to user_id if username not found
    
    await manager.connect(websocket, user_id, username) # type: ignore
    logger.info(f"User {username} (ID: {user_id}) connected via WebSocket.")
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received message from user {username}: {data}")
            await manager.broadcast(data, sender=websocket)
            logger.debug(f"Broadcasted message from user {username}")
    except WebSocketDisconnect:
        logger.info(f"User {username} (ID: {user_id}) disconnected from WebSocket.")
        manager.disconnect(websocket)

@router.get("/chat", include_in_schema=False)
async def chat_page(request: Request):
    logger.debug("Serving chat HTML page.")
    with open("src/templates/chat.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)