"""Migration service — async process migration between stations."""
import asyncio
from datetime import datetime, timezone

from app.core.exceptions import conflict, not_found, unprocessable
from app.core.utils import ev
from app.prisma_client import db
from app.utils.audit import write_audit
from app.websocket.manager import ws_manager


def _enrich(record, name_map: dict) -> dict:
    return {
        "id": record.id,
        "fromLineId": record.fromLineId,
        "fromStationId": record.fromStationId,
        "toLineId": record.toLineId,
        "toStationId": record.toStationId,
        "processNames": [name_map.get(pid, pid) for pid in record.processIds],
        "status": record.status,
        "performedByName": record.performer.name,
        "createdAt": record.createdAt,
        "completedAt": record.completedAt,
    }


async def list_migrations(
    status: str | None,
    from_line_id: str | None,
    page: int,
    limit: int,
) -> dict:
    where: dict = {}
    if status:
        where["status"] = status
    if from_line_id:
        where["fromLineId"] = from_line_id

    total = await db.migrationrecord.count(where=where)
    records = await db.migrationrecord.find_many(
        where=where, skip=(page - 1) * limit, take=limit,
        order={"createdAt": "desc"}, include={"performer": True},
    )
    all_pids = list({pid for r in records for pid in r.processIds})
    processes = await db.process.find_many(where={"id": {"in": all_pids}}) if all_pids else []
    name_map = {p.id: p.name for p in processes}
    return {"records": [_enrich(r, name_map) for r in records], "total": total}


async def get_migration(migration_id: str):
    record = await db.migrationrecord.find_unique(
        where={"id": migration_id}, include={"performer": True}
    )
    if not record:
        raise not_found("Migration record")
    processes = await db.process.find_many(where={"id": {"in": record.processIds}})
    name_map = {p.id: p.name for p in processes}
    return _enrich(record, name_map)


async def create_migration(
    from_line_id: str,
    from_station_id: str,
    to_line_id: str,
    to_station_id: str,
    process_ids: list[str],
    actor_id: str,
):
    if from_station_id == to_station_id and from_line_id == to_line_id:
        raise unprocessable("Source and destination station are the same.")

    if not await db.station.find_first(where={"id": from_station_id, "lineId": from_line_id}):
        raise not_found("Source station")
    to_station = await db.station.find_first(where={"id": to_station_id, "lineId": to_line_id})
    if not to_station:
        raise not_found("Destination station")

    # Validate all processes exist and are not already being migrated
    process_name_map: dict[str, str] = {}
    for pid in process_ids:
        process = await db.process.find_unique(where={"id": pid})
        if not process:
            raise not_found(f"Process {pid}")
        process_name_map[pid] = process.name
        in_flight = await db.migrationrecord.find_first(
            where={"processIds": {"has": pid}, "status": "pending"}
        )
        if in_flight:
            raise conflict(f"Process {pid} is already being migrated.")

    record = await db.migrationrecord.create(
        data={
            "fromLineId": from_line_id,
            "fromStationId": from_station_id,
            "toLineId": to_line_id,
            "toStationId": to_station_id,
            "processIds": process_ids,
            "performer": {"connect": {"id": actor_id}},
        },
        include={"performer": True},
    )

    # Run synchronously — migration is pure DB updates, no heavy work
    await _run_migration(
        record.id, process_ids, to_line_id, to_station_id,
        to_station.name, process_name_map, actor_id,
    )
    # Re-fetch to get the completed status
    record = await db.migrationrecord.find_unique(
        where={"id": record.id}, include={"performer": True}
    )
    return _enrich(record, process_name_map)


async def _run_migration(
    record_id: str,
    process_ids: list[str],
    to_line_id: str,
    to_station_id: str,
    to_station_name: str,
    process_name_map: dict[str, str],
    actor_id: str,
) -> None:
    """Background task: move processes and update migration status."""
    try:
        for pid in process_ids:
            await db.process.update(
                where={"id": pid},
                data={"lineId": to_line_id, "stationId": to_station_id},
            )

        completed = await db.migrationrecord.update(
            where={"id": record_id},
            data={"status": "completed", "completedAt": datetime.now(timezone.utc)},
        )
        process_names = [process_name_map.get(pid, pid) for pid in process_ids]
        await write_audit(
            "migrate",
            f"Migrated {len(process_ids)} process(es) to station {to_station_name}",
            to_station_name,
            actor_id,
            {"migrationId": record_id, "processNames": process_names},
        )
        payload = {
            "id": completed.id, "status": ev(completed.status),
            "processIds": completed.processIds,
        }
        await ws_manager.broadcast("migration.completed", payload)
    except Exception as exc:
        failed = await db.migrationrecord.update(
            where={"id": record_id},
            data={"status": "failed"},
        )
        payload = {"id": record_id, "status": "failed", "error": str(exc)}
        await ws_manager.broadcast("migration.failed", payload)
