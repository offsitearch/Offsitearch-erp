"""Timesheet business logic: daily entry logging, per-day approval flow.

Logging rules:
- Employees log entries for TODAY only while the day is a draft.
- Each day carries its own approval state (:class:`TimesheetDay`), so a
  lead can review single days; week-level submit/approve/reject are bulk
  operations over days. Rejected days reopen that date for editing (the
  fix window) until resubmitted; past draft days stay locked but remain
  submittable. Approved days are terminal and feed
  ``projects.hours_logged`` exactly once.
- The weekly sheet's ``status`` column is an aggregate kept in sync with
  its day rows: any submitted → submitted, else any rejected → rejected,
  else all approved → approved, else draft.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Department, Notification, OrgLevel, Project, Task, User
from app.modules.notifications.service import notify
from app.modules.timesheets.models import Timesheet, TimesheetDay, TimesheetEntry
from app.modules.timesheets.schemas import TimesheetWeekSave
from app.utils.enums import TimesheetStatus
from app.utils.errors import TimesheetError
from app.utils.shared import (
    LEVEL_RANK,
    UNKNOWN_LEVEL_RANK,
    level_rank,
    now_local,
    to_local,
    user_level_rank,
    utc_now,
)

MAX_HOURS_PER_DAY = Decimal("24")


def monday_of(day: date) -> date:
    """Normalise any date to the Monday starting its week."""
    return day - timedelta(days=day.weekday())


def week_end_of(week_start: date) -> date:
    return week_start + timedelta(days=6)


# ── Day-state helpers ───────────────────────────────────────────────


async def _day_rows(db: AsyncSession, sheet_id: int) -> dict[date, TimesheetDay]:
    rows = (
        (await db.execute(select(TimesheetDay).where(TimesheetDay.timesheet_id == sheet_id)))
        .scalars()
        .all()
    )
    return {row.date: row for row in rows}


async def _ensure_day_rows(
    db: AsyncSession, sheet_id: int, dates: list[date]
) -> dict[date, TimesheetDay]:
    """Create missing draft day rows; returns the full map afterwards."""
    mapping = await _day_rows(db, sheet_id)
    for day in dates:
        if day not in mapping:
            row = TimesheetDay(timesheet_id=sheet_id, date=day)
            db.add(row)
            try:
                await db.flush()
            except IntegrityError:
                await db.rollback()
                mapping = await _day_rows(db, sheet_id)
                continue
            mapping[day] = row
    return mapping


def _aggregate_status(days: dict[date, TimesheetDay]) -> TimesheetStatus:
    statuses = [row.status for row in days.values()]
    if not statuses:
        return TimesheetStatus.DRAFT
    if any(s == TimesheetStatus.SUBMITTED for s in statuses):
        return TimesheetStatus.SUBMITTED
    if any(s == TimesheetStatus.REJECTED for s in statuses):
        return TimesheetStatus.REJECTED
    if all(s == TimesheetStatus.APPROVED for s in statuses):
        return TimesheetStatus.APPROVED
    return TimesheetStatus.DRAFT


def _sync_sheet_status(sheet: Timesheet, days: dict[date, TimesheetDay]) -> None:
    sheet.status = _aggregate_status(days)


def _is_editable_day(day_row: TimesheetDay | None) -> bool:
    """Today's draft or a rejected day can still receive entries."""
    return day_row is None or day_row.status in (
        TimesheetStatus.DRAFT,
        TimesheetStatus.REJECTED,
    )


def _is_loggable_date(day_row: TimesheetDay | None, entry_date: date, today: date) -> bool:
    """Strict logging window: today while editable, or any rejected day."""
    if not _is_editable_day(day_row):
        return False
    return entry_date == today or (
        day_row is not None and day_row.status == TimesheetStatus.REJECTED
    )


# ── Serialization ───────────────────────────────────────────────────


async def _detail_dict(db: AsyncSession, sheet: Timesheet) -> dict:
    owner = await db.get(User, sheet.user_id)
    approver = await db.get(User, sheet.approved_by) if sheet.approved_by else None
    entries = (
        await db.execute(
            select(TimesheetEntry, Project.name, Task.title)
            .outerjoin(Project, Project.id == TimesheetEntry.project_id)
            .outerjoin(Task, Task.id == TimesheetEntry.task_id)
            .where(TimesheetEntry.timesheet_id == sheet.id)
            .order_by(TimesheetEntry.date, TimesheetEntry.id)
        )
    ).all()
    total = sum((entry.hours for entry, _, _ in entries), Decimal("0"))

    day_rows = list((await _day_rows(db, sheet.id)).values())
    approver_ids = {row.approved_by for row in day_rows if row.approved_by}
    day_approvers: dict[int, str] = {}
    if approver_ids:
        users = (
            await db.execute(select(User.id, User.name).where(User.id.in_(approver_ids)))
        ).all()
        day_approvers = {uid: name for uid, name in users}

    submitted_at = min((r.submitted_at for r in day_rows if r.submitted_at), default=None)
    rejection_reason = next((r.rejection_reason for r in day_rows if r.rejection_reason), None)

    return {
        "id": sheet.id,
        "user_id": sheet.user_id,
        "user_name": owner.name if owner else None,
        "employee_id": owner.employee_id if owner else None,
        "week_start": sheet.week_start,
        "week_end": week_end_of(sheet.week_start),
        "status": sheet.status.value,
        "total_hours": total,
        "submitted_at": submitted_at,
        "approved_by": sheet.approved_by,
        "approved_by_name": approver.name if approver else None,
        "approved_at": sheet.approved_at,
        "rejection_reason": rejection_reason,
        "entries": [
            {
                "id": entry.id,
                "project_id": entry.project_id,
                "task_id": entry.task_id,
                "date": entry.date,
                "hours": entry.hours,
                "description": entry.description,
                "project_name": project_name,
                "task_title": task_title,
            }
            for entry, project_name, task_title in entries
        ],
        "days": [
            {
                "date": row.date,
                "status": row.status.value,
                "submitted_at": row.submitted_at,
                "approved_by_name": day_approvers.get(row.approved_by) if row.approved_by else None,
                "approved_at": row.approved_at,
                "rejection_reason": row.rejection_reason,
            }
            for row in sorted(day_rows, key=lambda r: r.date)
        ],
    }


def _list_select():
    """Base select joining owner info, per-sheet hour aggregates and reviewer name."""
    totals = (
        select(
            TimesheetEntry.timesheet_id.label("timesheet_id"),
            func.coalesce(func.sum(TimesheetEntry.hours), 0).label("total_hours"),
            func.count(TimesheetEntry.id).label("entry_count"),
        )
        .group_by(TimesheetEntry.timesheet_id)
        .subquery()
    )
    approver = aliased(User)
    return (
        select(
            Timesheet,
            User.name,
            User.employee_id,
            Department.name,
            totals.c.total_hours,
            totals.c.entry_count,
            approver.name,
        )
        .join(User, User.id == Timesheet.user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .outerjoin(totals, totals.c.timesheet_id == Timesheet.id)
        .outerjoin(approver, approver.id == Timesheet.approved_by)
    )


def _row_dict(row) -> dict:
    (
        sheet,
        owner_name,
        employee_id,
        department,
        total_hours,
        entry_count,
        approver_name,
    ) = row
    return {
        "id": sheet.id,
        "user_id": sheet.user_id,
        "user_name": owner_name,
        "employee_id": employee_id,
        "department": department,
        "week_start": sheet.week_start,
        "week_end": week_end_of(sheet.week_start),
        "status": sheet.status.value,
        "total_hours": total_hours or Decimal("0"),
        "entry_count": entry_count or 0,
        "submitted_at": sheet.submitted_at,
        "approved_by_name": approver_name,
        "approved_at": sheet.approved_at,
        "rejection_reason": sheet.rejection_reason,
    }


# ── Reads ───────────────────────────────────────────────────────────


async def get_or_create_week_sheet(db: AsyncSession, user_id: int, week_start: date) -> Timesheet:
    stmt = select(Timesheet).where(Timesheet.user_id == user_id, Timesheet.week_start == week_start)
    sheet = (await db.execute(stmt)).scalar_one_or_none()
    if sheet is not None:
        return sheet
    sheet = Timesheet(user_id=user_id, week_start=week_start)
    db.add(sheet)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent first save for the same week — re-read the winner.
        await db.rollback()
        sheet = (await db.execute(stmt)).scalar_one_or_none()
        if sheet is None:
            raise TimesheetError("Could not create the weekly timesheet", 500)
        return sheet
    await db.refresh(sheet)
    return sheet


async def get_week_detail(db: AsyncSession, user_id: int, any_day: date) -> dict:
    sheet = await get_or_create_week_sheet(db, user_id, monday_of(any_day))
    return await _detail_dict(db, sheet)


async def get_detail(db: AsyncSession, timesheet_id: int) -> dict:
    sheet = await db.get(Timesheet, timesheet_id)
    if sheet is None:
        raise TimesheetError("Timesheet not found", 404)
    return await _detail_dict(db, sheet)


async def list_mine(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    base = _list_select().where(Timesheet.user_id == user_id)
    total = (
        await db.execute(
            select(func.count()).select_from(Timesheet).where(Timesheet.user_id == user_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Timesheet.week_start.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return [_row_dict(r) for r in rows], total


async def pending_queue(
    db: AsyncSession, reviewer: User, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    """Submitted sheets the reviewer may act on.

    Reviewers only see strictly junior owners (L3 sees L4–L6 and
    level-less users, never other L3s). The CEO (L0) sees everything.
    """
    base = _list_select().where(Timesheet.status == TimesheetStatus.SUBMITTED)
    count_stmt = (
        select(func.count())
        .select_from(Timesheet)
        .where(Timesheet.status == TimesheetStatus.SUBMITTED)
    )
    if user_level_rank(reviewer) != LEVEL_RANK["L0"]:
        allowed_codes = [
            code for code, rank in LEVEL_RANK.items() if rank > user_level_rank(reviewer)
        ]
        scope = OrgLevel.code.in_(allowed_codes) | User.org_level_id.is_(None)
        base = base.outerjoin(OrgLevel, OrgLevel.id == User.org_level_id).where(scope)
        count_stmt = (
            count_stmt.join(User, User.id == Timesheet.user_id)
            .outerjoin(OrgLevel, OrgLevel.id == User.org_level_id)
            .where(scope)
        )
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Timesheet.submitted_at.asc().nulls_last(), Timesheet.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return [_row_dict(r) for r in rows], total


async def admin_list(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    user_id: int | None = None,
    status_filter: str | None = None,
    from_week: date | None = None,
    to_week: date | None = None,
) -> tuple[list[dict], int]:
    stmt = _list_select()
    count_stmt = select(func.count()).select_from(Timesheet)
    if user_id is not None:
        stmt = stmt.where(Timesheet.user_id == user_id)
        count_stmt = count_stmt.where(Timesheet.user_id == user_id)
    if status_filter:
        try:
            status_enum = TimesheetStatus(status_filter)
        except ValueError as exc:
            raise TimesheetError(f"Unknown status '{status_filter}'", 400) from exc
        stmt = stmt.where(Timesheet.status == status_enum)
        count_stmt = count_stmt.where(Timesheet.status == status_enum)
    if from_week is not None:
        stmt = stmt.where(Timesheet.week_start >= monday_of(from_week))
        count_stmt = count_stmt.where(Timesheet.week_start >= monday_of(from_week))
    if to_week is not None:
        stmt = stmt.where(Timesheet.week_start <= monday_of(to_week))
        count_stmt = count_stmt.where(Timesheet.week_start <= monday_of(to_week))
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Timesheet.week_start.desc(), Timesheet.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return [_row_dict(r) for r in rows], total


# ── Logging (save) ──────────────────────────────────────────────────


async def _validate_refs(db: AsyncSession, project_id: int | None, task_id: int | None) -> None:
    if project_id is not None:
        project = await db.get(Project, project_id)
        if project is None or not project.is_active:
            raise TimesheetError("Project not found", 404)
    if task_id is not None:
        if project_id is None:
            raise TimesheetError("Task entries must also select a project", 400)
        task = await db.get(Task, task_id)
        if task is None or not getattr(task, "is_active", True):
            raise TimesheetError("Task not found", 404)
        if task.project_id != project_id:
            raise TimesheetError("The selected task does not belong to the selected project", 400)


async def save_week(db: AsyncSession, user_id: int, payload: TimesheetWeekSave) -> dict:
    week_start = monday_of(payload.week_start)
    sheet = await get_or_create_week_sheet(db, user_id, week_start)

    today = now_local().date()
    days = await _day_rows(db, sheet.id)

    per_day: dict[date, Decimal] = {}
    for entry in payload.entries:
        if entry.date < week_start or entry.date > week_end_of(week_start):
            raise TimesheetError(f"{entry.date.isoformat()} falls outside the selected week", 400)
        if entry.date > today:
            raise TimesheetError("Hours cannot be logged for future dates", 400)
        day_row = days.get(entry.date)
        if not _is_editable_day(day_row):
            raise TimesheetError(
                f"{entry.date.isoformat()} has already been submitted for review and is locked",
                409,
            )
        if not _is_loggable_date(day_row, entry.date, today):
            raise TimesheetError(
                f"Entries are limited to today ({today.isoformat()}) — "
                "past dates can only be corrected after they were rejected",
                400,
            )
        await _validate_refs(db, entry.project_id, entry.task_id)
        per_day[entry.date] = per_day.get(entry.date, Decimal("0")) + entry.hours
        if per_day[entry.date] > MAX_HOURS_PER_DAY:
            raise TimesheetError(
                f"Total hours for {entry.date.isoformat()} exceed {MAX_HOURS_PER_DAY} per day",
                400,
            )

    # Wholesale replacement of LOGGABLE days only — locked days keep their
    # entries untouched.
    loggable_dates = {
        d for d, row in days.items() if d == today or row.status == TimesheetStatus.REJECTED
    }
    target_dates = loggable_dates | {e.date for e in payload.entries}
    await db.execute(
        TimesheetEntry.__table__.delete().where(
            TimesheetEntry.timesheet_id == sheet.id,
            TimesheetEntry.date.in_(target_dates),
        )
    )
    for entry in payload.entries:
        db.add(
            TimesheetEntry(
                timesheet_id=sheet.id,
                project_id=entry.project_id,
                task_id=entry.task_id,
                date=entry.date,
                hours=entry.hours,
                description=entry.description,
            )
        )

    days = await _ensure_day_rows(db, sheet.id, [e.date for e in payload.entries])
    _sync_sheet_status(sheet, days)
    await db.commit()
    await db.refresh(sheet)
    return await _detail_dict(db, sheet)


# ── Submission & review ─────────────────────────────────────────────


def _hours_text(value) -> str:
    """Compact decimal text for exports (7.50 → '7.5', 8 → '8')."""
    normalised = Decimal(str(value)).normalize()
    if normalised == normalised.to_integral_value():
        return str(normalised.quantize(Decimal("1")))
    return format(normalised, "f")


async def build_pdf(db: AsyncSession, timesheet_id: int) -> tuple[bytes, str]:
    """Render a timesheet as a simple PDF receipt. Caller handles access control."""
    from app.utils.pdf import timesheet_pdf

    detail = await get_detail(db, timesheet_id)
    content = timesheet_pdf(
        employee_name=detail["user_name"] or f"User #{detail['user_id']}",
        employee_code=detail["employee_id"],
        week_label=(f"{detail['week_start'].isoformat()} — {detail['week_end'].isoformat()}"),
        status=str(detail["status"]),
        submitted_label=(
            to_local(detail["submitted_at"]).strftime("%d %b %Y")
            if detail["submitted_at"]
            else None
        ),
        reviewer_name=detail["approved_by_name"],
        rows=[
            {
                "date": entry["date"].isoformat(),
                "project": entry["project_name"] or "—",
                "description": entry["description"] or "",
                "hours": _hours_text(entry["hours"]),
            }
            for entry in detail["entries"]
        ],
        total_hours=_hours_text(detail["total_hours"]),
    )
    filename = (
        f"timesheet-{detail['employee_id'] or detail['user_id']}-"
        f"{detail['week_start'].isoformat()}.pdf"
    )
    return content, filename


async def _credit_project_hours(db: AsyncSession, project_id: int, hours: Decimal) -> None:
    if project_id is None:
        return
    project = await db.get(Project, project_id)
    if project is not None:
        project.hours_logged = (project.hours_logged or Decimal("0")) + hours


def _day_hours(entries: list[dict], day: date) -> Decimal:
    return sum((e["hours"] for e in entries if e["date"] == day), Decimal("0"))


async def _assert_can_review(db: AsyncSession, reviewer: User, owner_id: int) -> None:
    """Strict hierarchy for approvals/rejections.

    A reviewer may only act on sheets of strictly junior users — an L3
    cannot review another L3, an L2 not another L2, etc. The CEO (L0)
    is the sole exception: they may review anyone, including peers and
    their own sheet.
    """
    if user_level_rank(reviewer) == LEVEL_RANK["L0"]:
        return
    if owner_id == reviewer.id:
        raise TimesheetError("You cannot review your own timesheet", 403)
    owner = await db.get(User, owner_id)
    if owner is None:
        return
    owner_rank = UNKNOWN_LEVEL_RANK
    if owner.org_level_id is not None:
        level = await db.get(OrgLevel, owner.org_level_id)
        owner_rank = level_rank(level.code) if level else UNKNOWN_LEVEL_RANK
    if owner_rank <= user_level_rank(reviewer):
        raise TimesheetError("You can only review timesheets of lower levels", 403)


async def submit_timesheet(db: AsyncSession, user_id: int, timesheet_id: int) -> dict:
    """Owner submits every draft/rejected day of their own week."""
    detail = await get_detail(db, timesheet_id)
    if detail["user_id"] != user_id:
        raise TimesheetError("You can only submit your own timesheets", 403)
    if detail["total_hours"] <= 0:
        raise TimesheetError("Cannot submit an empty timesheet", 400)

    days = await _ensure_day_rows(db, timesheet_id, [e["date"] for e in detail["entries"]])
    changed = False
    now = utc_now()
    for day_date, row in days.items():
        if row.status in (TimesheetStatus.DRAFT, TimesheetStatus.REJECTED):
            row.status = TimesheetStatus.SUBMITTED
            row.submitted_at = now
            row.approved_by = None
            row.approved_at = None
            row.rejection_reason = None
            changed = True
    if not changed:
        raise TimesheetError(
            "Nothing to submit — all logged days are already under review or approved",
            409,
        )

    sheet = await db.get(Timesheet, timesheet_id)
    sheet.submitted_at = now
    sheet.rejection_reason = None
    _sync_sheet_status(sheet, days)
    await db.commit()
    await db.refresh(sheet)
    return await get_detail(db, timesheet_id)


async def submit_day(db: AsyncSession, user_id: int, timesheet_id: int, day: date) -> dict:
    """Owner submits a single day of their own week."""
    detail = await get_detail(db, timesheet_id)
    if detail["user_id"] != user_id:
        raise TimesheetError("You can only submit your own timesheets", 403)
    if _day_hours(detail["entries"], day) <= 0:
        raise TimesheetError(f"No hours logged for {day.isoformat()}", 400)

    days = await _ensure_day_rows(db, timesheet_id, [day])
    row = days[day]
    if row.status not in (TimesheetStatus.DRAFT, TimesheetStatus.REJECTED):
        raise TimesheetError(f"{day.isoformat()} is already '{row.status.value}'", 409)
    row.status = TimesheetStatus.SUBMITTED
    row.submitted_at = utc_now()

    sheet = await db.get(Timesheet, timesheet_id)
    sheet.submitted_at = row.submitted_at
    sheet.rejection_reason = None
    _sync_sheet_status(sheet, days)
    await db.commit()
    await db.refresh(sheet)
    return await get_detail(db, timesheet_id)


async def approve_timesheet(db: AsyncSession, reviewer: User, timesheet_id: int) -> dict:
    """Reviewer approves every submitted day of a team member's week."""
    detail = await get_detail(db, timesheet_id)
    await _assert_can_review(db, reviewer, detail["user_id"])

    days = await _day_rows(db, timesheet_id)
    targets = [d for d, row in days.items() if row.status == TimesheetStatus.SUBMITTED]
    if not targets:
        raise TimesheetError("No submitted days to approve — ask the employee to submit first", 409)

    entries_by_date = detail["entries"]
    now = utc_now()
    for day_date in targets:
        row = days[day_date]
        row.status = TimesheetStatus.APPROVED
        row.approved_by = reviewer.id
        row.approved_at = now
        for entry in entries_by_date:
            if entry["date"] == day_date and entry["project_id"]:
                await _credit_project_hours(db, entry["project_id"], entry["hours"])

    sheet = await db.get(Timesheet, timesheet_id)
    sheet.approved_by = reviewer.id
    sheet.approved_at = now
    sheet.rejection_reason = None
    _sync_sheet_status(sheet, days)
    await notify(
        db,
        detail["user_id"],
        title="Timesheet approved",
        body=(
            f"{reviewer.name} approved your timesheet for the week of "
            f"{detail['week_start'].isoformat()}."
        ),
        type="timesheet",
        link="/timesheets",
    )
    await db.commit()
    await db.refresh(sheet)
    return await get_detail(db, timesheet_id)


async def reject_timesheet(
    db: AsyncSession, reviewer: User, timesheet_id: int, reason: str
) -> dict:
    """Reviewer rejects every submitted day, reopening them for fixes."""
    detail = await get_detail(db, timesheet_id)
    await _assert_can_review(db, reviewer, detail["user_id"])

    days = await _day_rows(db, timesheet_id)
    targets = [d for d, row in days.items() if row.status == TimesheetStatus.SUBMITTED]
    if not targets:
        raise TimesheetError("No submitted days to reject — ask the employee to submit first", 409)

    for day_date in targets:
        row = days[day_date]
        row.status = TimesheetStatus.REJECTED
        row.submitted_at = None
        row.rejection_reason = reason

    sheet = await db.get(Timesheet, timesheet_id)
    sheet.approved_by = reviewer.id
    sheet.approved_at = None
    sheet.submitted_at = None
    sheet.rejection_reason = reason
    _sync_sheet_status(sheet, days)
    await notify(
        db,
        detail["user_id"],
        title="Timesheet rejected",
        body=(
            f"{reviewer.name} rejected your timesheet for the week of "
            f"{detail['week_start'].isoformat()}: {reason}"
        ),
        type="timesheet",
        link="/timesheets",
    )
    await db.commit()
    await db.refresh(sheet)
    return await get_detail(db, timesheet_id)


async def approve_day(db: AsyncSession, reviewer: User, timesheet_id: int, day: date) -> dict:
    """Reviewer approves a single submitted day."""
    detail = await get_detail(db, timesheet_id)
    await _assert_can_review(db, reviewer, detail["user_id"])

    days = await _day_rows(db, timesheet_id)
    row = days.get(day)
    if row is None or row.status != TimesheetStatus.SUBMITTED:
        state = row.status.value if row else "not submitted"
        raise TimesheetError(
            f"{day.isoformat()} is '{state}' — only submitted days can be approved",
            409,
        )

    row.status = TimesheetStatus.APPROVED
    row.approved_by = reviewer.id
    row.approved_at = utc_now()
    for entry in detail["entries"]:
        if entry["date"] == day and entry["project_id"]:
            await _credit_project_hours(db, entry["project_id"], entry["hours"])

    sheet = await db.get(Timesheet, timesheet_id)
    sheet.approved_by = reviewer.id
    sheet.approved_at = row.approved_at
    sheet.rejection_reason = None
    _sync_sheet_status(sheet, days)
    await notify(
        db,
        detail["user_id"],
        title="Timesheet day approved",
        body=(
            f"{reviewer.name} approved your hours for {day.isoformat()} "
            f"(week of {detail['week_start'].isoformat()})."
        ),
        type="timesheet",
        link="/timesheets",
    )
    await db.commit()
    await db.refresh(sheet)
    return await get_detail(db, timesheet_id)


async def reject_day(
    db: AsyncSession, reviewer: User, timesheet_id: int, day: date, reason: str
) -> dict:
    """Reviewer rejects a single submitted day, reopening it for fixes."""
    detail = await get_detail(db, timesheet_id)
    await _assert_can_review(db, reviewer, detail["user_id"])

    days = await _day_rows(db, timesheet_id)
    row = days.get(day)
    if row is None or row.status != TimesheetStatus.SUBMITTED:
        state = row.status.value if row else "not submitted"
        raise TimesheetError(
            f"{day.isoformat()} is '{state}' — only submitted days can be rejected",
            409,
        )

    row.status = TimesheetStatus.REJECTED
    row.submitted_at = None
    row.rejection_reason = reason

    sheet = await db.get(Timesheet, timesheet_id)
    sheet.approved_by = reviewer.id
    sheet.approved_at = None
    sheet.rejection_reason = reason
    _sync_sheet_status(sheet, days)
    await notify(
        db,
        detail["user_id"],
        title="Timesheet day rejected",
        body=(
            f"{reviewer.name} rejected your hours for {day.isoformat()} "
            f"(week of {detail['week_start'].isoformat()}): {reason}"
        ),
        type="timesheet",
        link="/timesheets",
    )
    await db.commit()
    await db.refresh(sheet)
    return await get_detail(db, timesheet_id)


# ── Month export (XLSX / PDF) ───────────────────────────────────────


async def month_export_rows(
    db: AsyncSession, year: int, month: int, user_id: int | None = None
) -> list[dict]:
    """Flat rows for one month of timesheets, grouped by employee downstream."""
    from calendar import monthrange

    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    stmt = (
        select(TimesheetEntry, User.name, User.employee_id, Project.name)
        .join(Timesheet, Timesheet.id == TimesheetEntry.timesheet_id)
        .join(User, User.id == Timesheet.user_id)
        .outerjoin(Project, Project.id == TimesheetEntry.project_id)
        .where(TimesheetEntry.date >= start, TimesheetEntry.date <= end)
        .order_by(User.name, User.id, TimesheetEntry.date, TimesheetEntry.id)
    )
    if user_id is not None:
        stmt = stmt.where(Timesheet.user_id == user_id)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "employee_id": employee_id,
            "employee": name,
            "date": entry.date,
            "project": project_name or "—",
            "description": entry.description or "",
            "hours": entry.hours,
            "status": "logged",  # day-level status lives in timesheet_days
        }
        for entry, name, employee_id, project_name in rows
    ]


async def build_month_xlsx(
    db: AsyncSession, year: int, month: int, user_id: int | None = None
) -> bytes:
    from app.utils.xlsx import write_xlsx

    rows = await month_export_rows(db, year, month, user_id)
    columns = ["Employee ID", "Employee", "Date", "Project", "Description", "Hours"]
    data = [
        [
            row["employee_id"],
            row["employee"],
            row["date"].isoformat(),
            row["project"],
            row["description"],
            float(row["hours"]),
        ]
        for row in rows
    ]
    return write_xlsx(
        [{"name": f"Timesheets {year}-{month:02d}", "columns": columns, "rows": data}]
    )


async def build_month_pdf(
    db: AsyncSession, year: int, month: int, user_id: int | None = None
) -> bytes:
    from app.utils.pdf import timesheet_month_pdf

    rows = await month_export_rows(db, year, month, user_id)
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["employee_id"], row["employee"]), []).append(row)

    pdf_groups = []
    grand_total = Decimal("0")
    for (employee_id, employee), group_rows in sorted(groups.items()):
        total = sum((r["hours"] for r in group_rows), Decimal("0"))
        grand_total += total
        pdf_groups.append(
            {
                "heading": f"{employee} ({employee_id})",
                "rows": [
                    {
                        "date": r["date"].isoformat(),
                        "project": r["project"],
                        "description": r["description"],
                        "hours": _hours_text(r["hours"]),
                    }
                    for r in group_rows
                ],
                "total_hours": _hours_text(total),
            }
        )
    return timesheet_month_pdf(
        title=f"Timesheets — {year}-{month:02d}",
        groups=pdf_groups,
        grand_total=_hours_text(grand_total),
    )


# ── Scheduled helpers (Friday reminder / Monday auto-submit) ────────


async def send_weekly_reminders(db: AsyncSession) -> int:
    """Nudge active users who haven't submitted this week's timesheet.

    Runs Friday afternoon (local time); deduplicated per user per week.
    """
    from app.core.config import settings

    if not settings.timesheet_reminder_enabled:
        return 0
    local_now = now_local()
    today = local_now.date()
    if today.weekday() != 4 or local_now.hour < settings.timesheet_reminder_hour:
        return 0

    monday = monday_of(today)
    reminded = set(
        (
            await db.execute(
                select(Notification.user_id).where(
                    Notification.title == "Weekly timesheet reminder",
                    Notification.created_at >= monday,
                )
            )
        ).scalars()
    )

    users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
    sheets = {
        ts.user_id: ts
        for ts in (
            await db.execute(select(Timesheet).where(Timesheet.week_start == monday))
        ).scalars()
    }

    sent = 0
    for user in users:
        if user.id in reminded:
            continue
        sheet = sheets.get(user.id)
        if sheet is not None and sheet.status in (
            TimesheetStatus.SUBMITTED,
            TimesheetStatus.APPROVED,
        ):
            continue
        await notify(
            db,
            user.id,
            title="Weekly timesheet reminder",
            body=("Please log today's hours and submit your timesheet before the week closes."),
            type="timesheet",
            link="/timesheets",
        )
        sent += 1
    if sent:
        await db.commit()
    return sent


async def auto_submit_finished_weeks(db: AsyncSession) -> int:
    """Auto-submit last week's DRAFT timesheets that have hours.

    Only touches plain drafts — sheets with rejected days keep waiting on
    the employee's fixes.
    """
    from app.core.config import settings

    if not settings.timesheet_autosubmit_enabled:
        return 0
    local_now = now_local()
    if local_now.date().weekday() != 0 or local_now.hour >= settings.timesheet_autosubmit_hour:
        return 0

    finished_monday = monday_of(local_now.date()) - timedelta(days=7)
    sheets = (
        (
            await db.execute(
                select(Timesheet).where(
                    Timesheet.week_start == finished_monday,
                    Timesheet.status == TimesheetStatus.DRAFT,
                )
            )
        )
        .scalars()
        .all()
    )

    submitted = 0
    for sheet in sheets:
        hours = (
            await db.execute(
                select(func.coalesce(func.sum(TimesheetEntry.hours), 0)).where(
                    TimesheetEntry.timesheet_id == sheet.id
                )
            )
        ).scalar_one()
        if not hours or Decimal(str(hours)) <= 0:
            continue
        days = await _day_rows(db, sheet.id)
        now = utc_now()
        touched = False
        for row in days.values():
            if row.status == TimesheetStatus.DRAFT:
                row.status = TimesheetStatus.SUBMITTED
                row.submitted_at = now
                touched = True
        if not touched:
            continue
        sheet.submitted_at = now
        sheet.rejection_reason = None
        _sync_sheet_status(sheet, days)
        await notify(
            db,
            sheet.user_id,
            title="Timesheet auto-submitted",
            body=(
                f"Your timesheet for the week of {finished_monday.isoformat()} "
                "was automatically submitted because it was still a draft."
            ),
            type="timesheet",
            link="/timesheets",
        )
        submitted += 1
    if submitted:
        await db.commit()
    return submitted
