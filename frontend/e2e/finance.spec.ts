import { test, expect } from '@playwright/test';

test.describe('Finance', () => {
  test('finance page loads with tabs', async ({ page }) => {
    await page.goto('/finance/overview');
    const nav = page.getByRole('navigation', { name: 'Finance sections' });
    await expect(nav).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Overview' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Invoices' })).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Expenses', exact: true })).toBeVisible();
  });

  test('invoices tab loads', async ({ page }) => {
    await page.goto('/finance/invoices');
    const nav = page.getByRole('navigation', { name: 'Finance sections' });
    await expect(nav.getByRole('link', { name: 'Invoices' })).toBeVisible();
  });
});
