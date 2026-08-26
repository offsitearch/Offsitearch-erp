import { test, expect } from '@playwright/test';

test.describe('Projects', () => {
  test('projects list page loads', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'New Project' }).first()).toBeVisible();
  });

  test('New Project button is visible', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('button', { name: 'New Project' }).first()).toBeVisible();
  });
});
