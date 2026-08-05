"""
Seed script — idempotent.
Creates the default Assembly line type, the 5 fixed assembly lines, and the
default admin user if they don't already exist.

Also links any existing lines that have no lineTypeId to the Assembly type.

Run via: python prisma/seed.py
Also called automatically from entrypoint.sh after prisma db push.

Default admin credentials (override via env vars):
  ADMIN_EMAIL    default: admin@haval.com
  ADMIN_PASSWORD default: changeme
"""
import asyncio
import os

from prisma import Prisma

# ── Default line type ──────────────────────────────────────────────────────────
ASSEMBLY_TYPE = {
    "id": "assembly",
    "name": "Assembly",
    "icon": "factory",
    "color": "#6366F1",
    "order": 0,
}

LINES = [
    {"id": "trim",    "name": "Trim Line",    "icon": "scissors", "color": "#6366F1", "order": 0},
    {"id": "chassis", "name": "Chassis Line", "icon": "car",      "color": "#F59E0B", "order": 1},
    {"id": "engine",  "name": "Engine Line",  "icon": "zap",      "color": "#EF4444", "order": 2},
    {"id": "frame",   "name": "Frame Line",   "icon": "box",      "color": "#10B981", "order": 3},
    {"id": "final",   "name": "Final Line",   "icon": "flag",     "color": "#3B82F6", "order": 4},
]

ADMIN = {
    "name": "haval_admin",
    "email": os.getenv("ADMIN_EMAIL", "admin@haval.com"),
    "password": os.getenv("ADMIN_PASSWORD", "changeme"),
    "role": "process_manager",
}


async def seed() -> None:
    # Import here to avoid loading app config before Prisma is ready
    import bcrypt

    db = Prisma()
    await db.connect()

    # ── Admin user ────────────────────────────────────────────────────────────
    existing_admin = await db.user.find_unique(where={"email": ADMIN["email"]})
    if not existing_admin:
        hashed_pw = bcrypt.hashpw(ADMIN["password"].encode(), bcrypt.gensalt()).decode()
        await db.user.create(
            data={
                "name": ADMIN["name"],
                "email": ADMIN["email"],
                "hashedPassword": hashed_pw,
                "role": ADMIN["role"],
            }
        )
        # Create default settings for the admin
        admin = await db.user.find_unique(where={"email": ADMIN["email"]})
        await db.usersettings.create(data={"userId": admin.id})
        print(f"  ✓ Created admin: {ADMIN['name']} ({ADMIN['email']})")
        print(f"    ⚠  Default password is '{ADMIN['password']}' — change it immediately.")
    else:
        print(f"  – Skipped (exists): admin {ADMIN['name']}")

    # ── Assembly line type ────────────────────────────────────────────────────
    existing_type = await db.linetype.find_unique(where={"id": ASSEMBLY_TYPE["id"]})
    if not existing_type:
        await db.linetype.create(data=ASSEMBLY_TYPE)
        print(f"  ✓ Created line type: {ASSEMBLY_TYPE['name']}")
    else:
        print(f"  – Skipped (exists): line type {ASSEMBLY_TYPE['name']}")

    # ── Assembly lines ────────────────────────────────────────────────────────
    for line in LINES:
        existing = await db.assemblyline.find_unique(where={"id": line["id"]})
        if not existing:
            await db.assemblyline.create(
                data={**line, "lineTypeId": ASSEMBLY_TYPE["id"]}
            )
            print(f"  ✓ Created line: {line['name']}")
        else:
            # If an existing line has no lineTypeId, assign it to Assembly type
            if not existing.lineTypeId:
                await db.assemblyline.update(
                    where={"id": line["id"]},
                    data={"lineTypeId": ASSEMBLY_TYPE["id"]},
                )
                print(f"  ✓ Linked existing line to Assembly type: {existing.name}")
            else:
                print(f"  – Skipped (exists): {existing.name}")

    await db.disconnect()
    print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
