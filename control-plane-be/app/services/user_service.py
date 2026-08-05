"""User service — CRUD, status management, settings."""
from app.core.exceptions import conflict, forbidden, not_found, unprocessable
from app.core.security import hash_password
from app.core.utils import ev
from app.prisma_client import db
from app.utils.audit import write_audit
from app.websocket.manager import ws_manager

VALID_ROLES = {"process_manager", "line_manager"}
VALID_STATUSES = {"active", "inactive"}


def _not_deleted() -> dict:
    return {"deletedAt": None}


async def list_users(role: str | None, status: str | None, page: int, limit: int) -> dict:
    where: dict = {**_not_deleted()}
    if role:
        where["role"] = role
    if status:
        where["status"] = status

    total = await db.user.count(where=where)
    users = await db.user.find_many(
        where=where, skip=(page - 1) * limit, take=limit, order={"createdAt": "desc"}
    )
    return {"users": users, "total": total}


async def create_user(name: str, email: str, role: str, password: str, actor_id: str):
    if role not in VALID_ROLES:
        raise unprocessable(f"role must be one of {sorted(VALID_ROLES)}")

    import datetime as _dt

    # find_unique works — email is still @unique, one row per email always exists
    existing = await db.user.find_unique(where={"email": email})

    if existing and existing.deletedAt is None:
        raise conflict("A user with this email already exists.")

    # Soft-deleted user with same email → restore instead of creating new
    deleted = existing if (existing and existing.deletedAt is not None) else None
    if deleted:
        user = await db.user.update(
            where={"id": deleted.id},
            data={
                "name": name,
                "role": role,
                "hashedPassword": hash_password(password),
                "status": "active",
                "deletedAt": None,
            },
        )
        # Ensure settings row exists
        if not await db.usersettings.find_unique(where={"userId": user.id}):
            await db.usersettings.create(data={"user": {"connect": {"id": user.id}}})
        # Revoke any old refresh tokens
        await db.refreshtoken.delete_many(where={"userId": user.id})
        await write_audit("user", f"Restored user: {user.email}", user.email, actor_id)
        return user

    user = await db.user.create(
        data={
            "name": name,
            "email": email,
            "role": role,
            "hashedPassword": hash_password(password),
        }
    )
    await db.usersettings.create(data={"user": {"connect": {"id": user.id}}})
    await write_audit("user", f"Created user: {user.email}", user.email, actor_id)
    return user


async def get_user(user_id: str):
    user = await db.user.find_unique(where={"id": user_id})
    if not user or user.deletedAt is not None:
        raise not_found("User")
    return user


async def update_user(user_id: str, name: str | None, email: str | None, actor_id: str):
    user = await db.user.find_unique(where={"id": user_id})
    if not user or user.deletedAt is not None:
        raise not_found("User")

    data: dict = {}
    if name is not None:
        data["name"] = name
    if email is not None:
        conflict_user = await db.user.find_first(
            where={"email": email, "id": {"not": user_id}, "deletedAt": None}
        )
        if conflict_user:
            raise conflict("Email already in use by another user.")
        data["email"] = email

    updated = await db.user.update(where={"id": user_id}, data=data)
    await write_audit("user", f"Updated user: {updated.email}", updated.email, actor_id)
    return updated


async def update_user_status(user_id: str, status: str, actor_id: str):
    if status not in VALID_STATUSES:
        raise unprocessable(f"status must be one of {sorted(VALID_STATUSES)}")

    user = await db.user.find_unique(where={"id": user_id})
    if not user or user.deletedAt is not None:
        raise not_found("User")

    updated = await db.user.update(where={"id": user_id}, data={"status": status})
    await write_audit(
        "user",
        f"User status changed to {status}: {updated.email}",
        updated.email,
        actor_id,
    )

    from app.schemas.user import UserOut
    user_payload = UserOut(
        id=updated.id, name=updated.name, email=updated.email,
        role=ev(updated.role), status=ev(updated.status),
        avatar=updated.avatar, createdAt=updated.createdAt, updatedAt=updated.updatedAt,
    )
    await ws_manager.broadcast("user.status.changed", user_payload.model_dump())
    return updated


async def delete_user(user_id: str, actor_id: str) -> None:
    import datetime as _dt

    if user_id == actor_id:
        raise conflict("Cannot delete your own account.")

    user = await db.user.find_unique(where={"id": user_id})
    if not user or user.deletedAt is not None:
        raise not_found("User")

    if user.email == "admin@haval.com":
        raise conflict("Cannot delete the system admin account.")

    if await db.assemblyline.find_first(where={"managerId": user_id}):
        raise conflict("Cannot delete user: they are assigned as a line manager.")

    # Soft-delete: mark deleted, revoke all sessions, deactivate
    await db.user.update(
        where={"id": user_id},
        data={"deletedAt": _dt.datetime.now(_dt.UTC), "status": "inactive"},
    )
    await db.refreshtoken.delete_many(where={"userId": user_id})
    await write_audit("user", f"Deleted user: {user.email}", user.email, actor_id)


async def get_settings(user_id: str):
    row = await db.usersettings.find_unique(where={"userId": user_id})
    if not row:
        raise not_found("Settings")
    return row


async def update_settings(
    user_id: str,
    notif_new_uploads: bool | None,
    notif_migrations: bool | None,
    notif_user_changes: bool | None,
    notif_system_alerts: bool | None,
    data_retention_days: int | None,
):
    if not await db.usersettings.find_unique(where={"userId": user_id}):
        raise not_found("Settings")

    data: dict = {}
    if notif_new_uploads is not None:
        data["notifNewUploads"] = notif_new_uploads
    if notif_migrations is not None:
        data["notifMigrations"] = notif_migrations
    if notif_user_changes is not None:
        data["notifUserChanges"] = notif_user_changes
    if notif_system_alerts is not None:
        data["notifSystemAlerts"] = notif_system_alerts
    if data_retention_days is not None:
        data["dataRetentionDays"] = data_retention_days

    return await db.usersettings.update(where={"userId": user_id}, data=data)
