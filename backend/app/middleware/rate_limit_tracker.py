"""In-memory rate limit usage tracker for admin dashboard.

Tracks per-route usage counts and response times.
Uses a circular buffer per route (last 1000 entries).
Resets on server restart.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


@dataclass
class RouteStats:
    total_requests: int = 0
    rate_limited: int = 0
    last_100_timestamps: deque = field(default_factory=lambda: deque(maxlen=100))
    avg_response_ms: float = 0.0
    _response_times: deque = field(default_factory=lambda: deque(maxlen=100))

    def record_request(self, was_rate_limited: bool, response_time_ms: float):
        self.total_requests += 1
        if was_rate_limited:
            self.rate_limited += 1
        now = time.time()
        self.last_100_timestamps.append(now)
        self._response_times.append(response_time_ms)
        if self._response_times:
            self.avg_response_ms = sum(self._response_times) / len(self._response_times)

    def to_dict(self) -> dict:
        now = time.time()
        recent = [t for t in self.last_100_timestamps if now - t < 60]
        return {
            "total_requests": self.total_requests,
            "rate_limited": self.rate_limited,
            "requests_last_60s": len(recent),
            "avg_response_ms": round(self.avg_response_ms, 1),
        }


# Global store — module-level singleton
_route_stats: dict[str, RouteStats] = defaultdict(RouteStats)
_start_time: float = time.time()


def get_rate_limit_stats() -> dict:
    """Return all stats for the admin dashboard."""
    return {
        "uptime_seconds": int(time.time() - _start_time),
        "routes": {route: stats.to_dict() for route, stats in sorted(_route_stats.items())},
        "total_requests": sum(s.total_requests for s in _route_stats.values()),
        "total_rate_limited": sum(s.rate_limited for s in _route_stats.values()),
    }


class RateLimitTrackerMiddleware(BaseHTTPMiddleware):
    """Non-blocking middleware that records request stats."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.time()
        response = await call_next(request)
        elapsed_ms = (time.time() - start) * 1000

        # Only track API routes
        path = request.url.path
        if path.startswith("/api/"):
            route = f"{request.method} {path}"
            was_limited = response.status_code == 429
            _route_stats[route].record_request(was_limited, elapsed_ms)

        return response
