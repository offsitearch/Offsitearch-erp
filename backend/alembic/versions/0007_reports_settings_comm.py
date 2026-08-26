"""notices, meetings, meeting_attendees, notifications, site_visits, site_visit_photos, audit_logs

Revision ID: 0007_reports_settings_comm
Revises: 0006_finance_vendors_payroll
Create Date: 2026-08-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_reports_settings_comm"
down_revision: Union[str, None] = "0006_finance_vendors_payroll"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)

_NOTICE_IMPORTANCES = "('LOW','MEDIUM','HIGH')"
_MEETING_TYPES = "('INTERNAL','CLIENT','SITE','VIDEO')"
_MEETING_STATUSES = "('SCHEDULED','COMPLETED','CANCELLED')"
_RSVP_STATUSES = "('PENDING','ACCEPTED','DECLINED')"
_SITE_VISIT_STATUSES = "('SCHEDULED','COMPLETED','CANCELLED')"


def upgrade() -> None:
    # --- notices ---
    op.create_table(
        "notices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("importance", sa.String(length=10), nullable=False, server_default="medium"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_notices_creator", "notices", "users", ["created_by"], ["id"])
    op.create_check_constraint(
        "ck_notices_importance", "notices", f"importance IN {_NOTICE_IMPORTANCES}"
    )

    # --- meetings ---
    op.create_table(
        "meetings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meeting_type", sa.String(length=15), nullable=False, server_default="internal"),
        sa.Column("scheduled_at", _ts, nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("60")),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="scheduled"),
        sa.Column("organizer_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_meetings_organizer", "meetings", "users", ["organizer_id"], ["id"])
    op.create_index("ix_meetings_scheduled_at", "meetings", ["scheduled_at"])
    op.create_check_constraint(
        "ck_meetings_type", "meetings", f"meeting_type IN {_MEETING_TYPES}"
    )
    op.create_check_constraint(
        "ck_meetings_status", "meetings", f"status IN {_MEETING_STATUSES}"
    )

    # --- meeting_attendees ---
    op.create_table(
        "meeting_attendees",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("meeting_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("rsvp_status", sa.String(length=10), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_meeting_attendees_meeting", "meeting_attendees", "meetings", ["meeting_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_meeting_attendees_user", "meeting_attendees", "users", ["user_id"], ["id"]
    )
    op.create_index("ix_meeting_attendees_meeting_id", "meeting_attendees", ["meeting_id"])
    op.create_index("ix_meeting_attendees_user_id", "meeting_attendees", ["user_id"])
    op.create_check_constraint(
        "ck_meeting_attendees_rsvp", "meeting_attendees", f"rsvp_status IN {_RSVP_STATUSES}"
    )

    # --- notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=True),
        sa.Column("type", sa.String(length=30), nullable=False, server_default="general"),
        sa.Column("link", sa.String(length=255), nullable=True),
        sa.Column("read_at", _ts, nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_notifications_user", "notifications", "users", ["user_id"], ["id"]
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])

    # --- site_visits ---
    op.create_table(
        "site_visits",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("status", sa.String(length=15), nullable=False, server_default="scheduled"),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("weather", sa.String(length=80), nullable=True),
        sa.Column("attendance_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("completed_at", _ts, nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_site_visits_project", "site_visits", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_site_visits_creator", "site_visits", "users", ["created_by"], ["id"])
    op.create_index("ix_site_visits_project_id", "site_visits", ["project_id"])
    op.create_index("ix_site_visits_visit_date", "site_visits", ["visit_date"])
    op.create_check_constraint(
        "ck_site_visits_status", "site_visits", f"status IN {_SITE_VISIT_STATUSES}"
    )

    # --- site_visit_photos ---
    op.create_table(
        "site_visit_photos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("site_visit_id", sa.BigInteger(), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("caption", sa.String(length=255), nullable=True),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key(
        "fk_site_visit_photos_visit", "site_visit_photos", "site_visits", ["site_visit_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_site_visit_photos_user", "site_visit_photos", "users", ["uploaded_by"], ["id"]
    )
    op.create_index("ix_site_visit_photos_site_visit_id", "site_visit_photos", ["site_visit_id"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.String(length=40), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_foreign_key("fk_audit_logs_user", "audit_logs", "users", ["user_id"], ["id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("site_visit_photos")
    op.drop_table("site_visits")
    op.drop_table("notifications")
    op.drop_table("meeting_attendees")
    op.drop_table("meetings")
    op.drop_table("notices")
