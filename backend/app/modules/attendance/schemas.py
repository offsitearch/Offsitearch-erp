from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.identity.schemas import UserOut
from app.utils.enums import AttendanceMethod, AttendanceStatus


class CheckInRequest(BaseModel):
    method: AttendanceMethod = AttendanceMethod.WEB
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class CheckOutRequest(BaseModel):
    notes: str | None = None


class AttendanceRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date: date
    check_in_time: datetime | None
    check_out_time: datetime | None
    status: AttendanceStatus
    late_minutes: int
    total_hours: Decimal | None
    check_in_method: AttendanceMethod
    check_in_location: str | None
    notes: str | None
    marked_by: int | None


class AttendanceUserRow(AttendanceRecordOut):
    user_name: str
    employee_id: str | None
    designation: str | None
    department: str | None


class AttendanceUpdateRequest(BaseModel):
    status: AttendanceStatus | None = None
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    notes: str | None = None


class BulkEntryItem(BaseModel):
    user_id: int
    status: AttendanceStatus
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    notes: str | None = None


class BulkEntryRequest(BaseModel):
    date: date
    entries: list[BulkEntryItem] = Field(min_length=1)


class MonthlySummaryOut(BaseModel):
    user: UserOut
    records: list[AttendanceRecordOut]
    totals: dict[str, int]


class ReportRow(BaseModel):
    date: date
    user_id: int
    user_name: str
    employee_id: str | None
    designation: str | None
    department: str | None
    phone: str | None = None
    status: AttendanceStatus
    check_in_time: datetime | None
    check_out_time: datetime | None
    late_minutes: int
    total_hours: Decimal | None


class ReportOut(BaseModel):
    from_date: date
    to_date: date
    rows: list[ReportRow]


class HolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date: date
    is_recurring: bool
