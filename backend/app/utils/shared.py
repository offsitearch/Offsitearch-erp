"""Shared utilities used across services and routes.

Centralises org-level authorization bands, ORM helpers, error mapping
and timezone constants so that individual route / service modules never
need to re-declare them.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, TYPE_CHECKING
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models import User

# ── Timezone ────────────────────────────────────────────────────────
APP_TZ = ZoneInfo("Asia/Kolkata")
_PENNY = Decimal("0.01")


def utc_now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    """Current datetime in the studio's business timezone (Asia/Kolkata)."""
    return datetime.now(APP_TZ)


def to_local(dt: datetime) -> datetime:
    """Convert a UTC (or naive) datetime to Asia/Kolkata."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(APP_TZ)


# ── Decimal helpers ─────────────────────────────────────────────────
def q(value: Any) -> Decimal:
    """Quantize a value to 2 decimal places (currency penny)."""
    return Decimal(value or 0).quantize(_PENNY)


# ── Org-level authorization ─────────────────────────────────────────
# Authorization is driven by the user's organizational level (L0–L6).
# Ranks are canonical and hardcoded here so that runtime edits to
# ``org_levels.rank`` (a display-ordering field) can never silently
# change permissions. L0 is the most senior.
LEVEL_RANK: dict[str, int] = {
    "L0": 0,  # CEO
    "L1": 1,  # Executive (Director)
    "L2": 2,  # Leadership (Department Head)
    "L3": 3,  # Management (Project / Team Lead)
    "L4": 4,  # Senior Professional
    "L5": 5,  # Professional
    "L6": 6,  # Junior / Entry (incl. interns)
}

UNKNOWN_LEVEL_RANK = 99  # users without a level are least-privileged

ExecutiveLevels = ("L0", "L1")
LeadershipLevels = ("L0", "L1", "L2")
ManagementLevels = ("L0", "L1", "L2", "L3")

# Financial data (invoices, expenses, payroll, salary, budgets, fees,
# deal values, revenue figures) is restricted to L0 CEO and L1 Director
# by explicit client mandate. This constant is the single source of
# truth for that boundary: the API dependency layer derives its guard
# from it (api.deps.require_financial_access) and in-process checks use
# has_financial_access below. Designation/department never grant access.
FINANCIAL_LEVEL = "L1"

STAFF_MIN_RANK = LEVEL_RANK["L4"]  # rank >= this ⇒ self-service band


def level_rank(code: str | None) -> int:
    """Canonical authorization rank for a level code (lower = seniorer)."""
    if not code:
        return UNKNOWN_LEVEL_RANK
    return LEVEL_RANK.get(code, UNKNOWN_LEVEL_RANK)


def user_level_code(user: "User") -> str | None:
    return user.org_level.code if user.org_level else None


def user_level_rank(user: "User") -> int:
    return level_rank(user_level_code(user))


def has_min_level(user: "User", min_level: str) -> bool:
    """True when the user's level is ``min_level`` or more senior."""
    return user_level_rank(user) <= LEVEL_RANK[min_level]


def has_financial_access(user: "User") -> bool:
    """True only for the financial-data boundary (L0 CEO / L1 Director).

    In-process counterpart of ``api.deps.require_financial_access`` —
    use it when serializing responses so financial fields can be
    omitted rather than nulled for unauthorized callers.
    """
    return has_min_level(user, FINANCIAL_LEVEL)


def is_staff_band(user: "User") -> bool:
    """True for the self-service band (L4–L6 or unknown): scoped to own data."""
    return user_level_rank(user) >= STAFF_MIN_RANK


# ── Route helpers ───────────────────────────────────────────────────
async def get_or_404(db: AsyncSession, model: type, record_id: int) -> Any:
    """Fetch a record by PK or raise 404.

    Caller must also check ``is_active`` if soft-delete semantics apply.
    """
    record = await db.get(model, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found"
        )
    return record


async def soft_delete(db: AsyncSession, record: Any) -> None:
    """Set ``is_active=False`` and commit."""
    record.is_active = False
    await db.commit()


def domain_error(exc: Exception) -> HTTPException:
    """Convert a DomainError subclass into an ``HTTPException``.

    Every domain error carries ``status_code`` and ``message`` attributes;
    this helper bridges them into FastAPI's error model so route handlers
    can simply ``raise _error(exc)`` instead of duplicating the mapping.
    """
    status_code = getattr(exc, "status_code", 400)
    message = getattr(exc, "message", str(exc))
    return HTTPException(status_code=status_code, detail=message)
