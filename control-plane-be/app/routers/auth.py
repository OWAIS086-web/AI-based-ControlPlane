"""Auth routes."""
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.controllers import auth_controller
from app.dependencies import get_current_user
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, RefreshRequest, RefreshResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    return await auth_controller.login(body.email, body.password)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(body: RefreshRequest):
    return await auth_controller.refresh(body.refreshToken)


@router.post("/logout", status_code=204)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    await auth_controller.logout(credentials.credentials)


@router.post("/change-password", status_code=204)
async def change_password(body: ChangePasswordRequest, current_user=Depends(get_current_user)):
    await auth_controller.change_password(current_user.id, body.currentPassword, body.newPassword)
