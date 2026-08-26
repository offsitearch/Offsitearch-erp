from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from app.db.base import Base, TimestampMixin
from app.utils.enums import SiteVisitStatus, _enum_values


class SiteVisit(TimestampMixin, Base):
    __tablename__ = "site_visits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    visit_date: Mapped[date] = mapped_column(Date, index=True)
    start_time: Mapped[Time | None] = mapped_column(Time)
    end_time: Mapped[Time | None] = mapped_column(Time)
    status: Mapped[SiteVisitStatus] = mapped_column(
        SAEnum(SiteVisitStatus, native_enum=False, length=15, values_callable=_enum_values),
        default=SiteVisitStatus.SCHEDULED,
    )
    purpose: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    weather: Mapped[str | None] = mapped_column(String(80))
    attendance_notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project", foreign_keys=[project_id])
    creator = relationship("User", foreign_keys=[created_by])
    photos = relationship(
        "SiteVisitPhoto",
        back_populates="site_visit",
        cascade="all, delete-orphan",
        order_by="SiteVisitPhoto.id",
    )


class SiteVisitPhoto(Base):
    __tablename__ = "site_visit_photos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    site_visit_id: Mapped[int] = mapped_column(ForeignKey("site_visits.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(255))
    caption: Mapped[str | None] = mapped_column(String(255))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    site_visit = relationship("SiteVisit", back_populates="photos")
    uploader = relationship("User", foreign_keys=[uploaded_by])
