import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('dashboard loads with greeting and stat cards', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.getByText('Total Employees').first()).toBeVisible();
  });

  test('dashboard has quick action buttons', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByRole('link', { name: 'Apply leave' }).first()).toBeVisible();
  });
});
