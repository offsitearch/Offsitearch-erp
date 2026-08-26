import { test, expect } from '@playwright/test';

test.describe('Project Lead Persona', () => {
  test.describe('Sidebar Navigation', () => {
    test('Studio, People, Studio Life groups visible', async ({ page }) => {
      await page.goto('/projects');
      await expect(page.getByRole('link', { name: 'Projects' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Tasks' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Clients' }).first()).toBeVisible();

      await page.goto('/attendance');
      await expect(page.getByRole('link', { name: 'Employees' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Attendance' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Leaves' }).first()).toBeVisible();

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

  test.describe('Route Access', () => {
    test('can access permitted routes', async ({ page }) => {
      for (const route of [
        '/projects', '/tasks', '/employees', '/attendance',
        '/leaves/my', '/notices', '/meetings', '/site-visits', '/clients',
      ]) {
        await page.goto(route);
        await expect(page).toHaveURL(new RegExp(route));
      }
    });

    test('CANNOT access finance — redirects to dashboard', async ({ page }) => {
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
    test('does NOT show revenue metric', async ({ page }) => {
      await page.goto('/dashboard');
      await expect(page.getByText('Revenue This Month')).not.toBeVisible();
    });
  });

  test.describe('Attendance Page', () => {
    test('three tabs visible — Bulk Entry hidden', async ({ page }) => {
      await page.goto('/attendance');
      const nav = page.getByRole('navigation', { name: 'Attendance sections' });
      await expect(nav.getByText('My Attendance')).toBeVisible();
      await expect(nav.getByText('Today')).toBeVisible();
      await expect(nav.getByText('Calendar')).toBeVisible();
      await expect(nav.getByText('Bulk Entry')).not.toBeVisible();
    });
  });

  test.describe('Leaves Page', () => {
    test('all three tabs visible including Approvals', async ({ page }) => {
      await page.goto('/leaves/my');
      const nav = page.getByRole('navigation', { name: 'Leave sections' });
      await expect(nav.getByRole('link', { name: 'My Leaves' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Apply' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Approvals' })).toBeVisible();
    });
  });

  test.describe('Finance Page', () => {
    test('only My Expenses tab accessible — admin tabs hidden', async ({ page }) => {
      await page.goto('/finance/my-expenses');
      await expect(page).toHaveURL(/\/finance\/my-expenses/);
      const nav = page.getByRole('navigation', { name: 'Finance sections' });
      await expect(nav.getByRole('link', { name: 'My Expenses' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Overview' })).not.toBeVisible();
      await expect(nav.getByRole('link', { name: 'Invoices' })).not.toBeVisible();
      await expect(nav.getByRole('link', { name: 'Payroll' })).not.toBeVisible();
    });
  });

  test.describe('Employees Page', () => {
    test('Directory and Org Chart visible — Departments hidden', async ({ page }) => {
      await page.goto('/employees');
      const nav = page.getByRole('navigation', { name: 'Employees sections' });
      await expect(nav.getByRole('link', { name: 'Directory' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Org Chart' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Departments' })).not.toBeVisible();
    });
  });
});
