/**
 * Static integration catalog used when /api/integrations is unavailable.
 * Mirrors backend integration metadata for source connection forms.
 */
export const INTEGRATION_CATALOG = [
  {
    name: "osv",
    kind: "custom",
    description: "Open Source Vulnerabilities (Google OSV.dev)",
    docs_url: "https://osv.dev",
    inputs: [],
  },
  {
    name: "github",
    kind: "bundled",
    description: "Pull requests, issues, workflows, Dependabot alerts",
    docs_url: "https://withcoral.com/docs/reference/bundled-sources#github",
    inputs: [
      {
        key: "GITHUB_TOKEN",
        label: "GitHub token",
        required: true,
        secret: true,
        placeholder: "ghp_...",
        help_text: "Personal access token with read access to the repos you want to query.",
        default: "",
      },
      {
        key: "GITHUB_API_BASE",
        label: "GitHub API base",
        required: false,
        secret: false,
        placeholder: "https://api.github.com",
        help_text: "Use the default for GitHub Cloud, or your /api/v3 URL for GitHub Enterprise.",
        default: "https://api.github.com",
      },
    ],
  },
  {
    name: "jira",
    kind: "bundled",
    description: "Security tickets, triage status, labels",
    docs_url: "https://withcoral.com/docs/reference/bundled-sources#jira",
    inputs: [
      {
        key: "JIRA_BASE_URL",
        label: "Jira base URL",
        required: true,
        secret: false,
        placeholder: "https://your-org.atlassian.net",
        help_text: "Base URL of your Jira Cloud site.",
        default: "",
      },
      {
        key: "JIRA_EMAIL",
        label: "Jira email",
        required: true,
        secret: false,
        placeholder: "you@example.com",
        help_text: "Email address for the Atlassian account tied to the API token.",
        default: "",
      },
      {
        key: "JIRA_API_TOKEN",
        label: "Jira API token",
        required: true,
        secret: true,
        placeholder: "",
        help_text: "API token from Atlassian account settings.",
        default: "",
      },
    ],
  },
  {
    name: "sentry",
    kind: "bundled",
    description: "Application errors, severity, frequency",
    docs_url: "https://withcoral.com/docs/reference/bundled-sources#sentry",
    inputs: [
      {
        key: "SENTRY_ORG",
        label: "Sentry org slug",
        required: true,
        secret: false,
        placeholder: "my-org",
        help_text: "Organization slug from the Sentry URL after /organizations/.",
        default: "",
      },
      {
        key: "SENTRY_TOKEN",
        label: "Sentry token",
        required: true,
        secret: true,
        placeholder: "",
        help_text: "Token with org and project read permissions.",
        default: "",
      },
    ],
  },
  {
    name: "grafana",
    kind: "bundled",
    description: "Alert rules, annotations, dashboards",
    docs_url: "https://withcoral.com/docs/reference/bundled-sources#grafana",
    inputs: [
      {
        key: "GRAFANA_URL",
        label: "Grafana URL",
        required: true,
        secret: false,
        placeholder: "https://my-org.grafana.net",
        help_text: "Base URL of your Grafana Cloud or self-hosted instance.",
        default: "",
      },
      {
        key: "GRAFANA_TOKEN",
        label: "Grafana token",
        required: true,
        secret: true,
        placeholder: "",
        help_text: "Service account token with read access.",
        default: "",
      },
    ],
  },
];

/**
 * Merge live source status from /api/sources into the static catalog.
 * @param {Array<object>} [sources] - Connected source metadata from the API.
 * @returns {Array<object>} Catalog entries enriched with connection state.
 */
export function mergeSourcesIntoCatalog(sources = []) {
  const sourceMap = Object.fromEntries(
    sources.map((source) => [String(source.name || "").toLowerCase(), source]),
  );

  return INTEGRATION_CATALOG.map((item) => {
    const source = sourceMap[item.name] || {};
    return {
      ...item,
      connected: Boolean(source.connected),
      table_count: source.table_count ?? 0,
      mode: source.mode || "cli",
    };
  });
}
