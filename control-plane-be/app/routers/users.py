"""Users routes."""
from fastapi import APIRouter, Depends, Query

from app.controllers import user_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.user import (
    UserCreate,
    UserOut,
    UserSettingsOut,
    UserSettingsUpdate,
    UserStatusUpdate,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=dict)
async def list_users(
    role: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _=Depends(require_process_manager),
):
    return await user_controller.list_users(role, status, page, limit)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, current_user=Depends(require_process_manager)):
    return await user_controller.create_user(body.name, body.email, body.role, body.password, current_user.id)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, _=Depends(get_current_user)):
    return await user_controller.get_user(user_id)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: str, body: UserUpdate, current_user=Depends(get_current_user)):
    return await user_controller.update_user(user_id, body.name, body.email, current_user)


@router.patch("/{user_id}/status", response_model=UserOut)
async def update_status(
    user_id: str, body: UserStatusUpdate, current_user=Depends(require_process_manager)
):
    return await user_controller.update_user_status(user_id, body.status, current_user.id)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: str, current_user=Depends(require_process_manager)):
    await user_controller.delete_user(user_id, current_user.id)


@router.get("/{user_id}/settings", response_model=UserSettingsOut)
async def get_settings(user_id: str, current_user=Depends(get_current_user)):
    return await user_controller.get_settings(user_id, current_user)


@router.patch("/{user_id}/settings", response_model=UserSettingsOut)
async def update_settings(
    user_id: str, body: UserSettingsUpdate, current_user=Depends(get_current_user)
):
    n = body.notifications or {}
    notif_data = n if isinstance(n, dict) else n.model_dump(exclude_none=True)
    return await user_controller.update_settings(user_id, notif_data, body.dataRetentionDays, current_user)
