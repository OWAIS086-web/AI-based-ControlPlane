from datetime import datetime

from pydantic import BaseModel


class MigrationRecordOut(BaseModel):
    id: str
    fromLineId: str
    fromStationId: str
    toLineId: str
    toStationId: str
    processNames: list[str]
    status: str
    performedByName: str
    createdAt: datetime
    completedAt: datetime | None

    model_config = {"from_attributes": True}


class MigrationCreate(BaseModel):
    fromLineId: str
    fromStationId: str
    toLineId: str
    toStationId: str
    processIds: list[str]
