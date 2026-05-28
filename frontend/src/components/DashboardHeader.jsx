/**
 * Full-width dashboard banner with branding, source chips, and theme toggle.
 */
import { T } from "../theme/tokens.js";

const SOURCES = [
  { label: "GitHub",  color: "#8b5cf6", icon: "◉" },
  { label: "Sentry",  color: "#f97316", icon: "◎" },
  { label: "Jira",    color: "#3b82f6", icon: "◆" },
  { label: "Grafana", color: "#10b981", icon: "◐" },
  { label: "OSV",     color: "#ef4444", icon: "◈" },
];

/** Source badge shown in the dashboard header. */
function SourceChip({ label, color, icon }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "4px 10px",
      background: `${color}12`,
      border: `1px solid ${color}30`,
      borderRadius: 6,
      fontSize: 11, fontWeight: 600,
      color,
      letterSpacing: "-0.01em",
      whiteSpace: "nowrap",
    }}>
      <span style={{ fontFamily: T.mono, fontSize: 10 }}>{icon}</span>
      {label}
    </span>
  );
}

/**
 * Top banner with product title, connected source chips, and dark/light toggle.
 * @param {{ theme: string, onToggleTheme: Function }} props
 */
export default function DashboardHeader({ theme, onToggleTheme }) {
  return (
    <div style={{
      background: T.surface,
      borderBottom: `1px solid ${T.border}`,
      padding: "0 28px",
      height: T.bannerHeight,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: 24,
      flexShrink: 0,
      boxShadow: T.shadowCard,
      position: "sticky",
      top: 0,
      zIndex: 50,
      overflow: "hidden",
    }}>
      {/* Accent glow in top-left */}
      <div style={{
        position: "absolute", top: 0, left: 0,
        width: 300, height: "100%",
        background: `linear-gradient(90deg, ${T.accentGlow} 0%, transparent 80%)`,
        pointerEvents: "none",
      }} />

      {/* Left: name + category */}
      <div style={{ display: "flex", alignItems: "center", gap: 20, position: "relative", zIndex: 1 }}>
        {/* Logo mark */}
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `linear-gradient(135deg, ${T.accent} 0%, #ff8555 100%)`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, fontWeight: 900, color: "#fff",
          boxShadow: `0 0 20px ${T.accentGlow}, 0 2px 8px rgba(0,0,0,0.3)`,
          flexShrink: 0,
          fontFamily: T.mono,
        }}>
          ◈
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <span style={{
              fontSize: 17, fontWeight: 800,
              letterSpacing: "-0.04em",
              color: T.text,
            }}>
              Coral<span style={{ color: T.accent }}>Sentinel</span>
            </span>
            <span style={{
              fontSize: 9, fontWeight: 700, textTransform: "uppercase",
              letterSpacing: "0.1em", color: T.textMuted,
              padding: "2px 7px",
              border: `1px solid ${T.border}`,
              borderRadius: 4,
              fontFamily: T.mono,
            }}>
              v0.1
            </span>
          </div>
          <div style={{
            fontSize: 11, color: T.textSecondary,
            marginTop: 1, letterSpacing: "-0.01em",
          }}>
            Security &amp; Compliance Monitor
          </div>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 32, background: T.border, flexShrink: 0 }} />

        {/* Source chips */}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {SOURCES.map((s) => <SourceChip key={s.label} {...s} />)}
        </div>
      </div>

      {/* Right: tagline + theme toggle */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16,
        position: "relative", zIndex: 1, flexShrink: 0,
      }}>
        <div style={{
          fontSize: 11, color: T.textMuted,
          maxWidth: 280, lineHeight: 1.5,
          textAlign: "right",
          display: "none", // hidden on narrow viewports via media query fallback
        }}
          className="header-tagline"
        >
          Surfaces risky access changes &amp; secrets in commits.
          Cross-references CVE databases and internal policy docs.
        </div>

        {/* Dark / Light toggle */}
        <button
          type="button"
          onClick={onToggleTheme}
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          style={{
            display: "flex", alignItems: "center", gap: 7,
            padding: "7px 13px",
            background: T.btnBase,
            border: `1px solid ${T.border}`,
            borderRadius: 8,
            color: T.textSecondary,
            fontSize: 12, fontWeight: 600,
            cursor: "pointer",
            transition: "all 0.15s",
            fontFamily: T.sans,
            whiteSpace: "nowrap",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = T.btnHover;
            e.currentTarget.style.borderColor = T.borderHover;
            e.currentTarget.style.color = T.text;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = T.btnBase;
            e.currentTarget.style.borderColor = T.border;
            e.currentTarget.style.color = T.textSecondary;
          }}
        >
          <span style={{ fontSize: 14 }}>{theme === "dark" ? "☀" : "☾"}</span>
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </div>
    </div>
  );
}
