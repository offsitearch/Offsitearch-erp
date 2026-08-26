"""Payroll processing, payslip PDF generation, and salary proration."""

import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Attendance, Department, Holiday, SalaryComponent, User
from app.modules.payroll.models import PayrollEntry, PayrollRun
from app.utils.enums import AttendanceStatus, PayrollStatus
from app.utils.errors import PayrollError
from app.utils.pdf import payslip_pdf
from app.utils.shared import q as _q, utc_now

_WORK_DAY_STATUSES = (
    AttendanceStatus.PRESENT,
    AttendanceStatus.LATE,
    AttendanceStatus.HALF_DAY,
    AttendanceStatus.WORK_FROM_HOME,
    AttendanceStatus.ON_LEAVE,
)


def _month_weekdays(month: int, year: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    return sum(1 for day in range(1, last_day + 1) if date(year, month, day).weekday() < 5)


async def _holidays(db: AsyncSession, month: int, year: int) -> set[date]:
    start = date(year, month, 1)
    end = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    rows = await db.execute(select(Holiday.date).where(Holiday.date >= start, Holiday.date < end))
    return set(rows.scalars().all())


async def _working_days_for(
    db: AsyncSession, user_id: int, month: int, year: int, holidays: set[date]
) -> int:
    start = date(year, month, 1)
    end = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    rows = await db.execute(
        select(Attendance.date).where(
            Attendance.user_id == user_id,
            Attendance.date >= start,
            Attendance.date < end,
            Attendance.status.in_(_WORK_DAY_STATUSES),
        )
    )
    return sum(1 for day in rows.scalars().all() if day not in holidays)


async def _compute_entries(db: AsyncSession, month: int, year: int) -> list[dict]:
    holidays = await _holidays(db, month, year)
    payable = _month_weekdays(month, year) - sum(1 for holiday in holidays if holiday.weekday() < 5)
    stmt = (
        select(User, SalaryComponent, Department.name)
        .join(SalaryComponent, SalaryComponent.user_id == User.id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(User.is_active.is_(True))
        .order_by(User.name)
    )
    rows = (await db.execute(stmt)).all()

    # Batch-fetch working days for all staff in one query (eliminates N+1)
    start = date(year, month, 1)
    end = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    user_ids = [user.id for user, _, _ in rows]
    attendance_stmt = select(Attendance.user_id, Attendance.date).where(
        Attendance.user_id.in_(user_ids),
        Attendance.date >= start,
        Attendance.date < end,
        Attendance.status.in_(_WORK_DAY_STATUSES),
    )
    attendance_rows = (await db.execute(attendance_stmt)).all()
    # Group dates by user_id, exclude holidays
    user_dates: dict[int, set[date]] = {}
    for uid, dt in attendance_rows:
        user_dates.setdefault(uid, set()).add(dt)
    working_days_map = {
        uid: sum(1 for d in dates if d not in holidays) for uid, dates in user_dates.items()
    }

    entries: list[dict] = []
    for user, salary, department_name in rows:
        working_days = working_days_map.get(user.id, 0)
        ratio = (Decimal(working_days) / Decimal(payable)) if payable else Decimal("0")
        monthly_gross = (salary.basic or 0) + (salary.hra or 0) + (salary.special_allowance or 0)
        gross = _q(Decimal(monthly_gross) * ratio)
        deductions = _q(Decimal(salary.pf_deduction or 0) * ratio)
        entries.append(
            {
                "user_id": user.id,
                "user_name": user.name,
                "employee_id": user.employee_id,
                "designation": user.designation,
                "department": department_name,
                "working_days": working_days,
                "gross_salary": gross,
                "deductions": deductions,
                "net_pay": _q(gross - deductions),
            }
        )
    return entries


async def _entries_for_run(db: AsyncSession, run_id: int) -> list[dict]:
    stmt = (
        select(PayrollEntry, User, Department.name)
        .join(User, User.id == PayrollEntry.user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .where(PayrollEntry.payroll_run_id == run_id)
        .order_by(User.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "user_id": entry.user_id,
            "user_name": user.name,
            "employee_id": user.employee_id,
            "designation": user.designation,
            "department": department_name,
            "working_days": entry.working_days,
            "gross_salary": entry.gross_salary,
            "deductions": entry.deductions,
            "net_pay": entry.net_pay,
        }
        for entry, user, department_name in rows
    ]


def _run_dict(
    run: PayrollRun | None, month: int, year: int, entries: list[dict], preview: bool
) -> dict:
    total_pay = sum((entry["net_pay"] for entry in entries), Decimal("0"))
    return {
        "id": run.id if run else None,
        "month": month,
        "year": year,
        "status": run.status.value if run else PayrollStatus.DRAFT.value,
        "processed_by": run.processed_by if run else None,
        "processed_at": run.processed_at if run else None,
        "is_preview": preview,
        "total_pay": _q(total_pay),
        "entries": entries,
    }


async def _find_run(db: AsyncSession, month: int, year: int) -> PayrollRun | None:
    return (
        await db.execute(
            select(PayrollRun).where(PayrollRun.month == month, PayrollRun.year == year)
        )
    ).scalar_one_or_none()


async def get_run(db: AsyncSession, month: int, year: int) -> dict:
    run = await _find_run(db, month, year)
    if run is not None:
        entries = await _entries_for_run(db, run.id)
        return _run_dict(run, month, year, entries, preview=False)
    entries = await _compute_entries(db, month, year)
    return _run_dict(None, month, year, entries, preview=True)


async def process_run(db: AsyncSession, month: int, year: int, processor: User) -> dict:
    existing = await _find_run(db, month, year)
    if existing is not None:
        if existing.status == PayrollStatus.PROCESSED:
            raise PayrollError("Payroll for this month has already been processed", 409)
        await db.delete(existing)
        await db.flush()

    entries = await _compute_entries(db, month, year)
    if not entries:
        raise PayrollError("No employees with salary data found for this month", 409)

    run = PayrollRun(
        month=month,
        year=year,
        status=PayrollStatus.PROCESSED,
        processed_by=processor.id,
        processed_at=utc_now(),
    )
    db.add(run)
    await db.flush()

    payslip_folder = Path(settings.upload_dir) / "payroll" / str(run.id)
    payslip_folder.mkdir(parents=True, exist_ok=True)
    for entry_data in entries:
        entry = PayrollEntry(
            payroll_run_id=run.id,
            user_id=entry_data["user_id"],
            working_days=entry_data["working_days"],
            gross_salary=entry_data["gross_salary"],
            deductions=entry_data["deductions"],
            net_pay=entry_data["net_pay"],
        )
        db.add(entry)
        entry.payslip_path = _write_payslip(payslip_folder, run, entry_data)

    await db.commit()
    await db.refresh(run)
    entries_out = await _entries_for_run(db, run.id)
    return _run_dict(run, month, year, entries_out, preview=False)


def _write_payslip(folder: Path, run: PayrollRun, entry: dict) -> str | None:
    try:
        month_label = f"{calendar.month_name[run.month]} {run.year}"
        content = payslip_pdf(
            employee_name=entry["user_name"],
            employee_id=entry["employee_id"] or f"U-{entry['user_id']}",
            designation=entry["designation"],
            month_label=month_label,
            working_days=entry["working_days"],
            gross_salary=entry["gross_salary"],
            deductions=entry["deductions"],
            net_pay=entry["net_pay"],
        )
        filename = f"{entry['user_id']}.pdf"
        (folder / filename).write_bytes(content)
        return f"payroll/{run.id}/{filename}"
    except Exception:
        return None


async def get_payslip(
    db: AsyncSession, month: int, year: int, user_id: int
) -> tuple[bytes | None, str | None]:
    run = await _find_run(db, month, year)
    if run is None or run.status != PayrollStatus.PROCESSED:
        raise PayrollError("Payroll has not been processed for this month", 404)
    entry = (
        await db.execute(
            select(PayrollEntry).where(
                PayrollEntry.payroll_run_id == run.id, PayrollEntry.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        raise PayrollError("Payslip not found for this employee", 404)
    filename = f"payslip-{user_id}-{month}-{year}.pdf"
    if entry.payslip_path:
        path = Path(settings.upload_dir) / entry.payslip_path
        if path.exists():
            return path.read_bytes(), filename
    row = (
        await db.execute(
            select(User, Department.name)
            .join(User, User.id == entry.user_id)
            .outerjoin(Department, Department.id == User.department_id)
        )
    ).first()
    if row is None:
        raise PayrollError("Employee not found", 404)
    user, department_name = row
    month_label = f"{calendar.month_name[month]} {year}"
    content = payslip_pdf(
        employee_name=user.name,
        employee_id=user.employee_id or f"U-{user.id}",
        designation=user.designation,
        month_label=month_label,
        working_days=entry.working_days,
        gross_salary=entry.gross_salary,
        deductions=entry.deductions,
        net_pay=entry.net_pay,
    )
    return content, filename
