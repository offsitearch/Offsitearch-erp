# ADR-0005: orgstructure service extraction; import-linter contract repair

- Date: 2026-08-24
- Status: Accepted
- Risk: LOW

## Context

Two architecture debts surfaced during the pre-testing pass:

1. `orgstructure` had no service layer — uniqueness checks, parent
   validation, delete guards and audit logging lived directly in route
   handlers, and its two read endpoints borrowed `employees.service`.
2. `.importlinter` referenced the non-existent `app.modules.vendors.models`
   (leftover of a removed module), making `lint-imports` fail with a
   config error that **masked** two genuinely broken contracts:
   every models package importing `app.utils.shared` appeared to violate
   model-independence because `shared.py` imports `User` under
   `TYPE_CHECKING`, which pulls the central `app.models` registry at
   *type-check time only*.

## Decision

1. Created `app/modules/orgstructure/service.py`; moved department/level
   write logic there **verbatim** (same validation order, same exception
   messages, same commit/refresh pattern), relocated the two read
   functions from `employees.service` to their true domain, and reduced
   routes to auth + delegation.
2. Removed the phantom vendors entry; set root-level
   `exclude_type_checking_imports = true` in `.importlinter` so contracts
   evaluate *runtime* coupling (their purpose: prevent circular imports).
   All three contracts now pass.

## Alternatives considered

- *Deleting the TYPE_CHECKING block in shared.py*: would silence the
  linter but degrade type documentation for zero architectural gain.
- *Leaving orgstructure as-is*: contradicts the service-layer rule every
  other module follows and keeps business logic untestable without HTTP.

## Consequences / revert

Pure code motion — response shapes, status codes, error messages and
transaction boundaries are unchanged (verified by ruff, import contracts,
app boot, and the unchanged test-failure set). Revert = `git revert` of
the refactor commit.
