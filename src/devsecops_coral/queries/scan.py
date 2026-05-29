"""SQL query templates for security posture scans."""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import JIRA_SECURITY_JQL, validate_ecosystem, validate_package_name
from devsecops_coral.coral_client import CoralError, execute_query
from devsecops_coral.models import QueryResult

# Coral's bundled Jira source exposes ``status_name``/``priority_name`` (not
# ``status``/``priority``), has no ``labels``/``description`` columns, and
# requires a constant ``jql`` equality filter. Pushing a bounded JQL into the
# JOIN ``ON`` clause satisfies that filter while leaving CVE/package text
# matching to the ``summary`` column.
SCAN_QUERY = """
SELECT
    '{package}' AS package,
    osv.id AS cve,
    osv.summary,
    CASE osv.severity WHEN 'MODERATE' THEN 'MEDIUM'
        ELSE COALESCE(osv.severity, 'UNKNOWN') END AS severity,
    osv.published,
    j.key AS jira_ticket,
    j.status_name AS jira_status,
    j.priority_name AS jira_priority,
    CASE WHEN j.key IS NULL THEN 'UNTRACKED'
         ELSE COALESCE(j.status_name, 'Tracked') END AS tracking_status,
    COALESCE(se.count, 0) AS error_count,
    se.level AS error_level
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LEFT JOIN jira.issues j
    ON j.jql = '{jira_jql}'
    AND (
        j.summary LIKE CONCAT('%', osv.id, '%')
        OR j.summary LIKE CONCAT('%', '{package}', '%')
    )
LEFT JOIN sentry.issues se
    ON se.level IN ('fatal', 'error')
    AND se.last_seen >= NOW() - INTERVAL '30' DAY
    AND (
        se.title LIKE CONCAT('%', '{package}', '%')
        OR se.culprit LIKE CONCAT('%', '{package}', '%')
    )
ORDER BY osv.published DESC
LIMIT 5
"""

SCAN_QUERY_NO_SENTRY = """
SELECT
    '{package}' AS package,
    osv.id AS cve,
    osv.summary,
    CASE osv.severity WHEN 'MODERATE' THEN 'MEDIUM'
        ELSE COALESCE(osv.severity, 'UNKNOWN') END AS severity,
    osv.published,
    j.key AS jira_ticket,
    j.status_name AS jira_status,
    j.priority_name AS jira_priority,
    CASE WHEN j.key IS NULL THEN 'UNTRACKED'
         ELSE COALESCE(j.status_name, 'Tracked') END AS tracking_status,
    CAST(0 AS BIGINT) AS error_count,
    CAST(NULL AS VARCHAR) AS error_level
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LEFT JOIN jira.issues j
    ON j.jql = '{jira_jql}'
    AND (
        j.summary LIKE CONCAT('%', osv.id, '%')
        OR j.summary LIKE CONCAT('%', '{package}', '%')
    )
ORDER BY osv.published DESC
LIMIT 5
"""

SCAN_QUERY_OSV_ONLY = """
SELECT
    '{package}' AS package,
    osv.id AS cve,
    osv.summary,
    CASE osv.severity WHEN 'MODERATE' THEN 'MEDIUM'
        ELSE COALESCE(osv.severity, 'UNKNOWN') END AS severity,
    osv.published,
    CAST(NULL AS VARCHAR) AS jira_ticket,
    CAST(NULL AS VARCHAR) AS jira_status,
    CAST(NULL AS VARCHAR) AS jira_priority,
    'UNTRACKED' AS tracking_status,
    CAST(0 AS BIGINT) AS error_count,
    CAST(NULL AS VARCHAR) AS error_level
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
ORDER BY osv.published DESC
LIMIT 5
"""


def build_scan_query(*, ecosystem: str, package: str) -> str:
    """Build a parameterized scan query for one package (OSV + Jira + Sentry)."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return SCAN_QUERY.format(ecosystem=eco, package=pkg, jira_jql=JIRA_SECURITY_JQL)


def build_scan_query_no_sentry(*, ecosystem: str, package: str) -> str:
    """Build a scan query joining OSV and Jira only (used when Sentry is absent)."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return SCAN_QUERY_NO_SENTRY.format(ecosystem=eco, package=pkg, jira_jql=JIRA_SECURITY_JQL)


def build_scan_query_osv_only(*, ecosystem: str, package: str) -> str:
    """Build an OSV-only fallback scan query (no Jira or Sentry JOIN)."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return SCAN_QUERY_OSV_ONLY.format(ecosystem=eco, package=pkg)


def run_scan(*, ecosystem: str, packages: list[str]) -> QueryResult:
    """Run security posture scan across packages and merge results.

    Each package is queried through a cascade of progressively simpler queries
    (OSV + Jira + Sentry → OSV + Jira → OSV only). The first tier that Coral
    accepts is used, so an unconfigured or schema-mismatched source degrades
    gracefully instead of failing the whole scan.
    """
    rows: list[dict[str, Any]] = []
    queries: list[str] = []
    errors: list[str] = []

    for package in packages:
        tiers = [
            build_scan_query(ecosystem=ecosystem, package=package),
            build_scan_query_no_sentry(ecosystem=ecosystem, package=package),
            build_scan_query_osv_only(ecosystem=ecosystem, package=package),
        ]
        result: list[dict[str, Any]] | None = None
        used_query = tiers[0]
        last_exc: CoralError | None = None
        for query in tiers:
            try:
                result = execute_query(query)
                used_query = query
                break
            except CoralError as exc:
                last_exc = exc
                continue

        queries.append(used_query)
        if result is None:
            errors.append(f"{package}: {last_exc}")
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
                    "tracking_status": "Clean",
                }
            )

    if errors and not rows:
        raise CoralError("; ".join(errors))
    return QueryResult(data=rows, sql=";\n\n".join(queries))
