"""Generate 100 test employees with realistic department/level distribution.

The module is pure-Python — no database calls.  ``generate_employees()``
returns a list of dicts ready for ``db.add_all()``.
"""

from __future__ import annotations

from random import Random

from ._names import generate_names

# ── Department → level quota (total = 100) ──────────────────────────────
# Each tuple: (level_code, count)
DEPT_DISTRIBUTION: dict[str, list[tuple[str, int]]] = {
    "Architecture & Design": [
        ("L2", 1), ("L3", 3), ("L4", 8), ("L5", 10), ("L6", 2),
    ],
    "Interior Design": [
        ("L2", 1), ("L3", 2), ("L4", 5), ("L5", 5), ("L6", 2),
    ],
    "Landscape": [
        ("L2", 1), ("L3", 1), ("L4", 3), ("L5", 4), ("L6", 1),
    ],
    "BIM & Visualization": [
        ("L2", 1), ("L3", 2), ("L4", 5), ("L5", 5), ("L6", 2),
    ],
    "Project & Site": [
        ("L2", 1), ("L3", 3), ("L4", 6), ("L5", 7), ("L6", 3),
    ],
    "Business & Operations": [
        ("L2", 1), ("L3", 2), ("L4", 4), ("L5", 5), ("L6", 2),
    ],
    "Corporate / Administration": [
        ("L2", 1), ("L3", 1),
    ],
}

# ── Designation pick-lists (from org_structure.py) ──────────────────────
_DESIGNATIONS: dict[str, dict[str, list[str]]] = {
    "Architecture & Design": {
        "L2": ["Design Head"],
        "L3": ["Project Lead", "Team Lead"],
        "L4": ["Sr. Architect", "Sr. Architect", "Sr. Architect",
                "Urban Designer", "Project Architect", "Project Architect",
                "Project Architect", "Project Architect"],
        "L5": ["Architect", "Architect", "Architect", "Architect",
                "Architect", "Jr. Architect", "Jr. Architect",
                "Jr. Architect", "Jr. Architect", "Jr. Architect"],
        "L6": ["Architecture Intern", "Architecture Intern",
               "Design Intern"],
    },
    "Interior Design": {
        "L2": ["Interior Design Head"],
        "L3": ["Project Lead", "Team Lead"],
        "L4": ["Sr. Interior Designer", "Sr. Interior Designer",
               "Sr. Interior Designer", "FF&E Designer",
               "FF&E Designer"],
        "L5": ["Interior Designer", "Interior Designer",
               "Interior Designer", "Jr. Interior Designer",
               "Jr. Interior Designer"],
        "L6": ["Interior Design Intern", "Interior Design Intern"],
    },
    "Landscape": {
        "L2": ["Landscape Lead"],
        "L3": ["Project Lead"],
        "L4": ["Sr. Landscape Designer", "Sr. Landscape Designer",
               "Landscape Architect"],
        "L5": ["Landscape Designer", "Landscape Designer",
               "Landscape Designer", "Landscape Designer"],
        "L6": ["Design Intern"],
    },
    "BIM & Visualization": {
        "L2": ["BIM Manager"],
        "L3": ["Project Lead", "Team Lead"],
        "L4": ["Sr. BIM Specialist", "Sr. BIM Specialist",
               "Sr. BIM Specialist", "CAD Specialist", "CAD Specialist"],
        "L5": ["BIM Specialist", "BIM Specialist", "BIM Specialist",
               "3D Visualizer", "3D Visualizer"],
        "L6": ["BIM Intern", "BIM Intern"],
    },
    "Project & Site": {
        "L2": ["Delivery Head"],
        "L3": ["Project Manager", "Project Manager", "Project Lead"],
        "L4": ["Site Engineer", "Site Engineer", "Site Engineer",
               "Site Engineer", "Construction Administrator",
               "Project Coordinator"],
        "L5": ["Site Engineer", "Site Engineer", "Site Engineer",
               "Site Engineer", "Site Engineer",
               "Project Coordinator", "Project Coordinator"],
        "L6": ["Site Intern", "Site Intern", "Design Intern"],
    },
    "Business & Operations": {
        "L2": ["Operations Head"],
        "L3": ["Business Development Manager", "Client Relations Executive"],
        "L4": ["Operations Executive", "Operations Executive",
               "Procurement Executive", "Procurement Executive"],
        "L5": ["Operations Executive", "Operations Executive",
               "Client Relations Executive", "Client Relations Executive",
               "Procurement Executive"],
        "L6": ["Operations Intern", "Operations Intern"],
    },
    "Corporate / Administration": {
        "L2": ["HR Head"],
        "L3": ["HR Executive"],
    },
}

# ── Skills per department ───────────────────────────────────────────────
_SKILLS: dict[str, list[str]] = {
    "Architecture & Design": [
        "revit", "autoCAD", "sketchup", "conceptual-design",
        "construction-drawing", "urban-design", "sustainable-design",
    ],
    "Interior Design": [
        "revit", "3ds-max", "vray", "interior-design", "FFE",
        "material-selection", "space-planning",
    ],
    "Landscape": [
        "autoCAD", "sketchup", "lumion", "landscape-design",
        "plant-selection", "site-analysis",
    ],
    "BIM & Visualization": [
        "revit", "navisworks", "3ds-max", "vray", "lumion",
        "bim-coordination", "cad-drafting", "enscape",
    ],
    "Project & Site": [
        "project-management", "site-supervision", "construction-admin",
        "client-coordination", "scheduling", "quality-control",
    ],
    "Business & Operations": [
        "client-relations", "procurement", "operations",
        "business-development", "negotiation",
    ],
    "Corporate / Administration": [
        "hr-operations", "finance", "office-management", "compliance",
    ],
}

# ── City names for location field (in timesheets) ──────────────────────
CITIES = [
    "Pune", "Mumbai", "Navi Mumbai", "Thane", "Kothrud", "Baner",
    "Hinjewadi", "Viman Nagar", "Kharadi", "Wagholi", "Undri",
    "Karve Nagar", "Aundh", "Hadapsar", "Magarpatta",
]

_rng = Random(42)


def _pick_designation(dept: str, level: str, index: int) -> str:
    """Pick a designation from the catalog, cycling if needed."""
    pool = _DESIGNATIONS.get(dept, {}).get(level, ["Staff"])
    return pool[index % len(pool)]


def _pick_skills(dept: str, count: int = 3) -> list[str]:
    pool = _SKILLS.get(dept, ["general"])
    return _rng.sample(pool, min(count, len(pool)))


def generate_employees() -> list[dict]:
    """Generate 100 employee dicts with all fields needed for User creation.

    Returns a list of dicts with keys:
        name, gender, phone, date_of_joining, department, level,
        designation, skills, employee_id, login_id_seq, reporting_to_name
    """
    # 1. Build flat list of (department, level) slots
    slots: list[tuple[str, str]] = []
    for dept, levels in DEPT_DISTRIBUTION.items():
        for level_code, count in levels:
            for _ in range(count):
                slots.append((dept, level_code))

    assert len(slots) == 100, f"Expected 100 slots, got {len(slots)}"

    # 2. Generate unique names
    names = generate_names(n=len(slots))

    # 3. Build employee list with designation index tracking
    dept_level_counter: dict[tuple[str, str], int] = {}
    employees: list[dict] = []

    for i, ((dept, level), name_data) in enumerate(zip(slots, names)):
        key = (dept, level)
        idx = dept_level_counter.get(key, 0)
        dept_level_counter[key] = idx + 1

        emp = {
            "name": name_data["name"],
            "gender": name_data["gender"],
            "phone": name_data["phone"],
            "date_of_joining": name_data["date_of_joining"],
            "department": dept,
            "level": level,
            "designation": _pick_designation(dept, level, idx),
            "skills": _pick_skills(dept),
            "employee_id": f"OA-{i + 1:03d}",
            "login_id_seq": i + 1,  # sequential; year = join year
            "reporting_to_name": None,  # filled in step 4
        }
        employees.append(emp)

    # 4. Build reporting hierarchy
    #    - L2 heads → first person in list (will be the "Director" placeholder)
    #    - L3 leads → L2 head of same department
    #    - L4/L5/L6 → nearest L3 in same dept, or L2 if no L3
    _assign_reporting(employees)

    return employees


def _assign_reporting(employees: list[dict]) -> None:
    """Set ``reporting_to_name`` for each employee based on hierarchy."""
    # Group by department
    by_dept: dict[str, list[dict]] = {}
    for emp in employees:
        by_dept.setdefault(emp["department"], []).append(emp)

    # The first L2 in each dept is the head
    dept_heads: dict[str, dict] = {}
    for dept, members in by_dept.items():
        for m in members:
            if m["level"] == "L2":
                dept_heads[dept] = m
                break

    for emp in employees:
        level = emp["level"]
        dept = emp["department"]

        if level == "L2":
            # Department heads report to the CEO (L0).
            emp["reporting_to_name"] = "_CEO_"
        elif level == "L3":
            emp["reporting_to_name"] = dept_heads.get(dept, {}).get("name")
        else:
            # L4/L5/L6 → nearest L3 in same dept
            leads = [m for m in by_dept[dept] if m["level"] == "L3"]
            if leads:
                emp["reporting_to_name"] = leads[0]["name"]
            else:
                # No L3 in dept → report to L2 head
                emp["reporting_to_name"] = dept_heads.get(dept, {}).get("name")


def get_department_heads(employees: list[dict]) -> dict[str, dict]:
    """Return {department_name: head_employee_dict}."""
    heads: dict[str, dict] = {}
    for emp in employees:
        if emp["level"] == "L2" and emp["department"] not in heads:
            heads[emp["department"]] = emp
    return heads


def get_team_leads(employees: list[dict]) -> dict[str, list[dict]]:
    """Return {department_name: [lead Employee, ...]}."""
    leads: dict[str, list[dict]] = {}
    for emp in employees:
        if emp["level"] == "L3":
            leads.setdefault(emp["department"], []).append(emp)
    return leads
