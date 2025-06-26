from fastapi import WebSocket
from typing import List
import random
from src.core.logger import get_logger

logger = get_logger(__name__)
def random_color():
    # Generate a random hex color
    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    logger.debug(f"Generated random color: {color}")
    return color

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, dict] = {}  # WebSocket -> {"color": str, "user_id": str}
        logger.debug("Initialized ConnectionManager with empty active_connections.")

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        color = random_color()
        self.active_connections[websocket] = {
            "color": color,
            "user_id": user_id,
        }
        logger.debug(f"WebSocket {websocket} connected with user_id: {user_id}, color: {color}.")
        logger.debug(f"Current active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        removed = self.active_connections.pop(websocket, None)
        if removed:
            logger.debug(f"WebSocket {websocket} disconnected. User info: {removed}")
        else:
            logger.debug(f"WebSocket {websocket} disconnect attempted, but not found.")
        logger.debug(f"Current active connections: {len(self.active_connections)}")

    async def broadcast(self, message: str, sender: WebSocket):
        sender_meta = self.active_connections.get(sender, {"color": "#000000", "user_id": "unknown"})
        logger.debug(f"Broadcasting message from user_id: {sender_meta['user_id']} with color: {sender_meta['color']}")
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "message": f"{sender_meta['user_id']}: {message}",
                    "color": sender_meta["color"]
                })
                logger.debug(f"Sent message to WebSocket {connection}")
            except Exception as e:
                logger.error(f"Error sending message to WebSocket {connection}: {e}")

# Shared singleton instance
manager = ConnectionManager()
