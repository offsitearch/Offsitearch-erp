"""Org structure routes: /departments and /org-levels.

Levels describe organizational seniority ONLY and never grant
application permissions — authorization stays in RBAC.

Business rules live in ``orgstructure.service``; these handlers only
perform authentication/authorization and delegate.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_min_level
from app.db.session import get_db
from app.models import User
from app.modules.employees.schemas import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
    OrgLevelOut,
)
from app.modules.orgstructure import service
from app.modules.orgstructure.models import OrgLevel
from app.modules.orgstructure.schemas import OrgLevelCreate, OrgLevelUpdate

departments_router = APIRouter(prefix="/departments", tags=["departments"])
org_levels_router = APIRouter(prefix="/org-levels", tags=["org-levels"])


@departments_router.get("", response_model=list[DepartmentOut])
async def list_departments(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    return await service.list_departments(db)


@departments_router.post("", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service.create_department(db, payload, current_user)


@departments_router.patch("/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service.update_department(db, department_id, payload, current_user)


@departments_router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: int,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await service.delete_department(db, department_id, current_user)


@org_levels_router.get("", response_model=list[OrgLevelOut])
async def list_org_levels(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrgLevel]:
    return await service.list_org_levels(db)


@org_levels_router.post("", response_model=OrgLevelOut, status_code=status.HTTP_201_CREATED)
async def create_org_level(
    payload: OrgLevelCreate,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service.create_org_level(db, payload, current_user)


@org_levels_router.patch("/{level_id}", response_model=OrgLevelOut)
async def update_org_level(
    level_id: int,
    payload: OrgLevelUpdate,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await service.update_org_level(db, level_id, payload, current_user)
