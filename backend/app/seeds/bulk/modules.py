"""Generate test data for ALL modules: tasks, expenses, invoices, meetings,
notices, leaves, attendance, site visits, and salary components.

Pure-Python — no database calls.  All generators take the employee and
project lists produced by ``employees.generate_employees()`` and
``projects.generate_projects()``.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from random import Random

_rng = Random(42)

TODAY = date.today()
NOW = datetime.now()

# ── Helpers ─────────────────────────────────────────────────────────────

def _pick(ls: list, n: int = 1):
    return _rng.choice(ls) if n == 1 else _rng.sample(ls, min(n, len(ls)))

def _date_range(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)
    return days

def _weekdays(start: date, end: date) -> list[date]:
    return [d for d in _date_range(start, end) if d.weekday() < 5]

# ── Salary Components ───────────────────────────────────────────────────

CTC_BY_LEVEL = {
    "L2": (1800000, 2800000),
    "L3": (1200000, 2000000),
    "L4": (800000, 1400000),
    "L5": (500000, 1000000),
    "L6": (200000, 360000),
}

def generate_salary_components(employees: list[dict]) -> list[dict]:
    results = []
    for emp in employees:
        if emp["level"] == "L6":
            continue
        low, high = CTC_BY_LEVEL[emp["level"]]
        ctc = Decimal(str(_rng.randint(low, high)))
        basic = (ctc * Decimal("0.40")).quantize(Decimal("0.01"))
        hra = (ctc * Decimal("0.20")).quantize(Decimal("0.01"))
        pf = (basic * Decimal("0.12")).quantize(Decimal("0.01"))
        special = ctc - basic - hra - pf
        results.append({
            "employee_name": emp["name"],
            "ctc_annual": ctc,
            "basic": basic,
            "hra": hra,
            "special_allowance": special,
            "pf_deduction": pf,
            "bank_name": _rng.choice(["HDFC Bank", "ICICI Bank", "SBI", "Kotak Mahindra"]),
            "account_number": f"50100{_rng.randint(10000000, 99999999)}",
            "ifsc_code": f"HDFC{_rng.randint(1000, 9999)}",
            "effective_from": emp["date_of_joining"],
        })
    return results

# ── Tasks ───────────────────────────────────────────────────────────────

TASK_TITLES = [
    "Prepare schematic design", "Develop floor plan options",
    "Structural BIM coordination", "MEP coordination drawings",
    "Interior concept mood boards", "Furniture layout plan",
    "3D exterior render", "3D walkthrough animation",
    "Construction drawing set", "Site survey report",
    "Material quantity estimation", "Client presentation deck",
    "Facade design options", "Landscape design concept",
    "Fire safety compliance review", "Building code compliance check",
    "Energy modeling simulation", "Acoustic panel layout",
    "Lighting design development", "Signage and wayfinding plan",
    "Drainage plan development", "Irrigation system layout",
    "Parking layout optimization", "Slab casting supervision",
    "Plumbing rough-in review", "Electrical conduit layout",
    "HVAC zone planning", "FF&E specification document",
    "Material and finish schedule", "Demolition plan preparation",
]

PRIORITIES = ["high", "urgent", "medium", "low"]
STATUSES_TASK = ["todo", "in_progress", "review", "done"]

def generate_tasks(employees: list[dict], projects: list[dict]) -> list[dict]:
    active_projects = [p for p in projects if p["status"] not in ("completed", "cancelled", "on_hold")]
    results = []
    task_id = 1
    for proj in active_projects:
        n_tasks = _rng.randint(3, 7)
        assignees = _pick(employees, n=min(5, len(employees)))
        for _ in range(n_tasks):
            assignee = _pick(assignees)
            assigner = _pick([e for e in employees if e["level"] in ("L2", "L3") and e["department"] == assignee["department"]] or employees[:5])
            start = TODAY - timedelta(days=_rng.randint(5, 60))
            due = start + timedelta(days=_rng.randint(7, 45))
            status = _pick(STATUSES_TASK)
            est = Decimal(str(_rng.choice([8, 12, 16, 20, 24, 32, 40, 60])))
            actual = est + Decimal(str(_rng.randint(-4, 8))) if status == "DONE" else None
            results.append({
                "title": f"{_pick(TASK_TITLES)} - {proj['name'][:30]}",
                "description": f"Task for {proj['name']} project",
                "project_name": proj["name"],
                "assigned_to_name": assignee["name"],
                "assigned_by_name": assigner["name"],
                "priority": _pick(PRIORITIES),
                "status": status,
                "start_date": start,
                "due_date": due,
                "estimated_hours": est,
                "actual_hours": actual,
                "tags": [_rng.choice(["design", "bim", "residential", "commercial", "interior", "site"])],
            })
            task_id += 1
    return results

# ── Expenses ────────────────────────────────────────────────────────────

EXPENSE_DESCS = [
    ("Site visit cab fare", "travel"),
    ("Material sample procurement", "material"),
    ("Software subscription renewal", "software"),
    ("Office supplies purchase", "office"),
    ("Printed presentation boards", "printing"),
    ("Team lunch celebration", "other"),
    ("Survey equipment rental", "other"),
    ("Model making material", "material"),
    ("Client dinner expenses", "other"),
    ("Conference registration fee", "other"),
    ("Travel expenses - client meeting", "travel"),
    ("Printer paper and ink", "office"),
]

EXPENSE_STATUSES = ["approved", "approved", "approved", "pending", "pending", "rejected"]

def generate_expenses(employees: list[dict], projects: list[dict]) -> list[dict]:
    active_projects = [p for p in projects if p["status"] not in ("cancelled",)]
    results = []
    non_interns = [e for e in employees if e["level"] != "L6"]
    for _ in range(200):
        desc, cat = _pick(EXPENSE_DESCS)
        proj = _rng.choice(active_projects + [None] * 3)
        payer = _pick(non_interns)
        amt = Decimal(str(_rng.randint(500, 50000)))
        d = TODAY - timedelta(days=_rng.randint(1, 180))
        results.append({
            "description": f"{desc} - {proj['name'][:20] if proj else 'Office'}",
            "category": cat,
            "amount": amt,
            "expense_date": d,
            "project_name": proj["name"] if proj else None,
            "paid_by_name": payer["name"],
            "status": _pick(EXPENSE_STATUSES),
        })
    return results

# ── Invoices ────────────────────────────────────────────────────────────

INVOICE_STATUSES = ["paid", "sent", "partial", "draft"]

def generate_invoices(clients: list[dict], projects: list[dict]) -> list[dict]:
    active_projects = [p for p in projects if p["status"] not in ("cancelled", "draft")]
    results = []
    for i, proj in enumerate(active_projects[:15]):
        client = clients[proj["client_idx"]]
        inv_num = f"INV-2026-{i + 1:03d}"
        inv_date = TODAY - timedelta(days=_rng.randint(5, 120))
        due = inv_date + timedelta(days=45)
        n_items = _rng.randint(1, 4)
        items = []
        for _ in range(n_items):
            rate = Decimal(str(_rng.choice([150000, 225000, 375000, 500000, 750000, 1000000, 1500000])))
            items.append({
                "description": _pick([
                    "Schematic Design Phase", "Design Development Phase",
                    "Construction Drawings", "3D Visualization Package",
                    "BIM Modelling Services", "MEP Coordination",
                    "Interior Concept Design", "Detailed Design & Drawings",
                ]),
                "quantity": Decimal("1"),
                "rate": rate,
            })
        subtotal = sum(it["quantity"] * it["rate"] for it in items)
        tax = (subtotal * Decimal("18") / Decimal("100")).quantize(Decimal("0.01"))
        status = _pick(INVOICE_STATUSES)
        paid = subtotal + tax if status == "paid" else (subtotal * Decimal("0.5")) if status == "partial" else Decimal("0")
        results.append({
            "invoice_number": inv_num,
            "client_name": client["name"],
            "project_name": proj["name"],
            "invoice_date": inv_date,
            "due_date": due,
            "items": items,
            "subtotal": subtotal,
            "tax_percent": Decimal("18.00"),
            "tax_amount": tax,
            "total": subtotal + tax,
            "status": status,
            "paid_amount": paid.quantize(Decimal("0.01")),
            "payment_date": inv_date + timedelta(days=_rng.randint(5, 30)) if status == "paid" else None,
        })
    return results

# ── Meetings ────────────────────────────────────────────────────────────

MEETING_TITLES = [
    "Weekly Design Review", "Client Presentation",
    "Site Coordination Meeting", "Project Kickoff",
    "Monthly All-Hands", "BIM Coordination",
    "Material Selection Review", "Budget Review",
    "Safety Briefing", "Team Standup",
]

MEETING_TYPES = ["internal", "client"]
MEETING_STATUSES = ["completed", "completed", "scheduled"]

def generate_meetings(employees: list[dict], projects: list[dict]) -> list[dict]:
    non_interns = [e for e in employees if e["level"] != "L6"]
    results = []
    for month_offset in range(12):
        base = date(TODAY.year, TODAY.month, 1) - timedelta(days=30 * month_offset)
        n = _rng.randint(3, 5)
        for _ in range(n):
            organizer = _pick(non_interns)
            attendees = _pick(non_interns, n=_rng.randint(2, 6))
            day_offset = _rng.randint(0, 28)
            sched = datetime.combine(
                base + timedelta(days=day_offset),
                time(_rng.choice([9, 10, 11, 14, 15, 16]), _rng.choice([0, 30])),
            )
            status = _pick(MEETING_STATUSES)
            past = sched < NOW
            if past and status == "scheduled":
                status = "completed"
            if not past and status == "completed":
                status = "scheduled"
            results.append({
                "title": f"{_pick(MEETING_TITLES)} - {organizer['department']}",
                "description": f"Monthly meeting for {organizer['department']}",
                "meeting_type": _pick(MEETING_TYPES),
                "scheduled_at": sched,
                "duration_minutes": _pick([30, 45, 60, 90, 120]),
                "location": _pick(["Studio Conference Room", "Client Office", "Site", "Online"]),
                "status": status,
                "organizer_name": organizer["name"],
                "attendee_names": [a["name"] for a in attendees],
            })
    return results

# ── Notices ─────────────────────────────────────────────────────────────

NOTICE_TITLES = [
    "Office Timings Updated", "Team Outing Announcement",
    "New Software Training", "Holiday Notice",
    "Fire Drill Schedule", "New Policy Update",
    "Birthday Celebrations", "Studio Maintenance Notice",
    "Safety Protocol Update", "Client Visit Reminder",
]

def generate_notices(employees: list[dict]) -> list[dict]:
    admins = [e for e in employees if e["department"] == "Corporate / Administration"]
    creator = admins[0] if admins else employees[0]
    results = []
    for month_offset in range(12):
        base = date(TODAY.year, TODAY.month, 1) - timedelta(days=30 * month_offset)
        n = _rng.randint(1, 3)
        for _ in range(n):
            d = base + timedelta(days=_rng.randint(0, 28))
            results.append({
                "title": f"{_pick(NOTICE_TITLES)} ({d.strftime('%b %Y')})",
                "body": f"This is an important notice for the month of {d.strftime('%B %Y')}. Please read carefully and follow the instructions.",
                "importance": _pick(["high", "medium", "medium", "low"]),
                "is_pinned": _rng.random() < 0.3,
                "publish_date": d,
                "expiry_date": d + timedelta(days=_rng.choice([14, 30, 60, 90])),
                "created_by_name": creator["name"],
            })
    return results

# ── Leaves ──────────────────────────────────────────────────────────────

LEAVE_TYPES = ["casual", "sick", "earned", "work_from_home"]
LEAVE_REASONS = [
    "Family function", "Medical appointment", "Personal work",
    "Family vacation", "Home renovation", "Child's school event",
    "Not feeling well", "Doctor consultation", "Bank work",
    "Out of town", "Wedding ceremony", "Religious occasion",
]
LEAVE_STATUSES = ["approved", "approved", "approved", "pending", "rejected"]

def generate_leaves(employees: list[dict]) -> list[dict]:
    non_interns = [e for e in employees if e["level"] != "L6"]
    results = []
    for emp in employees:
        n_leaves = _rng.randint(0, 4)
        for _ in range(n_leaves):
            start = TODAY + timedelta(days=_rng.randint(-90, 60))
            dur = _rng.choice([1, 1, 1, 2, 2, 3])
            end = start + timedelta(days=dur - 1)
            status = _pick(LEAVE_STATUSES)
            approver = _pick(non_interns)
            results.append({
                "employee_name": emp["name"],
                "leave_type": _pick(LEAVE_TYPES),
                "from_date": start,
                "to_date": end,
                "total_days": Decimal(str(dur)),
                "reason": _pick(LEAVE_REASONS),
                "status": status,
                "approved_by_name": approver["name"] if status != "PENDING" else None,
            })
    return results

# ── Attendance ──────────────────────────────────────────────────────────

def generate_attendance(employees: list[dict]) -> list[dict]:
    start = TODAY - timedelta(days=90)
    days = _weekdays(start, TODAY)
    results = []
    for emp in employees:
        join = emp["date_of_joining"]
        for d in days:
            if d < join:
                continue
            if _rng.random() < 0.05:
                continue  # absent
            check_in_h = 8
            check_in_m = _rng.randint(40, 59)
            late = check_in_h * 60 + check_in_m > 9 * 60 + 15
            check_out_h = 17
            check_out_m = _rng.randint(40, 59)
            ci = datetime.combine(d, time(check_in_h, check_in_m))
            co = datetime.combine(d, time(check_out_h, check_out_m))
            total = Decimal(str(round((co - ci).total_seconds() / 3600, 2)))
            results.append({
                "employee_name": emp["name"],
                "date": d,
                "check_in_time": ci,
                "check_out_time": co,
                "status": "late" if late else "present",
                "late_minutes": max(0, check_in_h * 60 + check_in_m - 555),
                "total_hours": total,
            })
    return results

# ── Site Visits ─────────────────────────────────────────────────────────

SITE_PURPOSES = [
    "Foundation inspection", "Slab casting supervision",
    "Plumbing rough-in review", "Electrical inspection",
    "Interior fit-out progress check", "Landscape installation review",
    "Structural audit", "Fire safety inspection",
    "MEP coordination visit", "Client walkthrough",
]

def generate_site_visits(employees: list[dict], projects: list[dict]) -> list[dict]:
    active = [p for p in projects if p["status"] not in ("completed", "cancelled", "draft")]
    non_interns = [e for e in employees if e["level"] != "L6"]
    results = []
    for _ in range(80):
        proj = _pick(active)
        creator = _pick(non_interns)
        d = TODAY - timedelta(days=_rng.randint(1, 180))
        sh = _rng.choice([8, 9, 10, 11])
        eh = sh + _rng.choice([1, 2, 3])
        results.append({
            "project_name": proj["name"],
            "visit_date": d,
            "start_time": time(sh, _rng.choice([0, 30])),
            "end_time": time(eh, _rng.choice([0, 30])),
            "status": "completed" if d < TODAY else "scheduled",
            "purpose": _pick(SITE_PURPOSES),
            "notes": f"Site visit notes for {proj['name']} on {d}. Observations recorded.",
            "location": proj["location"],
            "weather": _pick(["Sunny", "Overcast", "Rainy", "Humid", None]),
            "created_by_name": creator["name"],
        })
    return results


def generate_all_modules(
    employees: list[dict],
    projects: list[dict],
    clients: list[dict],
) -> dict:
    """Generate test data for all remaining modules."""
    return {
        "salary_components": generate_salary_components(employees),
        "tasks": generate_tasks(employees, projects),
        "expenses": generate_expenses(employees, projects),
        "invoices": generate_invoices(clients, projects),
        "meetings": generate_meetings(employees, projects),
        "notices": generate_notices(employees),
        "leaves": generate_leaves(employees),
        "attendance": generate_attendance(employees),
        "site_visits": generate_site_visits(employees, projects),
    }
