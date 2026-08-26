from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from app.db.base import Base
from app.utils.enums import TimesheetStatus, _enum_values


class Timesheet(Base):
    __tablename__ = "timesheets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date)
    status: Mapped[TimesheetStatus] = mapped_column(
        SAEnum(TimesheetStatus, native_enum=False, length=15, values_callable=_enum_values),
        default=TimesheetStatus.DRAFT,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    entries = relationship(
        "TimesheetEntry",
        back_populates="timesheet",
        cascade="all, delete-orphan",
        order_by="TimesheetEntry.date",
    )


class TimesheetEntry(Base):
    __tablename__ = "timesheet_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timesheet_id: Mapped[int] = mapped_column(ForeignKey("timesheets.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    date: Mapped[date] = mapped_column(Date)
    hours: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    description: Mapped[str | None] = mapped_column(Text)

    timesheet = relationship("Timesheet", back_populates="entries")


class TimesheetDay(Base):
    """Per-day approval state inside a weekly sheet (daily submission flow)."""

    __tablename__ = "timesheet_days"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timesheet_id: Mapped[int] = mapped_column(
        ForeignKey("timesheets.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    status: Mapped[TimesheetStatus] = mapped_column(
        SAEnum(TimesheetStatus, native_enum=False, length=15, values_callable=_enum_values),
        default=TimesheetStatus.DRAFT,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("timesheet_id", "date", name="uq_timesheet_days_sheet_date"),
        CheckConstraint(
            "status IN ('draft','submitted','approved','rejected')",
            name="ck_timesheet_days_status",
        ),
        Index("ix_timesheet_days_status", "status"),
    )
