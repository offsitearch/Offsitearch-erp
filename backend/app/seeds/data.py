from datetime import date

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models import Department, Holiday, LeaveBalance, OrgLevel, Setting, User
from app.utils.enums import LeaveType
from app.utils.org_structure import DEPARTMENTS as ORG_DEPARTMENTS
from app.utils.org_structure import ORG_LEVELS
from app.utils.shared import now_local

DEPARTMENTS = ORG_DEPARTMENTS

# Runtime defaults now live in their owning modules; re-exported here for
# seeding use and backward compatibility with existing imports.
from app.modules.attendance.defaults import ATTENDANCE_SETTINGS  # noqa: E402
from app.modules.leave.defaults import LEAVE_SETTINGS  # noqa: E402
from app.modules.projects.defaults import PROJECT_TYPE_TEMPLATES  # noqa: E402

COMPANY_SETTINGS = {
    "profile": {
        "name": "Offsitearch",
        "tagline": "Architecture & Interiors",
        "monogram": "OA",
        "address": "42 Studio Lane, Block C, Bengaluru, Karnataka 560001",
        "phone": "+91 80 4123 4567",
        "email": "hello@offsitearch.com",
        "gstin": "29AAAAA0000A1Z5",
        "website": "https://offsitearch.com",
        "bank_name": "HDFC Bank",
        "account_name": "Offsitearch Design LLP",
        "account_number": "50200042118876",
        "ifsc_code": "HDFC0001234",
        "upi_id": "offsitearch@hdfcbank",
        "default_terms": "Payment due within 30 days of invoice date. "
        "Interest at 1.5% per month applies on overdue amounts.",
    }
}

HOLIDAYS = [
    {"name": "Republic Day", "date": date(2026, 1, 26)},
    {"name": "Holi", "date": date(2026, 3, 4)},
    {"name": "Independence Day", "date": date(2026, 8, 15)},
    {"name": "Gandhi Jayanti", "date": date(2026, 10, 2)},
    {"name": "Diwali", "date": date(2026, 11, 8)},
    {"name": "Christmas", "date": date(2026, 12, 25)},
]

DEMO_CLIENTS = [
    {
        "name": "Meera & Rajesh Sharma",
        "client_type": "individual",
        "phone": "9822012345",
        "email": "sharma.family@example.com",
        "source": "referral",
        "budget_range": "1.5 - 2.5 Cr",
        "interest": "Residential villa",
    },
    {
        "name": "Skyline Developers",
        "client_type": "developer",
        "company_name": "Skyline Developers Pvt. Ltd.",
        "contact_person": "Anand Kulkarni",
        "phone": "9822098765",
        "email": "anand@skyline.in",
        "source": "website",
        "budget_range": "20 Cr+",
        "interest": "Mixed-use + commercial towers",
    },
    {
        "name": "Kaveri Art Gallery",
        "client_type": "company",
        "company_name": "Kaveri Arts",
        "contact_person": "Ritika Bose",
        "phone": "9822011223",
        "email": "ritika@kaveriarts.in",
        "source": "social",
        "budget_range": "80L - 1.2 Cr",
        "interest": "Interior fit-out for gallery + cafe",
    },
]

DEMO_PROJECTS = [
    {
        "name": "Sharma Residence - Villa",
        "project_type": "residential",
        "category": "Villa",
        "location": "Kothrud, Pune",
        "plot_area": 4200,
        "built_up_area": 6800,
        "no_of_floors": "G+1",
        "budget": 21000000,
        "studio_fee": 1575000,
        "fee_type": "percent",
        "fee_percent": 7.5,
        "status": "in_construction",
        "priority": "high",
    },
    {
        "name": "Skyline Commercial Tower B",
        "project_type": "commercial",
        "category": "Office Tower",
        "location": "Baner, Pune",
        "plot_area": 18500,
        "built_up_area": 62000,
        "no_of_floors": "G+14",
        "budget": 145000000,
        "studio_fee": 8700000,
        "fee_type": "percent",
        "fee_percent": 6,
        "status": "under_review",
        "priority": "high",
    },
    {
        "name": "Kaveri Gallery Interiors",
        "project_type": "interior",
        "category": "Cultural Interior",
        "location": "Koregaon Park, Pune",
        "built_up_area": 4600,
        "no_of_floors": "G",
        "budget": 9800000,
        "studio_fee": 882000,
        "fee_type": "percent",
        "fee_percent": 9,
        "status": "design",
        "priority": "medium",
    },
]


async def seed_departments(db) -> None:
    for dept in DEPARTMENTS:
        exists = await db.execute(select(Department).where(Department.name == dept["name"]))
        if exists.scalar_one_or_none():
            continue
        db.add(Department(**dept))
    await db.commit()


async def seed_org_levels(db) -> None:
    for level in ORG_LEVELS:
        exists = await db.execute(select(OrgLevel).where(OrgLevel.code == level["code"]))
        if exists.scalar_one_or_none():
            continue
        db.add(OrgLevel(**level))
    await db.commit()


async def seed_settings(db) -> None:
    for group, group_settings in {
        "attendance": ATTENDANCE_SETTINGS,
        "leave": LEAVE_SETTINGS,
        "company": COMPANY_SETTINGS,
    }.items():
        for key, value in group_settings.items():
            exists = await db.execute(
                select(Setting).where(Setting.group == group, Setting.key == key)
            )
            if exists.scalar_one_or_none():
                continue
            db.add(Setting(group=group, key=key, value=value))
    await db.commit()


async def seed_superuser(db) -> None:
    email = settings.first_superuser_email.lower()
    exists = await db.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none():
        return
    level = (await db.execute(select(OrgLevel).where(OrgLevel.code == "L0"))).scalar_one_or_none()
    if level is None:
        level = (
            await db.execute(select(OrgLevel).where(OrgLevel.code == "L1"))
        ).scalar_one_or_none()
    from app.core.security import format_login_id
    from app.modules.identity.repository import user_repository

    year = now_local().date().year
    login_id = format_login_id(year, await user_repository.next_login_sequence(db, year))
    db.add(
        User(
            email=email,
            login_id=login_id,
            name="Studio Owner",
            org_level_id=level.id if level else None,
            designation="Chief Executive Officer",
            password_hash=hash_password(settings.first_superuser_password),
        )
    )
    await db.commit()


async def seed_holidays(db) -> None:
    for holiday in HOLIDAYS:
        exists = await db.execute(select(Holiday).where(Holiday.date == holiday["date"]))
        if exists.scalar_one_or_none():
            continue
        db.add(Holiday(**holiday))
    await db.commit()


async def seed_leave_balances(db, year: int | None = None) -> None:
    """Create default annual leave balances for all active users."""
    year = year or now_local().date().year
    policy = LEAVE_SETTINGS["policy"]
    users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
    for user in users:
        for leave_type, allocated in policy.items():
            if leave_type == "carry_forward":
                continue
            exists = await db.execute(
                select(LeaveBalance).where(
                    LeaveBalance.user_id == user.id,
                    LeaveBalance.leave_type == LeaveType(leave_type),
                    LeaveBalance.year == year,
                )
            )
            if exists.scalar_one_or_none():
                continue
            db.add(
                LeaveBalance(
                    user_id=user.id,
                    leave_type=LeaveType(leave_type),
                    year=year,
                    allocated=allocated,
                    used=0,
                )
            )
    await db.commit()


async def seed_clients(db) -> None:
    from app.models import Client
    from app.utils.enums import ClientType

    for item in DEMO_CLIENTS:
        email = item["email"]
        if email:
            exists = await db.execute(select(Client).where(Client.email == email))
            if exists.scalar_one_or_none():
                continue
        else:
            exists = await db.execute(select(Client).where(Client.name == item["name"]))
            if exists.scalar_one_or_none():
                continue
        db.add(
            Client(
                name=item["name"],
                client_type=ClientType(item["client_type"]),
                **{k: v for k, v in item.items() if k not in ("name", "client_type")},
            )
        )
    await db.commit()


async def seed_projects(db) -> None:
    from app.models import Client, Project, ProjectPhase
    from app.modules.projects.service import _compute_progress, next_project_code
    from app.utils.enums import PhaseStatus, ProjectStatus, ProjectType

    lead = (
        (
            await db.execute(
                select(User)
                .join(OrgLevel, OrgLevel.id == User.org_level_id)
                .where(OrgLevel.code == "L1", User.is_active.is_(True))
            )
        )
        .scalars()
        .first()
    )

    for index, item in enumerate(DEMO_PROJECTS):
        exists = await db.execute(select(Project).where(Project.name == item["name"]))
        if exists.scalar_one_or_none():
            continue
        client = (
            await db.execute(
                select(Client).where(Client.name == DEMO_CLIENTS[index % len(DEMO_CLIENTS)]["name"])
            )
        ).scalar_one_or_none()
        code = await next_project_code(db, now_local().date().year)
        project = Project(
            project_code=code,
            name=item["name"],
            project_type=ProjectType(item["project_type"]),
            category=item.get("category"),
            location=item.get("location"),
            plot_area=item.get("plot_area"),
            built_up_area=item.get("built_up_area"),
            no_of_floors=item.get("no_of_floors"),
            budget=item.get("budget"),
            studio_fee=item.get("studio_fee"),
            fee_type=item.get("fee_type"),
            fee_percent=item.get("fee_percent"),
            status=ProjectStatus(item["status"]),
            priority=item.get("priority", "medium"),
            client_id=client.id if client else None,
            project_lead_id=lead.id if lead else None,
        )
        db.add(project)
        await db.flush()

        template = PROJECT_TYPE_TEMPLATES[item["project_type"]]
        phases = [
            ProjectPhase(
                project_id=project.id,
                name=name,
                order_index=phase_index,
                status=PhaseStatus.NOT_STARTED,
                completion_pct=0,
            )
            for phase_index, name in enumerate(template["phases"])
        ]
        db.add_all(phases)
        await db.flush()
        project.progress_pct = _compute_progress(phases)
    await db.commit()
