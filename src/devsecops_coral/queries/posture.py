"""Security posture aggregation from scan results."""

from __future__ import annotations

from devsecops_coral.config import parse_packages
from devsecops_coral.models import PostureResponse, QueryResult
from devsecops_coral.queries.scan import run_scan

DEFAULT_PACKAGES = "django,flask,requests,celery"
DEFAULT_ECOSYSTEM = "PyPI"

_SEVERITY_KEYS = ("critical", "high", "medium", "low")


def _count_severities(rows: list[dict]) -> dict[str, int]:
    """Count rows by severity level."""
    counts = {key: 0 for key in _SEVERITY_KEYS}
    for row in rows:
        if not row.get("cve"):
            continue
        severity = str(row.get("severity") or "").upper()
        key = severity.lower() if severity.lower() in _SEVERITY_KEYS else None
        if key:
            counts[key] += 1
    return counts


def _count_untracked(rows: list[dict]) -> int:
    """Count CVEs without a Jira tracking ticket."""
    return sum(1 for row in rows if row.get("cve") and not row.get("jira_ticket"))


def run_posture(
    *,
    ecosystem: str = DEFAULT_ECOSYSTEM,
    packages: str | list[str] | None = None,
) -> PostureResponse:
    """Aggregate severity counts and untracked CVEs from a scan."""
    if packages is None:
        pkg_list = parse_packages(DEFAULT_PACKAGES)
    elif isinstance(packages, str):
        pkg_list = parse_packages(packages)
    else:
        pkg_list = packages

    result: QueryResult = run_scan(ecosystem=ecosystem, packages=pkg_list)
    counts = _count_severities(result.data)
    untracked = _count_untracked(result.data)
    total = sum(counts.values())

    return PostureResponse(
        critical=counts["critical"],
        high=counts["high"],
        medium=counts["medium"],
        low=counts["low"],
        untracked=untracked,
        total=total,
        sql=result.sql,
        ecosystem=ecosystem,
        packages=pkg_list,
    )
