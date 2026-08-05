"""Migrations controller."""
from app.core.utils import ev
from app.schemas.common import make_paginated
from app.schemas.migration import MigrationRecordOut
from app.services import migration_service


def _out(r) -> MigrationRecordOut:
    return MigrationRecordOut(
        id=r["id"], fromLineId=r["fromLineId"], fromStationId=r["fromStationId"],
        toLineId=r["toLineId"], toStationId=r["toStationId"],
        processNames=r["processNames"], status=ev(r["status"]),
        performedByName=r["performedByName"], createdAt=r["createdAt"], completedAt=r["completedAt"],
    )


async def list_migrations(status, from_line_id, page, limit) -> dict:
    result = await migration_service.list_migrations(status, from_line_id, page, limit)
    return make_paginated([_out(r) for r in result["records"]], result["total"], page, limit)


async def create_migration(from_line_id, from_station_id, to_line_id, to_station_id, process_ids, actor_id) -> MigrationRecordOut:
    record = await migration_service.create_migration(
        from_line_id, from_station_id, to_line_id, to_station_id, process_ids, actor_id,
    )
    return _out(record)


async def get_migration(migration_id: str) -> MigrationRecordOut:
    return _out(await migration_service.get_migration(migration_id))
