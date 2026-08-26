import { expect, type Page } from '@playwright/test';

export const SA_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@studioerp.dev';
export const SA_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'Studio@2026';
export const API_BASE = process.env.E2E_API_URL ?? 'http://localhost:8000';

export async function loginViaUI(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });
}

export async function expectHidden(page: Page, text: string) {
  await expect(page.getByRole('link', { name: text }).first()).not.toBeVisible();
}

export async function expectVisible(page: Page, text: string) {
  await expect(page.getByRole('link', { name: text }).first()).toBeVisible();
}
