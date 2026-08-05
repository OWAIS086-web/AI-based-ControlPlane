"""WebSocket route."""
from fastapi import APIRouter, WebSocket, Query

from app.controllers import ws_controller

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    await ws_controller.websocket_endpoint(websocket, token)
