from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=255)
    hsn_sac: str | None = Field(default=None, max_length=20)
    quantity: Decimal = Field(default=Decimal("1"), ge=0)
    rate: Decimal = Field(default=Decimal("0"), ge=0)


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    description: str
    hsn_sac: str | None = None
    quantity: Decimal
    rate: Decimal
    amount: Decimal


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int
    project_id: int | None = None
    invoice_date: date
    due_date: date
    tax_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    items: list[InvoiceItemIn] = Field(min_length=1)
    notes: str | None = None
    terms: str | None = None


class InvoiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int | None = None
    project_id: int | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    tax_percent: Decimal | None = Field(default=None, ge=0, le=100)
    items: list[InvoiceItemIn] | None = None
    notes: str | None = None
    terms: str | None = None


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    client_id: int
    client_name: str | None = None
    project_id: int | None = None
    project_code: str | None = None
    invoice_date: date
    due_date: date
    subtotal: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    total: Decimal
    status: str
    sent_at: datetime | None
    paid_amount: Decimal
    payment_date: date | None
    payment_method: str | None
    notes: str | None
    terms: str | None
    items: list[InvoiceItemOut] = []


class InvoicePaymentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0)
    method: str = Field(default="bank_transfer")
    payment_date: date | None = None


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=80)
    description: str | None = None
    amount: Decimal = Field(gt=0)
    expense_date: date | None = None
    project_id: int | None = None
    paid_by: str | None = None


class ExpenseOut(BaseModel):
    id: int
    category: str
    description: str | None
    amount: Decimal
    expense_date: date | None
    project_id: int | None
    project_code: str | None = None
    paid_by: str | None
    receipt_path: str | None
    status: str
    approved_by: int | None
    approved_at: datetime | None


class ExpenseDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approve: bool
    note: str | None = None
