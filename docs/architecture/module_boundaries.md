> **STATUS (2026-08-24): PROPOSAL DOCUMENT — superseded by implementation.** The 7-wave refactor
> is complete, but the shipped shape differs: no per-module `contracts.py` or shared
> `repository.py` convention was built; actual modules are attendance, audit, backup, clients,
> dashboard, employees, finance, holidays, identity, leave, meetings, notices, notifications,
> orgstructure, payroll, projects, reports, settings, site_visits, tasks (`reporting` split into
> reports + dashboard; **vendors deleted entirely**, not extracted). Enforcement today =
> `backend/.importlinter` contracts + `require_financial_access()` (L0/L1), not RevenueRoles.
> Current rules live in `_ai_context/MODULE_BOUNDARIES.md`.


