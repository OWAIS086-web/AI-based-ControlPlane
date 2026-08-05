"""Stations controller."""
from app.schemas.common import make_paginated
from app.schemas.station import StationOut
from app.services import station_service


def _out(s) -> StationOut:
    return StationOut(
        id=s.id, name=s.name, lineId=s.lineId,
        processCount=len(s.processes or []),
        createdAt=s.createdAt, updatedAt=s.updatedAt,
    )


async def list_stations(line_id: str, page: int, limit: int) -> dict:
    result = await station_service.list_stations(line_id, page, limit)
    return make_paginated([_out(s) for s in result["stations"]], result["total"], page, limit)


async def create_station(line_id: str, name: str, actor_id: str) -> StationOut:
    return _out(await station_service.create_station(line_id, name, actor_id))


async def update_station(line_id: str, station_id: str, name: str, actor_id: str) -> StationOut:
    return _out(await station_service.update_station(line_id, station_id, name, actor_id))


async def delete_station(line_id: str, station_id: str, actor_id: str) -> None:
    await station_service.delete_station(line_id, station_id, actor_id)
