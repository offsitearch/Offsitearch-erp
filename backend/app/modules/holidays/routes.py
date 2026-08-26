"""Holiday calendar management routes.

Endpoints: /holidays — CRUD for company holidays. Admin roles only.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.holidays.models import Holiday
from app.modules.identity.schemas import MessageResponse
from app.modules.holidays import service as holiday_service
from app.modules.holidays.schemas import HolidayCreate, HolidayOut, HolidayUpdate
from app.modules.audit.service import log_audit
from app.utils.shared import get_or_404

router = APIRouter(prefix="/holidays", tags=["holidays"])


@router.get("", response_model=list[HolidayOut])
async def list_holidays(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    year: int | None = Query(default=None, ge=2000, le=2100),
) -> list[Holiday]:
    return await holiday_service.list_holidays(db, year)


@router.post("", response_model=HolidayOut, status_code=status.HTTP_201_CREATED)
async def create_holiday(
    payload: HolidayCreate,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Holiday:
    holiday = await holiday_service.create_holiday(db, payload)
    await log_audit(
        db,
        current_user,
        "create",
        "holiday",
        entity_id=str(holiday.id),
        details={"name": holiday.name, "date": holiday.date.isoformat()},
    )
    await db.commit()
    return holiday


@router.patch("/{holiday_id}", response_model=HolidayOut)
async def update_holiday(
    holiday_id: int,
    payload: HolidayUpdate,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Holiday:
    holiday = await get_or_404(db, Holiday, holiday_id)
    holiday = await holiday_service.update_holiday(db, holiday, payload)
    await log_audit(db, current_user, "update", "holiday", entity_id=str(holiday.id))
    await db.commit()
    return holiday


@router.delete("/{holiday_id}", response_model=MessageResponse)
async def delete_holiday(
    holiday_id: int,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    holiday = await get_or_404(db, Holiday, holiday_id)
    await log_audit(db, current_user, "delete", "holiday", entity_id=str(holiday.id))
    await holiday_service.delete_holiday(db, holiday)
    return MessageResponse(message="Holiday deleted")
