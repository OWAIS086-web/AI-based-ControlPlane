"""System configuration routes."""
from fastapi import APIRouter, Depends

from app.controllers import config_controller
from app.dependencies import get_current_user, require_process_manager
from app.schemas.config import SystemConfigOut, SystemConfigUpdate

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("", response_model=SystemConfigOut)
async def get_config(_=Depends(get_current_user)):
    return await config_controller.get_config()


@router.patch("", response_model=SystemConfigOut)
async def update_config(body: SystemConfigUpdate, _=Depends(require_process_manager)):
    return await config_controller.update_config(body.cardDisplayMode)
