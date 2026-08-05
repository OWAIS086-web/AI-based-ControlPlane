"""Dashboard controller."""
from app.services import dashboard_service


async def get_stats():
    return await dashboard_service.get_stats()
