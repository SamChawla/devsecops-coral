"""SQL query templates for vulnerability root-cause investigation.

Root cause stitches together three signals for a single CVE/package:
the OSV vulnerability (the *what*), recent Sentry errors mentioning the
package (the *symptom*), and recently merged GitHub PRs that look related
(the likely *cause* or *fix*). The agent then narrates the probable chain.
"""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import (
    GITHUB_OWNER,
    GITHUB_REPO,
    validate_ecosystem,
    validate_github_owner,
    validate_github_repo,
    validate_package_name,
    validate_vuln_id,
)
from devsecops_coral.coral_client import (
    CoralError,
    execute_query,
    is_source_unavailable,
    parse_since,
)
from devsecops_coral.models import QueryResult

# Full query — OSV vulnerability + correlated Sentry errors + related GitHub PRs.
ROOT_CAUSE_QUERY_WITH_GITHUB = """
SELECT
    osv.id AS cve,
    '{package}' AS package,
    CASE osv.severity WHEN 'MODERATE' THEN 'MEDIUM'
        ELSE COALESCE(osv.severity, 'UNKNOWN') END AS severity,
    osv.summary AS vuln_summary,
    se.title AS error_title,
    se.level AS error_level,
    se.count AS error_count,
    se.first_seen AS error_first_seen,
    se.last_seen AS error_last_seen,
    g.number AS pr_number,
    g.title AS pr_title,
    g.user__login AS pr_author,
    g.merged_at AS pr_merged_at
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LEFT JOIN sentry.issues se
    ON se.level IN ('fatal', 'error')
    AND CAST(se.last_seen AS TIMESTAMP) >= NOW() - {interval}
    AND se.title LIKE CONCAT('%', '{package}', '%')
LEFT JOIN github.pulls g
    ON g.owner = '{owner}'
    AND g.repo = '{repo}'
    AND g.state = 'merged'
    AND g.merged_at >= NOW() - {interval}
    AND (
        g.title LIKE CONCAT('%', '{package}', '%')
        OR g.title LIKE '%upgrade%'
        OR g.title LIKE '%patch%'
        OR g.title LIKE '%bump%'
        OR g.title LIKE '%fix%'
    )
{id_filter}
ORDER BY g.merged_at DESC NULLS LAST, se.count DESC NULLS LAST
LIMIT 25
"""

# No GitHub source — OSV vulnerability + correlated Sentry errors only.
ROOT_CAUSE_QUERY_NO_GITHUB = """
SELECT
    osv.id AS cve,
    '{package}' AS package,
    CASE osv.severity WHEN 'MODERATE' THEN 'MEDIUM'
        ELSE COALESCE(osv.severity, 'UNKNOWN') END AS severity,
    osv.summary AS vuln_summary,
    se.title AS error_title,
    se.level AS error_level,
    se.count AS error_count,
    se.first_seen AS error_first_seen,
    se.last_seen AS error_last_seen,
    CAST(NULL AS BIGINT) AS pr_number,
    CAST(NULL AS VARCHAR) AS pr_title,
    CAST(NULL AS VARCHAR) AS pr_author,
    CAST(NULL AS TIMESTAMP) AS pr_merged_at
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
LEFT JOIN sentry.issues se
    ON se.level IN ('fatal', 'error')
    AND CAST(se.last_seen AS TIMESTAMP) >= NOW() - {interval}
    AND se.title LIKE CONCAT('%', '{package}', '%')
{id_filter}
ORDER BY se.count DESC NULLS LAST
LIMIT 25
"""

# OSV only — when neither Sentry nor GitHub is available.
ROOT_CAUSE_QUERY_OSV_ONLY = """
SELECT
    osv.id AS cve,
    '{package}' AS package,
    CASE osv.severity WHEN 'MODERATE' THEN 'MEDIUM'
        ELSE COALESCE(osv.severity, 'UNKNOWN') END AS severity,
    osv.summary AS vuln_summary,
    CAST(NULL AS VARCHAR) AS error_title,
    CAST(NULL AS VARCHAR) AS error_level,
    CAST(0 AS BIGINT) AS error_count,
    CAST(NULL AS TIMESTAMP) AS error_first_seen,
    CAST(NULL AS TIMESTAMP) AS error_last_seen,
    CAST(NULL AS BIGINT) AS pr_number,
    CAST(NULL AS VARCHAR) AS pr_title,
    CAST(NULL AS VARCHAR) AS pr_author,
    CAST(NULL AS TIMESTAMP) AS pr_merged_at
FROM osv.search_vulnerabilities(
    package => '{package}',
    ecosystem => '{ecosystem}'
) osv
{id_filter}
LIMIT 25
"""


def _id_filter(cve: str | None) -> str:
    """Return an optional ``WHERE osv.id = '...'`` clause for a specific CVE."""
    if not cve:
        return ""
    return f"WHERE osv.id = '{validate_vuln_id(cve)}'"


def build_root_cause_query(
    *,
    ecosystem: str,
    package: str,
    since: str,
    cve: str | None = None,
    owner: str | None = None,
    repo: str | None = None,
) -> str:
    """Build a root-cause query joining OSV, Sentry, and (optionally) GitHub PRs."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    interval = parse_since(since)
    id_filter = _id_filter(cve)

    if owner and repo:
        gh_owner = validate_github_owner(owner)
        gh_repo = validate_github_repo(repo)
        return ROOT_CAUSE_QUERY_WITH_GITHUB.format(
            ecosystem=eco,
            package=pkg,
            interval=interval,
            owner=gh_owner,
            repo=gh_repo,
            id_filter=id_filter,
        )
    return ROOT_CAUSE_QUERY_NO_GITHUB.format(
        ecosystem=eco, package=pkg, interval=interval, id_filter=id_filter
    )


def build_root_cause_query_osv_only(
    *, ecosystem: str, package: str, cve: str | None = None
) -> str:
    """Fallback root-cause query using OSV only (no Sentry or GitHub)."""
    eco = validate_ecosystem(ecosystem)
    pkg = validate_package_name(package)
    return ROOT_CAUSE_QUERY_OSV_ONLY.format(
        ecosystem=eco, package=pkg, id_filter=_id_filter(cve)
    )


def run_root_cause(
    *,
    ecosystem: str,
    package: str,
    cve: str | None = None,
    since: str = "30d",
    owner: str | None = None,
    repo: str | None = None,
) -> QueryResult:
    """Gather the OSV vuln, correlated Sentry errors, and related GitHub PRs.

    Degrades gracefully: if GitHub or Sentry is unavailable the offending leg is
    dropped and the query retried, falling back to OSV-only as a last resort.

    Args:
        ecosystem: Package ecosystem (e.g. ``PyPI``).
        package: Affected package name.
        cve: Optional CVE/GHSA id to scope the vulnerability lookup.
        since: Time window for Sentry/GitHub correlation (e.g. ``30d``).
        owner: GitHub owner/org (defaults to ``GITHUB_OWNER``).
        repo: GitHub repository (defaults to ``GITHUB_REPO``).

    Returns:
        :class:`~devsecops_coral.models.QueryResult` with root-cause rows and SQL.
    """
    resolved_owner: str | None = owner or GITHUB_OWNER or None
    resolved_repo: str | None = repo or GITHUB_REPO or None

    attempts: list[str] = [
        build_root_cause_query(
            ecosystem=ecosystem,
            package=package,
            since=since,
            cve=cve,
            owner=resolved_owner,
            repo=resolved_repo,
        )
    ]
    # If GitHub was in the first attempt, the next fallback drops it.
    if resolved_owner and resolved_repo:
        attempts.append(
            build_root_cause_query(
                ecosystem=ecosystem, package=package, since=since, cve=cve
            )
        )
    attempts.append(
        build_root_cause_query_osv_only(ecosystem=ecosystem, package=package, cve=cve)
    )

    last_error: CoralError | None = None
    for query in attempts:
        try:
            rows = execute_query(query)
        except CoralError as exc:
            last_error = exc
            if is_source_unavailable(exc):
                continue
            raise
        return QueryResult(data=rows, sql=query)

    if last_error is not None:
        raise last_error
    return QueryResult(data=[], sql=attempts[-1])


def summarize_signals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Condense root-cause rows into headline counts for quick display."""
    errors = [r for r in rows if r.get("error_title")]
    prs = [r for r in rows if r.get("pr_title")]
    total_error_count = 0
    for r in errors:
        try:
            total_error_count += int(r.get("error_count") or 0)
        except (TypeError, ValueError):
            pass
    return {
        "error_signals": len(errors),
        "total_error_count": total_error_count,
        "related_prs": len({(r.get("pr_number"), r.get("pr_title")) for r in prs}),
    }
