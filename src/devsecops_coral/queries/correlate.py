"""SQL query templates for vulnerability-error correlation."""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import validate_ecosystem, validate_package_name
from devsecops_coral.coral_client import CoralError, execute_query, parse_since

CORRELATE_QUERY = """
SELECT
    osv.id AS cve,
    '{package}' AS package,
    COALESCE(osv.severity, 'UNKNOWN') AS severity,
    osv.summary,
    se.title AS error_title,
    se.level AS error_level,
    se.count AS error_count,
    se.first_seen,
    se.last_seen
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LEFT JOIN sentry.issues se
    ON se.level IN ('fatal', 'error')
    AND se.last_seen >= NOW() - {interval}
ORDER BY se.count DESC NULLS LAST
LIMIT 50
"""


def build_correlate_query(*, ecosystem: str, package: str, since: str) -> str:
    """Build a correlation query for one package."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    interval = parse_since(since)
    return CORRELATE_QUERY.format(ecosystem=eco, package=pkg, interval=interval)


def classify_signal(row: dict[str, Any]) -> str:
    """Classify exploitation signal from error count and severity."""
    count = row.get("error_count") or 0
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 0
    severity = str(row.get("severity") or "").upper()

    if count >= 10 and severity in ("CRITICAL", "HIGH"):
        return "active"
    if count >= 1:
        return "monitor"
    return "clean"


def run_correlate(
    *,
    ecosystem: str,
    packages: list[str],
    since: str = "7d",
) -> list[dict[str, Any]]:
    """Correlate OSV vulnerabilities with Sentry errors."""
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for package in packages:
        query = build_correlate_query(ecosystem=ecosystem, package=package, since=since)
        try:
            result = execute_query(query)
        except CoralError as exc:
            errors.append(f"{package}: {exc}")
            continue
        for row in result:
            row["signal"] = classify_signal(row)
            rows.append(row)

    if errors and not rows:
        raise CoralError("; ".join(errors))
    return rows
