"""Org structure: departments and org levels."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True)
    head_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")
    members = relationship("User", back_populates="department", foreign_keys="User.department_id")

    @property
    def parent_name(self) -> str | None:
        from sqlalchemy import inspect

        if self.parent_id is None or "parent" in inspect(self).unloaded:
            return None
        return self.parent.name if self.parent else None


class OrgLevel(TimestampMixin, Base):
    """Organizational seniority level (L1-L6).

    Drives application authorization: L1 (Executive) is the most
    senior. ``rank`` orders the levels for display; permission ranks
    are canonicalized in ``app.utils.shared.LEVEL_RANK`` so runtime
    edits here cannot silently change permissions.
    """

    __tablename__ = "org_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    members = relationship("User", back_populates="org_level", foreign_keys="User.org_level_id")
