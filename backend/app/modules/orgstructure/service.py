"""Org structure service: departments and org levels.

All business rules (uniqueness, parent validation, delete guards,
audit logging) live here; routes only handle authentication and
delegation.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models import User
from app.modules.audit.service import log_audit
from app.modules.employees.schemas import (
    DepartmentCreate,
    DepartmentUpdate,
)
from app.modules.orgstructure.models import Department, OrgLevel
from app.modules.orgstructure.schemas import OrgLevelCreate, OrgLevelUpdate


# ── Reads ────────────────────────────────────────────────────────────
async def list_departments(db: AsyncSession) -> list[dict]:
    parent_names = {d.id: d.name for d in (await db.execute(select(Department))).scalars().all()}
    rows = (
        await db.execute(
            select(Department, func.count(User.id))
            .outerjoin(User, User.department_id == Department.id)
            .group_by(Department.id)
            .order_by(Department.name)
        )
    ).all()
    result = []
    for dept, count in rows:
        result.append(
            {
                "id": dept.id,
                "name": dept.name,
                "parent_id": dept.parent_id,
                "parent_name": parent_names.get(dept.parent_id) if dept.parent_id else None,
                "head_id": dept.head_id,
                "description": dept.description,
                "is_active": dept.is_active,
                "member_count": count,
            }
        )
    return result


async def list_org_levels(db: AsyncSession) -> list[OrgLevel]:
    rows = await db.execute(
        select(OrgLevel).where(OrgLevel.is_active.is_(True)).order_by(OrgLevel.rank)
    )
    return list(rows.scalars().all())


# ── Departments ──────────────────────────────────────────────────────
async def create_department(db: AsyncSession, payload: DepartmentCreate, actor: User) -> Department:
    exists = await db.execute(Department.__table__.select().where(Department.name == payload.name))
    if exists.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Department already exists"
        )
    if payload.parent_id is not None:
        parent = await db.get(Department, payload.parent_id)
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent department not found"
            )
    dept = Department(**payload.model_dump())
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    if dept.parent_id is not None:
        await db.refresh(dept, ["parent"])
    await log_audit(db, actor, "create", "department", entity_id=str(dept.id))
    await db.commit()
    return dept


async def update_department(
    db: AsyncSession, department_id: int, payload: DepartmentUpdate, actor: User
) -> Department:
    dept = await db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("parent_id") is not None:
        if data["parent_id"] == department_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department cannot be its own parent",
            )
        parent = await db.get(Department, data["parent_id"])
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent department not found"
            )
    for field, value in data.items():
        if value is not None:
            setattr(dept, field, value)
    await db.commit()
    await db.refresh(dept)
    if dept.parent_id is not None:
        await db.refresh(dept, ["parent"])
    await log_audit(db, actor, "update", "department", entity_id=str(department_id))
    await db.commit()
    return dept


async def delete_department(db: AsyncSession, department_id: int, actor: User) -> None:
    dept = await db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    member_count = (
        await db.execute(select(func.count(User.id)).where(User.department_id == department_id))
    ).scalar()
    if member_count and member_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete department — {member_count} employee{'s' if member_count != 1 else ''} still assigned. Reassign them first.",
        )
    child_count = (
        await db.execute(
            select(func.count(Department.id)).where(Department.parent_id == department_id)
        )
    ).scalar()
    if child_count and child_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete department — {child_count} sub-department{'s' if child_count != 1 else ''} still linked. Reassign them first.",
        )
    await log_audit(db, actor, "delete", "department", entity_id=str(department_id))
    await db.delete(dept)
    await db.commit()


# ── Org levels ───────────────────────────────────────────────────────
async def create_org_level(db: AsyncSession, payload: OrgLevelCreate, actor: User) -> OrgLevel:
    code = payload.code.strip().upper()
    exists = (await db.execute(select(OrgLevel).where(OrgLevel.code == code))).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Level code already exists"
        )
    level = OrgLevel(
        code=code,
        name=payload.name,
        description=payload.description,
        rank=payload.rank,
    )
    db.add(level)
    await db.commit()
    await db.refresh(level)
    await log_audit(db, actor, "create", "org_level", entity_id=str(level.id))
    await db.commit()
    return level


async def update_org_level(
    db: AsyncSession, level_id: int, payload: OrgLevelUpdate, actor: User
) -> OrgLevel:
    level = await db.get(OrgLevel, level_id)
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(level, field, value)
    await db.commit()
    await db.refresh(level)
    await log_audit(db, actor, "update", "org_level", entity_id=str(level_id))
    await db.commit()
    return level
