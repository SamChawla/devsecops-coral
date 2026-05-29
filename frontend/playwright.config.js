import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for devsecops-coral dashboard UI tests.
 *
 * Tests run against the Vite dev server and mock all `/api/*` calls via
 * route interception, so they are fast, deterministic, and require neither a
 * running FastAPI backend nor a live Coral connection.
 */
const PORT = 4317;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 7_000 },
  fullyParallel: true,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
