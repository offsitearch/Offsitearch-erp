from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    project_id: int | None = None
    phase_id: int | None = None
    assigned_to: int | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    start_date: date | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    tags: list[str] | None = None


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    project_id: int | None = None
    phase_id: int | None = None
    assigned_to: int | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    start_date: date | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = Field(default=None, ge=0)
    actual_hours: Decimal | None = Field(default=None, ge=0)
    tags: list[str] | None = None


class ChecklistItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=255)


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    text: str
    is_done: bool


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    project_id: int | None
    project_name: str | None = None
    phase_id: int | None
    assigned_to: int | None
    assignee_name: str | None = None
    priority: str
    status: str
    start_date: date | None
    due_date: date | None
    estimated_hours: Decimal | None
    actual_hours: Decimal | None
    parent_task_id: int | None
    tags: list[str] | None
    checklist: list[ChecklistItemOut] = []
    created_at: datetime
    updated_at: datetime


class TaskPage(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    page_size: int


class TaskBoardColumn(BaseModel):
    status: str
    tasks: list[TaskOut]


class TaskBoardOut(BaseModel):
    columns: list[TaskBoardColumn]
