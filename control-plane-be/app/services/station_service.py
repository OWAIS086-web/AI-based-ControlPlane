"""Station service."""
from app.core.exceptions import conflict, not_found
from app.prisma_client import db
from app.utils.audit import write_audit
from app.websocket.manager import ws_manager


async def list_stations(line_id: str, page: int, limit: int) -> dict:
    where = {"lineId": line_id, "deletedAt": None}
    total = await db.station.count(where=where)
    stations = await db.station.find_many(
        where=where,
        skip=(page - 1) * limit,
        take=limit,
        include={"processes": True},
        order={"createdAt": "asc"},
    )
    return {"stations": stations, "total": total}


async def create_station(line_id: str, name: str, actor_id: str):
    line = await db.assemblyline.find_unique(where={"id": line_id})
    if not line:
        raise not_found("Assembly line")

    duplicate = await db.station.find_first(where={"lineId": line_id, "name": name, "deletedAt": None})
    if duplicate:
        raise conflict(f"A station named '{name}' already exists on this line.")

    deleted = await db.station.find_first(
        where={"lineId": line_id, "name": name, "deletedAt": {"not": None}}
    )
    if deleted:
        station = await db.station.update(
            where={"id": deleted.id},
            data={"deletedAt": None},
            include={"processes": True},
        )
        await write_audit("station", f"Restored station: {name}", name, actor_id)
        await ws_manager.broadcast("station.created", {
            "id": station.id, "name": station.name, "lineId": station.lineId,
        })
        return station

    station = await db.station.create(
        data={"name": name, "line": {"connect": {"id": line_id}}}, include={"processes": True}
    )
    await write_audit("station", f"Created station: {name}", name, actor_id)
    await ws_manager.broadcast("station.created", {
        "id": station.id, "name": station.name, "lineId": station.lineId,
    })
    return station


async def update_station(line_id: str, station_id: str, name: str, actor_id: str):
    station = await db.station.find_first(where={"id": station_id, "lineId": line_id})
    if not station:
        raise not_found("Station")

    duplicate = await db.station.find_first(
        where={"lineId": line_id, "name": name, "id": {"not": station_id}, "deletedAt": None}
    )
    if duplicate:
        raise conflict(f"A station named '{name}' already exists on this line.")

    updated = await db.station.update(
        where={"id": station_id},
        data={"name": name},
        include={"processes": True},
    )
    await write_audit("station", f"Renamed station to: {name}", name, actor_id)
    return updated


async def delete_station(line_id: str, station_id: str, actor_id: str) -> None:
    from datetime import datetime, timezone

    station = await db.station.find_first(
        where={"id": station_id, "lineId": line_id, "deletedAt": None}
    )
    if not station:
        raise not_found("Station")

    active_processes = await db.process.count(
        where={"stationId": station_id, "status": {"not": "deleted"}}
    )
    if active_processes:
        raise conflict("Station has processes — migrate or delete all processes before removing the station.")

    await db.station.update(
        where={"id": station_id},
        data={"deletedAt": datetime.now(timezone.utc)},
    )
    await write_audit("station", f"Deleted station: {station.name}", station.name, actor_id)
    await ws_manager.broadcast("station.deleted", {"stationId": station_id, "lineId": line_id})
