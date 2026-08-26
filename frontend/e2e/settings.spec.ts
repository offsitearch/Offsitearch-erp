import { test, expect } from '@playwright/test';

test.describe('Settings', () => {
  test('settings page loads with sections', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings & Admin' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Company' })).toBeVisible();
  });

  test('settings has company profile section', async ({ page }) => {
    await page.goto('/settings');
    await page.getByRole('button', { name: 'Company' }).click();
    await expect(page.getByRole('heading', { name: 'Company profile' })).toBeVisible();
  });

  test('theme toggle works', async ({ page }) => {
    await page.goto('/dashboard');
    const html = page.locator('html');

    const toggle = page.getByRole('button', { name: /switch to (dark|light|system) mode/i });
    await expect(toggle).toBeVisible();

    await toggle.click();
    await page.waitForTimeout(500);

    await toggle.click();
    await page.waitForTimeout(500);
  });
});
