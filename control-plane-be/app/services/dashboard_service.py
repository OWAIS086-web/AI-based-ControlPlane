"""Dashboard aggregation service."""
from app.core.utils import ev
from app.prisma_client import db
from app.utils.cache import cache_get, cache_set

_CACHE_KEY = "dashboard:stats"
_TTL = 60


async def get_stats() -> dict:
    cached = await cache_get(_CACHE_KEY)
    if cached:
        return cached

    total_stations = await db.station.count()
    total_processes = await db.process.count()
    total_car_models = await db.carmodel.count(where={"status": "active"})
    missing_cp_count = await db.process.count(where={"hasMissingCp": True, "status": "active"})

    lines_raw = await db.assemblyline.find_many(include={"stations": True})
    lines = []
    for line in lines_raw:
        station_ids = [s.id for s in (line.stations or [])]
        process_count = await db.process.count(where={"lineId": line.id}) if station_ids else 0
        missing = (
            await db.process.count(where={"lineId": line.id, "hasMissingCp": True, "status": "active"})
            if station_ids else 0
        )
        lines.append({
            "id": line.id,
            "name": line.name,
            "stationCount": len(line.stations or []),
            "processCount": process_count,
            "missingCPCount": missing,
            "managerId": line.managerId,
        })

    recent_activity = await db.auditentry.find_many(
        take=10, order={"createdAt": "desc"}, include={"performer": True}
    )

    result = {
        "totalStations": total_stations,
        "totalProcesses": total_processes,
        "totalCarModels": total_car_models,
        "missingCPCount": missing_cp_count,
        "lines": lines,
        "recentActivity": [
            {
                "id": e.id,
                "type": ev(e.type),
                "action": e.action,
                "target": e.target,
                "performedBy": e.performedBy,
                "metadata": e.metadata,
                "createdAt": e.createdAt.isoformat(),
            }
            for e in recent_activity
        ],
    }
    await cache_set(_CACHE_KEY, result, ttl=_TTL)
    return result
