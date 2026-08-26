"""Comprehensive Supabase seed script.

Run:  python scripts/seed_supabase.py
Idempotent: skips records that already exist.

Requires DATABASE_URL environment variable (or .env file).
Superadmin password read from FIRST_SUPERUSER_PASSWORD env var.
"""

import asyncio
import json
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")

import asyncpg
import bcrypt

DSN = os.environ.get("DATABASE_URL", "")
if not DSN:
    print("ERROR: DATABASE_URL environment variable is required.")
    print("  Set it in your shell or in the backend/.env file.")
    sys.exit(1)

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = date.today()
YEAR = TODAY.year


def hp(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


DEPARTMENTS = [
    ("Design Team", "Conceptual, schematic and detail design"),
    ("Technical / Drafting Team", "CAD/BIM operators, structural & MEP coordination"),
    ("Visualization / 3D Team", "3D modelling, rendering and animation"),
    ("Project Management", "Project coordinators and site supervisors"),
    ("Site Team", "Site engineers and supervisors"),
    ("Business Development", "Client relations and marketing"),
    ("Administration", "HR, finance/accounts, office management"),
    ("Interns", "Design and technical interns"),
]

EMPLOYEES = [
    (
        "admin@studioerp.dev",
        "Studio Owner",
        "EMP-001",
        "Administration",
        "Principal Architect",
        "super_admin",
        "2020-01-15",
        "1985-06-20",
        "male",
        "O+",
        None,
    ),
    (
        "aisha.verma@studioerp.dev",
        "Aisha Verma",
        "EMP-002",
        "Design Team",
        "Junior Architect",
        "employee",
        "2023-03-10",
        "1998-11-05",
        "female",
        "B+",
        "admin@studioerp.dev",
    ),
    (
        "rohan.mehta@studioerp.dev",
        "Rohan Mehta",
        "EMP-003",
        "Technical / Drafting Team",
        "BIM Coordinator",
        "employee",
        "2022-07-01",
        "1996-04-12",
        "male",
        "A+",
        "admin@studioerp.dev",
    ),
    (
        "priya.nair@studioerp.dev",
        "Priya Nair",
        "EMP-004",
        "Visualization / 3D Team",
        "3D Visualizer",
        "employee",
        "2023-06-15",
        "1997-09-23",
        "female",
        "AB+",
        "admin@studioerp.dev",
    ),
    (
        "karan.singh@studioerp.dev",
        "Karan Singh",
        "EMP-005",
        "Project Management",
        "Project Coordinator",
        "employee",
        "2021-11-20",
        "1994-02-14",
        "male",
        "B-",
        "admin@studioerp.dev",
    ),
    (
        "neha.joshi@studioerp.dev",
        "Neha Joshi",
        "EMP-006",
        "Design Team",
        "Senior Architect",
        "project_lead",
        "2021-04-05",
        "1993-07-30",
        "female",
        "A-",
        "admin@studioerp.dev",
    ),
    (
        "vikram.patel@studioerp.dev",
        "Vikram Patel",
        "EMP-007",
        "Site Team",
        "Site Engineer",
        "employee",
        "2022-09-12",
        "1995-01-18",
        "male",
        "O-",
        "karan.singh@studioerp.dev",
    ),
    (
        "ananya.reddy@studioerp.dev",
        "Ananya Reddy",
        "EMP-008",
        "Business Development",
        "BD Manager",
        "admin",
        "2022-01-10",
        "1994-08-11",
        "female",
        "B+",
        "admin@studioerp.dev",
    ),
    (
        "deepak.kumar@studioerp.dev",
        "Deepak Kumar",
        "EMP-009",
        "Visualization / 3D Team",
        "Senior Visualizer",
        "project_lead",
        "2021-06-20",
        "1992-12-05",
        "male",
        "A+",
        "admin@studioerp.dev",
    ),
    (
        "meera.iyer@studioerp.dev",
        "Meera Iyer",
        "EMP-010",
        "Administration",
        "HR & Accounts",
        "admin",
        "2021-03-15",
        "1995-03-22",
        "female",
        "O+",
        "admin@studioerp.dev",
    ),
    (
        "arjun.gupta@studioerp.dev",
        "Arjun Gupta",
        "EMP-011",
        "Technical / Drafting Team",
        "CAD Operator",
        "employee",
        "2024-01-08",
        "2000-06-15",
        "male",
        "B+",
        "rohan.mehta@studioerp.dev",
    ),
    (
        "sara.khan@studioerp.dev",
        "Sara Khan",
        "EMP-012",
        "Design Team",
        "Interior Designer",
        "employee",
        "2023-08-20",
        "1999-04-08",
        "female",
        "AB-",
        "neha.joshi@studioerp.dev",
    ),
    (
        "rahul.desai@studioerp.dev",
        "Rahul Desai",
        "EMP-013",
        "Site Team",
        "Site Supervisor",
        "employee",
        "2023-02-14",
        "1996-10-27",
        "male",
        "A-",
        "karan.singh@studioerp.dev",
    ),
    (
        "kavya.menon@studioerp.dev",
        "Kavya Menon",
        "EMP-014",
        "Design Team",
        "Landscape Architect",
        "employee",
        "2024-04-01",
        "2001-01-12",
        "female",
        "B-",
        "neha.joshi@studioerp.dev",
    ),
    (
        "intern.rahul@studioerp.dev",
        "Rahul Sharma",
        "INT-001",
        "Interns",
        "Design Intern",
        "intern",
        "2025-06-01",
        "2002-08-19",
        "male",
        "O+",
        "aisha.verma@studioerp.dev",
    ),
    (
        "intern.pooja@studioerp.dev",
        "Pooja Deshmukh",
        "INT-002",
        "Interns",
        "Technical Intern",
        "intern",
        "2025-06-01",
        "2003-02-28",
        "female",
        "A+",
        "arjun.gupta@studioerp.dev",
    ),
]

CLIENTS = [
    (
        "Meera & Rajesh Sharma",
        "individual",
        None,
        None,
        "9822012345",
        "sharma.family@example.com",
        "referral",
        "1.5 - 2.5 Cr",
        "Residential villa",
    ),
    (
        "Skyline Developers",
        "developer",
        "Skyline Developers Pvt. Ltd.",
        "Anand Kulkarni",
        "9822098765",
        "anand@skyline.in",
        "website",
        "20 Cr+",
        "Mixed-use + commercial towers",
    ),
    (
        "Kaveri Art Gallery",
        "company",
        "Kaveri Arts",
        "Ritika Bose",
        "9822011223",
        "ritika@kaveriarts.in",
        "social",
        "80L - 1.2 Cr",
        "Interior fit-out for gallery + cafe",
    ),
    (
        "Pune Municipal Corporation",
        "government",
        "PMC",
        "Suresh Patil",
        "9822055667",
        "suresh.pmc@gov.in",
        "tender",
        "5 Cr+",
        "Urban planning and public spaces",
    ),
    (
        "Green Valley Homes",
        "developer",
        "Green Valley Builders",
        "Farhan Ahmad",
        "9822044556",
        "farhan@greenvalley.in",
        "referral",
        "8 - 12 Cr",
        "Residential township",
    ),
    (
        "The Leela Group",
        "company",
        "The Leela Palaces",
        "Shruti Kapoor",
        "9822077889",
        "shruti@theleela.com",
        "website",
        "15 Cr+",
        "Hospitality interior redesign",
    ),
]

PROJECTS = [
    (
        "Sharma Residence - Villa",
        "residential",
        "Villa",
        "Kothrud, Pune",
        4200,
        6800,
        "G+1",
        21000000,
        1575000,
        "percent",
        7.5,
        "in_construction",
        "high",
        0,
    ),
    (
        "Skyline Commercial Tower B",
        "commercial",
        "Office Tower",
        "Baner, Pune",
        18500,
        62000,
        "G+14",
        145000000,
        8700000,
        "percent",
        6,
        "under_review",
        "high",
        1,
    ),
    (
        "Kaveri Gallery Interiors",
        "interior",
        "Cultural Interior",
        "Koregaon Park, Pune",
        None,
        4600,
        "G",
        9800000,
        882000,
        "percent",
        9,
        "design",
        "medium",
        2,
    ),
    (
        "PMC Dhanakwadi Park",
        "landscape",
        "Public Park",
        "Dhanakwadi, Pune",
        35000,
        None,
        None,
        5200000,
        520000,
        "percent",
        10,
        "in_construction",
        "medium",
        3,
    ),
    (
        "Green Valley Township Phase 1",
        "residential",
        "Township",
        "Wagholi, Pune",
        85000,
        120000,
        "G+8",
        280000000,
        16800000,
        "percent",
        6,
        "concept",
        "high",
        4,
    ),
    (
        "Leela Heritage Wing",
        "interior",
        "Hospitality",
        "Koregaon Park, Pune",
        None,
        18500,
        "G+3",
        42000000,
        4200000,
        "percent",
        10,
        "design",
        "high",
        5,
    ),
    (
        "Sharma City Apartment",
        "residential",
        "Apartment",
        "Hinjewadi, Pune",
        1200,
        2400,
        "12th Floor",
        1800000,
        135000,
        "percent",
        7.5,
        "completed",
        "low",
        0,
    ),
    (
        "Skyline Tech Park",
        "commercial",
        "IT Park",
        "Hinjewadi Phase 3, Pune",
        45000,
        95000,
        "G+12",
        220000000,
        13200000,
        "percent",
        6,
        "in_construction",
        "high",
        1,
    ),
]

PHASES = {
    "residential": [
        "Concept",
        "Schematic Design",
        "Design Development",
        "Construction Drawings",
        "Approvals",
        "Construction Administration",
    ],
    "commercial": [
        "Concept",
        "Schematic Design",
        "Design Development",
        "Construction Drawings",
        "Approvals",
        "Construction Administration",
    ],
    "interior": [
        "Client Brief & Programme",
        "Concept Design",
        "Design Development",
        "Tender & Costing",
        "Execution & Site Works",
        "Handover & Aftercare",
    ],
    "landscape": [
        "Site Analysis",
        "Concept Design",
        "Design Development",
        "Planting & Material Specification",
        "Construction Documents",
        "Construction Administration",
    ],
}

TASK_TEMPLATES = [
    ("Site survey and measurements", "high", "done", 8),
    ("Prepare existing condition drawings", "high", "done", 16),
    ("Client brief document", "medium", "done", 4),
    ("Concept sketches - Option A", "high", "in_progress", 24),
    ("Concept sketches - Option B", "high", "in_progress", 24),
    ("Prepare presentation boards", "medium", "todo", 12),
    ("3D massing model", "medium", "todo", 16),
    ("Structural consultant coordination", "high", "todo", 8),
    ("MEP layout preliminary", "low", "todo", 12),
    ("Cost estimate review", "medium", "todo", 6),
    ("Building bylaw compliance check", "high", "todo", 8),
    ("Landscape concept design", "medium", "todo", 20),
    ("Interior material palette", "medium", "todo", 8),
    ("Furniture layout plan", "high", "todo", 12),
    ("Electrical layout - Ground Floor", "medium", "todo", 8),
    ("Plumbing layout - Ground Floor", "medium", "todo", 8),
    ("Section drawings", "high", "review", 16),
    ("Elevation design development", "high", "in_progress", 20),
    ("Drawing set QC review", "high", "todo", 4),
    ("Submission package preparation", "medium", "todo", 6),
]

INVOICES = [
    (
        0,
        0,
        "INV-2026-001",
        "2026-01-15",
        "2026-02-15",
        [("Concept Design - Phase 1", 1, 393750), ("Schematic Design - Phase 1", 1, 393750)],
        "paid",
        1.0,
    ),
    (
        0,
        0,
        "INV-2026-002",
        "2026-04-01",
        "2026-05-01",
        [("Design Development", 1, 393750)],
        "paid",
        1.0,
    ),
    (
        0,
        0,
        "INV-2026-003",
        "2026-07-01",
        "2026-08-01",
        [("Construction Drawings - Set 1", 1, 393750)],
        "sent",
        0.0,
    ),
    (
        1,
        1,
        "INV-2026-004",
        "2026-02-01",
        "2026-03-01",
        [("Concept & Schematic Design", 1, 2900000)],
        "paid",
        1.0,
    ),
    (
        1,
        1,
        "INV-2026-005",
        "2026-05-15",
        "2026-06-15",
        [("Design Development", 1, 2900000)],
        "partial",
        0.5,
    ),
    (
        2,
        2,
        "INV-2026-006",
        "2026-03-01",
        "2026-04-01",
        [("Concept Design", 1, 294000), ("Design Development", 1, 294000)],
        "paid",
        1.0,
    ),
    (
        2,
        2,
        "INV-2026-007",
        "2026-06-01",
        "2026-07-01",
        [("Tender & Costing", 1, 294000)],
        "overdue",
        0.0,
    ),
    (
        4,
        4,
        "INV-2026-008",
        "2026-05-01",
        "2026-06-01",
        [("Phase 1 - Concept", 1, 5600000)],
        "sent",
        0.0,
    ),
    (
        5,
        5,
        "INV-2026-009",
        "2026-03-15",
        "2026-04-15",
        [("Concept Design", 1, 1400000)],
        "paid",
        1.0,
    ),
    (
        5,
        5,
        "INV-2026-010",
        "2026-07-15",
        "2026-08-15",
        [("Design Development", 1, 1400000)],
        "draft",
        0.0,
    ),
]

EXPENSES = [
    (
        "printing",
        "Construction drawing prints - Sharma Residence",
        4500,
        0,
        "Karan Singh",
        "approved",
        10,
    ),
    ("software", "AutoCAD annual license renewal", 42000, None, "Meera Iyer", "approved", 30),
    ("travel", "Site visit travel - Kaveri Gallery", 1800, 2, "Vikram Patel", "approved", 5),
    ("material", "Model making materials", 3200, 0, "Aisha Verma", "approved", 8),
    ("printing", "Presentation boards - Skyline Tower", 8500, 1, "Rohan Mehta", "pending", 3),
    ("travel", "Client meeting travel - Green Valley", 2400, 4, "Ananya Reddy", "approved", 7),
    ("software", "Lumion Pro license", 35000, None, "Deepak Kumar", "approved", 45),
    ("office", "Studio supplies and stationery", 6800, None, "Meera Iyer", "approved", 12),
    ("subcontract", "Structural consultant - PMC Park", 150000, 3, "Karan Singh", "approved", 20),
    ("printing", "Tender document printing - Green Valley", 12000, 4, "Rahul Desai", "pending", 2),
]

HOLIDAYS = [
    ("Republic Day", f"{YEAR}-01-26"),
    ("Holi", f"{YEAR}-03-04"),
    ("Independence Day", f"{YEAR}-08-15"),
    ("Gandhi Jayanti", f"{YEAR}-10-02"),
    ("Diwali", f"{YEAR}-11-08"),
    ("Christmas", f"{YEAR}-12-25"),
    ("Makar Sankranti", f"{YEAR}-01-14"),
    ("Ambedkar Jayanti", f"{YEAR}-04-14"),
]

NOTICES = [
    (
        "Office Timing Update",
        "Starting August, office hours are 9:00 AM to 6:00 PM with a 1-hour lunch break. Please ensure punctual attendance.",
        "HIGH",
        True,
    ),
    (
        "Fire Safety Drill - August 25",
        "Mandatory fire safety drill scheduled for August 25 at 3:00 PM. All employees must participate.",
        "MEDIUM",
        False,
    ),
    (
        "New Project Kickoff: Green Valley",
        "We are pleased to announce a new township project with Green Valley Homes. Kickoff meeting on Monday.",
        "MEDIUM",
        True,
    ),
    (
        "Birthday Celebrations - August",
        "August birthdays: Deepak Kumar (Aug 12), Priya Nair (Aug 23). Cake cutting at 4 PM in the common area.",
        "LOW",
        False,
    ),
    (
        "Year-End Party Planning Committee",
        "Volunteers needed for the annual year-end party. Please contact Meera by end of this week.",
        "LOW",
        False,
    ),
]

MEETINGS = [
    (
        "Sharma Residence - Client Review",
        "CLIENT",
        "2026-08-20 10:00",
        60,
        "Studio Meeting Room 1",
        "SCHEDULED",
    ),
    (
        "Weekly Design Team Standup",
        "INTERNAL",
        "2026-08-18 09:30",
        30,
        "Design Studio",
        "SCHEDULED",
    ),
    (
        "Skyline Tower - Structural Review",
        "CLIENT",
        "2026-08-19 14:00",
        90,
        "Video - Google Meet",
        "SCHEDULED",
    ),
    (
        "Kaveri Gallery - Site Visit",
        "SITE",
        "2026-08-22 08:00",
        180,
        "Koregaon Park, Pune",
        "SCHEDULED",
    ),
    ("Monthly All-Hands", "INTERNAL", "2026-08-25 16:00", 60, "Main Conference Room", "SCHEDULED"),
    (
        "Green Valley - Concept Presentation",
        "CLIENT",
        "2026-08-26 11:00",
        120,
        "Video - Zoom",
        "SCHEDULED",
    ),
    (
        "Leela Heritage - Kickoff",
        "CLIENT",
        "2026-08-28 10:00",
        90,
        "The Leela Office, Pune",
        "SCHEDULED",
    ),
    (
        "Past: Design Review - Kaveri",
        "INTERNAL",
        "2026-08-10 15:00",
        60,
        "Studio Meeting Room 2",
        "COMPLETED",
    ),
    (
        "Past: PMC Park Progress Review",
        "INTERNAL",
        "2026-08-12 10:00",
        60,
        "Studio Meeting Room 1",
        "COMPLETED",
    ),
    ("Past: Weekly Standup", "INTERNAL", "2026-08-11 09:30", 30, "Design Studio", "COMPLETED"),
]

SALARY = {
    "super_admin": (2400000, 100000, 40000, 30000, 18000),
    "admin": (1500000, 62500, 25000, 20000, 18000),
    "project_lead": (1200000, 50000, 20000, 15000, 18000),
    "employee": (720000, 30000, 12000, 8000, 1800),
    "intern": (240000, 10000, 4000, 2000, 0),
}


# ── Seed functions ──


async def seed_departments(conn):
    for name, desc in DEPARTMENTS:
        await conn.execute(
            "INSERT INTO departments (name, description) VALUES ($1, $2) ON CONFLICT (name) DO NOTHING",
            name,
            desc,
        )
    print(f"  Departments: {len(DEPARTMENTS)}")


async def seed_employees(conn):
    dept_ids = {r["name"]: r["id"] for r in await conn.fetch("SELECT id, name FROM departments")}
    superadmin_pw = os.environ.get("FIRST_SUPERUSER_PASSWORD", "")
    if not superadmin_pw:
        print("ERROR: FIRST_SUPERUSER_PASSWORD environment variable is required.")
        sys.exit(1)
    pw_super = hp(superadmin_pw)
    pw_demo = hp("demo-pass-123")

    # Pre-compute YY#### login ids per joining-year cohort (order preserved).
    cohort_seq: dict[int, int] = {}
    login_ids: list[str] = []
    for row in EMPLOYEES:
        doj = date.fromisoformat(row[6]) if row[6] else TODAY
        year = doj.year
        seq = cohort_seq.get(year, 0) + 1
        cohort_seq[year] = seq
        login_ids.append(f"{year % 100:02d}{seq:04d}")

    taken = {
        r["login_id"]
        for r in await conn.fetch("SELECT login_id FROM users WHERE login_id IS NOT NULL")
    }
    used = set(taken)
    for idx, lid in enumerate(login_ids):
        while lid in used:
            year = (date.fromisoformat(EMPLOYEES[idx][6]) if EMPLOYEES[idx][6] else TODAY).year
            cohort_seq[year] += 1
            lid = f"{year % 100:02d}{cohort_seq[year]:04d}"
        login_ids[idx] = lid
        used.add(lid)

    for (email, name, eid, dept, desig, role, doj, dob, gender, blood, rpt), login_id in zip(
        EMPLOYEES, login_ids
    ):
        pw = pw_super if role == "super_admin" else pw_demo
        rpt_id = None
        if rpt:
            r = await conn.fetchrow("SELECT id FROM users WHERE email = $1", rpt)
            if r:
                rpt_id = r["id"]
        await conn.execute(
            """INSERT INTO users (email, login_id, name, employee_id, department_id, designation,
                   password_hash, date_of_joining, date_of_birth, gender, blood_group,
                   reporting_to_id, is_active, employment_type)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,true,$13)
               ON CONFLICT (email) DO NOTHING""",
            email,
            login_id,
            name,
            eid,
            dept_ids.get(dept),
            desig,
            pw,
            date.fromisoformat(doj) if doj else None,
            date.fromisoformat(dob) if dob else None,
            gender,
            blood,
            rpt_id,
            ("INTERNSHIP" if role == "intern" else "FULL_TIME"),
        )
    print(f"  Employees: {len(EMPLOYEES)}")


async def seed_settings(conn):
    data = [
        (
            "attendance",
            "working_hours",
            {"start": "09:00", "end": "18:00", "break_minutes": 60, "min_hours": 8},
        ),
        (
            "attendance",
            "late_policy",
            {
                "grace_minutes": 15,
                "late_threshold": "09:15",
                "half_day_threshold": "11:00",
                "three_late_equals_one_leave": True,
            },
        ),
        (
            "attendance",
            "working_days",
            {"monday_friday": "full", "saturday": "half", "sunday": "off"},
        ),
        ("attendance", "checkin_methods", {"web": True, "manual": True, "qr": False, "gps": False}),
        (
            "leave",
            "policy",
            {
                "casual": 12,
                "sick": 8,
                "earned": 15,
                "compensatory": 0,
                "maternity": 90,
                "paternity": 15,
                "work_from_home": 48,
                "unpaid": 0,
                "carry_forward": 5,
            },
        ),
        (
            "company",
            "profile",
            {
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
                "default_terms": "Payment due within 30 days of invoice date.",
            },
        ),
    ]
    for g, k, v in data:
        await conn.execute(
            'INSERT INTO settings ("group", key, value) VALUES ($1,$2,$3) ON CONFLICT ("group", key) DO NOTHING',
            g,
            k,
            json.dumps(v),
        )
    print(f"  Settings: {len(data)}")


async def seed_holidays(conn):
    for name, dt in HOLIDAYS:
        await conn.execute(
            "INSERT INTO holidays (name, date) VALUES ($1,$2) ON CONFLICT (date) DO NOTHING",
            name,
            date.fromisoformat(dt),
        )
    print(f"  Holidays: {len(HOLIDAYS)}")


async def seed_leave_balances(conn):
    users = await conn.fetch(
        "SELECT id FROM users WHERE is_active = true AND role != 'SUPER_ADMIN'"
    )
    alloc = {"CASUAL": 12, "SICK": 8, "EARNED": 15, "WORK_FROM_HOME": 48}
    count = 0
    for u in users:
        for lt, amt in alloc.items():
            await conn.execute(
                "INSERT INTO leave_balance (user_id, leave_type, year, allocated, used) VALUES ($1,$2,$3,$4,0) ON CONFLICT (user_id, leave_type, year) DO NOTHING",
                u["id"],
                lt,
                YEAR,
                amt,
            )
            count += 1
    print(f"  Leave balances: {count}")


async def seed_clients(conn):
    for name, ctype, company, contact, phone, email, source, budget, interest in CLIENTS:
        if email and await conn.fetchrow("SELECT id FROM clients WHERE email = $1", email):
            continue
        if not email and await conn.fetchrow("SELECT id FROM clients WHERE name = $1", name):
            continue
        await conn.execute(
            """INSERT INTO clients (name, client_type, company_name, contact_person, phone, email,
                   source, budget_range, interest, deal_stage, is_active)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'LEAD',true)""",
            name,
            ctype.upper(),
            company,
            contact,
            phone,
            email,
            source,
            budget,
            interest,
        )
    print(f"  Clients: {len(CLIENTS)}")


async def seed_projects(conn):
    lead = await conn.fetchrow(
        "SELECT id FROM users WHERE role = 'SUPER_ADMIN' AND is_active = true LIMIT 1"
    )
    lead_id = lead["id"] if lead else None
    cids = [r["id"] for r in await conn.fetch("SELECT id FROM clients ORDER BY id")]

    for idx, (name, pt, cat, loc, plot, built, fl, budget, fee, ft, fp, st, pri, ci) in enumerate(
        PROJECTS
    ):
        if await conn.fetchrow("SELECT id FROM projects WHERE name = $1", name):
            continue
        code = f"PRJ-{YEAR}-{idx + 1:03d}"
        pid = await conn.fetchval(
            """INSERT INTO projects (project_code, name, project_type, category, location,
                   plot_area, built_up_area, no_of_floors, budget, studio_fee,
                   fee_type, fee_percent, status, priority, client_id, project_lead_id, start_date, is_active)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,true) RETURNING id""",
            code,
            name,
            pt.upper(),
            cat,
            loc,
            plot,
            built,
            fl,
            budget,
            fee,
            ft,
            fp,
            st.upper(),
            pri.upper(),
            cids[ci] if ci < len(cids) else None,
            lead_id,
            date.fromisoformat(f"{YEAR}-01-15")
            if st.upper() not in ("DRAFT", "CONCEPT")
            else date.fromisoformat(f"{YEAR}-06-01"),
        )
        phases = PHASES.get(pt, PHASES["residential"])
        ps = (
            "COMPLETED"
            if st.upper() == "COMPLETED"
            else ("IN_PROGRESS" if st.upper() in ("DESIGN", "IN_CONSTRUCTION") else "NOT_STARTED")
        )
        for pi, pn in enumerate(phases):
            comp = 100 if ps == "completed" else (50 if pi == 0 and ps == "in_progress" else 0)
            sps = "COMPLETED" if comp == 100 else ("IN_PROGRESS" if comp > 0 else "NOT_STARTED")
            await conn.execute(
                "INSERT INTO project_phases (project_id, name, order_index, status, completion_pct) VALUES ($1,$2,$3,$4,$5)",
                pid,
                pn,
                pi,
                sps,
                comp,
            )
        emps = await conn.fetch(
            "SELECT id, designation FROM users WHERE role IN ('EMPLOYEE','PROJECT_LEAD') AND is_active = true"
        )
        random.seed(idx)
        for emp in random.sample(emps, min(5, len(emps))):
            await conn.execute(
                "INSERT INTO project_team (project_id, user_id, role) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
                pid,
                emp["id"],
                emp["designation"],
            )
    print(f"  Projects: {len(PROJECTS)}")


async def seed_tasks(conn):
    projs = await conn.fetch(
        "SELECT id, name FROM projects WHERE status NOT IN ('COMPLETED','CANCELLED') ORDER BY id"
    )
    users = await conn.fetch(
        "SELECT id FROM users WHERE role IN ('EMPLOYEE','PROJECT_LEAD') AND is_active = true"
    )
    count = 0
    for pi, proj in enumerate(projs):
        random.seed(pi * 7)
        for title, pri, st, est in random.sample(TASK_TEMPLATES, min(6, len(TASK_TEMPLATES))):
            assignee = random.choice(users)
            due = TODAY + timedelta(days=random.randint(5, 60))
            await conn.execute(
                """INSERT INTO tasks (title, project_id, assigned_to, assigned_by, priority, status,
                       start_date, due_date, estimated_hours) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
                f"{title} - {proj['name']}",
                proj["id"],
                assignee["id"],
                users[0]["id"],
                pri.upper(),
                st.upper(),
                TODAY - timedelta(days=random.randint(1, 14)),
                due,
                est,
            )
            count += 1
    print(f"  Tasks: {count}")


async def seed_invoices(conn):
    cids = [r["id"] for r in await conn.fetch("SELECT id FROM clients ORDER BY id")]
    pids = [r["id"] for r in await conn.fetch("SELECT id FROM projects ORDER BY id")]
    count = 0
    for ci, pi, num, idt, ddt, items, st, pp in INVOICES:
        if await conn.fetchrow("SELECT id FROM invoices WHERE invoice_number = $1", num):
            continue
        sub = sum(q * r for _, q, r in items)
        tax = round(sub * 18 / 100, 2)
        total = round(sub + tax, 2)
        paid = round(total * pp, 2)
        inv_id = await conn.fetchval(
            """INSERT INTO invoices (invoice_number, client_id, project_id, invoice_date, due_date,
                   subtotal, tax_percent, tax_amount, total, status, paid_amount, payment_date, payment_method)
               VALUES ($1,$2,$3,$4,$5,$6,18,$7,$8,$9,$10,$11,$12) RETURNING id""",
            num,
            cids[ci] if ci < len(cids) else None,
            pids[pi] if pi < len(pids) else None,
            date.fromisoformat(idt),
            date.fromisoformat(ddt),
            sub,
            tax,
            total,
            st.upper(),
            paid,
            date.fromisoformat(ddt) if pp > 0 else None,
            "BANK_TRANSFER" if pp > 0 else None,
        )
        for desc, qty, rate in items:
            await conn.execute(
                "INSERT INTO invoice_items (invoice_id, description, quantity, rate, amount) VALUES ($1,$2,$3,$4,$5)",
                inv_id,
                desc,
                qty,
                rate,
                qty * rate,
            )
        count += 1
    print(f"  Invoices: {count}")


async def seed_expenses(conn):
    pids = [r["id"] for r in await conn.fetch("SELECT id FROM projects ORDER BY id")]
    adm = await conn.fetchrow(
        "SELECT id FROM users WHERE role IN ('SUPER_ADMIN','ADMIN') AND is_active = true LIMIT 1"
    )
    aid = adm["id"] if adm else None
    for cat, desc, amt, pi, paid_by, st, ago in EXPENSES:
        if await conn.fetchrow(
            "SELECT id FROM expenses WHERE description = $1 AND amount = $2", desc, amt
        ):
            continue
        await conn.execute(
            """INSERT INTO expenses (category, description, amount, expense_date, project_id,
                   paid_by, status, approved_by, approved_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            cat,
            desc,
            amt,
            TODAY - timedelta(days=ago),
            pids[pi] if pi is not None and pi < len(pids) else None,
            paid_by,
            st.upper(),
            aid if st.upper() == "APPROVED" else None,
            datetime.now(IST) - timedelta(days=max(0, ago - 2))
            if st.upper() == "APPROVED"
            else None,
        )
    print(f"  Expenses: {len(EXPENSES)}")


async def seed_attendance(conn):
    users = await conn.fetch(
        "SELECT id FROM users WHERE is_active = true AND role != 'INTERN' ORDER BY id"
    )
    pats = [
        ("PRESENT", "09:00", 18, 0),
        ("PRESENT", "08:50", 18, 0),
        ("LATE", "09:20", 18, 20),
        ("LATE", "09:35", 18, 35),
        ("HALF_DAY", "11:05", 14, 125),
        ("WORK_FROM_HOME", "08:45", 18, 0),
    ]
    count = 0
    for u in users:
        random.seed(u["id"])
        for off in range(30, 0, -1):
            day = TODAY - timedelta(days=off)
            if day.weekday() >= 5:
                continue
            if await conn.fetchrow(
                "SELECT id FROM attendance WHERE user_id = $1 AND date = $2", u["id"], day
            ):
                continue
            st, ci_t, co_h, lm = random.choice(pats)
            ci_h, ci_m = (int(x) for x in ci_t.split(":"))
            ci_dt = datetime(day.year, day.month, day.day, ci_h, ci_m, tzinfo=IST)
            co_dt = datetime(day.year, day.month, day.day, co_h, 0, tzinfo=IST)
            ci_u = ci_dt.astimezone(timezone.utc)
            co_u = co_dt.astimezone(timezone.utc)
            th = round((co_u - ci_u).total_seconds() / 3600 - 1, 2)
            if th < 0:
                th = 0
            await conn.execute(
                """INSERT INTO attendance (user_id, date, check_in_time, check_out_time, status,
                       late_minutes, total_hours, check_in_method)                    VALUES ($1,$2,$3,$4,$5,$6,$7,'WEB')
                   ON CONFLICT (user_id, date) DO NOTHING""",
                u["id"],
                day,
                ci_u,
                co_u,
                st,
                lm,
                th,
            )
            count += 1
        if TODAY.weekday() < 5:
            if not await conn.fetchrow(
                "SELECT id FROM attendance WHERE user_id = $1 AND date = $2", u["id"], TODAY
            ):
                ci = datetime(
                    TODAY.year, TODAY.month, TODAY.day, 9, random.randint(0, 5), tzinfo=IST
                )
                await conn.execute(
                    "INSERT INTO attendance (user_id, date, check_in_time, status, late_minutes, check_in_method) VALUES ($1,$2,$3,'PRESENT',0,'WEB') ON CONFLICT (user_id, date) DO NOTHING",
                    u["id"],
                    TODAY,
                    ci.astimezone(timezone.utc),
                )
                count += 1
    print(f"  Attendance: {count}")


async def seed_leaves(conn):
    users = await conn.fetch(
        "SELECT id FROM users WHERE is_active = true AND role NOT IN ('SUPER_ADMIN','INTERN') ORDER BY id LIMIT 6"
    )
    ld = [
        ("CASUAL", 5, 1, "Family function out of town"),
        ("SICK", 2, 10, "Fever and cold"),
        ("EARNED", 4, 20, "Vacation travel to Kerala"),
        ("WORK_FROM_HOME", 1, 8, "Home renovation work"),
    ]
    adm = await conn.fetchrow("SELECT id FROM users WHERE role = 'SUPER_ADMIN' LIMIT 1")
    count = 0
    for i, u in enumerate(users):
        lt, days, ago, reason = ld[i % len(ld)]
        fd = TODAY - timedelta(days=ago)
        td = fd + timedelta(days=days - 1)
        if await conn.fetchrow(
            "SELECT id FROM leaves WHERE user_id = $1 AND from_date = $2", u["id"], fd
        ):
            continue
        st_val = "APPROVED" if ago > 3 else "PENDING"
        await conn.execute(
            """INSERT INTO leaves (user_id, leave_type, from_date, to_date, total_days, reason,
                   status, approved_by, approved_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            u["id"],
            lt,
            fd,
            td,
            days,
            reason,
            st_val,
            adm["id"] if st_val == "APPROVED" else None,
            datetime.now(IST) - timedelta(days=max(0, ago - 1)) if st_val == "APPROVED" else None,
        )
        count += 1
    print(f"  Leaves: {count}")


async def seed_notices(conn):
    adm = await conn.fetchrow("SELECT id FROM users WHERE role = 'SUPER_ADMIN' LIMIT 1")
    aid = adm["id"] if adm else None
    for title, body, imp, pinned in NOTICES:
        if await conn.fetchrow("SELECT id FROM notices WHERE title = $1", title):
            continue
        await conn.execute(
            "INSERT INTO notices (title, body, importance, is_pinned, is_active, publish_date, created_by) VALUES ($1,$2,$3,$4,true,$5,$6)",
            title,
            body,
            imp,
            pinned,
            TODAY,
            aid,
        )
    print(f"  Notices: {len(NOTICES)}")


async def seed_meetings(conn):
    adm = await conn.fetchrow("SELECT id FROM users WHERE role = 'SUPER_ADMIN' LIMIT 1")
    aid = adm["id"] if adm else None
    users = await conn.fetch("SELECT id FROM users WHERE is_active = true ORDER BY id")
    count = 0
    for title, mt, dt_str, dur, loc, st in MEETINGS:
        if await conn.fetchrow("SELECT id FROM meetings WHERE title = $1", title):
            continue
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
        mid = await conn.fetchval(
            """INSERT INTO meetings (title, meeting_type, scheduled_at, duration_minutes, location, status, organizer_id)
               VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id""",
            title,
            mt.upper(),
            dt.astimezone(timezone.utc),
            dur,
            loc,
            st.upper(),
            aid,
        )
        for u in random.sample(users, min(4, len(users))):
            await conn.execute(
                "INSERT INTO meeting_attendees (meeting_id, user_id, rsvp_status) VALUES ($1,$2,$3)",
                mid,
                u["id"],
                "ACCEPTED" if st.upper() == "COMPLETED" else "PENDING",
            )
        count += 1
    print(f"  Meetings: {count}")


async def seed_salary(conn):
    users = await conn.fetch("SELECT id, role FROM users WHERE is_active = true")
    count = 0
    for u in users:
        s = SALARY.get(u["role"].lower(), SALARY["employee"])
        if await conn.fetchrow("SELECT id FROM salary_components WHERE user_id = $1", u["id"]):
            continue
        await conn.execute(
            """INSERT INTO salary_components (user_id, ctc_annual, basic, hra, special_allowance, pf_deduction, effective_from)
               VALUES ($1,$2,$3,$4,$5,$6,$7)""",
            u["id"],
            *s,
            date(YEAR, 1, 1),
        )
        count += 1
    print(f"  Salary components: {count}")


# ── Main ──


async def main():
    print("Connecting to Supabase...")
    conn = await asyncpg.connect(dsn=DSN, timeout=30, statement_cache_size=0)
    try:
        print("Seeding...")
        await seed_departments(conn)
        await seed_employees(conn)
        await seed_settings(conn)
        await seed_holidays(conn)
        await seed_leave_balances(conn)
        await seed_clients(conn)
        await seed_projects(conn)
        await seed_tasks(conn)
        await seed_invoices(conn)
        await seed_expenses(conn)
        await seed_attendance(conn)
        await seed_leaves(conn)
        await seed_notices(conn)
        await seed_meetings(conn)
        await seed_salary(conn)
        print("\nDone! All demo data seeded.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
