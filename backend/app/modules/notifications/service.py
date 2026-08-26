"""In-app notification creation and delivery.

Handles creating, listing, marking read, and querying unread counts.
"""

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


async def notify(
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str | None = None,
    type: str = "general",
    link: str | None = None,
) -> Notification:
    notification = Notification(user_id=user_id, title=title, body=body, type=type, link=link)
    db.add(notification)
    return notification


async def list_mine(
    db: AsyncSession, user_id: int, limit: int = 50, page: int = 1, page_size: int = 20
) -> tuple[list[Notification], int]:
    count_stmt = select(func.count()).where(Notification.user_id == user_id)
    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def unread_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
    )
    return int(result.scalar_one())


async def mark_read(db: AsyncSession, notification_id: int, user_id: int) -> Notification | None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    notification = result.scalar_one_or_none()
    if notification is not None and notification.read_at is None:
        notification.read_at = func.now()
    return notification


async def mark_all_read(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=func.now())
    )


async def delete_mine(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    result = await db.execute(
        delete(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
    )
    return bool(result.rowcount)
