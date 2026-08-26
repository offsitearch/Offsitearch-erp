import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

async function resetTodayAttendance(page: Page): Promise<void> {
  const now = new Date();
  const todayISO = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate(),
  ).padStart(2, '0')}`;

  const result = await page.evaluate(
    async ({ month, year, todayISO }) => {
      const raw = localStorage.getItem('studio-erp-auth');
      const token = raw ? JSON.parse(raw).state.accessToken : null;
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
      const me = await fetch(`/api/v1/attendance/me?month=${month}&year=${year}`, { headers });
      const body = await me.json();
      const record = body.records?.find((r) => r.date === todayISO);
      if (!record) return 'clean';
      const patch = await fetch(`/api/v1/attendance/${record.id}`, {
        method: 'PATCH',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'absent',
          check_in_time: null,
          check_out_time: null,
          notes: null,
        }),
      });
      return patch.ok ? 'reset' : `reset-failed:${patch.status}`;
    },
    { month: now.getMonth() + 1, year: now.getFullYear(), todayISO },
  );
  expect(result).not.toMatch(/^reset-failed/);
}

test('check in (idempotent, resets today first)', async ({ page }) => {
  await page.goto('/attendance');
  await expect(page.getByRole('heading', { name: 'Attendance' })).toBeVisible();
  await resetTodayAttendance(page);
  await page.reload();

  const checkIn = page.getByRole('button', { name: 'Check In' });
  await expect(checkIn).toBeVisible();
  await checkIn.click();
  await expect(page.getByText(/Checked in successfully/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Check Out' })).toBeVisible();
});

test('create a project with auto-generated phases', async ({ page }) => {
  const projectName = `E2E Project ${Date.now()}`;

  await page.goto('/projects');
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();

  await page.getByRole('button', { name: 'New Project' }).first().click();
  await page.getByLabel('Project name').fill(projectName);
  await page.getByRole('button', { name: 'Create Project' }).click();

  await expect(page.getByText(projectName)).toBeVisible({ timeout: 20_000 });
});

test('create an invoice opens modal', async ({ page }) => {
  await page.goto('/finance/invoices');
  await expect(page.getByRole('heading', { name: 'Invoices' })).toBeVisible();

  await page.getByRole('button', { name: 'New Invoice' }).first().click();

  await expect(page.getByRole('heading', { name: 'New Invoice' })).toBeVisible();
  await expect(page.getByLabel('Client')).toBeVisible();
});
