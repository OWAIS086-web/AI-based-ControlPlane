"""System configuration service."""
from app.core.exceptions import unprocessable
from app.prisma_client import db
from app.schemas.config import CARD_DISPLAY_MODES

DEFAULTS = {
    "cardDisplayMode": "name",
}


async def _get(key: str) -> str:
    row = await db.systemconfig.find_unique(where={"key": key})
    return row.value if row else DEFAULTS[key]


async def get_config() -> dict:
    return {key: await _get(key) for key in DEFAULTS}


async def update_config(card_display_mode: str | None) -> dict:
    if card_display_mode is not None:
        if card_display_mode not in CARD_DISPLAY_MODES:
            raise unprocessable(f"cardDisplayMode must be one of {sorted(CARD_DISPLAY_MODES)}")
        await db.systemconfig.upsert(
            where={"key": "cardDisplayMode"},
            data={
                "create": {"key": "cardDisplayMode", "value": card_display_mode},
                "update": {"value": card_display_mode},
            },
        )
    return await get_config()
