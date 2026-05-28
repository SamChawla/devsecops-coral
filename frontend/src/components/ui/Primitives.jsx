/**
 * Shared UI primitives — badges, cards, buttons, and typography helpers.
 */
import { useState } from "react";
import { T, SEV } from "../../theme/tokens.js";

/** Severity-colored badge for CVE/signal labels. */
export function Badge({ severity }) {
  const key = (severity || "UNKNOWN").toUpperCase();
  const s = SEV[key] || SEV.UNKNOWN;
  return (
    <span style={{
      background: s.bg,
      color: s.text,
      border: `1px solid ${s.border}`,
      boxShadow: `0 0 8px ${s.glow}`,
      padding: "2px 8px",
      borderRadius: 4,
      fontSize: 10, fontWeight: 700, letterSpacing: "0.06em",
      fontFamily: T.mono, whiteSpace: "nowrap",
    }}>
      {key}
    </span>
  );
}

/** Rounded pill label with optional accent color. */
export function Pill({ children, color = T.textMuted }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "3px 10px", borderRadius: 999,
      background: `${color}14`, border: `1px solid ${color}30`,
      fontSize: 11, color, fontWeight: 600, whiteSpace: "nowrap",
      letterSpacing: "-0.01em",
    }}>
      {children}
    </span>
  );
}

/** Elevated surface container with optional accent border and glow. */
export function Card({ children, style, accent, flat, glow }) {
  return (
    <div style={{
      background: flat ? "transparent" : T.surface,
      border: `1px solid ${accent ? `${accent}28` : T.border}`,
      borderRadius: 14,
      overflow: "hidden",
      boxShadow: glow
        ? `0 0 40px ${glow}22, ${T.shadowElevated}`
        : accent
          ? `0 0 28px ${accent}10, ${T.shadowCard}`
          : T.shadowCard,
      ...style,
    }}>
      {children}
    </div>
  );
}

/** Card title row with optional right-side actions. */
export function CardHeader({ title, right, accent }) {
  return (
    <div style={{
      padding: "11px 16px",
      borderBottom: `1px solid ${T.border}`,
      display: "flex", justifyContent: "space-between", alignItems: "center",
      gap: 12,
      background: accent
        ? `linear-gradient(90deg, ${accent}08 0%, transparent 60%)`
        : `linear-gradient(90deg, ${T.accentGlow.replace("0.15", "0.03")} 0%, transparent 60%)`,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 3, height: 14, borderRadius: 2,
          background: accent || T.accent,
          boxShadow: `0 0 8px ${accent || T.accent}`,
          flexShrink: 0,
        }} />
        <span style={{
          fontSize: 11, fontWeight: 700, textTransform: "uppercase",
          letterSpacing: "0.1em", color: T.textMuted,
        }}>
          {title}
        </span>
      </div>
      {right}
    </div>
  );
}

/** Centered placeholder when a data panel has no rows. */
export function EmptyState({ message, icon }) {
  return (
    <div style={{
      padding: "48px 24px", textAlign: "center", color: T.textMuted, fontSize: 13,
      display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
    }}>
      {icon ? <div style={{ fontSize: 28, opacity: 0.3, fontFamily: T.mono }}>{icon}</div> : null}
      <div style={{ maxWidth: 280, lineHeight: 1.6 }}>{message}</div>
    </div>
  );
}

/** Styled button with default, accent, and danger tone variants. */
export function ActionButton({
  children, onClick, disabled = false, active = false,
  tone = "default", style, title, type = "button",
}) {
  const [hovered, setHovered] = useState(false);

  const palettes = {
    default: {
      border:     active ? T.accentBorder : hovered ? T.borderHover : T.border,
      background: active ? T.accentGlow   : hovered ? T.btnHover    : T.btnBase,
      color:      active ? T.accent       : disabled ? T.textMuted  : hovered ? T.text : T.textSecondary,
      shadow:     active ? `0 0 12px ${T.accentGlow}` : "none",
    },
    accent: {
      border:     "transparent",
      background: disabled ? "rgba(255,107,53,0.4)" : hovered ? T.accentHover : T.accent,
      color:      "#fff",
      shadow:     hovered && !disabled ? "0 0 18px rgba(255,107,53,0.35)" : "none",
    },
    danger: {
      border:     hovered ? "rgba(239,68,68,0.45)" : "rgba(239,68,68,0.2)",
      background: hovered ? "rgba(239,68,68,0.12)" : "rgba(239,68,68,0.05)",
      color:      disabled ? T.textMuted : T.red,
      shadow:     "none",
    },
  };
  const p = palettes[tone] || palettes.default;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: "7px 13px",
        borderRadius: 8,
        border: `1px solid ${p.border}`,
        background: p.background,
        color: p.color,
        boxShadow: p.shadow,
        fontSize: 12, fontWeight: 600,
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "all 0.15s ease",
        fontFamily: T.sans, lineHeight: 1,
        whiteSpace: "nowrap",
        display: "inline-flex", alignItems: "center", gap: 6,
        ...style,
      }}
    >
      {children}
    </button>
  );
}

/** Uppercase section heading label. */
export function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 700, textTransform: "uppercase",
      letterSpacing: "0.12em", color: T.textMuted, marginBottom: 10,
    }}>
      {children}
    </div>
  );
}

/** Inline monospace text span for IDs, SQL fragments, and timestamps. */
export function Mono({ children, color }) {
  return (
    <span style={{
      fontFamily: T.mono, fontSize: "0.88em",
      color: color || T.textSecondary,
      background: T.btnBase,
      border: `1px solid ${T.border}`,
      borderRadius: 4, padding: "1px 6px",
    }}>
      {children}
    </span>
  );
}
