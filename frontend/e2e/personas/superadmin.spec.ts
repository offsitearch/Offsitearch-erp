import { test, expect } from '@playwright/test';

test.describe('Super Admin Persona', () => {
  test.describe('Sidebar Navigation', () => {
    test('all four nav groups visible with expected items', async ({ page }) => {
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

      await page.goto('/finance/overview');
      await expect(page.getByRole('link', { name: 'Finance' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Vendors' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Reports' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Settings' }).first()).toBeVisible();
    });
  });

  test.describe('Route Access', () => {
    test('can access departments', async ({ page }) => {
      await page.goto('/departments');
      await expect(page).toHaveURL(/\/departments/);
    });

    test('can access finance payroll', async ({ page }) => {
      await page.goto('/finance/payroll');
      await expect(page).toHaveURL(/\/finance\/payroll/);
    });

    test('can access settings, vendors, reports', async ({ page }) => {
      for (const route of ['/settings', '/vendors', '/reports']) {
        await page.goto(route);
        await expect(page).toHaveURL(new RegExp(route));
      }
    });

    test('can access all authenticated routes', async ({ page }) => {
      for (const route of [
        '/projects', '/tasks', '/attendance', '/leaves/my',
        '/notices', '/meetings', '/site-visits', '/notifications',
      ]) {
        await page.goto(route);
        await expect(page).toHaveURL(new RegExp(route));
      }
    });
  });

  test.describe('Dashboard', () => {
    test('shows all admin metric cards', async ({ page }) => {
      await page.goto('/dashboard');
      await expect(page.getByText('Total Employees')).toBeVisible();
      await expect(page.getByText('Active Projects').first()).toBeVisible();
      await expect(page.getByText('Revenue This Month')).toBeVisible();
    });
  });

  test.describe('Attendance Page', () => {
    test('all four tabs visible', async ({ page }) => {
      await page.goto('/attendance');
      const nav = page.getByRole('navigation', { name: 'Attendance sections' });
      await expect(nav.getByText('My Attendance')).toBeVisible();
      await expect(nav.getByText('Today')).toBeVisible();
      await expect(nav.getByText('Calendar')).toBeVisible();
      await expect(nav.getByText('Bulk Entry')).toBeVisible();
    });
  });

  test.describe('Leaves Page', () => {
    test('all three tabs visible', async ({ page }) => {
      await page.goto('/leaves/my');
      const nav = page.getByRole('navigation', { name: 'Leave sections' });
      await expect(nav.getByRole('link', { name: 'My Leaves' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Apply' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Approvals' })).toBeVisible();
    });
  });

  test.describe('Finance Page', () => {
    test('all five tabs visible including Payroll', async ({ page }) => {
      await page.goto('/finance/overview');
      const nav = page.getByRole('navigation', { name: 'Finance sections' });
      await expect(nav.getByRole('link', { name: 'Overview' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Invoices' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Expenses', exact: true })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'My Expenses' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Payroll' })).toBeVisible();
    });
  });

  test.describe('Employees Page', () => {
    test('all three tabs including Departments', async ({ page }) => {
      await page.goto('/employees');
      const nav = page.getByRole('navigation', { name: 'Employees sections' });
      await expect(nav.getByRole('link', { name: 'Directory' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Org Chart' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Departments' })).toBeVisible();
    });
  });

  test.describe('Settings Page', () => {
    test('settings page loads with heading', async ({ page }) => {
      await page.goto('/settings');
      await expect(page.getByRole('heading', { name: 'Settings & Admin' })).toBeVisible();
    });
  });
});
