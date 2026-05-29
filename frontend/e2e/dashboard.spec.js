import { expect, test } from "@playwright/test";

/**
 * UI correctness tests for the devsecops-coral dashboard.
 *
 * All `/api/*` calls are mocked with deterministic fixtures so the tests
 * verify rendering and the DETECT -> RECOMMEND -> ACT workflow without a
 * running FastAPI backend or live Coral.
 */

const SOURCES = {
  sources: [
    { name: "osv", connected: true, table_count: 1, mode: "cli" },
    { name: "github", connected: true, table_count: 362, mode: "cli" },
    { name: "jira", connected: true, table_count: 11, mode: "cli" },
    { name: "sentry", connected: false, table_count: 0, mode: "cli" },
    { name: "grafana", connected: false, table_count: 0, mode: "cli" },
  ],
};

const POSTURE = {
  critical: 1,
  high: 2,
  medium: 5,
  low: 0,
  unknown: 0,
  untracked: 3,
  total: 8,
  sql: "SELECT * FROM osv.search_vulnerabilities(package => 'pillow')",
  ecosystem: "PyPI",
  packages: ["pillow"],
};

const SCAN = {
  data: [
    {
      package: "pillow",
      cve: "GHSA-pillow-001",
      summary: "Pillow heap buffer overflow",
      severity: "CRITICAL",
      jira_ticket: null,
      jira_status: null,
      tracking_status: "UNTRACKED",
      error_count: 12,
      error_level: "fatal",
    },
    {
      package: "django",
      cve: "GHSA-django-001",
      summary: "Django SQL injection",
      severity: "HIGH",
      jira_ticket: "SSC-1",
      jira_status: "In Progress",
      tracking_status: "In Progress",
      error_count: 0,
      error_level: null,
    },
  ],
  sql: "SELECT osv.id FROM osv.search_vulnerabilities(package => 'pillow') osv LEFT JOIN jira.issues j ON j.jql = 'created >= -365d'",
};

const CORRELATE = {
  data: [
    {
      cve: "GHSA-pillow-001",
      package: "pillow",
      severity: "CRITICAL",
      error_count: 12,
      error_level: "fatal",
      signal: "active",
      summary: "Pillow heap buffer overflow",
    },
  ],
  sql: "SELECT osv.id FROM osv.search_vulnerabilities(package => 'pillow') osv LEFT JOIN sentry.issues se",
};

const TIMELINE = {
  data: [
    {
      event_time: "2026-05-29T10:00:00Z",
      source: "jira",
      event_type: "ticket",
      title: "Create Jira ticket for GHSA-pillow-001",
      detail: "SSC-1",
      severity: "High",
    },
  ],
  sql: "SELECT event_time, source FROM (...) timeline ORDER BY event_time DESC",
};

const ACTIONS = [
  {
    id: 1,
    type: "create_jira",
    status: "pending",
    title: "[Security] CRITICAL vulnerability in pillow (GHSA-pillow-001)",
    detail: "CRITICAL severity CVE with active Sentry error spike. No tracking ticket exists.",
    cve: "GHSA-pillow-001",
    package: "pillow",
    severity: "CRITICAL",
    urgent: true,
  },
  {
    id: 2,
    type: "create_pr",
    status: "pending",
    title: "Draft GitHub PR to upgrade pillow",
    detail: "Upgrade pillow to the latest patched version to remediate GHSA-pillow-001.",
    cve: "GHSA-pillow-001",
    package: "pillow",
    severity: "CRITICAL",
    urgent: true,
  },
  {
    id: 3,
    type: "generate_report",
    status: "pending",
    title: "Generate security posture report",
    detail: "Export a Markdown summary of current vulnerability status.",
    severity: "INFO",
    urgent: false,
  },
];

/** Register deterministic mocks for every dashboard API endpoint. */
async function mockApi(page) {
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = req.url();
    const method = req.method();
    const json = (body, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

    if (method === "POST" && url.includes("/api/actions/approve-all")) {
      return json({
        actions: ACTIONS.map((a) => ({ ...a, status: "done", result: { key: `SSC-${a.id}` } })),
        pending: 0,
        executing: 0,
        done: ACTIONS.length,
        dismissed: 0,
        failed: 0,
      });
    }
    const approveMatch = url.match(/\/api\/actions\/(\d+)\/approve/);
    if (method === "POST" && approveMatch) {
      const id = Number(approveMatch[1]);
      const a = ACTIONS.find((x) => x.id === id) || ACTIONS[0];
      return json({
        ...a,
        status: "done",
        result: { key: "SSC-9", url: "https://example.atlassian.net/browse/SSC-9" },
      });
    }
    const dismissMatch = url.match(/\/api\/actions\/(\d+)\/dismiss/);
    if (method === "POST" && dismissMatch) {
      const id = Number(dismissMatch[1]);
      const a = ACTIONS.find((x) => x.id === id) || ACTIONS[0];
      return json({ ...a, status: "dismissed" });
    }

    if (url.includes("/api/integrations")) return json({ detail: "Not Found" }, 404);
    if (url.includes("/api/sources")) return json(SOURCES);
    if (url.includes("/api/posture")) return json(POSTURE);
    if (url.includes("/api/scan")) return json(SCAN);
    if (url.includes("/api/correlate")) return json(CORRELATE);
    if (url.includes("/api/timeline")) return json(TIMELINE);
    if (url.includes("/api/actions")) {
      return json({
        actions: ACTIONS,
        pending: ACTIONS.length,
        executing: 0,
        done: 0,
        dismissed: 0,
        failed: 0,
      });
    }
    if (url.includes("/api/ask") || url.includes("/api/sql")) {
      return json({ sql: "SELECT 1", analysis: "Analysis text", data: [] });
    }
    return json({ detail: "unmocked" }, 404);
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
});

/** The primary tab navigation buttons live inside the page <nav>. */
function tab(page, name) {
  return page.locator("nav").getByRole("button", { name });
}

test("renders the dashboard shell with tabs and agent tagline", async ({ page }) => {
  await expect(tab(page, /Detect/)).toBeVisible();
  await expect(tab(page, /Actions/)).toBeVisible();
  await expect(tab(page, /Timeline/)).toBeVisible();
  await expect(
    page.getByText("coral reads → agent analyzes → human approves → agent acts"),
  ).toBeVisible();
});

test("posture overview shows severity counts and threat strip", async ({ page }) => {
  await expect(page.getByText("Threat Level")).toBeVisible();
  await expect(page.getByText("Total CVEs")).toBeVisible();
  await expect(page.getByText("Risk Score")).toBeVisible();
  // total CVEs = 8 from POSTURE fixture
  await expect(page.getByText("8", { exact: true }).first()).toBeVisible();
});

test("Detect tab shows scan results, untracked status, and generated SQL", async ({ page }) => {
  await expect(page.getByText("Vulnerability Scan Results")).toBeVisible();
  await expect(page.getByText("GHSA-pillow-001").first()).toBeVisible();
  await expect(page.getByText("UNTRACKED").first()).toBeVisible();
  await expect(page.getByText("Generated Coral SQL")).toBeVisible();
});

test("Actions tab lists pending recommendations with approve controls", async ({ page }) => {
  await tab(page, /Actions/).click();
  await expect(page.getByText("Recommended Actions")).toBeVisible();
  await expect(
    page.getByText("[Security] CRITICAL vulnerability in pillow (GHSA-pillow-001)"),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve All (3)" })).toBeVisible();
  await expect(page.getByText("URGENT").first()).toBeVisible();
});

test("approving a single action transitions it to Executed", async ({ page }) => {
  await tab(page, /Actions/).click();
  await page.getByRole("button", { name: "Approve", exact: true }).first().click();
  await expect(page.getByText(/Executed/).first()).toBeVisible();
});

test("Approve All executes every pending action", async ({ page }) => {
  await tab(page, /Actions/).click();
  await page.getByRole("button", { name: "Approve All (3)" }).click();
  await expect(page.getByText("3 completed")).toBeVisible();
  await expect(page.getByText(/Executed/).first()).toBeVisible();
});

test("dismissing an action marks it Dismissed", async ({ page }) => {
  await tab(page, /Actions/).click();
  await page.getByRole("button", { name: "Dismiss", exact: true }).first().click();
  await expect(page.getByText("Dismissed").first()).toBeVisible();
});

test("Actions tab SQL viewer shows the DETECT + ACT comment block", async ({ page }) => {
  await tab(page, /Actions/).click();
  await expect(page.getByText(/The agent executes via direct API calls/)).toBeVisible();
});

test("Timeline tab renders cross-source events", async ({ page }) => {
  await tab(page, /Timeline/).click();
  await expect(page.getByText("Security Event Timeline")).toBeVisible();
  await expect(page.getByText("Create Jira ticket for GHSA-pillow-001")).toBeVisible();
});
