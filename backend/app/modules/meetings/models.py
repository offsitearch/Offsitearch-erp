from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from app.db.base import Base, TimestampMixin
from app.utils.enums import MeetingStatus, MeetingType, RsvpStatus, _enum_values


class Meeting(TimestampMixin, Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    meeting_type: Mapped[MeetingType] = mapped_column(
        SAEnum(MeetingType, native_enum=False, length=15, values_callable=_enum_values),
        default=MeetingType.INTERNAL,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    location: Mapped[str | None] = mapped_column(String(255))
    meeting_link: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[MeetingStatus] = mapped_column(
        SAEnum(MeetingStatus, native_enum=False, length=15, values_callable=_enum_values),
        default=MeetingStatus.SCHEDULED,
    )
    organizer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)

    organizer = relationship("User", foreign_keys=[organizer_id])
    attendees = relationship(
        "MeetingAttendee",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="MeetingAttendee.id",
    )


class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rsvp_status: Mapped[RsvpStatus] = mapped_column(
        SAEnum(RsvpStatus, native_enum=False, length=10, values_callable=_enum_values),
        default=RsvpStatus.PENDING,
    )

    meeting = relationship("Meeting", back_populates="attendees")
    user = relationship("User", foreign_keys=[user_id])
