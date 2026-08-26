"""In-memory, fixed-window rate limiter for login brute-force protection.

Single-process design (per-uvicorn-worker): adequate for a small studio ERP and
keeps the dependency footprint at zero. Keys are client IPs; only *failed*
login attempts are counted, and a successful login resets the bucket.
"""

import time
from collections import defaultdict, deque
from threading import Lock

_lock = Lock()
_failures: dict[str, deque[float]] = defaultdict(deque)


def _prune(key: str, now: float, window_seconds: int) -> None:
    bucket = _failures[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if not bucket:
        _failures.pop(key, None)


def record_failure(key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    """Record a failed attempt. Returns (allowed, retry_after_seconds).

    When the bucket is already at the limit the failure is not recorded again,
    so hammering past the cap does not inflate the retry window.
    """
    now = time.monotonic()
    with _lock:
        _prune(key, now, window_seconds)
        bucket = _failures[key]
        if len(bucket) >= max_attempts:
            retry = int(window_seconds - (now - bucket[0])) + 1
            return False, max(1, retry)
        bucket.append(now)
        return True, 0


def record_success(key: str) -> None:
    """Clear the failure bucket for a key after a successful login."""
    with _lock:
        _failures.pop(key, None)


def check_blocked(key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    """Returns (blocked, retry_after_seconds) without recording anything."""
    now = time.monotonic()
    with _lock:
        _prune(key, now, window_seconds)
        bucket = _failures.get(key)
        if bucket is not None and len(bucket) >= max_attempts:
            retry = int(window_seconds - (now - bucket[0])) + 1
            return True, max(1, retry)
        return False, 0


def reset_rate_limits() -> None:
    """Clear all buckets. Used by tests between cases."""
    with _lock:
        _failures.clear()
