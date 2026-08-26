import { test as setup, expect } from '@playwright/test';
import { SA_EMAIL, SA_PASSWORD } from './helpers';

const KNOWN_PASSWORD = 'E2ETest123';

const PERSONAS = [
  { name: 'Zara Admin', level: 'L2', authFile: 'e2e/.auth/admin.json' },
  { name: 'Arnav Lead', level: 'L3', authFile: 'e2e/.auth/lead.json' },
  { name: 'Chetan Worker', level: 'L5', authFile: 'e2e/.auth/employee.json' },
  { name: 'Esha Intern', level: 'L6', authFile: 'e2e/.auth/intern.json' },
];

setup('seed persona users and save all auth states', async ({ page }) => {
  setup.setTimeout(180_000);

  // 1. Login as superadmin via UI
  await page.goto('/login');
  await page.locator('#email').fill(SA_EMAIL);
  await page.locator('#password').fill(SA_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });

  // Save superadmin auth state
  await page.context().storageState({ path: 'e2e/.auth/superadmin.json' });
  await page.context().storageState({ path: 'e2e/.auth/user.json' });

  // 2. Find each persona user and reset their password to KNOWN_PASSWORD
  const results: { email: string; name: string }[] = await page.evaluate(
    async ({ personas, password }) => {
      const raw = localStorage.getItem('studio-erp-auth');
      const token = raw ? JSON.parse(raw).state.accessToken : null;
      if (!token) throw new Error('No auth token in localStorage');

      const headers = {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      // Fetch all users
      const listResp = await fetch('/api/v1/users?page_size=100', { headers });
      const listData = await listResp.json();
      const items: Array<Record<string, unknown>> = listData.items || listData;

      const levelsResp = await fetch('/api/v1/org-levels', { headers });
      const levelsData = await levelsResp.json();
      const levels: Array<Record<string, unknown>> = Array.isArray(levelsData)
        ? levelsData
        : levelsData.items || [];
      const levelIdFor = (code: string): number | null => {
        const found = levels.find((l) => l.code === code);
        return found ? Number(found.id) : null;
      };

      const results: { email: string; name: string }[] = [];

      for (const p of personas) {
        const user = items.find(
          (u) => u.name === p.name && u.org_level_code === p.level,
        );
        if (!user) {
          console.warn(`Persona user ${p.name} (${p.level}) not found in DB — creating`);
          // Create with known password
          const createResp = await fetch('/api/v1/users', {
            method: 'POST',
            headers,
            body: JSON.stringify({ name: p.name, org_level_id: levelIdFor(p.level), password }),
          });
          if (createResp.ok) {
            const data = await createResp.json();
            results.push({ email: data.email, name: p.name });
          }
          continue;
        }

        // Reset password to known value
        await fetch(`/api/v1/users/${user.id}`, {
          method: 'PATCH',
          headers,
          body: JSON.stringify({ password }),
        });

        results.push({ email: user.email as string, name: p.name });
      }
      return results;
    },
    { personas: PERSONAS, password: KNOWN_PASSWORD },
  );

  // 3. For each persona, login via UI and save auth state
  for (const cred of results) {
    const persona = PERSONAS.find((p) => p.name === cred.name)!;

    // Clear session
    await page.context().clearCookies();
    await page.evaluate(() => localStorage.clear());

    await page.goto('/login');
    await page.locator('#email').fill(cred.email);
    await page.locator('#password').fill(KNOWN_PASSWORD);
    await page.getByRole('button', { name: 'Sign in' }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });

    await page.context().storageState({ path: persona.authFile });

    // Re-login as superadmin for next persona (unless last)
    if (cred !== results[results.length - 1]) {
      await page.context().clearCookies();
      await page.evaluate(() => localStorage.clear());
      await page.goto('/login');
      await page.locator('#email').fill(SA_EMAIL);
      await page.locator('#password').fill(SA_PASSWORD);
      await page.getByRole('button', { name: 'Sign in' }).click();
      await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });
    }
  }
});
