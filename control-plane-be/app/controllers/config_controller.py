"""System config controller."""
from app.schemas.config import SystemConfigOut
from app.services import config_service


async def get_config() -> SystemConfigOut:
    data = await config_service.get_config()
    return SystemConfigOut(**data)


async def update_config(card_display_mode: str | None) -> SystemConfigOut:
    data = await config_service.update_config(card_display_mode)
    return SystemConfigOut(**data)
