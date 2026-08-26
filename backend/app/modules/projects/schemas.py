from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import PhaseStatus, ProjectStatus, ProjectType


class ProjectTeamIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    role: str | None = Field(default=None, max_length=80)


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    project_type: ProjectType
    category: str | None = Field(default=None, max_length=80)
    client_id: int | None = None
    location: str | None = Field(default=None, max_length=255)
    plot_area: Decimal | None = None
    built_up_area: Decimal | None = None
    no_of_floors: str | None = Field(default=None, max_length=20)
    coordinates: str | None = Field(default=None, max_length=80)
    budget: Decimal | None = None
    studio_fee: Decimal | None = None
    fee_type: str | None = Field(default=None, max_length=20)
    fee_percent: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus = ProjectStatus.DRAFT
    project_lead_id: int | None = None
    priority: str = Field(default="medium", max_length=10)
    team: list[ProjectTeamIn] = []


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    project_type: ProjectType | None = None
    category: str | None = Field(default=None, max_length=80)
    client_id: int | None = None
    location: str | None = Field(default=None, max_length=255)
    plot_area: Decimal | None = None
    built_up_area: Decimal | None = None
    no_of_floors: str | None = Field(default=None, max_length=20)
    coordinates: str | None = Field(default=None, max_length=80)
    budget: Decimal | None = None
    studio_fee: Decimal | None = None
    fee_type: str | None = Field(default=None, max_length=20)
    fee_percent: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus | None = None
    project_lead_id: int | None = None
    priority: str | None = Field(default=None, max_length=10)


class ProjectTeamOut(BaseModel):
    id: int
    user_id: int
    name: str
    designation: str | None
    role: str | None


class PhaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    status: PhaseStatus = PhaseStatus.NOT_STARTED
    completion_pct: Decimal = Field(default=0, ge=0, le=100)
    studio_fee: Decimal | None = None


class PhaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=150)
    start_date: date | None = None
    end_date: date | None = None
    status: PhaseStatus | None = None
    completion_pct: Decimal | None = Field(default=None, ge=0, le=100)
    studio_fee: Decimal | None = None


class PhaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    order_index: int
    start_date: date | None
    end_date: date | None
    status: str
    completion_pct: Decimal
    studio_fee: Decimal | None = None


class ProjectListItem(BaseModel):
    id: int
    project_code: str
    name: str
    project_type: str
    client_id: int | None = None
    client_name: str | None = None
    location: str | None = None
    status: str
    project_lead_id: int | None = None
    lead_name: str | None = None
    priority: str
    start_date: date | None = None
    end_date: date | None = None
    progress_pct: Decimal
    hours_logged: Decimal = Decimal("0")
    budget: Decimal | None = None
    studio_fee: Decimal | None = None


class ProjectOut(BaseModel):
    id: int
    project_code: str
    name: str
    description: str | None = None
    project_type: str
    category: str | None = None
    client_id: int | None = None
    client_name: str | None = None
    location: str | None = None
    plot_area: Decimal | None = None
    built_up_area: Decimal | None = None
    no_of_floors: str | None = None
    coordinates: str | None = None
    budget: Decimal | None = None
    studio_fee: Decimal | None = None
    fee_type: str | None = None
    fee_percent: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str
    project_lead_id: int | None = None
    lead_name: str | None = None
    priority: str
    progress_pct: Decimal
    hours_logged: Decimal = Decimal("0")
    team: list[ProjectTeamOut] = []
    phases: list[PhaseOut] = []
    created_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int


class TimelineRow(BaseModel):
    id: int
    name: str
    order_index: int
    status: str
    start_date: date | None
    end_date: date | None
    completion_pct: Decimal


class TimelineOut(BaseModel):
    project_id: int
    start_date: date | None
    end_date: date | None
    rows: list[TimelineRow]


class PhaseTemplateOut(BaseModel):
    project_type: str
    label: str
    phases: list[str]
