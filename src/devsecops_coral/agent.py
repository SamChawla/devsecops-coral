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

ANALYSIS_SYSTEM_PROMPT = """
You are a senior security analyst summarizing the results of a Coral SQL query
for a DevSecOps dashboard.

OUTPUT FORMAT:
- Respond in concise GitHub-flavored Markdown prose. NEVER return JSON.
- Do NOT echo the SQL query and do NOT include a "sql" or "reasoning" field.
- Lead with the single most critical finding in one bold sentence.
- Follow with 2-4 short bullet points of supporting detail.
- End with a clear **Recommended action** when a threat is present.
- Keep it under ~150 words. Do not dump raw rows; summarize patterns.

SAFETY:
- Never reference specific company, client, or internal project names.
- Redact any credential-like strings (ghp_, sk-, AKIA, ...) as [REDACTED].
""".strip()

ROOT_CAUSE_SYSTEM_PROMPT = """
You are a senior incident responder performing root-cause analysis for a
DevSecOps dashboard. You are given a single vulnerability, any correlated
runtime errors (Sentry), and any related code changes (merged GitHub PRs).

OUTPUT FORMAT (GitHub-flavored Markdown prose, never JSON):
- Start with a one-sentence **Likely root cause:** in bold.
- Add a short **Evidence** section as bullets, citing the concrete signals you
  were given (error titles/counts, PR titles/authors, severity, timing).
- If merged PRs are present, state whether they look like the FIX or a possible
  CAUSE/regression, and reference them by title (and #number when available).
- End with a **Recommended next step** line.
- If there are no errors and no PRs, say the vulnerability is not yet showing
  runtime impact and recommend preventative tracking. Do NOT invent signals.
- Keep it under ~170 words.

SAFETY:
- Never reference specific company, client, or internal project names.
- Redact credential-like strings (ghp_, sk-, AKIA, ...) as [REDACTED].
""".strip()

SQL_BLOCK_PATTERN = re.compile(r"```sql\s*(.*?)```", re.DOTALL | re.IGNORECASE)
JSON_PATTERN = re.compile(r"\{[\s\S]*\}")

# Clause keywords that start a new line; longer phrases must precede their prefixes.
_SQL_CLAUSE_NEWLINE = re.compile(
    r"\s+(LEFT JOIN|RIGHT JOIN|INNER JOIN|FULL JOIN|CROSS JOIN|JOIN|FROM|WHERE|"
    r"GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET|UNION ALL|UNION)\b",
    re.IGNORECASE,
)
# Boolean / join predicate keywords that start an indented continuation line.
_SQL_PREDICATE_NEWLINE = re.compile(r"\s+(AND|OR|ON)\b", re.IGNORECASE)
# Splits a query into alternating [non-literal, 'string literal', ...] segments.
_SQL_LITERAL_SPLIT = re.compile(r"('(?:[^']|'')*')")


def format_sql(sql: str) -> str:
    """Pretty-print a single-line SQL string onto clause-aligned lines.

    The agent emits SQL on one line; the scan/correlate templates are multi-line.
    This formats generated SQL to match, without altering semantics: newlines are
    only inserted outside string literals, so ``LIKE '%a and b%'`` is untouched.
    """
    stripped = sql.strip()
    if not stripped or "\n" in stripped:
        return stripped

    parts = _SQL_LITERAL_SPLIT.split(stripped)
    out: list[str] = []
    for index, part in enumerate(parts):
        if index % 2 == 1:  # odd segments are quoted string literals — leave as-is
            out.append(part)
            continue
        seg = _SQL_CLAUSE_NEWLINE.sub(lambda m: "\n" + m.group(1).upper(), part)
        seg = _SQL_PREDICATE_NEWLINE.sub(lambda m: "\n    " + m.group(1).upper(), seg)
        out.append(seg)
    return "".join(out).strip()


def _unwrap_json_analysis(content: str) -> str:
    """Defensively unwrap analysis text if the model still returns a JSON blob.

    Some models echo ``{"sql": ..., "reasoning": ...}`` even when asked for prose.
    In that case, surface the human-readable field instead of the raw JSON.
    """
    stripped = content.strip()
    if not stripped.startswith("{"):
        return stripped
    match = JSON_PATTERN.search(stripped)
    if not match:
        return stripped
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return stripped
    if not isinstance(parsed, dict):
        return stripped
    for key in ("analysis", "summary", "reasoning"):
        value = parsed.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return stripped


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
    return format_sql(sql), reasoning


def summarize_results(question: str, sql: str, rows: list[dict[str, Any]]) -> str:
    """Generate human-readable analysis from query results."""
    preview = rows[:15]
    payload = json.dumps(preview, default=str)[:8000]
    prompt = (
        f"User question: {question}\n\nSQL executed:\n{sql}\n\n"
        f"Results ({len(rows)} rows, showing up to 15):\n{payload}\n\n"
        "Write the Markdown security analysis now."
    )
    try:
        content = chat_completion(
            [
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
    except LLMError as exc:
        raise AgentError(str(exc)) from exc

    return _unwrap_json_analysis(content)


def analyze_root_cause(
    *,
    cve: str | None,
    package: str | None,
    rows: list[dict[str, Any]],
) -> str:
    """Generate a Markdown root-cause narrative from cross-source signal rows.

    Args:
        cve: Vulnerability identifier under investigation.
        package: Affected package name.
        rows: Rows from :func:`~devsecops_coral.queries.root_cause.run_root_cause`,
            containing vuln summary, Sentry error fields, and related PR fields.

    Returns:
        Concise GitHub-flavored Markdown explaining the probable root cause.
    """
    preview = rows[:20]
    payload = json.dumps(preview, default=str)[:8000]
    target = f"{cve or 'vulnerability'} in {package or 'the affected package'}"
    prompt = (
        f"Root-cause target: {target}\n\n"
        f"Correlated signals ({len(rows)} rows, OSV vuln + Sentry errors + GitHub PRs):\n"
        f"{payload}\n\n"
        "Write the Markdown root-cause analysis now."
    )
    try:
        content = chat_completion(
            [
                {"role": "system", "content": ROOT_CAUSE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
    except LLMError as exc:
        raise AgentError(str(exc)) from exc

    return _unwrap_json_analysis(content)


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
