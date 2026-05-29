"""SQL query templates for unified security event timelines."""

from __future__ import annotations

from devsecops_coral.config import (
    GITHUB_OWNER,
    GITHUB_REPO,
    JIRA_SECURITY_JQL,
    resolve_github_scope,
)
from devsecops_coral.coral_client import (
    CoralError,
    execute_query,
    identify_failed_source,
    is_source_unavailable,
    parse_since,
)
from devsecops_coral.models import QueryResult

_SCHEMA_NAMES = ("github", "sentry", "jira", "grafana")


def _missing_schema(exc: CoralError) -> str | None:
    """Return the source name a timeline leg failed on, if it can be identified.

    Matches unregistered sources, column/required-filter errors, and upstream
    connectivity/timeout failures so the offending UNION leg can be dropped and
    the query retried instead of failing the whole timeline.
    """
    if not is_source_unavailable(exc):
        return None
    return identify_failed_source(exc, _SCHEMA_NAMES)


TIMELINE_QUERY_WITH_GITHUB = """
SELECT event_time, source, event_type, title, detail, severity
FROM (
    SELECT
        g.merged_at AS event_time,
        'github' AS source,
        'pr_merged' AS event_type,
        g.title AS title,
        g.user__login AS detail,
        CAST(NULL AS VARCHAR) AS severity
    FROM github.pulls g
    WHERE g.owner = '{owner}'
        AND g.repo = '{repo}'
        AND g.state = 'merged'
        AND g.merged_at >= NOW() - {interval}

    UNION ALL

    SELECT
        se.first_seen AS event_time,
        'sentry' AS source,
        'error' AS event_type,
        se.title AS title,
        se.level AS detail,
        se.level AS severity
    FROM sentry.issues se
    WHERE se.level IN ('fatal', 'error')
        AND se.first_seen >= NOW() - {interval}

    UNION ALL

    SELECT
        j.created AS event_time,
        'jira' AS source,
        'ticket' AS event_type,
        j.summary AS title,
        j.key AS detail,
        j.priority_name AS severity
    FROM jira.issues j
    WHERE j.jql = '{jql}'
        AND j.created >= NOW() - {interval}

    UNION ALL

    SELECT
        ga.time AS event_time,
        'grafana' AS source,
        'annotation' AS event_type,
        ga.text AS title,
        ga.tags AS detail,
        CAST(NULL AS VARCHAR) AS severity
    FROM grafana.annotations ga
    WHERE ga.time >= NOW() - {interval}
) timeline
ORDER BY event_time DESC
LIMIT 100
"""

TIMELINE_QUERY_NO_GITHUB = """
SELECT event_time, source, event_type, title, detail, severity
FROM (
    SELECT
        se.first_seen AS event_time,
        'sentry' AS source,
        'error' AS event_type,
        se.title AS title,
        se.level AS detail,
        se.level AS severity
    FROM sentry.issues se
    WHERE se.level IN ('fatal', 'error')
        AND se.first_seen >= NOW() - {interval}

    UNION ALL

    SELECT
        j.created AS event_time,
        'jira' AS source,
        'ticket' AS event_type,
        j.summary AS title,
        j.key AS detail,
        j.priority_name AS severity
    FROM jira.issues j
    WHERE j.jql = '{jql}'
        AND j.created >= NOW() - {interval}

    UNION ALL

    SELECT
        ga.time AS event_time,
        'grafana' AS source,
        'annotation' AS event_type,
        ga.text AS title,
        ga.tags AS detail,
        CAST(NULL AS VARCHAR) AS severity
    FROM grafana.annotations ga
    WHERE ga.time >= NOW() - {interval}
) timeline
ORDER BY event_time DESC
LIMIT 100
"""


_GITHUB_LEG = """
    SELECT
        g.merged_at AS event_time,
        'github' AS source,
        'pr_merged' AS event_type,
        g.title AS title,
        g.user__login AS detail,
        CAST(NULL AS VARCHAR) AS severity
    FROM github.pulls g
    WHERE g.owner = '{owner}'
        AND g.repo = '{repo}'
        AND g.state = 'merged'
        AND g.merged_at >= NOW() - {interval}"""

_SENTRY_LEG = """
    SELECT
        se.first_seen AS event_time,
        'sentry' AS source,
        'error' AS event_type,
        se.title AS title,
        se.level AS detail,
        se.level AS severity
    FROM sentry.issues se
    WHERE se.level IN ('fatal', 'error')
        AND se.first_seen >= NOW() - {interval}"""

_JIRA_LEG = """
    SELECT
        j.created AS event_time,
        'jira' AS source,
        'ticket' AS event_type,
        j.summary AS title,
        j.key AS detail,
        j.priority_name AS severity
    FROM jira.issues j
    WHERE j.jql = '{jql}'
        AND j.created >= NOW() - {interval}"""

_GRAFANA_LEG = """
    SELECT
        ga.time AS event_time,
        'grafana' AS source,
        'annotation' AS event_type,
        ga.text AS title,
        ga.tags AS detail,
        CAST(NULL AS VARCHAR) AS severity
    FROM grafana.annotations ga
    WHERE ga.time >= NOW() - {interval}"""

_WRAPPER = """SELECT event_time, source, event_type, title, detail, severity
FROM ({legs}
) timeline
ORDER BY event_time DESC
LIMIT 100
"""


def _build_timeline_query_flexible(
    *,
    since: str,
    owner: str | None,
    repo: str | None,
    skip: set[str],
) -> str | None:
    """Build a timeline UNION query omitting any schemas in ``skip``."""
    interval = parse_since(since)
    legs = []

    if "github" not in skip and owner and repo:
        legs.append(_GITHUB_LEG.format(interval=interval, owner=owner, repo=repo))
    if "sentry" not in skip:
        legs.append(_SENTRY_LEG.format(interval=interval))
    if "jira" not in skip:
        legs.append(_JIRA_LEG.format(interval=interval, jql=JIRA_SECURITY_JQL))
    if "grafana" not in skip:
        legs.append(_GRAFANA_LEG.format(interval=interval))

    if not legs:
        return None
    return _WRAPPER.format(legs="\n\n    UNION ALL".join(legs))


def build_timeline_query(*, since: str, owner: str | None, repo: str | None) -> str:
    """Build the unified timeline query, omitting GitHub leg if owner is unset."""
    interval = parse_since(since)
    if owner and repo:
        return TIMELINE_QUERY_WITH_GITHUB.format(
            interval=interval, owner=owner, repo=repo, jql=JIRA_SECURITY_JQL
        )
    return TIMELINE_QUERY_NO_GITHUB.format(interval=interval, jql=JIRA_SECURITY_JQL)


def run_timeline(
    *,
    since: str = "24h",
    owner: str | None = None,
    repo: str | None = None,
) -> QueryResult:
    """Build a chronological security event timeline.

    GitHub leg is included only when GITHUB_OWNER is configured. If any source
    schema is not registered, it is stripped from the UNION and the query retried,
    so the endpoint never returns 502 just because some sources are unconfigured.
    """
    resolved_owner: str | None = owner or GITHUB_OWNER or None
    resolved_repo: str | None = repo or GITHUB_REPO or None

    if resolved_owner:
        try:
            gh_owner, gh_repo = resolve_github_scope(owner=resolved_owner, repo=resolved_repo)
        except ValueError:
            gh_owner, gh_repo = None, None
    else:
        gh_owner, gh_repo = None, None

    skip: set[str] = set()
    for _ in range(len(_SCHEMA_NAMES) + 1):
        query = _build_timeline_query_flexible(since=since, owner=gh_owner, repo=gh_repo, skip=skip)
        if query is None:
            return QueryResult(data=[], sql="-- no configured timeline sources")
        try:
            rows = execute_query(query)
            return QueryResult(data=rows, sql=query)
        except CoralError as exc:
            if not is_source_unavailable(exc):
                raise
            missing = identify_failed_source(exc, _SCHEMA_NAMES)
            if missing is None or missing in skip:
                # Connectivity/timeout error we can't attribute: drop the first
                # still-active leg so the next attempt makes progress.
                active = [
                    name
                    for name in _SCHEMA_NAMES
                    if name not in skip and (name != "github" or (gh_owner and gh_repo))
                ]
                if not active:
                    raise
                missing = active[0]
            skip.add(missing)
            if missing == "github":
                gh_owner, gh_repo = None, None

    return QueryResult(data=[], sql="-- no configured timeline sources")
