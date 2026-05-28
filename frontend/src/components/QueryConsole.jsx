/**
 * Dual-mode query console — natural language (agent) or raw Coral SQL.
 */
import { useEffect, useMemo, useState } from "react";
import { T } from "../theme/tokens.js";
import { ActionButton, Card, CardHeader } from "./ui/Primitives.jsx";

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

/**
 * Natural language and raw SQL query input with paginated results.
 * @param {{ onAsk: Function, onSql: Function, loading: boolean, result: object|null, seedQuery: object }} props
 */
export default function QueryConsole({ onAsk, onSql, loading, result, seedQuery }) {
  const [mode, setMode] = useState("nl");
  const [input, setInput] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    if (seedQuery?.text) { setInput(seedQuery.text); setMode("nl"); }
  }, [seedQuery?.id, seedQuery?.text]);

  useEffect(() => { setPage(0); }, [result]);

  const rows = result?.data || [];
  const columns = useMemo(() => (rows.length > 0 ? Object.keys(rows[0]) : []), [rows]);
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const pageRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

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
        <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
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
            }}
          />
          <ActionButton tone="accent" onClick={run} disabled={loading || !input.trim()} style={{ minWidth: 100 }}>
            {loading ? "Running…" : "▶ Execute"}
          </ActionButton>
        </div>

        {/* Quick prompts */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
          {QUICK_PROMPTS[mode].map((prompt) => (
            <ActionButton key={prompt} onClick={() => setInput(prompt)} style={{ fontSize: 11 }}>
              {prompt}
            </ActionButton>
          ))}
        </div>

        {/* Analysis */}
        {result?.analysis ? (
          <div style={{
            padding: 12, marginBottom: rows.length ? 10 : 0,
            background: "rgba(16,185,129,0.06)",
            borderRadius: 8,
            border: "1px solid rgba(16,185,129,0.18)",
          }}>
            <div style={{ fontSize: 10, color: T.green, textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700, marginBottom: 6 }}>
              Analysis
            </div>
            <div style={{ fontSize: 13, color: T.textSecondary, lineHeight: 1.7 }}>
              {result.analysis}
            </div>
          </div>
        ) : null}

        {/* Results table */}
        {rows.length > 0 ? (
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
    </Card>
  );
}
