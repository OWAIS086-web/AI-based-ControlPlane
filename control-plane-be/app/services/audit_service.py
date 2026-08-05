"""Audit service — query ledger and aggregate stats."""
from datetime import datetime

from app.prisma_client import db
from app.utils.cache import cache_delete, cache_get, cache_set

_STATS_CACHE_KEY = "audit:stats"
_STATS_TTL = 60  # seconds


async def list_audit(
    type: str | None,
    performed_by: str | None,
    search: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
    page: int,
    limit: int,
) -> dict:
    where: dict = {}
    if type:
        where["type"] = type
    if performed_by:
        where["performedBy"] = performed_by
    if search:
        where["OR"] = [
            {"action": {"contains": search, "mode": "insensitive"}},
            {"target": {"contains": search, "mode": "insensitive"}},
        ]
    if from_date or to_date:
        where["createdAt"] = {}
        if from_date:
            where["createdAt"]["gte"] = from_date
        if to_date:
            where["createdAt"]["lte"] = to_date

    total = await db.auditentry.count(where=where)
    entries = await db.auditentry.find_many(
        where=where,
        skip=(page - 1) * limit,
        take=limit,
        include={"performer": True},
        order={"createdAt": "desc"},
    )
    return {"entries": entries, "total": total}


async def get_stats() -> dict:
    cached = await cache_get(_STATS_CACHE_KEY)
    if cached:
        return cached

    total = await db.auditentry.count()
    by_type: dict[str, int] = {}
    for audit_type in ["upload", "user", "station", "archive", "migrate", "model", "tool", "worker", "tool_request"]:
        by_type[audit_type] = await db.auditentry.count(where={"type": audit_type})

    result = {"total": total, "byType": by_type}
    await cache_set(_STATS_CACHE_KEY, result, ttl=_STATS_TTL)
    return result


async def invalidate_stats_cache() -> None:
    await cache_delete(_STATS_CACHE_KEY)
