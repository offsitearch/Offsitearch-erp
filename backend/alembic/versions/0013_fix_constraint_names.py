"""No-op: constraint fix is now handled by 0010_fix_enum_case.

Revision ID: 0013_fix_constraint_names
Revises: 0012_add_performance_indexes
Create Date: 2026-08-18
"""

revision = "0013_fix_constraint_names"
down_revision = "0012_add_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
