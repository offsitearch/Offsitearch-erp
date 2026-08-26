"""Company notice/announcement routes.

Endpoints: /notices — CRUD for notices. Read for all authenticated users; create/update/delete require Admin roles.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.notices.models import Notice
from app.modules.notices.schemas import NoticeCreate, NoticeOut, NoticeUpdate
from app.modules.notices import service as notice_service
from app.modules.identity.schemas import MessageResponse
from app.core.schemas import PaginatedResponse
from app.modules.audit.service import log_audit
from app.utils.shared import get_or_404, has_min_level

router = APIRouter(prefix="/notices", tags=["notices"])


@router.get("", response_model=PaginatedResponse[NoticeOut])
async def list_notices(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_inactive: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    is_admin = has_min_level(current_user, "L2")
    items, total = await notice_service.list_notices(
        db,
        include_inactive=include_inactive and is_admin,
        only_active_now=not is_admin,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
async def create_notice(
    payload: NoticeCreate,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await notice_service.create_notice(db, payload, current_user)
    await log_audit(
        db,
        current_user,
        "create",
        "notice",
        entity_id=str(result["id"]),
        details={"title": result["title"]},
    )
    await db.commit()
    return result


@router.patch("/{notice_id}", response_model=NoticeOut)
async def update_notice(
    notice_id: int,
    payload: NoticeUpdate,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    notice = await get_or_404(db, Notice, notice_id)
    result = await notice_service.update_notice(db, notice, payload)
    await log_audit(db, current_user, "update", "notice", entity_id=str(notice_id))
    await db.commit()
    return result


@router.delete("/{notice_id}", response_model=MessageResponse)
async def delete_notice(
    notice_id: int,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    notice = await get_or_404(db, Notice, notice_id)
    await notice_service.soft_delete(db, notice)
    await log_audit(db, current_user, "delete", "notice", entity_id=str(notice_id))
    await db.commit()
    return MessageResponse(message="Notice deleted")
