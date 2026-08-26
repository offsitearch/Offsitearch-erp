"""Site visit logging and photo upload routes.

Endpoints: /site-visits — CRUD with image attachments. Authenticated users; admins see all visits, others see own only.
"""

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.storage import get_storage
from app.db.session import get_db
from app.models import Project, User
from app.modules.projects import service as project_service
from app.modules.site_visits import service as site_visit_service
from app.modules.site_visits.models import SiteVisit
from app.modules.site_visits.schemas import (
    SiteVisitCreate,
    SiteVisitOut,
    SiteVisitPhotoOut,
    SiteVisitUpdate,
)
from app.modules.identity.schemas import MessageResponse
from app.core.schemas import PaginatedResponse
from app.modules.audit.service import log_audit
from app.utils.errors import SiteVisitError
from app.utils.pdf import site_visit_pdf
from app.utils.shared import (
    LEVEL_RANK,
    domain_error,
    get_or_404,
    has_min_level,
    is_staff_band,
    user_level_rank,
)
from app.utils.upload import ALLOWED_IMAGE_EXTENSIONS, validate_upload

router = APIRouter(prefix="/site-visits", tags=["site-visits"])


async def _can_manage(db: AsyncSession, visit: SiteVisit, user: User) -> bool:
    if has_min_level(user, "L2") or visit.created_by == user.id:
        return True
    if has_min_level(user, "L3") and visit.project_id is not None:
        project = await db.get(Project, visit.project_id)
        return project is not None and project.project_lead_id == user.id
    return False


async def _can_view(db: AsyncSession, visit: SiteVisit, user: User) -> bool:
    if await _can_manage(db, visit, user):
        return True
    if is_staff_band(user) and visit.project_id is not None:
        return await project_service.user_in_project(db, visit.project_id, user.id)
    return False


@router.get("", response_model=PaginatedResponse[SiteVisitOut])
async def list_visits(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: int | None = None,
    status_: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    scope_project_ids: list[int] | None = None
    if has_min_level(current_user, "L2"):
        include_all = True
    else:
        include_all = False
        led_rows = await db.execute(
            select(Project.id).where(Project.project_lead_id == current_user.id)
        )
        scope_project_ids = list(led_rows.scalars().all())
        if is_staff_band(current_user):
            member_ids = await project_service.user_project_ids(db, current_user.id)
            scope_project_ids = sorted(set(scope_project_ids) | set(member_ids))
    items, total = await site_visit_service.list_visits(
        db,
        include_all=include_all,
        current_user_id=current_user.id,
        project_id=project_id,
        status=status_,
        scope_project_ids=scope_project_ids,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=SiteVisitOut, status_code=status.HTTP_201_CREATED)
async def create_visit(
    payload: SiteVisitCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not has_min_level(current_user, "L2"):
        if user_level_rank(current_user) > LEVEL_RANK["L3"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        project = await db.get(Project, payload.project_id)
        if project is None or not project.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        if project.project_lead_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project lead can create visits for this project",
            )
    try:
        result = await site_visit_service.create_visit(db, payload, current_user)
    except SiteVisitError as exc:
        raise domain_error(exc) from exc
    await log_audit(
        db,
        current_user,
        "create",
        "site_visit",
        entity_id=str(result["id"]),
        details={
            "project_id": result["project_id"],
            "visit_date": result["visit_date"].isoformat(),
        },
    )
    await db.commit()
    return result


@router.get("/{visit_id}", response_model=SiteVisitOut)
async def get_visit(
    visit_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    visit = await get_or_404(db, SiteVisit, visit_id)
    if not await _can_view(db, visit, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    return await site_visit_service._profile(db, visit)


@router.patch("/{visit_id}", response_model=SiteVisitOut)
async def update_visit(
    visit_id: int,
    payload: SiteVisitUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    visit = await get_or_404(db, SiteVisit, visit_id)
    if not await _can_manage(db, visit, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the creator")
    try:
        result = await site_visit_service.update_visit(db, visit, payload)
    except SiteVisitError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "site_visit", entity_id=str(visit_id))
    await db.commit()
    return result


@router.delete("/{visit_id}", response_model=MessageResponse)
async def delete_visit(
    visit_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    visit = await get_or_404(db, SiteVisit, visit_id)
    if not await _can_manage(db, visit, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the creator")
    await log_audit(db, current_user, "delete", "site_visit", entity_id=str(visit_id))
    await site_visit_service.delete_visit(db, visit)
    await db.commit()
    return MessageResponse(message="Site visit deleted")


@router.post(
    "/{visit_id}/photos", response_model=SiteVisitPhotoOut, status_code=status.HTTP_201_CREATED
)
async def upload_photo(
    visit_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form()] = None,
) -> dict:
    visit = await get_or_404(db, SiteVisit, visit_id)
    if not await _can_manage(db, visit, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the creator")
    content = await file.read()
    suffix = validate_upload(file, content, allowed=ALLOWED_IMAGE_EXTENSIONS, label="photo")
    return await site_visit_service.add_photo(db, visit, content, suffix, caption, current_user)


@router.get("/{visit_id}/photos/{photo_id}")
async def download_photo(
    visit_id: int,
    photo_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    visit = await get_or_404(db, SiteVisit, visit_id)
    if not await _can_view(db, visit, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    photo = await site_visit_service.get_photo(db, photo_id)
    if photo.site_visit_id != visit.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    storage = get_storage()
    try:
        content = await storage.download(photo.file_path)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Photo file missing from storage"
        )
    filename = Path(photo.file_path).name
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{visit_id}/report")
async def visit_report(
    visit_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    visit = await get_or_404(db, SiteVisit, visit_id)
    if not await _can_view(db, visit, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    profile = await site_visit_service._profile(db, visit)
    content = site_visit_pdf(
        project_code=profile["project_code"] or "",
        project_name=profile["project_name"] or "",
        visit_date=profile["visit_date"],
        purpose=profile["purpose"],
        location=profile["location"],
        notes=profile["notes"],
        attendance_notes=profile["attendance_notes"],
        photos=profile["photos"],
    )
    filename = f"site_visit_{visit_id}_{visit.visit_date.isoformat()}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
