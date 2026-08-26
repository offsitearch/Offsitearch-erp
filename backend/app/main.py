import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import api_router
from app.core.config import settings
from app.core.request_context import (
    FORWARDED_FOR_HEADER,
    USER_AGENT_HEADER,
    capture_request_context,
)
from app.db.init_db import init_db
from app.db.session import engine
from app.middleware.cors_safety import CORSSafetyMiddleware
from app.middleware.rate_limit_tracker import RateLimitTrackerMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware


# ── Structured JSON logging ──────────────────────────────────────────────
class JsonRequestFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_entry["method"] = record.method
        if hasattr(record, "path"):
            log_entry["path"] = record.path
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonRequestFormatter())
    logger.handlers = [handler]
    logger.propagate = False
    return logger


logger = setup_logging()


# ── Rate limiter ─────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
slowapi_state = {"limiter": limiter}


# ── Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    # Deferred import: modules must never depend on app.main, and the
    # schedulers only need to exist while the app is running.
    from app.modules.backup.scheduler import start_backup_scheduler, stop_backup_scheduler
    from app.modules.timesheets.scheduler import (
        start_timesheet_scheduler,
        stop_timesheet_scheduler,
    )

    start_backup_scheduler()
    start_timesheet_scheduler()
    yield
    stop_backup_scheduler()
    stop_timesheet_scheduler()
    await engine.dispose()


# ── App ──────────────────────────────────────────────────────────────────
is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None,
    openapi_url=None if is_production else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Global error boundary ────────────────────────────────────────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
        },
        exc_info=exc,
    )
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )
    response.headers["X-Request-ID"] = request_id
    return response


# ── CORS — handled by CORSSafetyMiddleware at the outermost layer ────────
# CORSMiddleware removed: it produced duplicate Access-Control-Allow-Origin
# headers that the browser rejected. CORSSafetyMiddleware (added below after
# all BaseHTTPMiddleware layers) handles preflight + response headers
# uniformly, including error responses.

app.add_middleware(
    GZipMiddleware,
    minimum_size=settings.gzip_min_size,
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(RateLimitTrackerMiddleware)


# ── Request logging & request_id middleware ──────────────────────────────
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    forwarded_for = request.headers.get(FORWARDED_FOR_HEADER)
    client_ip = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else None)
    )
    capture_request_context(request_id, client_ip, request.headers.get(USER_AGENT_HEADER))

    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    response.headers["X-Request-ID"] = request_id

    extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }
    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra=extra,
    )
    return response


# ── CORS safety-net (OUTERMOST middleware) ────────────────────────────────
# Guarantees CORS headers on EVERY response, including 500s that might
# bypass the inner CORSMiddleware when BaseHTTPMiddleware re-raises.
app.add_middleware(
    CORSSafetyMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["authorization", "content-type", "x-request-id"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", include_in_schema=False)
async def root() -> Response:
    if is_production:
        return {"status": "ok", "docs": "/api/v1/system/health"}
    return RedirectResponse(url="/docs")
