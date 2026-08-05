from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.user import UserOut


class AuditEntryOut(BaseModel):
    id: str
    type: str
    action: str
    target: str
    performedBy: str
    performer: UserOut | None = None
    metadata: dict[str, Any]
    createdAt: datetime

    model_config = {"from_attributes": True}


class AuditStatsOut(BaseModel):
    total: int
    byType: dict[str, int]
