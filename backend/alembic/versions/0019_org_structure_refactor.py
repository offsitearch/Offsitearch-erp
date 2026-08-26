"""Organizational structure refactor.

- Creates org_levels lookup table seeded with the 6 OFFSITE levels.
- Adds users.org_level_id (informational seniority, no RBAC effect).
- Adds departments.parent_id for future sub-departments.
- Seeds the 7 initial top-level departments.
- Maps legacy departments onto the new structure where unambiguous:
  members are reassigned, emptied legacy rows are deactivated (kept,
  never deleted). Ambiguous legacy departments are left untouched so
  no employee loses organizational data.

Revision ID: 0019_org_structure_refactor
Revises: 0018_add_audit_request_id
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_org_structure_refactor"
down_revision = "0018_add_audit_request_id"
branch_labels = None
depends_on = None

ORG_LEVELS = [
    ("L1", "Director", "Studio Director - a single director; highest authority", 1),
    ("L2", "Department Head", "Department heads: operations, delivery, etc.", 2),
    ("L3", "Project / Team Lead", "Project manager, project lead, team lead, etc.", 3),
    ("L4", "Sr. Professional", "Sr. architect, Sr. designer, etc.", 4),
    ("L5", "Professional", "Architect, designer, etc.", 5),
    ("L6", "Intern", "Interns and entry-level staff", 6),
]

NEW_DEPARTMENTS = [
    "Architecture & Design",
    "Interior Design",
    "Landscape",
    "BIM & Visualization",
    "Project & Site",
    "Business & Operations",
    "Corporate / Administration",
]

# Exact legacy name → new department (covers v1 seed data).
EXACT_MAP = {
    "Design Team": "Architecture & Design",
    "Technical / Drafting Team": "BIM & Visualization",
    "Visualization / 3D Team": "BIM & Visualization",
    "Project Management": "Project & Site",
    "Site Team": "Project & Site",
    "Business Development": "Business & Operations",
    "Administration": "Corporate / Administration",
}

# Keyword rules for legacy name variants created outside the seeds.
KEYWORD_MAP = [
    (("architect", "urban design"), "Architecture & Design"),
    (("interior", "ff&e", "furniture"), "Interior Design"),
    (("landscape",), "Landscape"),
    (("bim", "visual", "3d", "render", "cad", "draft"), "BIM & Visualization"),
    (("project", "site", "construction"), "Project & Site"),
    (("business", "client", "operation", "procure"), "Business & Operations"),
    (("hr", "human resource", "finance", "account", "admin", "corporate"), "Corporate / Administration"),
]


def _map_legacy(name: str) -> str | None:
    if not name:
        return None
    target = EXACT_MAP.get(name.strip())
    if target:
        return target
    lowered = f" {name.lower().strip()} "
    for keywords, candidate in KEYWORD_MAP:
        if any(keyword in lowered for keyword in keywords):
            return candidate
    return None


def upgrade() -> None:
    conn = op.get_bind()

    org_levels = sa.table(
        "org_levels",
        sa.column("code"),
        sa.column("name"),
        sa.column("description"),
        sa.column("rank"),
        sa.column("is_active"),
    )
    departments = sa.table(
        "departments",
        sa.column("id"),
        sa.column("name"),
        sa.column("parent_id"),
        sa.column("head_id"),
        sa.column("description"),
        sa.column("is_active"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )

    # 1. org_levels table + seed
    op.create_table(
        "org_levels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_org_levels_code"), "org_levels", ["code"])
    conn.execute(
        org_levels.insert().values(
            [
                {"code": code, "name": name, "description": desc, "rank": rank, "is_active": True}
                for code, name, desc, rank in ORG_LEVELS
            ]
        )
    )

    # 2. New columns
    op.add_column(
        "users",
        sa.Column("org_level_id", sa.Integer(), nullable=True),
    )
    op.create_index(op.f("ix_users_org_level_id"), "users", ["org_level_id"])
    op.create_foreign_key(
        "fk_users_org_level_id_org_levels", "users", "org_levels", ["org_level_id"], ["id"]
    )
    op.add_column(
        "departments",
        sa.Column("parent_id", sa.Integer(), nullable=True),
    )
    op.create_index(op.f("ix_departments_parent_id"), "departments", ["parent_id"])
    op.create_foreign_key(
        "fk_departments_parent_id_departments",
        "departments",
        "departments",
        ["parent_id"],
        ["id"],
    )

    # 3. Seed the 7 initial top-level departments
    conn.execute(
        departments.insert().values(
            [{"name": name, "is_active": True} for name in NEW_DEPARTMENTS]
        )
    )

    # 4. Migrate legacy departments onto the new structure
    rows = conn.execute(sa.text("SELECT id, name FROM departments")).fetchall()
    dept_by_name = {row[1]: row[0] for row in rows}
    legacy_ids: list[int] = []
    for dept_id, name in rows:
        if name in NEW_DEPARTMENTS:
            continue
        target_name = _map_legacy(name)
        if target_name is None:
            # Ambiguous — keep untouched, do not guess.
            continue
        target_id = dept_by_name[target_name]
        conn.execute(
            sa.text("UPDATE users SET department_id = :target WHERE department_id = :src")
            .bindparams(target=target_id, src=dept_id)
        )
        legacy_ids.append(dept_id)

    # Deactivate only legacy departments that no longer have members.
    for dept_id in legacy_ids:
        count = conn.execute(
            sa.text("SELECT COUNT(*) FROM users WHERE department_id = :d").bindparams(d=dept_id)
        ).scalar()
        if count == 0:
            conn.execute(
                sa.text("UPDATE departments SET is_active = false WHERE id = :d").bindparams(d=dept_id)
            )


def downgrade() -> None:
    op.drop_constraint("fk_departments_parent_id_departments", "departments", type_="foreignkey")
    op.drop_index(op.f("ix_departments_parent_id"), table_name="departments")
    op.drop_column("departments", "parent_id")
    op.drop_constraint("fk_users_org_level_id_org_levels", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_org_level_id"), table_name="users")
    op.drop_column("users", "org_level_id")
    op.drop_index(op.f("ix_org_levels_code"), table_name="org_levels")
    op.drop_table("org_levels")
