from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import LeaveStatus, LeaveType


class LeaveApplyRequest(BaseModel):
    leave_type: LeaveType
    from_date: date
    to_date: date
    half_day_first: bool = False
    half_day_second: bool = False
    reason: str | None = Field(default=None, max_length=2000)
    attachment: str | None = None


class LeaveRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class LeaveBalanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    leave_type: LeaveType
    year: int
    allocated: Decimal
    used: Decimal
    remaining: Decimal = 0


class LeaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    leave_type: LeaveType
    from_date: date
    to_date: date
    total_days: Decimal
    half_day_first: bool
    half_day_second: bool
    reason: str | None
    status: LeaveStatus
    approved_by: int | None
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class LeaveUserRow(LeaveOut):
    user_name: str
    employee_id: str | None
    designation: str | None
    department: str | None


class TeamAvailabilityRow(BaseModel):
    user_id: int
    user_name: str
    department: str | None
    leave_type: LeaveType
    status: LeaveStatus
    from_date: date
    to_date: date
