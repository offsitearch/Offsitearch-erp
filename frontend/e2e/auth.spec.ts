import { test, expect } from '@playwright/test';

async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.locator('#email').fill('admin@studioerp.dev');
  await page.locator('#password').fill('Studio@2026');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });
}

test.describe('Auth flow', () => {
  test('valid login redirects to dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
    await loginAsAdmin(page);
  });

  test('invalid login shows error message', async ({ page }) => {
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
    await page.goto('/login');
    await page.locator('#email').fill('wrong@example.com');
    await page.locator('#password').fill('WrongPassword123');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 15_000 });
  });

  test('logout redirects to login', async ({ page }) => {
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
    await loginAsAdmin(page);

    await page.getByRole('button', { name: /studio owner/i }).first().click();
    await page.getByRole('button', { name: /sign out/i }).click();
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
  });

  test('protected route redirects to login when unauthenticated', async ({ page }) => {
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.clear());
    await page.context().clearCookies();
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/, { timeout: 15_000 });
  });
});
