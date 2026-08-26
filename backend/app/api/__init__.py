from fastapi import APIRouter

from app.api.routes import (
    rate_limit,
    system,
)

# Modular monolith routers (mounted from modules/<name>/routes.py)
from app.modules.attendance.routes import router as attendance_router
from app.modules.audit.routes import router as audit_router
from app.modules.backup.routes import router as backup_router
from app.modules.clients.routes import router as clients_router
from app.modules.dashboard.routes import router as dashboard_router
from app.modules.employees.routes import router as employees_router
from app.modules.finance.routes import (
    expenses_router,
    finance_router,
    invoices_router,
)
from app.modules.holidays.routes import router as holidays_router
from app.modules.identity.routes import auth_router, users_router
from app.modules.leave.routes import router as leave_router
from app.modules.meetings.routes import router as meetings_router
from app.modules.notifications.routes import router as notifications_router
from app.modules.notices.routes import router as notices_router
from app.modules.orgstructure.routes import departments_router, org_levels_router
from app.modules.payroll.routes import router as payroll_router
from app.modules.projects.routes import router as projects_router
from app.modules.reports.routes import router as reports_router
from app.modules.settings.routes import router as settings_router
from app.modules.site_visits.routes import router as site_visits_router
from app.modules.tasks.routes import router as tasks_router
from app.modules.timesheets.routes import router as timesheets_router

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(dashboard_router)
api_router.include_router(attendance_router)
api_router.include_router(leave_router)
api_router.include_router(employees_router)
api_router.include_router(departments_router)
api_router.include_router(org_levels_router)
api_router.include_router(projects_router)
api_router.include_router(clients_router)
api_router.include_router(tasks_router)
api_router.include_router(finance_router)
api_router.include_router(invoices_router)
api_router.include_router(expenses_router)
api_router.include_router(payroll_router)
api_router.include_router(settings_router)
api_router.include_router(holidays_router)
api_router.include_router(notices_router)
api_router.include_router(meetings_router)
api_router.include_router(notifications_router)
api_router.include_router(site_visits_router)
api_router.include_router(timesheets_router)
api_router.include_router(audit_router)
api_router.include_router(reports_router)
api_router.include_router(backup_router)
api_router.include_router(rate_limit.router)
