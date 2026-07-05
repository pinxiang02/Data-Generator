import json
from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        # Stores active browser connections per generator_id
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, generator_id: int):
        await websocket.accept()
        if generator_id not in self.active_connections:
            self.active_connections[generator_id] = []
        self.active_connections[generator_id].append(websocket)

    def disconnect(self, websocket: WebSocket, generator_id: int):
        if generator_id in self.active_connections:
            if websocket in self.active_connections[generator_id]:
                self.active_connections[generator_id].remove(websocket)

    async def broadcast(self, generator_id: int, message_type: str, data: dict):
        """Sends data to the UI consoles. Dead connections are dropped, never raised."""
        if generator_id in self.active_connections:
            message = json.dumps({"type": message_type, "content": data})
            dead = []
            for connection in list(self.active_connections[generator_id]):
                try:
                    await connection.send_text(message)
                except Exception:
                    dead.append(connection)
            for connection in dead:
                self.disconnect(connection, generator_id)

ws_manager = ConnectionManager()