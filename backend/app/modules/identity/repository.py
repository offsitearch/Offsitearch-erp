from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.identity.models import RefreshToken, User


class UserRepository:
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(
            select(User).options(selectinload(User.org_level)).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_login_id(self, db: AsyncSession, login_id: str) -> User | None:
        result = await db.execute(
            select(User).options(selectinload(User.org_level)).where(User.login_id == login_id)
        )
        return result.scalar_one_or_none()

    async def next_login_sequence(self, db: AsyncSession, year: int) -> int:
        """Next free per-year sequence number for ``YY####`` login ids."""
        prefix = f"{year % 100:02d}"
        max_seq = await db.scalar(
            select(func.max(func.right(User.login_id, 4).cast(Integer))).where(
                User.login_id.like(f"{prefix}%")
            )
        )
        return (max_seq or 0) + 1

    async def get(self, db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(
            select(User).options(selectinload(User.org_level)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


class RefreshTokenRepository:
    async def get_by_jti(self, db: AsyncSession, jti: str) -> RefreshToken | None:
        result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        return result.scalar_one_or_none()


user_repository = UserRepository()
refresh_token_repository = RefreshTokenRepository()
