"""Rule-based recommendation engine for CVE remediation actions.

Analyzes scan and correlate results and produces a prioritised list of
:class:`~devsecops_coral.models.RecommendedAction` objects ready for human
approval in Phase 3.
"""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import parse_packages
from devsecops_coral.models import ActionStatus, ActionType, RecommendedAction, RecommendResponse
from devsecops_coral.queries.correlate import run_correlate
from devsecops_coral.queries.scan import run_scan

_DEFAULT_PACKAGES = "django,flask,requests,celery,pillow"
_DEFAULT_ECOSYSTEM = "PyPI"
_DEFAULT_SINCE = "7d"

_HIGH_SEVERITY = {"CRITICAL", "HIGH"}
_TYPE_LABELS: dict[ActionType, str] = {
    ActionType.CREATE_JIRA: "JIRA",
    ActionType.CREATE_PR: "GITHUB PR",
    ActionType.CREATE_GITHUB_ISSUE: "GITHUB",
    ActionType.ANNOTATE_GRAFANA: "GRAFANA",
    ActionType.GENERATE_REPORT: "REPORT",
}


def _worst_signal(signals: list[str]) -> str:
    """Return the most severe signal from a list (active > monitor > clean)."""
    if "active" in signals:
        return "active"
    if "monitor" in signals:
        return "monitor"
    return "clean"


def _package_signal_map(correlate_data: list[dict[str, Any]]) -> dict[str, str]:
    """Build a package-to-worst-signal mapping from correlate rows.

    Args:
        correlate_data: Rows from :func:`~devsecops_coral.queries.correlate.run_correlate`.

    Returns:
        Dict mapping package name to its worst signal (``active``, ``monitor``, or ``clean``).
    """
    by_pkg: dict[str, list[str]] = {}
    for row in correlate_data:
        pkg = str(row.get("package") or "").strip()
        sig = str(row.get("signal") or "clean")
        by_pkg.setdefault(pkg, []).append(sig)
    return {pkg: _worst_signal(sigs) for pkg, sigs in by_pkg.items()}


def build_recommendations(
    scan_data: list[dict[str, Any]],
    correlate_data: list[dict[str, Any]],
) -> list[RecommendedAction]:
    """Apply rule-based logic to detection data and return ordered action list.

    Rules applied in order:
    - Each untracked HIGH/CRITICAL CVE → ``create_jira`` (urgent when actively exploited)
    - First actively-exploited untracked package → ``create_pr``
    - Any untracked CVEs exist → ``annotate_grafana``
    - Always → ``generate_report``

    Args:
        scan_data: Rows from :func:`~devsecops_coral.queries.scan.run_scan`.
        correlate_data: Rows from :func:`~devsecops_coral.queries.correlate.run_correlate`.

    Returns:
        Ordered list of :class:`~devsecops_coral.models.RecommendedAction` objects,
        all with status ``PENDING``.
    """
    signal_map = _package_signal_map(correlate_data)

    untracked = [
        row
        for row in scan_data
        if row.get("cve")
        and not row.get("jira_ticket")
        and str(row.get("severity") or "").upper() in _HIGH_SEVERITY
    ]

    actions: list[RecommendedAction] = []
    next_id = 1
    pr_packages: set[str] = set()

    for row in untracked:
        pkg = str(row.get("package") or "")
        cve = str(row.get("cve") or "")
        severity = str(row.get("severity") or "HIGH").upper()
        signal = signal_map.get(pkg, "clean")
        urgent = signal == "active"

        error_note = " with active Sentry error spike" if urgent else ""
        actions.append(
            RecommendedAction(
                id=next_id,
                type=ActionType.CREATE_JIRA,
                status=ActionStatus.PENDING,
                title=f"Create Jira ticket for {cve} ({pkg})",
                detail=(
                    f"{severity} severity CVE{error_note}. "
                    "No tracking ticket exists — remediation untracked."
                ),
                cve=cve,
                package=pkg,
                severity=severity,
                urgent=urgent,
            )
        )
        next_id += 1

        if signal in ("active", "monitor") and pkg not in pr_packages:
            actions.append(
                RecommendedAction(
                    id=next_id,
                    type=ActionType.CREATE_PR,
                    status=ActionStatus.PENDING,
                    title=f"Draft GitHub PR to upgrade {pkg}",
                    detail=(
                        f"Upgrade {pkg} to the latest patched version "
                        f"to remediate {cve}. Check OSV for fixed version."
                    ),
                    cve=cve,
                    package=pkg,
                    severity=severity,
                    urgent=urgent,
                )
            )
            pr_packages.add(pkg)
            next_id += 1

    if untracked:
        actions.append(
            RecommendedAction(
                id=next_id,
                type=ActionType.ANNOTATE_GRAFANA,
                status=ActionStatus.PENDING,
                title="Annotate Grafana timeline — CVE remediation initiated",
                detail=(
                    f"Mark start of remediation workflow for "
                    f"{len(untracked)} untracked CVE(s) on the infrastructure timeline."
                ),
                severity="INFO",
            )
        )
        next_id += 1

    actions.append(
        RecommendedAction(
            id=next_id,
            type=ActionType.GENERATE_REPORT,
            status=ActionStatus.PENDING,
            title="Generate security posture report",
            detail=(
                "Export a Markdown summary of current vulnerability status, "
                "signal classifications, and recommended next steps for team review."
            ),
            severity="INFO",
        )
    )

    return actions


def run_recommend(
    *,
    ecosystem: str = _DEFAULT_ECOSYSTEM,
    packages: str | list[str] | None = None,
    since: str = _DEFAULT_SINCE,
) -> RecommendResponse:
    """Run scan + correlate and produce a RecommendResponse with ordered actions.

    Args:
        ecosystem: Package ecosystem (e.g. ``PyPI``).
        packages: Comma-separated string or list of package names.
            Defaults to the standard demo package set.
        since: Time window for Sentry correlation (e.g. ``7d``, ``24h``).

    Returns:
        :class:`~devsecops_coral.models.RecommendResponse` with all actions
        at ``PENDING`` status.
    """
    if packages is None:
        pkg_list = parse_packages(_DEFAULT_PACKAGES)
    elif isinstance(packages, str):
        pkg_list = parse_packages(packages)
    else:
        pkg_list = list(packages)

    scan_result = run_scan(ecosystem=ecosystem, packages=pkg_list)
    correlate_result = run_correlate(ecosystem=ecosystem, packages=pkg_list, since=since)
    actions = build_recommendations(scan_result.data, correlate_result.data)

    return RecommendResponse(actions=actions, ecosystem=ecosystem, packages=pkg_list)
