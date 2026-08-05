"""WebSocket connection manager for real-time push events."""
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # user_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)

    async def broadcast(self, event: str, payload: Any) -> None:
        """Send an event to every connected client."""
        message = json.dumps(
            {
                "event": event,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            default=str,
        )
        dead: list[tuple[str, WebSocket]] = []
        for user_id, sockets in list(self._connections.items()):
            for ws in list(sockets):
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append((user_id, ws))

        for user_id, ws in dead:
            self.disconnect(ws, user_id)

    async def send_to_user(self, user_id: str, event: str, payload: Any) -> None:
        """Send an event to a specific user's connections."""
        message = json.dumps(
            {
                "event": event,
                "payload": payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            default=str,
        )
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws, user_id)


ws_manager = ConnectionManager()
