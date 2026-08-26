import { test, expect } from '@playwright/test';

test.describe('Admin / HR Persona', () => {
  test.describe('Sidebar Navigation', () => {
    test('all nav groups visible including Administration', async ({ page }) => {
      await page.goto('/projects');
      await expect(page.getByRole('link', { name: 'Projects' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Clients' }).first()).toBeVisible();

      await page.goto('/attendance');
      await expect(page.getByRole('link', { name: 'Employees' }).first()).toBeVisible();

      await page.goto('/finance/overview');
      await expect(page.getByRole('link', { name: 'Finance' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Vendors' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Reports' }).first()).toBeVisible();
      await expect(page.getByRole('link', { name: 'Settings' }).first()).toBeVisible();
    });
  });

  test.describe('Route Access', () => {
    test('can access admin routes', async ({ page }) => {
      for (const route of [
        '/departments', '/finance/overview', '/finance/invoices',
        '/finance/expenses', '/reports', '/settings',
        '/vendors', '/employees', '/clients',
      ]) {
        await page.goto(route);
        await expect(page).toHaveURL(new RegExp(route));
      }
    });

    test('can access common routes', async ({ page }) => {
      for (const route of [
        '/projects', '/tasks', '/attendance', '/leaves/my',
        '/notices', '/meetings', '/site-visits', '/finance/my-expenses',
      ]) {
        await page.goto(route);
        await expect(page).toHaveURL(new RegExp(route));
      }
    });

    test('CANNOT access payroll — redirects to dashboard', async ({ page }) => {
      await page.goto('/finance/payroll');
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    });
  });

  test.describe('Dashboard', () => {
    test('shows admin metric cards', async ({ page }) => {
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
    test('four tabs visible — Payroll hidden', async ({ page }) => {
      await page.goto('/finance/overview');
      const nav = page.getByRole('navigation', { name: 'Finance sections' });
      await expect(nav.getByRole('link', { name: 'Overview' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Invoices' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Expenses', exact: true })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'My Expenses' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Payroll' })).not.toBeVisible();
    });
  });

  test.describe('Employees Page', () => {
    test('all three tabs visible including Departments', async ({ page }) => {
      await page.goto('/employees');
      const nav = page.getByRole('navigation', { name: 'Employees sections' });
      await expect(nav.getByRole('link', { name: 'Directory' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Org Chart' })).toBeVisible();
      await expect(nav.getByRole('link', { name: 'Departments' })).toBeVisible();
    });
  });

  test.describe('Settings Page', () => {
    test('settings page loads', async ({ page }) => {
      await page.goto('/settings');
      await expect(page.getByRole('heading', { name: 'Settings & Admin' })).toBeVisible();
    });
  });
});
