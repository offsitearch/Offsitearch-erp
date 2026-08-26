"""Notice board CRUD, publish scheduling, and expiry management."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.modules.notices.models import Notice
from app.modules.notices.schemas import NoticeCreate, NoticeUpdate
from app.utils.enums import NoticeImportance
from app.utils.shared import now_local


def _parse_importance(value: NoticeImportance | None) -> NoticeImportance:
    if value is None:
        return NoticeImportance.MEDIUM
    return value


async def list_notices(
    db: AsyncSession,
    include_inactive: bool = False,
    only_active_now: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = (
        select(Notice, User.name)
        .outerjoin(User, User.id == Notice.created_by)
        .order_by(Notice.is_pinned.desc(), Notice.created_at.desc())
    )
    if not include_inactive:
        stmt = stmt.where(Notice.is_active.is_(True))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
    today = now_local().date()
    result: list[dict] = []
    for notice, author_name in rows:
        if only_active_now:
            if notice.publish_date and notice.publish_date > today:
                continue
            if notice.expiry_date and notice.expiry_date < today:
                continue
        result.append(_profile(notice, author_name))
    return result, total


def _profile(notice: Notice, author_name: str | None = None) -> dict:
    return {
        "id": notice.id,
        "title": notice.title,
        "body": notice.body,
        "importance": notice.importance.value,
        "is_pinned": notice.is_pinned,
        "is_active": notice.is_active,
        "publish_date": notice.publish_date,
        "expiry_date": notice.expiry_date,
        "created_by": notice.created_by,
        "author_name": author_name,
        "created_at": notice.created_at,
    }


async def create_notice(db: AsyncSession, payload: NoticeCreate, user: User) -> dict:
    notice = Notice(
        title=payload.title,
        body=payload.body,
        importance=_parse_importance(payload.importance),
        is_pinned=payload.is_pinned,
        publish_date=payload.publish_date,
        expiry_date=payload.expiry_date,
        created_by=user.id,
    )
    db.add(notice)
    await db.flush()
    await db.commit()
    return _profile(notice, user.name)


async def update_notice(db: AsyncSession, notice: Notice, payload: NoticeUpdate) -> dict:
    if payload.title is not None:
        notice.title = payload.title
    if payload.body is not None:
        notice.body = payload.body
    if payload.importance is not None:
        notice.importance = _parse_importance(payload.importance)
    if payload.is_pinned is not None:
        notice.is_pinned = payload.is_pinned
    if payload.is_active is not None:
        notice.is_active = payload.is_active
    if payload.publish_date is not None:
        notice.publish_date = payload.publish_date
    if payload.expiry_date is not None:
        notice.expiry_date = payload.expiry_date
    await db.commit()
    await db.refresh(notice)
    return _profile(notice)


async def soft_delete(db: AsyncSession, notice: Notice) -> None:
    notice.is_active = False
    await db.commit()
