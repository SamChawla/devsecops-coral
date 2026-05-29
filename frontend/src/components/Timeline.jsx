/**
 * Unified cross-source security event timeline with source and severity filters.
 */
import { memo, useEffect, useMemo, useState } from "react";
import { T, SRC_CLR, SEV } from "../theme/tokens.js";
import { mapTimelineRows } from "../utils/mapData.js";
import { ActionButton, Badge, Card, CardHeader, EmptyState } from "./ui/Primitives.jsx";

export default memo(Timeline);

const PAGE_SIZE = 14;

const SEV_FILTERS = ["all", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
const SEV_COLORS  = { CRITICAL: T.red, HIGH: T.orange, MEDIUM: T.yellow, LOW: T.green, INFO: T.blue };

/** Colored badge for a timeline event source. */
function SourceChip({ src }) {
  const color = SRC_CLR[src] || T.textMuted;
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 4,
      background: `${color}14`, border: `1px solid ${color}33`,
      fontSize: 10, fontWeight: 700, textTransform: "uppercase",
      letterSpacing: "0.06em", color, whiteSpace: "nowrap",
    }}>
      {src}
    </span>
  );
}

/**
 * Chronological security event timeline across GitHub, Sentry, Jira, and Grafana.
 * @param {{ rows: Array<object>, loading: boolean, onRefresh: Function }} props
 */
function Timeline({ rows, loading, onRefresh }) {
  const [page, setPage]                 = useState(0);
  const [sourceFilter, setSourceFilter] = useState("all");
  const [sevFilter, setSevFilter]       = useState("all");

  const events = mapTimelineRows(rows);

  useEffect(() => { setPage(0); }, [rows, sourceFilter, sevFilter]);

  const sources = useMemo(() => ["all", ...Array.from(new Set(events.map((e) => e.src)))], [events]);

  const filtered = useMemo(() =>
    events.filter((e) =>
      (sourceFilter === "all" || e.src === sourceFilter) &&
      (sevFilter    === "all" || e.sev === sevFilter)
    ),
    [events, sourceFilter, sevFilter]
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageData   = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <Card>
      <CardHeader
        title="Security Event Timeline"
        right={
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
              {loading ? "building…" : `${filtered.length} / ${events.length} events`}
            </span>
            <ActionButton onClick={onRefresh} disabled={loading} style={{ padding: "5px 10px", fontSize: 11 }}>
              {loading ? "Loading…" : "↻ Refresh"}
            </ActionButton>
          </div>
        }
      />

      {/* Filter bar */}
      <div style={{
        padding: "8px 14px",
        borderBottom: `1px solid ${T.border}`,
        background: T.surfaceAlt,
        display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
      }}>
        {/* Source filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
          <span style={{ fontSize: 9, color: T.textMuted, fontFamily: T.mono, textTransform: "uppercase", letterSpacing: "0.08em", marginRight: 2 }}>Source</span>
          {sources.map((src) => {
            const color = src === "all" ? T.textSecondary : (SRC_CLR[src] || T.textMuted);
            const active = sourceFilter === src;
            return (
              <button
                key={src}
                type="button"
                onClick={() => setSourceFilter(src)}
                style={{
                  padding: "4px 10px",
                  borderRadius: 6,
                  border: `1px solid ${active ? `${color}66` : T.border}`,
                  background: active ? `${color}18` : T.btnBase,
                  color: active ? color : T.textMuted,
                  fontSize: 10, fontWeight: 700,
                  cursor: "pointer",
                  transition: "all 0.12s",
                  textTransform: "uppercase",
                  fontFamily: T.mono,
                  letterSpacing: "0.06em",
                  whiteSpace: "nowrap",
                }}
              >
                {src}
              </button>
            );
          })}
        </div>

        <div style={{ width: 1, height: 20, background: T.border, flexShrink: 0 }} />

        {/* Severity filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
          <span style={{ fontSize: 9, color: T.textMuted, fontFamily: T.mono, textTransform: "uppercase", letterSpacing: "0.08em", marginRight: 2 }}>Severity</span>
          {SEV_FILTERS.map((v) => {
            const color = v === "all" ? T.textSecondary : SEV_COLORS[v];
            const active = sevFilter === v;
            return (
              <button
                key={v}
                type="button"
                onClick={() => setSevFilter(v)}
                style={{
                  padding: "4px 10px",
                  borderRadius: 6,
                  border: `1px solid ${active ? `${color}66` : T.border}`,
                  background: active ? `${color}18` : T.btnBase,
                  color: active ? color : T.textMuted,
                  fontSize: 10, fontWeight: 700,
                  cursor: "pointer",
                  transition: "all 0.12s",
                  letterSpacing: "0.06em",
                  textTransform: "uppercase",
                  fontFamily: T.mono,
                  whiteSpace: "nowrap",
                }}
              >
                {v === "all" ? "All" : v}
              </button>
            );
          })}
        </div>
      </div>

      {loading && !events.length ? (
        <EmptyState message="Building timeline…" icon="◌" />
      ) : !events.length ? (
        <EmptyState
          icon="◌"
          message={
            <span>
              No timeline events found.
              <br />
              <span style={{ fontSize: 11, color: T.textMuted, display: "block", marginTop: 6 }}>
                Connect <strong>Jira</strong>, <strong>Sentry</strong>, or <strong>Grafana</strong> sources
                in the sidebar to populate the timeline.
                <br />
                Or set <code style={{ fontFamily: "monospace" }}>GITHUB_OWNER</code> in{" "}
                <code style={{ fontFamily: "monospace" }}>.env</code> for GitHub PR events.
              </span>
            </span>
          }
        />
      ) : !filtered.length ? (
        <EmptyState message="No events match the current filters." />
      ) : (
        <>
          <div style={{ padding: "12px 20px 8px 36px", position: "relative", maxHeight: 480, overflowY: "auto" }}>
            {/* Vertical timeline line */}
            <div style={{ position: "absolute", left: 22, top: 12, bottom: 8, width: 1.5, background: `linear-gradient(to bottom, ${T.accent}44, transparent)` }} />

            {pageData.map((evt, idx) => {
              const dotColor = SRC_CLR[evt.src] || T.textMuted;
              return (
                <div key={`${page}-${idx}`} style={{ display: "grid", gridTemplateColumns: "96px 68px 1fr 80px", gap: 12, marginBottom: 14, position: "relative", alignItems: "center" }}>
                  {/* Timeline dot */}
                  <div style={{
                    position: "absolute", left: -18, top: "50%", transform: "translateY(-50%)",
                    width: 9, height: 9, borderRadius: "50%",
                    background: dotColor, border: `2px solid ${T.bg}`,
                    boxShadow: `0 0 8px ${dotColor}66`,
                  }} />
                  <span style={{ fontFamily: T.mono, fontSize: 11, color: T.textMuted, lineHeight: 1.4 }}>{evt.ts}</span>
                  <SourceChip src={evt.src} />
                  <span style={{ fontSize: 12, color: T.textSecondary, lineHeight: 1.5 }}>{evt.evt}</span>
                  <div style={{ display: "flex", justifyContent: "flex-end" }}><Badge severity={evt.sev} /></div>
                </div>
              );
            })}
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderTop: `1px solid ${T.border}`, gap: 10 }}>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>{page + 1}/{totalPages} · {filtered.length} events</span>
            <div style={{ display: "flex", gap: 6 }}>
              <ActionButton onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>← Prev</ActionButton>
              <ActionButton onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}>Next →</ActionButton>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}
