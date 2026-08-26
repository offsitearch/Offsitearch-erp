import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 45_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/user.json' },
      dependencies: ['setup'],
      testIgnore: /personas\//,
    },
    { name: 'persona-setup', testMatch: /persona-setup\.ts/ },
    {
      name: 'persona-superadmin',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/superadmin.json' },
      dependencies: ['persona-setup'],
      testMatch: /personas\/superadmin\.spec\.ts/,
    },
    {
      name: 'persona-admin',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/admin.json' },
      dependencies: ['persona-setup'],
      testMatch: /personas\/admin\.spec\.ts/,
    },
    {
      name: 'persona-lead',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/lead.json' },
      dependencies: ['persona-setup'],
      testMatch: /personas\/lead\.spec\.ts/,
    },
    {
      name: 'persona-employee',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/employee.json' },
      dependencies: ['persona-setup'],
      testMatch: /personas\/employee\.spec\.ts/,
    },
    {
      name: 'persona-intern',
      use: { ...devices['Desktop Chrome'], storageState: 'e2e/.auth/intern.json' },
      dependencies: ['persona-setup'],
      testMatch: /personas\/intern\.spec\.ts/,
    },
  ],
});
