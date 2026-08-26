"""Attendance service.

Clock-in/out, bulk attendance marking, monthly summaries, and attendance reports.
"""

from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Setting, User
from app.modules.attendance.defaults import ATTENDANCE_SETTINGS
from app.modules.attendance.models import Attendance
from app.modules.attendance.repository import attendance_repository
from app.modules.attendance.schemas import CheckInRequest, CheckOutRequest
from app.utils.enums import AttendanceMethod, AttendanceStatus
from app.utils.errors import AttendanceError
from app.utils.shared import now_local, to_local


def _minutes_between(after: time, before: time) -> int:
    base = date(2000, 1, 1)
    delta = datetime.combine(base, after) - datetime.combine(base, before)
    return max(0, int(delta.total_seconds() // 60))


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def compute_check_in_status(
    check_in_local: datetime,
    working_hours: dict,
    late_policy: dict,
) -> tuple[AttendanceStatus, int]:
    """Derive status and late minutes from the (business-local) check-in time."""
    start = _parse_time(working_hours["start"])
    late_threshold = _parse_time(late_policy["late_threshold"])
    half_day_threshold = _parse_time(late_policy["half_day_threshold"])
    t = check_in_local.time()
    if t <= late_threshold:
        return AttendanceStatus.PRESENT, 0
    if t <= half_day_threshold:
        return AttendanceStatus.LATE, _minutes_between(t, start)
    return AttendanceStatus.HALF_DAY, _minutes_between(t, start)


def compute_total_hours(check_in: datetime, check_out: datetime, working_hours: dict) -> Decimal:
    """Total billed hours, subtracting the scheduled break."""
    break_minutes = int(working_hours.get("break_minutes", 0))
    minutes = (check_out - check_in).total_seconds() / 60 - break_minutes
    return Decimal(str(round(max(minutes, 0) / 60, 2)))


async def load_attendance_settings(db: AsyncSession) -> dict:
    """Load attendance settings (JSONB rows) merged over seed defaults."""
    cfg: dict = {key: dict(value) for key, value in ATTENDANCE_SETTINGS.items()}
    result = await db.execute(select(Setting).where(Setting.group == "attendance"))
    for setting in result.scalars().all():
        cfg[setting.key] = setting.value
    return cfg


async def check_in(
    db: AsyncSession,
    user: User,
    payload: CheckInRequest,
    now: datetime | None = None,
) -> Attendance:
    now = now or now_local()
    local_now = to_local(now)
    existing = await attendance_repository.get_by_user_date(db, user.id, local_now.date())
    if existing is not None and existing.check_in_time is not None and existing.check_out_time is None:
        raise AttendanceError("Already checked in today")

    cfg = await load_attendance_settings(db)
    status, late_minutes = compute_check_in_status(
        local_now, cfg["working_hours"], cfg["late_policy"]
    )
    if existing is not None:
        existing.check_in_time = now
        existing.check_out_time = None
        existing.status = status
        existing.late_minutes = late_minutes
        existing.check_in_method = payload.method
        existing.check_in_location = payload.location
        if payload.notes:
            existing.notes = payload.notes
        await db.commit()
        await db.refresh(existing)
        return existing

    record = Attendance(
        user_id=user.id,
        date=local_now.date(),
        check_in_time=now,
        status=status,
        late_minutes=late_minutes,
        check_in_method=payload.method,
        check_in_location=payload.location,
        notes=payload.notes,
    )
    return await attendance_repository.add(db, record)


async def check_out(
    db: AsyncSession,
    user: User,
    payload: CheckOutRequest,
    now: datetime | None = None,
) -> Attendance:
    now = now or now_local()
    record = await attendance_repository.get_by_user_date(db, user.id, to_local(now).date())
    if record is None or record.check_in_time is None:
        raise AttendanceError("Not checked in today", 404)
    if record.check_out_time is not None:
        raise AttendanceError("Already checked out today")

    cfg = await load_attendance_settings(db)
    record.check_out_time = now
    session_hours = compute_total_hours(record.check_in_time, now, cfg["working_hours"])
    previous = Decimal(str(record.total_hours or 0))
    record.total_hours = previous + session_hours
    if payload.notes:
        record.notes = payload.notes
    await db.commit()
    await db.refresh(record)
    return record


def _row_from(attendance: Attendance, user: User, department_name: str | None) -> dict:
    return {
        "id": attendance.id,
        "user_id": attendance.user_id,
        "date": attendance.date,
        "check_in_time": attendance.check_in_time,
        "check_out_time": attendance.check_out_time,
        "status": attendance.status.value,
        "late_minutes": attendance.late_minutes,
        "total_hours": attendance.total_hours,
        "check_in_method": attendance.check_in_method.value,
        "check_in_location": attendance.check_in_location,
        "notes": attendance.notes,
        "marked_by": attendance.marked_by,
        "user_name": user.name,
        "employee_id": user.employee_id,
        "designation": user.designation,
        "department": department_name,
        "phone": user.phone,
    }


async def rows_for_date(
    db: AsyncSession,
    date_: date,
    department_id: int | None = None,
    status: str | None = None,
) -> list[dict]:
    stmt = (
        select(Attendance, User, Department.name)
        .join(User, User.id == Attendance.user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(Attendance.date == date_)
    )
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    if status is not None:
        stmt = stmt.where(Attendance.status == status)
    stmt = stmt.order_by(Attendance.check_in_time)
    result = await db.execute(stmt)
    return [_row_from(att, user, dept) for att, user, dept in result.all()]


async def monthly_records(
    db: AsyncSession, user_id: int, year: int, month: int
) -> tuple[list[Attendance], dict[str, int]]:
    records = await attendance_repository.list_by_user_month(db, user_id, year, month)
    totals = dict(Counter(record.status.value for record in records))
    return records, totals


async def bulk_mark(
    db: AsyncSession,
    admin: User,
    date_: date,
    entries: list,
) -> None:
    deduped = {entry.user_id: entry for entry in entries}
    user_ids = list(deduped.keys())

    # Batch-fetch existing records for all users on this date (eliminates N+1)
    existing_stmt = select(Attendance).where(
        Attendance.user_id.in_(user_ids),
        Attendance.date == date_,
    )
    existing_records = (await db.execute(existing_stmt)).scalars().all()
    existing_map = {r.user_id: r for r in existing_records}

    # Load settings once (eliminates repeated per-iteration load)
    cfg = await load_attendance_settings(db)

    for user_id, entry in deduped.items():
        record = existing_map.get(user_id)
        if record is None:
            record = Attendance(
                user_id=user_id,
                date=date_,
                status=entry.status,
                check_in_method=AttendanceMethod.MANUAL,
                marked_by=admin.id,
                notes=entry.notes,
            )
            db.add(record)
        else:
            record.status = entry.status
            record.marked_by = admin.id
            if entry.notes is not None:
                record.notes = entry.notes
        if entry.check_in_time is not None:
            record.check_in_time = entry.check_in_time
        if entry.check_out_time is not None:
            record.check_out_time = entry.check_out_time
            if entry.check_in_time is not None:
                record.total_hours = compute_total_hours(
                    entry.check_in_time, entry.check_out_time, cfg["working_hours"]
                )
            elif record.check_in_time is not None:
                record.total_hours = compute_total_hours(
                    record.check_in_time, entry.check_out_time, cfg["working_hours"]
                )
    await db.commit()


async def update_record(db: AsyncSession, record_id: int, payload) -> Attendance:
    record = await attendance_repository.get(db, record_id)
    if record is None:
        raise AttendanceError("Attendance record not found", 404)

    data = payload.model_dump(exclude_unset=True)
    if "check_in_time" in data:
        record.check_in_time = data["check_in_time"]
    if "check_out_time" in data:
        record.check_out_time = data["check_out_time"]
    if "notes" in data:
        record.notes = data["notes"]

    status_explicit = "status" in data and data["status"] is not None
    if status_explicit:
        record.status = data["status"]

    if "check_in_time" in data or "check_out_time" in data:
        cfg = await load_attendance_settings(db)
        if record.check_in_time is not None and record.check_out_time is not None:
            record.total_hours = compute_total_hours(
                record.check_in_time, record.check_out_time, cfg["working_hours"]
            )
        else:
            record.total_hours = 0
        if record.check_in_time is not None and not status_explicit:
            status, late_minutes = compute_check_in_status(
                to_local(record.check_in_time), cfg["working_hours"], cfg["late_policy"]
            )
            record.status = status
            record.late_minutes = late_minutes

    await db.commit()
    await db.refresh(record)
    return record


async def report_rows(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
) -> list[dict]:
    stmt = (
        select(Attendance, User, Department.name)
        .join(User, User.id == Attendance.user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(Attendance.date >= from_date, Attendance.date <= to_date)
    )
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    stmt = stmt.order_by(Attendance.date, User.name)
    result = await db.execute(stmt)
    return [_row_from(att, user, dept) for att, user, dept in result.all()]


def _attendance_sheets(rows: list[dict]) -> list[dict]:
    return [
        {
            "name": "Attendance",
            "columns": [
                "date",
                "employee_id",
                "user_name",
                "department",
                "designation",
                "phone",
                "status",
                "check_in_time",
                "check_out_time",
                "late_minutes",
                "total_hours",
            ],
            "rows": [
                [
                    row["date"],
                    row["employee_id"],
                    row["user_name"],
                    row["department"],
                    row["designation"],
                    row["phone"] or "N/A",
                    row["status"],
                    row["check_in_time"].isoformat() if row["check_in_time"] else "",
                    row["check_out_time"].isoformat() if row["check_out_time"] else "",
                    row["late_minutes"],
                    row["total_hours"],
                ]
                for row in rows
            ],
        }
    ]


async def mark_on_leave(
    db: AsyncSession,
    user_id: int,
    working_days: list[date],
    note: str,
) -> None:
    """Cross-module contract: write ON_LEAVE rows for the given working days.

    Skips days that already have an attendance record, then commits. Owned by
    the attendance module so other modules (leave) never touch the table raw.
    """
    if not working_days:
        return
    existing_stmt = select(Attendance.date).where(
        Attendance.user_id == user_id,
        Attendance.date.in_(working_days),
    )
    existing_dates = set((await db.execute(existing_stmt)).scalars().all())
    for day in working_days:
        if day in existing_dates:
            continue
        db.add(
            Attendance(
                user_id=user_id,
                date=day,
                status=AttendanceStatus.ON_LEAVE,
                check_in_method=AttendanceMethod.MANUAL,
                notes=note,
            )
        )
    await db.commit()
