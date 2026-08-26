"""Drop the legacy users.role column.

Authorization is now driven entirely by organizational levels
(users.org_level_id, backfilled in 0020_backfill_org_levels).

Revision ID: 0021_drop_user_role
Revises: 0020_backfill_org_levels
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa


revision = "0021_drop_user_role"
down_revision = "0020_backfill_org_levels"
branch_labels = None
depends_on = None

LEGACY_VALUES = [
    ("super_admin", "L1"),
    ("admin", "L2"),
    ("project_lead", "L3"),
    ("employee", "L5"),
    ("intern", "L6"),
]


def upgrade() -> None:
    # Safety net: make sure no user was left without a level before the
    # column that could re-derive it disappears.
    for role_value, level_code in LEGACY_VALUES:
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
    op.drop_column("users", "role")


def downgrade() -> None:
    role_enum = sa.Enum(
        "super_admin",
        "admin",
        "project_lead",
        "employee",
        "intern",
        name="userrole",
        native_enum=False,
        length=20,
    )
    op.add_column("users", sa.Column("role", role_enum, nullable=True))
    op.create_index("ix_users_role", "users", ["role"])
    # Best-effort reverse mapping; levels outside the standard mapping
    # (e.g. L4) default to 'employee'.
    for level_code, role_value in [
        ("L1", "super_admin"),
        ("L2", "admin"),
        ("L3", "project_lead"),
        ("L4", "employee"),
        ("L5", "employee"),
        ("L6", "intern"),
    ]:
        op.execute(
            f"""
            UPDATE users u
            SET role = '{role_value}'
            FROM org_levels ol
            WHERE ol.code = '{level_code}'
              AND u.org_level_id = ol.id
              AND u.role IS NULL
            """
        )
    op.execute("UPDATE users SET role = 'employee' WHERE role IS NULL")
