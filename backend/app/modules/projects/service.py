"""Projects CRUD, phases, progress tracking, team, and timeline."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Client, Task, User
from app.modules.projects.defaults import PROJECT_TYPE_TEMPLATES
from app.modules.projects.models import Project, ProjectPhase, ProjectTeam
from app.modules.projects.schemas import (
    PhaseCreate,
    PhaseUpdate,
    ProjectCreate,
    ProjectTeamIn,
    ProjectUpdate,
)
from app.utils.enums import PhaseStatus, ProjectType
from app.utils.errors import ProjectError
from app.utils.shared import now_local

_PCT = Decimal("0.01")

# Financial fields (see docs/architecture/financial_access_policy.md):
# omitted from every response for callers without financial access,
# and rejected on writes from the same callers.
FINANCIAL_PROJECT_FIELDS = ("budget", "studio_fee", "fee_type", "fee_percent")


def _strip_financial(data: dict, include_financial: bool) -> dict:
    if not include_financial:
        for field in FINANCIAL_PROJECT_FIELDS:
            data.pop(field, None)
    return data


def _label(project_type: str) -> str:
    template = PROJECT_TYPE_TEMPLATES.get(project_type)
    return template["label"] if template else project_type.replace("_", " ").title()


def _template_phases(project_type: str) -> list[str]:
    template = PROJECT_TYPE_TEMPLATES.get(project_type)
    return template["phases"] if template else []


def _compute_progress(phases: list[ProjectPhase]) -> Decimal:
    if not phases:
        return Decimal("0.00")
    total = sum((phase.completion_pct or Decimal("0")) for phase in phases)
    return (total / len(phases)).quantize(_PCT)


async def next_project_code(db: AsyncSession, year: int) -> str:
    codes = (await db.execute(select(Project.project_code))).scalars().all()
    prefix = f"ARC-{year}-"
    nums: list[int] = []
    for code in codes:
        if code and code.startswith(prefix):
            try:
                nums.append(int(code[len(prefix) :]))
            except ValueError:
                pass
    return f"{prefix}{max(nums, default=0) + 1:03d}"


def _phase_dates(
    start: date | None, end: date | None, count: int
) -> list[tuple[date | None, date | None]]:
    if not start or not end or count == 0 or start > end:
        return [(None, None)] * count
    total = (end - start).days
    step = max(total // count, 1)
    result: list[tuple[date | None, date | None]] = []
    cursor = start
    for i in range(count):
        phase_start = cursor
        phase_end = min(phase_start + timedelta(days=step - 1), end)
        if i == count - 1:
            phase_end = end
        result.append((phase_start, phase_end))
        cursor = phase_end + timedelta(days=1)
    return result


def _apply_phase_dates(phases: list[ProjectPhase], start: date | None, end: date | None) -> None:
    pairs = _phase_dates(start, end, len(phases))
    for phase, (p_start, p_end) in zip(phases, pairs):
        phase.start_date = p_start
        phase.end_date = p_end


async def _phases_for(db: AsyncSession, project_id: int) -> list[ProjectPhase]:
    return (
        (
            await db.execute(
                select(ProjectPhase)
                .where(ProjectPhase.project_id == project_id)
                .order_by(ProjectPhase.order_index)
            )
        )
        .scalars()
        .all()
    )


def scope_condition(scope_user_id: int | None):
    if scope_user_id is None:
        return None
    return or_(
        Project.project_lead_id == scope_user_id,
        Project.id.in_(select(ProjectTeam.project_id).where(ProjectTeam.user_id == scope_user_id)),
        Project.id.in_(
            select(Task.project_id).where(
                Task.assigned_to == scope_user_id, Task.project_id.isnot(None)
            )
        ),
    )


async def user_in_project(db: AsyncSession, project_id: int, user_id: int) -> bool:
    condition = scope_condition(user_id)
    stmt = select(Project.id).where(Project.id == project_id)
    if condition is not None:
        stmt = stmt.where(condition)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def user_project_ids(db: AsyncSession, user_id: int) -> list[int]:
    condition = scope_condition(user_id)
    if condition is None:
        return []
    rows = (
        (
            await db.execute(
                select(Project.id)
                .where(Project.is_active.is_(True), condition)
                .order_by(Project.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def list_projects(
    db: AsyncSession,
    search: str | None,
    project_type: str | None,
    status: str | None,
    client_id: int | None,
    lead_id: int | None,
    page: int,
    page_size: int,
    scope_user_id: int | None = None,
    include_financial: bool = True,
) -> tuple[list[dict], int]:
    base = (
        select(Project, Client.name, User.name)
        .outerjoin(Client, Client.id == Project.client_id)
        .outerjoin(User, User.id == Project.project_lead_id)
        .where(Project.is_active.is_(True))
    )
    count_stmt = select(func.count(Project.id)).where(Project.is_active.is_(True))

    scope_cond = scope_condition(scope_user_id)
    if scope_cond is not None:
        base = base.where(scope_cond)
        count_stmt = count_stmt.where(scope_cond)

    if search:
        like = f"%{search}%"
        cond = or_(Project.name.ilike(like), Project.project_code.ilike(like))
        base = base.where(cond)
        count_stmt = count_stmt.where(cond)
    if project_type:
        base = base.where(Project.project_type == ProjectType(project_type))
        count_stmt = count_stmt.where(Project.project_type == ProjectType(project_type))
    if status:
        base = base.where(Project.status == status)
        count_stmt = count_stmt.where(Project.status == status)
    if client_id is not None:
        base = base.where(Project.client_id == client_id)
        count_stmt = count_stmt.where(Project.client_id == client_id)
    if lead_id is not None:
        base = base.where(Project.project_lead_id == lead_id)
        count_stmt = count_stmt.where(Project.project_lead_id == lead_id)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Project.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    items = [
        _strip_financial(
            {
                "id": project.id,
                "project_code": project.project_code,
                "name": project.name,
                "project_type": project.project_type.value,
                "client_id": project.client_id,
                "client_name": client_name,
                "location": project.location,
                "status": project.status.value,
                "project_lead_id": project.project_lead_id,
                "lead_name": lead_name,
                "priority": project.priority,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "progress_pct": project.progress_pct,
                "hours_logged": project.hours_logged,
                "budget": project.budget,
                "studio_fee": project.studio_fee,
            },
            include_financial,
        )
        for project, client_name, lead_name in rows
    ]
    return items, total


async def get_project(db: AsyncSession, project_id: int, include_financial: bool = True) -> dict:
    row = (
        await db.execute(
            select(Project, Client.name, User.name)
            .options(selectinload(Project.phases))
            .outerjoin(Client, Client.id == Project.client_id)
            .outerjoin(User, User.id == Project.project_lead_id)
            .where(Project.id == project_id, Project.is_active.is_(True))
        )
    ).first()
    if row is None:
        raise ProjectError("Project not found", 404)
    project, client_name, lead_name = row

    team_rows = (
        await db.execute(
            select(ProjectTeam, User)
            .join(User, User.id == ProjectTeam.user_id)
            .where(ProjectTeam.project_id == project_id)
            .order_by(ProjectTeam.id)
        )
    ).all()
    team = [
        {
            "id": pt.id,
            "user_id": pt.user_id,
            "name": user.name,
            "designation": user.designation,
            "role": pt.role,
        }
        for pt, user in team_rows
    ]

    project.progress_pct = _compute_progress(project.phases)
    return _strip_financial(
        {
            "id": project.id,
            "project_code": project.project_code,
            "name": project.name,
            "description": project.description,
            "project_type": project.project_type.value,
            "category": project.category,
            "client_id": project.client_id,
            "client_name": client_name,
            "location": project.location,
            "plot_area": project.plot_area,
            "built_up_area": project.built_up_area,
            "no_of_floors": project.no_of_floors,
            "coordinates": project.coordinates,
            "budget": project.budget,
            "studio_fee": project.studio_fee,
            "fee_type": project.fee_type,
            "fee_percent": project.fee_percent,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "status": project.status.value,
            "project_lead_id": project.project_lead_id,
            "lead_name": lead_name,
            "priority": project.priority,
            "progress_pct": project.progress_pct,
            "hours_logged": project.hours_logged,
            "team": team,
            "phases": [
                {
                    "id": phase.id,
                    "project_id": phase.project_id,
                    "name": phase.name,
                    "order_index": phase.order_index,
                    "start_date": phase.start_date,
                    "end_date": phase.end_date,
                    "status": phase.status.value,
                    "completion_pct": phase.completion_pct,
                    "studio_fee": phase.studio_fee if include_financial else None,
                }
                for phase in project.phases
            ],
            "created_at": project.created_at,
        },
        include_financial,
    )


async def _validate_references(
    db: AsyncSession, client_id: int | None, lead_id: int | None
) -> None:
    if client_id is not None:
        client = await db.get(Client, client_id)
        if client is None or not client.is_active:
            raise ProjectError("Client not found", 404)
    if lead_id is not None:
        lead = await db.get(User, lead_id)
        if lead is None or not lead.is_active:
            raise ProjectError("Project lead not found", 404)


async def _add_team(db: AsyncSession, project: Project, members: list[ProjectTeamIn]) -> None:
    for member in members:
        user = await db.get(User, member.user_id)
        if user is None or not user.is_active:
            raise ProjectError(f"Team member {member.user_id} not found", 404)
        exists = (
            await db.execute(
                select(ProjectTeam).where(
                    ProjectTeam.project_id == project.id, ProjectTeam.user_id == member.user_id
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(ProjectTeam(project_id=project.id, user_id=member.user_id, role=member.role))


async def create_project(db: AsyncSession, payload: ProjectCreate) -> Project:
    await _validate_references(db, payload.client_id, payload.project_lead_id)
    code = await next_project_code(db, now_local().year)

    project = Project(
        project_code=code,
        name=payload.name,
        description=payload.description,
        project_type=payload.project_type,
        category=payload.category,
        client_id=payload.client_id,
        location=payload.location,
        plot_area=payload.plot_area,
        built_up_area=payload.built_up_area,
        no_of_floors=payload.no_of_floors,
        coordinates=payload.coordinates,
        budget=payload.budget,
        studio_fee=payload.studio_fee,
        fee_type=payload.fee_type,
        fee_percent=payload.fee_percent,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        project_lead_id=payload.project_lead_id,
        priority=payload.priority,
    )
    db.add(project)
    await db.flush()

    new_phases: list[ProjectPhase] = []
    for index, name in enumerate(_template_phases(payload.project_type.value)):
        new_phases.append(
            ProjectPhase(
                project_id=project.id,
                name=name,
                order_index=index,
                status=PhaseStatus.NOT_STARTED,
                completion_pct=0,
            )
        )
    _apply_phase_dates(new_phases, payload.start_date, payload.end_date)
    db.add_all(new_phases)
    await db.flush()
    project.progress_pct = _compute_progress(new_phases)

    if payload.team:
        await _add_team(db, project, payload.team)

    await db.commit()
    await db.refresh(project)
    return project


async def update_project(db: AsyncSession, project: Project, payload: ProjectUpdate) -> Project:
    data = payload.model_dump(exclude_unset=True)
    if "client_id" in data:
        await _validate_references(db, data["client_id"], None)
    if "project_lead_id" in data:
        await _validate_references(db, None, data["project_lead_id"])
    if "status" in data and data["status"] is not None:
        from app.utils.state_machines import assert_transition

        assert_transition(project.status, data["status"], "project")
    for field, value in data.items():
        if value is not None:
            setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


async def soft_delete(db: AsyncSession, project: Project) -> None:
    project.is_active = False
    await db.commit()


async def add_team_member(
    db: AsyncSession, project: Project, user_id: int, role: str | None
) -> None:
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise ProjectError("User not found", 404)
    exists = (
        await db.execute(
            select(ProjectTeam).where(
                ProjectTeam.project_id == project.id, ProjectTeam.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise ProjectError("User is already on the project team", 409)
    db.add(ProjectTeam(project_id=project.id, user_id=user_id, role=role))
    await db.commit()


async def remove_team_member(db: AsyncSession, project: Project, user_id: int) -> None:
    member = (
        await db.execute(
            select(ProjectTeam).where(
                ProjectTeam.project_id == project.id, ProjectTeam.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise ProjectError("Team member not found", 404)
    await db.delete(member)
    await db.commit()


async def get_timeline(db: AsyncSession, project: Project) -> dict:
    phases = await _phases_for(db, project.id)
    rows = [
        {
            "id": phase.id,
            "name": phase.name,
            "order_index": phase.order_index,
            "status": phase.status.value,
            "start_date": phase.start_date,
            "end_date": phase.end_date,
            "completion_pct": phase.completion_pct,
        }
        for phase in phases
    ]
    starts = [phase.start_date for phase in phases if phase.start_date]
    ends = [phase.end_date for phase in phases if phase.end_date]
    start = project.start_date or (min(starts) if starts else None)
    end = project.end_date or (max(ends) if ends else None)
    return {
        "project_id": project.id,
        "start_date": start,
        "end_date": end,
        "rows": rows,
    }


async def add_phase(db: AsyncSession, project: Project, payload: PhaseCreate) -> ProjectPhase:
    max_order = (
        await db.execute(
            select(func.max(ProjectPhase.order_index)).where(ProjectPhase.project_id == project.id)
        )
    ).scalar_one()
    order = (max_order or -1) + 1
    phase = ProjectPhase(
        project_id=project.id,
        name=payload.name,
        order_index=order,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        completion_pct=payload.completion_pct,
        studio_fee=payload.studio_fee,
    )
    db.add(phase)
    phases = await _phases_for(db, project.id)
    project.progress_pct = _compute_progress(phases)
    await db.commit()
    await db.refresh(phase)
    return phase


async def update_phase(
    db: AsyncSession, project: Project, phase: ProjectPhase, payload: PhaseUpdate
) -> ProjectPhase:
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        from app.utils.state_machines import assert_transition

        assert_transition(phase.status, data["status"], "phase")
    for field, value in data.items():
        if value is not None:
            setattr(phase, field, value)
    phases = await _phases_for(db, project.id)
    project.progress_pct = _compute_progress(phases)
    await db.commit()
    await db.refresh(phase)
    return phase


async def delete_phase(db: AsyncSession, project: Project, phase: ProjectPhase) -> None:
    await db.delete(phase)
    phases = await _phases_for(db, project.id)
    for index, item in enumerate(phases):
        if item.order_index != index:
            item.order_index = index
    project.progress_pct = _compute_progress(phases)
    await db.commit()


def list_templates() -> list[dict]:
    return [
        {
            "project_type": project_type,
            "label": _label(project_type),
            "phases": _template_phases(project_type),
        }
        for project_type in sorted(PROJECT_TYPE_TEMPLATES, key=lambda t: _label(t))
    ]


async def active_project_options(db: AsyncSession) -> list[dict]:
    """Unscoped id/name list of ACTIVE projects for pickers (timesheets, etc.).

    The main listing scopes staff-band users to their own projects, which
    would empty hour-logging dropdowns; options here are intentionally
    unrestricted (no financial fields).
    """
    rows = await db.execute(
        select(Project.id, Project.name).where(Project.is_active.is_(True)).order_by(Project.name)
    )
    return [{"id": pid, "name": name} for pid, name in rows.all()]
