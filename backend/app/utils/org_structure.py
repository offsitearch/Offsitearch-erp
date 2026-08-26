"""OFFSITE organizational structure — single source of truth.

Organizational levels (L1-L6) drive authorization: endpoints enforce a
minimum level via require_min_level; canonical permission ranks live in
app.utils.shared.LEVEL_RANK.
"""

# ── 7 Organizational Levels ─────────────────────────────────────────
ORG_LEVELS = [
    {
        "code": "L0",
        "name": "CEO",
        "description": "Chief Executive Officer - founder/owner; highest authority",
        "rank": 0,
    },
    {
        "code": "L1",
        "name": "Director",
        "description": "Studio Director - a single director; executive authority",
        "rank": 1,
    },
    {
        "code": "L2",
        "name": "Department Head",
        "description": "Department heads: operations, delivery, etc.",
        "rank": 2,
    },
    {
        "code": "L3",
        "name": "Project / Team Lead",
        "description": "Project manager, project lead, team lead, etc.",
        "rank": 3,
    },
    {
        "code": "L4",
        "name": "Sr. Professional",
        "description": "Sr. architect, Sr. designer, etc.",
        "rank": 4,
    },
    {"code": "L5", "name": "Professional", "description": "Architect, designer, etc.", "rank": 5},
    {"code": "L6", "name": "Intern", "description": "Interns and entry-level staff", "rank": 6},
]

# ── Initial OFFSITE departments (top-level) ─────────────────────────
DEPARTMENTS = [
    {
        "name": "Architecture & Design",
        "description": "Architecture, urban design, design development and architectural documentation",
    },
    {
        "name": "Interior Design",
        "description": "Interior design, furniture/FF&E and interior documentation",
    },
    {
        "name": "Landscape",
        "description": "Landscape design and landscape documentation",
    },
    {
        "name": "BIM & Visualization",
        "description": "BIM, 3D visualization, rendering and CAD/drafting",
    },
    {
        "name": "Project & Site",
        "description": "Project management, site coordination and construction administration",
    },
    {
        "name": "Business & Operations",
        "description": "Business development, client relations, operations and procurement",
    },
    {
        "name": "Corporate / Administration",
        "description": "HR, finance & accounts, administration and IT/systems",
    },
]

# Legacy department name → new top-level department mapping.
# Exact names first (covers v1 seed data), then keyword rules for variants.
LEGACY_DEPARTMENT_MAP: dict[str, str] = {
    "Design Team": "Architecture & Design",
    "Technical / Drafting Team": "BIM & Visualization",
    "Visualization / 3D Team": "BIM & Visualization",
    "Project Management": "Project & Site",
    "Site Team": "Project & Site",
    "Business Development": "Business & Operations",
    "Administration": "Corporate / Administration",
}

_LEGACY_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("architect", "urban design"), "Architecture & Design"),
    (("interior", "ff&e", "furniture"), "Interior Design"),
    (("landscape",), "Landscape"),
    (("bim", "visual", "3d", "render", "cad", "draft"), "BIM & Visualization"),
    (("project", "site", "construction"), "Project & Site"),
    (("business", "client", "operation", "procure", "bd "), "Business & Operations"),
    (
        ("hr", "human resource", "finance", "account", "admin", "it ", "corporate"),
        "Corporate / Administration",
    ),
]


def map_legacy_department(name: str) -> str | None:
    """Return the new top-level department for a legacy name, or None if ambiguous.

    Ambiguous records are intentionally NOT guessed — callers should keep
    them untouched so no employee loses their organizational data.
    """
    if not name:
        return None
    exact = LEGACY_DEPARTMENT_MAP.get(name.strip())
    if exact:
        return exact
    lowered = f" {name.lower().strip()} "
    for keywords, target in _LEGACY_KEYWORD_MAP:
        if any(keyword in lowered for keyword in keywords):
            return target
    return None


# Suggested designation catalog grouped by level. HR information only —
# designations never grant permissions and are not tied to levels by FK.
DESIGNATION_CATALOG: dict[str, list[str]] = {
    "L0": [],
    "L1": [],
    "L2": [
        "Operations Head",
        "Delivery Head",
        "Design Head",
        "Finance Head",
        "HR Head",
    ],
    "L3": [
        "Project Manager",
        "Project Lead",
        "Team Lead",
        "Studio Manager",
    ],
    "L4": [
        "Sr. Architect",
        "Sr. Designer",
        "Sr. Interior Designer",
        "Sr. Landscape Designer",
        "Sr. BIM Specialist",
    ],
    "L5": [
        "Architect",
        "Project Architect",
        "Designer",
        "Interior Designer",
        "Landscape Designer",
        "BIM Architect",
        "BIM Specialist",
        "CAD Specialist",
        "Site Engineer",
        "3D Visualizer",
    ],
    "L6": [
        "Architecture Intern",
        "Interior Design Intern",
        "BIM Intern",
        "Design Intern",
        "Research Intern",
    ],
}

# Suggested designations grouped by department. HR information only —
# designations never grant permissions and are not tied to departments by FK.
DEPARTMENT_DESIGNATIONS: dict[str, list[str]] = {
    "Architecture & Design": [
        "Design Head",
        "Sr. Architect",
        "Architect",
        "Project Architect",
        "Jr. Architect",
        "Urban Designer",
    ],
    "Interior Design": [
        "Interior Design Head",
        "Sr. Interior Designer",
        "Interior Designer",
        "FF&E Designer",
        "Jr. Interior Designer",
    ],
    "Landscape": [
        "Landscape Lead",
        "Sr. Landscape Designer",
        "Landscape Designer",
        "Landscape Architect",
    ],
    "BIM & Visualization": [
        "BIM Manager",
        "Sr. BIM Specialist",
        "BIM Specialist",
        "CAD Specialist",
        "3D Visualizer",
        "Renderer",
    ],
    "Project & Site": [
        "Delivery Head",
        "Project Manager",
        "Project Coordinator",
        "Site Engineer",
        "Site Supervisor",
        "Construction Administrator",
    ],
    "Business & Operations": [
        "Operations Head",
        "Business Development Manager",
        "Client Relations Executive",
        "Operations Executive",
        "Procurement Executive",
    ],
    "Corporate / Administration": [
        "Finance Head",
        "HR Head",
        "HR Executive",
        "Accountant",
        "Accounts Executive",
        "Office Administrator",
        "IT Administrator",
    ],
}
