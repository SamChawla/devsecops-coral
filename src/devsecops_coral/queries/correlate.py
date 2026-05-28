"""SQL query templates for vulnerability-error correlation."""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import (
    GITHUB_OWNER,
    GITHUB_REPO,
    validate_ecosystem,
    validate_github_owner,
    validate_github_repo,
    validate_package_name,
)
from devsecops_coral.coral_client import CoralError, execute_query, parse_since
from devsecops_coral.models import QueryResult

_SCHEMA_NOT_REGISTERED = "not currently registered"


def _is_schema_error(exc: CoralError) -> bool:
    """Return True when Coral reports a missing or unregistered source schema."""
    return _SCHEMA_NOT_REGISTERED in str(exc) or "not found" in str(exc).lower()


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
    se.last_seen,
    CAST(NULL AS VARCHAR) AS pr_title,
    CAST(NULL AS VARCHAR) AS pr_author
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

CORRELATE_QUERY_OSV_ONLY = """
SELECT
    osv.id AS cve,
    '{package}' AS package,
    COALESCE(osv.severity, 'UNKNOWN') AS severity,
    osv.summary,
    CAST(NULL AS VARCHAR) AS error_title,
    CAST(NULL AS VARCHAR) AS error_level,
    CAST(0 AS BIGINT) AS error_count,
    CAST(NULL AS TIMESTAMP) AS first_seen,
    CAST(NULL AS TIMESTAMP) AS last_seen,
    CAST(NULL AS VARCHAR) AS pr_title,
    CAST(NULL AS VARCHAR) AS pr_author
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LIMIT 50
"""

CORRELATE_QUERY_WITH_GITHUB = """
SELECT
    osv.id AS cve,
    '{package}' AS package,
    COALESCE(osv.severity, 'UNKNOWN') AS severity,
    osv.summary,
    se.title AS error_title,
    se.level AS error_level,
    se.count AS error_count,
    se.first_seen,
    se.last_seen,
    g.title AS pr_title,
    g.user_login AS pr_author
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LEFT JOIN sentry.issues se
    ON se.level IN ('fatal', 'error')
    AND se.last_seen >= NOW() - {interval}
LEFT JOIN github.pulls g
    ON g.owner = '{owner}'
    AND g.repo = '{repo}'
    AND g.state = 'merged'
    AND g.merged_at >= NOW() - {interval}
    AND (
        g.title LIKE CONCAT('%', '{package}', '%')
        OR g.title LIKE '%upgrade%'
        OR g.title LIKE '%patch%'
        OR g.title LIKE '%fix%'
    )
ORDER BY se.count DESC NULLS LAST
LIMIT 50
"""


def build_correlate_query(
    *,
    ecosystem: str,
    package: str,
    since: str,
    owner: str | None = None,
    repo: str | None = None,
) -> str:
    """Build a correlation query for one package, optionally joining GitHub PRs."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    interval = parse_since(since)

    if owner and repo:
        gh_owner = validate_github_owner(owner)
        gh_repo = validate_github_repo(repo)
        return CORRELATE_QUERY_WITH_GITHUB.format(
            ecosystem=eco, package=pkg, interval=interval, owner=gh_owner, repo=gh_repo
        )
    return CORRELATE_QUERY.format(ecosystem=eco, package=pkg, interval=interval)


def build_correlate_query_osv_only(*, ecosystem: str, package: str) -> str:
    """Fallback correlation query using OSV only (no Sentry or GitHub)."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return CORRELATE_QUERY_OSV_ONLY.format(ecosystem=eco, package=pkg)


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
    owner: str | None = None,
    repo: str | None = None,
) -> QueryResult:
    """Correlate OSV vulnerabilities with Sentry errors and optional GitHub PRs."""
    resolved_owner: str | None = owner or GITHUB_OWNER or None
    resolved_repo: str | None = repo or GITHUB_REPO or None

    rows: list[dict[str, Any]] = []
    queries: list[str] = []
    errors: list[str] = []

    for package in packages:
        query = build_correlate_query(
            ecosystem=ecosystem,
            package=package,
            since=since,
            owner=resolved_owner,
            repo=resolved_repo,
        )
        queries.append(query)
        try:
            result = execute_query(query)
        except CoralError as exc:
            if _is_schema_error(exc):
                fallback = build_correlate_query_osv_only(ecosystem=ecosystem, package=package)
                queries[-1] = fallback
                try:
                    result = execute_query(fallback)
                except CoralError as exc2:
                    errors.append(f"{package}: {exc2}")
                    continue
            else:
                errors.append(f"{package}: {exc}")
                continue
        for row in result:
            row["signal"] = classify_signal(row)
            rows.append(row)

    if errors and not rows:
        raise CoralError("; ".join(errors))
    return QueryResult(data=rows, sql=";\n\n".join(queries))
