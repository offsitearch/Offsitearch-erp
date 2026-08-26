from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SAEnum

from app.db.base import Base, TimestampMixin
from app.utils.enums import AttendanceMethod, AttendanceStatus, _enum_values


class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus, native_enum=False, length=20, values_callable=_enum_values),
        default=AttendanceStatus.PRESENT,
        index=True,
    )
    late_minutes: Mapped[int] = mapped_column(Integer, default=0)
    total_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    overtime_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    check_in_method: Mapped[AttendanceMethod] = mapped_column(
        SAEnum(AttendanceMethod, native_enum=False, length=20, values_callable=_enum_values),
        default=AttendanceMethod.WEB,
    )
    check_in_location: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    marked_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
