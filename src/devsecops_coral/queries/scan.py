"""SQL query templates for security posture scans."""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import validate_ecosystem, validate_package_name
from devsecops_coral.coral_client import CoralError, execute_query

SCAN_QUERY = """
SELECT
    '{package}' AS package,
    osv.id AS cve,
    osv.summary,
    COALESCE(osv.severity, 'UNKNOWN') AS severity,
    osv.published,
    j.key AS jira_ticket,
    j.status AS jira_status,
    j.priority AS jira_priority
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LEFT JOIN jira.issues j
    ON j.labels LIKE '%security%'
    AND (
        j.summary LIKE CONCAT('%', osv.id, '%')
        OR j.summary LIKE CONCAT('%', '{package}', '%')
        OR j.description LIKE CONCAT('%', osv.id, '%')
    )
ORDER BY osv.published DESC
LIMIT 20
"""


def build_scan_query(*, ecosystem: str, package: str) -> str:
    """Build a parameterized scan query for one package."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return SCAN_QUERY.format(ecosystem=eco, package=pkg)


def run_scan(*, ecosystem: str, packages: list[str]) -> list[dict[str, Any]]:
    """Run security posture scan across packages and merge results."""
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    for package in packages:
        query = build_scan_query(ecosystem=ecosystem, package=package)
        try:
            result = execute_query(query)
        except CoralError as exc:
            errors.append(f"{package}: {exc}")
            continue
        if result:
            rows.extend(result)
        else:
            rows.append(
                {
                    "package": package,
                    "cve": None,
                    "summary": None,
                    "severity": None,
                    "jira_ticket": None,
                    "jira_status": None,
                }
            )

    if errors and not rows:
        raise CoralError("; ".join(errors))
    return rows
