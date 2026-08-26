# ⚛️ Frontend Architecture (React)

React 18 + TypeScript + Vite + Tailwind CSS. Feature-first organization so each ERP module is self-contained and removable.

---

## 1. Routing & Layout

Actual route table (`src/App.tsx`; all pages lazy-loaded):

```
/login                          → LoginPage (6-digit User ID + password)
/                               → protected shell: RequireAuth → AppLayout (sidebar + force-change-password gate)
  /dashboard                    → role-aware home (revenue widgets L0/L1 only)
  /attendance                   → my attendance (check-in/out + history)
  /leaves                       → redirect to /leaves/my
    /leaves/my                  → my leave requests
    /leaves/apply               → apply for leave
    /leaves/approvals           → approvals queue            [L3+]
  /employees                    → directory                  [L3+]
    /employees/org-chart        → org chart                  [L3+]
    /employees/:id              → profile (+ salary L0/L1)   [L3+]
  /departments                  → departments admin          [L2+]
  /projects                     → project list
    /projects/:id               → detail (overview/phases/tasks/team/timeline tabs)
  /clients                      → client list                [L3+]
    /clients/:id                → client profile             [L3+]
  /tasks                        → kanban task board
  /notices                      → notice board
  /meetings                     → meetings + RSVP
  /notifications                → inbox (click = mark read; delete per row)
  /site-visits                  → visit logs + photos + PDF report
  /finance                      → redirect to /finance/overview
    /finance/overview           → finance dashboard          [L1+] (financial)
    /finance/invoices           → GST invoices               [L1+] (financial)
    /finance/expenses           → expenses                   [L1+] (financial)
    /finance/my-expenses        → own expense claims         (all users)
    /finance/payroll            → payroll + payslips         [L1+] (financial)
  /reports                      → reports (attendance/projects/finance/HR tabs) [L1+]
  /settings                     → settings                   [L2+]
       tabs: Company · Attendance · Leave Policy · Holidays · Users · Security · Backup ([L0/L1] only)
  *                             → NotFoundPage
```

> `[Ln]` gates are `<RequireRole minLevel="Ln" />` wrappers backed by `canAccess(userLevel, required)` from `src/lib/constants.ts`. Org levels: **L0 CEO > L1 Director > L2 Dept Head > L3 Lead > L4–L6 staff** (legacy `UserRole` enum was dropped). Financial pages use the `L1` gate to mirror the server-side executive-only money policy. The sidebar renders nav groups filtered by the same check. There is no forgot-password route — credential recovery is an executive's one-time password regeneration.

---

## 2. Folder Structure

```
src/
├── main.tsx                  # QueryClientProvider, RouterProvider
├── App.tsx                   # Router config
├── api/
│   ├── client.ts             # Axios instance + token refresh interceptor
│   ├── auth.ts               # login/logout/me
│   └── endpoints.ts          # typed endpoint helpers per module
├── features/                 # ONE folder per module
│   ├── attendance/
│   │   ├── AttendanceToday.tsx
│   │   ├── AttendanceCalendar.tsx
│   │   ├── CheckInCard.tsx        # employee check-in/out
│   │   ├── BulkAttendance.tsx
│   │   ├── attendance.api.ts      # API calls (TanStack Query)
│   │   ├── useAttendance.ts       # hooks: useTodayAttendance, useMonthly
│   │   └── types.ts               # Zod schemas / TS types
│   ├── leaves/  projects/  clients/
│   ├── finance/  tasks/  reports/  notices/  meetings/  settings/
│   ├── employees/  dashboard/  site-visits/
│   └── auth/
├── components/               # shared UI
│   ├── layout/
│   │   ├── AppLayout.tsx     # Sidebar + Topbar + Outlet
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   ├── ui/                   # shadcn/ui primitives: button, card, dialog...
│   ├── DataTable.tsx         # TanStack Table wrapper (sort/filter/page/export)
│   ├── Modal.tsx
│   ├── StatCard.tsx
│   ├── charts/               # Recharts wrappers: LineChart, DonutChart, BarChart
│   ├── CalendarGrid.tsx      # reusable month calendar (attendance)
│   ├── KanbanBoard.tsx       # dnd-kit board
│   ├── StatusBadge.tsx
│   ├── EmptyState.tsx
│   └── Avatar.tsx
├── hooks/                    # cross-cutting: useAuth, useDebounce, useLocalStorage
├── store/                    # Zustand
│   ├── authStore.ts          # user, tokens, role
│   └── uiStore.ts            # sidebar collapsed, theme, toasts
├── lib/
│   ├── formatters.ts         # INR currency, dates, hours
│   ├── constants.ts          # role names, status colors, module list
│   └── types.ts              # shared types
└── styles/
    ├── index.css             # tailwind directives
    └── theme.ts              # design tokens (see palette below)
```

---

## 3. State Management Strategy

| Kind of state | Tool | Example |
|---------------|------|---------|
| Server data | TanStack Query | today's attendance, project list |
| Mutations | TanStack Query mutations | check-in, create invoice |
| Auth/session | Zustand | user object, role, token |
| UI ephemeral | local state / Zustand uiStore | sidebar collapsed, open modal |

Rule: **server state never lives in client stores.** Every fetch is a `useQuery` keyed by module + params; every write is a `useMutation` that invalidates the relevant keys.

```ts
// Example — attendance module hook
export function useTodayAttendance() {
  return useQuery({ queryKey: ['attendance', 'today'], queryFn: fetchToday });
}
export function useCheckIn() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: checkIn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['attendance'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}
```

---

## 4. Design System

Taken directly from the blueprint's UI guidelines (`Project overview.txt` → "UI/UX Design Guidelines"):

```ts
// tailwind.config.js theme extensions
colors: {
  primary:   '#2C3E50',   // dark blue-gray — architecture feel
  secondary: '#E67E22',   // warm orange — CTAs
  success:   '#27AE60',   // present / approved
  warning:   '#F39C12',   // late / pending / in-progress
  danger:    '#E74C3C',   // absent / overdue
  info:      '#3498DB',   // links / info
  background:'#F8F9FA',
  card:      '#FFFFFF',
  text:      { DEFAULT:'#2C3E50', secondary:'#7F8C8D' },
}
```

- Fonts: **Inter** (headings + body), **JetBrains Mono** for codes/IDs (employee id, invoice numbers)
- Spacing: 8px grid · Cards with subtle elevation · Rounded corners
- Icons: `lucide-react` · Charts: `recharts` · Tables: `tanstack/table`

---

## 5. Shared Components Checklist

| Component | Used for |
|-----------|----------|
| `DataTable` | List pages (employees, clients, invoices, …) |
| `KanbanBoard` | Task board |
| `CalendarGrid` | Monthly attendance view |
| `StatCard` | All dashboard + module KPI cards |
| `StatusBadge` | attendance/leave/invoice status chips |
| `EmptyState` | "No records" screens with illustration + CTA |
| `ChartCard` | Dashboards and reports |
| `DatePicker` / `TimeInput` | Styled date & time controls mirroring native input contracts |
| `CurrencyInput` | ₹ money inputs with live Indian digit grouping |

---

## 6. Key Interactions

- **Check-in**: `CheckInCard` polls `GET /attendance/today` (for the current user) on mount + refetch on window focus; shows live running-hours timer computed from `check_in_time`.
- **Kanban drag**: drag a task card → `useMutation` PATCH task status → optimistic update → invalidate board query.
- **Invoice builder**: line-item table with HSN/SAC codes, quantity × rate amounts and live subtotal/GST/total (recomputed server-side as source of truth; PDF renders CGST/SGST vs IGST breakup).

---

## 7. Vite Config (essentials)

```ts
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': { target: 'http://backend:8000', changeOrigin: true },
    },
  },
});
```

In Docker dev, the proxy target is the `backend` service name; locally it would be `http://localhost:8000`. Use an env var so both work.

---

## 8. Accessibility & Responsiveness

- Desktop-first (studio staff use desktops), but all key flows (check-in, leave apply, task update) must work on mobile — the PWA upgrade (Sprint 6) relies on this.
- Semantic HTML + Radix primitives for dialogs/popovers (focus trap, escape key).
- Color-blind-safe status differentiation (icon + text label, never color alone).
