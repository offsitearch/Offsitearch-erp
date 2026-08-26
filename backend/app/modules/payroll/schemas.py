from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PayrollEntryOut(BaseModel):
    user_id: int
    user_name: str | None = None
    employee_id: str | None = None
    designation: str | None = None
    department: str | None = None
    working_days: int
    gross_salary: Decimal
    deductions: Decimal
    net_pay: Decimal


class PayrollRunOut(BaseModel):
    id: int | None = None
    month: int
    year: int
    status: str
    processed_by: int | None = None
    processed_at: datetime | None = None
    is_preview: bool = False
    total_pay: Decimal = Decimal("0")
    entries: list[PayrollEntryOut] = []
