"""Dashboard routes."""
from fastapi import APIRouter, Depends

from app.controllers import dashboard_controller
from app.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def dashboard_stats(_=Depends(get_current_user)):
    return await dashboard_controller.get_stats()
