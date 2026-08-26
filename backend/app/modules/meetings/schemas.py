from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import MeetingStatus, MeetingType, RsvpStatus


class MeetingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    meeting_type: MeetingType = MeetingType.INTERNAL
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=600)
    location: str | None = Field(default=None, max_length=255)
    meeting_link: str | None = Field(default=None, max_length=500)
    attendee_ids: list[int] = []


class MeetingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    meeting_type: MeetingType | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=600)
    location: str | None = Field(default=None, max_length=255)
    meeting_link: str | None = Field(default=None, max_length=500)
    status: MeetingStatus | None = None
    attendee_ids: list[int] | None = None


class MeetingAttendeeOut(BaseModel):
    user_id: int
    name: str
    email: str
    rsvp_status: RsvpStatus


class MeetingOut(BaseModel):
    id: int
    title: str
    description: str | None
    meeting_type: str
    scheduled_at: datetime
    duration_minutes: int
    location: str | None
    meeting_link: str | None
    status: str
    organizer_id: int | None
    organizer_name: str | None
    attendees: list[MeetingAttendeeOut] = []
    my_rsvp: RsvpStatus | None = None
