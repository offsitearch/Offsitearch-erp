"""Report generation routes.

Endpoints: /reports — attendance, expense, project, timesheet, and
finance reports with JSON/CSV/XLSX export. The projects and finance
reports contain financial data and are executive-only (L0/L1) via
require_financial_access — see docs/architecture/financial_access_policy.md.
The HR and timesheets reports carry no financial columns and remain L2.
"""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_financial_access, require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.reports import service as reports_service
from app.utils.pdf import timesheet_report_pdf
from app.utils.shared import now_local
from app.utils.xlsx import write_xlsx

router = APIRouter(prefix="/reports", tags=["reports"])

_FORMAT_PATTERN = "^(json|csv|xlsx)$"


def _export_response(
    title: str, summary: dict, columns: list[str], rows: list[list], format: str
) -> Response:
    if format == "csv":
        content = reports_service._to_csv(columns, rows)
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{title.replace(" ", "_").lower()}.csv"'
            },
        )
    content = reports_service._to_xlsx(title, summary, columns, rows)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{title.replace(" ", "_").lower()}.xlsx"'
        },
    )


@router.get("/projects")
async def projects_report(
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(default=None),
    project_type: str | None = Query(default=None),
    format: str = Query(default="json", pattern=_FORMAT_PATTERN),
):
    report = await reports_service.projects_report(db, status, project_type)
    columns = [
        "project_code",
        "name",
        "client_name",
        "project_type",
        "status",
        "progress_pct",
        "budget",
        "studio_fee",
        "expenses",
        "hours_logged",
    ]
    rows = [[row[c] for c in columns] for row in report["rows"]]
    if format != "json":
        return _export_response(report["title"], report["summary"], columns, rows, format)
    return report


@router.get("/finance")
async def finance_report(
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: str = Query(default="month", pattern="^(month|quarter|year|all)$"),
    format: str = Query(default="json", pattern=_FORMAT_PATTERN),
):
    report = await reports_service.finance_report(db, period)
    columns = [
        "invoice_number",
        "client_name",
        "invoice_date",
        "due_date",
        "total",
        "paid_amount",
        "outstanding",
        "status",
    ]
    rows = [[row[c] for c in columns] for row in report["rows"]]
    if format != "json":
        return _export_response(report["title"], report["summary"], columns, rows, format)
    return report


@router.get("/timesheets/options")
async def timesheet_employee_options(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    department_id: int | None = None,
):
    """Active employees for the timesheet report filters (L2+)."""
    return await reports_service.timesheet_employee_options(db, department_id)


@router.get("/timesheets")
async def timesheets_report(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: date = Query(default_factory=lambda: now_local().date() - timedelta(days=29)),
    to_date: date = Query(default_factory=lambda: now_local().date()),
    department_id: int | None = None,
    employee_id: int | None = None,
    group_by: str = Query(default="day", pattern="^(day|week|month)$"),
    format: str = Query(default="json", pattern="^(json|csv|xlsx|pdf)$"),
):
    """Per-employee timesheet report (L2+).

    ``group_by`` picks the detail granularity — day lists every entry,
    week/month roll entries up per project within the period.
    ``department_id`` / ``employee_id`` narrow the scope. ``format=pdf``
    renders one section per employee (each starting on a fresh page,
    flowing across pages when long); xlsx adds a Detail sheet; csv
    stays the flat project × employee aggregate.
    """
    if to_date < from_date:
        from_date, to_date = to_date, from_date
    report = await reports_service.timesheets_detail(
        db, from_date, to_date, department_id, employee_id, group_by
    )
    columns = [
        "project_code",
        "project_name",
        "employee_id",
        "employee_name",
        "hours",
    ]
    rows = [[row[c] for c in columns] for row in report["rows"]]

    if format == "pdf":
        filters_bits = [f"{from_date.isoformat()} → {to_date.isoformat()}"]
        filters_bits.append(f"grouped by {group_by}")
        if department_id is not None:
            dept_name = next(
                (emp["department"] for emp in report["employees"] if emp["department"]),
                None,
            )
            filters_bits.append(
                f"department #{department_id}" + (f" · {dept_name}" if dept_name else "")
            )
        if employee_id is not None:
            filters_bits.append("single employee")
        content = timesheet_report_pdf(
            title=report["title"],
            filters_line=" · ".join(filters_bits),
            employees=[
                {
                    **emp,
                    "total_hours": f"{emp['total_hours']:g}",
                    "groups": [{**g, "hours": f"{g['hours']:g}"} for g in emp["groups"]],
                }
                for emp in report["employees"]
            ],
        )
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="timesheet_report_'
                    f"{from_date.isoformat()}_"
                    f'{to_date.isoformat()}.pdf"'
                )
            },
        )

    if format == "xlsx":
        detail_columns = ["Employee", "Period", "Date", "Project", "Description", "Hours"]
        detail_rows = []
        for emp in report["employees"]:
            for group in emp["groups"]:
                for r in group["rows"]:
                    detail_rows.append(
                        [
                            emp["employee_name"],
                            group["label"],
                            r.get("date") or "",
                            r["project"],
                            r.get("description") or "",
                            float(r["hours"]),
                        ]
                    )
        content = write_xlsx(
            [
                {
                    "name": "Summary",
                    "columns": columns,
                    "rows": rows,
                },
                {"name": "Detail", "columns": detail_columns, "rows": detail_rows},
            ]
        )
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="timesheet_report.xlsx"'},
        )

    if format == "csv":
        return _export_response(report["title"], report["summary"], columns, rows, format)
    return report


@router.get("/hr")
async def hr_report(
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    month: int = Query(default_factory=lambda: now_local().date().month, ge=1, le=12),
    year: int = Query(default_factory=lambda: now_local().date().year, ge=2000, le=2100),
    format: str = Query(default="json", pattern=_FORMAT_PATTERN),
):
    report = await reports_service.hr_report(db, month, year)
    columns = [
        "employee_id",
        "name",
        "department",
        "designation",
        "org_level_code",
        "present_days",
        "absent_days",
        "attendance_pct",
        "leave_days_ytd",
    ]
    rows = [[row[c] for c in columns] for row in report["rows"]]
    if format != "json":
        return _export_response(report["title"], report["summary"], columns, rows, format)
    return report
