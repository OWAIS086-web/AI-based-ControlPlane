"""Car models routes."""
from fastapi import APIRouter, Depends, Query

from app.controllers import car_model_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.car_model import CarModelCreate, CarModelOut, CarModelStatusUpdate, CarModelUpdate

router = APIRouter(prefix="/car-models", tags=["Car Models"])


@router.get("", response_model=dict)
async def list_car_models(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(get_current_user),
):
    return await car_model_controller.list_car_models(status, page, limit)


@router.post("", response_model=CarModelOut, status_code=201)
async def create_car_model(body: CarModelCreate, current_user=Depends(require_process_manager)):
    return await car_model_controller.create_car_model(body.name, body.code, body.color, current_user.id)


@router.patch("/{model_id}", response_model=CarModelOut)
async def update_car_model(
    model_id: str, body: CarModelUpdate, current_user=Depends(require_process_manager)
):
    return await car_model_controller.update_car_model(model_id, body.name, body.code, body.color, current_user.id)


@router.patch("/{model_id}/status", response_model=CarModelOut)
async def update_status(
    model_id: str, body: CarModelStatusUpdate, current_user=Depends(require_process_manager)
):
    return await car_model_controller.update_car_model_status(model_id, body.status, current_user.id)
