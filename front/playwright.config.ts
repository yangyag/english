import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests', workers: 1, timeout: 120_000,
  use: { baseURL: 'http://127.0.0.1:13000', browserName: 'chromium', headless: true },
  webServer: { command: 'npm run dev -- --host 127.0.0.1 --port 13000', url: 'http://127.0.0.1:13000', reuseExistingServer: false, timeout: 120_000 },
})
