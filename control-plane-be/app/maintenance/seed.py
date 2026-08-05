"""Seed the maintenance DB with an initial admin user on first startup."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.core.security import hash_password
from app.maintenance.database import AsyncSessionLocal
from app.maintenance.models import MaintenanceUser, MaintenanceUserRole, MaintenanceUserStatus


async def seed_maintenance_admin() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MaintenanceUser).where(
                MaintenanceUser.email == settings.MAINTENANCE_ADMIN_EMAIL
            )
        )
        if result.scalar_one_or_none():
            return

        admin = MaintenanceUser(
            name=settings.MAINTENANCE_ADMIN_NAME,
            email=settings.MAINTENANCE_ADMIN_EMAIL,
            hashed_password=hash_password(settings.MAINTENANCE_ADMIN_PASSWORD),
            role=MaintenanceUserRole.admin,
            status=MaintenanceUserStatus.active,
        )
        db.add(admin)
        await db.commit()
        print(f"[maintenance] Admin seeded: {settings.MAINTENANCE_ADMIN_EMAIL}")
