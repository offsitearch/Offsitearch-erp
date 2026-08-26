"""Reporting: attendance, project, finance, and HR reports."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

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


# ── Formatting helpers ──────────────────────────────────────────


def _summary_rows(summary: dict) -> list[list]:
    return [[str(key), value] for key, value in summary.items()]


def _title_row(title: str, num_cols: int) -> list[tuple[str, str | None]]:
    return [(title, "title")] + [("", None)] * (num_cols - 1)


def _subtitle_row(text: str, num_cols: int) -> list[tuple[str, str | None]]:
    return [(text, "subtitle")] + [("", None)] * (num_cols - 1)


def _section_row(text: str, num_cols: int) -> list[tuple[str, str | None]]:
    return [(text, "section")] + [("", None)] * (num_cols - 1)


def _kpi_rows(summary_items: list[tuple[str, str | int | float]], num_cols: int) -> list[list[tuple[str, str | None]]]:
    """Build 1-2 rows of KPI cards from (label, formatted_value) pairs."""
    rows: list[list[tuple[str, str | None]]] = []
    for label, value in summary_items:
        rows.append([(label, "summary_label"), (str(value), "summary_value")] + [("", None)] * (num_cols - 2))
    return rows


def _fmt_money(v: int | float | Decimal | None) -> str:
    if v is None:
        return "\u20b90.00"
    return f"\u20b9{float(v):,.2f}"


def _fmt_int(v: int | float | Decimal | None) -> str:
    if v is None:
        return "0"
    return f"{int(float(v)):,}"


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.1f}%"


def _to_xlsx(title: str, summary: dict, columns: list[str], rows: list[list]) -> bytes:
    """Legacy simple builder — still used for basic exports."""
    sheets: list[dict] = [
        {
            "name": "Summary",
            "columns": ["Metric", "Value"],
            "rows": _summary_rows(summary),
        },
        {"name": "Detail", "columns": columns, "rows": rows},
    ]
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


def _to_rich_csv(
    title: str,
    subtitle: str,
    summary_items: list[tuple[str, str]],
    columns: list[str],
    rows: list[list],
) -> str:
    """Attractive CSV with title, summary, and separator before data."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([title])
    writer.writerow([subtitle])
    writer.writerow([])
    for label, value in summary_items:
        writer.writerow([label, value])
    writer.writerow([])
    writer.writerow([])
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)
    return buffer.getvalue()


# ── Projects Report ─────────────────────────────────────────────


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


def projects_xlsx(report: dict, title: str = "Projects Report") -> bytes:
    """Professional XLSX for projects report."""
    today = now_local().date().isoformat()
    columns = [
        "Project Code", "Project Name", "Client", "Type", "Status",
        "Progress %", "Budget", "Studio Fee", "Expenses", "Hours Logged",
    ]
    col_formats = [None, None, None, None, None, "percent", "currency", "currency", "currency", "integer"]
    col_styles = ["text_border", "text_border", "text_border", "text_border", "text_border",
                  "percent_border", "currency_border", "currency_border", "currency_border", "integer_border"]
    alt_col_styles = ["text_alt", "text_alt", "text_alt", "text_alt", "text_alt",
                      "percent_alt", "currency_alt", "currency_alt", "currency_alt", "integer_alt"]

    rows = [
        [
            r["project_code"], r["name"], r["client_name"] or "—",
            r["project_type"], r["status"],
            float(r["progress_pct"] or 0) / 100 if r["progress_pct"] else 0,
            float(r["budget"]), float(r["studio_fee"]),
            float(r["expenses"]), r["hours_logged"],
        ]
        for r in report["rows"]
    ]

    s = report["summary"]
    total_profit = float(s["total_studio_fee"]) - float(s["total_expenses"])
    kpi_items = [
        ("Total Projects", _fmt_int(s["total_projects"])),
        ("Active Projects", _fmt_int(s["active_projects"])),
        ("Total Budget", _fmt_money(s["total_budget"])),
        ("Studio Fees", _fmt_money(s["total_studio_fee"])),
        ("Total Expenses", _fmt_money(s["total_expenses"])),
        ("Net Profit", _fmt_money(total_profit)),
        ("Total Hours", _fmt_int(s["total_hours"])),
    ]

    num_cols = len(columns)
    extra_before = [
        _title_row(title, num_cols),
        _subtitle_row(f"Generated: {today}", num_cols),
        [("", None)] * num_cols,
        _section_row("Key Metrics", num_cols),
    ]
    extra_before.extend(_kpi_rows(kpi_items, num_cols))
    extra_before.append([("", None)] * num_cols)
    extra_before.append(_section_row("Project Details", num_cols))

    # Total row
    total_row: list[tuple[str, str | None]] = [
        ("TOTAL", "subtotal"),
        ("", None), ("", None), ("", None), ("", None),
        (None, None),
        (_fmt_money(s["total_budget"]), "subtotal_currency"),
        (_fmt_money(s["total_studio_fee"]), "subtotal_currency"),
        (_fmt_money(s["total_expenses"]), "subtotal_currency"),
        (_fmt_int(s["total_hours"]), "subtotal"),
    ]

    return write_xlsx([{
        "name": "Projects",
        "columns": columns,
        "rows": rows,
        "col_styles": col_styles,
        "alt_col_styles": alt_col_styles,
        "col_formats": col_formats,
        "freeze_row": len(extra_before) + 1,
        "extra_rows_before": extra_before,
        "extra_rows_after": [total_row],
    }])


def projects_csv(report: dict) -> str:
    """Attractive CSV for projects report."""
    today = now_local().date().isoformat()
    s = report["summary"]
    total_profit = float(s["total_studio_fee"]) - float(s["total_expenses"])
    columns = [
        "Project Code", "Project Name", "Client", "Type", "Status",
        "Progress %", "Budget", "Studio Fee", "Expenses", "Hours Logged",
    ]
    rows = [
        [
            r["project_code"], r["name"], r["client_name"] or "—",
            r["project_type"], r["status"],
            f"{r['progress_pct'] or 0}%",
            f"\u20b9{float(r['budget']):,.2f}",
            f"\u20b9{float(r['studio_fee']):,.2f}",
            f"\u20b9{float(r['expenses']):,.2f}",
            r["hours_logged"],
        ]
        for r in report["rows"]
    ]
    return _to_rich_csv(
        title="Projects Report",
        subtitle=f"Generated: {today}",
        summary_items=[
            ("Total Projects", _fmt_int(s["total_projects"])),
            ("Active Projects", _fmt_int(s["active_projects"])),
            ("Total Budget", _fmt_money(s["total_budget"])),
            ("Studio Fees", _fmt_money(s["total_studio_fee"])),
            ("Total Expenses", _fmt_money(s["total_expenses"])),
            ("Net Profit", _fmt_money(total_profit)),
            ("Total Hours", _fmt_int(s["total_hours"])),
        ],
        columns=columns,
        rows=rows,
    )


# ── Finance Report ──────────────────────────────────────────────


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


def finance_xlsx(report: dict) -> bytes:
    """Professional XLSX for finance report with multiple sections."""
    today_str = now_local().date().isoformat()
    s = report["summary"]
    period_label = {"month": "Monthly", "quarter": "Quarterly", "year": "Annual", "all": "All-Time"}.get(s["period"], s["period"])

    # ── Sheet 1: Executive Summary ──────────────────────────────
    num_cols = 6
    kpi_items = [
        ("Invoiced", _fmt_money(s["invoiced"])),
        ("Received", _fmt_money(s["received"])),
        ("Outstanding", _fmt_money(s["outstanding"])),
        ("Expenses", _fmt_money(s["expenses"])),
        ("Net Profit", _fmt_money(s["profit"])),
        ("Invoice Count", _fmt_int(s["invoice_count"])),
    ]
    aging = report["aging"]
    aging_items = [
        ("0-30 Days", _fmt_money(aging["0_30"])),
        ("31-60 Days", _fmt_money(aging["31_60"])),
        ("61-90 Days", _fmt_money(aging["61_90"])),
        ("90+ Days", _fmt_money(aging["90_plus"])),
    ]
    expense_items = [(e["category"], _fmt_money(e["amount"])) for e in report.get("expense_rows", [])]

    extra_before: list[list[tuple[str, str | None]]] = [
        _title_row(f"{period_label} Finance Report", num_cols),
        _subtitle_row(f"Period: {s['from']} to {s['to']}  |  Generated: {today_str}", num_cols),
        [("", None)] * num_cols,
        _section_row("Revenue & Cash Flow", num_cols),
    ]
    extra_before.extend(_kpi_rows(kpi_items, num_cols))
    extra_before.append([("", None)] * num_cols)
    extra_before.append(_section_row("Accounts Receivable Aging", num_cols))
    extra_before.extend(_kpi_rows(aging_items, num_cols))
    if expense_items:
        extra_before.append([("", None)] * num_cols)
        extra_before.append(_section_row("Expenses by Category", num_cols))
        extra_before.extend(_kpi_rows(expense_items, num_cols))

    summary_sheet: dict = {
        "name": "Summary",
        "columns": ["", "", "", "", "", ""],
        "rows": [],
        "extra_rows_before": extra_before,
        "freeze_row": 0,
    }

    # ── Sheet 2: Invoice Detail ─────────────────────────────────
    inv_columns = ["Invoice #", "Client", "Invoice Date", "Due Date", "Total", "Paid", "Outstanding", "Status"]
    inv_col_styles = ["text_border", "text_border", "date_border", "date_border",
                      "currency_border", "currency_border", "currency_border", "text_border"]
    inv_alt_col_styles = ["text_alt", "text_alt", "date_alt", "date_alt",
                          "currency_alt", "currency_alt", "currency_alt", "text_alt"]

    inv_rows = [
        [
            r["invoice_number"], r["client_name"] or "—",
            str(r["invoice_date"]), str(r["due_date"]),
            float(r["total"]), float(r["paid_amount"]),
            float(r["outstanding"]), r["status"],
        ]
        for r in report["rows"]
    ]

    inv_total_row: list[tuple[str, str | None]] = [
        ("TOTAL", "subtotal"),
        ("", None), ("", None), ("", None),
        (_fmt_money(s["invoiced"]), "subtotal_currency"),
        (_fmt_money(s["received"]), "subtotal_currency"),
        (_fmt_money(s["outstanding"]), "subtotal_currency"),
        ("", None),
    ]

    invoice_sheet: dict = {
        "name": "Invoices",
        "columns": inv_columns,
        "rows": inv_rows,
        "col_styles": inv_col_styles,
        "alt_col_styles": inv_alt_col_styles,
        "freeze_row": 1,
        "extra_rows_after": [inv_total_row],
    }

    sheets: list[dict] = [summary_sheet, invoice_sheet]

    # ── Sheet 3: Expense Breakdown (if present) ─────────────────
    if report.get("expense_rows"):
        exp_columns = ["Category", "Amount"]
        exp_rows = [[e["category"], float(e["amount"])] for e in report["expense_rows"]]
        sheets.append({
            "name": "Expenses",
            "columns": exp_columns,
            "rows": exp_rows,
            "col_styles": ["text_border", "currency_border"],
            "alt_col_styles": ["text_alt", "currency_alt"],
            "freeze_row": 1,
        })

    return write_xlsx(sheets)


def finance_csv(report: dict) -> str:
    """Attractive CSV for finance report."""
    s = report["summary"]
    aging = report["aging"]
    period_label = {"month": "Monthly", "quarter": "Quarterly", "year": "Annual", "all": "All-Time"}.get(s["period"], s["period"])

    columns = ["Invoice #", "Client", "Invoice Date", "Due Date", "Total", "Paid", "Outstanding", "Status"]
    rows = [
        [
            r["invoice_number"], r["client_name"] or "—",
            str(r["invoice_date"]), str(r["due_date"]),
            f"\u20b9{float(r['total']):,.2f}", f"\u20b9{float(r['paid_amount']):,.2f}",
            f"\u20b9{float(r['outstanding']):,.2f}", r["status"],
        ]
        for r in report["rows"]
    ]

    summary_items = [
        ("Period", f"{s['from']} to {s['to']}"),
        ("Invoiced", _fmt_money(s["invoiced"])),
        ("Received", _fmt_money(s["received"])),
        ("Outstanding", _fmt_money(s["outstanding"])),
        ("Expenses", _fmt_money(s["expenses"])),
        ("Net Profit", _fmt_money(s["profit"])),
        ("", ""),
        ("AGING: 0-30 Days", _fmt_money(aging["0_30"])),
        ("AGING: 31-60 Days", _fmt_money(aging["31_60"])),
        ("AGING: 61-90 Days", _fmt_money(aging["61_90"])),
        ("AGING: 90+ Days", _fmt_money(aging["90_plus"])),
    ]
    for e in report.get("expense_rows", []):
        summary_items.append((f"EXPENSE: {e['category']}", _fmt_money(e["amount"])))

    return _to_rich_csv(
        title=f"{period_label} Finance Report",
        subtitle=f"Generated: {now_local().date().isoformat()}",
        summary_items=summary_items,
        columns=columns,
        rows=rows,
    )


# ── HR Report ───────────────────────────────────────────────────


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


def hr_xlsx(report: dict) -> bytes:
    """Professional XLSX for HR report with summary, headcount, and detail."""
    today_str = now_local().date().isoformat()
    s = report["summary"]
    month_name = date(s["year"], s["month"], 1).strftime("%B %Y")

    # ── Sheet 1: Executive Summary ──────────────────────────────
    num_cols = 6
    kpi_items = [
        ("Total Employees", _fmt_int(s["total_employees"])),
        ("Present Days", _fmt_int(s["total_present_days"])),
        ("Absent Days", _fmt_int(s["total_absent_days"])),
        ("Avg Attendance", _fmt_pct(s["avg_attendance_pct"])),
    ]

    dept_items = [(d["department"], str(d["count"])) for d in report.get("headcount_dept", [])]
    level_items = [(lv["level"], str(lv["count"])) for lv in report.get("headcount_level", [])]

    extra_before: list[list[tuple[str, str | None]]] = [
        _title_row("HR Report", num_cols),
        _subtitle_row(f"{month_name}  |  Generated: {today_str}", num_cols),
        [("", None)] * num_cols,
        _section_row("Workforce Overview", num_cols),
    ]
    extra_before.extend(_kpi_rows(kpi_items, num_cols))
    if dept_items:
        extra_before.append([("", None)] * num_cols)
        extra_before.append(_section_row("Headcount by Department", num_cols))
        extra_before.extend(_kpi_rows(dept_items, num_cols))
    if level_items:
        extra_before.append([("", None)] * num_cols)
        extra_before.append(_section_row("Headcount by Level", num_cols))
        extra_before.extend(_kpi_rows(level_items, num_cols))

    summary_sheet: dict = {
        "name": "Summary",
        "columns": ["", "", "", "", "", ""],
        "rows": [],
        "extra_rows_before": extra_before,
        "freeze_row": 0,
    }

    # ── Sheet 2: Employee Detail ────────────────────────────────
    detail_columns = [
        "Employee ID", "Name", "Department", "Designation", "Level",
        "Present Days", "Absent Days", "Attendance %", "Leaves (YTD)",
    ]
    detail_col_styles = [
        "text_border", "text_border", "text_border", "text_border", "text_border",
        "integer_border", "integer_border", "percent_border", "decimal1_border",
    ]
    detail_alt_col_styles = [
        "text_alt", "text_alt", "text_alt", "text_alt", "text_alt",
        "integer_alt", "integer_alt", "percent_alt", "decimal1_alt",
    ]

    detail_rows = [
        [
            r["employee_id"], r["name"], r["department"] or "—",
            r["designation"] or "—", r["org_level_code"] or "—",
            r["present_days"], r["absent_days"],
            float(r["attendance_pct"] or 0) / 100 if r["attendance_pct"] is not None else None,
            float(r["leave_days_ytd"]),
        ]
        for r in report["rows"]
    ]

    total_present = sum(r["present_days"] for r in report["rows"])
    total_absent = sum(r["absent_days"] for r in report["rows"])
    total_leaves = sum(r["leave_days_ytd"] for r in report["rows"])
    avg_att = round(total_present / (total_present + total_absent) * 100, 1) if (total_present + total_absent) else 0

    total_row: list[tuple[str, str | None]] = [
        ("TOTAL", "subtotal"),
        ("", None), ("", None), ("", None), ("", None),
        (str(total_present), "subtotal"),
        (str(total_absent), "subtotal"),
        (f"{avg_att:.1f}%", "subtotal"),
        (f"{total_leaves:.1f}", "subtotal"),
    ]

    detail_sheet: dict = {
        "name": "Employee Detail",
        "columns": detail_columns,
        "rows": detail_rows,
        "col_styles": detail_col_styles,
        "alt_col_styles": detail_alt_col_styles,
        "freeze_row": 1,
        "extra_rows_after": [total_row],
    }

    return write_xlsx([summary_sheet, detail_sheet])


def hr_csv(report: dict) -> str:
    """Attractive CSV for HR report."""
    today_str = now_local().date().isoformat()
    s = report["summary"]
    month_name = date(s["year"], s["month"], 1).strftime("%B %Y")

    columns = [
        "Employee ID", "Name", "Department", "Designation", "Level",
        "Present Days", "Absent Days", "Attendance %", "Leaves (YTD)",
    ]
    rows = [
        [
            r["employee_id"], r["name"], r["department"] or "—",
            r["designation"] or "—", r["org_level_code"] or "—",
            r["present_days"], r["absent_days"],
            f"{r['attendance_pct']}%" if r["attendance_pct"] is not None else "N/A",
            f"{r['leave_days_ytd']:.1f}",
        ]
        for r in report["rows"]
    ]

    summary_items = [
        ("Month", month_name),
        ("Total Employees", _fmt_int(s["total_employees"])),
        ("Total Present Days", _fmt_int(s["total_present_days"])),
        ("Total Absent Days", _fmt_int(s["total_absent_days"])),
        ("Avg Attendance", _fmt_pct(s["avg_attendance_pct"])),
    ]
    for d in report.get("headcount_dept", []):
        summary_items.append((f"DEPT: {d['department']}", str(d["count"])))

    return _to_rich_csv(
        title="HR Report",
        subtitle=f"{month_name}  |  Generated: {today_str}",
        summary_items=summary_items,
        columns=columns,
        rows=rows,
    )


# ── Timesheets Report ───────────────────────────────────────────


async def timesheets_report(
    db: AsyncSession,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
    employee_id: int | None = None,
) -> dict:
    """Hours logged per project x employee in a date range."""
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
    for project_code, project_name, emp_id, employee_name, hours in rows:
        total_hours += Decimal(str(hours))
        if emp_id:
            employees.add(emp_id)
        projects.add(project_name or project_code or "Unassigned")
        detail.append(
            {
                "project_code": project_code,
                "project_name": project_name or "Unassigned",
                "employee_id": emp_id,
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
    if group_by == "week":
        return entry_date - timedelta(days=entry_date.weekday())
    if group_by == "month":
        return entry_date.replace(day=1)
    return entry_date


def _period_label(period: date, group_by: str) -> str:
    if group_by == "week":
        end = period + timedelta(days=6)
        return f"Week of {period.strftime('%d %b')} - {end.strftime('%d %b %Y')}"
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
            group["rows"].append(
                {
                    "date": entry.date.isoformat(),
                    "project": project_name or "Unassigned",
                    "description": entry.description or "",
                    "location": entry.location or "",
                    "hours": float(hours.normalize()),
                }
            )
        else:
            key = project_name or "Unassigned"
            agg = group["_projects"].get(key)
            if agg is None:
                agg = group["_projects"][key] = {
                    "date": None,
                    "project": key,
                    "description": None,
                    "location": None,
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

    approvers: dict[int, str] = {}
    if employees_out:
        emp_ids = [e["user_id"] for e in employees_out]
        approver_alias = aliased(User)
        approver_rows = (
            await db.execute(
                select(Timesheet.user_id, approver_alias.name, Timesheet.approved_at)
                .select_from(Timesheet)
                .join(approver_alias, approver_alias.id == Timesheet.approved_by)
                .where(
                    Timesheet.user_id.in_(emp_ids),
                    Timesheet.approved_by.isnot(None),
                    Timesheet.approved_at.isnot(None),
                )
                .order_by(Timesheet.approved_at.desc())
            )
        ).all()
        for uid, name, _ in approver_rows:
            approvers.setdefault(uid, name)
    for emp in employees_out:
        emp["approved_by_name"] = approvers.get(emp["user_id"], "")

    if employees_out:
        emp_ids = [e["user_id"] for e in employees_out]
        leave_stmt = (
            select(
                Leave.user_id,
                Leave.from_date,
                Leave.to_date,
                Leave.half_day_first,
                Leave.half_day_second,
            )
            .where(
                Leave.status == LeaveStatus.APPROVED,
                Leave.from_date <= to_date,
                Leave.to_date >= from_date,
                Leave.user_id.in_(emp_ids),
            )
        )
        leave_rows = (await db.execute(leave_stmt)).all()

        leave_map: dict[int, list[tuple[date, date, bool, bool]]] = {}
        for uid, lf, lt, hdf, hds in leave_rows:
            leave_map.setdefault(uid, []).append((lf, lt, hdf, hds))

        hours_by_emp: dict[int, dict[date, float]] = {}
        for emp in employees_out:
            hours_by_emp[emp["user_id"]] = {}
        for emp in people.values():
            uid = emp["user_id"]
            for period_key, grp in emp["_groups"].items():
                for r in grp["rows"]:
                    if r.get("date"):
                        d = date.fromisoformat(r["date"])
                        hours_by_emp.setdefault(uid, {})
                        hours_by_emp[uid][d] = hours_by_emp[uid].get(d, 0.0) + float(r["hours"])

        for emp in employees_out:
            uid = emp["user_id"]
            cal_days = []
            d = from_date
            while d <= to_date:
                is_weekend = d.weekday() >= 5
                day_hours = hours_by_emp.get(uid, {}).get(d, 0.0)
                day_label = d.strftime("%a")

                status = "absent"
                if is_weekend:
                    status = "weekend_work" if day_hours > 0 else "weekend_off"
                else:
                    if day_hours > 0:
                        status = "present"
                    else:
                        for lf, lt, hdf, hds in leave_map.get(uid, []):
                            if lf <= d <= lt:
                                if hdf and d == lf:
                                    status = "half_day_leave"
                                elif hds and d == lt:
                                    status = "half_day_leave"
                                else:
                                    status = "leave"
                                break

                cal_days.append({
                    "date": d.isoformat(),
                    "day": day_label,
                    "hours": round(day_hours, 2),
                    "status": status,
                })
                d += timedelta(days=1)

            emp["calendar"] = cal_days

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
    stmt = (
        select(User.id, User.name, User.employee_id)
        .where(User.is_active.is_(True))
        .order_by(User.name)
    )
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    rows = (await db.execute(stmt)).all()
    return [{"id": r.id, "name": r.name, "employee_id": r.employee_id} for r in rows]
