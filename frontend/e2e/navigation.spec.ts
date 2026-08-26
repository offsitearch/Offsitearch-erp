import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('sidebar nav items are visible across groups', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('link', { name: 'Dashboard' }).first()).toBeVisible();

    await page.goto('/projects');
    await expect(page.getByRole('link', { name: 'Projects' }).first()).toBeVisible();

    await page.goto('/attendance');
    await expect(page.getByRole('link', { name: 'Attendance' }).first()).toBeVisible();

    await page.goto('/finance/overview');
    await expect(page.getByRole('link', { name: 'Finance' }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Settings' }).first()).toBeVisible();
  });

  test('navigates to attendance page', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: 'Attendance' }).first().click();
    await expect(page).toHaveURL(/\/attendance/);
  });

  test('navigates to projects page', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: 'Projects' }).first().click();
    await expect(page).toHaveURL(/\/projects/);
  });

  test('navigates to finance page', async ({ page }) => {
    await page.goto('/dashboard');
    await page.getByRole('link', { name: 'Finance' }).first().click();
    await expect(page).toHaveURL(/\/finance/);
  });

  test('responsive mobile nav opens sidebar', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/dashboard');

    const menuButton = page.getByRole('button', { name: 'Open menu' });
    await expect(menuButton).toBeVisible();

    await menuButton.click();
    await expect(page.getByRole('link', { name: 'Dashboard' }).first()).toBeVisible();
  });
});
