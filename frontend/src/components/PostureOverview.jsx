/**
 * Severity KPI cards and threat summary strip at the top of the dashboard.
 */
import { T, SEV } from "../theme/tokens.js";
import { postureFromApi } from "../utils/mapData.js";
import { ActionButton } from "./ui/Primitives.jsx";

const SEV_ENTRIES = [
  { key: "CRITICAL", label: "Critical", icon: "▲", sublabel: "Immediate action" },
  { key: "HIGH",     label: "High",     icon: "●", sublabel: "Prioritize" },
  { key: "MEDIUM",   label: "Medium",   icon: "◆", sublabel: "Schedule fix" },
  { key: "LOW",      label: "Low",      icon: "○", sublabel: "Monitor" },
];

/** Single severity counter card with optional critical alert styling. */
function KpiCard({ sevKey, label, icon, sublabel, count, loading }) {
  const s = SEV[sevKey];
  const active = count > 0;
  const isCritical = sevKey === "CRITICAL" && active;
  const isHigh = sevKey === "HIGH" && active;

  return (
    <div style={{
      background: active
        ? `linear-gradient(135deg, ${s.bg} 0%, ${T.surface} 100%)`
        : T.surface,
      border: `1px solid ${active ? s.border : T.border}`,
      borderRadius: 16,
      overflow: "hidden",
      position: "relative",
      animation: isCritical ? "pulse-glow 3s ease-in-out infinite" : "none",
      transition: "border-color 0.4s, box-shadow 0.4s",
      boxShadow: isCritical
        ? s.glowStrong
        : isHigh
          ? `0 0 32px ${s.glow}, ${T.shadowCard}`
          : active
            ? `0 0 20px ${s.glow}, ${T.shadowCard}`
            : T.shadowCard,
    }}>
      {/* Top accent bar */}
      <div style={{
        height: 4,
        background: active
          ? `linear-gradient(90deg, ${s.text}, ${s.text}66, transparent)`
          : T.border,
      }} />

      {/* Radial glow overlay */}
      {active && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
          background: `radial-gradient(ellipse at 50% 0%, ${s.glow} 0%, transparent 65%)`,
          pointerEvents: "none", zIndex: 0,
        }} />
      )}

      <div style={{ padding: "18px 20px 16px", position: "relative", zIndex: 1 }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
          <div>
            <div style={{
              fontSize: 10, fontWeight: 700, textTransform: "uppercase",
              letterSpacing: "0.12em", color: active ? s.text : T.textMuted, marginBottom: 2,
            }}>
              {icon}&nbsp;&nbsp;{label}
            </div>
            <div style={{ fontSize: 10, color: T.textMuted, letterSpacing: "0.04em" }}>{sublabel}</div>
          </div>

          {isCritical && (
            <div style={{
              display: "flex", alignItems: "center", gap: 5,
              padding: "3px 7px",
              background: "rgba(239,68,68,0.15)",
              border: "1px solid rgba(239,68,68,0.35)",
              borderRadius: 5,
              animation: "border-pulse 2s ease-in-out infinite",
            }}>
              <div style={{
                width: 6, height: 6, borderRadius: "50%", background: s.text,
                animation: "blink-dot 1s ease-in-out infinite",
              }} />
              <span style={{ fontSize: 9, fontWeight: 800, letterSpacing: "0.1em", color: s.text, fontFamily: T.mono }}>
                ALERT
              </span>
            </div>
          )}
        </div>

        {/* Big number */}
        <div style={{
          fontSize: 68, fontWeight: 900, fontFamily: T.mono, lineHeight: 1,
          letterSpacing: "-0.06em",
          color: active ? s.text : T.textMuted,
          animation: isCritical ? "counter-glow 3s ease-in-out infinite" : "none",
          opacity: loading ? 0.25 : 1,
          transition: "opacity 0.3s",
        }}>
          {loading ? "—" : count}
        </div>

        {/* Mini bar row */}
        {active && (
          <div style={{ marginTop: 12, display: "flex", gap: 2, alignItems: "flex-end", height: 18 }}>
            {[0.55,0.3,0.8,0.45,0.7,0.35,0.6,0.25].map((h, i) => (
              <div key={i} style={{
                flex: 1,
                height: `${Math.round(h * 18)}px`,
                background: `${s.text}${Math.round(h * 70 + 20).toString(16).padStart(2, "0")}`,
                borderRadius: 2,
              }} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Aggregated vulnerability posture overview with severity KPIs.
 * @param {{ posture: object|null, scanRows: Array<object>, loading: boolean, onRefresh: Function }} props
 */
export default function PostureOverview({ posture, scanRows, loading, onRefresh }) {
  const { counts, total, untracked } = postureFromApi(posture, scanRows);
  const score = counts.CRITICAL * 10 + counts.HIGH * 4 + counts.MEDIUM * 2 + counts.LOW;
  const threatLevel = counts.CRITICAL > 0 ? "CRITICAL" : counts.HIGH > 3 ? "HIGH" : counts.HIGH > 0 ? "ELEVATED" : "NOMINAL";
  const threatColor = counts.CRITICAL > 0 ? T.red : counts.HIGH > 3 ? T.orange : counts.HIGH > 0 ? T.yellow : T.green;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* 4 KPI cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {SEV_ENTRIES.map(({ key, label, icon, sublabel }) => (
          <KpiCard
            key={key} sevKey={key} label={label} icon={icon} sublabel={sublabel}
            count={counts[key] || 0} loading={loading}
          />
        ))}
      </div>

      {/* Threat summary strip */}
      <div style={{
        display: "flex", alignItems: "center",
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: T.shadowCard,
      }}>
        {/* Threat level */}
        <div style={{
          padding: "12px 18px",
          background: `${threatColor}0d`,
          borderRight: `1px solid ${T.border}`,
          display: "flex", flexDirection: "column", gap: 2, flexShrink: 0,
        }}>
          <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.12em", color: T.textMuted, textTransform: "uppercase" }}>
            Threat Level
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: "50%", background: threatColor,
              boxShadow: `0 0 8px ${threatColor}`,
              animation: counts.CRITICAL > 0 ? "blink-dot 1s ease-in-out infinite" : "none",
            }} />
            <span style={{ fontSize: 14, fontWeight: 800, fontFamily: T.mono, color: threatColor, letterSpacing: "-0.01em" }}>
              {threatLevel}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: "flex", flex: 1, alignItems: "stretch" }}>
          <StatItem label="Total CVEs"      value={total} loading={loading} />
          <Divider />
          <StatItem label="Untracked"       value={untracked} loading={loading} color={untracked > 0 ? T.orange : T.green} />
          <Divider />
          <StatItem label="Risk Score"      value={score} loading={loading} color={score > 30 ? T.red : score > 10 ? T.orange : undefined} />
          <Divider />
          <StatItem label="Critical + High" value={(counts.CRITICAL || 0) + (counts.HIGH || 0)} loading={loading} color={T.red} />
        </div>

        {/* Refresh */}
        <div style={{ padding: "0 16px", flexShrink: 0 }}>
          <ActionButton onClick={onRefresh} disabled={loading} style={{ padding: "8px 16px" }}>
            {loading ? "Refreshing…" : "↻ Refresh"}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}

/** Label/value pair in the threat summary strip. */
function StatItem({ label, value, loading, color }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 3, padding: "10px 18px" }}>
      <span style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: "0.12em", color: T.textMuted, fontWeight: 700 }}>
        {label}
      </span>
      <span style={{
        fontSize: 22, fontWeight: 800, fontFamily: T.mono, letterSpacing: "-0.04em",
        color: color || T.text,
        opacity: loading ? 0.25 : 1, transition: "opacity 0.3s",
      }}>
        {loading ? "—" : value}
      </span>
    </div>
  );
}

/** Vertical divider between summary stats. */
function Divider() {
  return <div style={{ width: 1, background: T.border, alignSelf: "stretch", flexShrink: 0 }} />;
}
