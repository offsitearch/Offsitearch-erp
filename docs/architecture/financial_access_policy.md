# Financial Access Policy

> Status: **ADOPTED (client mandate)** — supersedes any earlier "revenue = L1-only" or
> "operational finance open to admins" conventions where they conflict.
> Companion document: [financial_data_inventory.md](financial_data_inventory.md) (Phase 1 audit).
>
> Note (2026-08-24): the vendors module was removed entirely, so vendor bank-details clauses
> elsewhere in the historical docs are moot.

## Rule

**All information related to money is accessible only to L0 (CEO) and L1 (Director).**

| Level | Financial access |
|---|---|
| L0 CEO | ALLOW |
| L1 Director | ALLOW |
| L2 Department Head | DENY |
| L3 Project/Team Lead | DENY |
| L4 Senior Professional | DENY |
| L5 Professional | DENY |
| L6 Junior/Intern | DENY |
| No org level assigned | DENY |

Access is rank-based and cumulative: `require_financial_access()` admits every user whose
level ranks at or above **`FinancialLevel` (currently `"L1"`)** — i.e., L0 and L1 today.
Granting a future level financial access is a one-line constant change, never a code sweep.

## Applies to

- Finance: invoices, invoice items, payments, expenses, receipts, revenue
- Payroll: runs, entries, salary, payslips, proration, salary components
- Employee compensation: CTC breakdowns (+ bank details stored with them)
- Project financials: budget, studio_fee, fee_type, fee_percent, phase fees
- Client financials: deal/budget values, contract values, invoiced/received/outstanding summaries
- Financial reports and their exports (finance report, projects report money columns)
- Financial dashboard metrics (revenue KPIs, snapshots)
- Indirect aggregations that reveal or rank financial figures
- Audit trails remain as-is; they carry no amounts (Q4)

## Does NOT automatically apply to

Normal operational information without monetary content:
project names/timelines/teams/tasks/phases (non-financial fields), client CRM records,
employee directory/profile/skills/documents metadata,
attendance, leave, meetings, notices, site visits, org structure.

Self-scoped expense submission (`/finance/my-expenses`) remains available to all levels
per Q1 so employees can file reimbursements; it returns only the submitter's own rows.

## Enforcement architecture

The existing general authorization system is untouched and remains responsible for all
non-financial access. Financial access becomes a specialized boundary on top of it:

```
General authorization   →  require_min_level() / has_min_level()   (unchanged)
Financial authorization →  require_financial_access()             (new, single source)
Special permissions     →  existing RBAC helpers                  (unchanged)
```

### Backend layers (all three required)

1. **Route gate** — `require_financial_access()` dependency on every endpoint whose
   purpose is financial data (finance, payroll, salary, financial reports/exports).
2. **Data redaction** — response schemas/services omit financial fields for callers
   below `FinancialLevel` (omission over null-masking) on operational endpoints that
   embed money (projects, clients). Implemented via dedicated response schemas or a
   single central redaction helper in the service layer — no scattered `if level <= …`.
3. **Write parity** — creating/editing financial values requires financial access
   (write implies read).

### Frontend layer (UX only, never security)

Existing `canAccess(level, 'L1')` gates hide finance/payroll/revenue navigation, widgets,
money columns and export buttons for L2–L6. No new frontend authorization mechanism.

### Definition (single authoritative implementation)

```python
# app/api/deps.py  (extends existing primitives; nothing replaced)
FinancialLevel = "L1"

def require_financial_access():
    return require_min_level(FinancialLevel)

# app/utils/shared.py
def has_financial_access(user) -> bool:
    return has_min_level(user, FinancialLevel)
```

`RevenueLevel` folds into this policy (`require_revenue_access` becomes an alias of the
same boundary rather than a separate rule). Unknown/unset levels keep failing closed via
the existing rank-99 behavior.

## Level capability summary after enforcement

| Capability | Who |
|---|---|
| View/edit invoices, payments, expenses, payroll, salaries, revenue reports/exports | L0, L1 |
| See project budget/fee fields (read or write) | L0, L1 |
| See client financial summaries / budget_range / deal values | L0, L1 |
| Dashboard revenue metrics | L0, L1 |
| Everything else per the existing authorization matrix | unchanged |

## Future-proofing

`FinancialLevel` + `require_financial_access()` establish the pattern for additional
sensitive-category policies (personnel-sensitive, executive-sensitive, system-admin):
each is one constant + one factory dependency reusing `require_min_level`. No new
categories are implemented now.

## Test policy

- A reusable matrix test asserts L0 ALLOW, L1 ALLOW, L2–L6 DENY, unleveled DENY across
  representative endpoints of finance, payroll, employees(salary), projects, clients,
  reports, dashboard, exports.
- Data-leakage tests assert **response bodies**, not just status codes: unauthorized
  responses must not contain `salary`, `budget`, `studio_fee`, `fee_percent`, `budget_range`,
  `total_pay`, `paid_amount`, `outstanding`, etc.
- Existing tests asserting L2 access to finance (`test_operational_finance_stays_open_to_admins`)
  are superseded and will be updated to the new boundary.

---
_Last Updated: 2026-08-22_
