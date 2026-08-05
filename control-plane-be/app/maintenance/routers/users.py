"""Maintenance user management routes — admin only."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import conflict, not_found
from app.core.security import hash_password
from app.maintenance.dependencies import (
    get_maintenance_db,
    get_current_maintenance_user,
    require_maintenance_admin,
)
from app.maintenance.models import MaintenanceUser, MaintenanceUserRole, MaintenanceUserStatus
from app.maintenance.schemas import (
    MaintenanceUserCreate,
    MaintenanceUserOut,
    MaintenanceUserStatusUpdate,
    MaintenanceUserUpdate,
)

router = APIRouter(prefix="/maintenance/users", tags=["Maintenance Users"])


@router.get("", response_model=list[MaintenanceUserOut])
async def list_users(
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(require_maintenance_admin),
):
    result = await db.execute(
        select(MaintenanceUser).order_by(MaintenanceUser.created_at.desc())
    )
    users = result.scalars().all()
    return [MaintenanceUserOut.from_orm_model(u) for u in users]


@router.post("", response_model=MaintenanceUserOut, status_code=201)
async def create_user(
    body: MaintenanceUserCreate,
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(require_maintenance_admin),
):
    existing = await db.execute(
        select(MaintenanceUser).where(MaintenanceUser.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise conflict(f"Email {body.email} already in use.")

    user = MaintenanceUser(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=MaintenanceUserRole(body.role),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return MaintenanceUserOut.from_orm_model(user)


@router.get("/me", response_model=MaintenanceUserOut)
async def get_me(current_user: MaintenanceUser = Depends(get_current_maintenance_user)):
    return MaintenanceUserOut.from_orm_model(current_user)


@router.get("/{user_id}", response_model=MaintenanceUserOut)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(require_maintenance_admin),
):
    result = await db.execute(select(MaintenanceUser).where(MaintenanceUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise not_found("Maintenance user")
    return MaintenanceUserOut.from_orm_model(user)


@router.patch("/{user_id}", response_model=MaintenanceUserOut)
async def update_user(
    user_id: str,
    body: MaintenanceUserUpdate,
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(require_maintenance_admin),
):
    result = await db.execute(select(MaintenanceUser).where(MaintenanceUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise not_found("Maintenance user")

    if body.name is not None:
        user.name = body.name
    if body.email is not None:
        dup = await db.execute(
            select(MaintenanceUser).where(
                MaintenanceUser.email == body.email, MaintenanceUser.id != user_id
            )
        )
        if dup.scalar_one_or_none():
            raise conflict(f"Email {body.email} already in use.")
        user.email = body.email

    await db.commit()
    await db.refresh(user)
    return MaintenanceUserOut.from_orm_model(user)


@router.patch("/{user_id}/status", response_model=MaintenanceUserOut)
async def update_user_status(
    user_id: str,
    body: MaintenanceUserStatusUpdate,
    db: AsyncSession = Depends(get_maintenance_db),
    _: MaintenanceUser = Depends(require_maintenance_admin),
):
    result = await db.execute(select(MaintenanceUser).where(MaintenanceUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise not_found("Maintenance user")

    user.status = MaintenanceUserStatus(body.status)
    await db.commit()
    await db.refresh(user)
    return MaintenanceUserOut.from_orm_model(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_maintenance_db),
    current_user: MaintenanceUser = Depends(require_maintenance_admin),
):
    if user_id == current_user.id:
        from app.core.exceptions import bad_request
        raise bad_request("Cannot delete your own account.")

    result = await db.execute(select(MaintenanceUser).where(MaintenanceUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise not_found("Maintenance user")

    await db.delete(user)
    await db.commit()
