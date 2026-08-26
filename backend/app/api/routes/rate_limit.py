"""Rate limit dashboard endpoint — admin only."""

from fastapi import APIRouter, Depends

from app.api.deps import require_min_level
from app.middleware.rate_limit_tracker import get_rate_limit_stats

router = APIRouter(prefix="/rate-limit", tags=["rate-limit"])


@router.get("/stats")
async def get_stats(
    _current_user=Depends(require_min_level("L2")),
):
    """Return rate limit usage stats. Admin/Super Admin only."""
    return get_rate_limit_stats()
