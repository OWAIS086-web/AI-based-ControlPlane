"""Maintenance module — SQLAlchemy async engine and session factory.

Connects to a separate maintenance_db PostgreSQL database.
Uses create_all() on startup — no Alembic/Prisma needed while the module is embedded.
"""
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.MAINTENANCE_DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def _ensure_db_exists() -> None:
    """Create maintenance_db if it doesn't exist yet."""
    # Connect to the default 'postgres' DB to run CREATE DATABASE
    raw_url = settings.MAINTENANCE_DATABASE_URL.replace("postgresql+asyncpg://", "")
    # raw_url = "user:pass@host:port/dbname"
    creds, rest = raw_url.rsplit("@", 1)
    host_port, _ = rest.split("/", 1)
    user, password = creds.split(":", 1)
    host, port = (host_port.split(":", 1) if ":" in host_port else (host_port, "5432"))

    conn = await asyncpg.connect(
        host=host, port=int(port), user=user, password=password, database="postgres"
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'maintenance_db'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE maintenance_db")
    finally:
        await conn.close()


async def init_db() -> None:
    """Create the maintenance_db database and all tables."""
    await _ensure_db_exists()
    # Import models so Base.metadata is populated
    from app.maintenance import models  # noqa: F401
    from app.paint_inspection import models as paint_models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
