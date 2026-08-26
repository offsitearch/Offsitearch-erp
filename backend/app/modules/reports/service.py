"""Reporting: attendance, project, finance, and HR reports."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.shared import now_local

from app.models import (
    Attendance,
    Client,
    Department,
    Expense,
    Invoice,
    Leave,
    OrgLevel,
    Project,
    Timesheet,
    TimesheetEntry,
    User,
)
from app.modules.finance.service import _period_bounds, _status_for
from app.utils.enums import (
    AttendanceStatus,
    ExpenseStatus,
    InvoiceStatus,
    LeaveStatus,
)
from app.utils.xlsx import write_xlsx
from app.utils.shared import q as _q

_ACTIVE_PROJECT_STATUSES = (
    "concept",
    "design",
    "under_review",
    "in_construction",
    "on_hold",
)


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - date.resolution


def _summary_rows(summary: dict) -> list[list]:
    return [[str(key), value] for key, value in summary.items()]


def _to_xlsx(title: str, summary: dict, columns: list[str], rows: list[list]) -> bytes:
    sheets = [{"name": "Summary", "columns": ["Metric", "Value"], "rows": _summary_rows(summary)}]
    sheets.append({"name": "Detail", "columns": columns, "rows": rows})
    return write_xlsx(sheets)


def _to_csv(columns: list[str], rows: list[list]) -> str:
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)
    return buffer.getvalue()


async def projects_report(
    db: AsyncSession,
    status: str | None = None,
    project_type: str | None = None,
) -> dict:
    stmt = select(Project, Client.name).outerjoin(Client, Client.id == Project.client_id)
    if status:
        stmt = stmt.where(Project.status == status)
    if project_type:
        stmt = stmt.where(Project.project_type == project_type)
    stmt = stmt.order_by(Project.project_code)
    rows = (await db.execute(stmt)).all()

    exp_stmt = (
        select(Expense.project_id, func.sum(Expense.amount))
        .where(Expense.status == ExpenseStatus.APPROVED)
        .group_by(Expense.project_id)
    )
    exp_sums = dict((await db.execute(exp_stmt)).all())

    detail: list[dict] = []
    total_budget = Decimal("0")
    total_fee = Decimal("0")
    total_expenses = Decimal("0")
    total_hours = 0
    active_count = 0
    for project, client_name in rows:
        expenses = _q(exp_sums.get(project.id, 0))
        budget = _q(project.budget)
        fee = _q(project.studio_fee)
        hours = int(project.hours_logged or 0)
        total_budget += budget
        total_fee += fee
        total_expenses += expenses
        total_hours += hours
        if project.status.value in _ACTIVE_PROJECT_STATUSES:
            active_count += 1
        detail.append(
            {
                "project_code": project.project_code,
                "name": project.name,
                "client_name": client_name,
                "project_type": project.project_type.value,
                "status": project.status.value,
                "progress_pct": project.progress_pct,
                "budget": budget,
                "studio_fee": fee,
                "expenses": expenses,
                "hours_logged": hours,
            }
        )
    summary = {
        "total_projects": len(detail),
        "active_projects": active_count,
        "total_budget": total_budget,
        "total_studio_fee": total_fee,
        "total_expenses": total_expenses,
        "total_hours": total_hours,
    }
    return {"title": "Projects Report", "summary": summary, "rows": detail}


async def finance_report(db: AsyncSession, period: str = "month") -> dict:
    start, end = _period_bounds(period)
    today = now_local().date()
    inv_stmt = (
        select(Invoice, Client.name)
        .outerjoin(Client, Client.id == Invoice.client_id)
        .where(
            Invoice.invoice_date >= start,
            Invoice.invoice_date < end,
            Invoice.status != InvoiceStatus.CANCELLED,
        )
        .order_by(Invoice.invoice_date)
    )
    invoices = (await db.execute(inv_stmt)).all()

    invoiced = Decimal("0")
    received = Decimal("0")
    detail: list[dict] = []
    for invoice, client_name in invoices:
        effective = _status_for(invoice, today)
        outstanding = _q(invoice.total - invoice.paid_amount)
        invoiced += invoice.total
        received += invoice.paid_amount
        detail.append(
            {
                "invoice_number": invoice.invoice_number,
                "client_name": client_name,
                "invoice_date": invoice.invoice_date,
                "due_date": invoice.due_date,
                "total": _q(invoice.total),
                "paid_amount": _q(invoice.paid_amount),
                "outstanding": outstanding,
                "status": effective.value,
            }
        )

    outstanding_total = _q(invoiced - received)
    aging = {
        "0_30": Decimal("0"),
        "31_60": Decimal("0"),
        "61_90": Decimal("0"),
        "90_plus": Decimal("0"),
    }
    aging_rows = (
        await db.execute(
            select(Invoice, Client.name)
            .outerjoin(Client, Client.id == Invoice.client_id)
            .where(Invoice.status != InvoiceStatus.CANCELLED)
        )
    ).all()
    for invoice, _ in aging_rows:
        balance = invoice.total - invoice.paid_amount
        if balance <= 0:
            continue
        days = (today - invoice.due_date).days
        if days <= 30:
            aging["0_30"] += balance
        elif days <= 60:
            aging["31_60"] += balance
        elif days <= 90:
            aging["61_90"] += balance
        else:
            aging["90_plus"] += balance

    exp_stmt = (
        select(Expense.category, func.sum(Expense.amount))
        .where(
            Expense.status == ExpenseStatus.APPROVED,
            Expense.expense_date >= start,
            Expense.expense_date < end,
        )
        .group_by(Expense.category)
    )
    expense_rows = [{"category": c, "amount": _q(a)} for c, a in (await db.execute(exp_stmt)).all()]
    expenses_total = sum((row["amount"] for row in expense_rows), Decimal("0"))

    summary = {
        "period": period,
        "from": start,
        "to": end,
        "invoiced": _q(invoiced),
        "received": _q(received),
        "outstanding": _q(outstanding_total),
        "expenses": _q(expenses_total),
        "profit": _q(received - expenses_total),
        "invoice_count": len(detail),
    }
    return {
        "title": "Finance Report",
        "summary": summary,
        "rows": detail,
        "expense_rows": expense_rows,
        "aging": aging,
    }


async def hr_report(db: AsyncSession, month: int, year: int) -> dict:
    dept_stmt = (
        select(Department.name, func.count(User.id))
        .join(User, User.department_id == Department.id)
        .where(User.is_active.is_(True))
        .group_by(Department.name)
        .order_by(Department.name)
    )
    headcount_dept = [
        {"department": name, "count": count} for name, count in (await db.execute(dept_stmt)).all()
    ]
    level_stmt = (
        select(OrgLevel.code, func.count(User.id))
        .join(OrgLevel, OrgLevel.id == User.org_level_id)
        .where(User.is_active.is_(True))
        .group_by(OrgLevel.code)
        .order_by(OrgLevel.code)
    )
    headcount_level = [
        {"level": code, "count": count} for code, count in (await db.execute(level_stmt)).all()
    ]

    users_stmt = (
        select(User, Department.name, OrgLevel)
        .outerjoin(Department, Department.id == User.department_id)
        .outerjoin(OrgLevel, OrgLevel.id == User.org_level_id)
        .where(User.is_active.is_(True))
        .order_by(User.name)
    )
    user_rows = (await db.execute(users_stmt)).all()

    present_statuses = (
        AttendanceStatus.PRESENT,
        AttendanceStatus.LATE,
        AttendanceStatus.HALF_DAY,
        AttendanceStatus.WORK_FROM_HOME,
    )

    # Batch-fetch all attendance records for the month (eliminates N+1)
    user_ids = [user.id for user, _, _ in user_rows]
    att_stmt = select(Attendance.user_id, Attendance.status).where(
        Attendance.user_id.in_(user_ids),
        Attendance.date >= date(year, month, 1),
        Attendance.date <= _month_end(year, month),
    )
    att_rows = (await db.execute(att_stmt)).all()
    att_by_user: dict[int, list] = {}
    for uid, status in att_rows:
        att_by_user.setdefault(uid, []).append(status)

    # Batch-fetch leave totals for all users (eliminates N+1)
    leave_stmt = (
        select(Leave.user_id, func.coalesce(func.sum(Leave.total_days), 0))
        .where(
            Leave.user_id.in_(user_ids),
            Leave.status == LeaveStatus.APPROVED,
            Leave.from_date >= date(year, 1, 1),
            Leave.from_date <= date(year, 12, 31),
        )
        .group_by(Leave.user_id)
    )
    leave_rows = (await db.execute(leave_stmt)).all()
    leave_map = {uid: total for uid, total in leave_rows}

    detail: list[dict] = []
    total_present = 0
    total_absent = 0
    for user, department_name, level in user_rows:
        statuses = att_by_user.get(user.id, [])
        present = sum(1 for s in statuses if s in present_statuses)
        absent = sum(1 for s in statuses if s == AttendanceStatus.ABSENT)
        marked = present + absent
        total_present += present
        total_absent += absent
        leaves_year = leave_map.get(user.id, 0)
        detail.append(
            {
                "employee_id": user.employee_id,
                "name": user.name,
                "department": department_name,
                "designation": user.designation,
                "org_level_code": level.code if level else None,
                "present_days": present,
                "absent_days": absent,
                "attendance_pct": round((present / marked * 100), 1) if marked else None,
                "leave_days_ytd": float(leaves_year),
            }
        )

    summary = {
        "month": month,
        "year": year,
        "total_employees": len(detail),
        "total_present_days": total_present,
        "total_absent_days": total_absent,
        "avg_attendance_pct": round(total_present / (total_present + total_absent) * 100, 1)
        if (total_present + total_absent)
        else None,
    }
    return {
        "title": "HR Report",
        "summary": summary,
        "rows": detail,
        "headcount_dept": headcount_dept,
        "headcount_level": headcount_level,
    }


async def timesheets_report(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
    employee_id: int | None = None,
) -> dict:
    """Hours logged per project × employee in a date range."""
    stmt = (
        select(
            Project.project_code,
            Project.name,
            User.employee_id,
            User.name,
            func.coalesce(func.sum(TimesheetEntry.hours), 0).label("total_hours"),
        )
        .select_from(TimesheetEntry)
        .join(Timesheet, Timesheet.id == TimesheetEntry.timesheet_id)
        .join(User, User.id == Timesheet.user_id)
        .outerjoin(Project, Project.id == TimesheetEntry.project_id)
        .where(TimesheetEntry.date >= from_date, TimesheetEntry.date <= to_date)
        .group_by(Project.project_code, Project.name, User.employee_id, User.name, User.id)
        .order_by(Project.name.nulls_last(), User.name)
    )
    if employee_id is not None:
        stmt = stmt.where(Timesheet.user_id == employee_id)
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    rows = (await db.execute(stmt)).all()

    detail: list[dict] = []
    total_hours = Decimal("0")
    employees: set[str] = set()
    projects: set[str] = set()
    for project_code, project_name, employee_id, employee_name, hours in rows:
        total_hours += Decimal(str(hours))
        if employee_id:
            employees.add(employee_id)
        projects.add(project_name or project_code or "Unassigned")
        detail.append(
            {
                "project_code": project_code,
                "project_name": project_name or "Unassigned",
                "employee_id": employee_id,
                "employee_name": employee_name,
                "hours": float(Decimal(str(hours)).normalize()),
            }
        )

    summary = {
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "total_hours": float(total_hours),
        "employees": len(employees),
        "projects": len(projects),
    }
    return {"title": "Timesheets Report", "summary": summary, "rows": detail}


def _period_key(entry_date: date, group_by: str) -> date:
    """Normalise a date to its day/week(Monday)/month bucket."""
    if group_by == "week":
        return entry_date - timedelta(days=entry_date.weekday())
    if group_by == "month":
        return entry_date.replace(day=1)
    return entry_date


def _period_label(period: date, group_by: str) -> str:
    if group_by == "week":
        end = period + timedelta(days=6)
        return f"Week of {period.strftime('%d %b')} – {end.strftime('%d %b %Y')}"
    if group_by == "month":
        return period.strftime("%B %Y")
    return period.strftime("%a %d %b %Y")


async def timesheets_detail(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
    employee_id: int | None = None,
    group_by: str = "day",
) -> dict:
    """Per-employee timesheet detail for a range, grouped by day/week/month.

    ``employees`` sections are designed for sectioned PDF export (one
    fresh page per employee; long employees flow across pages) and the
    frontend's per-employee cards. The flat ``rows`` aggregate from
    :func:`timesheets_report` is included unchanged so CSV/XLSX exports
    keep working.
    """
    stmt = (
        select(
            TimesheetEntry,
            User.id,
            User.name,
            User.employee_id,
            Department.name,
            Project.name,
        )
        .select_from(TimesheetEntry)
        .join(Timesheet, Timesheet.id == TimesheetEntry.timesheet_id)
        .join(User, User.id == Timesheet.user_id)
        .outerjoin(Department, Department.id == User.department_id)
        .outerjoin(Project, Project.id == TimesheetEntry.project_id)
        .where(TimesheetEntry.date >= from_date, TimesheetEntry.date <= to_date)
        .order_by(User.name, User.id, TimesheetEntry.date, TimesheetEntry.id)
    )
    if employee_id is not None:
        stmt = stmt.where(Timesheet.user_id == employee_id)
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    rows = (await db.execute(stmt)).all()

    order: list[int] = []
    people: dict[int, dict] = {}
    total_hours = Decimal("0")
    projects: set[str] = set()
    period_keys: set[date] = set()
    for entry, uid, name, emp_code, dept, project_name in rows:
        period = _period_key(entry.date, group_by)
        period_keys.add(period)
        person = people.get(uid)
        if person is None:
            person = people[uid] = {
                "user_id": uid,
                "employee_id": emp_code,
                "employee_name": name,
                "department": dept,
                "total_hours": Decimal("0"),
                "_groups": {},
                "_group_order": [],
            }
            order.append(uid)
        groups = person["_groups"]
        group = groups.get(period)
        if group is None:
            group = groups[period] = {
                "label": _period_label(period, group_by),
                "hours": Decimal("0"),
                "rows": [],
                "_projects": {},
            }
            person["_group_order"].append(period)

        hours = Decimal(str(entry.hours))
        total_hours += hours
        person["total_hours"] += hours
        group["hours"] += hours
        projects.add(project_name or "Unassigned")

        if group_by == "day":
            # Entry-level lines: every logged task is visible.
            group["rows"].append(
                {
                    "date": entry.date.isoformat(),
                    "project": project_name or "Unassigned",
                    "description": entry.description or "",
                    "hours": float(hours.normalize()),
                }
            )
        else:
            # Week/month views roll entries up per project within the period.
            key = project_name or "Unassigned"
            agg = group["_projects"].get(key)
            if agg is None:
                agg = group["_projects"][key] = {
                    "date": None,
                    "project": key,
                    "description": None,
                    "hours": Decimal("0"),
                }
                group["rows"].append(agg)
            agg["hours"] += hours

    employees_out = []
    for uid in order:
        person = people[uid]
        groups_out = []
        for period in sorted(person["_group_order"]):
            g = person["_groups"][period]
            rows_out = [
                {**r, "hours": float(r["hours"].normalize())}
                if isinstance(r["hours"], Decimal)
                else r
                for r in g["rows"]
            ]
            rows_out.sort(key=lambda r: (r.get("date") or "", r["project"]))
            groups_out.append(
                {
                    "label": g["label"],
                    "hours": float(g["hours"].normalize()),
                    "rows": rows_out,
                }
            )
        employees_out.append(
            {
                "user_id": uid,
                "employee_id": person["employee_id"],
                "employee_name": person["employee_name"],
                "department": person["department"],
                "total_hours": float(person["total_hours"].normalize()),
                "groups": groups_out,
            }
        )

    summary = {
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "group_by": group_by,
        "total_hours": float(total_hours),
        "employees": len(employees_out),
        "projects": len(projects),
        "periods": len(period_keys),
    }
    base = await timesheets_report(db, from_date, to_date, department_id, employee_id)
    return {
        "title": "Timesheet Report",
        "summary": summary,
        "rows": base["rows"],
        "employees": employees_out,
    }


async def timesheet_employee_options(
    db: AsyncSession,
    department_id: int | None = None,
) -> list[dict]:
    """Active employees for the timesheet report filter dropdowns.

    Deliberately unpaginated and permission-light (the report itself is
    already L2+): the generic /employees list is L3+ with a hard
    page-size cap, which left L2 viewers with an empty picker.
    """
    stmt = (
        select(User.id, User.name, User.employee_id)
        .where(User.is_active.is_(True))
        .order_by(User.name)
    )
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    rows = (await db.execute(stmt)).all()
    return [{"id": r.id, "name": r.name, "employee_id": r.employee_id} for r in rows]
