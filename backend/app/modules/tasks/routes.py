"""Task management routes.

Endpoints: /tasks — CRUD, board view, checklist items, status updates. Authenticated users; bulk operations require Admin roles.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Project, User
from app.modules.projects import service as project_service
from app.modules.tasks import service as task_service
from app.modules.tasks.models import Task
from app.modules.tasks.schemas import (
    ChecklistItemIn,
    ChecklistItemOut,
    TaskBoardOut,
    TaskCreate,
    TaskOut,
    TaskPage,
    TaskUpdate,
)
from app.modules.notifications.service import notify
from app.modules.audit.service import log_audit
from app.utils.errors import TaskError
from app.utils.shared import (
    LEVEL_RANK,
    domain_error,
    get_or_404,
    has_min_level,
    is_staff_band,
    user_level_rank,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _project_led_by(db: AsyncSession, project_id: int | None, user: User) -> bool:
    if project_id is None:
        return True
    project = await db.get(Project, project_id)
    return project is not None and project.project_lead_id == user.id


async def _can_view_task(db: AsyncSession, task: Task, user: User) -> bool:
    if has_min_level(user, "L3"):
        return True
    if task.assigned_to == user.id:
        return True
    if task.project_id is None:
        return False
    return await project_service.user_in_project(db, task.project_id, user.id)


@router.get("/board", response_model=TaskBoardOut)
async def task_board(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: int | None = Query(default=None),
) -> dict:
    if is_staff_band(current_user) and project_id is not None:
        if not await project_service.user_in_project(db, project_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    scope_user_id = current_user.id if is_staff_band(current_user) else None
    return await task_service.get_board(db, project_id, scope_user_id)


@router.get("", response_model=TaskPage)
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=100),
    project_id: int | None = None,
    assignee: int | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TaskPage:
    scope_user_id = current_user.id if is_staff_band(current_user) else None
    items, total = await task_service.list_tasks(
        db, search, project_id, assignee, status, page, page_size, scope_user_id
    )
    return TaskPage(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not has_min_level(current_user, "L2"):
        if user_level_rank(current_user) > LEVEL_RANK["L3"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        if not await _project_led_by(db, payload.project_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project lead can create tasks for this project",
            )
    try:
        task = await task_service.create_task(db, payload, current_user)
    except TaskError as exc:
        raise domain_error(exc) from exc
    await _notify_assignment(db, task.assigned_to, task, current_user)
    await log_audit(db, current_user, "create", "task", entity_id=str(task.id))
    return await task_service.get_task(db, task.id)


async def _notify_assignment(
    db: AsyncSession, assignee_id: int | None, task, current_user: User
) -> None:
    if assignee_id and assignee_id != current_user.id:
        await notify(
            db,
            assignee_id,
            "Task assigned",
            f"'{task.title}' was assigned to you",
            "task",
            f"/tasks/{task.id}",
        )
        await db.commit()


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    task = await get_or_404(db, Task, task_id)
    if not await _can_view_task(db, task, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        return await task_service.get_task(db, task_id)
    except TaskError as exc:
        raise domain_error(exc) from exc


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    task = await get_or_404(db, Task, task_id)
    can_manage = has_min_level(current_user, "L2")
    if not can_manage and (
        task.assigned_to == current_user.id or task.assigned_by == current_user.id
    ):
        can_manage = True
    if not can_manage and has_min_level(current_user, "L3"):
        can_manage = await _project_led_by(db, task.project_id, current_user)
    if not can_manage:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assignee, creator, or the project lead can update this task",
        )
    if (
        not has_min_level(current_user, "L3")
        and payload.assigned_to is not None
        and payload.assigned_to != task.assigned_to
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners, managers, and project leads can reassign tasks",
        )
    old_assignee = task.assigned_to
    try:
        updated = await task_service.update_task(db, task, payload)
    except TaskError as exc:
        raise domain_error(exc) from exc
    if payload.assigned_to is not None and payload.assigned_to != old_assignee:
        await _notify_assignment(db, payload.assigned_to, updated, current_user)
    await log_audit(db, current_user, "update", "task", entity_id=str(task_id))
    return await task_service.get_task(db, updated.id)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    task = await get_or_404(db, Task, task_id)
    can_manage = has_min_level(current_user, "L2")
    if not can_manage and has_min_level(current_user, "L3"):
        can_manage = await _project_led_by(db, task.project_id, current_user)
    if not can_manage:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    await task_service.soft_delete(db, task)
    await log_audit(db, current_user, "delete", "task", entity_id=str(task_id))


@router.post(
    "/{task_id}/checklist", response_model=ChecklistItemOut, status_code=status.HTTP_201_CREATED
)
async def add_checklist_item(
    task_id: int,
    payload: ChecklistItemIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    task = await get_or_404(db, Task, task_id)
    if not await _can_view_task(db, task, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    item = await task_service.add_checklist_item(db, task, payload)
    await log_audit(db, current_user, "create", "task_checklist", entity_id=str(item.id))
    return {
        "id": item.id,
        "task_id": item.task_id,
        "text": item.text,
        "is_done": item.is_done,
    }


@router.patch("/{task_id}/checklist/{item_id}", response_model=ChecklistItemOut)
async def toggle_checklist_item(
    task_id: int,
    item_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    task = await get_or_404(db, Task, task_id)
    if not await _can_view_task(db, task, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    try:
        item = await task_service.toggle_checklist_item(db, task, item_id)
    except TaskError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "task_checklist", entity_id=str(item_id))
    return {
        "id": item.id,
        "task_id": item.task_id,
        "text": item.text,
        "is_done": item.is_done,
    }
