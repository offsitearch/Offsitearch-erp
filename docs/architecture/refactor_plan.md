> **STATUS (2026-08-24): COMPLETED & ARCHIVED.** This extraction plan was executed across 7 waves;
> the modular monolith it proposed is now the shipped architecture (`backend/app/modules/`).
> Deltas from the plan: vendors was **deleted** rather than extracted; `reporting` split into
> `reports` + `dashboard`; no `test_architecture.py` was created — enforcement lives in
> `backend/.importlinter` contracts instead; the "no RBAC/auth changes" rule was later superseded
> by the org-level authorization rewrite (migrations 0020–0024). Current rules:
> `_ai_context/MODULE_BOUNDARIES.md`.

# OFFSITE ERP — Refactoring Plan (Modular Monolith)

> Phase 1 deliverable 4/4. Sequenced, behavior-preserving extraction plan.
> Rules in force: no rewrites, no microservices, no RBAC/auth changes, no API
> contract changes, tests green after every step, one module per PR-sized change.

---

## 0. Preconditions

1. **Commit the current working tree first.** There are uncommitted changes
   (org-structure refactor, revenue tests, migration 0019). The refactor must
   start from a clean, green baseline.
2. Run the full backend suite once to record the baseline:
   `pytest backend/tests` (requires `DATABASE_URL`; conftest creates a scratch DB).
3. Tag the baseline commit for easy diffing.

## 1. Migration strategy — strangler pattern with shims

Each extraction step is mechanical and reversible:

1. Create `modules/<name>/` with `models/schemas/service/routes(/repository)/tests`.
2. **Move** code; do not edit logic.
3. Leave a compatibility shim at the old path (`app/services/x_service.py`
   re-exports from the new location) so any straggler import keeps working during
   the transition; delete shims at the end of each phase.
4. Update `app/api/__init__.py` to mount the module router (same prefix/tags).
5. Keep `app/models/__init__.py` importing from new locations → Alembic unaffected.
6. Run: module tests → full backend suite → frontend smoke (`playwright`) when
   routes touched (they won't be).
7. Freeze: document the module's contracts in its `__init__` docstring +
   update `docs/architecture/`.

Rollback = revert the single extraction commit.

## 2. Extraction order (safest → riskiest)

Rationale: start with zero-coupling leaves to establish the pattern cheaply;
introduce shared contracts before touching high fan-in modules; identity and
finance last because they are the highest blast radius.

| Step | Module | Why here | Contracts introduced/needed |
|---|---|---|---|
| 1 | **notices** | Zero cross-domain deps beyond User; tiny service+route+tests (`test_communication.py`). Perfect pilot. | none (uses core only) |
| 2 | **meetings**, **notifications**, **vendors** | Same profile: isolated, dedicated tests. Vendors' Project validation becomes first real contract use. | `ProjectLookup`, formalize `NotifyPort` |
| 3 | **settings** + extract runtime defaults | Small, but unlocks killing the seeds cycle: move `ATTENDANCE_SETTINGS`→`modules/attendance/defaults.py`, `LEAVE_SETTINGS`→leave, `PROJECT_TYPE_TEMPLATES`→projects; seeds import from modules afterwards (fixes circular dep C1). | `SettingsPort` defined here, consumed later |
| 4 | **holidays** | Tiny; needed as contract before leave/payroll extraction. | `HolidayCalendar` |
| 5 | **clients** | Moderate deps (reads projects/invoices for profile → switch to lookups). | `ClientLookup` published |
| 6 | **projects** | Hub of the delivery cluster; publish `ProjectAccess`/`ProjectLookup`. Tasks/site_visits/finance still on shims. | publishes `ProjectAccess` |
| 7 | **tasks**, **site_visits** | Depend on projects via now-existing contracts. | consume `ProjectAccess` |
| 8 | **attendance** | Well-tested (`test_attendance.py` 16 KB), clear ownership. Needs `SettingsPort`, `EmployeeDirectory`, `HolidayCalendar`. Publishes `AttendanceQuery`/`AttendanceWriter`. | publishes attendance contracts |
| 9 | **leave** | Highest-risk business coupling (writes Attendance). Becomes first consumer of `AttendanceWriter` — the write becomes explicit. Also consumes HolidayCalendar/SettingsPort. | consumes attendance contracts |
| 10 | **employees** | Big service; drops its direct Attendance read in favor of `AttendanceQuery.month_summary`; `/employees/{id}/leaves` switches to leave's public façade. Publishes `EmployeeDirectory`. | publishes EmployeeDirectory |
| 11 | **payroll** | Reads Attendance/Holiday/SalaryComponent → all via contracts by now. | consumes |
| 12 | **finance** | Revenue-critical; guards stay byte-identical (`require_revenue_access`). Reports still on shim until next step. | publishes finance read-model |
| 13 | **reporting** (reports + dashboard) | Last because it reads everyone. Rebuild over per-module summary/read contracts; delete private imports (`_period_bounds`, `_status_for`, `_attendance_sheets`) by promoting them into contracts or duplicating trivial logic locally with tests. Dashboard route stops doing raw queries. | `SummaryProvider`s |
| 14 | **identity** + **platform** | Everything depends on them, so they move last with shims kept longest. RBAC deps stay in `core/api/deps.py` untouched. `can_manage_project` moves to projects/permissions. | — |
| 15 | Cleanup | Delete all shims, split `shared/enums.py`+`errors.py`+`state_machines.py` per module behind re-export shims, add enforcement (§4), final full test run. | — |

> Steps are independently shippable. If capacity runs out after any step, the
> system is still one app, fully working, just partially modularized.

## 3. First module — decision

**Pilot: `notices`** (step 1).

- Clear ownership: one model, one table, one service, one route, no cross-domain writes.
- Lowest possible blast radius: consumers are NoticeBoardPage/Dashboard via HTTP only.
- Existing coverage in `test_communication.py`.
- Establishes every convention the bigger extractions reuse: folder shape,
  router mounting, model registry update, shim removal, contract doc format.

Runner-up: `vendors` (equally isolated but demonstrates a contract immediately);
it follows right after in step 2 anyway.

## 4. High-risk areas (handle with explicit care)

| Risk | Where | Mitigation |
|---|---|---|
| Revenue regression | `/finance/overview`, `/reports/finance`, dashboard `revenue_this_month` | Guards untouched in `core/api/deps.py`; `test_revenue_security.py` must pass unmodified after finance & reporting steps; dashboard field logic ported verbatim into reporting service |
| Leave→Attendance write semantics | leave approval creating ON_LEAVE rows incl. method=`manual` fields | `AttendanceWriter.mark_on_leave` replicates exact column values; `test_leave.py` asserts these today — keep assertions green |
| Attendance settings merge order | DB rows override seed defaults | `SettingsPort.get_group("attendance")` preserves merge precedence; unit-test the merge |
| Working-day calculations duplicated in payroll/reports/leave | three near-copies of holiday-aware day counting | Do NOT deduplicate during migration (behavior rule); note for post-refactor consolidation behind attendance contract |
| Alembic model registration | env.py imports `app.models` | keep registry import working at every step; never leave a model unimported |
| Circular seeds↔services | C1 | fixed in step 3 by moving defaults into modules; verify `python -c "import app.seeds.data"` clean |
| Route-layer raw queries (users/dashboard/holidays/departments/org_levels/audit_logs) | no service today | introduce minimal services during their module's extraction; copy queries verbatim first, tidy later |
| `test_walkthrough.py` journey suite | spans everything | treat as canary: run after every step; never edit it during pure moves |
| Uncommitted WIP in tree | org-structure + revenue work | commit baseline before step 1 |

## 5. Architecture enforcement (after boundaries exist)

Add lightweight, dependency-only checks (no runtime impact):

1. **Import-boundary test** (`backend/tests/test_architecture.py`):
   - forbid `app.modules.X` importing `app.modules.Y.service/models/routes` for Y≠X
     (allowlist: via `contracts`);
   - forbid `core/*` and `shared/*` importing `modules/*`;
   - forbid route modules importing foreign models directly;
   - walk the AST/importlib of the package — no third-party tooling required.
2. **CI gate**: run the architecture test + full suite on every PR (existing GitHub workflow).
3. **Optional ruff rule**: `flake8-tidy-imports` banned-api for `app.services.` /
   `app.models.` paths once shims are gone.
4. **Contract docs**: each module's `__init__.py` docstring lists its public
   surface; PR template asks "does this cross a module boundary?"

## 6. Definition of done (per module)

- [ ] Code moved; old paths are shims or deleted; no logic edits (diff proves it)
- [ ] Router mounted with identical prefix/tags/response models
- [ ] Model registered in registry; `alembic check` (or upgrade head on scratch DB) clean
- [ ] Module tests live in `modules/<name>/tests/` (moved, not rewritten)
- [ ] Full backend suite green; walkthrough canary green
- [ ] Cross-module access exclusively via contracts; architecture test passes
- [ ] Public surface documented in module `__init__` + `docs/architecture/` updated

## 7. Explicitly out of scope (separate efforts)

- Splitting the `users` table (identity vs HR profile)
- ~~Removing `password_plain`~~ — ✅ done separately (migration 0024, auth rewrite, 2026-08-23)
- Deduplicating working-day/business-day logic across payroll/reports/leave
- Frontend restructuring (already feature-oriented; only map dependencies now)
- Any API path/payload change (note: the auth rewrite later changed `/auth/login` payloads by owner decision)
