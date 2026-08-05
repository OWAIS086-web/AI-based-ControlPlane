from datetime import datetime

from pydantic import BaseModel


class CarModelOut(BaseModel):
    id: str
    name: str
    code: str
    color: str
    status: str
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class CarModelCreate(BaseModel):
    name: str
    code: str
    color: str = "#3B82F6"


class CarModelUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    color: str | None = None


class CarModelStatusUpdate(BaseModel):
    status: str  # active | archived
