"""Redis cache helpers."""
import json
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _pool


async def cache_get(key: str) -> Any | None:
    r = get_redis()
    value = await r.get(key)
    return json.loads(value) if value else None


async def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    r = get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))


async def cache_delete(key: str) -> None:
    r = get_redis()
    await r.delete(key)


async def cache_delete_pattern(pattern: str) -> None:
    r = get_redis()
    keys = await r.keys(pattern)
    if keys:
        await r.delete(*keys)
