/**
 * Security-related GitHub Pull Requests panel.
 *
 * Lists remediation PRs (upgrades / patches / CVE fixes) from Coral's
 * `github.pulls` table, each linking out to the PR on github.com.
 */
import { memo, useEffect, useMemo, useState } from "react";
import { T } from "../theme/tokens.js";
import { mapGithubPrRows } from "../utils/mapData.js";
import { ActionButton, Card, CardHeader, EmptyState, Pill } from "./ui/Primitives.jsx";

export default memo(GithubPrs);

const PAGE_SIZE = 6;

const STATE_META = {
  merged: { label: "MERGED", color: T.purple },
  open:   { label: "OPEN",   color: T.green },
  closed: { label: "CLOSED", color: T.textMuted },
};

/** One PR row with a clickable title and state pill. */
function PrRow({ pr }) {
  const meta = STATE_META[pr.state] || STATE_META.open;
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "10px 12px", borderRadius: 8,
      background: "rgba(255,255,255,0.02)",
      border: `1px solid ${T.border}`,
      borderLeft: `3px solid ${meta.color}66`,
    }}>
      <span style={{
        fontFamily: T.mono, fontSize: 11, color: T.textMuted, flexShrink: 0, paddingTop: 2,
      }}>
        {pr.number != null ? `#${pr.number}` : "—"}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {pr.url ? (
            <a
              href={pr.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 13, fontWeight: 600, color: T.text, textDecoration: "none" }}
              title="Open this pull request on GitHub"
              onMouseEnter={(e) => { e.currentTarget.style.textDecoration = "underline"; }}
              onMouseLeave={(e) => { e.currentTarget.style.textDecoration = "none"; }}
            >
              {pr.title} <span style={{ color: T.purple, fontSize: 11 }}>↗</span>
            </a>
          ) : (
            <span style={{ fontSize: 13, fontWeight: 600, color: T.text }}>{pr.title}</span>
          )}
        </div>
        <div style={{ marginTop: 3, fontSize: 11, color: T.textMuted, fontFamily: T.mono, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <span>@{pr.author}</span>
          {pr.merged ? <span>merged {pr.merged}</span> : null}
        </div>
      </div>
      <span style={{
        fontSize: 9, fontWeight: 800, letterSpacing: "0.06em",
        color: meta.color, background: `${meta.color}1c`,
        border: `1px solid ${meta.color}40`,
        padding: "2px 7px", borderRadius: 999, flexShrink: 0,
        fontFamily: T.mono,
      }}>
        {meta.label}
      </span>
    </div>
  );
}

/**
 * GitHub PRs panel — security remediation pull requests.
 * @param {{ rows: Array<object>, loading: boolean, onRefresh?: Function }} props
 */
function GithubPrs({ rows, loading, onRefresh }) {
  const [page, setPage] = useState(0);
  const data = useMemo(() => mapGithubPrRows(rows), [rows]);

  useEffect(() => { setPage(0); }, [rows]);

  const merged = data.filter((p) => p.state === "merged").length;
  const open   = data.filter((p) => p.state === "open").length;
  const totalPages = Math.max(1, Math.ceil(data.length / PAGE_SIZE));
  const pageData   = data.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <Card accent={T.purple}>
      <CardHeader
        title="GitHub Pull Requests · Security"
        accent={T.purple}
        right={
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <Pill color={T.purple}>{merged} merged</Pill>
            <Pill color={T.green}>{open} open</Pill>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
              {loading ? "loading…" : `${data.length} PRs`}
            </span>
            {onRefresh ? (
              <ActionButton onClick={onRefresh} disabled={loading} style={{ padding: "5px 10px", fontSize: 11 }}>
                ↻ Refresh
              </ActionButton>
            ) : null}
          </div>
        }
      />

      {loading && !data.length ? (
        <EmptyState message="Loading security pull requests…" icon="◌" />
      ) : !data.length ? (
        <EmptyState
          message="No security-related PRs found. Connect GitHub and set GITHUB_OWNER/GITHUB_REPO, then Refresh."
          icon="🔀"
        />
      ) : (
        <>
          <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8, maxHeight: 420, overflowY: "auto" }}>
            {pageData.map((pr, idx) => (
              <PrRow key={`${pr.number}-${idx}`} pr={pr} />
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", borderTop: `1px solid ${T.border}`, gap: 10 }}>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>{page + 1}/{totalPages} · {data.length} PRs</span>
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
