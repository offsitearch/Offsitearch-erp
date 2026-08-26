"""Leave management service.

Leave applications, approval workflows, and balance tracking.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Holiday, Setting, User
from app.modules.attendance.service import mark_on_leave
from app.modules.leave.defaults import LEAVE_SETTINGS
from app.modules.leave.models import Leave, LeaveBalance
from app.modules.leave.schemas import LeaveApplyRequest
from app.utils.enums import LeaveStatus, LeaveType
from app.utils.errors import LeaveError
from app.utils.shared import now_local, utc_now

_ZERO = Decimal("0.00")
_HALF = Decimal("0.50")
_ONE = Decimal("1.00")


async def load_leave_policy(db: AsyncSession) -> dict:
    cfg: dict = {key: dict(value) for key, value in LEAVE_SETTINGS.items()}
    result = await db.execute(select(Setting).where(Setting.group == "leave"))
    for setting in result.scalars().all():
        cfg[setting.key] = setting.value
    return cfg


async def get_holiday_dates(db: AsyncSession, from_date: date, to_date: date) -> set[date]:
    result = await db.execute(
        select(Holiday.date).where(and_(Holiday.date >= from_date, Holiday.date <= to_date))
    )
    return set(result.scalars().all())


def working_day_count(
    from_date: date, to_date: date, holidays: set[date], half_first: bool, half_second: bool
) -> Decimal:
    """Business days (Mon-Fri) minus holidays, adjusted for half days."""
    days = Decimal("0.00")
    cursor = from_date
    while cursor <= to_date:
        if cursor.weekday() < 5 and cursor not in holidays:
            days += _ONE
        cursor += timedelta(days=1)
    if half_first and days > 0:
        days -= _HALF
    if half_second and days > 0:
        days -= _HALF
    return max(days, _ZERO)


def _iter_days(from_date: date, to_date: date):
    cursor = from_date
    while cursor <= to_date:
        yield cursor
        cursor += timedelta(days=1)


async def compute_total_days(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    half_first: bool,
    half_second: bool,
) -> Decimal:
    holidays = await get_holiday_dates(db, from_date, to_date)
    return working_day_count(from_date, to_date, holidays, half_first, half_second)


async def ensure_balances(db: AsyncSession, user_id: int, year: int) -> None:
    """Create any missing balance rows for the year from the policy defaults."""
    policy = (await load_leave_policy(db))["policy"]
    existing = (
        (
            await db.execute(
                select(LeaveBalance).where(
                    LeaveBalance.user_id == user_id, LeaveBalance.year == year
                )
            )
        )
        .scalars()
        .all()
    )
    existing_types = {row.leave_type for row in existing}
    for name, allocated in policy.items():
        if name == "carry_forward":
            continue
        leave_type = LeaveType(name)
        if leave_type in existing_types:
            continue
        db.add(
            LeaveBalance(
                user_id=user_id,
                leave_type=leave_type,
                year=year,
                allocated=Decimal(str(allocated)),
                used=_ZERO,
            )
        )
    await db.commit()


async def get_balances(db: AsyncSession, user_id: int, year: int) -> list[dict]:
    await ensure_balances(db, user_id, year)
    rows = (
        (
            await db.execute(
                select(LeaveBalance)
                .where(LeaveBalance.user_id == user_id, LeaveBalance.year == year)
                .order_by(LeaveBalance.leave_type)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "leave_type": row.leave_type.value,
            "year": row.year,
            "allocated": row.allocated,
            "used": row.used,
            "remaining": Decimal(str(row.allocated)) - Decimal(str(row.used)),
        }
        for row in rows
    ]


async def _effective_used(
    db: AsyncSession, user_id: int, leave_type: LeaveType, year: int
) -> Decimal:
    """Used days = approved usage + pending requests already reserved in the year."""
    rows = (
        (
            await db.execute(
                select(Leave).where(
                    Leave.user_id == user_id,
                    Leave.leave_type == leave_type,
                    Leave.from_date >= date(year, 1, 1),
                    Leave.to_date <= date(year, 12, 31),
                    Leave.status.in_([LeaveStatus.APPROVED, LeaveStatus.PENDING]),
                )
            )
        )
        .scalars()
        .all()
    )
    return sum((Decimal(str(row.total_days)) for row in rows), _ZERO)


async def apply_leave(db: AsyncSession, user: User, payload: LeaveApplyRequest) -> Leave:
    if payload.to_date < payload.from_date:
        raise LeaveError("to_date must be on or after from_date", 400)

    today = now_local().date()
    if payload.from_date < today:
        raise LeaveError("Cannot apply for a date in the past", 400)

    overlap = (
        (
            await db.execute(
                select(Leave).where(
                    Leave.user_id == user.id,
                    Leave.status.in_([LeaveStatus.PENDING, LeaveStatus.APPROVED]),
                    Leave.from_date <= payload.to_date,
                    Leave.to_date >= payload.from_date,
                )
            )
        )
        .scalars()
        .first()
    )
    if overlap is not None:
        raise LeaveError(
            f"Overlaps with an existing {overlap.leave_type.value} leave ({overlap.from_date} to {overlap.to_date})",
            409,
        )

    total_days = await compute_total_days(
        db, payload.from_date, payload.to_date, payload.half_day_first, payload.half_day_second
    )
    if total_days <= _ZERO:
        raise LeaveError("Selected dates contain no working days", 400)

    if payload.leave_type != LeaveType.UNPAID:
        year = payload.from_date.year
        await ensure_balances(db, user.id, year)
        balance = (
            (
                await db.execute(
                    select(LeaveBalance).where(
                        LeaveBalance.user_id == user.id,
                        LeaveBalance.leave_type == payload.leave_type,
                        LeaveBalance.year == year,
                    )
                )
            )
            .scalars()
            .first()
        )
        if balance is None:
            raise LeaveError(
                f"No balance configured for {payload.leave_type.value} leave in {year}", 400
            )
        used = await _effective_used(db, user.id, payload.leave_type, year)
        remaining = Decimal(str(balance.allocated)) - used
        if remaining < total_days:
            raise LeaveError(
                f"Insufficient {payload.leave_type.value} leave balance "
                f"(remaining {remaining:g}, requested {total_days:g})",
                409,
            )

    leave = Leave(
        user_id=user.id,
        leave_type=payload.leave_type,
        from_date=payload.from_date,
        to_date=payload.to_date,
        total_days=total_days,
        half_day_first=payload.half_day_first,
        half_day_second=payload.half_day_second,
        reason=payload.reason,
        attachment=payload.attachment,
        status=LeaveStatus.PENDING,
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave


async def cancel_leave(db: AsyncSession, user: User, leave_id: int) -> Leave:
    leave = (await db.execute(select(Leave).where(Leave.id == leave_id))).scalars().first()
    if leave is None:
        raise LeaveError("Leave request not found", 404)
    if leave.user_id != user.id:
        raise LeaveError("Not allowed to cancel this leave", 403)
    if leave.status != LeaveStatus.PENDING:
        raise LeaveError("Only pending leaves can be cancelled", 409)
    leave.status = LeaveStatus.CANCELLED
    await db.commit()
    await db.refresh(leave)
    return leave


async def _mark_attendance_on_leave(db: AsyncSession, leave: Leave) -> None:
    """Write ON_LEAVE attendance rows for each working day of an approved leave."""
    holidays = await get_holiday_dates(db, leave.from_date, leave.to_date)
    working_days = [
        day
        for day in _iter_days(leave.from_date, leave.to_date)
        if day.weekday() < 5 and day not in holidays
    ]
    await mark_on_leave(
        db,
        leave.user_id,
        working_days,
        f"Approved {leave.leave_type.value} leave",
    )


async def approve_leave(db: AsyncSession, admin: User, leave_id: int) -> Leave:
    leave = (await db.execute(select(Leave).where(Leave.id == leave_id))).scalars().first()
    if leave is None:
        raise LeaveError("Leave request not found", 404)
    if leave.status != LeaveStatus.PENDING:
        raise LeaveError("Only pending leaves can be approved", 409)
    if leave.user_id == admin.id:
        raise LeaveError("You cannot approve your own leave", 409)

    leave.status = LeaveStatus.APPROVED
    leave.approved_by = admin.id
    leave.approved_at = utc_now()

    if leave.leave_type != LeaveType.UNPAID:
        year = leave.from_date.year
        days = Decimal(str(leave.total_days))

        # Ensure balance row exists
        balance = (
            (
                await db.execute(
                    select(LeaveBalance).where(
                        LeaveBalance.user_id == leave.user_id,
                        LeaveBalance.leave_type == leave.leave_type,
                        LeaveBalance.year == year,
                    )
                )
            )
            .scalars()
            .first()
        )
        if balance is None:
            await ensure_balances(db, leave.user_id, year)

        # Atomic increment — prevents race condition when two admins
        # approve concurrently for the same user/leave type.
        result = await db.execute(
            update(LeaveBalance)
            .where(
                LeaveBalance.user_id == leave.user_id,
                LeaveBalance.leave_type == leave.leave_type,
                LeaveBalance.year == year,
                LeaveBalance.used + days <= LeaveBalance.allocated,
            )
            .values(used=LeaveBalance.used + days)
        )
        if result.rowcount == 0:
            raise LeaveError("Insufficient leave balance", 409)

    await db.commit()
    await _mark_attendance_on_leave(db, leave)
    await db.refresh(leave)
    return leave


async def reject_leave(db: AsyncSession, admin: User, leave_id: int, reason: str) -> Leave:
    leave = (await db.execute(select(Leave).where(Leave.id == leave_id))).scalars().first()
    if leave is None:
        raise LeaveError("Leave request not found", 404)
    if leave.status != LeaveStatus.PENDING:
        raise LeaveError("Only pending leaves can be rejected", 409)
    if leave.user_id == admin.id:
        raise LeaveError("You cannot reject your own leave", 409)
    leave.status = LeaveStatus.REJECTED
    leave.rejection_reason = reason
    leave.approved_by = admin.id
    leave.approved_at = utc_now()
    await db.commit()
    await db.refresh(leave)
    return leave


async def list_mine(
    db: AsyncSession, user_id: int, page: int = 1, page_size: int = 20
) -> tuple[list[Leave], int]:
    base = select(Leave).where(Leave.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    result = await db.execute(
        base.order_by(Leave.from_date.desc(), Leave.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def _leave_row(leave: Leave, user: User, department_name: str | None) -> dict:
    return {
        "id": leave.id,
        "user_id": leave.user_id,
        "leave_type": leave.leave_type.value,
        "from_date": leave.from_date,
        "to_date": leave.to_date,
        "total_days": leave.total_days,
        "half_day_first": leave.half_day_first,
        "half_day_second": leave.half_day_second,
        "reason": leave.reason,
        "status": leave.status.value,
        "approved_by": leave.approved_by,
        "approved_at": leave.approved_at,
        "rejection_reason": leave.rejection_reason,
        "created_at": leave.created_at,
        "user_name": user.name,
        "employee_id": user.employee_id,
        "designation": user.designation,
        "department": department_name,
    }


async def pending_queue(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    stmt = (
        select(Leave, User, Department.name)
        .join(User, User.id == Leave.user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(Leave.status == LeaveStatus.PENDING)
        .order_by(Leave.from_date, Leave.created_at)
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    return [await _leave_row(leave, user, dept) for leave, user, dept in result.all()], total


async def team_availability(db: AsyncSession, from_date: date, to_date: date) -> list[dict]:
    stmt = (
        select(Leave, User, Department.name)
        .join(User, User.id == Leave.user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(
            Leave.status.in_([LeaveStatus.APPROVED, LeaveStatus.PENDING]),
            Leave.from_date <= to_date,
            Leave.to_date >= from_date,
        )
        .order_by(Leave.from_date)
    )
    result = await db.execute(stmt)
    rows = []
    for leave, user, dept in result.all():
        rows.append(
            {
                "user_id": user.id,
                "user_name": user.name,
                "department": dept,
                "leave_type": leave.leave_type.value,
                "status": leave.status.value,
                "from_date": leave.from_date,
                "to_date": leave.to_date,
            }
        )
    return rows
