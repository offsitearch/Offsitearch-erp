> **STATUS (2026-08-24): PRE-ENFORCEMENT AUDIT SNAPSHOT.** The "Today: L2 ⚠" gates and leak
> register below describe the state BEFORE enforcement. All listed exposures are now gated to
> L0/L1 via `require_financial_access()` / redaction — see `financial_access_policy.md` for the
> adopted policy and `_ai_context/SECURITY.md` for the current surface. Vendors rows are moot
> (module deleted 2026-08-24). Open decisions Q1–Q5 were resolved in the policy doc. Invoice
> money fields gained `hsn_sac`/`tax_percent` GST structure via migration 0026.

# Financial Data Inventory

> Phase 1 audit for the financial-isolation requirement: **only L0 (CEO) and L1 (Director)
> may access any financial datum.** This document is the complete map of where financial
> data exists and how it can leave the system today. No code was modified for this audit.
>
> Audited: 2026-08-22 · HEAD of `main` · backend `backend/app/` · frontend `frontend/src/`
> Method: full-model/schema/route sweep + dashboard/report/export service review +
> frontend component sweep. All line references verified against current files.

## Classification legend

| Cat | Meaning |
|-----|---------|
| A | Direct financial data (invoices, expenses, payroll, salary) |
| B | Business financial data (project budget/fees, client deal values) |
| C | Financial aggregations (revenue totals, profitability, KPIs) |
| D | Financial exports (PDF/XLSX/CSV, emailed invoices) |
| E | Indirect exposure (money fields riding in operational responses) |

Current gate column uses the **effective** server-side authorization.
`auth-only` = any authenticated user (L0–L6 and unleveled).

---

## 1. Backend — money-bearing model columns

### Finance (`modules/finance/models.py`) — Cat A
| Field | Column | Line |
|---|---|---|
| Invoice.subtotal / tax_percent / tax_amount / total | Numeric(14,2)/(5,2) | :28-31 |
| Invoice.paid_amount, payment_date, payment_method | Numeric/date/str | :36-40 |
| InvoiceItem.quantity / rate / amount | Numeric | :60-62 |
| Expense.amount | Numeric(14,2) | :73 |

### Payroll (`modules/payroll/models.py`) — Cat A (+banking PII)
| Field | Column | Line |
|---|---|---|
| PayrollEntry.gross_salary / deductions / net_pay | Numeric(14,2) | :42-44 |
| PayrollEntry.payslip_path (salary PDF pointer) | str | :45 |
| SalaryComponent.ctc_annual / basic / hra / special_allowance / pf_deduction | Numeric(14,2) | :60-64 |
| SalaryComponent.bank_name / account_number / ifsc_code | banking PII | :65-67 |

### Projects (`modules/projects/models.py`) — Cat B
| Field | Column | Line |
|---|---|---|
| Project.budget | Numeric(14,2) | :29 |
| Project.studio_fee | Numeric(14,2) | :30 |
| Project.fee_type ("percent"/…) | String(20) | :31 |
| Project.fee_percent | Numeric(5,2) | :32 |
| ProjectPhase.studio_fee | Numeric(14,2) | :86 |

### Clients (`modules/clients/models.py`) — Cat B/E
| Field | Column | Line | Note |
|---|---|---|---|
| Client.budget_range | String(40), free text ("20 Cr+") | :29 | quasi-financial string — easy to miss in scrub |
| Client.deal_stage | enum | :33 | commercial pipeline state (policy call needed) |
| Client.gst_number / pan_number | fiscal identity | :25-26 | not amounts; policy call needed |

### Vendors (`modules/vendors/models.py`)
No amount columns exist today. `rating Numeric(2,1)` (:25) is **not** money.
`gst_number` (:23) and `bank_details Text` (:24) are payment-identity PII — policy call needed.

### Employees / Users
No salary columns on `User`. Compensation lives in `SalaryComponent` via
`User.salary` relationship (`modules/identity/models.py:85-87`). Employee documents may
include uploaded payslips (`doc_type="salary"`, `utils/enums.py:140`).

### Settings (`modules/settings/models.py:15`, seeds `data.py:21-31`)
Company profile JSONB holds GSTIN etc. — business identity, not amounts. Flagged only.

---

## 2. Backend — response schemas exposing money

| Schema | Money fields | File:line |
|---|---|---|
| InvoiceItemOut / InvoiceOut | rate, amount; subtotal/tax_*/total/paid_amount + items[] | finance/schemas.py:15-23, 52-72 |
| ExpenseOut | amount | finance/schemas.py:94-106 |
| PayrollEntryOut / PayrollRunOut | gross/deductions/net; **total_pay aggregate** + entries[] | payroll/schemas.py:7-28 |
| SalaryUpdate (in) / SalaryOut | full CTC breakdown + bank account/IFSC | employees/schemas.py:134-160 |
| ProjectListItem | **budget, studio_fee on every list row** | projects/schemas.py:109-126 |
| ProjectOut | budget, studio_fee, fee_type, fee_percent + phases[].studio_fee | projects/schemas.py:129-157 |
| PhaseOut → BoardOut/BoardColumn | studio_fee rides into kanban payload | projects/schemas.py:95-106, 167-178 |
| ClientListItem / ClientOut | budget_range, deal_stage, gst/pan | clients/schemas.py:55-95 |
| ClientProjectSummary | budget, studio_fee per project | clients/schemas.py:105-115 |
| FinancialSummary | total_budget, total_studio_fee, invoiced, received, outstanding | clients/schemas.py:138-144 |
| ClientProfileOut | embeds all of the above | clients/schemas.py:147-151 |

`ProfileOut` / `UserOut` do **not** embed salary (verified clean).

---

## 3. Backend — endpoint exposure matrix

### Directly financial endpoints (endpoint's purpose is the money)

| Endpoint | Today | Data | Cat |
|---|---|---|---|
| GET `/finance/overview` | `require_revenue_access()` = L1 ✔ | invoiced/received/outstanding/expenses/profit, period compare | A,C |
| GET/POST `/invoices`, GET/PATCH `/invoices/{id}` | **L2 ⚠** | full invoice money + items | A |
| POST `/invoices/{id}/send` | **L2 ⚠** | triggers client email containing invoice **total** (out-of-band channel) | D |
| POST `/invoices/{id}/payment` | **L2 ⚠** | records paid_amount | A |
| GET `/invoices/{id}/pdf` | **L2 ⚠** | PDF with subtotal/tax/total/paid/balance-due (`utils/pdf.py:330-342`) | D |
| GET/POST/PATCH `/expenses*`, GET `/expenses/{id}/receipt` | **L2 ⚠** | expense amounts + receipt file download | A,D |
| GET `/payroll` (+month/year) | L1 ✔ | per-user gross/deductions/net + total_pay | A,C |
| POST `/payroll/process` | L1 ✔ | computes + returns entries | A |
| GET `/payroll/{m}/{y}/payslips/{user_id}` | L1 ✔ | payslip PDF (gross/deductions/net) | D |
| GET/PUT `/employees/{user_id}/salary` | **L2 ⚠** | CTC components **+ bank account/IFSC** | A |
| GET `/reports/finance` (+csv/xlsx) | `require_revenue_access()` = L1 ✔ | per-invoice totals, AR aging, expense-by-category, profit | C,D |
| GET `/reports/projects` (+csv/xlsx) | **L2 ⚠** | per-project budget/studio_fee/expenses + portfolio totals (`reports/routes.py:50-61`, service :90-127) | B,C,D |

### Indirect exposure (money inside operational endpoints)

| Endpoint | Today | Leak |
|---|---|---|
| GET `/projects` | auth-only (staff band row-scoped) | `budget`, `studio_fee` on every row — E |
| GET `/projects/{id}` | auth-only (staff band membership-scoped) | budget, studio_fee, fee_type, fee_percent, phases[].studio_fee — E |
| PATCH `/projects/{id}` | `can_manage_project` (L2+, or **L3 assigned lead**) | returns full money payload; **an L3 lead can WRITE budget/fee values** — E |
| POST/PATCH `/projects/{id}/phases[/phase_id]` | `can_manage_project`; phase routes at routes.py:198/:225 are can_manage-gated via project load | accepts + stores phase studio_fee writes — E |
| GET `/projects/{id}/board` | **auth-only, NO scoping at all** (routes.py:178-185) | any user × any project → kanban incl. per-phase `studio_fee` — worst project leak — E |
| GET `/clients` | **auth-only** (routes.py:34-44) | `budget_range` + deal_stage to every user down to L6 — E |
| GET `/clients/{client_id}` | **auth-only** (routes.py:61-70) | ClientProfileOut = client + projects[].budget/studio_fee + **financial_summary{invoiced/received/outstanding/…}** — worst overall leak — E |
| POST/PATCH `/clients` | L3 | accepts/returns budget_range — E |
| GET/PUT `/employees/{id}/salary` | L2 (listed above) | also indirect via admin UI flows |
| GET `/dashboard/summary` | auth-only | `revenue_this_month` computed **only if has_min_level(user,"L1")**, else serialized null (routes.py:77-105) — correct behavior, ad-hoc implementation |
| GET `/audit-logs`(+count/export) | L2 | metadata: who/when touched `invoice`/`expense`/`salary` entities + entity_ids (no amounts; list endpoint includes details JSONB) — inference risk, low |

### Write-side money inputs (who can currently *change* financial data)

| Action | Today |
|---|---|
| Create/edit invoices, record payments, approve expenses | L2 |
| Set employee salary (CTC + bank details) | L2 |
| Process payroll runs | L1 |
| Edit project budget/studio_fee/fee_percent | L2+, or **L3 assigned lead** |
| Phase studio_fee writes | same as above |
| Set client budget_range | L3 |

### Search / sort / filter
- **No `sort_by` parameter exists anywhere in the backend** (verified by grep); ordering is hardcoded.
  ⇒ no money-sorting leak vector today.
- Money-adjacent filters that exist: invoice search by `invoice_number`
  (finance/service.py:168-170); expense filters category/project/status/month/year
  (:357-369). Both live behind their module gates.

---

## 4. Services / aggregations / exports inventory

| Producer | Metrics | Served by | Today |
|---|---|---|---|
| finance/service.py `_overview_metrics` :476-521, `finance_overview` :524-536 | revenue aggregates + profit + previous-period compare | GET /finance/overview | L1 ✔ |
| finance/service.py `_invoice_dict` :49-81, `build_invoice_pdf` :304-322 | invoice money dicts + PDF block | /invoices*, PDF route | L2 ⚠ |
| payroll/service.py `_compute_entries` :58-115, `_run_dict` :143-155, payslip gen :217-278 | prorated salary figures, total_pay, payslip PDF | /payroll* | L1 ✔ |
| clients/service.py `get_profile` :163-216 | per-project budget/fee + financial_summary (invoiced/received/outstanding currently hardcoded zero) | GET /clients/{id} | **auth-only ⚠⚠** |
| dashboard/routes.py :40-107 | counts + conditional `revenue_this_month` (sum Invoice.paid_amount MTD) | GET /dashboard/summary | field-level L1 ✔ (ad-hoc) |
| reports/service.py `projects_report` :69-128 | budget/fee/expense per project + totals | /reports/projects | L2 ⚠ |
| reports/service.py `finance_report` :131-213 | invoiced/received/outstanding/profit, aging buckets, expense-by-category | /reports/finance | L1 ✔ |
| reports/service.py `hr_report` :216-322 | attendance/headcount — **no salary columns** | /reports/hr | L2 ✔ non-financial |
| utils/pdf.py invoice block :250-360, payslip :406-439; utils/xlsx.py writers | file exports | via routes above | gates ride on routes |
| audit CSV export (audit/routes.py:82) | no amounts | /audit-logs/export | L2 |

---

## 5. Frontend financial surface map

Gates quoted as implemented (`canAccess(org_level_code, minLevel)` mirrors backend rank logic).

| Surface | Money shown | Gate today | File |
|---|---|---|---|
| Route `/finance` (FinanceTabs: invoices, expenses, overview) | full finance UI | **route minLevel L2** ⚠ (overview tab already 403s for L2 — pre-existing mismatch) | App.tsx:95,108; FinanceTabs.tsx:13 |
| Route `/reports` | report cards + CSV/XLSX buttons | **route minLevel L2** ⚠ | App.tsx:104-ish; ReportsPage.tsx |
| Route `/payroll` | runs, entries, payslips | route minLevel L1 ✔ | App.tsx:101-102 |
| DashboardPageNew | Revenue-this-month card (:623-667), Revenue snapshot section (:982-1055, `{isAdmin && …}` :1305), overdue-invoices link (:603-608), New-invoice action (:736-741) | `isAdmin = canAccess(level,'L2')` (:334) ⚠ — card renders but server sends null below L1 | DashboardPageNew.tsx |
| ProjectsPage / ProjectDetailPage / EditProjectModal / PhaseEditModal | budget & fee columns/cards/inputs (₹ literals :527,:537,:185,:194,:477) | detail-page `canManage = canAccess('L2') \|\| (L3 && lead)` (:135-137) unlocks money **editing**; display itself ungated ⚠ | pages/projects/* |
| ClientsPage cards + CreateClientModal | budget_range chips (:51-55), budget input (:430-438) | route L3 only ⚠ | ClientsPage.tsx |
| ClientProfilePage | total_budget/total_studio_fee stat cards (:145-149), studio-fee column (:187), Invoiced/Received/Outstanding aside (:252-254), budget_range edit in modal (:456-486) | route L3 only ⚠ | ClientProfilePage.tsx |
| VendorsPage + VendorProfileModal | bank_details render (:549) + form input (:414-421) | route L2 ⚠ (policy call pending) | VendorsPage.tsx |
| EmployeeProfilePage SalarySection | CTC breakdown + bank details, set-salary form | inline `canAccess('L2')` (:82, :242, :279; queries enabled-gated :94-101) ⚠ | EmployeeProfilePage.tsx |
| Sidebar nav | finance L2, vendors L2, reports L2, clients L3, payroll L1 | AppLayout.tsx:60-85 | |
| api/*.ts + lib/types.ts | money-typed interfaces, zero client-side role logic (correct — backend must enforce) | n/a | |

Money formatting: shared `formatINR` (~57 call sites across 12 files);
SalarySection uses a local `toLocaleString('en-IN')` bypass (:728-731).

---

## 6. Leak-risk register (ranked)

1. **CRITICAL** — `GET /clients/{id}` and `GET /clients`: financial_summary + per-project
   budgets + budget_range to **every authenticated user including L6 interns**
   (clients/routes.py:34-44, 61-70). UI hides below L3; API does not.
2. **CRITICAL** — Project money to everyone: list/detail/board expose budget, studio_fee,
   fee_* ; `/board` additionally has **no scoping whatsoever** (any project id, any user).
   An L3 lead can also **write** budgets/fees today.
3. **HIGH** — Salary endpoints gated at L2 (CTC + bank account/IFSC readable/writable by
   department heads).
4. **HIGH** — Invoices/expenses gated at L2 (totals, payments, outstanding, receipts,
   invoice PDFs) — codified by `test_operational_finance_stays_open_to_admins`, which will
   conflict with the new rule and be rewritten.
5. **MEDIUM** — `/reports/projects` emits budget/fee/expense columns + totals at L2,
   exportable XLSX/CSV — a de-facto profitability report outside the revenue gate.
6. **MEDIUM** — Out-of-band channels: invoice email carries the total to the client
   contact (fine — recipient is counterparty — but endpoint trigger must be L0/L1);
   PDF/XLSX/receipt downloads inherit their JSON route gates, so re-gating routes covers them.
7. **LOW/MEDIUM** — Audit-log metadata reveals timing/actors of financial-entity actions to L2.
8. **LOW** — Quasi-financial strings (`budget_range`, `fee_type`) and identity fields
   (GST/PAN/bank details) are easy to miss in a numeric-field-only scrub.

**Correct today, keep it that way:** dashboard nulls revenue below L1; `/reports/hr` has no
salary; Profile/User schemas exclude salary; no sort-by-money parameters anywhere.

---

## 7. Incidental defects discovered during audit (not fixed yet)

1. `reports/service.py:226` — `OrgLevel` used without import → `GET /reports/hr` raises
   NameError at runtime regardless of permissions.
2. `/projects/{id}/board` missing staff-band/membership scoping (security gap beyond money).

---

## 8. Open policy decisions (block specific chunks, not the whole effort)

| # | Question | Recommendation |
|---|---|---|
| Q1 | `/finance/my-expenses` (self-scoped reimbursement submissions) — visible to submitting employees? | Keep self-service: own expense data is personal reimbursement info, not company financial intelligence. Strict reading would break expense submission for everyone. |
| Q2 | Client `deal_stage`, `gst_number`, `pan_number` below L0/L1? | Keep operational (CRM status/fiscal IDs), hide only rupee figures + `budget_range`. |
| Q3 | Vendor `bank_details` under the financial boundary? | Yes — payment-identity data belongs behind L0/L1. |
| Q4 | Audit-log metadata about financial entities for L2? | Defer (no amounts leaked). |
| Q5 | Money **writes**: confirm budget/fee editing moves from "L2+/L3-lead" to L0/L1. | Yes — write access implies read access; consistent with spec §17. |
