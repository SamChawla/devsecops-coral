"""Grafana Annotations API — write timeline markers after CVE remediation."""

from __future__ import annotations

import time
from typing import Any

import httpx

from devsecops_coral.config import GRAFANA_API_KEY, GRAFANA_DASHBOARD_UID, GRAFANA_URL


class GrafanaError(Exception):
    """Raised when a Grafana API call fails."""


def create_annotation(
    *,
    text: str,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a timeline annotation on the configured Grafana dashboard.

    Args:
        text: Annotation label shown on the timeline.
        tags: Optional list of tags (defaults to ``["devsecops-coral", "cve-remediation"]``).

    Returns:
        Dict with keys ``id``, ``url``, and ``message``.

    Raises:
        GrafanaError: If credentials are missing or the API call fails.
    """
    if not GRAFANA_URL:
        raise GrafanaError("GRAFANA_URL is not set in .env")
    if not GRAFANA_API_KEY:
        raise GrafanaError("GRAFANA_API_KEY is not set in .env")

    payload: dict[str, Any] = {
        "text": text,
        "tags": tags or ["devsecops-coral", "cve-remediation"],
        "time": int(time.time() * 1000),
    }
    if GRAFANA_DASHBOARD_UID:
        payload["dashboardUID"] = GRAFANA_DASHBOARD_UID

    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{GRAFANA_URL.rstrip('/')}/api/annotations"
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        raise GrafanaError(f"Grafana request failed: {exc}") from exc

    if response.status_code >= 400:
        raise GrafanaError(f"Grafana API error ({response.status_code}): {response.text[:200]}")

    data = response.json()
    annotation_id = data.get("id", "unknown")
    return {
        "id": annotation_id,
        "url": f"{GRAFANA_URL.rstrip('/')}/api/annotations/{annotation_id}",
        "message": "Annotation created successfully",
    }
