from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import NoticeImportance


class NoticeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    body: str | None = None
    importance: NoticeImportance = NoticeImportance.MEDIUM
    is_pinned: bool = False
    publish_date: date | None = None
    expiry_date: date | None = None


class NoticeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None
    importance: NoticeImportance | None = None
    is_pinned: bool | None = None
    is_active: bool | None = None
    publish_date: date | None = None
    expiry_date: date | None = None


class NoticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str | None
    importance: str
    is_pinned: bool
    is_active: bool
    publish_date: date | None
    expiry_date: date | None
    created_by: int | None
    created_at: datetime
