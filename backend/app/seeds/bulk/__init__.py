"""Bulk test-data generator for the Offsite ERP.

Usage::

    from app.seeds.bulk import generate_all, export_json

    data = generate_all()
    export_json(data, "app/seeds/bulk/sample")
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from .employees import generate_employees
from .modules import generate_all_modules
from .projects import CLIENTS, generate_projects
from .timesheets import generate_timesheets


class _Encoder(json.JSONEncoder):
    """Serialize dates/datetimes/decimals for JSON output."""

    def default(self, o):
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, time):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def generate_all() -> dict:
    """Generate the full test dataset across ALL modules."""
    employees = generate_employees()
    projects = generate_projects()
    timesheets, entries, days = generate_timesheets(employees)
    modules = generate_all_modules(employees, projects, CLIENTS)

    data = {
        "clients": CLIENTS,
        "projects": projects,
        "employees": employees,
        "timesheets": timesheets,
        "entries": entries,
        "days": days,
    }
    data.update(modules)
    return data


def export_json(data: dict, output_dir: str | Path) -> None:
    """Write the full dataset as JSON files."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for key in ("clients", "projects", "employees"):
        with open(out / f"{key}.json", "w", encoding="utf-8") as f:
            json.dump(data[key], f, cls=_Encoder, indent=2, ensure_ascii=False)

    for key in ("salary_components", "tasks", "expenses", "invoices",
                "meetings", "notices", "leaves", "attendance", "site_visits"):
        with open(out / f"{key}.json", "w", encoding="utf-8") as f:
            json.dump(data[key], f, cls=_Encoder, indent=2, ensure_ascii=False)

    # Timesheets split by month
    ts_dir = out / "timesheets"
    ts_dir.mkdir(parents=True, exist_ok=True)
    by_month: dict[str, list] = {}
    for ts in data["timesheets"]:
        by_month.setdefault(ts["week_start"].strftime("%Y-%m"), []).append(ts)
    entries_by_ts: dict[int, list] = {}
    for e in data["entries"]:
        entries_by_ts.setdefault(e["timesheet_id"], []).append(e)
    days_by_ts: dict[int, list] = {}
    for d in data["days"]:
        days_by_ts.setdefault(d["timesheet_id"], []).append(d)
    for mk in sorted(by_month):
        month_data = []
        for ts in by_month[mk]:
            tc = {k: v for k, v in ts.items() if k != "emp_idx"}
            tc["entries"] = [{k: v for k, v in e.items() if k != "project_idx"}
                             for e in entries_by_ts.get(ts["id"], [])]
            tc["days"] = days_by_ts.get(ts["id"], [])
            month_data.append(tc)
        with open(ts_dir / f"{mk}.json", "w", encoding="utf-8") as f:
            json.dump(month_data, f, cls=_Encoder, indent=2, ensure_ascii=False)


def print_summary(data: dict) -> None:
    """Print a human-readable summary of the generated dataset."""
    print(f"Clients:            {len(data['clients'])}")
    print(f"Projects:           {len(data['projects'])}")
    print(f"Employees:          {len(data['employees'])}")
    print(f"Timesheets:         {len(data['timesheets'])}")
    print(f"Timesheet Entries:  {len(data['entries'])}")
    print(f"Timesheet Days:     {len(data['days'])}")
    print(f"Tasks:              {len(data['tasks'])}")
    print(f"Expenses:           {len(data['expenses'])}")
    print(f"Invoices:           {len(data['invoices'])}")
    print(f"Meetings:           {len(data['meetings'])}")
    print(f"Notices:            {len(data['notices'])}")
    print(f"Leaves:             {len(data['leaves'])}")
    print(f"Attendance:         {len(data['attendance'])}")
    print(f"Site Visits:        {len(data['site_visits'])}")
    print(f"Salary Components:  {len(data['salary_components'])}")

    ts = Counter(t["status"] for t in data["timesheets"])
    print(f"\nTimesheet statuses: {dict(ts)}")

    depts = Counter(e["department"] for e in data["employees"])
    print("\nEmployees per department:")
    for dept, count in sorted(depts.items()):
        print(f"  {dept}: {count}")

    levels = Counter(e["level"] for e in data["employees"])
    print(f"\nEmployees per level: {dict(sorted(levels.items()))}")
