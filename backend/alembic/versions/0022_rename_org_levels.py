"""Rename org levels to the final studio taxonomy.

L1 Director (single), L2 Department Head, L3 Project / Team Lead,
L4 Sr. Professional, L5 Professional, L6 Intern.

Revision ID: 0022_rename_org_levels
Revises: 0021_drop_user_role
Create Date: 2026-08-22
"""
from alembic import op


revision = "0022_rename_org_levels"
down_revision = "0021_drop_user_role"
branch_labels = None
depends_on = None

LEVEL_NAMES = [
    ("L1", "Director", "Studio Director - a single director; highest authority"),
    ("L2", "Department Head", "Department heads: operations, delivery, etc."),
    ("L3", "Project / Team Lead", "Project manager, project lead, team lead, etc."),
    ("L4", "Sr. Professional", "Sr. architect, Sr. designer, etc."),
    ("L5", "Professional", "Architect, designer, etc."),
    ("L6", "Intern", "Interns and entry-level staff"),
]


def upgrade() -> None:
    for code, name, description in LEVEL_NAMES:
        op.execute(
            f"""
            UPDATE org_levels
            SET name = '{name}', description = '{description}'
            WHERE code = '{code}'
              AND (name <> '{name}' OR description IS DISTINCT FROM '{description}')
            """
        )


def downgrade() -> None:
    legacy = [
        ("L1", "Executive", "Studio-wide executive leadership"),
        ("L2", "Leadership", "Studio and functional leadership"),
        ("L3", "Management", "Department/project management"),
        ("L4", "Senior Professional", "Senior professional/specialist staff"),
        ("L5", "Professional", "Professional/specialist staff"),
        ("L6", "Junior / Entry", "Junior employees and interns"),
    ]
    for code, name, description in legacy:
        op.execute(
            f"""
            UPDATE org_levels
            SET name = '{name}', description = '{description}'
            WHERE code = '{code}'
            """
        )
