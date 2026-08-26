"""Project management routes.

Endpoints: /projects — CRUD, phases, timeline, templates. Authenticated users; phase templates require Super Admin.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import can_manage_project, get_current_user, require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.projects.models import Project, ProjectPhase
from app.utils.enums import ProjectStatus
from app.modules.projects.schemas import (
    PhaseCreate,
    PhaseOut,
    PhaseTemplateOut,
    PhaseUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectPage,
    ProjectTeamIn,
    ProjectTeamOut,
    ProjectUpdate,
    TimelineOut,
)
from app.modules.projects import service as project_service
from app.modules.audit.service import log_audit
from app.utils.errors import ProjectError
from app.utils.shared import (
    LEVEL_RANK,
    domain_error,
    get_or_404,
    has_financial_access,
    has_min_level,
    is_staff_band,
    user_level_rank,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _reject_financial_writes(payload, current_user: User, fields: tuple[str, ...]) -> None:
    """Financial values may only be written by L0/L1 (write implies read)."""
    if has_financial_access(current_user):
        return
    touched = [
        f for f in fields if f in payload.model_fields_set and getattr(payload, f) is not None
    ]
    if touched:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Financial fields require executive access",
        )


@router.get("/templates", response_model=list[PhaseTemplateOut])
async def phase_templates(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    return project_service.list_templates()


@router.get("/options")
async def project_options(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    """Unscoped id/name list of active projects for pickers (any authed user).

    Deliberately declared before ``/{project_id}``.
    """
    return await project_service.active_project_options(db)


@router.get("", response_model=ProjectPage, response_model_exclude_none=True)
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=100),
    project_type: str | None = None,
    status: str | None = None,
    client_id: int | None = None,
    lead_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ProjectPage:
    scope_user_id = None
    if is_staff_band(current_user):
        scope_user_id = current_user.id
    items, total = await project_service.list_projects(
        db,
        search,
        project_type,
        status,
        client_id,
        lead_id,
        page,
        page_size,
        scope_user_id,
        include_financial=has_financial_access(current_user),
    )
    return ProjectPage(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
)
async def create_project(
    payload: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not has_min_level(current_user, "L3"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    _reject_financial_writes(payload, current_user, project_service.FINANCIAL_PROJECT_FIELDS)
    # New projects always start as drafts — the client cannot fast-forward
    # the lifecycle by posting an arbitrary status.
    payload = payload.model_copy(update={"status": ProjectStatus.DRAFT})
    if user_level_rank(current_user) > LEVEL_RANK["L2"]:
        payload = payload.model_copy(update={"project_lead_id": current_user.id})
    try:
        project = await project_service.create_project(db, payload)
    except ProjectError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "create", "project", entity_id=str(project.id))
    await db.commit()
    return await project_service.get_project(
        db, project.id, include_financial=has_financial_access(current_user)
    )


@router.get("/{project_id}", response_model=ProjectOut, response_model_exclude_none=True)
async def get_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if is_staff_band(current_user):
        await get_or_404(db, Project, project_id)
        if not await project_service.user_in_project(db, project_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    try:
        return await project_service.get_project(
            db, project_id, include_financial=has_financial_access(current_user)
        )
    except ProjectError as exc:
        raise domain_error(exc) from exc


@router.patch("/{project_id}", response_model=ProjectOut, response_model_exclude_none=True)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    project = await get_or_404(db, Project, project_id)
    if not await can_manage_project(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    _reject_financial_writes(payload, current_user, project_service.FINANCIAL_PROJECT_FIELDS)
    if (
        payload.project_lead_id is not None
        and payload.project_lead_id != project.project_lead_id
        and not has_min_level(current_user, "L2")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and managers can reassign a project lead",
        )
    try:
        updated = await project_service.update_project(db, project, payload)
    except ProjectError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "project", entity_id=str(project_id))
    await db.commit()
    return await project_service.get_project(
        db, updated.id, include_financial=has_financial_access(current_user)
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await get_or_404(db, Project, project_id)
    await project_service.soft_delete(db, project)
    await log_audit(db, current_user, "delete", "project", entity_id=str(project_id))
    await db.commit()


@router.post(
    "/{project_id}/team", response_model=ProjectTeamOut, status_code=status.HTTP_201_CREATED
)
async def add_team_member(
    project_id: int,
    payload: ProjectTeamIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    project = await get_or_404(db, Project, project_id)
    if not await can_manage_project(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    try:
        await project_service.add_team_member(db, project, payload.user_id, payload.role)
    except ProjectError as exc:
        raise domain_error(exc) from exc
    user = await db.get(User, payload.user_id)
    await log_audit(db, current_user, "add", "project_team", entity_id=str(project_id))
    await db.commit()
    return {
        "id": payload.user_id,
        "user_id": user.id,
        "name": user.name,
        "designation": user.designation,
        "role": payload.role,
    }


@router.delete("/{project_id}/team/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    project_id: int,
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await get_or_404(db, Project, project_id)
    if not await can_manage_project(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    try:
        await project_service.remove_team_member(db, project, user_id)
    except ProjectError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "remove", "project_team", entity_id=str(project_id))
    await db.commit()


@router.get("/{project_id}/timeline", response_model=TimelineOut)
async def project_timeline(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if is_staff_band(current_user):
        await get_or_404(db, Project, project_id)
        if not await project_service.user_in_project(db, project_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    project = await get_or_404(db, Project, project_id)
    return await project_service.get_timeline(db, project)


@router.post("/{project_id}/phases", response_model=PhaseOut, status_code=status.HTTP_201_CREATED)
async def add_phase(
    project_id: int,
    payload: PhaseCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    project = await get_or_404(db, Project, project_id)
    if not await can_manage_project(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    _reject_financial_writes(payload, current_user, ("studio_fee",))
    try:
        phase = await project_service.add_phase(db, project, payload)
    except ProjectError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "create", "project_phase", entity_id=str(phase.id))
    await db.commit()
    return {
        "id": phase.id,
        "project_id": phase.project_id,
        "name": phase.name,
        "order_index": phase.order_index,
        "start_date": phase.start_date,
        "end_date": phase.end_date,
        "status": phase.status.value,
        "completion_pct": phase.completion_pct,
    }


@router.patch("/{project_id}/phases/{phase_id}", response_model=PhaseOut)
async def update_phase(
    project_id: int,
    phase_id: int,
    payload: PhaseUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    project = await get_or_404(db, Project, project_id)
    if not await can_manage_project(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    _reject_financial_writes(payload, current_user, ("studio_fee",))
    phase = await db.get(ProjectPhase, phase_id)
    if phase is None or phase.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    try:
        updated = await project_service.update_phase(db, project, phase, payload)
    except ProjectError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "project_phase", entity_id=str(phase_id))
    await db.commit()
    return {
        "id": updated.id,
        "project_id": updated.project_id,
        "name": updated.name,
        "order_index": updated.order_index,
        "start_date": updated.start_date,
        "end_date": updated.end_date,
        "status": updated.status.value,
        "completion_pct": updated.completion_pct,
    }


@router.delete("/{project_id}/phases/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phase(
    project_id: int,
    phase_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    project = await get_or_404(db, Project, project_id)
    if not await can_manage_project(project, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    phase = await db.get(ProjectPhase, phase_id)
    if phase is None or phase.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    await project_service.delete_phase(db, project, phase)
    await log_audit(db, current_user, "delete", "project_phase", entity_id=str(phase_id))
    await db.commit()
