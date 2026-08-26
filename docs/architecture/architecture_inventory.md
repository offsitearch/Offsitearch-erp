> **STATUS (2026-08-24): HISTORICAL SNAPSHOT — pre-modularization.** This audit describes the
> OLD layered tree (`app/api`, `app/services`, `app/repositories`). The codebase is now a modular
> monolith (`backend/app/modules/<name>/`): 20 modules incl. `dashboard`, `orgstructure`,
> `audit`, `backup`; the vendors module has been DELETED. The revenue guard was renamed to
> `require_financial_access()` (L0/L1 executive-only). Read as history/rationale only — for the
> current architecture see `_ai_context/ARCHITECTURE.md` and `docs/ARCHITECTURE.md`.


