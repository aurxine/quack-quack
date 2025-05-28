from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.utils.connection_manager import manager
from src.services.chat_manager import process_message
from fastapi.responses import HTMLResponse
from fastapi import Request

router = APIRouter()

@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await manager.connect(websocket)
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
