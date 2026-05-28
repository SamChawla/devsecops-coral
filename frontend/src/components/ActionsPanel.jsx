/**
 * Actions tab panel — shows recommended actions with Approve / Dismiss controls.
 * Implements the human-in-the-loop approval flow from the PRD.
 */
import { T } from "../theme/tokens.js";
import { ActionButton, Badge, Card, CardHeader, EmptyState, Pill } from "./ui/Primitives.jsx";

const TYPE_META = {
  create_jira:        { label: "JIRA",     icon: "🎫", color: "#3b82f6" },
  create_pr:          { label: "GITHUB PR", icon: "🔀", color: "#8b5cf6" },
  create_github_issue:{ label: "GITHUB",   icon: "🐛", color: "#10b981" },
  annotate_grafana:   { label: "GRAFANA",  icon: "📌", color: "#f97316" },
  generate_report:    { label: "REPORT",   icon: "📋", color: "#6b7280" },
};

const STATUS_ROW_STYLE = {
  pending:   { background: "transparent",                   border: T.border,                        opacity: 1 },
  executing: { background: "rgba(255,107,53,0.05)",         border: "rgba(255,107,53,0.3)",          opacity: 1 },
  done:      { background: "rgba(16,185,129,0.04)",         border: "rgba(16,185,129,0.18)",         opacity: 1 },
  dismissed: { background: "transparent",                   border: T.border,                        opacity: 0.4 },
  failed:    { background: "rgba(239,68,68,0.04)",          border: "rgba(239,68,68,0.2)",           opacity: 1 },
};

/** Type badge pill: JIRA / GITHUB PR / GRAFANA / REPORT */
function TypeBadge({ type }) {
  const m = TYPE_META[type] || { label: type?.toUpperCase?.() || "?", icon: "•", color: T.textMuted };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 999, fontSize: 9,
      fontWeight: 800, fontFamily: "var(--mono, monospace)",
      background: `${m.color}20`, color: m.color,
      border: `1px solid ${m.color}35`,
      letterSpacing: "0.06em", whiteSpace: "nowrap", flexShrink: 0,
    }}>
      {m.icon} {m.label}
    </span>
  );
}

/** Single action row. */
function ActionRow({ action, onApprove, onDismiss, approving }) {
  const st = action.status || "pending";
  const rowStyle = STATUS_ROW_STYLE[st] || STATUS_ROW_STYLE.pending;
  const isExecuting = approving === action.id || st === "executing";
  const resultDetail = action.result
    ? (action.result.key || action.result.url || action.result.path || action.result.error || "")
    : "";

  return (
    <div style={{
      padding: "12px 16px",
      borderBottom: `1px solid ${T.border}`,
      background: rowStyle.background,
      opacity: rowStyle.opacity,
      borderLeft: `3px solid ${action.urgent ? "rgba(239,68,68,0.6)" : rowStyle.border}`,
      transition: "background 0.3s, opacity 0.3s",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10, flexWrap: "wrap" }}>
        {/* Left: type + severity badges */}
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexShrink: 0, paddingTop: 1 }}>
          <TypeBadge type={action.type} />
          {action.severity && action.severity !== "INFO" && <Badge severity={action.severity} />}
          {action.urgent && (
            <span style={{
              fontSize: 9, fontWeight: 800, color: T.red,
              background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)",
              padding: "1px 6px", borderRadius: 4, letterSpacing: "0.06em",
            }}>
              URGENT
            </span>
          )}
        </div>

        {/* Middle: title + detail */}
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 3 }}>
            {action.title}
          </div>
          <div style={{ fontSize: 12, color: T.textSecondary, lineHeight: 1.5 }}>
            {action.detail}
          </div>
          {/* Status / result feedback */}
          {(isExecuting || st === "done" || st === "failed" || st === "dismissed") && (
            <div style={{ marginTop: 5, fontSize: 11, fontFamily: "var(--mono, monospace)" }}>
              {isExecuting && st !== "done" && (
                <span style={{ color: T.accent }}>⟳ Executing…</span>
              )}
              {st === "done" && (
                <span style={{ color: T.green }}>
                  ✓ Executed{resultDetail ? ` — ${resultDetail}` : ""}
                </span>
              )}
              {st === "failed" && (
                <span style={{ color: T.red }}>
                  ✗ Failed — {action.result?.error || "unknown error"}
                </span>
              )}
              {st === "dismissed" && (
                <span style={{ color: T.textMuted }}>Dismissed</span>
              )}
            </div>
          )}
        </div>

        {/* Right: approve/dismiss (pending only) */}
        {st === "pending" && (
          <div style={{ display: "flex", gap: 6, flexShrink: 0, marginTop: 1 }}>
            <ActionButton
              tone="accent"
              onClick={() => onApprove(action.id)}
              disabled={!!approving}
              style={{ padding: "5px 12px", fontSize: 11 }}
            >
              Approve
            </ActionButton>
            <ActionButton
              onClick={() => onDismiss(action.id)}
              disabled={!!approving}
              style={{ padding: "5px 10px", fontSize: 11 }}
            >
              Dismiss
            </ActionButton>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Actions panel — lists recommended actions with approve/dismiss controls.
 * @param {{ actions: Array, loading: boolean, approving: number|null, onApprove: Function, onDismiss: Function, onApproveAll: Function, onRefresh: Function }} props
 */
export default function ActionsPanel({ actions = [], loading, approving, onApprove, onDismiss, onApproveAll, onRefresh }) {
  const pendingCount = actions.filter((a) => a.status === "pending").length;
  const doneCount    = actions.filter((a) => a.status === "done").length;
  const hasPending   = pendingCount > 0;

  return (
    <Card
      accent={hasPending ? T.accent : undefined}
      glow={hasPending ? T.accent : undefined}
    >
      <CardHeader
        title="Recommended Actions"
        accent={T.accent}
        right={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {doneCount > 0 && <Pill color={T.green}>{doneCount} completed</Pill>}
            {loading && !approving && (
              <span style={{ fontSize: 11, color: T.textMuted, fontFamily: "var(--mono, monospace)" }}>
                loading…
              </span>
            )}
            <ActionButton
              onClick={onRefresh}
              disabled={loading || !!approving}
              style={{ padding: "5px 10px", fontSize: 11 }}
            >
              ↻ Refresh
            </ActionButton>
            {hasPending && (
              <ActionButton
                tone="accent"
                onClick={onApproveAll}
                disabled={loading || !!approving}
                style={{ padding: "5px 14px", fontSize: 11 }}
              >
                Approve All ({pendingCount})
              </ActionButton>
            )}
          </div>
        }
      />

      {actions.length === 0 ? (
        <EmptyState
          message={loading ? "Loading recommendations…" : "No pending actions. Run Scan + Correlate first, then Refresh."}
          icon={loading ? "◌" : "✓"}
        />
      ) : (
        <div>
          {actions.map((action) => (
            <ActionRow
              key={action.id}
              action={action}
              approving={approving}
              onApprove={onApprove}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
