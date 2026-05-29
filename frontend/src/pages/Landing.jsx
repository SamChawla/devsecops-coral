/**
 * Public landing / home page. Explains the DETECT → RECOMMEND → ACT workflow,
 * the cross-source Coral SQL value prop, and routes visitors to sign up / log in.
 * Self-contained: no API calls, reuses the shared design tokens.
 */
import { Link } from "react-router-dom";
import { T, SOURCE_META, SRC_CLR } from "../theme/tokens.js";
import SiteHeader from "../components/SiteHeader.jsx";
import SiteFooter from "../components/SiteFooter.jsx";

const SAMPLE_SQL = `SELECT osv.id, osv.severity, j.key AS jira_ticket,
       se.error_count, se.level
FROM   osv.search_vulnerabilities(package => 'pillow',
                                  ecosystem => 'PyPI') osv
LEFT JOIN jira.issues   j  ON j.summary LIKE CONCAT('%', osv.id, '%')
LEFT JOIN sentry.issues se ON se.first_seen
       BETWEEN osv.published AND osv.published + INTERVAL '7 day'
ORDER BY osv.severity DESC;`;

const STEPS = [
  {
    n: "01",
    title: "Detect",
    icon: "◈",
    color: T.red,
    body: "One Coral SQL query JOINs OSV, GitHub, Jira, Sentry, and Grafana. Untracked CVEs and active exploitation surface in a single read — no ETL, no glue code.",
  },
  {
    n: "02",
    title: "Recommend",
    icon: "◉",
    color: T.accent,
    body: "The agent reads the JOIN and produces an ordered, typed action list: open a Jira ticket, draft an upgrade PR, annotate Grafana — each flagged by urgency.",
  },
  {
    n: "03",
    title: "Act",
    icon: "◐",
    color: T.green,
    body: "You approve. Only approved actions execute, via direct REST calls. Coral itself stays strictly read-only — a safe layer to point at production.",
  },
];

const SOURCES = ["osv", "github", "jira", "sentry", "grafana"];

function BriefCard() {
  return (
    <div
      style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: 16,
        padding: 18,
        boxShadow: T.shadowElevated,
        maxWidth: 460,
        width: "100%",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: T.red,
            boxShadow: `0 0 10px ${T.red}`,
            animation: "blink-dot 1.2s ease-in-out infinite",
          }}
        />
        <span style={{ fontSize: 11, fontFamily: T.mono, color: T.red, fontWeight: 700, letterSpacing: "0.08em" }}>
          ACTIVE EXPLOITATION
        </span>
        <span style={{ marginLeft: "auto", fontSize: 11, fontFamily: T.mono, color: T.textMuted }}>
          pillow · CVE
        </span>
      </div>

      <div style={{ fontSize: 14, fontWeight: 700, color: T.text, marginBottom: 6 }}>
        Heap overflow in pillow + 12 fatal Sentry errors
      </div>
      <div style={{ fontSize: 12.5, color: T.textSecondary, lineHeight: 1.6, marginBottom: 14 }}>
        Critical CVE with no Jira ticket, correlated with an error spike in the same window. The
        agent recommends opening a ticket and drafting an upgrade PR.
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          borderTop: `1px solid ${T.border}`,
          paddingTop: 12,
        }}
      >
        {[
          { c: T.red, t: "Open Jira SEC-9 — pillow CVE (urgent)" },
          { c: T.accent, t: "Draft PR — upgrade pillow 9.0.0 → 10.3.0" },
          { c: T.green, t: "Annotate Grafana incident timeline" },
        ].map((r) => (
          <div key={r.t} style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: r.c, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: T.textSecondary }}>{r.t}</span>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 14,
          fontSize: 10.5,
          fontFamily: T.mono,
          color: T.textMuted,
          letterSpacing: "0.04em",
        }}
      >
        ✓ 5 sources joined · via coral.sql
      </div>
    </div>
  );
}

export default function Landing() {
  return (
    <div style={{ minHeight: "100vh", background: T.bg, color: T.text, fontFamily: T.sans }}>
      <SiteHeader variant="landing" />

      {/* Hero */}
      <section
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          padding: "72px 28px 56px",
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 0.9fr)",
          gap: 48,
          alignItems: "center",
        }}
        className="landing-hero"
      >
        <div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 12px",
              border: `1px solid ${T.accentBorder}`,
              borderRadius: 999,
              background: T.accentGlow,
              fontSize: 11.5,
              fontWeight: 600,
              color: T.accent,
              marginBottom: 22,
              fontFamily: T.mono,
              letterSpacing: "0.02em",
            }}
          >
            🪸 Cross-stack security, powered by Coral SQL
          </div>

          <h1
            style={{
              fontSize: 48,
              lineHeight: 1.05,
              fontWeight: 850,
              letterSpacing: "-0.04em",
              margin: "0 0 18px",
            }}
          >
            From scattered alerts to{" "}
            <span style={{ color: T.accent }}>one security verdict.</span>
          </h1>

          <p
            style={{
              fontSize: 16.5,
              lineHeight: 1.6,
              color: T.textSecondary,
              maxWidth: 540,
              margin: "0 0 28px",
            }}
          >
            CoralSentinel runs a single SQL query across OSV, GitHub, Jira, Sentry, and Grafana to
            correlate vulnerabilities, deploys, and errors. The agent recommends fixes; your team
            approves; the agent acts. No tab-switching, no glue code.
          </p>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <Link
              to="/signup"
              style={{
                padding: "13px 24px",
                fontSize: 14.5,
                fontWeight: 700,
                color: "#fff",
                textDecoration: "none",
                borderRadius: 10,
                background: `linear-gradient(135deg, ${T.accent} 0%, ${T.accentHover} 100%)`,
                boxShadow: `0 0 28px ${T.accentGlow}`,
              }}
            >
              Create your workspace →
            </Link>
            <Link
              to="/login"
              style={{
                padding: "13px 24px",
                fontSize: 14.5,
                fontWeight: 600,
                color: T.text,
                textDecoration: "none",
                borderRadius: 10,
                border: `1px solid ${T.borderStrong}`,
                background: T.btnBase,
              }}
            >
              Log in
            </Link>
          </div>

          <div style={{ display: "flex", gap: 28, marginTop: 34 }}>
            {[
              { k: "5", v: "sources, one JOIN" },
              { k: "0", v: "writes without approval" },
              { k: "<90s", v: "cached cross-source reads" },
            ].map((s) => (
              <div key={s.v}>
                <div style={{ fontSize: 24, fontWeight: 800, color: T.text, letterSpacing: "-0.03em" }}>
                  {s.k}
                </div>
                <div style={{ fontSize: 12, color: T.textMuted }}>{s.v}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "center" }}>
          <BriefCard />
        </div>
      </section>

      {/* How it works */}
      <section
        id="how"
        style={{ maxWidth: 1120, margin: "0 auto", padding: "32px 28px 56px" }}
      >
        <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.12em", color: T.textMuted, textTransform: "uppercase", margin: "0 0 8px", fontFamily: T.mono }}>
          How it works
        </h2>
        <p style={{ fontSize: 22, fontWeight: 750, letterSpacing: "-0.03em", margin: "0 0 28px" }}>
          DETECT → RECOMMEND → ACT
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 18 }} className="landing-steps">
          {STEPS.map((s) => (
            <div
              key={s.n}
              style={{
                background: T.surface,
                border: `1px solid ${T.border}`,
                borderRadius: 14,
                padding: 22,
                boxShadow: T.shadowCard,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                <span
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: 9,
                    border: `1px solid ${s.color}40`,
                    background: `${s.color}14`,
                    color: s.color,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: T.mono,
                    fontSize: 15,
                  }}
                >
                  {s.icon}
                </span>
                <span style={{ fontFamily: T.mono, fontSize: 12, color: T.textMuted }}>{s.n}</span>
              </div>
              <div style={{ fontSize: 17, fontWeight: 750, marginBottom: 8, letterSpacing: "-0.02em" }}>
                {s.title}
              </div>
              <div style={{ fontSize: 13.5, lineHeight: 1.6, color: T.textSecondary }}>{s.body}</div>
            </div>
          ))}
        </div>
      </section>

      {/* SQL transparency */}
      <section style={{ maxWidth: 1120, margin: "0 auto", padding: "0 28px 56px" }}>
        <div
          style={{
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: 16,
            overflow: "hidden",
            boxShadow: T.shadowElevated,
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 0.9fr) minmax(0, 1.1fr)" }} className="landing-sql">
            <div style={{ padding: 28, borderRight: `1px solid ${T.border}` }}>
              <h2
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  letterSpacing: "0.12em",
                  color: T.textMuted,
                  textTransform: "uppercase",
                  margin: "0 0 10px",
                  fontFamily: T.mono,
                }}
              >
                Radically transparent
              </h2>
              <p style={{ fontSize: 22, fontWeight: 750, letterSpacing: "-0.03em", margin: "0 0 14px" }}>
                See the exact cross-source query.
              </p>
              <p style={{ fontSize: 14, lineHeight: 1.6, color: T.textSecondary, margin: 0 }}>
                Every result ships with the Coral SQL that produced it. No black box — the dashboard
                shows the literal 5-source JOIN so you can audit, copy, and adapt it.
              </p>
            </div>
            <div
              style={{
                background: T.codeBg,
                padding: "20px 22px",
                fontFamily: T.mono,
                fontSize: 12.5,
                lineHeight: 1.7,
                color: T.textSecondary,
                overflowX: "auto",
              }}
            >
              <pre style={{ margin: 0, whiteSpace: "pre" }}>{SAMPLE_SQL}</pre>
            </div>
          </div>
        </div>
      </section>

      {/* Sources */}
      <section id="sources" style={{ maxWidth: 1120, margin: "0 auto", padding: "0 28px 64px" }}>
        <h2 style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.12em", color: T.textMuted, textTransform: "uppercase", margin: "0 0 18px", fontFamily: T.mono, textAlign: "center" }}>
          Reads the tools you already use
        </h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "center" }}>
          {SOURCES.map((id) => {
            const meta = SOURCE_META[id];
            const color = SRC_CLR[id];
            return (
              <div
                key={id}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 9,
                  padding: "10px 16px",
                  background: `${color}12`,
                  border: `1px solid ${color}30`,
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 700,
                  color,
                }}
              >
                <span style={{ fontFamily: T.mono }}>{meta.icon}</span>
                {meta.label}
                <span style={{ fontSize: 10, color: T.textMuted, fontWeight: 500, fontFamily: T.mono }}>
                  {meta.type}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* CTA */}
      <section style={{ maxWidth: 1120, margin: "0 auto", padding: "0 28px 72px" }}>
        <div
          style={{
            background: `linear-gradient(135deg, ${T.surface} 0%, var(--t-surface-alt) 100%)`,
            border: `1px solid ${T.accentBorder}`,
            borderRadius: 18,
            padding: "44px 32px",
            textAlign: "center",
            boxShadow: T.shadowElevated,
          }}
        >
          <p style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.04em", margin: "0 0 10px" }}>
            Stand up your security command center.
          </p>
          <p style={{ fontSize: 15, color: T.textSecondary, margin: "0 0 24px" }}>
            Create an organization workspace and connect your sources in minutes.
          </p>
          <Link
            to="/signup"
            style={{
              padding: "14px 28px",
              fontSize: 15,
              fontWeight: 700,
              color: "#fff",
              textDecoration: "none",
              borderRadius: 10,
              background: `linear-gradient(135deg, ${T.accent} 0%, ${T.accentHover} 100%)`,
              boxShadow: `0 0 28px ${T.accentGlow}`,
            }}
          >
            Get started free →
          </Link>
        </div>
      </section>

      <SiteFooter />

      <style>{`
        @media (max-width: 860px) {
          .landing-hero { grid-template-columns: 1fr !important; }
          .landing-steps { grid-template-columns: 1fr !important; }
          .landing-sql { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
