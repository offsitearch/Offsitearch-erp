import os
import shutil
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/system", tags=["system"])

_is_prod = settings.environment.lower() == "production"


@router.get("/health")
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    await db.execute(text("SELECT 1"))

    result: dict = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not _is_prod:
        disk = shutil.disk_usage("/")
        result.update(
            {
                "app": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": round((disk.used / disk.total) * 100, 1),
                },
                "pid": os.getpid(),
            }
        )

    return result


@router.get("/ready")
async def ready(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    await db.execute(text("SELECT 1"))
    return {"status": "ready"}
