import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '/app/tests/e2e',
  outputDir: '/tmp/test-results',
  timeout: 60000,
  retries: 0,
  workers: 1,
  reporter: [
    ['line'],
    ['json', { outputFile: '/tmp/test-results/results.json' }],
  ],
  use: {
    baseURL: 'http://localhost:8001',
    screenshot: 'only-on-failure',
    trace: 'off',
    headless: true,
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
