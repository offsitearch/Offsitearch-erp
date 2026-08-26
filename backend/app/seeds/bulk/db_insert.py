"""Async DB insertion script for the Offsite ERP.

Reads generated data from ``app.seeds.bulk`` and inserts everything
into the local Docker PostgreSQL database.

Usage::

    python -m app.seeds.bulk.db_insert
    python -m app.seeds.bulk.db_insert --url postgresql+asyncpg://user:pass@host:5432/dbname

The script is idempotent — it skips entities whose unique key already
exists in the database.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
_backend = Path(__file__).resolve().parents[2]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from app.core.security import format_login_id, generate_email, generate_numeric_password, hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Attendance,
    Client,
    Department,
    Expense,
    Invoice,
    InvoiceItem,
    Leave,
    Meeting,
    MeetingAttendee,
    Notice,
    OrgLevel,
    Project,
    SalaryComponent,
    SiteVisit,
    Task,
    Timesheet,
    TimesheetDay,
    TimesheetEntry,
    User,
)
from app.utils.enums import (  # noqa: E402
    AttendanceStatus,
    ExpenseCategory,
    ExpenseStatus,
    InvoiceStatus,
    LeaveStatus,
    LeaveType,
    NoticeImportance,
    RsvpStatus,
    SiteVisitStatus,
    TaskPriority,
    TaskStatus,
    TimesheetStatus,
)
from app.seeds.bulk import generate_all  # noqa: E402


DEFAULT_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/offsite_erp"


# ── Helpers ─────────────────────────────────────────────────────────────

async def _load_ref_data(db: AsyncSession) -> dict:
    """Load departments, org levels, existing users, projects, clients."""
    depts = {}
    for row in (await db.execute(select(Department))).scalars().all():
        depts[row.name] = row.id

    levels = {}
    for row in (await db.execute(select(OrgLevel))).scalars().all():
        levels[row.code] = row.id

    users_by_email = {}
    users_by_name = {}
    for row in (await db.execute(select(User))).scalars().all():
        users_by_email[row.email] = row.id
        users_by_name[row.name] = row.id

    projects = {}
    for row in (await db.execute(select(Project))).scalars().all():
        projects[row.name] = row.id

    clients = {}
    for row in (await db.execute(select(Client))).scalars().all():
        clients[row.name] = row.id

    return {
        "depts": depts,
        "levels": levels,
        "users_by_email": users_by_email,
        "users_by_name": users_by_name,
        "projects": projects,
        "clients": clients,
    }


async def _insert_clients(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for c in data:
        if c["name"] in ref["clients"]:
            continue
        client = Client(
            name=c["name"],
            client_type=c.get("client_type", "individual"),
            company_name=c.get("company_name"),
            contact_person=c.get("contact_person"),
            phone=c.get("phone"),
            email=c.get("email"),
            source=c.get("source"),
            budget_range=c.get("budget_range"),
            interest=c.get("interest"),
        )
        db.add(client)
        await db.flush()
        ref["clients"][c["name"]] = client.id
        count += 1
    return count


async def _insert_projects(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for p in data:
        if p["name"] in ref["projects"]:
            continue
        client_idx = p.get("client_idx")
        client_names = list(ref["clients"].keys())
        client_id = ref["clients"].get(client_names[client_idx]) if client_idx is not None and client_idx < len(client_names) else None
        proj = Project(
            project_code=p["project_code"],
            name=p["name"],
            project_type=p["project_type"],
            category=p.get("category"),
            client_id=client_id,
            location=p.get("location"),
            plot_area=p.get("plot_area"),
            built_up_area=p.get("built_up_area"),
            no_of_floors=p.get("no_of_floors"),
            budget=p.get("budget"),
            studio_fee=p.get("studio_fee"),
            fee_type=p.get("fee_type"),
            fee_percent=p.get("fee_percent"),
            start_date=p.get("start_date"),
            end_date=p.get("end_date"),
            status=p["status"],
            priority=p.get("priority", "medium"),
        )
        db.add(proj)
        await db.flush()
        ref["projects"][p["name"]] = proj.id
        count += 1
    return count


async def _insert_employees(db: AsyncSession, data: list[dict], ref: dict) -> int:
    """Insert users. Resolves department, org level, reporting_to by name."""
    # CEO email for reporting resolution
    ceo_id = ref["users_by_name"].get("Admin User") or ref["users_by_name"].get("CEO")

    # Collect all existing login_ids from DB
    existing_login_ids = set()
    for row in (await db.execute(select(User.login_id))).scalars().all():
        existing_login_ids.add(row)

    count = 0
    cohort_seq: dict[int, int] = {}

    for emp in data:
        email = generate_email(emp["name"], emp["date_of_joining"])
        if email in ref["users_by_email"]:
            continue

        dept_id = ref["depts"].get(emp["department"])
        level_id = ref["levels"].get(emp["level"])

        joining = emp["date_of_joining"]
        year = joining.year
        while True:
            seq = cohort_seq.get(year, 0) + 1
            cohort_seq[year] = seq
            login_id = format_login_id(year, seq)
            if login_id not in existing_login_ids:
                existing_login_ids.add(login_id)
                break

        user = User(
            email=email,
            login_id=login_id,
            name=emp["name"],
            designation=emp["designation"],
            phone=emp["phone"],
            gender=emp["gender"],
            date_of_joining=emp["date_of_joining"],
            skills=emp["skills"],
            employee_id=emp.get("employee_id"),
            department_id=dept_id,
            org_level_id=level_id,
            password_hash=hash_password(generate_numeric_password()),
        )
        db.add(user)
        await db.flush()

        ref["users_by_email"][email] = user.id
        ref["users_by_name"][emp["name"]] = user.id
        count += 1

    # Now resolve reporting_to
    for emp in data:
        user_id = ref["users_by_name"].get(emp["name"])
        if not user_id:
            continue
        target_name = emp.get("reporting_to_name")
        if target_name == "_CEO_":
            manager_id = ceo_id
        elif target_name:
            manager_id = ref["users_by_name"].get(target_name)
        else:
            manager_id = None
        if manager_id:
            user = await db.get(User, user_id)
            if user and not user.reporting_to_id:
                user.reporting_to_id = manager_id

    return count


async def _insert_salary_components(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for sc in data:
        user_id = ref["users_by_name"].get(sc["employee_name"])
        if not user_id:
            continue
        exists = await db.execute(
            select(SalaryComponent).where(SalaryComponent.user_id == user_id)
        )
        if exists.scalar_one_or_none():
            continue
        db.add(SalaryComponent(
            user_id=user_id,
            ctc_annual=sc["ctc_annual"],
            basic=sc["basic"],
            hra=sc["hra"],
            special_allowance=sc["special_allowance"],
            pf_deduction=sc["pf_deduction"],
            bank_name=sc["bank_name"],
            account_number=sc["account_number"],
            ifsc_code=sc["ifsc_code"],
            effective_from=sc["effective_from"],
        ))
        count += 1
    return count


async def _insert_tasks(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for t in data:
        exists = await db.execute(select(Task).where(Task.title == t["title"]))
        if exists.scalar_one_or_none():
            continue
        db.add(Task(
            title=t["title"],
            description=t.get("description"),
            project_id=ref["projects"].get(t["project_name"]),
            assigned_to=ref["users_by_name"].get(t["assigned_to_name"]),
            assigned_by=ref["users_by_name"].get(t["assigned_by_name"]),
            priority=TaskPriority(t["priority"].lower()),
            status=TaskStatus(t["status"].lower()),
            start_date=t.get("start_date"),
            due_date=t.get("due_date"),
            estimated_hours=t.get("estimated_hours"),
            actual_hours=t.get("actual_hours"),
            tags=t.get("tags"),
        ))
        count += 1
    return count


async def _insert_expenses(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for e in data:
        exists = await db.execute(
            select(Expense).where(Expense.description == e["description"], Expense.amount == e["amount"])
        )
        if exists.scalar_one_or_none():
            continue
        db.add(Expense(
            category=ExpenseCategory(e["category"].lower()),
            description=e["description"],
            amount=e["amount"],
            expense_date=e["expense_date"],
            project_id=ref["projects"].get(e["project_name"]) if e.get("project_name") else None,
            paid_by=e["paid_by_name"],
            status=ExpenseStatus(e["status"].lower()),
        ))
        count += 1
    return count


async def _insert_invoices(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for inv in data:
        exists = await db.execute(
            select(Invoice).where(Invoice.invoice_number == inv["invoice_number"])
        )
        if exists.scalar_one_or_none():
            continue
        invoice = Invoice(
            invoice_number=inv["invoice_number"],
            client_id=ref["clients"].get(inv["client_name"]),
            project_id=ref["projects"].get(inv["project_name"]),
            invoice_date=inv["invoice_date"],
            due_date=inv["due_date"],
            subtotal=inv["subtotal"],
            tax_percent=inv["tax_percent"],
            tax_amount=inv["tax_amount"],
            total=inv["total"],
            status=InvoiceStatus(inv["status"].lower()),
            paid_amount=inv.get("paid_amount", Decimal("0")),
            payment_date=inv.get("payment_date"),
        )
        db.add(invoice)
        await db.flush()
        for item in inv["items"]:
            db.add(InvoiceItem(
                invoice_id=invoice.id,
                description=item["description"],
                quantity=item["quantity"],
                rate=item["rate"],
                amount=item["quantity"] * item["rate"],
            ))
        count += 1
    return count


async def _insert_meetings(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for m in data:
        exists = await db.execute(select(Meeting).where(Meeting.title == m["title"]))
        if exists.scalar_one_or_none():
            continue
        meeting = Meeting(
            title=m["title"],
            description=m.get("description"),
            meeting_type=m["meeting_type"],
            scheduled_at=m["scheduled_at"],
            duration_minutes=m["duration_minutes"],
            location=m.get("location"),
            status=m["status"],
            organizer_id=ref["users_by_name"].get(m["organizer_name"]),
        )
        db.add(meeting)
        await db.flush()
        for att_name in m.get("attendee_names", []):
            att_id = ref["users_by_name"].get(att_name)
            if att_id:
                db.add(MeetingAttendee(
                    meeting_id=meeting.id,
                    user_id=att_id,
                    rsvp_status=RsvpStatus.ACCEPTED if m["status"] == "completed" else RsvpStatus.PENDING,
                ))
        count += 1
    return count


async def _insert_notices(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for n in data:
        exists = await db.execute(select(Notice).where(Notice.title == n["title"]))
        if exists.scalar_one_or_none():
            continue
        db.add(Notice(
            title=n["title"],
            body=n["body"],
            importance=NoticeImportance(n["importance"].lower()),
            is_pinned=n.get("is_pinned", False),
            publish_date=n["publish_date"],
            expiry_date=n["expiry_date"],
            created_by=ref["users_by_name"].get(n.get("created_by_name")),
        ))
        count += 1
    return count


async def _insert_leaves(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for lv in data:
        user_id = ref["users_by_name"].get(lv["employee_name"])
        if not user_id:
            continue
        exists = await db.execute(
            select(Leave).where(
                Leave.user_id == user_id,
                Leave.from_date == lv["from_date"],
                Leave.to_date == lv["to_date"],
            )
        )
        if exists.scalar_one_or_none():
            continue
        db.add(Leave(
            user_id=user_id,
            leave_type=LeaveType(lv["leave_type"]),
            from_date=lv["from_date"],
            to_date=lv["to_date"],
            total_days=lv["total_days"],
            reason=lv["reason"],
            status=LeaveStatus(lv["status"]),
            approved_by=ref["users_by_name"].get(lv.get("approved_by_name")) if lv.get("approved_by_name") else None,
        ))
        count += 1
    return count


async def _insert_attendance(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for a in data:
        user_id = ref["users_by_name"].get(a["employee_name"])
        if not user_id:
            continue
        exists = await db.execute(
            select(Attendance).where(
                Attendance.user_id == user_id,
                Attendance.date == a["date"],
            )
        )
        if exists.scalar_one_or_none():
            continue
        db.add(Attendance(
            user_id=user_id,
            date=a["date"],
            check_in_time=a["check_in_time"],
            check_out_time=a["check_out_time"],
            status=AttendanceStatus(a["status"].lower()),
            late_minutes=a.get("late_minutes", 0),
            total_hours=a["total_hours"],
        ))
        count += 1
    return count


async def _insert_site_visits(db: AsyncSession, data: list[dict], ref: dict) -> int:
    count = 0
    for sv in data:
        project_id = ref["projects"].get(sv["project_name"])
        if not project_id:
            continue
        exists = await db.execute(
            select(SiteVisit).where(
                SiteVisit.project_id == project_id,
                SiteVisit.visit_date == sv["visit_date"],
            )
        )
        if exists.scalar_one_or_none():
            continue
        db.add(SiteVisit(
            project_id=project_id,
            visit_date=sv["visit_date"],
            start_time=sv["start_time"],
            end_time=sv["end_time"],
            status=SiteVisitStatus(sv["status"].lower()),
            purpose=sv["purpose"],
            notes=sv.get("notes"),
            location=sv.get("location"),
            weather=sv.get("weather"),
            created_by=ref["users_by_name"].get(sv["created_by_name"]),
        ))
        count += 1
    return count


async def _insert_timesheets(
    db: AsyncSession,
    timesheets: list[dict],
    entries: list[dict],
    days: list[dict],
    employees: list[dict],
    ref: dict,
) -> tuple[int, int, int]:
    """Insert timesheets, entries, and days."""
    # Build emp_idx → user_id mapping
    emp_user_map = {}
    for idx, emp in enumerate(employees):
        emp_user_map[idx] = ref["users_by_name"].get(emp["name"])

    # Index entries/days by timesheet id
    entries_by_ts: dict[int, list] = {}
    for e in entries:
        entries_by_ts.setdefault(e["timesheet_id"], []).append(e)
    days_by_ts: dict[int, list] = {}
    for d in days:
        days_by_ts.setdefault(d["timesheet_id"], []).append(d)

    ts_count = ent_count = day_count = 0
    for ts in timesheets:
        user_id = emp_user_map.get(ts["emp_idx"])
        if not user_id:
            continue

        exists = await db.execute(
            select(Timesheet).where(
                Timesheet.user_id == user_id,
                Timesheet.week_start == ts["week_start"],
            )
        )
        if exists.scalar_one_or_none():
            continue

        status = TimesheetStatus(ts["status"].lower())
        approved_by_id = None
        if ts.get("approved_by_emp_idx") is not None:
            approved_by_id = emp_user_map.get(ts["approved_by_emp_idx"])
        elif status == TimesheetStatus.APPROVED:
            # Find the employee's manager
            emp_data = employees[ts["emp_idx"]]
            target = emp_data.get("reporting_to_name")
            if target == "_CEO_":
                ceo_name = "Admin User"
                approved_by_id = ref["users_by_name"].get(ceo_name)
                if not approved_by_id:
                    for name, uid in ref["users_by_name"].items():
                        approved_by_id = uid
                        break
            elif target:
                approved_by_id = ref["users_by_name"].get(target)

        sheet = Timesheet(
            user_id=user_id,
            week_start=ts["week_start"],
            status=status,
            submitted_at=ts.get("submitted_at"),
            approved_by=approved_by_id,
            approved_at=ts.get("approved_at"),
            rejection_reason=ts.get("rejection_reason"),
        )
        db.add(sheet)
        await db.flush()
        ts_count += 1

        for e in entries_by_ts.get(ts["id"], []):
            proj_idx = e.get("project_idx")
            project_names = list(ref["projects"].keys())
            project_id = ref["projects"].get(project_names[proj_idx]) if proj_idx is not None and proj_idx < len(project_names) else None
            db.add(TimesheetEntry(
                timesheet_id=sheet.id,
                project_id=project_id,
                date=e["date"],
                hours=Decimal(str(e["hours"])),
                location=e.get("location", ""),
                description=e.get("description", ""),
            ))
            ent_count += 1

        for d in days_by_ts.get(ts["id"], []):
            day_status = TimesheetStatus(d["status"].lower())
            day_approved_by = None
            if day_status == TimesheetStatus.APPROVED and approved_by_id:
                day_approved_by = approved_by_id
            db.add(TimesheetDay(
                timesheet_id=sheet.id,
                date=d["date"],
                status=day_status,
                submitted_at=d.get("submitted_at"),
                approved_by=day_approved_by,
                approved_at=d.get("approved_at"),
                rejection_reason=d.get("rejection_reason"),
            ))
            day_count += 1

    return ts_count, ent_count, day_count


# ── Main ────────────────────────────────────────────────────────────────

async def seed_db(url: str = DEFAULT_URL) -> None:
    print(f"Connecting to {url} ...")
    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("Generating test data ...")
    data = generate_all()

    async with async_session() as db:
        # Check reference data exists
        ref = await _load_ref_data(db)
        if not ref["depts"]:
            print("ERROR: No departments found. Run seed_org_levels() and seed_departments() first.")
            return
        if not ref["levels"]:
            print("ERROR: No org levels found. Run seed_org_levels() first.")
            return

        print(f"  Departments: {len(ref['depts'])}")
        print(f"  Org Levels:  {len(ref['levels'])}")
        print(f"  Users (existing): {len(ref['users_by_name'])}")
        print(f"  Projects (existing): {len(ref['projects'])}")
        print(f"  Clients (existing): {len(ref['clients'])}")
        print()

        n = await _insert_clients(db, data["clients"], ref)
        print(f"  Clients inserted: {n}")

        n = await _insert_projects(db, data["projects"], ref)
        print(f"  Projects inserted: {n}")

        n = await _insert_employees(db, data["employees"], ref)
        print(f"  Employees inserted: {n}")

        n = await _insert_salary_components(db, data["salary_components"], ref)
        print(f"  Salary components inserted: {n}")

        n = await _insert_tasks(db, data["tasks"], ref)
        print(f"  Tasks inserted: {n}")

        n = await _insert_expenses(db, data["expenses"], ref)
        print(f"  Expenses inserted: {n}")

        n = await _insert_invoices(db, data["invoices"], ref)
        print(f"  Invoices inserted: {n}")

        n = await _insert_meetings(db, data["meetings"], ref)
        print(f"  Meetings inserted: {n}")

        n = await _insert_notices(db, data["notices"], ref)
        print(f"  Notices inserted: {n}")

        n = await _insert_leaves(db, data["leaves"], ref)
        print(f"  Leaves inserted: {n}")

        n = await _insert_attendance(db, data["attendance"], ref)
        print(f"  Attendance inserted: {n}")

        n = await _insert_site_visits(db, data["site_visits"], ref)
        print(f"  Site visits inserted: {n}")

        ts, ent, day = await _insert_timesheets(
            db, data["timesheets"], data["entries"], data["days"],
            data["employees"], ref,
        )
        print(f"  Timesheets inserted: {ts}")
        print(f"  Timesheet entries inserted: {ent}")
        print(f"  Timesheet days inserted: {day}")

        await db.commit()
        print("\nDone. All data committed.")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Seed bulk test data into PostgreSQL")
    parser.add_argument("--url", default=DEFAULT_URL, help="Async PostgreSQL connection URL")
    args = parser.parse_args()
    asyncio.run(seed_db(args.url))


if __name__ == "__main__":
    main()
