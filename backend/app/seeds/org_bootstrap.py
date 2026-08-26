"""Initial organisation bootstrap for the Offsite Architecture studio.

Run AFTER migrations + ``init_db`` (reference data + superuser row exist).
Expects a FRESH database: raises :class:`OrgBootstrapError` when employee
rows already exist, so a wipe (TRUNCATE ... RESTART IDENTITY CASCADE) is
required before re-running.

Creates, in order:

1. CEO update of the superuser row (login ``260001``, name "CEO",
   ``ceo@offsitearch.com``; password stays ``FIRST_SUPERUSER_PASSWORD``).
2. 10 employees across L1-L6 with reporting lines and one-time numeric
   passwords (``must_change_password=True``). Login ids are sequential
   ``YY####`` values from joining-year 2026 -> ``260002``..``260011``.
3. Two promotions baked into history: Meera L6->L5 ("Architect") and
   Devang L5->L4 ("Sr. Architect"). Final level coverage: every one of
   L1..L6 is present at least once.
4. Business seed data: 3 clients, 3 projects with phases/teams, tasks,
   a pinned notice, an internal meeting with attendees, a site visit,
   salary components for everyone, two pending expenses and two invoices.
5. Leave balances for all users (``seed_leave_balances``).

Returns a JSON-serialisable manifest with every login id / email /
one-time password so the caller can capture credentials::

    python -c "import asyncio,json;from app.seeds.org_bootstrap import
    bootstrap_org;print(json.dumps(asyncio.run(bootstrap_org()),indent=2))"
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core.security import (
    format_login_id,
    generate_email,
    generate_numeric_password,
    hash_password,
)
from app.db.session import AsyncSessionLocal
from app.models import (
    Client,
    ClientCommunication,
    Department,
    Expense,
    Invoice,
    InvoiceItem,
    Meeting,
    MeetingAttendee,
    Notice,
    OrgLevel,
    Project,
    ProjectPhase,
    ProjectTeam,
    SalaryComponent,
    SiteVisit,
    Task,
    TaskChecklist,
    User,
)
from app.seeds.data import (
    seed_departments,
    seed_holidays,
    seed_leave_balances,
    seed_org_levels,
    seed_settings,
    seed_superuser,
)
from app.utils.enums import (
    ExpenseStatus,
    InvoiceStatus,
    MeetingStatus,
    MeetingType,
    NoticeImportance,
    PaymentMethod,
    PhaseStatus,
    ProjectStatus,
    ProjectType,
    RsvpStatus,
    SiteVisitStatus,
    TaskPriority,
    TaskStatus,
)

JOBS_YEAR = 2026

CEO_LOGIN_ID = "260001"
CEO_NAME = "CEO"
CEO_EMAIL = "ceo@offsitearch.com"


# Final passwords applied during each walkthrough (documented in creds).
def final_password(login_id: str) -> str:
    return f"Offsite#{login_id}@2026"


EMPLOYEE_BLUEPRINT: list[dict] = [
    dict(
        key="ishaan",
        name="Ishaan Malhotra",
        department="Architecture & Design",
        initial_level="L2",
        initial_designation="Design Head",
        joining=date(2026, 1, 12),
        reports_to="ceo",
        gender="Male",
        phone="+91 98200 11201",
    ),
    dict(
        key="rohan",
        name="Rohan Kapoor",
        department="BIM & Visualization",
        initial_level="L4",
        initial_designation="Sr. BIM Specialist",
        joining=date(2026, 2, 9),
        reports_to="ishaan",
        gender="Male",
        phone="+91 98200 11202",
    ),
    dict(
        key="meera",
        name="Meera Krishnan",
        department="Architecture & Design",
        initial_level="L6",
        initial_designation="Architecture Intern",
        joining=date(2026, 6, 1),
        reports_to="ishaan",
        gender="Female",
        phone="+91 98200 11203",
    ),
    dict(
        key="tara",
        name="Tara Deshpande",
        department="Interior Design",
        initial_level="L2",
        initial_designation="Interior Design Head",
        joining=date(2026, 1, 26),
        reports_to="ceo",
        gender="Female",
        phone="+91 98200 11204",
    ),
    dict(
        key="kabir",
        name="Kabir Anand",
        department="Project & Site",
        initial_level="L3",
        initial_designation="Project Manager",
        joining=date(2026, 3, 30),
        reports_to="ishaan",
        gender="Male",
        phone="+91 98200 11205",
    ),
    dict(
        key="ananya",
        name="Ananya Rao",
        department="Landscape",
        initial_level="L4",
        initial_designation="Sr. Landscape Designer",
        joining=date(2026, 2, 16),
        reports_to="kabir",
        gender="Female",
        phone="+91 98200 11206",
    ),
    dict(
        key="devang",
        name="Devang Shah",
        department="Architecture & Design",
        initial_level="L5",
        initial_designation="Architect",
        joining=date(2026, 5, 18),
        reports_to="ishaan",
        gender="Male",
        phone="+91 98200 11207",
    ),
    dict(
        key="sana",
        name="Sana Qureshi",
        department="Business & Operations",
        initial_level="L6",
        initial_designation="Operations Executive",
        joining=date(2026, 8, 10),
        reports_to="priya",
        gender="Female",
        phone="+91 98200 11208",
    ),
    dict(
        key="vikram",
        name="Vikram Sethi",
        department="Corporate / Administration",
        initial_level="L1",
        initial_designation="Director - Finance",
        joining=date(2026, 1, 5),
        reports_to="ceo",
        gender="Male",
        phone="+91 98200 11209",
    ),
    dict(
        key="priya",
        name="Priya Nambiar",
        department="Corporate / Administration",
        initial_level="L1",
        initial_designation="Director - HR & Operations",
        joining=date(2026, 4, 20),
        reports_to="ceo",
        gender="Female",
        phone="+91 98200 11210",
    ),
]

# Baked-in promotion history (final levels still cover L1..L6 exactly once
# per person below; see module docstring).
PROMOTIONS: list[dict] = [
    dict(key="meera", to_level="L5", to_designation="Architect"),
    dict(key="devang", to_level="L4", to_designation="Sr. Architect"),
]

# Annual CTC by final org level - used for salary components.
CTC_BY_LEVEL = {
    "L1": Decimal("2400000"),
    "L2": Decimal("1800000"),
    "L3": Decimal("1500000"),
    "L4": Decimal("1200000"),
    "L5": Decimal("900000"),
    "L6": Decimal("480000"),
}


class OrgBootstrapError(RuntimeError):
    """Raised when the database is not in a fresh, bootstrap-ready state."""


def _phase_rows(project_id: int, template: list[str], start: date) -> list[ProjectPhase]:
    rows = []
    for idx, name in enumerate(template):
        status = (
            PhaseStatus.COMPLETED
            if idx == 0
            else (PhaseStatus.IN_PROGRESS if idx == 1 else PhaseStatus.NOT_STARTED)
        )
        pct = Decimal("100") if idx == 0 else (Decimal("40") if idx == 1 else Decimal("0"))
        rows.append(
            ProjectPhase(
                project_id=project_id,
                name=name,
                order_index=idx,
                start_date=start + timedelta(days=45 * idx),
                end_date=start + timedelta(days=45 * idx + 40),
                status=status,
                completion_pct=pct,
            )
        )
    return rows


async def _update_ceo(db) -> User:
    ceo = (await db.execute(select(User).where(User.login_id == CEO_LOGIN_ID))).scalar_one_or_none()
    if ceo is None:
        raise OrgBootstrapError(f"Superuser row {CEO_LOGIN_ID} missing - run init_db first.")
    corp = (
        await db.execute(select(Department).where(Department.name == "Corporate / Administration"))
    ).scalar_one()
    ceo.name = CEO_NAME
    ceo.email = CEO_EMAIL
    ceo.department_id = corp.id
    ceo.designation = "Chief Executive Officer"
    ceo.date_of_joining = date(JOBS_YEAR, 1, 1)
    ceo.employee_id = "OA-001"
    ceo.must_change_password = False
    await db.flush()
    return ceo


async def _create_employees(db, ceo: User) -> tuple[dict[str, User], list[dict]]:
    existing = (
        await db.execute(
            select(func.count()).select_from(User).where(User.login_id != CEO_LOGIN_ID)
        )
    ).scalar_one()
    if existing:
        raise OrgBootstrapError(
            f"{existing} employee row(s) already exist - wipe the database "
            "before bootstrapping the organisation."
        )

    dept_ids = {
        name: did for name, did in (await db.execute(select(Department.name, Department.id))).all()
    }
    level_ids = {}
    for code, lid in (await db.execute(select(OrgLevel.code, OrgLevel.id))).all():
        level_ids[code] = lid

    users_by_key: dict[str, User] = {"ceo": ceo}
    manifest_rows: list[dict] = []
    temp_passwords: dict[str, str] = {}

    for idx, bp in enumerate(EMPLOYEE_BLUEPRINT):
        seq = idx + 2  # 260001 is the CEO
        login_id = format_login_id(bp["joining"].year, seq)
        email = generate_email(bp["name"], bp["joining"])
        temp = generate_numeric_password()
        temp_passwords[bp["key"]] = temp
        user = User(
            email=email,
            login_id=login_id,
            name=bp["name"],
            designation=bp["initial_designation"],
            phone=bp["phone"],
            gender=bp["gender"],
            date_of_joining=bp["joining"],
            employee_id=f"OA-{seq:03d}",
            department_id=dept_ids[bp["department"]],
            org_level_id=level_ids[bp["initial_level"]],
            password_hash=hash_password(temp),
            must_change_password=True,
        )
        db.add(user)
        users_by_key[bp["key"]] = user
        await db.flush()

    # Reporting lines need every user id first.
    for bp in EMPLOYEE_BLUEPRINT:
        users_by_key[bp["key"]].reporting_to_id = users_by_key[bp["reports_to"]].id
    await db.flush()

    for bp in EMPLOYEE_BLUEPRINT:
        u = users_by_key[bp["key"]]
        promoted = next((p for p in PROMOTIONS if p["key"] == bp["key"]), None)
        if promoted:
            u.org_level_id = level_ids[promoted["to_level"]]
            u.designation = promoted["to_designation"]
        final_level = promoted["to_level"] if promoted else bp["initial_level"]
        final_designation = promoted["to_designation"] if promoted else bp["initial_designation"]
        manifest_rows.append(
            dict(
                key=bp["key"],
                id=u.id,
                login_id=u.login_id,
                name=u.name,
                email=u.email,
                department=bp["department"],
                designation=final_designation,
                initial_level=bp["initial_level"],
                level=final_level,
                promoted_to=promoted["to_level"] if promoted else None,
                joining_date=u.date_of_joining.isoformat(),
                temp_password=temp_passwords[bp["key"]],
                password=final_password(u.login_id),
                reporting_to_login_id=users_by_key[bp["reports_to"]].login_id,
            )
        )
    return users_by_key, manifest_rows


async def _seed_business_data(db, ceo: User, users_by_key: dict[str, User]) -> dict:
    today = datetime.now().date()

    # -- Clients -----------------------------------------------------------
    clients: dict[str, Client] = {}
    client_specs = [
        dict(
            name="Aditya Bhandari",
            client_type="individual",
            contact_person="Aditya Bhandari",
            email="aditya.bhandari@example.com",
            phone="+91 90040 55101",
            address="12, Palm Grove, Bandra West",
            budget_range="₹25-50 lakh",
            interest="4BHK family residence",
            deal_stage="won",
        ),
        dict(
            name="Meridian Developers LLP",
            client_type="developer",
            company_name="Meridian Developers LLP",
            contact_person="Farhan Mistry",
            email="farhan@meridiandev.example.com",
            phone="+91 90040 55102",
            address="5th Floor, Trade Centre, Lower Parel",
            budget_range="₹2-5 crore",
            interest="Clubhouse interiors",
            deal_stage="proposal",
        ),
        dict(
            name="GreenLeaf Organics",
            client_type="company",
            company_name="GreenLeaf Organics Pvt Ltd",
            contact_person="Nandita Rao",
            email="nandita@greenleaforganics.example.com",
            phone="+91 90040 55103",
            address="Survey 44, Airoli Knowledge Park",
            budget_range="₹50 lakh-1 crore",
            interest="Office landscape retrofit",
            deal_stage="negotiation",
        ),
    ]
    for spec in client_specs:
        client = Client(**spec, notes="Seeded during org bootstrap.")
        db.add(client)
        await db.flush()
        clients[client.name] = client
        db.add(
            ClientCommunication(
                client_id=client.id,
                user_id=ceo.id,
                type="call" if spec["client_type"] == "individual" else "meeting",
                subject="Introductory discussion",
                notes="Requirement briefing completed.",
                occurred_at=datetime.now(),
            )
        )

    def uid(key: str) -> int:
        return users_by_key[key].id

    # -- Projects ----------------------------------------------------------
    start_a = today - timedelta(days=75)
    projects: dict[str, Project] = {}

    p1 = Project(
        project_code="OA-2601-RES",
        name="Bhandari Residence, Bandra",
        description="4BHK family residence - architecture and interior package.",
        project_type=ProjectType.RESIDENTIAL,
        category="residential",
        client_id=clients["Aditya Bhandari"].id,
        location="Bandra West, Mumbai",
        plot_area=Decimal("4200.00"),
        built_up_area=Decimal("3800.00"),
        no_of_floors="G+2",
        budget=Decimal("3200000.00"),
        studio_fee=Decimal("288000.00"),
        fee_type="lumpsum",
        start_date=start_a,
        end_date=today + timedelta(days=200),
        status=ProjectStatus.DESIGN,
        project_lead_id=uid("kabir"),
        priority="high",
        progress_pct=Decimal("25.00"),
    )
    db.add(p1)
    await db.flush()
    projects[p1.project_code] = p1
    for ph in _phase_rows(p1.id, ["Concept Design", "Design Development", "GFC Drawings"], start_a):
        db.add(ph)
    for member, role in [
        ("ishaan", "Design Review"),
        ("rohan", "BIM Modeler"),
        ("meera", "Junior Designer"),
        ("devang", "Architect"),
    ]:
        db.add(ProjectTeam(project_id=p1.id, user_id=uid(member), role=role))

    p2 = Project(
        project_code="OA-2602-INT",
        name="Meridian Clubhouse Interiors",
        description="Clubhouse interior design for a 12-storey residential tower.",
        project_type=ProjectType.INTERIOR,
        category="interior",
        client_id=clients["Meridian Developers LLP"].id,
        location="Lower Parel, Mumbai",
        built_up_area=Decimal("12500.00"),
        no_of_floors="Ground + Mezzanine",
        budget=Decimal("8500000.00"),
        studio_fee=Decimal("765000.00"),
        fee_type="percentage",
        fee_percent=Decimal("9.00"),
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=300),
        status=ProjectStatus.CONCEPT,
        project_lead_id=uid("ishaan"),
        priority="medium",
        progress_pct=Decimal("10.00"),
    )
    db.add(p2)
    await db.flush()
    projects[p2.project_code] = p2
    for ph in _phase_rows(
        p2.id,
        ["Concept & Moodboards", "3D Visualisation", "Execution Drawings"],
        today - timedelta(days=30),
    ):
        db.add(ph)
    for member, role in [
        ("tara", "Interior Lead"),
        ("devang", "Designer"),
        ("sana", "Client Coordination"),
    ]:
        db.add(ProjectTeam(project_id=p2.id, user_id=uid(member), role=role))

    p3 = Project(
        project_code="OA-2603-LAN",
        name="GreenLeaf Office Campus Landscape",
        description="Campus landscape retrofit with native planting palette.",
        project_type=ProjectType.LANDSCAPE,
        category="landscape",
        client_id=clients["GreenLeaf Organics"].id,
        location="Airoli, Navi Mumbai",
        plot_area=Decimal("22000.00"),
        budget=Decimal("4500000.00"),
        studio_fee=Decimal("360000.00"),
        fee_type="lumpsum",
        start_date=today - timedelta(days=15),
        end_date=today + timedelta(days=240),
        status=ProjectStatus.CONCEPT,
        project_lead_id=uid("kabir"),
        priority="medium",
        progress_pct=Decimal("5.00"),
    )
    db.add(p3)
    await db.flush()
    projects[p3.project_code] = p3
    for ph in _phase_rows(
        p3.id, ["Site Analysis", "Landscape Concept", "Planting Plan"], today - timedelta(days=15)
    ):
        db.add(ph)
    for member, role in [("ananya", "Landscape Designer"), ("kabir", "Project Manager")]:
        db.add(ProjectTeam(project_id=p3.id, user_id=uid(member), role=role))

    # -- Tasks -------------------------------------------------------------
    async def add_task(
        title,
        desc,
        project,
        assignee,
        assigned_by_key,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        due_days=14,
        est_hours=None,
        checklist=None,
    ):
        t = Task(
            title=title,
            description=desc,
            project_id=project.id,
            assigned_to=uid(assignee),
            assigned_by=uid(assigned_by_key),
            priority=priority,
            status=status,
            start_date=today - timedelta(days=3),
            due_date=today + timedelta(days=due_days),
            estimated_hours=est_hours,
            tags=[project.category] if project.category else None,
        )
        db.add(t)
        await db.flush()
        for item in checklist or []:
            db.add(TaskChecklist(task_id=t.id, text=item))
        return t

    t1 = await add_task(
        "Concept floor plan revision 2",
        "Incorporate client feedback on the west wing.",
        p1,
        "meera",
        "kabir",
        TaskStatus.IN_PROGRESS,
        TaskPriority.HIGH,
        7,
        Decimal("24"),
        ["Revise grid", "Share with lead"],
    )
    await add_task(
        "LOD300 model update",
        "Update structural coordination model.",
        p1,
        "rohan",
        "kabir",
        TaskStatus.IN_PROGRESS,
        TaskPriority.MEDIUM,
        10,
        Decimal("32"),
    )
    await add_task(
        "Material board for living areas",
        "Curate finishes palette.",
        p1,
        "devang",
        "ishaan",
        TaskStatus.REVIEW,
        TaskPriority.MEDIUM,
        5,
        Decimal("12"),
    )
    await add_task(
        "Clubhouse moodboard round 1",
        "Three moodboard directions for review.",
        p2,
        "tara",
        "ishaan",
        TaskStatus.IN_PROGRESS,
        TaskPriority.HIGH,
        9,
        Decimal("20"),
    )
    await add_task(
        "FF&E budget sheet",
        "Draft FF&E allowance vs budget check.",
        p2,
        "sana",
        "tara",
        TaskStatus.TODO,
        TaskPriority.MEDIUM,
        12,
        Decimal("8"),
    )
    await add_task(
        "Render set for sales gallery",
        "Six camera angles, dusk lighting.",
        p2,
        "rohan",
        "ishaan",
        TaskStatus.TODO,
        TaskPriority.HIGH,
        16,
        Decimal("40"),
    )
    await add_task(
        "Topographic survey review",
        "Validate survey vendor deliverable.",
        p3,
        "ananya",
        "kabir",
        TaskStatus.DONE,
        TaskPriority.MEDIUM,
        -1,
        Decimal("10"),
    )
    await add_task(
        "Native species planting list",
        "Draft palette of coastal-native species.",
        p3,
        "ananya",
        "kabir",
        TaskStatus.IN_PROGRESS,
        TaskPriority.MEDIUM,
        11,
        Decimal("18"),
    )
    await add_task(
        "Monthly project cost tracker",
        "Consolidate consultant invoices and fees.",
        p3,
        "vikram",
        "kabir",
        TaskStatus.TODO,
        TaskPriority.LOW,
        20,
        Decimal("4"),
    )
    task_ids = {"concept_floor_plan": t1.id}

    # -- Notice / meeting / site visit --------------------------------------
    db.add(
        Notice(
            title="Welcome to Offsite Architects!",
            body=(
                "Our studio runs on this ERP. Log in with your 6-digit login ID, "
                "set a new password on first sign-in, and fill in your timesheet weekly."
            ),
            importance=NoticeImportance.HIGH,
            is_pinned=True,
            publish_date=today,
            created_by=ceo.id,
        )
    )
    meeting = Meeting(
        title="Monday design sync",
        description="Weekly design progress across active projects.",
        meeting_type=MeetingType.INTERNAL,
        scheduled_at=datetime.combine(
            today + timedelta(days=(7 - today.weekday()) % 7 or 1), time(10, 0)
        ),
        duration_minutes=45,
        location="Studio - Conference Room",
        status=MeetingStatus.SCHEDULED,
        organizer_id=uid("ishaan"),
    )
    db.add(meeting)
    await db.flush()
    for key, rsvp in [
        ("ishaan", RsvpStatus.ACCEPTED),
        ("rohan", RsvpStatus.PENDING),
        ("meera", RsvpStatus.PENDING),
        ("devang", RsvpStatus.ACCEPTED),
    ]:
        db.add(MeetingAttendee(meeting_id=meeting.id, user_id=uid(key), rsvp_status=rsvp))

    visit = SiteVisit(
        project_id=p1.id,
        visit_date=today + timedelta(days=5),
        start_time=time(10, 30),
        end_time=time(13, 0),
        purpose="Site measurement verification for GFC drawings",
        location="Bandra West site office",
        status=SiteVisitStatus.SCHEDULED,
        created_by=uid("kabir"),
    )
    db.add(visit)
    await db.flush()

    # -- Salaries / expenses / invoices -------------------------------------
    for bp in EMPLOYEE_BLUEPRINT:
        u = users_by_key[bp["key"]]
        promoted = next((p for p in PROMOTIONS if p["key"] == bp["key"]), None)
        level = promoted["to_level"] if promoted else bp["initial_level"]
        ctc = CTC_BY_LEVEL[level]
        db.add(SalaryComponent(user_id=u.id, ctc_annual=float(ctc)))
    db.add(SalaryComponent(user_id=ceo.id, ctc_annual=4800000.0))

    db.add(
        Expense(
            category="travel",
            description="Site visit travel - Bandra",
            amount=Decimal("1850.00"),
            expense_date=today - timedelta(days=2),
            project_id=p1.id,
            paid_by="Rohan Kapoor",
            status=ExpenseStatus.PENDING,
        )
    )
    db.add(
        Expense(
            category="software",
            description="Enscape licence renewal",
            amount=Decimal("24999.00"),
            expense_date=today - timedelta(days=1),
            paid_by="Sana Qureshi",
            status=ExpenseStatus.PENDING,
        )
    )

    # Keep the paid invoice inside the current calendar month so executive
    # dashboards always show revenue regardless of when bootstrap runs.
    payment_day = today - timedelta(days=min(12, today.day - 1))
    inv1 = Invoice(
        invoice_number="INV-2026-0001",
        client_id=clients["Aditya Bhandari"].id,
        project_id=p1.id,
        invoice_date=payment_day - timedelta(days=40),
        due_date=payment_day - timedelta(days=2),
        subtotal=Decimal("144000.00"),
        tax_percent=Decimal("18.00"),
        tax_amount=Decimal("25920.00"),
        total=Decimal("169920.00"),
        status=InvoiceStatus.PAID,
        sent_at=datetime.combine(payment_day - timedelta(days=38), time(9, 0)),
        paid_amount=Decimal("169920.00"),
        payment_date=payment_day,
        payment_method=PaymentMethod.BANK_TRANSFER,
        terms="50% advance against design fee.",
    )
    db.add(inv1)
    await db.flush()
    db.add(
        InvoiceItem(
            invoice_id=inv1.id,
            description="Design fee milestone 1 (concept)",
            quantity=Decimal("1"),
            rate=Decimal("144000.00"),
            amount=Decimal("144000.00"),
        )
    )

    inv2 = Invoice(
        invoice_number="INV-2026-0002",
        client_id=clients["Meridian Developers LLP"].id,
        project_id=p2.id,
        invoice_date=today - timedelta(days=8),
        due_date=today + timedelta(days=22),
        subtotal=Decimal("191250.00"),
        tax_percent=Decimal("18.00"),
        tax_amount=Decimal("34425.00"),
        total=Decimal("225675.00"),
        status=InvoiceStatus.SENT,
        sent_at=datetime.now() - timedelta(days=7),
        notes="Mobilisation advance as per agreement.",
    )
    db.add(inv2)
    await db.flush()
    db.add(
        InvoiceItem(
            invoice_id=inv2.id,
            description="Mobilisation advance - clubhouse interiors",
            quantity=Decimal("1"),
            rate=Decimal("191250.00"),
            amount=Decimal("191250.00"),
        )
    )

    return {
        "clients": [
            {"name": c.name, "id": c.id, "deal_stage": c.deal_stage} for c in clients.values()
        ],
        "projects": [
            {"project_code": p.project_code, "id": p.id, "name": p.name} for p in projects.values()
        ],
        "site_visit_id": visit.id,
        "meeting_id": meeting.id,
        "task_ids": task_ids,
    }


async def bootstrap_org() -> dict:
    """Bootstrap the whole initial organisation and return the manifest."""
    async with AsyncSessionLocal() as db:
        await seed_org_levels(db)
        await seed_departments(db)
        await seed_settings(db)
        await seed_holidays(db)
        await seed_superuser(db)
        ceo = await _update_ceo(db)
        users_by_key, employees = await _create_employees(db, ceo)
        business = await _seed_business_data(db, ceo, users_by_key)
        await seed_leave_balances(db)
        await db.commit()

    employees.sort(key=lambda e: e["login_id"])
    return {
        "ceo": dict(
            id=ceo.id, login_id=ceo.login_id, name=ceo.name, email=ceo.email, password="Studio@2026"
        ),
        "employees": employees,
        **business,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(asyncio.run(bootstrap_org()), indent=2))
