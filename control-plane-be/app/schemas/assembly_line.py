from pydantic import BaseModel

from app.schemas.user import UserOut


class AssemblyLineOut(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    stationCount: int
    managerId: str | None
    manager: UserOut | None = None
    lineTypeId: str | None = None
    order: int = 0

    model_config = {"from_attributes": True}


class AssemblyLineCreate(BaseModel):
    name: str
    icon: str = "factory"
    color: str = "#6366F1"
    lineTypeId: str | None = None


class AssemblyLineUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    lineTypeId: str | None = None


class AssemblyLineReorderRequest(BaseModel):
    ids: list[str]


class AssignManagerRequest(BaseModel):
    managerId: str | None
