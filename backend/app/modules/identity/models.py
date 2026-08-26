"""Identity: users, refresh tokens, authentication.

Owns: the ``users`` and ``refresh_tokens`` tables (``User``,
``RefreshToken`` models).
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from app.db.base import Base, TimestampMixin
from app.utils.enums import EmploymentType, _enum_values


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    employee_id: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True)
    org_level_id: Mapped[int | None] = mapped_column(ForeignKey("org_levels.id"), index=True)
    designation: Mapped[str | None] = mapped_column(String(120))
    reporting_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(10))
    blood_group: Mapped[str | None] = mapped_column(String(5))
    address: Mapped[str | None] = mapped_column(Text)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(120))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20))
    profile_photo: Mapped[str | None] = mapped_column(String(255))
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType, native_enum=False, length=20, values_callable=_enum_values),
        default=EmploymentType.FULL_TIME,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    department = relationship("Department", back_populates="members", foreign_keys=[department_id])
    org_level = relationship("OrgLevel", back_populates="members", foreign_keys=[org_level_id])
    reports_to = relationship("User", remote_side=[id])

    @property
    def org_level_code(self) -> str | None:
        from sqlalchemy import inspect

        if self.org_level_id is None or "org_level" in inspect(self).unloaded:
            return None
        return self.org_level.code if self.org_level else None

    @property
    def org_level_name(self) -> str | None:
        from sqlalchemy import inspect

        if self.org_level_id is None or "org_level" in inspect(self).unloaded:
            return None
        return self.org_level.name if self.org_level else None

    leave_balances = relationship(
        "LeaveBalance", back_populates="user", cascade="all, delete-orphan"
    )
    leaves = relationship("Leave", back_populates="user", foreign_keys="Leave.user_id")
    documents = relationship(
        "EmployeeDocument",
        back_populates="user",
        foreign_keys="EmployeeDocument.user_id",
        cascade="all, delete-orphan",
    )
    salary = relationship(
        "SalaryComponent", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
