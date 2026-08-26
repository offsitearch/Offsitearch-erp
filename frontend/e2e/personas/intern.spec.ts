import { test, expect } from '@playwright/test';

test.describe('Intern Persona', () => {
  test.describe('Sidebar Navigation', () => {
    test('Studio group shows Projects and Tasks — Clients hidden', async ({ page }) => {
      await page.goto('/projects');
      await expect(page.getByRole('link', { name: 'Projects' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Tasks' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Clients' }).first()).not.toBeVisible();
    });

    test('People group shows Attendance and Leaves — Employees hidden', async ({ page }) => {
      await page.goto('/attendance');
      await expect(page.getByRole('link', { name: 'Attendance' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Leaves' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Employees' }).first()).not.toBeVisible();
    });

    test('Studio Life group fully visible', async ({ page }) => {
      await page.goto('/notices');
      await expect(page.getByRole('link', { name: 'Notice Board' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Meetings' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Site Visits' }).first()).toBeVisible();
    });

    test('Administration group completely hidden', async ({ page }) => {
      await page.goto('/dashboard');
      await expect(page.getByText('Administration')).not.toBeVisible();
      await expect(page.getByRole('link', { name: 'Finance' }).first()).not.toBeVisible();
      await expect(page.getByRole('link', { name: 'Vendors' }).first()).not.toBeVisible();
      await expect(page.getByRole('link', { name: 'Reports' }).first()).not.toBeVisible();
      await expect(page.getByRole('link', { name: 'Settings' }).first()).not.toBeVisible();
    });
  });

  test.describe('Route Access — Allowed', () => {
    test('can access common routes', async ({ page }) => {
      for (const route of [
        '/projects', '/tasks', '/attendance', '/leaves/my',
        '/leaves/apply', '/notices', '/meetings', '/site-visits',
        '/notifications', '/finance/my-expenses',
      ]) {
        await page.goto(route);
        await expect(page).toHaveURL(new RegExp(route));
      }
    });
  });

  test.describe('Route Access — Restricted', () => {
    test('CANNOT access employees — redirects to dashboard', async ({ page }) => {
      await page.goto('/employees');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });

    test('CANNOT access clients — redirects to dashboard', async ({ page }) => {
      await page.goto('/clients');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });

    test('CANNOT access finance overview — redirects to dashboard', async ({ page }) => {
      await page.goto('/finance/overview');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });

    test('CANNOT access settings — redirects to dashboard', async ({ page }) => {
      await page.goto('/settings');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });

    test('CANNOT access vendors — redirects to dashboard', async ({ page }) => {
      await page.goto('/vendors');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });

    test('CANNOT access reports — redirects to dashboard', async ({ page }) => {
      await page.goto('/reports');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });

    test('CANNOT access departments — redirects to dashboard', async ({ page }) => {
      await page.goto('/departments');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });
  });

  test.describe('Dashboard', () => {
    test('does NOT show admin metrics', async ({ page }) => {
      await page.goto('/dashboard');
      await expect(page.getByText('Revenue This Month')).not.toBeVisible();
      await expect(page.getByText('Total Employees')).not.toBeVisible();
    });
  });

  test.describe('Attendance Page', () => {
    test('only My Attendance tab — Today, Calendar, Bulk Entry hidden', async ({ page }) => {
      await page.goto('/attendance');
      const nav = page.getByRole('navigation', { name: 'Attendance sections' });
      await expect(nav.getByText('My Attendance')).toBeVisible();
      await expect(nav.getByText('Today')).not.toBeVisible();
      await expect(nav.getByText('Calendar')).not.toBeVisible();
      await expect(nav.getByText('Bulk Entry')).not.toBeVisible();
    });
  });

  test.describe('Leaves Page', () => {
    test('My Leaves and Apply visible — Approvals hidden', async ({ page }) => {
      await page.goto('/leaves/my');
      const nav = page.getByRole('navigation', { name: 'Leave sections' });
      await expect(nav.getByRole('link', { name: 'My Leaves' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Apply' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Approvals' })).not.toBeVisible();
    });
  });

  test.describe('Finance Page', () => {
    test('only My Expenses tab visible — admin tabs hidden', async ({ page }) => {
      await page.goto('/finance/my-expenses');
      await expect(page).toHaveURL(/\/finance\/my-expenses/);
      const nav = page.getByRole('navigation', { name: 'Finance sections' });
      await expect(nav.getByRole('link', { name: 'My Expenses' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Overview' })).not.toBeVisible();
      await expect(nav.getByRole('link', { name: 'Invoices' })).not.toBeVisible();
      await expect(nav.getByRole('link', { name: 'Payroll' })).not.toBeVisible();
    });
  });
});
