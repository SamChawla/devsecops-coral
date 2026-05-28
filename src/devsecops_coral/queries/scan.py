"""SQL query templates for security posture scans."""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import validate_ecosystem, validate_package_name
from devsecops_coral.coral_client import CoralError, execute_query
from devsecops_coral.models import QueryResult

SCAN_QUERY = """
SELECT
    '{package}' AS package,
    osv.id AS cve,
    osv.summary,
    COALESCE(osv.severity, 'UNKNOWN') AS severity,
    osv.published,
    j.key AS jira_ticket,
    j.status AS jira_status,
    j.priority AS jira_priority,
    COALESCE(se.count, 0) AS error_count,
    se.level AS error_level
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
LEFT JOIN sentry.issues se
    ON se.level IN ('fatal', 'error')
    AND (
        se.title LIKE CONCAT('%', '{package}', '%')
        OR se.culprit LIKE CONCAT('%', '{package}', '%')
    )
ORDER BY osv.published DESC
LIMIT 20
"""

SCAN_QUERY_OSV_ONLY = """
SELECT
    '{package}' AS package,
    osv.id AS cve,
    osv.summary,
    COALESCE(osv.severity, 'UNKNOWN') AS severity,
    osv.published,
    CAST(NULL AS VARCHAR) AS jira_ticket,
    CAST(NULL AS VARCHAR) AS jira_status,
    CAST(NULL AS VARCHAR) AS jira_priority,
    CAST(0 AS BIGINT) AS error_count,
    CAST(NULL AS VARCHAR) AS error_level
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
ORDER BY osv.published DESC
LIMIT 20
"""

_SCHEMA_NOT_REGISTERED = "not currently registered"


def _is_schema_error(exc: CoralError) -> bool:
    """Return True when Coral reports a missing or unregistered source schema."""
    return _SCHEMA_NOT_REGISTERED in str(exc) or "not found" in str(exc).lower()


def build_scan_query(*, ecosystem: str, package: str) -> str:
    """Build a parameterized scan query for one package."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return SCAN_QUERY.format(ecosystem=eco, package=pkg)


def build_scan_query_osv_only(*, ecosystem: str, package: str) -> str:
    """Build an OSV-only fallback scan query (no Jira or Sentry JOIN)."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return SCAN_QUERY_OSV_ONLY.format(ecosystem=eco, package=pkg)


def run_scan(*, ecosystem: str, packages: list[str]) -> QueryResult:
    """Run security posture scan across packages and merge results."""
    rows: list[dict[str, Any]] = []
    queries: list[str] = []
    errors: list[str] = []

    for package in packages:
        query = build_scan_query(ecosystem=ecosystem, package=package)
        queries.append(query)
        try:
            result = execute_query(query)
        except CoralError as exc:
            if _is_schema_error(exc):
                fallback = build_scan_query_osv_only(ecosystem=ecosystem, package=package)
                queries[-1] = fallback
                try:
                    result = execute_query(fallback)
                except CoralError as exc2:
                    errors.append(f"{package}: {exc2}")
                    continue
            else:
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
    return QueryResult(data=rows, sql=";\n\n".join(queries))
