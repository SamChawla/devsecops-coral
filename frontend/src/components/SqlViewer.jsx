/**
 * Syntax-highlighted Coral SQL viewer with copy-to-clipboard.
 */
import { useState } from "react";
import { T } from "../theme/tokens.js";
import { ActionButton, Card, CardHeader, Pill } from "./ui/Primitives.jsx";
import SqlCode from "./ui/SqlCode.jsx";

const ACT_COMMENT_BLOCK = `
-- ACT: The agent executes via direct API calls after approval:
-- POST /rest/api/3/issue        → Create Jira ticket
-- POST /repos/{owner}/{repo}/pulls → Draft GitHub PR
-- POST /api/annotations         → Annotate Grafana timeline
-- Local file write              → Generate Markdown report
--
-- All actions require explicit human approval before execution.`.trimStart();

/**
 * Displays the last executed Coral SQL query with syntax highlighting.
 * @param {{ sql: string, mode?: "detect"|"actions" }} props
 */
export default function SqlViewer({ sql, mode = "detect" }) {
  const [copied, setCopied] = useState(false);
  const detectSql = sql || "";
  const text = mode === "actions" && detectSql
    ? `-- DETECT: Coral cross-source query\n${detectSql}\n\n${ACT_COMMENT_BLOCK}`
    : detectSql;
  const placeholder = !text;
  const displayText = text || "-- Run a query to see the generated Coral SQL here\n-- Cross-source JOINs will appear with full syntax highlighting";

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
          <SqlCode text={displayText} maxHeight={360} />
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
