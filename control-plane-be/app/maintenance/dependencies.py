"""FastAPI dependencies for the maintenance module."""
from typing import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import forbidden, unauthorized
from app.maintenance.database import AsyncSessionLocal
from app.maintenance.models import MaintenanceUser, MaintenanceUserStatus
from app.maintenance.security import decode_token

bearer_scheme = HTTPBearer()


async def get_maintenance_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_maintenance_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_maintenance_db),
) -> MaintenanceUser:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise unauthorized()

    if payload.get("type") != "access" or payload.get("svc") != "maintenance":
        raise unauthorized("Invalid token.")

    user_id: str = payload.get("sub", "")
    result = await db.execute(select(MaintenanceUser).where(MaintenanceUser.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise unauthorized("User not found.")
    if user.status == MaintenanceUserStatus.inactive:
        raise forbidden("Account is inactive.")
    return user


async def require_maintenance_admin(
    current_user: MaintenanceUser = Depends(get_current_maintenance_user),
) -> MaintenanceUser:
    if current_user.role.value != "admin":
        raise forbidden("Requires maintenance admin role.")
    return current_user
