"""Integration catalog for pluggable Coral data sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from devsecops_coral.config import osv_spec_path, project_root


@dataclass(frozen=True)
class IntegrationInput:
    """UI-friendly input metadata for a Coral source."""

    key: str
    label: str
    required: bool = True
    secret: bool = False
    placeholder: str = ""
    help_text: str = ""
    default: str = ""


@dataclass(frozen=True)
class Integration:
    """A connectable data source."""

    name: str
    kind: str  # bundled | custom | planned
    description: str
    spec_path: Path | None = None
    docs_url: str = ""
    inputs: list[IntegrationInput] = field(default_factory=list)


INTEGRATIONS: dict[str, Integration] = {
    "osv": Integration(
        name="osv",
        kind="custom",
        description="Open Source Vulnerabilities (Google OSV.dev)",
        spec_path=osv_spec_path(),
        docs_url="https://osv.dev",
    ),
    "github": Integration(
        name="github",
        kind="bundled",
        description="Pull requests, issues, workflows, Dependabot alerts",
        docs_url="https://withcoral.com/docs/reference/bundled-sources#github",
        inputs=[
            IntegrationInput(
                key="GITHUB_TOKEN",
                label="GitHub token",
                secret=True,
                placeholder="ghp_...",
                help_text="Personal access token with read access to the repos you want to query.",
            ),
            IntegrationInput(
                key="GITHUB_API_BASE",
                label="GitHub API base",
                required=False,
                default="https://api.github.com",
                placeholder="https://api.github.com",
                help_text=(
                    "Keep the default for GitHub Cloud. Use your /api/v3 URL for GitHub Enterprise."
                ),
            ),
        ],
    ),
    "jira": Integration(
        name="jira",
        kind="bundled",
        description="Security tickets, triage status, labels",
        docs_url="https://withcoral.com/docs/reference/bundled-sources#jira",
        inputs=[
            IntegrationInput(
                key="JIRA_BASE_URL",
                label="Jira base URL",
                placeholder="https://your-org.atlassian.net",
                help_text="Base URL of your Jira Cloud site.",
            ),
            IntegrationInput(
                key="JIRA_EMAIL",
                label="Jira email",
                placeholder="you@example.com",
                help_text="Email address for the Atlassian account tied to the API token.",
            ),
            IntegrationInput(
                key="JIRA_API_TOKEN",
                label="Jira API token",
                secret=True,
                help_text="API token from Atlassian account settings.",
            ),
        ],
    ),
    "sentry": Integration(
        name="sentry",
        kind="bundled",
        description="Application errors, severity, frequency",
        docs_url="https://withcoral.com/docs/reference/bundled-sources#sentry",
        inputs=[
            IntegrationInput(
                key="SENTRY_ORG",
                label="Sentry org slug",
                placeholder="my-org",
                help_text="Organization slug from the Sentry URL after /organizations/.",
            ),
            IntegrationInput(
                key="SENTRY_TOKEN",
                label="Sentry token",
                secret=True,
                help_text=(
                    "Internal integration token with org:read, event:read, "
                    "member:read, project:read, and project:releases scopes."
                ),
            ),
        ],
    ),
    "grafana": Integration(
        name="grafana",
        kind="bundled",
        description="Alert rules, annotations, dashboards",
        docs_url="https://withcoral.com/docs/reference/bundled-sources#grafana",
        inputs=[
            IntegrationInput(
                key="GRAFANA_URL",
                label="Grafana URL",
                placeholder="https://my-org.grafana.net",
                help_text="Base URL of your Grafana Cloud or self-hosted instance.",
            ),
            IntegrationInput(
                key="GRAFANA_TOKEN",
                label="Grafana token",
                secret=True,
                help_text="Service account token with read access.",
            ),
        ],
    ),
    "sentinel": Integration(
        name="sentinel",
        kind="planned",
        description="Microsoft Sentinel incidents and alerts (custom spec - planned)",
        spec_path=project_root() / "sources" / "sentinel" / "sentinel.yaml",
    ),
    "sentinelone": Integration(
        name="sentinelone",
        kind="planned",
        description="SentinelOne threats and agents (custom spec - planned)",
        spec_path=project_root() / "sources" / "sentinelone" / "s1.yaml",
    ),
    "cybereason": Integration(
        name="cybereason",
        kind="planned",
        description="Cybereason malops and sensors (custom spec - planned)",
        spec_path=project_root() / "sources" / "cybereason" / "cybereason.yaml",
    ),
}


def list_integrations() -> list[Integration]:
    """Return all known integrations."""
    return list(INTEGRATIONS.values())


def get_integration(name: str) -> Integration:
    """Look up an integration by name."""
    key = name.lower().strip()
    if key not in INTEGRATIONS:
        msg = f"Unknown integration: {name}. Run 'devsecops-coral integrations list'."
        raise ValueError(msg)
    return INTEGRATIONS[key]
