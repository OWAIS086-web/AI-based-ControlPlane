"""Maintenance auth routes."""
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import unauthorized
from app.core.security import hash_password, verify_password
from app.maintenance.dependencies import get_maintenance_db, get_current_maintenance_user
from app.maintenance.models import MaintenanceRefreshToken, MaintenanceUser, MaintenanceUserStatus
from app.maintenance.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MaintenanceUserOut,
    RefreshRequest,
    RefreshResponse,
)
from app.maintenance.security import (
    ACCESS_EXPIRE_SECONDS,
    REFRESH_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)

router = APIRouter(prefix="/maintenance/auth", tags=["Maintenance Auth"])
bearer_scheme = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_maintenance_db)):
    result = await db.execute(
        select(MaintenanceUser).where(MaintenanceUser.email == body.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise unauthorized("Invalid email or password.")
    if user.status == MaintenanceUserStatus.inactive:
        raise unauthorized("Account is inactive.")

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    token_obj = MaintenanceRefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS),
    )
    db.add(token_obj)
    await db.commit()

    return LoginResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        expiresIn=ACCESS_EXPIRE_SECONDS,
        user=MaintenanceUserOut.from_orm_model(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_maintenance_db)):
    try:
        payload = decode_token(body.refreshToken)
    except JWTError:
        raise unauthorized("Invalid or expired refresh token.")

    if payload.get("type") != "refresh" or payload.get("svc") != "maintenance":
        raise unauthorized("Not a maintenance refresh token.")

    result = await db.execute(
        select(MaintenanceRefreshToken).where(
            MaintenanceRefreshToken.token_hash == hash_token(body.refreshToken)
        )
    )
    stored = result.scalar_one_or_none()

    if not stored or stored.revoked:
        raise unauthorized("Refresh token has been revoked.")
    if stored.expires_at < datetime.now(timezone.utc):
        raise unauthorized("Refresh token expired.")

    user_result = await db.execute(
        select(MaintenanceUser).where(MaintenanceUser.id == stored.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise unauthorized("User not found.")

    return RefreshResponse(
        accessToken=create_access_token(user.id, user.role.value),
        expiresIn=ACCESS_EXPIRE_SECONDS,
    )


@router.post("/logout", status_code=204)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_maintenance_db),
):
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise unauthorized()

    user_id = payload.get("sub", "")
    result = await db.execute(
        select(MaintenanceRefreshToken).where(
            MaintenanceRefreshToken.user_id == user_id,
            MaintenanceRefreshToken.revoked == False,  # noqa: E712
        )
    )
    tokens = result.scalars().all()
    for t in tokens:
        t.revoked = True
    await db.commit()


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current_user: MaintenanceUser = Depends(get_current_maintenance_user),
    db: AsyncSession = Depends(get_maintenance_db),
):
    if not verify_password(body.currentPassword, current_user.hashed_password):
        raise unauthorized("Current password is incorrect.")
    current_user.hashed_password = hash_password(body.newPassword)
    await db.commit()
