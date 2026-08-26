"""Generate ~1 year of timesheet data for 100 employees.

Pure-Python — no database calls.  Returns lists of dicts matching
Timesheet, TimesheetEntry, and TimesheetDay model columns.

Date range: 2025-09-01 to 2026-08-31 (52 weeks).
"""

from __future__ import annotations

from datetime import date, timedelta
from random import Random

_rng = Random(42)

# ── Constants ───────────────────────────────────────────────────────────
RANGE_START = date(2025, 9, 1)
RANGE_END = date(2026, 8, 31)

# Indian public holidays within our range (fixed + some festivals)
HOLIDAYS: set[date] = {
    date(2025, 9, 5),    # Ganesh Chaturthi
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 21),  # Dussehra
    date(2025, 11, 1),   # Diwali
    date(2025, 11, 5),   # Diwali (day after)
    date(2025, 12, 25),  # Christmas
    date(2026, 1, 1),    # New Year
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 10),   # Holi
    date(2026, 3, 30),   # Eid
    date(2026, 4, 14),   # Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 8, 15),   # Independence Day
}

# Project indices (0-based) for分配 work — employees work on 1-3 projects
_PROJECT_POOLS: list[list[int]] = [
    [0, 2, 6],      # Architecture staff
    [1, 4, 12],     # Interior staff
    [8, 12],         # Landscape staff
    [1, 4, 7],       # BIM staff
    [0, 5, 8],       # Project & Site staff
    [3, 6, 9],       # Business staff
]

# Realistic work descriptions per project type
_DESCRIPTIONS: dict[str, list[str]] = {
    "residential": [
        "Floor plan review and revision",
        "Structural drawing coordination",
        "Client presentation preparation",
        "Material selection and sample review",
        "Site visit and progress check",
        "Landscape sketch development",
        "Kitchen and bathroom detail drawings",
        "MEP coordination meeting",
        "Construction drawing set update",
        "Vastu compliance review",
    ],
    "commercial": [
        "Façade design development",
        "Fire safety compliance review",
        "HVAC layout coordination",
        "Parking layout optimization",
        "Building code compliance check",
        "Lobby and entrance design",
        "Signage and wayfinding plan",
        "Structural system selection",
        "Energy modeling review",
        "Contractor coordination",
    ],
    "interior": [
        "Mood board and palette development",
        "Furniture layout finalization",
        "FF&E specification document",
        "Material and finish schedule",
        "Lighting design review",
        "Custom joinery detail drawings",
        "Color palette client presentation",
        "Vendor coordination for fixtures",
        "3D walkthrough update",
        "On-site installation supervision",
    ],
    "landscape": [
        "Plant species selection research",
        "Hardscape material specification",
        "Irrigation system layout",
        "Drainage plan development",
        "Outdoor lighting design",
        "Tree survey and preservation plan",
        "Play area design concept",
        "Pathway and circulation design",
        "Maintenance schedule document",
        "Site grading plan review",
    ],
    "institutional": [
        "Building code and ADA compliance",
        "Classroom layout optimization",
        "Safety egress planning",
        "Acoustic panel layout",
        "HVAC zone planning",
        "Furniture procurement list",
        "Signage and wayfinding design",
        "Assembly area design",
    ],
    "mixed_use": [
        "Zoning and mixed-use compliance",
        "Podium level planning",
        "Residential vs commercial separation",
        "Common area design",
        "Parking structure coordination",
        "Retail frontage design",
    ],
    "renovation": [
        "Existing condition survey",
        "Demolition plan preparation",
        "Structural assessment review",
        "Before/after documentation",
        "Heritage compliance check",
        "MEP rerouting plan",
    ],
    "commercial_fallback": [
        "Office layout optimization",
        "Conference room AV design",
        "Reception and lobby concept",
        "Workstation specification",
    ],
}

# ── Status distribution logic ──────────────────────────────────────────

def _week_status(week_monday: date, today: date) -> str:
    """Determine timesheet status based on how far in the past the week is."""
    weeks_ago = (today - week_monday).days // 7
    if weeks_ago < 0:
        return "draft"       # future week (shouldn't happen but safe)
    if weeks_ago == 0:
        return "draft"       # current week
    if weeks_ago <= 2:
        return "submitted"   # last 1-2 weeks
    if weeks_ago <= 4:
        # Mix of submitted/approved
        return _rng.choice(["submitted", "approved", "approved"])
    # Past: mostly approved, rare rejection
    roll = _rng.random()
    if roll < 0.02:
        return "rejected"
    if roll < 0.05:
        return "submitted"
    return "approved"


def _monday(d: date) -> date:
    """Return the Monday of the week containing *d*."""
    return d - timedelta(days=d.weekday())


def _working_days_in_week(monday: date) -> list[date]:
    """Return Mon-Fri dates in the week, excluding holidays."""
    days = []
    for offset in range(5):
        d = monday + timedelta(days=offset)
        if d not in HOLIDAYS and RANGE_START <= d <= RANGE_END:
            days.append(d)
    return days


def _hours_for_day(rng: Random) -> float:
    """Generate realistic daily hours (mostly 8, occasionally 6-9)."""
    roll = rng.random()
    if roll < 0.05:
        return 0.0  # leave day
    if roll < 0.12:
        return rng.choice([6.0, 6.5, 7.0])
    if roll < 0.20:
        return rng.choice([8.5, 9.0, 9.5])
    return 8.0


def _pick_project(employee_idx: int) -> int:
    """Pick a project index for an employee (0-based into PROJECTS list)."""
    pool_idx = employee_idx % len(_PROJECT_POOLS)
    pool = _PROJECT_POOLS[pool_idx]
    return _rng.choice(pool)


def _description_for_project(project_idx: int) -> str:
    """Get a realistic description based on project type."""
    # Map project index to project type (from projects.py)
    project_types = [
        "residential", "commercial", "interior", "residential",
        "residential", "interior", "commercial", "residential",
        "institutional", "renovation", "residential", "commercial",
        "landscape", "interior", "mixed_use", "institutional",
        "residential", "commercial", "residential", "commercial",
        "landscape", "residential", "renovation", "commercial",
        "residential",
    ]
    ptype = project_types[project_idx % len(project_types)]
    descs = _DESCRIPTIONS.get(ptype, _DESCRIPTIONS["commercial_fallback"])
    return _rng.choice(descs)


def generate_timesheets(
    employees: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Generate timesheets, entries, and days for all employees.

    Returns (timesheets, entries, days) — each a list of dicts.
    """
    today = date.today()
    all_timesheets: list[dict] = []
    all_entries: list[dict] = []
    all_days: list[dict] = []

    # Employee join dates determine their start week
    join_dates = [e["date_of_joining"] for e in employees]

    ts_id = 1
    entry_id = 1
    day_id = 1

    for emp_idx, emp in enumerate(employees):
        join = join_dates[emp_idx]
        emp_start = max(_monday(join), RANGE_START)
        emp_start = _monday(emp_start)  # ensure Monday

        current = emp_start
        while current <= RANGE_END:
            days = _working_days_in_week(current)
            if not days:
                current += timedelta(days=7)
                continue

            status = _week_status(current, today)

            # Build timesheet dict
            ts = {
                "id": ts_id,
                "emp_idx": emp_idx,        # maps to employee list index
                "week_start": current,
                "status": status,
                "submitted_at": None,
                "approved_by_emp_idx": None,
                "approved_at": None,
                "rejection_reason": None,
            }

            if status == "submitted":
                ts["submitted_at"] = current + timedelta(
                    days=_rng.randint(4, 6), hours=_rng.randint(9, 17)
                )
            elif status == "approved":
                ts["submitted_at"] = current + timedelta(
                    days=_rng.randint(4, 6), hours=_rng.randint(9, 17)
                )
                ts["approved_at"] = ts["submitted_at"] + timedelta(
                    days=_rng.randint(1, 5), hours=_rng.randint(9, 17)
                )
                # Approver = reporting manager (resolved at DB insert time)
                ts["approved_by_emp_idx"] = None  # resolved later
            elif status == "rejected":
                ts["submitted_at"] = current + timedelta(
                    days=_rng.randint(4, 6), hours=_rng.randint(9, 17)
                )
                ts["rejection_reason"] = _rng.choice([
                    "Missing project descriptions",
                    "Hours exceed expected daily limit",
                    "Please resubmit with correct project codes",
                ])

            all_timesheets.append(ts)

            # Build entries and days for this timesheet
            for day_date in days:
                hours = _hours_for_day(_rng)
                project_idx = _pick_project(emp_idx)

                if hours > 0:
                    entry = {
                        "id": entry_id,
                        "timesheet_id": ts_id,
                        "project_idx": project_idx,
                        "date": day_date,
                        "hours": hours,
                        "location": _rng.choice(["", "Office", "Site", "WFH"]),
                        "description": _description_for_project(project_idx),
                    }
                    all_entries.append(entry)
                    entry_id += 1

                # TimesheetDay row (one per working day, even leaves)
                day_status = status if status != "rejected" else "submitted"
                day_row = {
                    "id": day_id,
                    "timesheet_id": ts_id,
                    "date": day_date,
                    "status": day_status,
                    "submitted_at": ts["submitted_at"] if day_status != "draft" else None,
                    "approved_by_emp_idx": ts["approved_by_emp_idx"] if day_status == "approved" else None,
                    "approved_at": ts["approved_at"] if day_status == "approved" else None,
                    "rejection_reason": ts["rejection_reason"] if day_status == "rejected" else None,
                }
                all_days.append(day_row)
                day_id += 1

            ts_id += 1
            current += timedelta(days=7)

    return all_timesheets, all_entries, all_days
