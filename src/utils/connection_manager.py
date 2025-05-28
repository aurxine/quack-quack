from fastapi import WebSocket
from typing import List
import random

def random_color():
    # Generate a random hex color
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {}  # WebSocket -> color

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = random_color()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def broadcast(self, message: str, sender: WebSocket):
        color = self.active_connections.get(sender, "#000000")
        for connection in self.active_connections:
            await connection.send_json({"message": message, "color": color})



# Shared singleton instance
manager = ConnectionManager()
