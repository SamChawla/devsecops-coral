/**
 * Syntax-highlighted Coral SQL viewer with copy-to-clipboard.
 */
import { useState } from "react";
import { T } from "../theme/tokens.js";
import { ActionButton, Card, CardHeader, Pill } from "./ui/Primitives.jsx";

const TOKENS = [
  { re: /\b(SELECT|FROM|LEFT JOIN|JOIN|INNER JOIN|WHERE|ORDER BY|GROUP BY|HAVING|UNION ALL|AND|OR|ON|AS|LIMIT|OFFSET|DISTINCT|CASE|WHEN|THEN|ELSE|END)\b/, color: "#60a5fa" },
  { re: /\b(osv|github|sentry|jira|grafana|coral|slack|notion)\b/,                                                                                           color: "#f97316" },
  { re: /\b(search_vulnerabilities|vulnerability_detail|issues|pulls|events|alerts|tables|columns|table_functions)\b/,                                        color: "#a78bfa" },
  { re: /'[^']*'/,                                                                                                                                             color: "#34d399" },
  { re: /--.*$/,                                                                                                                                               color: "#64748b" },
  { re: /\b(\d+)\b/,                                                                                                                                           color: "#fbbf24" },
];

/** Apply lightweight syntax highlighting to a single SQL line. */
function tokenize(line) {
  if (!line.trim()) return [{ text: line, color: null }];
  const segments = [];
  let remaining = line;
  let safety = 0;
  while (remaining.length > 0 && safety++ < 500) {
    let earliest = null, earliestIndex = Infinity, earliestMatch = null;
    for (const tok of TOKENS) {
      const m = tok.re.exec(remaining);
      if (m && m.index < earliestIndex) { earliest = tok; earliestIndex = m.index; earliestMatch = m; }
    }
    if (!earliest) { segments.push({ text: remaining, color: null }); break; }
    if (earliestIndex > 0) segments.push({ text: remaining.slice(0, earliestIndex), color: null });
    segments.push({ text: earliestMatch[0], color: earliest.color });
    remaining = remaining.slice(earliestIndex + earliestMatch[0].length);
  }
  return segments;
}

/**
 * Displays the last executed Coral SQL query with syntax highlighting.
 * @param {{ sql: string }} props
 */
export default function SqlViewer({ sql }) {
  const [copied, setCopied] = useState(false);
  const text = sql || "";
  const placeholder = !text;
  const displayText = text || "-- Run a query to see the generated Coral SQL here\n-- Cross-source JOINs will appear with full syntax highlighting";
  const lines = displayText.split("\n");

  const copySql = async () => {
    if (!text) return;
    try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { /* ignore */ }
  };

  return (
    <Card>
      <CardHeader
        title="Generated Coral SQL"
        right={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Pill color={T.accent}>cross-source join</Pill>
            <ActionButton onClick={copySql} disabled={placeholder} style={{ padding: "5px 10px", fontSize: 11 }}>
              {copied ? "✓ Copied" : "Copy SQL"}
            </ActionButton>
          </div>
        }
      />

      {/* Code area */}
      <div style={{ background: T.codeBg }}>
        {placeholder ? (
          <div style={{ padding: "18px 20px", fontFamily: T.mono, fontSize: 12, color: T.textMuted, lineHeight: 1.8 }}>
            {displayText.split("\n").map((line, i) => <div key={i}>{line}</div>)}
          </div>
        ) : (
          <pre style={{ margin: 0, padding: "14px 0", fontSize: 12, lineHeight: 1.75, fontFamily: T.mono, overflowX: "auto", maxHeight: 360, overflowY: "auto" }}>
            {lines.map((line, lineIdx) => {
              const segments = tokenize(line);
              return (
                <div key={lineIdx} style={{ display: "flex", minHeight: "1.75em" }}>
                  <span style={{
                    display: "inline-block", width: 44, textAlign: "right",
                    paddingRight: 16, color: T.textMuted, fontSize: 10,
                    userSelect: "none", flexShrink: 0, opacity: 0.5,
                  }}>
                    {lineIdx + 1}
                  </span>
                  <span>
                    {segments.map((seg, si) => (
                      <span key={si} style={{ color: seg.color || T.textSecondary }}>{seg.text}</span>
                    ))}
                  </span>
                </div>
              );
            })}
          </pre>
        )}
      </div>

      {/* Legend */}
      <div style={{
        padding: "8px 14px", borderTop: `1px solid ${T.border}`,
        display: "flex", gap: 14, flexWrap: "wrap",
        background: T.surfaceAlt,
      }}>
        {[["#60a5fa", "keywords"], ["#f97316", "sources"], ["#a78bfa", "tables"], ["#34d399", "strings"]].map(([color, label]) => (
          <span key={label} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: T.textMuted }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: color, display: "inline-block" }} />
            {label}
          </span>
        ))}
      </div>
    </Card>
  );
}
