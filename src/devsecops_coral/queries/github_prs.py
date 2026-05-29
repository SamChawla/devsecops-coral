"""SQL query templates for security-related GitHub pull requests.

Reads merged/open PRs from Coral's ``github.pulls`` table and keeps only the
security-relevant ones (dependency upgrades, patches, CVE fixes) so the
dashboard can show what remediation work is actually moving through code review.
"""

from __future__ import annotations

from devsecops_coral.config import (
    GITHUB_OWNER,
    GITHUB_REPO,
    validate_github_owner,
    validate_github_repo,
)
from devsecops_coral.coral_client import (
    CoralError,
    execute_query,
    is_source_unavailable,
    parse_since,
)
from devsecops_coral.models import QueryResult

# Title keywords that mark a PR as security-relevant.
_SECURITY_TITLE_FILTER = """(
        g.title LIKE '%security%'
        OR g.title LIKE '%vuln%'
        OR g.title LIKE '%CVE%'
        OR g.title LIKE '%GHSA%'
        OR g.title LIKE '%upgrade%'
        OR g.title LIKE '%patch%'
        OR g.title LIKE '%bump%'
        OR g.title LIKE '%dependab%'
        OR g.title LIKE '%fix%'
    )"""

GITHUB_PRS_QUERY = """
SELECT
    g.number AS number,
    g.title AS title,
    g.state AS state,
    g.user__login AS author,
    g.merged_at AS merged_at,
    CONCAT('https://github.com/{owner}/{repo}/pull/', CAST(g.number AS VARCHAR)) AS url
FROM github.pulls g
WHERE g.owner = '{owner}'
    AND g.repo = '{repo}'
    AND g.created_at >= NOW() - {interval}
    AND {security_filter}{state_filter}
ORDER BY g.merged_at DESC NULLS LAST, g.number DESC
LIMIT 50
"""


def build_github_prs_query(
    *,
    owner: str,
    repo: str,
    since: str = "90d",
    state: str | None = None,
) -> str:
    """Build a query for security-related PRs in a repository.

    Args:
        owner: GitHub owner/org (validated for SQL interpolation).
        repo: Repository name (validated for SQL interpolation).
        since: Time window on ``created_at`` (e.g. ``90d``).
        state: Optional state filter (``open`` or ``merged``); ``None`` = any.

    Returns:
        A single Coral SQL SELECT statement.
    """
    gh_owner = validate_github_owner(owner)
    gh_repo = validate_github_repo(repo)
    interval = parse_since(since)

    state_filter = ""
    if state in ("open", "merged", "closed"):
        state_filter = f"\n    AND g.state = '{state}'"

    return GITHUB_PRS_QUERY.format(
        owner=gh_owner,
        repo=gh_repo,
        interval=interval,
        security_filter=_SECURITY_TITLE_FILTER,
        state_filter=state_filter,
    )


def run_github_prs(
    *,
    owner: str | None = None,
    repo: str | None = None,
    since: str = "90d",
    state: str | None = None,
) -> QueryResult:
    """Return security-related GitHub PRs, degrading gracefully when unavailable.

    If GitHub is not configured or the source is unreachable, an empty result is
    returned (never a hard error) so the dashboard panel can render an empty state.

    Args:
        owner: GitHub owner/org (defaults to ``GITHUB_OWNER``).
        repo: Repository name (defaults to ``GITHUB_REPO``).
        since: Time window on ``created_at`` (e.g. ``90d``).
        state: Optional state filter (``open``/``merged``).

    Returns:
        :class:`~devsecops_coral.models.QueryResult` with PR rows and the SQL used.
    """
    resolved_owner = (owner or GITHUB_OWNER or "").strip()
    resolved_repo = (repo or GITHUB_REPO or "").strip()
    if not resolved_owner or not resolved_repo:
        return QueryResult(data=[], sql="-- GitHub owner/repo not configured")

    try:
        query = build_github_prs_query(
            owner=resolved_owner, repo=resolved_repo, since=since, state=state
        )
    except ValueError:
        return QueryResult(data=[], sql="-- invalid GitHub owner/repo")

    try:
        rows = execute_query(query)
    except CoralError as exc:
        if is_source_unavailable(exc):
            return QueryResult(data=[], sql=query)
        raise
    return QueryResult(data=rows, sql=query)
