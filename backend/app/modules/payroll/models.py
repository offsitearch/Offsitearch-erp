from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from app.db.base import Base, TimestampMixin
from app.utils.enums import PayrollStatus, _enum_values


class PayrollRun(TimestampMixin, Base):
    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    month: Mapped[int] = mapped_column(Integer)
    year: Mapped[int] = mapped_column(Integer)
    status: Mapped[PayrollStatus] = mapped_column(
        SAEnum(PayrollStatus, native_enum=False, length=20, values_callable=_enum_values),
        default=PayrollStatus.DRAFT,
    )
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entries = relationship(
        "PayrollEntry",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="PayrollEntry.user_id",
    )
    processor = relationship("User", foreign_keys=[processed_by])

    __table_args__ = (UniqueConstraint("month", "year", name="uq_payroll_month_year"),)


class PayrollEntry(Base):
    __tablename__ = "payroll_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    payroll_run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    working_days: Mapped[int] = mapped_column(Integer, default=0)
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    payslip_path: Mapped[str | None] = mapped_column(String(255))

    run = relationship("PayrollRun", back_populates="entries")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (UniqueConstraint("payroll_run_id", "user_id", name="uq_payroll_entry_user"),)


class SalaryComponent(TimestampMixin, Base):
    __tablename__ = "salary_components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    ctc_annual: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    basic: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    hra: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    special_allowance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    pf_deduction: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    bank_name: Mapped[str | None] = mapped_column(String(120))
    account_number: Mapped[str | None] = mapped_column(String(30))
    ifsc_code: Mapped[str | None] = mapped_column(String(15))
    effective_from: Mapped[date | None] = mapped_column(Date)

    user = relationship("User", back_populates="salary")
