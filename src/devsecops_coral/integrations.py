"""Integration catalog for pluggable Coral data sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from devsecops_coral.config import osv_spec_path, project_root


@dataclass(frozen=True)
class Integration:
    """A connectable data source."""

    name: str
    kind: str  # bundled | custom | planned
    description: str
    spec_path: Path | None = None
    docs_url: str = ""


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
    ),
    "jira": Integration(
        name="jira",
        kind="bundled",
        description="Security tickets, triage status, labels",
        docs_url="https://withcoral.com/docs/reference/bundled-sources#jira",
    ),
    "sentry": Integration(
        name="sentry",
        kind="bundled",
        description="Application errors, severity, frequency",
        docs_url="https://withcoral.com/docs/reference/bundled-sources#sentry",
    ),
    "grafana": Integration(
        name="grafana",
        kind="bundled",
        description="Alert rules, annotations, dashboards",
        docs_url="https://withcoral.com/docs/reference/bundled-sources#grafana",
    ),
    "sentinel": Integration(
        name="sentinel",
        kind="planned",
        description="Microsoft Sentinel incidents and alerts (custom spec — planned)",
        spec_path=project_root() / "sources" / "sentinel" / "sentinel.yaml",
    ),
    "sentinelone": Integration(
        name="sentinelone",
        kind="planned",
        description="SentinelOne threats and agents (custom spec — planned)",
        spec_path=project_root() / "sources" / "sentinelone" / "s1.yaml",
    ),
    "cybereason": Integration(
        name="cybereason",
        kind="planned",
        description="Cybereason malops and sensors (custom spec — planned)",
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
