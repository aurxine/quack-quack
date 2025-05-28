from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.utils.connection_manager import get_connection_manager
from src.services.chat_manager import process_message


router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    manager = get_connection_manager()
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            processed = await process_message(data)
            await manager.broadcast(processed)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
