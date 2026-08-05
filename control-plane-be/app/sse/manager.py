"""SSE connection manager for AI status push events."""
import asyncio
import json
from typing import Any, AsyncGenerator


class SSEManager:
    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings. Sends keepalive every 15s to prevent timeout."""
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._queues.append(q)
        try:
            while True:
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield data
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except (GeneratorExit, asyncio.CancelledError):
            pass
        finally:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    async def publish(self, event: str, payload: dict[str, Any]) -> None:
        if not self._queues:
            return
        msg = f"event: {event}\ndata: {json.dumps(payload)}\n\n"
        dead: list[asyncio.Queue] = []
        for q in self._queues:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            try:
                self._queues.remove(q)
            except ValueError:
                pass


# Singleton — imported everywhere
ai_sse = SSEManager()
