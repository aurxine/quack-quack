from fastapi import WebSocket
from typing import List
import random

def random_color():
    # Generate a random hex color
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, dict] = {}  # WebSocket -> {"color": str, "user_id": str}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[websocket] = {
            "color": random_color(),
            "user_id": user_id,
        }

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def broadcast(self, message: str, sender: WebSocket):
        sender_meta = self.active_connections.get(sender, {"color": "#000000", "user_id": "unknown"})
        for connection in self.active_connections:
            await connection.send_json({
                "message": f"{sender_meta['user_id']}: {message}",
                "color": sender_meta["color"]
            })




# Shared singleton instance
manager = ConnectionManager()
