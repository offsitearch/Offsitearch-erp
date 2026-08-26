"""Tasks CRUD, board view, checklist, and assignments."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, User
from app.modules.tasks.models import Task, TaskChecklist
from app.modules.tasks.schemas import ChecklistItemIn, TaskCreate, TaskUpdate
from app.modules.projects import service as project_service
from app.utils.enums import TaskStatus
from app.utils.errors import TaskError


def _task_dict(
    task: Task,
    project_name: str | None = None,
    assignee_name: str | None = None,
    checklist: list[TaskChecklist] | None = None,
) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "project_id": task.project_id,
        "project_name": project_name,
        "phase_id": task.phase_id,
        "assigned_to": task.assigned_to,
        "assignee_name": assignee_name,
        "priority": task.priority.value,
        "status": task.status.value,
        "start_date": task.start_date,
        "due_date": task.due_date,
        "estimated_hours": task.estimated_hours,
        "actual_hours": task.actual_hours,
        "parent_task_id": task.parent_task_id,
        "tags": task.tags,
        "checklist": [
            {"id": item.id, "task_id": item.task_id, "text": item.text, "is_done": item.is_done}
            for item in (checklist or [])
        ],
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


async def _checklist_for(db: AsyncSession, task_id: int) -> list[TaskChecklist]:
    return (
        (
            await db.execute(
                select(TaskChecklist)
                .where(TaskChecklist.task_id == task_id)
                .order_by(TaskChecklist.id)
            )
        )
        .scalars()
        .all()
    )


def _scope_cond(scope_user_id: int | None, project_ids: list[int] | None = None):
    if scope_user_id is None:
        return None
    if project_ids is None:
        project_ids = []
    return or_(
        Task.assigned_to == scope_user_id,
        Task.project_id.in_(project_ids),
    )


async def list_tasks(
    db: AsyncSession,
    search: str | None,
    project_id: int | None,
    assignee: int | None,
    status: str | None,
    page: int,
    page_size: int,
    scope_user_id: int | None = None,
) -> tuple[list[dict], int]:
    base = (
        select(Task, Project.name, User.name)
        .outerjoin(Project, Project.id == Task.project_id)
        .outerjoin(User, User.id == Task.assigned_to)
        .where(Task.is_active.is_(True))
    )
    count_stmt = select(func.count(Task.id)).where(Task.is_active.is_(True))

    if scope_user_id is not None:
        scope_cond = _scope_cond(
            scope_user_id, await project_service.user_project_ids(db, scope_user_id)
        )
        base = base.where(scope_cond)
        count_stmt = count_stmt.where(scope_cond)

    if search:
        like = f"%{search}%"
        cond = Task.title.ilike(like)
        base = base.where(cond)
        count_stmt = count_stmt.where(cond)
    if project_id is not None:
        base = base.where(Task.project_id == project_id)
        count_stmt = count_stmt.where(Task.project_id == project_id)
    if assignee is not None:
        base = base.where(Task.assigned_to == assignee)
        count_stmt = count_stmt.where(Task.assigned_to == assignee)
    if status:
        base = base.where(Task.status == TaskStatus(status))
        count_stmt = count_stmt.where(Task.status == TaskStatus(status))

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Task.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    items: list[dict] = []
    for task, project_name, assignee_name in rows:
        items.append(_task_dict(task, project_name, assignee_name))
    return items, total


async def get_task(db: AsyncSession, task_id: int) -> dict:
    row = (
        await db.execute(
            select(Task, Project.name, User.name)
            .outerjoin(Project, Project.id == Task.project_id)
            .outerjoin(User, User.id == Task.assigned_to)
            .where(Task.id == task_id, Task.is_active.is_(True))
        )
    ).first()
    if row is None:
        raise TaskError("Task not found", 404)
    task, project_name, assignee_name = row
    checklist = await _checklist_for(db, task.id)
    return _task_dict(task, project_name, assignee_name, checklist)


async def _validate_refs(db: AsyncSession, project_id: int | None, assignee: int | None) -> None:
    if project_id is not None:
        project = await db.get(Project, project_id)
        if project is None or not project.is_active:
            raise TaskError("Project not found", 404)
    if assignee is not None:
        assignee_user = await db.get(User, assignee)
        if assignee_user is None or not assignee_user.is_active:
            raise TaskError("Assignee not found", 404)


async def create_task(db: AsyncSession, payload: TaskCreate, assigned_by: User) -> Task:
    await _validate_refs(db, payload.project_id, payload.assigned_to)
    task = Task(
        title=payload.title,
        description=payload.description,
        project_id=payload.project_id,
        phase_id=payload.phase_id,
        assigned_to=payload.assigned_to,
        assigned_by=assigned_by.id,
        priority=payload.priority,
        status=payload.status,
        start_date=payload.start_date,
        due_date=payload.due_date,
        estimated_hours=payload.estimated_hours,
        tags=payload.tags,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task: Task, payload: TaskUpdate) -> Task:
    data = payload.model_dump(exclude_unset=True)
    if "project_id" in data:
        await _validate_refs(db, data["project_id"], None)
    if "assigned_to" in data:
        await _validate_refs(db, None, data["assigned_to"])
    if "status" in data and data["status"] is not None:
        from app.utils.state_machines import assert_transition

        assert_transition(task.status, data["status"], "task")
    for field, value in data.items():
        if value is not None:
            setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


async def soft_delete(db: AsyncSession, task: Task) -> None:
    task.is_active = False
    await db.commit()


async def add_checklist_item(
    db: AsyncSession, task: Task, payload: ChecklistItemIn
) -> TaskChecklist:
    item = TaskChecklist(task_id=task.id, text=payload.text)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def toggle_checklist_item(
    db: AsyncSession, task: Task, item_id: int, is_done: bool | None = None
) -> TaskChecklist:
    item = await db.get(TaskChecklist, item_id)
    if item is None or item.task_id != task.id:
        raise TaskError("Checklist item not found", 404)
    item.is_done = not item.is_done if is_done is None else is_done
    await db.commit()
    await db.refresh(item)
    return item


async def get_board(
    db: AsyncSession, project_id: int | None, scope_user_id: int | None = None
) -> dict:
    stmt = (
        select(Task, Project.name, User.name)
        .outerjoin(Project, Project.id == Task.project_id)
        .outerjoin(User, User.id == Task.assigned_to)
        .where(Task.is_active.is_(True))
    )
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if scope_user_id is not None:
        scope_cond = _scope_cond(
            scope_user_id, await project_service.user_project_ids(db, scope_user_id)
        )
        stmt = stmt.where(scope_cond)
    rows = (await db.execute(stmt.order_by(Task.id.desc()))).all()

    columns = []
    for status in TaskStatus:
        tasks = [
            _task_dict(task, project_name, assignee_name)
            for task, project_name, assignee_name in rows
            if task.status == status
        ]
        columns.append({"status": status.value, "tasks": tasks})
    return {"columns": columns}
