"""Employee management routes.

Endpoints: /employees — CRUD, document uploads, org-level assignments.
Management band (L3+); sensitive ops restricted to L2+/L1+.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_financial_access, require_min_level
from app.core.storage import get_storage
from app.db.session import get_db
from app.models import OrgLevel, User
from app.modules.employees.models import EmployeeDocument
from app.modules.audit.service import log_audit
from app.core.schemas import PaginatedResponse
from app.modules.employees.schemas import (
    DocumentOut,
    EmployeeCreate,
    EmployeeCreateOut,
    EmployeePage,
    EmployeeUpdate,
    OrgChartNode,
    ProfileOut,
    SalaryOut,
    SalaryUpdate,
)
from app.modules.leave.schemas import LeaveOut
from app.modules.leave import service as leave_service
from app.modules.employees import service as employee_service
from app.core.email import send_welcome_email
from app.utils.errors import EmployeeError
from app.utils.shared import domain_error, get_or_404, has_min_level, level_rank, user_level_rank
from app.utils.upload import ALLOWED_DOCUMENT_EXTENSIONS, validate_upload

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=EmployeePage)
async def list_employees(
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(default=None, max_length=100),
    department_id: int | None = None,
    org_level_id: int | None = None,
    skill: str | None = Query(default=None, max_length=50),
    active_only: bool = True,
    inactive_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> EmployeePage:
    items, total = await employee_service.list_employees(
        db,
        search,
        department_id,
        skill,
        active_only,
        inactive_only,
        page,
        page_size,
        org_level_id=org_level_id,
    )
    return EmployeePage(items=items, total=total, page=page, page_size=page_size)


@router.get("/skills", response_model=list[str])
async def list_skills(
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    return await employee_service.list_skills(db)


@router.get("/designations", response_model=dict[str, list[str]])
async def designation_catalog(
    current_user: Annotated[User, Depends(require_min_level("L3"))],
) -> dict[str, list[str]]:
    """Suggested designations per organizational level. HR info only."""
    return await employee_service.get_designation_catalog()


@router.get("/department-designations", response_model=dict[str, list[str]])
async def department_designation_catalog(
    current_user: Annotated[User, Depends(require_min_level("L3"))],
) -> dict[str, list[str]]:
    """Suggested designations per department name. HR info only."""
    return await employee_service.get_department_designation_catalog()


@router.get("/org-chart", response_model=list[OrgChartNode])
async def org_chart(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    return await employee_service.org_chart(db)


@router.post("", response_model=EmployeeCreateOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeCreateOut:
    if payload.org_level_id is not None:
        level = await db.get(OrgLevel, payload.org_level_id)
        target_code = level.code if level else None
        # Strictly junior only — never the creator's own level or above.
        if level_rank(target_code) <= user_level_rank(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only assign organizational levels below your own",
            )
    try:
        user, password = await employee_service.create_employee(db, payload)
    except EmployeeError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "create", "employee", entity_id=str(user.id))
    await db.commit()
    await send_welcome_email(user.email, user.name, password)
    profile = await employee_service.get_profile(db, user.id)
    return EmployeeCreateOut(**profile, generated_password=password)


@router.get("/{user_id}", response_model=ProfileOut)
async def get_employee(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not has_min_level(current_user, "L3") and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    try:
        return await employee_service.get_profile(db, user_id)
    except EmployeeError as exc:
        raise domain_error(exc) from exc


@router.patch("/{user_id}", response_model=ProfileOut)
async def update_employee(
    user_id: int,
    payload: EmployeeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileOut:
    is_management = has_min_level(current_user, "L3")
    if not (is_management or current_user.id == user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    # Eager-load org_level: the seniority guard below reads it and a lazy
    # load on an async session would raise MissingGreenlet.
    target = (
        await db.execute(
            select(User).options(selectinload(User.org_level)).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Rank-based administration hardening: nobody admin-edits a senior
    # colleague (self-edit stays allowed via the identity check above).
    # This includes the CEO: even L1 Directors cannot modify L0.
    if target.id != current_user.id and user_level_rank(target) < user_level_rank(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot edit a user senior to your organizational level",
        )
    if "is_active" in payload.model_dump(exclude_unset=True) and not has_min_level(
        current_user, "L1"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Executive Leadership can activate or deactivate an employee",
        )
    if payload.org_level_id is not None:
        level = await db.get(OrgLevel, payload.org_level_id)
        if level is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organizational level not found",
            )
        target_code = level.code
        if target_code == "L1" and not has_min_level(current_user, "L1"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Executive Leadership can assign L1",
            )
        if level_rank(target_code) < user_level_rank(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot assign an organizational level senior to your own",
            )
    try:
        updated = await employee_service.update_employee(
            db, target, payload, current_user, allow_full=is_management
        )
    except EmployeeError as exc:
        raise domain_error(exc) from exc
    await log_audit(db, current_user, "update", "employee", entity_id=str(user_id))
    await db.commit()
    return ProfileOut.model_validate(await employee_service.get_profile(db, updated.id))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    user_id: int,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    target = (
        await db.execute(
            select(User).options(selectinload(User.org_level)).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    if user_level_rank(target) < user_level_rank(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot deactivate a user senior to your organizational level",
        )
    await employee_service.soft_delete(db, target)
    await log_audit(db, current_user, "delete", "employee", entity_id=str(user_id))
    await db.commit()


@router.post("/{user_id}/purge")
async def purge_employee(
    user_id: int,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Permanently delete an employee and all personal data (L0 only).

    L1/L2 can only deactivate (``DELETE /employees/{user_id}``). This
    erases the account plus their timesheets, leaves, payroll entries,
    salary, documents, notifications, memberships and logged client
    communications, detaches surviving records from their id, and frees
    the email/login slots for reuse. Irreversible.
    """
    if current_user.org_level_code != "L0":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the CEO (L0) can permanently delete employees",
        )
    target = (
        await db.execute(
            select(User).options(selectinload(User.org_level)).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    if target.org_level_code == "L0":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CEO accounts cannot be deleted",
        )
    summary = await employee_service.permanent_delete(db, target)
    await log_audit(db, current_user, "purge", "employee", entity_id=str(user_id))
    await db.commit()
    return {"status": "deleted", "user_id": user_id, **summary}


@router.get("/{user_id}/attendance-summary")
async def attendance_summary(
    user_id: int,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
) -> dict:
    ref = leave_service.now_local()
    month = month or ref.month
    year = year or ref.year
    return await employee_service.get_attendance_summary(db, user_id, month, year)


@router.get("/{user_id}/salary", response_model=SalaryOut)
async def get_salary(
    user_id: int,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    salary = await employee_service.get_salary(db, user_id)
    if salary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No salary record yet")
    return salary


@router.put("/{user_id}/salary", response_model=SalaryOut)
async def put_salary(
    user_id: int,
    payload: SalaryUpdate,
    current_user: Annotated[User, Depends(require_financial_access())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await employee_service.upsert_salary(db, user_id, payload)
    await log_audit(db, current_user, "upsert", "salary", entity_id=str(user_id))
    await db.commit()
    return result


@router.get("/{user_id}/documents", response_model=PaginatedResponse[DocumentOut])
async def list_documents(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    if not has_min_level(current_user, "L3") and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    items, total = await employee_service.list_documents(db, user_id, page, page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/{user_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    user_id: int,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile,
    doc_type: str = Query(default="other", max_length=40),
) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    validate_upload(file, content, allowed=ALLOWED_DOCUMENT_EXTENSIONS, label="document")
    # Verify the target exists before writing anything to storage.
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    result = await employee_service.store_document(
        db, user_id, current_user, doc_type, file.filename or "document", content
    )
    await log_audit(db, current_user, "create", "employee_document", entity_id=str(user_id))
    await db.commit()
    return result


@router.get("/{user_id}/documents/{doc_id}/download")
async def download_document(
    user_id: int,
    doc_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not has_min_level(current_user, "L3") and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    doc = (
        (
            await db.execute(
                select(EmployeeDocument).where(
                    EmployeeDocument.id == doc_id, EmployeeDocument.user_id == user_id
                )
            )
        )
        .scalars()
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    storage = get_storage()
    try:
        content = await storage.download(doc.file_path)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File missing from storage"
        )
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'},
    )


@router.delete("/{user_id}/documents/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    user_id: int,
    doc_id: int,
    current_user: Annotated[User, Depends(require_min_level("L2"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    doc = (
        (
            await db.execute(
                select(EmployeeDocument).where(
                    EmployeeDocument.id == doc_id, EmployeeDocument.user_id == user_id
                )
            )
        )
        .scalars()
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await employee_service.delete_document(db, doc)
    await log_audit(db, current_user, "delete", "employee_document", entity_id=str(doc_id))
    await db.commit()
    return {"message": "Document deleted"}


@router.get("/{user_id}/leaves", response_model=PaginatedResponse[LeaveOut])
async def employee_leaves(
    user_id: int,
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    await get_or_404(db, User, user_id)
    items, total = await leave_service.list_mine(db, user_id, page, page_size)
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
