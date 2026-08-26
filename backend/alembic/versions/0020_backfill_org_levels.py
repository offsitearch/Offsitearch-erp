"""Backfill users.org_level_id from the legacy role column.

Maps the old role hierarchy onto organizational levels so that
authorization can move from roles to org levels:

    super_admin  -> L1  (Director)
    admin        -> L2  (Department Head)
    project_lead -> L3  (Project / Team Lead)
    employee     -> L5  (Professional; L4 reserved for manual assignment)
    intern       -> L6  (Intern)

Users whose role is NULL or unrecognised are left untouched and must be
assigned a level manually.

Revision ID: 0020_backfill_org_levels
Revises: 0019_org_structure_refactor
Create Date: 2026-08-22
"""
from alembic import op

revision = "0020_backfill_org_levels"
down_revision = "0019_org_structure_refactor"
branch_labels = None
depends_on = None

ROLE_TO_LEVEL = [
    ("super_admin", "L1"),
    ("admin", "L2"),
    ("project_lead", "L3"),
    ("employee", "L5"),
    ("intern", "L6"),
]


def upgrade() -> None:
    for role_value, level_code in ROLE_TO_LEVEL:
        op.execute(
            f"""
            UPDATE users u
            SET org_level_id = ol.id
            FROM org_levels ol
            WHERE ol.code = '{level_code}'
              AND u.role = '{role_value}'
              AND u.org_level_id IS NULL
            """
        )


def downgrade() -> None:
    # Backfill is not reversible per-user without re-deriving levels;
    # restoring role-based defaults would corrupt real assignments.
    pass
