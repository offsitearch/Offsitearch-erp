from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import TimesheetStatus


class TimesheetEntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int | None = None
    task_id: int | None = None
    date: date
    hours: Decimal = Field(gt=0, le=24)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class TimesheetWeekSave(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_start: date
    entries: list[TimesheetEntryIn] = Field(default_factory=list, max_length=200)


class TimesheetEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    task_id: int | None
    date: date
    hours: Decimal
    location: str | None = None
    description: str | None


class TimesheetDayOut(BaseModel):
    """Approval state of a single day inside the weekly sheet."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    status: TimesheetStatus
    submitted_at: datetime | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None


class TimesheetDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: str | None = None
    employee_id: str | None = None
    week_start: date
    week_end: date
    status: TimesheetStatus
    total_hours: Decimal = Decimal("0")
    submitted_at: datetime | None = None
    approved_by: int | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    entries: list[TimesheetEntryOut] = []
    days: list[TimesheetDayOut] = []


class TimesheetRow(BaseModel):
    """Summary row for history / pending / admin lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: str | None = None
    employee_id: str | None = None
    department: str | None = None
    week_start: date
    week_end: date
    status: TimesheetStatus
    total_hours: Decimal = Decimal("0")
    entry_count: int = 0
    submitted_at: datetime | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None


class TimesheetPage(BaseModel):
    items: list[TimesheetRow]
    total: int
    page: int
    page_size: int


class RejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)
