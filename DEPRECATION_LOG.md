# Deprecation & Deferred-Removal Log

Items flagged during the pre-testing overhaul pass (2026-08-24). Nothing here
was deleted; each entry records why the code/asset still exists and what must
happen before it can be removed.

| # | Item | Status | Reason kept | Removal conditions |
|---|------|--------|-------------|--------------------|
| 1 | `vendors` / `vendor_projects` DB tables (created by migration `backend/alembic/versions/0006_finance_vendors_payroll.py`) | Deprecated — no source module exists | The migration shipped to deployed databases; dropping tables is forbidden in this pass (backward-compat rule: schema changes are add-only). No Python module references these tables at runtime. | After a future release confirms no data of value: write a new **additive-forward** migration pair (`down` recreates empty tables, `up` drops them), run in staging, then delete. Never edit or delete migration 0006 itself. |
| 2 | `.importlinter` reference to `app.modules.vendors.models` | **Removed** (2026-08-24) | Referenced a package that does not exist; made `lint-imports` fail with "Module does not exist", masking real contract results in local runs. CI backend-lint job does not run import-linter yet, so the break went unnoticed. | n/a — removed; see REFACTOR_CHANGELOG.md. Consider adding lint-imports to CI (flagged below). |
| 3 | Stale bytecode `backend/tests/__pycache__/test_vendors.*.pyc` | **Deleted** (2026-08-24) | Orphaned compiled cache from a deleted test module; untracked artifact. | n/a |
| 4 | Rate-limiting triplication: slowapi limiter (`app/main.py`), custom login limiter (`app/core/rate_limit.py`), usage tracker middleware (`app/middleware/rate_limit_tracker.py`) | Kept — consolidation deferred | Each mechanism has distinct semantics (request throttling vs. brute-force lockout vs. admin metrics). Merging them before the testing phase risks changing auth-throttling behavior, which is exactly the kind of regression this pass must not introduce. | Consolidate behind one rate-limit facade after testing phase, behind a feature flag, with load tests. |
| 5 | Idempotency-key infrastructure for write endpoints | Not implemented — flagged | No payment gateway exists today; ERP writes are guarded by org-level authz + DB constraints + audit trail. Adding an idempotency-key table + middleware across all POST/PATCH endpoints is a large surface change inappropriate for a pre-testing gate. | Implement for any future payment/integration endpoints first; extend to critical state-change endpoints after contract tests exist. |
| 6 | Circuit-breaker wrapper for external calls (SMTP, Supabase Storage, Google Drive) | Not implemented — flagged | All external call sites already fail gracefully (email returns False and callers continue; storage/drive errors are caught) and now carry explicit timeouts. A breaker adds shared mutable state per worker process; correctness under gunicorn multi-worker needs design + tests that don't belong in this pass. | Add after testing phase as a small reusable async breaker with per-worker metrics exposed via `/api/v1/system/health`. |

## Review flags for humans

- **HIGH-risk review requested:** none of the changes in this pass alter API
  contracts, auth behavior, or financial logic. See `REFACTOR_CHANGELOG.md`
  for per-change risk ratings.
- `lint-imports` is not wired into CI (`.github/workflows/ci.yml` runs ruff
  only). Recommend adding it to the backend-lint job so contract breaks like
  #2 cannot recur silently.
