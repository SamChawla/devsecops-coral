/**
 * Dual-mode query console — natural language (agent) or raw Coral SQL.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { T } from "../theme/tokens.js";
import { ActionButton, Card, CardHeader } from "./ui/Primitives.jsx";
import Markdown from "./ui/Markdown.jsx";
import SqlCode from "./ui/SqlCode.jsx";

const PAGE_SIZE = 8;

const QUICK_PROMPTS = {
  nl: [
    "Which critical vulnerabilities are still untracked?",
    "Which package has the noisiest Sentry errors this week?",
    "Show timeline events related to GitHub activity.",
  ],
  sql: [
    "SELECT * FROM github.pulls LIMIT 10",
    "SELECT * FROM sentry.issues LIMIT 10",
    "SELECT * FROM jira.issues LIMIT 10",
  ],
};

/** Pagination controls for query result tables. */
function ResultPager({ page, totalPages, setPage, totalRows }) {
  if (totalPages <= 1) return null;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, marginTop: 10 }}>
      <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
        Page {page + 1} of {totalPages} · {totalRows} rows
      </span>
      <div style={{ display: "flex", gap: 6 }}>
        <ActionButton onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>Prev</ActionButton>
        <ActionButton onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}>Next</ActionButton>
      </div>
    </div>
  );
}

const TYPE_BADGE = {
  create_jira: { label: "JIRA",    color: "#3b82f6" },
  create_pr:   { label: "PR",      color: "#8b5cf6" },
  annotate_grafana: { label: "GRAFANA", color: "#f97316" },
  generate_report:  { label: "REPORT",  color: "#6b7280" },
  create_github_issue: { label: "GITHUB", color: "#10b981" },
};

/** Mini action pill shown in the recommendations block. */
function ActionPill({ action }) {
  const badge = TYPE_BADGE[action.type] || { label: action.type.toUpperCase(), color: "#6b7280" };
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 8,
      padding: "8px 10px",
      background: "rgba(255,255,255,0.03)",
      borderRadius: 6,
      border: `1px solid rgba(255,255,255,0.07)`,
      borderLeft: action.urgent ? "3px solid rgba(239,68,68,0.6)" : `3px solid ${badge.color}44`,
    }}>
      <span style={{
        display: "inline-block", padding: "2px 7px", borderRadius: 999, fontSize: 9,
        fontWeight: 800, fontFamily: "var(--mono, monospace)",
        background: `${badge.color}22`, color: badge.color,
        letterSpacing: "0.08em", flexShrink: 0, marginTop: 1,
      }}>
        {badge.label}
      </span>
      <span style={{ fontSize: 12, color: "rgba(255,255,255,0.7)", lineHeight: 1.5 }}>
        {action.title}
        {action.urgent && (
          <span style={{ marginLeft: 6, fontSize: 10, fontWeight: 700, color: "#ef4444" }}>
            URGENT
          </span>
        )}
      </span>
    </div>
  );
}

/**
 * Natural language and raw SQL query input with paginated results.
 * @param {{ onAsk: Function, onSql: Function, loading: boolean, result: object|null, seedQuery: object, onSwitchTab: Function }} props
 */
export default function QueryConsole({ onAsk, onSql, loading, result, seedQuery, onSwitchTab }) {
  const [mode, setMode] = useState("nl");
  const [input, setInput] = useState("");
  const [page, setPage] = useState(0);
  const [resultTab, setResultTab] = useState("analysis");
  const [copied, setCopied] = useState(false);
  const taRef = useRef(null);

  useEffect(() => {
    if (seedQuery?.text) { setInput(seedQuery.text); setMode("nl"); }
  }, [seedQuery?.id, seedQuery?.text]);

  useEffect(() => { setPage(0); }, [result]);

  // Auto-grow the textarea to fit multi-line SQL (capped, then scrolls).
  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [input, mode]);

  const rows = result?.data || [];
  const columns = useMemo(() => (rows.length > 0 ? Object.keys(rows[0]) : []), [rows]);
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const pageRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const hasAnalysis = Boolean(result?.analysis);
  const hasSql = Boolean(result?.sql);
  const tabs = useMemo(() => {
    const t = [];
    if (hasAnalysis) t.push(["analysis", "Analysis"]);
    if (hasSql) t.push(["sql", "Coral SQL"]);
    if (rows.length) t.push(["results", `Results · ${rows.length}`]);
    return t;
  }, [hasAnalysis, hasSql, rows.length]);

  // When a fresh result arrives, focus the most relevant tab.
  useEffect(() => {
    if (!result) return;
    if (result.analysis) setResultTab("analysis");
    else if (result.data?.length) setResultTab("results");
    else if (result.sql) setResultTab("sql");
  }, [result]);

  const copySql = async () => {
    if (!result?.sql) return;
    try {
      await navigator.clipboard.writeText(result.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch { /* ignore */ }
  };

  const run = () => {
    if (!input.trim() || loading) return;
    if (mode === "nl") onAsk(input.trim());
    else onSql(input.trim());
  };

  return (
    <Card accent={T.accent}>
      <CardHeader
        title="Query Console"
        accent={T.accent}
        right={
          <div style={{ display: "flex", gap: 4 }}>
            {[["nl", "Natural language"], ["sql", "Raw SQL"]].map(([m, label]) => (
              <ActionButton
                key={m} onClick={() => setMode(m)} active={mode === m}
                style={{ padding: "5px 10px", fontSize: 10, textTransform: "uppercase" }}
              >
                {label}
              </ActionButton>
            ))}
          </div>
        }
      />

      <div style={{ padding: 12 }}>
        {/* Input + Execute */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); run(); }
            }}
            rows={1}
            spellCheck={false}
            placeholder={
              mode === "nl"
                ? "Ask a question about sources, vulnerabilities, or activity…"
                : "SELECT id, severity FROM osv.search_vulnerabilities(…)"
            }
            style={{
              flex: 1, minWidth: 220,
              padding: "9px 13px",
              background: T.inputBg,
              border: `1px solid ${T.border}`,
              borderRadius: 8,
              color: T.text,
              fontSize: 13,
              fontFamily: mode === "sql" ? T.mono : T.sans,
              outline: "none",
              resize: "vertical",
              lineHeight: 1.5,
              minHeight: 42,
              maxHeight: 220,
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              boxSizing: "border-box",
            }}
          />
          <ActionButton tone="accent" onClick={run} disabled={loading || !input.trim()} style={{ minWidth: 100, height: 42 }}>
            {loading ? "Running…" : "▶ Execute"}
          </ActionButton>
        </div>

        <div style={{ fontSize: 10, color: T.textMuted, fontFamily: T.mono, marginBottom: 10 }}>
          Enter to run · Shift+Enter for a new line
        </div>

        {/* Quick prompts */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
          {QUICK_PROMPTS[mode].map((prompt) => (
            <ActionButton key={prompt} onClick={() => setInput(prompt)} style={{ fontSize: 11 }}>
              {prompt}
            </ActionButton>
          ))}
        </div>

        {/* Tabbed result panel — Analysis · Coral SQL · Results */}
        {tabs.length > 0 ? (
          <div style={{
            marginBottom: 10,
            border: `1px solid ${T.border}`,
            borderRadius: 8,
            overflow: "hidden",
          }}>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              gap: 8, padding: "6px 8px",
              borderBottom: `1px solid ${T.border}`,
              background: T.surfaceAlt,
            }}>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {tabs.map(([id, label]) => (
                  <ActionButton
                    key={id}
                    onClick={() => setResultTab(id)}
                    active={resultTab === id}
                    style={{ padding: "5px 10px", fontSize: 11 }}
                  >
                    {label}
                  </ActionButton>
                ))}
              </div>
              {resultTab === "sql" && hasSql ? (
                <ActionButton onClick={copySql} style={{ padding: "5px 10px", fontSize: 11 }}>
                  {copied ? "✓ Copied" : "Copy SQL"}
                </ActionButton>
              ) : null}
            </div>

            <div style={{ padding: resultTab === "sql" ? 0 : 12 }}>
              {/* Analysis tab */}
              {resultTab === "analysis" && hasAnalysis ? (
                <Markdown text={result.analysis} />
              ) : null}

              {/* Coral SQL tab */}
              {resultTab === "sql" && hasSql ? (
                <SqlCode text={result.sql} maxHeight={320} />
              ) : null}

              {/* Results tab */}
              {resultTab === "results" && rows.length > 0 ? (
                <>
                  <div style={{ overflowX: "auto", borderRadius: 8, border: `1px solid ${T.border}` }}>
                    <div style={{ maxHeight: 260, overflowY: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: T.mono }}>
                        <thead>
                          <tr style={{
                            borderBottom: `1px solid ${T.border}`,
                            position: "sticky", top: 0,
                            background: T.surfaceAlt,
                          }}>
                            {columns.map((col) => (
                              <th key={col} style={{ padding: "8px 10px", textAlign: "left", color: T.textMuted, fontWeight: 600 }}>
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {pageRows.map((row, ri) => (
                            <tr key={`${page}-${ri}`} style={{ borderBottom: `1px solid ${T.border}` }}>
                              {columns.map((col) => (
                                <td key={col}
                                  style={{ padding: "6px 10px", color: T.textSecondary, maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                                  title={row[col] == null ? "-" : String(row[col])}
                                >
                                  {row[col] == null ? "-" : String(row[col])}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <ResultPager page={page} totalPages={totalPages} setPage={setPage} totalRows={rows.length} />
                </>
              ) : null}
            </div>
          </div>
        ) : null}

        {/* Agent Analysis + Recommended Actions block */}
        {result?.recommendations?.length > 0 ? (
          <div style={{
            marginBottom: rows.length ? 10 : 0,
            background: "rgba(16,185,129,0.04)",
            borderRadius: 8,
            border: "1px solid rgba(16,185,129,0.2)",
            overflow: "hidden",
          }}>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "9px 12px",
              borderBottom: "1px solid rgba(16,185,129,0.15)",
              background: "rgba(16,185,129,0.08)",
            }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: T.green, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                Agent Analysis + Recommended Actions
              </span>
              <span style={{ fontSize: 11, fontFamily: "var(--mono, monospace)", color: T.textMuted }}>
                {result.recommendations.length} action(s)
              </span>
            </div>
            <div style={{ padding: "8px 10px", display: "flex", flexDirection: "column", gap: 5 }}>
              {result.recommendations.map((action) => (
                <ActionPill key={action.id} action={action} />
              ))}
            </div>
            {onSwitchTab ? (
              <div style={{ padding: "6px 12px 10px", borderTop: "1px solid rgba(16,185,129,0.1)" }}>
                <button
                  type="button"
                  onClick={() => onSwitchTab("actions")}
                  style={{
                    background: "none", border: "none", padding: 0, cursor: "pointer",
                    fontSize: 12, color: T.green, fontWeight: 600,
                    textDecoration: "underline", textDecorationColor: "rgba(16,185,129,0.4)",
                  }}
                >
                  Review in Actions tab →
                </button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
