"""Stations routes."""
from fastapi import APIRouter, Depends, Query

from app.controllers import station_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.station import StationCreate, StationOut, StationUpdate

router = APIRouter(prefix="/lines/{line_id}/stations", tags=["Stations"])


@router.get("", response_model=dict)
async def list_stations(
    line_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(get_current_user),
):
    return await station_controller.list_stations(line_id, page, limit)


@router.post("", response_model=StationOut, status_code=201)
async def create_station(
    line_id: str, body: StationCreate, current_user=Depends(require_process_manager)
):
    return await station_controller.create_station(line_id, body.name, current_user.id)


@router.patch("/{station_id}", response_model=StationOut)
async def update_station(
    line_id: str,
    station_id: str,
    body: StationUpdate,
    current_user=Depends(require_process_manager),
):
    return await station_controller.update_station(line_id, station_id, body.name, current_user.id)


@router.delete("/{station_id}", status_code=204)
async def delete_station(
    line_id: str, station_id: str, current_user=Depends(require_process_manager)
):
    await station_controller.delete_station(line_id, station_id, current_user.id)
