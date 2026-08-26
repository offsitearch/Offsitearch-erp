"""Dashboard aggregation routes.

Endpoints: /dashboard — summary stats (projects, tasks, attendance, invoices). Authenticated users; admins see org-wide data.
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Attendance, Invoice, Project, Task, User
from app.modules.projects import service as project_service
from app.utils.shared import has_financial_access, is_staff_band, now_local
from app.utils.enums import (
    InvoiceStatus,
    ProjectStatus,
    TaskStatus,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_ACTIVE_PROJECT_STATUSES = (
    ProjectStatus.DRAFT,
    ProjectStatus.CONCEPT,
    ProjectStatus.DESIGN,
    ProjectStatus.UNDER_REVIEW,
    ProjectStatus.IN_CONSTRUCTION,
)
_OPEN_TASK_STATUSES = (
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.REVIEW,
    TaskStatus.BLOCKED,
)


@router.get("/summary")
async def summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    staff_filter = [User.is_active.is_(True)]

    scope_user_id = current_user.id if is_staff_band(current_user) else None

    present_today_task = db.scalar(
        select(func.count())
        .select_from(Attendance)
        .join(User, User.id == Attendance.user_id)
        .where(
            *staff_filter,
            Attendance.date == now_local().date(),
            Attendance.check_in_time.isnot(None),
        )
    )
    active_projects_stmt = select(func.count(Project.id)).where(
        Project.is_active.is_(True),
        Project.status.in_(_ACTIVE_PROJECT_STATUSES),
    )
    if scope_user_id is not None:
        active_projects_stmt = active_projects_stmt.where(
            project_service.scope_condition(scope_user_id)
        )
    active_projects_task = db.scalar(active_projects_stmt)

    pending_tasks_stmt = select(func.count(Task.id)).where(
        Task.is_active.is_(True),
        Task.status.in_(_OPEN_TASK_STATUSES),
    )
    if scope_user_id is not None:
        pending_tasks_stmt = pending_tasks_stmt.where(Task.assigned_to == scope_user_id)
    pending_tasks_task = db.scalar(pending_tasks_stmt)

    revenue_task = None
    if has_financial_access(current_user):
        month_start = now_local().date().replace(day=1)
        revenue_task = db.scalar(
            select(func.coalesce(func.sum(Invoice.paid_amount), 0)).where(
                Invoice.invoice_date >= month_start,
                Invoice.status != InvoiceStatus.CANCELLED,
            )
        )

    total_employees = await db.scalar(select(func.count()).select_from(User).where(*staff_filter))

    tasks = [present_today_task, active_projects_task, pending_tasks_task]
    if revenue_task is not None:
        tasks.append(revenue_task)
    results = await asyncio.gather(*tasks)

    present_today = results[0]
    active_projects = results[1]
    pending_tasks = results[2]
    revenue_this_month = results[3] if revenue_task is not None else None

    return {
        "total_employees": total_employees or 0,
        "present_today": present_today or 0,
        "active_projects": active_projects or 0,
        "revenue_this_month": revenue_this_month,
        "pending_tasks": pending_tasks or 0,
    }
