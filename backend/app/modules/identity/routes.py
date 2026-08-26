"""Identity routes: /auth and /users.

Endpoints: /auth — login (by 6-digit user ID), logout, password change,
token refresh. Endpoints: /users — CRUD, level changes, one-time password
regeneration. Lead roles for listing; executives (L0/L1) for create/update/
delete and credential resets.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_min_level
from app.core.config import settings
from app.core.rate_limit import check_blocked, record_failure, record_success
from app.core.security import (
    format_login_id,
    generate_email,
    generate_numeric_password,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models import Department, OrgLevel
from app.modules.audit.service import log_audit
from app.modules.identity.models import RefreshToken, User
from app.modules.identity.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RegeneratedCredentials,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from app.modules.identity.users_admin import (
    UserAdminCreateOut,
    UserAdminOut,
    UserBriefOut,
    UserCreateIn,
    UserUpdateIn,
)
from app.modules.identity import service as auth_service
from app.modules.identity.repository import user_repository
from app.utils.errors import AuthError
from app.utils.shared import now_local, user_level_rank

auth_router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@auth_router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    key = _client_key(request)
    blocked, retry = check_blocked(
        key, settings.login_max_attempts, settings.login_rate_window_seconds
    )
    if blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(retry)},
        )

    try:
        user = await auth_service.authenticate(db, payload.user_id, payload.password)
    except AuthError as exc:
        allowed, retry = record_failure(
            key, settings.login_max_attempts, settings.login_rate_window_seconds
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(retry)},
            ) from exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc

    record_success(key)
    await log_audit(db, user, "login", "auth", entity_id=str(user.id))
    tokens = await auth_service.issue_tokens(db, user)
    return TokenResponse(**tokens, user=UserOut.model_validate(user))


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenResponse:
    try:
        tokens = await auth_service.rotate_refresh(db, payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc

    user = await auth_service.get_user_from_token(db, payload.refresh_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return TokenResponse(**tokens, user=UserOut.model_validate(user))


@auth_router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> MessageResponse:
    await auth_service.revoke_refresh(db, payload.refresh_token)
    await log_audit(db, None, "logout", "auth")
    # revoke_refresh only commits when the token exists; make sure the
    # audit row lands either way.
    await db.commit()
    return MessageResponse(message="Logged out successfully")


@auth_router.get("/me", response_model=UserOut)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    from sqlalchemy.orm import selectinload

    user = await db.scalar(
        select(User).options(selectinload(User.org_level)).where(User.id == current_user.id)
    )
    return UserOut.model_validate(user or current_user)


@auth_router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )
    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    # Invalidate every outstanding session (access tokens die via the
    # token_version claim, refresh tokens are revoked below); the fresh
    # pair returned here keeps the current session alive seamlessly.
    current_user.token_version += 1
    await _revoke_user_refresh_tokens(db, current_user.id)
    await log_audit(db, current_user, "change_password", "auth", entity_id=str(current_user.id))
    tokens = await auth_service.issue_tokens(db, current_user)
    user = await db.get(User, current_user.id)
    return TokenResponse(**tokens, user=UserOut.model_validate(user))


async def _revoke_user_refresh_tokens(db: AsyncSession, user_id: int) -> None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
    )
    for token in result.scalars():
        token.revoked = True


@users_router.get("", response_model=list[UserBriefOut])
async def list_users(
    current_user: Annotated[User, Depends(require_min_level("L3"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    department_id: int | None = None,
    active_only: bool = True,
) -> list[UserBriefOut]:
    stmt = (
        select(User, Department.name, OrgLevel)
        .outerjoin(Department, Department.id == User.department_id)
        .outerjoin(OrgLevel, OrgLevel.id == User.org_level_id)
    )
    if department_id is not None:
        stmt = stmt.where(User.department_id == department_id)
    if active_only:
        stmt = stmt.where(User.is_active.is_(True))
    stmt = stmt.order_by(User.name)
    result = await db.execute(stmt)

    rows: list[UserBriefOut] = []
    for user, department_name, level in result.all():
        rows.append(
            UserBriefOut(
                id=user.id,
                login_id=user.login_id,
                employee_id=user.employee_id,
                name=user.name,
                email=user.email,
                department_id=user.department_id,
                department=department_name,
                org_level_id=level.id if level else None,
                org_level_code=level.code if level else None,
                org_level_name=level.name if level else None,
                designation=user.designation,
                is_active=user.is_active,
                must_change_password=user.must_change_password,
            )
        )
    return rows


@users_router.post("", response_model=UserAdminCreateOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateIn,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAdminCreateOut:
    email = generate_email(payload.name, payload.date_of_joining)
    password = payload.password or generate_numeric_password()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Generated email {email} already exists. Try a different name or date.",
        )
    if payload.employee_id:
        emp_exists = await db.execute(select(User).where(User.employee_id == payload.employee_id))
        if emp_exists.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Employee ID already in use"
            )
    if payload.department_id is not None:
        department = await db.get(Department, payload.department_id)
        if department is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
            )
    if payload.org_level_id is not None:
        level = await db.get(OrgLevel, payload.org_level_id)
        if level is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organizational level not found"
            )

    year = (
        payload.date_of_joining.year
        if payload.date_of_joining is not None
        else now_local().date().year
    )
    login_id = await _allocate_login_id(db, year)

    user = User(
        name=payload.name,
        login_id=login_id,
        email=email,
        contact_email=payload.contact_email,
        password_hash=hash_password(password),
        must_change_password=True,
        department_id=payload.department_id,
        org_level_id=payload.org_level_id,
        designation=payload.designation,
        employee_id=payload.employee_id,
        phone=payload.phone,
        date_of_joining=payload.date_of_joining,
    )
    db.add(user)
    await db.flush()
    await log_audit(
        db,
        current_user,
        "create",
        "user",
        entity_id=str(user.id),
        details={"email": user.email, "login_id": login_id, "org_level_id": payload.org_level_id},
    )
    await db.commit()
    await db.refresh(user)
    admin_out = await _to_admin_out(db, user)
    return UserAdminCreateOut(**admin_out.model_dump(), generated_password=password)


async def _allocate_login_id(db: AsyncSession, year: int) -> str:
    """Allocate the next free ``YY####`` login id for the given joining year."""
    for _ in range(5):
        sequence = await user_repository.next_login_sequence(db, year)
        candidate = format_login_id(year, sequence)
        exists = await db.execute(select(User).where(User.login_id == candidate))
        if exists.scalar_one_or_none() is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Could not allocate a unique user ID for this joining year",
    )


async def _to_admin_out(db: AsyncSession, user: User) -> UserAdminOut:
    department_name = None
    if user.department_id is not None:
        department = await db.get(Department, user.department_id)
        department_name = department.name if department else None
    level = None
    if user.org_level_id is not None:
        level = await db.get(OrgLevel, user.org_level_id)
    return UserAdminOut(
        id=user.id,
        login_id=user.login_id,
        employee_id=user.employee_id,
        name=user.name,
        email=user.email,
        contact_email=user.contact_email,
        department_id=user.department_id,
        department=department_name,
        org_level_id=user.org_level_id,
        org_level_code=level.code if level else None,
        org_level_name=level.name if level else None,
        designation=user.designation,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        phone=user.phone,
        date_of_joining=user.date_of_joining,
    )


@users_router.patch("/{user_id}", response_model=UserAdminOut)
async def update_user(
    user_id: int,
    payload: UserUpdateIn,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserAdminOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.name is not None:
        user.name = payload.name
    if payload.contact_email is not None:
        user.contact_email = payload.contact_email
    if payload.employee_id is not None and payload.employee_id != user.employee_id:
        emp_exists = await db.execute(select(User).where(User.employee_id == payload.employee_id))
        if emp_exists.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Employee ID already in use"
            )
        user.employee_id = payload.employee_id
    if payload.department_id is not None:
        if payload.department_id == 0:
            user.department_id = None
        else:
            department = await db.get(Department, payload.department_id)
            if department is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
                )
            user.department_id = payload.department_id
    if payload.designation is not None:
        user.designation = payload.designation
    if payload.org_level_id is not None:
        if payload.org_level_id == 0:
            user.org_level_id = None
        else:
            level = await db.get(OrgLevel, payload.org_level_id)
            if level is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Organizational level not found"
                )
            user.org_level_id = payload.org_level_id
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        # Executive-assigned passwords are temporary: force a change at next
        # login and kill any outstanding sessions.
        user.must_change_password = True
        user.token_version += 1
        await _revoke_user_refresh_tokens(db, user.id)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await log_audit(
        db,
        current_user,
        "update",
        "user",
        entity_id=str(user.id),
        details={
            "email": user.email,
            "is_active": user.is_active,
            "password_reset": payload.password is not None,
        },
    )
    await db.commit()
    await db.refresh(user)
    return await _to_admin_out(db, user)


@users_router.post("/{user_id}/regenerate-password", response_model=RegeneratedCredentials)
async def regenerate_password(
    user_id: int,
    current_user: Annotated[User, Depends(require_min_level("L1"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegeneratedCredentials:
    """Issue a new one-time password for a user who forgot theirs.

    The generated password is returned exactly once (to be handed to the
    user out-of-band) and never stored in plaintext. Any outstanding
    sessions are invalidated and the user must change the password at
    next login.
    """
    # Eager-load org_level: the rank guard below reads it, and a lazy load
    # on an async session would raise MissingGreenlet.
    target = await user_repository.get(db, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use change-password to update your own password",
        )
    if user_level_rank(target) <= user_level_rank(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reset passwords of users at or above your level",
        )

    new_password = generate_numeric_password()
    target.password_hash = hash_password(new_password)
    target.must_change_password = True
    target.token_version += 1
    await _revoke_user_refresh_tokens(db, target.id)
    await log_audit(
        db,
        current_user,
        "password_reset",
        "user",
        entity_id=str(target.id),
        details={"login_id": target.login_id},
    )
    # Persist the reset — get_db never commits at request end.
    await db.commit()
    return RegeneratedCredentials(
        login_id=target.login_id,
        name=target.name,
        generated_password=new_password,
    )
