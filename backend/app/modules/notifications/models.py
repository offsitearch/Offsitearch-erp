from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # Composite index for unread_count: WHERE user_id = ? AND read_at IS NULL
        # Handled via Alembic migration (index name: ix_notifications_user_read).
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(String(500))
    type: Mapped[str] = mapped_column(String(30), default="general")
    link: Mapped[str | None] = mapped_column(String(255))
    read_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
