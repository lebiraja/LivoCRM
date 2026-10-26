"""LivoCRM — FastAPI entry point."""

from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, IntegrityError

from app.config import settings
from app.logging_config import configure_logging
from app.routers import (
    auth_router,
    contacts_router,
    deals_router,
    activities_router,
    analytics_router,
    ai_router,
    chat_router,
    pipeline_stages_router,
    ws_router,
    ws_ticket_router,
    appointments_router,
    follow_ups_router,
    recovery_router,
    demo_router,
)
from app.services.recovery import run_scheduler

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: import models so Alembic sees them
    import app.models  # noqa: F401
    scheduler = asyncio.create_task(run_scheduler()) if settings.ENABLE_SCHEDULER else None
    yield
    # shutdown
    if scheduler is not None:
        scheduler.cancel()


app = FastAPI(
    title="LivoCRM API",
    version="1.0.0",
    lifespan=lifespan,
    # Interactive docs only on request (ENABLE_DOCS), under /api so nginx routes them
    docs_url="/api/docs" if settings.ENABLE_DOCS else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.ENABLE_DOCS else None,
)

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Database error mapping (no SQL or values in responses) ──────────────────
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Unique/foreign-key/check violations that validation could not catch up front."""
    logger.info("Integrity error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=409, content={"detail": "Conflicts with existing data"})


@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError) -> JSONResponse:
    """Values the database rejects (out of range, too long, malformed)."""
    logger.info("Data error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=422, content={"detail": "Invalid data"})


# ── Global Exception Handler ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return generic error response."""
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ── Routers ─────────────────────────────────────────────────────────────────
API = "/api"
app.include_router(auth_router, prefix=API)
app.include_router(contacts_router, prefix=API)
app.include_router(deals_router, prefix=API)
app.include_router(activities_router, prefix=API)
app.include_router(analytics_router, prefix=API)
app.include_router(ai_router, prefix=API)
app.include_router(chat_router, prefix=API)
app.include_router(pipeline_stages_router, prefix=API)
app.include_router(appointments_router, prefix=API)
app.include_router(follow_ups_router, prefix=API)
app.include_router(recovery_router, prefix=API)
app.include_router(demo_router, prefix=API)
app.include_router(ws_ticket_router, prefix=API)  # POST /api/ws/ticket
app.include_router(ws_router)  # WebSocket — no /api prefix (served at /ws/...)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
