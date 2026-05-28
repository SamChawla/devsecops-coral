/**
 * Design tokens for CoralSentinel — Security & Compliance Monitor.
 *
 * Theme-sensitive values (bg, surface, border, text) reference CSS custom
 * properties defined in globals.css so a single data-theme attribute on
 * <html> flips the whole palette with zero JS re-renders.
 *
 * Fixed values (severity colors, accent, typography) are plain hex strings
 * and never change between themes.
 */

/* Theme-sensitive tokens (CSS vars) */
export const T = {
  // Backgrounds
  bg:           "var(--t-bg)",
  surface:      "var(--t-surface)",
  surfaceAlt:   "var(--t-surface-alt)",
  surfaceHover: "var(--t-surface-hover)",
  surfaceMid:   "var(--t-surface-mid)",

  // Frosted / overlay / code
  frosted:  "var(--t-frosted)",
  codeBg:   "var(--t-code-bg)",
  cardDim:  "var(--t-card-dim)",
  inputBg:  "var(--t-input-bg)",

  // Sidebar gradient stops
  sidebarTop: "var(--t-sidebar-top)",
  sidebarBot: "var(--t-sidebar-bot)",

  // Borders
  border:       "var(--t-border)",
  borderHover:  "var(--t-border-hover)",
  borderStrong: "var(--t-border-strong)",

  // Text
  text:          "var(--t-text)",
  textSecondary: "var(--t-text-secondary)",
  textMuted:     "var(--t-text-muted)",

  // Button base backgrounds
  btnBase:  "var(--t-btn-base)",
  btnHover: "var(--t-btn-hover)",

  // Shadows
  shadowCard:     "var(--t-shadow-card)",
  shadowElevated: "var(--t-shadow-elevated)",

  // Fixed tokens (same in all themes)

  // Accent — orange ember
  accent:       "#ff6b35",
  accentHover:  "#ff8555",
  accentGlow:   "rgba(255,107,53,0.15)",
  accentBorder: "rgba(255,107,53,0.35)",

  // Semantic colors
  green:  "#10b981",
  red:    "#ef4444",
  orange: "#f97316",
  yellow: "#eab308",
  blue:   "#3b82f6",
  purple: "#8b5cf6",
  cyan:   "#06b6d4",

  // Typography
  mono: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
  sans: "'Inter', system-ui, -apple-system, sans-serif",

  // Layout
  sidebarWidth: 280,
  headerHeight: 52,
  bannerHeight: 68,   // DashboardHeader strip height
};

/* Severity palette (fixed) */
export const SEV = {
  CRITICAL: {
    bg:        "rgba(239,68,68,0.08)",
    text:      "#ef4444",
    border:    "rgba(239,68,68,0.22)",
    glow:      "rgba(239,68,68,0.18)",
    glowStrong:"0 0 40px rgba(239,68,68,0.25), 0 0 80px rgba(239,68,68,0.1)",
  },
  HIGH: {
    bg:        "rgba(249,115,22,0.08)",
    text:      "#f97316",
    border:    "rgba(249,115,22,0.22)",
    glow:      "rgba(249,115,22,0.14)",
    glowStrong:"0 0 40px rgba(249,115,22,0.2), 0 0 80px rgba(249,115,22,0.08)",
  },
  MEDIUM: {
    bg:        "rgba(234,179,8,0.07)",
    text:      "#eab308",
    border:    "rgba(234,179,8,0.22)",
    glow:      "rgba(234,179,8,0.12)",
    glowStrong:"0 0 40px rgba(234,179,8,0.18), 0 0 80px rgba(234,179,8,0.07)",
  },
  LOW: {
    bg:        "rgba(16,185,129,0.07)",
    text:      "#10b981",
    border:    "rgba(16,185,129,0.22)",
    glow:      "rgba(16,185,129,0.1)",
    glowStrong:"0 0 40px rgba(16,185,129,0.15), 0 0 80px rgba(16,185,129,0.06)",
  },
  INFO: {
    bg:        "rgba(59,130,246,0.07)",
    text:      "#3b82f6",
    border:    "rgba(59,130,246,0.22)",
    glow:      "rgba(59,130,246,0.1)",
    glowStrong:"0 0 40px rgba(59,130,246,0.15), 0 0 80px rgba(59,130,246,0.06)",
  },
  UNKNOWN: {
    bg:        "rgba(148,163,184,0.04)",
    text:      "#64748b",
    border:    "rgba(148,163,184,0.12)",
    glow:      "transparent",
    glowStrong:"none",
  },
};

/* Source brand colors (fixed) */
export const SRC_CLR = {
  osv:     "#ef4444",
  github:  "#8b5cf6",
  sentry:  "#f97316",
  jira:    "#3b82f6",
  grafana: "#10b981",
  slack:   "#e01e5a",
  notion:  "#64748b",
};

export const SOURCE_META = {
  osv:     { icon: "◈", type: "Custom Spec", label: "OSV" },
  github:  { icon: "◉", type: "Bundled",     label: "GitHub" },
  sentry:  { icon: "◎", type: "Bundled",     label: "Sentry" },
  jira:    { icon: "◆", type: "Bundled",     label: "Jira" },
  grafana: { icon: "◐", type: "Bundled",     label: "Grafana" },
};

/* Global keyframe CSS (injected once by App.jsx) */
export const GLOBAL_STYLES = `
  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3), 0 0 20px rgba(239,68,68,0.1); }
    50%       { box-shadow: 0 0 0 8px rgba(239,68,68,0), 0 0 40px rgba(239,68,68,0.2); }
  }
  @keyframes blink-dot {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.25; }
  }
  @keyframes fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes counter-glow {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.88; }
  }
  @keyframes border-pulse {
    0%, 100% { border-color: rgba(239,68,68,0.22); }
    50%       { border-color: rgba(239,68,68,0.52); }
  }
  @keyframes theme-fade {
    from { opacity: 0.7; }
    to   { opacity: 1; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; }
`;
