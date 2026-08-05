from datetime import datetime

from pydantic import BaseModel


class StationOut(BaseModel):
    id: str
    name: str
    lineId: str
    processCount: int
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class StationCreate(BaseModel):
    name: str


class StationUpdate(BaseModel):
    name: str
