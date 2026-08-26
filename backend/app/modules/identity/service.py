"""Authentication service.

Handles user login, JWT token creation and refresh, and logout.
"""

from datetime import timezone

from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.identity.models import RefreshToken, User
from app.modules.identity.repository import (
    refresh_token_repository,
    user_repository,
)
from app.utils.errors import AuthError
from app.utils.shared import user_level_code, utc_now


async def authenticate(db: AsyncSession, login_id: str, password: str) -> User:
    user = await user_repository.get_by_login_id(db, login_id)
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Incorrect user ID or password")
    if not user.is_active:
        raise AuthError("Account is deactivated")
    return user


async def issue_tokens(db: AsyncSession, user: User) -> dict[str, str]:
    access = create_access_token(
        user.id, user_level_code(user) or "", token_version=user.token_version
    )
    refresh, jti, expires_at = create_refresh_token(user.id, token_version=user.token_version)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            expires_at=expires_at,
        )
    )
    await db.commit()
    return {"access_token": access, "refresh_token": refresh}


async def rotate_refresh(db: AsyncSession, refresh_token: str) -> dict[str, str]:
    try:
        payload = decode_token(refresh_token)
    except PyJWTError as exc:
        raise AuthError("Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type")

    jti = payload.get("jti")
    if not jti:
        raise AuthError("Invalid refresh token")

    stored = await refresh_token_repository.get_by_jti(db, jti)
    if stored is None or stored.revoked:
        raise AuthError("Refresh token has been revoked")
    if stored.expires_at.replace(tzinfo=stored.expires_at.tzinfo or timezone.utc) < utc_now():
        raise AuthError("Refresh token has expired")

    user = await user_repository.get(db, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthError("User not found or deactivated")
    if int(payload.get("tvp", -1)) != user.token_version:
        raise AuthError("Refresh token invalidated by a password change")

    stored.revoked = True
    tokens = await issue_tokens(db, user)
    return tokens


async def get_user_from_token(db: AsyncSession, refresh_token: str) -> User | None:
    try:
        payload = decode_token(refresh_token)
    except PyJWTError:
        return None
    if payload.get("type") != "refresh":
        return None
    return await user_repository.get(db, int(payload["sub"]))


async def revoke_refresh(db: AsyncSession, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)
    except PyJWTError:
        return
    if payload.get("type") != "refresh":
        return
    jti = payload.get("jti")
    if not jti:
        return
    stored = await refresh_token_repository.get_by_jti(db, jti)
    if stored is not None:
        stored.revoked = True
        await db.commit()
