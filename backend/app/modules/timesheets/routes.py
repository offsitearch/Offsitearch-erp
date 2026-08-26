"""Timesheet routes.

Endpoints: /timesheets — daily entry logging (today only, rejected days
reopen), week/day submit for review, lead+ approval per day or in bulk,
admin listing, PDF receipt per sheet and month XLSX/PDF exports.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_min_level
from app.core.schemas import PaginatedResponse
from app.db.session import get_db
from app.models import User
from app.modules.audit.service import log_audit
from app.modules.timesheets import service as timesheet_service
from app.modules.timesheets.models import Timesheet
from app.modules.timesheets.schemas import (
    RejectRequest,
    TimesheetDetail,
    TimesheetRow,
)
from app.modules.timesheets.schemas import TimesheetWeekSave
from app.utils.errors import TimesheetError
from app.utils.shared import domain_error, has_min_level

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


def _today() -> date:
    from app.utils.shared import now_local

    return now_local().date()


async def _authorise_view(db: AsyncSession, timesheet_id: int, user: User) -> None:
    """Owner or L3+ may view a sheet; others get the standard 404."""
    sheet = await db.get(Timesheet, timesheet_id)
    if sheet is None or (sheet.user_id != user.id and not has_min_level(user, "L3")):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timesheet not found")


@router.get("/week", response_model=TimesheetDetail)
async def my_week(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    date: date | None = Query(default=None),
) -> dict:
    """The caller's timesheet for the week containing ``date`` (defaults to today).

    Missing weeks are created on demand as drafts.
    """
    try:
        return await timesheet_service.get_week_detail(db, current_user.id, date or _today())
    except TimesheetError as exc:
        raise domain_error(exc) from exc


@router.put("/week", response_model=TimesheetDetail)
async def save_week(
    payload: TimesheetWeekSave,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        detail = await timesheet_service.save_week(db, current_user.id, payload)
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "timesheet", entity_id=str(detail["id"]))
    await db.commit()
    return detail


@router.get("/mine", response_model=PaginatedResponse[TimesheetRow])
async def mine(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await timesheet_service.list_mine(db, current_user.id, page, page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/pending", response_model=PaginatedResponse[TimesheetRow])
async def pending(
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    """Submitted sheets awaiting review — strictly junior owners only
    (L0 sees all)."""
    items, total = await timesheet_service.pending_queue(db, current_user, page, page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("", response_model=PaginatedResponse[TimesheetRow])
async def admin_list(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    from_week: date | None = None,
    to_week: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = await timesheet_service.admin_list(
        db, page, page_size, user_id, status_filter, from_week, to_week
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/export/month")
async def export_month(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    month: int = Query(default_factory=lambda: _today().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: _today().year, ge=2000, le=2100),
    format: str = Query(default="xlsx", pattern="^(xlsx|pdf)$"),
    user_id: int | None = None,
) -> Response:
    """Month export of timesheet entries (own data; other users need L2+)."""
    if user_id is not None and user_id != current_user.id and not has_min_level(current_user, "L2"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only L2+ can export other employees' timesheets",
        )
    try:
        if format == "pdf":
            content = await timesheet_service.build_month_pdf(db, year, month, user_id)
            filename = f"timesheets-{year}-{month:02d}.pdf"
        else:
            content = await timesheet_service.build_month_xlsx(db, year, month, user_id)
            filename = f"timesheets-{year}-{month:02d}.xlsx"
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    media = (
        "application/pdf"
        if format == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    await log_audit(
        db,
        current_user,
        "export",
        "timesheet",
        entity_id=f"{year}-{month:02d}",
        details={"format": format, "user_id": user_id},
    )
    await db.commit()
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{timesheet_id}/pdf")
async def timesheet_pdf(
    timesheet_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Download the week sheet as a PDF receipt (owner or lead+)."""
    await _authorise_view(db, timesheet_id, current_user)
    try:
        content, filename = await timesheet_service.build_pdf(db, timesheet_id)
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{timesheet_id}", response_model=TimesheetDetail)
async def get_timesheet(
    timesheet_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _authorise_view(db, timesheet_id, current_user)
    try:
        return await timesheet_service.get_detail(db, timesheet_id)
    except TimesheetError as exc:
        raise domain_error(exc) from exc


@router.post("/{timesheet_id}/submit", response_model=TimesheetDetail)
async def submit(
    timesheet_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        detail = await timesheet_service.submit_timesheet(db, current_user.id, timesheet_id)
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "submit", "timesheet", entity_id=str(timesheet_id))
    await db.commit()
    return detail


@router.post("/{timesheet_id}/approve", response_model=TimesheetDetail)
async def approve(
    timesheet_id: int,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        detail = await timesheet_service.approve_timesheet(db, current_user, timesheet_id)
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "approve", "timesheet", entity_id=str(timesheet_id))
    await db.commit()
    return detail


@router.post("/{timesheet_id}/reject", response_model=TimesheetDetail)
async def reject(
    timesheet_id: int,
    payload: RejectRequest,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        detail = await timesheet_service.reject_timesheet(
            db, current_user, timesheet_id, payload.reason
        )
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "reject", "timesheet", entity_id=str(timesheet_id))
    await db.commit()
    return detail


@router.post("/{timesheet_id}/days/{day}/submit", response_model=TimesheetDetail)
async def submit_day(
    timesheet_id: int,
    day: date,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Owner submits a single day of their own week."""
    try:
        detail = await timesheet_service.submit_day(db, current_user.id, timesheet_id, day)
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    await log_audit(
        db,
        current_user,
        "submit_day",
        "timesheet",
        entity_id=str(timesheet_id),
        details={"day": day.isoformat()},
    )
    await db.commit()
    return detail


@router.post("/{timesheet_id}/days/{day}/approve", response_model=TimesheetDetail)
async def approve_day(
    timesheet_id: int,
    day: date,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        detail = await timesheet_service.approve_day(db, current_user, timesheet_id, day)
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    await log_audit(
        db,
        current_user,
        "approve_day",
        "timesheet",
        entity_id=str(timesheet_id),
        details={"day": day.isoformat()},
    )
    await db.commit()
    return detail


@router.post("/{timesheet_id}/days/{day}/reject", response_model=TimesheetDetail)
async def reject_day(
    timesheet_id: int,
    day: date,
    payload: RejectRequest,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        detail = await timesheet_service.reject_day(
            db, current_user, timesheet_id, day, payload.reason
        )
    except TimesheetError as exc:
        raise domain_error(exc) from exc
    await log_audit(
        db,
        current_user,
        "reject_day",
        "timesheet",
        entity_id=str(timesheet_id),
        details={"day": day.isoformat(), "reason": payload.reason},
    )
    await db.commit()
    return detail
