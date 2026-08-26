import { test as setup, expect } from '@playwright/test';
import { SA_EMAIL, SA_PASSWORD } from './helpers';

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login');
  await page.locator('#email').fill(SA_EMAIL);
  await page.locator('#password').fill(SA_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });
  await page.context().storageState({ path: 'e2e/.auth/user.json' });
});
