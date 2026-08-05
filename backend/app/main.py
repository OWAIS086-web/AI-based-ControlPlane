import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.core.metrics import user_requests_total
from app.prisma_client import db
from app.services.metrics_report_service import send_eod_report
from app.maintenance.database import init_db as maintenance_init_db
from app.maintenance.seed import seed_maintenance_admin
from app.maintenance.routers import auth as maintenance_auth
from app.maintenance.routers import users as maintenance_users
from app.maintenance.routers import faults as maintenance_faults
from app.maintenance.routers import comments as maintenance_comments
from app.paint_inspection.router import router as paint_inspection_router
from app.routers import (
    audit,
    auth,
    car_models,
    config,
    dashboard,
    line_types,
    lines,
    migrations,
    processes,
    stations,
    tool_requests,
    tools,
    users,
    versions,
    workers,
    ws,
    support,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()

    # GIN index for full-text search on process document content.
    # CREATE INDEX IF NOT EXISTS is a no-op on subsequent startups.
    await db.execute_raw(
        """
        CREATE INDEX IF NOT EXISTS processes_search_text_fts_idx
        ON processes
        USING GIN (to_tsvector('simple', coalesce(search_text, '')))
        """
    )

    # Maintenance module — create DB + tables + seed admin on first boot
    await maintenance_init_db()
    await seed_maintenance_admin()

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(send_eod_report, "cron", hour=settings.METRICS_REPORT_HOUR, minute=0)
    scheduler.add_job(send_eod_report, "date")  # fire once on startup
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await db.disconnect()


app = FastAPI(
    title="ControlPlane API",
    description="Manufacturing assembly line management system.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Metrics ───────────────────────────────────────────────────────────────────
# Patch: older prometheus_fastapi_instrumentator (<7) crashes on _IncludedRouter
# objects (FastAPI internal routing type) that lack a .path attribute.
try:
    import prometheus_fastapi_instrumentator.routing as _pfi_routing
    _orig_get_route_name = _pfi_routing._get_route_name

    def _patched_get_route_name(scope, routes):
        try:
            return _orig_get_route_name(scope, routes)
        except AttributeError:
            return scope.get("path", "")

    _pfi_routing._get_route_name = _patched_get_route_name
except Exception:
    pass

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# ── User-level metrics middleware ─────────────────────────────────────────────
@app.middleware("http")
async def track_user_metrics(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/metrics":
        return response
    user_id = "anonymous"
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = jwt.get_unverified_claims(auth[7:])
            user_id = payload.get("sub", "anonymous")
        except Exception:
            pass
    route = request.scope.get("route")
    handler = route.path if route else request.url.path
    user_requests_total.labels(
        user_id=user_id,
        method=request.method,
        handler=handler,
        status_code=str(response.status_code),
    ).inc()
    return response


# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": str(exc),
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"

app.include_router(auth.router, prefix=PREFIX)
app.include_router(config.router, prefix=PREFIX)
app.include_router(users.router, prefix=PREFIX)
app.include_router(line_types.router, prefix=PREFIX)
app.include_router(lines.router, prefix=PREFIX)
app.include_router(stations.router, prefix=PREFIX)
app.include_router(processes.router, prefix=PREFIX)
app.include_router(versions.router, prefix=PREFIX)
app.include_router(car_models.router, prefix=PREFIX)
app.include_router(migrations.router, prefix=PREFIX)
app.include_router(audit.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)
app.include_router(workers.router, prefix=PREFIX)
app.include_router(tools.router, prefix=PREFIX)
app.include_router(tool_requests.router, prefix=PREFIX)
app.include_router(ws.router, prefix=PREFIX)
app.include_router(support.router, prefix=PREFIX)

# ── Maintenance module ────────────────────────────────────────────────────────
app.include_router(maintenance_auth.router, prefix=PREFIX)
app.include_router(maintenance_users.router, prefix=PREFIX)
app.include_router(maintenance_faults.router, prefix=PREFIX)
app.include_router(maintenance_comments.router, prefix=PREFIX)

# ── Paint Inspection module ──────────────────────────────────────────────────
app.include_router(paint_inspection_router, prefix=PREFIX)


@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": os.getenv("APP_VERSION", "dev")}
