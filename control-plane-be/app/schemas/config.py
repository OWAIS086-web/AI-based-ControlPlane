from pydantic import BaseModel

CARD_DISPLAY_MODES = {"name", "filename"}


class SystemConfigOut(BaseModel):
    cardDisplayMode: str


class SystemConfigUpdate(BaseModel):
    cardDisplayMode: str | None = None
