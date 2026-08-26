# ADR-0003: Non-blocking storage backends with hard timeouts

- Date: 2026-08-24
- Status: Accepted
- Risk: MEDIUM

## Context

`SupabaseStorage` called the synchronous `supabase-py` client inside
`async def` methods. Every upload/download/delete therefore **blocked the
event loop** for the duration of a cross-continent network call — stalling
all concurrent requests in that worker. None of the operations had a
timeout, so a hung provider connection could wedge a worker indefinitely.
`LocalStorage` had the same shape with blocking disk I/O (mild, but real
on network volumes).

## Decision

Both backends now execute their blocking work via
`asyncio.to_thread(...)` bounded by `asyncio.wait_for(...)` with a new
`STORAGE_TIMEOUT_SECONDS` setting (default 30). Timeouts surface as
`delete -> False` / raised `TimeoutError` on download/upload; callers'
existing error handling (graceful degradation) is preserved.

## Alternatives considered

- *Async HTTP client for Supabase (storage3 async API)*: would change the
  dependency surface and auth handling mid-gate; revisit during the
  planned starlette/fastapi major upgrade window.
- *Circuit breaker around storage*: deferred — see DEPRECATION_LOG.md #6;
  timeouts + graceful failure deliver most of the protection without
  per-worker shared state.

## Consequences / revert

On timeout the worker thread is abandoned in the background (its result is
discarded); this is acceptable for idempotent-ish operations and prevents
unbounded thread pile-up only under extreme provider latency. Revert =
restore previous file from git history (`git revert` of the storage
commit); no data-format or API changes are involved.

Legacy semantics intentionally preserved: `SupabaseStorage.exists()`
returns True on any *successful* listing (even an empty folder listing) —
changing that detection logic is a behavior fix belonging to the testing
phase, noted in REFACTOR_CHANGELOG.md.
