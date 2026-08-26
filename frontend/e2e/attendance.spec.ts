import { test, expect } from '@playwright/test';

test.describe('Attendance', () => {
  test('attendance page loads with heading', async ({ page }) => {
    await page.goto('/attendance');
    await expect(page.getByRole('heading', { name: 'Attendance' })).toBeVisible();
  });

  test('check-in button is visible', async ({ page }) => {
    await page.goto('/attendance');
    await expect(page.getByRole('button', { name: 'Check In' })).toBeVisible();
  });
});
