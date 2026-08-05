from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import EmailField


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    avatar: str | None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: EmailField
    role: str
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailField | None = None


class UserStatusUpdate(BaseModel):
    status: str  # active | inactive


class NotificationSettings(BaseModel):
    newUploads: bool | None = None
    migrations: bool | None = None
    userChanges: bool | None = None
    systemAlerts: bool | None = None


class UserSettingsOut(BaseModel):
    userId: str
    notifications: dict
    dataRetentionDays: int
    updatedAt: datetime

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    notifications: NotificationSettings | None = None
    dataRetentionDays: int | None = None
