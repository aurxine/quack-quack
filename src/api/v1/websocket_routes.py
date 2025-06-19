from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from src.core.redis import redis_client
from src.services.chat_manager import process_message
from src.utils.connection_manager import manager

router = APIRouter()

@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)):
    user_id = redis_client.get(f"session:{token}")
    if not user_id:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id) # type: ignore
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(data, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)



@router.get("/chat", include_in_schema=False)
async def chat_page(request: Request):
    with open("src/templates/chat.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
