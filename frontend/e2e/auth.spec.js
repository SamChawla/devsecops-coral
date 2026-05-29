import { expect, test } from "@playwright/test";

/**
 * Covers the public landing page and the auth gate that protects /app.
 * The session is an httpOnly cookie set by the backend; here we mock
 * /api/auth/* so the flows run without a live FastAPI server.
 */

/** Mock the auth endpoints; `authed` controls whether /api/auth/me resolves. */
async function mockAuth(page, { authed = false } = {}) {
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

    if (url.includes("/api/auth/login") || url.includes("/api/auth/signup")) {
      return json({
        user: { id: 1, email: "demo@coral.dev", role: "owner" },
        org: { id: 1, name: "Demo Org" },
      });
    }
    if (url.includes("/api/auth/me")) {
      if (authed) {
        return json({
          user: { id: 1, email: "demo@coral.dev", role: "owner" },
          org: { id: 1, name: "Demo Org" },
        });
      }
      return json({ user: null, org: null });
    }
    // Any dashboard data call after login — keep it cheap and empty.
    return json({ data: [], sql: "SELECT 1", integrations: [], sources: [] });
  });
}

test("landing page presents the product and CTAs", async ({ page }) => {
  await mockAuth(page);
  await page.goto("/");
  await expect(page.getByText("DETECT → RECOMMEND → ACT")).toBeVisible();
  await expect(page.getByRole("link", { name: /Create your workspace/ })).toBeVisible();
  await expect(page.getByRole("link", { name: "Log in" }).first()).toBeVisible();
});

test("visiting /app while signed out redirects to login", async ({ page }) => {
  await mockAuth(page, { authed: false });
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();
});

test("logging in routes to the dashboard", async ({ page }) => {
  await mockAuth(page, { authed: false });
  await page.goto("/login");
  await page.getByPlaceholder("you@company.com").fill("demo@coral.dev");
  await page.getByPlaceholder("••••••••").fill("supersecret");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/app$/);
});
