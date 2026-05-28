/**
 * Filter bar for ecosystem, packages, time window, and query actions.
 */
import { useState } from "react";
import { T } from "../theme/tokens.js";
import { ActionButton } from "./ui/Primitives.jsx";

/** Labeled text input for a command-bar filter field. */
function Field({ label, value, onChange, placeholder, note, small }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{
        fontSize: 10, fontWeight: 700, textTransform: "uppercase",
        letterSpacing: "0.08em", color: T.textMuted,
      }}>
        {label}
      </span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          padding: "7px 11px",
          background: T.inputBg,
          border: `1px solid ${T.border}`,
          borderRadius: 8,
          color: T.text,
          fontSize: 12,
          outline: "none",
          fontFamily: T.sans,
          width: small ? 120 : "100%",
          transition: "border-color 0.15s, box-shadow 0.15s",
        }}
      />
      {note ? <span style={{ fontSize: 10, color: T.textMuted }}>{note}</span> : null}
    </label>
  );
}

/**
 * Query filter controls and run buttons for scan, correlate, and timeline.
 * @param {{ filters: object, onChange: Function, onRunScan: Function, onRunCorrelate: Function, onRunTimeline: Function, onRefreshAll: Function, loading: boolean }} props
 */
export default function CommandBar({ filters, onChange, onRunScan, onRunCorrelate, onRunTimeline, onRefreshAll, loading }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{
      background: T.surface,
      border: `1px solid ${T.border}`,
      borderRadius: 14,
      overflow: "hidden",
      boxShadow: T.shadowCard,
    }}>
      {/* Primary row */}
      <div style={{ padding: "12px 16px", display: "flex", alignItems: "flex-end", gap: 12, flexWrap: "wrap", minHeight: 66 }}>
        <div style={{ flex: "2 1 160px" }}>
          <Field label="Ecosystem" value={filters.ecosystem} onChange={(v) => onChange("ecosystem", v)} placeholder="PyPI" small />
        </div>
        <div style={{ flex: "4 1 260px" }}>
          <Field label="Packages" value={filters.packages} onChange={(v) => onChange("packages", v)} placeholder="django, flask, requests, celery" />
        </div>
        <div style={{ flex: "1 1 90px" }}>
          <Field label="Lookback" value={filters.since} onChange={(v) => onChange("since", v)} placeholder="7d" small />
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexShrink: 0 }}>
          <ActionButton tone="accent" onClick={onRunScan} disabled={loading} style={{ padding: "8px 20px" }}>
            {loading ? "Running…" : "▶ Run Scan"}
          </ActionButton>
          <ActionButton onClick={onRunCorrelate} disabled={loading}>Correlate</ActionButton>
          <ActionButton onClick={onRunTimeline}  disabled={loading}>Timeline</ActionButton>
          <ActionButton onClick={onRefreshAll}   disabled={loading} title="Refresh all panels">↺</ActionButton>
          <ActionButton onClick={() => setExpanded((v) => !v)} active={expanded} title="GitHub filters">
            {expanded ? "▲" : "▼"} GitHub
          </ActionButton>
        </div>
      </div>

      {/* Collapsible GitHub filters */}
      {expanded && (
        <div style={{
          padding: "12px 16px 14px",
          borderTop: `1px solid ${T.border}`,
          display: "flex", gap: 12,
          background: T.surfaceAlt,
        }}>
          <div style={{ flex: 1 }}>
            <Field label="GitHub owner" value={filters.github_owner} onChange={(v) => onChange("github_owner", v)} placeholder="your-org" note="Optional — scopes timeline queries" />
          </div>
          <div style={{ flex: 1 }}>
            <Field label="GitHub repo" value={filters.github_repo} onChange={(v) => onChange("github_repo", v)} placeholder="your-repo" note="Optional" />
          </div>
        </div>
      )}
    </div>
  );
}
