"""LLM agent — natural language to Coral SQL."""

from __future__ import annotations

import json
import re
from typing import Any

from devsecops_coral.coral_client import CoralError, execute_query
from devsecops_coral.llm_client import LLMError, chat_completion

AGENT_SYSTEM_PROMPT = """
You are a security analysis agent that generates Coral SQL queries.

AVAILABLE SCHEMAS (examples):
- osv.search_vulnerabilities(package => 'name', ecosystem => 'PyPI')
  columns: id, summary, severity, published
- osv.vulnerability_detail — requires WHERE id = 'GHSA-...'
- github.pulls — requires WHERE owner = '...' AND repo = '...' (constant values)
  columns: number, title, state, merged_at, user_login
- github.issues — columns: number, title, state, labels, created_at
- sentry.issues — columns: title, level, count, first_seen, last_seen
- jira.issues — columns: key, summary, status, priority, labels, created
- grafana.alert_rules — columns: name, state
- grafana.annotations — columns: time, text, tags

RULES:
- Only generate SELECT queries. Never INSERT, UPDATE, DELETE, or DDL.
- Never include API keys, tokens, or credentials in queries or responses.
- Never reference specific company names, internal project names, or client data.
- Use LEFT JOIN for cross-source queries.
- Use osv.search_vulnerabilities() with named arguments, not WHERE on a vulnerabilities table.
- If query results contain credential-like strings (ghp_, sk-, AKIA), redact as [REDACTED].
- Respond with JSON only: {"sql": "...", "reasoning": "brief explanation"}
- The sql field must be a single valid Coral SQL SELECT statement.
""".strip()

SQL_BLOCK_PATTERN = re.compile(r"```sql\s*(.*?)```", re.DOTALL | re.IGNORECASE)
JSON_PATTERN = re.compile(r"\{[\s\S]*\}")


class AgentError(Exception):
    """Raised when the agent or LLM call fails."""


def _parse_sql_response(content: str) -> tuple[str, str]:
    """Extract SQL and reasoning from LLM response."""
    match = JSON_PATTERN.search(content)
    if match:
        try:
            parsed = json.loads(match.group())
            sql = str(parsed.get("sql", "")).strip()
            reasoning = str(parsed.get("reasoning", parsed.get("analysis", ""))).strip()
            if sql.upper().startswith("SELECT"):
                return sql, reasoning
        except json.JSONDecodeError:
            pass

    block = SQL_BLOCK_PATTERN.search(content)
    if block:
        return block.group(1).strip(), content.strip()

    if content.strip().upper().startswith("SELECT"):
        return content.strip(), ""

    raise AgentError("Model did not return valid SQL. Try rephrasing your question.")


def _validate_sql(sql: str) -> None:
    """Ensure generated SQL is read-only."""
    normalized = sql.strip().upper()
    forbidden = ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "CREATE ", "ALTER ", "TRUNCATE ")
    if not normalized.startswith("SELECT"):
        raise AgentError("Only SELECT queries are allowed.")
    for keyword in forbidden:
        if keyword in normalized:
            raise AgentError(f"Forbidden SQL keyword detected: {keyword.strip()}")


def generate_sql(question: str, *, error_context: str | None = None) -> tuple[str, str]:
    """Translate a natural language question into Coral SQL."""
    user_content = question
    if error_context:
        user_content = (
            f"{question}\n\nPrevious SQL failed with error:\n{error_context}\n"
            "Fix the SQL and return JSON with sql and reasoning."
        )

    try:
        content = chat_completion(
            [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]
        )
    except LLMError as exc:
        raise AgentError(str(exc)) from exc

    sql, reasoning = _parse_sql_response(content)
    _validate_sql(sql)
    return sql, reasoning


def summarize_results(question: str, sql: str, rows: list[dict[str, Any]]) -> str:
    """Generate human-readable analysis from query results."""
    preview = rows[:15]
    payload = json.dumps(preview, default=str)[:8000]
    prompt = (
        f"User question: {question}\n\nSQL executed:\n{sql}\n\n"
        f"Results ({len(rows)} rows, showing up to 15):\n{payload}\n\n"
        "Provide a concise security analysis. Lead with the most critical finding. "
        "Recommend an action if a threat is found. Do not echo raw data unnecessarily."
    )
    try:
        return chat_completion(
            [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
    except LLMError as exc:
        raise AgentError(str(exc)) from exc


def ask(question: str) -> dict[str, Any]:
    """Run the full ask flow: NL → SQL → execute → analyze → recommend.

    Args:
        question: Natural language security question from the user.

    Returns:
        Dict with keys: ``question``, ``sql``, ``reasoning``, ``analysis``,
        ``rows``, ``row_count``, ``recommendations`` (list of dicts, best-effort).
    """
    sql, reasoning = generate_sql(question)

    try:
        rows = execute_query(sql)
    except CoralError as first_error:
        sql, reasoning = generate_sql(question, error_context=str(first_error))
        rows = execute_query(sql)

    analysis = summarize_results(question, sql, rows)

    recommendations: list[dict[str, Any]] = []
    try:
        from devsecops_coral.recommender import run_recommend

        rec_response = run_recommend()
        recommendations = [a.model_dump() for a in rec_response.actions]
    except Exception:
        pass

    return {
        "question": question,
        "sql": sql,
        "reasoning": reasoning,
        "analysis": analysis,
        "rows": rows,
        "row_count": len(rows),
        "recommendations": recommendations,
    }
