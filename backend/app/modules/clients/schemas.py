from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.utils.enums import ClientType, CommunicationType, DealStage


class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    client_type: ClientType = ClientType.INDIVIDUAL
    company_name: str | None = Field(default=None, max_length=200)
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    phone_secondary: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = None
    gst_number: str | None = Field(default=None, max_length=20)
    pan_number: str | None = Field(default=None, max_length=20)
    source: str | None = Field(default=None, max_length=40)
    referred_by: int | None = None
    budget_range: str | None = Field(default=None, max_length=40)
    interest: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    deal_stage: DealStage = DealStage.LEAD
    next_follow_up_date: date | None = None
    next_follow_up_action: str | None = Field(default=None, max_length=120)


class ClientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=200)
    client_type: ClientType | None = None
    company_name: str | None = Field(default=None, max_length=200)
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    phone_secondary: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    address: str | None = None
    gst_number: str | None = Field(default=None, max_length=20)
    pan_number: str | None = Field(default=None, max_length=20)
    source: str | None = Field(default=None, max_length=40)
    referred_by: int | None = None
    budget_range: str | None = Field(default=None, max_length=40)
    interest: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    deal_stage: DealStage | None = None
    next_follow_up_date: date | None = None
    next_follow_up_action: str | None = Field(default=None, max_length=120)


class ClientListItem(BaseModel):
    id: int
    name: str
    client_type: str
    company_name: str | None
    contact_person: str | None
    phone: str | None
    email: str | None
    source: str | None
    budget_range: str | None = None
    deal_stage: str
    next_follow_up_date: date | None
    is_active: bool
    project_count: int = 0


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    client_type: str
    company_name: str | None
    contact_person: str | None
    phone: str | None
    phone_secondary: str | None
    email: str | None
    address: str | None
    gst_number: str | None
    pan_number: str | None
    source: str | None
    referred_by: int | None
    referred_name: str | None = None
    budget_range: str | None = None
    interest: str | None
    notes: str | None
    deal_stage: str
    next_follow_up_date: date | None
    next_follow_up_action: str | None
    is_active: bool
    created_at: datetime


class ClientPage(BaseModel):
    items: list[ClientListItem]
    total: int
    page: int
    page_size: int


class ClientProjectSummary(BaseModel):
    id: int
    project_code: str
    name: str
    project_type: str
    status: str
    start_date: date | None
    end_date: date | None
    progress_pct: Decimal
    budget: Decimal | None
    studio_fee: Decimal | None


class CommunicationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: CommunicationType
    subject: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    occurred_at: datetime | None = None


class CommunicationOut(BaseModel):
    id: int
    client_id: int
    user_id: int
    user_name: str
    type: str
    subject: str | None
    notes: str | None
    occurred_at: datetime


class FinancialSummary(BaseModel):
    total_projects: int = 0
    total_budget: Decimal | None = None
    total_studio_fee: Decimal | None = None
    invoiced: Decimal | None = None
    received: Decimal | None = None
    outstanding: Decimal | None = None


class ClientProfileOut(BaseModel):
    client: ClientOut
    projects: list[ClientProjectSummary] = []
    communications: list[CommunicationOut] = []
    financial_summary: FinancialSummary
