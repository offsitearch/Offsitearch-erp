"""Project type templates — phase scaffolding per project type.

Consumed by project_service (template application, template listing) and by
seed data for demo projects.
"""

PROJECT_TYPE_TEMPLATES = {
    "residential": {
        "label": "Residential",
        "phases": [
            "Concept",
            "Schematic Design",
            "Design Development",
            "Construction Drawings",
            "Approvals",
            "Construction Administration",
        ],
    },
    "commercial": {
        "label": "Commercial",
        "phases": [
            "Concept",
            "Schematic Design",
            "Design Development",
            "Construction Drawings",
            "Approvals",
            "Construction Administration",
        ],
    },
    "interior": {
        "label": "Interior",
        "phases": [
            "Client Brief & Programme",
            "Concept Design",
            "Design Development",
            "Tender & Costing",
            "Execution & Site Works",
            "Handover & Aftercare",
        ],
    },
    "institutional": {
        "label": "Institutional",
        "phases": [
            "Concept",
            "Schematic Design",
            "Design Development",
            "Construction Drawings",
            "Approvals",
            "Construction Administration",
        ],
    },
    "landscape": {
        "label": "Landscape",
        "phases": [
            "Site Analysis",
            "Concept Design",
            "Design Development",
            "Planting & Material Specification",
            "Construction Documents",
            "Construction Administration",
        ],
    },
    "urban_planning": {
        "label": "Urban Planning",
        "phases": [
            "Context Analysis",
            "Vision & Framework",
            "Master Plan Concept",
            "Detailed Master Plan",
            "Guidelines & Policies",
            "Final Deliverables",
        ],
    },
    "renovation": {
        "label": "Renovation",
        "phases": [
            "Site Audit & Survey",
            "Concept Design",
            "Design Development",
            "Construction Drawings",
            "Approvals",
            "Construction Administration",
        ],
    },
    "mixed_use": {
        "label": "Mixed-Use",
        "phases": [
            "Concept",
            "Schematic Design",
            "Design Development",
            "Construction Drawings",
            "Approvals",
            "Construction Administration",
        ],
    },
}
