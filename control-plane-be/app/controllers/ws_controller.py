"""WebSocket controller — authenticated real-time push."""
from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.security import decode_token
from app.core.utils import ev
from app.prisma_client import db
from app.websocket.manager import ws_manager


async def websocket_endpoint(websocket: WebSocket, token: str) -> None:
    # Authenticate before accepting
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001)
            return
        user_id: str = payload.get("sub", "")
        user = await db.user.find_unique(where={"id": user_id})
        if not user or ev(user.status) == "inactive":
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
