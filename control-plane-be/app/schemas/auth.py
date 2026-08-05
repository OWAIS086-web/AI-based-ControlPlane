from pydantic import BaseModel

from app.schemas.common import EmailField
from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    email: EmailField
    password: str


class LoginResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int
    user: UserOut


class RefreshRequest(BaseModel):
    refreshToken: str


class RefreshResponse(BaseModel):
    accessToken: str
    expiresIn: int


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
