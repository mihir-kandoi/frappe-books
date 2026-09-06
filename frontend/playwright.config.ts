import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/ui',
  workers: 1,
  use: {
    baseURL: process.env.BOOKS_TEST_URL ?? 'http://books-test.localhost:8000',
    channel: process.env.BOOKS_BROWSER_CHANNEL,
    // Headless Chromium hides scrollbars by default.
    launchOptions: { ignoreDefaultArgs: ['--hide-scrollbars'] },
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});
