/**
 * Vulnerability ↔ Sentry error correlation cards with signal classification.
 */
import { useEffect, useMemo, useState } from "react";
import { T, SEV } from "../theme/tokens.js";
import { mapCorrelateRows } from "../utils/mapData.js";
import { ActionButton, Badge, Card, CardHeader, EmptyState, Pill } from "./ui/Primitives.jsx";

const PAGE_SIZE = 6;

const SIG = {
  active:  { label: "🔴 ACTIVE",  color: T.red,    bg: "rgba(239,68,68,0.06)",   border: "rgba(239,68,68,0.2)",   left: T.red },
  monitor: { label: "🟡 MONITOR", color: T.yellow,  bg: "rgba(234,179,8,0.05)",   border: "rgba(234,179,8,0.18)",  left: T.yellow },
  clean:   { label: "🟢 CLEAN",   color: T.green,   bg: "rgba(16,185,129,0.04)",  border: "rgba(16,185,129,0.14)", left: T.green },
  unknown: { label: "⚪ UNKNOWN", color: T.textMuted, bg: "transparent",          border: T.border,                left: T.border },
};

const SEV_FILTERS = ["all", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
const SEV_COLORS  = { CRITICAL: T.red, HIGH: T.orange, MEDIUM: T.yellow, LOW: T.green };

const SIG_FILTERS = [
  { id: "all",     label: "All",     color: T.textSecondary },
  { id: "active",  label: "🔴 Active",  color: T.red },
  { id: "monitor", label: "🟡 Monitor", color: T.yellow },
  { id: "clean",   label: "🟢 Clean",   color: T.green },
];

/** Card showing one CVE/error correlation with ACTIVE/MONITOR/CLEAN signal. */
function SignalCard({ row, onFocusPackage, onAskQuestion }) {
  const [hovered, setHovered] = useState(false);
  const cfg = SIG[row.sig] || SIG.unknown;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "grid", gap: 10, padding: "14px 14px 14px 18px",
        borderRadius: 10, position: "relative",
        background: hovered ? `${cfg.bg}cc` : cfg.bg,
        border: `1px solid ${cfg.border}`,
        borderLeft: `3px solid ${cfg.left}`,
        transition: "background 0.15s",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 14, fontWeight: 700 }}>{row.pkg}</span>
          <Badge severity={row.sev} />
          <span style={{ fontSize: 11, fontFamily: T.mono, color: T.textMuted }}>{row.cve}</span>
        </div>
        <span style={{ fontSize: 10, fontWeight: 800, letterSpacing: "0.08em", color: cfg.color }}>{cfg.label}</span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, fontSize: 12, color: T.textSecondary }}>
        <span>Errors: <strong style={{ color: row.errs > 10 ? T.red : row.errs > 0 ? T.orange : T.textMuted, fontFamily: T.mono }}>{row.errs || 0}</strong></span>
        {row.errLvl ? <span>Level: <strong>{row.errLvl}</strong></span> : null}
        {row.pr ? <span title={row.pr}>PR: <strong style={{ color: T.purple }}>{row.pr.slice(0, 36)}{row.pr.length > 36 ? "…" : ""}</strong></span> : null}
        {row.summary ? <span style={{ color: T.textMuted, fontStyle: "italic" }}>{row.summary.slice(0, 80)}{row.summary.length > 80 ? "…" : ""}</span> : null}
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <ActionButton
          onClick={() => onFocusPackage(row.pkg)}
          disabled={row.pkg === "-"}
          style={{ padding: "5px 10px", fontSize: 11 }}
          title="Re-run scan scoped to this package only"
        >
          Focus package
        </ActionButton>
        <ActionButton
          onClick={() => onAskQuestion(`Why is ${row.cve} for ${row.pkg} marked ${row.sig} and what should I do next?`)}
          disabled={row.cve === "-"}
          style={{ padding: "5px 10px", fontSize: 11 }}
          title="Pre-fills the Query Console below — then click Execute"
        >
          Investigate with AI
        </ActionButton>
      </div>
    </div>
  );
}

/**
 * Correlation view — maps vulns to Sentry error spikes.
 * @param {{ rows: Array<object>, loading: boolean, onFocusPackage: Function, onAskQuestion: Function }} props
 */
export default function CorrelationView({ rows, loading, onFocusPackage, onAskQuestion }) {
  const [page, setPage]           = useState(0);
  const [sigFilter, setSigFilter] = useState("all");
  const [sevFilter, setSevFilter] = useState("all");

  const data = mapCorrelateRows(rows);

  useEffect(() => { setPage(0); }, [rows, sigFilter, sevFilter]);

  const filtered = useMemo(() => {
    let d = data;
    if (sigFilter !== "all") d = d.filter((r) => r.sig === sigFilter);
    if (sevFilter !== "all") d = d.filter((r) => r.sev === sevFilter);
    return d;
  }, [data, sigFilter, sevFilter]);

  const counts = {
    active:  data.filter((r) => r.sig === "active").length,
    monitor: data.filter((r) => r.sig === "monitor").length,
    clean:   data.filter((r) => r.sig === "clean").length,
  };

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageData   = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <Card accent={counts.active > 0 ? T.red : undefined}>
      <CardHeader
        title="Vulnerability · Error Correlation"
        right={
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            <Pill color={T.red}>{counts.active} active</Pill>
            <Pill color={T.yellow}>{counts.monitor} monitor</Pill>
            <Pill color={T.green}>{counts.clean} clean</Pill>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
              {loading ? "correlating…" : `${filtered.length} / ${data.length}`}
            </span>
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
        {/* Signal filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ fontSize: 9, color: T.textMuted, fontFamily: T.mono, textTransform: "uppercase", letterSpacing: "0.08em", marginRight: 2 }}>Signal</span>
          {SIG_FILTERS.map(({ id, label, color }) => (
            <button
              key={id}
              type="button"
              onClick={() => setSigFilter(id)}
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                border: `1px solid ${sigFilter === id ? `${color}66` : T.border}`,
                background: sigFilter === id ? `${color}14` : T.btnBase,
                color: sigFilter === id ? color : T.textMuted,
                fontSize: 10, fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.12s",
                fontFamily: T.sans,
                whiteSpace: "nowrap",
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div style={{ width: 1, height: 20, background: T.border, flexShrink: 0 }} />

        {/* Severity filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
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

      {loading && !data.length ? (
        <EmptyState message="Correlating vulnerability and runtime signals…" icon="◌" />
      ) : !filtered.length ? (
        <EmptyState message="No correlations match the current filters." />
      ) : (
        <>
          <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10, maxHeight: 460, overflowY: "auto" }}>
            {pageData.map((row, idx) => (
              <SignalCard key={`${row.cve}-${idx}`} row={row} onFocusPackage={onFocusPackage} onAskQuestion={onAskQuestion} />
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderTop: `1px solid ${T.border}`, gap: 10 }}>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>{page + 1}/{totalPages} · {filtered.length} correlations</span>
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
