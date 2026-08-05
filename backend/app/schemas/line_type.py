from pydantic import BaseModel


class LineTypeOut(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    order: int

    model_config = {"from_attributes": True}


class LineTypeCreate(BaseModel):
    name: str
    icon: str = "factory"
    color: str = "#6366F1"


class LineTypeUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None


class LineTypeReorderRequest(BaseModel):
    ids: list[str]
