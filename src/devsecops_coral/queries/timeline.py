"""SQL query templates for unified security event timelines."""

from __future__ import annotations

from typing import Any

from devsecops_coral.config import resolve_github_scope
from devsecops_coral.coral_client import execute_query, parse_since

TIMELINE_QUERY = """
SELECT event_time, source, event_type, title, detail, severity
FROM (
    SELECT
        g.merged_at AS event_time,
        'github' AS source,
        'pr_merged' AS event_type,
        g.title AS title,
        g.user_login AS detail,
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
        j.priority AS severity
    FROM jira.issues j
    WHERE j.labels LIKE '%security%'
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


def build_timeline_query(*, since: str, owner: str, repo: str) -> str:
    """Build the unified timeline query."""
    interval = parse_since(since)
    return TIMELINE_QUERY.format(interval=interval, owner=owner, repo=repo)


def run_timeline(
    *,
    since: str = "24h",
    owner: str | None = None,
    repo: str | None = None,
) -> list[dict[str, Any]]:
    """Build a chronological security event timeline."""
    gh_owner, gh_repo = resolve_github_scope(owner=owner, repo=repo)
    query = build_timeline_query(since=since, owner=gh_owner, repo=gh_repo)
    return execute_query(query)
