from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import SiteVisitStatus


class SiteVisitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int
    visit_date: date
    start_time: time | None = None
    end_time: time | None = None
    status: SiteVisitStatus = SiteVisitStatus.SCHEDULED
    purpose: str | None = None
    notes: str | None = None
    location: str | None = Field(default=None, max_length=255)
    weather: str | None = Field(default=None, max_length=80)
    attendance_notes: str | None = None


class SiteVisitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int | None = None
    visit_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    status: SiteVisitStatus | None = None
    purpose: str | None = None
    notes: str | None = None
    location: str | None = Field(default=None, max_length=255)
    weather: str | None = Field(default=None, max_length=80)
    attendance_notes: str | None = None


class SiteVisitPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    caption: str | None
    uploaded_by: int | None
    uploaded_at: datetime


class SiteVisitOut(BaseModel):
    id: int
    project_id: int
    project_code: str | None
    project_name: str | None
    visit_date: date
    start_time: time | None
    end_time: time | None
    status: str
    purpose: str | None
    notes: str | None
    location: str | None
    weather: str | None
    attendance_notes: str | None
    created_by: int | None
    creator_name: str | None
    completed_at: datetime | None
    photos: list[SiteVisitPhotoOut] = []
