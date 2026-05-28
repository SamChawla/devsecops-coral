/**
 * Paginated vulnerability scan table with severity filters.
 */
import { useEffect, useMemo, useState } from "react";
import { T, SEV } from "../theme/tokens.js";
import { mapScanRows } from "../utils/mapData.js";
import { ActionButton, Badge, Card, CardHeader, EmptyState, Pill } from "./ui/Primitives.jsx";

const PAGE_SIZE = 12;

const SEV_FILTERS = ["all", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
const SEV_COLORS  = { CRITICAL: T.red, HIGH: T.orange, MEDIUM: T.yellow, LOW: T.green };

const COL = {
  th: {
    padding: "10px 14px", textAlign: "left", fontSize: 10,
    textTransform: "uppercase", letterSpacing: "0.1em", color: T.textMuted,
    fontWeight: 700, borderBottom: `1px solid ${T.border}`,
    background: T.surfaceAlt,
    position: "sticky", top: 0, zIndex: 1, whiteSpace: "nowrap",
  },
};

/** Severity filter toggle button. */
function SevButton({ value, active, onClick }) {
  const color = value === "all" ? T.textSecondary : SEV_COLORS[value];
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: "4px 10px",
        borderRadius: 6,
        border: `1px solid ${active ? (color || T.accentBorder) : T.border}`,
        background: active ? `${color || T.accent}18` : T.btnBase,
        color: active ? (color || T.accent) : T.textMuted,
        fontSize: 10, fontWeight: 700,
        cursor: "pointer",
        transition: "all 0.12s",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        fontFamily: T.mono,
        whiteSpace: "nowrap",
      }}
    >
      {value === "all" ? "All" : value}
    </button>
  );
}

/** Single scan result row with drill-down actions. */
function TableRow({ row, index, onFocusPackage, onAskQuestion }) {
  const [hovered, setHovered] = useState(false);

  return (
    <tr
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ background: hovered ? T.surfaceHover : index % 2 === 0 ? "transparent" : "rgba(255,255,255,0.012)", transition: "background 0.12s" }}
    >
      <td style={{ padding: "10px 14px", fontFamily: T.mono, fontSize: 11, color: T.accent, whiteSpace: "nowrap", borderBottom: `1px solid ${T.border}` }}>
        {row.id}
      </td>
      <td style={{ padding: "10px 14px", fontWeight: 600, whiteSpace: "nowrap", borderBottom: `1px solid ${T.border}` }}>
        {row.pkg}
      </td>
      <td style={{ padding: "10px 14px", borderBottom: `1px solid ${T.border}` }}>
        <Badge severity={row.sev} />
      </td>
      <td style={{ padding: "10px 14px", color: T.textSecondary, maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 12, borderBottom: `1px solid ${T.border}` }} title={row.sum}>
        {row.sum}
      </td>
      <td style={{ padding: "10px 14px", fontFamily: T.mono, fontSize: 11, color: T.textMuted, borderBottom: `1px solid ${T.border}` }}>
        {row.ticket || <span style={{ opacity: 0.3 }}>—</span>}
      </td>
      <td style={{ padding: "10px 14px", borderBottom: `1px solid ${T.border}` }}>
        <span style={{
          display: "inline-block", padding: "2px 10px", borderRadius: 999, fontSize: 10, fontWeight: 700,
          background: row.status === "UNTRACKED" ? "rgba(249,115,22,0.1)" : "rgba(16,185,129,0.1)",
          border: `1px solid ${row.status === "UNTRACKED" ? "rgba(249,115,22,0.25)" : "rgba(16,185,129,0.25)"}`,
          color: row.status === "UNTRACKED" ? T.orange : T.green,
        }}>
          {row.status}
        </span>
      </td>
      <td style={{ padding: "10px 14px", fontFamily: T.mono, fontSize: 12, borderBottom: `1px solid ${T.border}`, color: row.errs > 10 ? T.red : row.errs > 0 ? T.orange : T.textMuted }}>
        {row.errs > 0 ? row.errs : <span style={{ opacity: 0.3 }}>—</span>}
      </td>
      <td style={{ padding: "10px 14px", borderBottom: `1px solid ${T.border}`, minWidth: 200 }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <ActionButton
            onClick={() => onFocusPackage(row.pkg)}
            disabled={row.pkg === "-"}
            style={{ padding: "5px 10px", fontSize: 11 }}
            title="Re-run scan scoped to this package only"
          >
            Focus
          </ActionButton>
          <ActionButton
            onClick={() => onAskQuestion(`What should I investigate first for ${row.id} in ${row.pkg}?`)}
            disabled={row.id === "-"}
            style={{ padding: "5px 10px", fontSize: 11 }}
            title="Pre-fills the Query Console below with a targeted question — then click Execute"
          >
            Ask AI
          </ActionButton>
          {row.id !== "-" ? (
            <a href={`https://osv.dev/vulnerability/${encodeURIComponent(row.id)}`} target="_blank" rel="noreferrer" style={{
              padding: "5px 10px", borderRadius: 8, border: `1px solid ${T.border}`,
              color: T.accent, textDecoration: "none", fontSize: 11, fontWeight: 600,
            }}>
              OSV ↗
            </a>
          ) : null}
        </div>
      </td>
    </tr>
  );
}

/**
 * Vulnerability scan results table.
 * @param {{ rows: Array<object>, loading: boolean, onFocusPackage: Function, onAskQuestion: Function }} props
 */
export default function ScanTable({ rows, loading, onFocusPackage, onAskQuestion }) {
  const [page, setPage]               = useState(0);
  const [statusFilter, setStatusFilter] = useState("all");
  const [sevFilter, setSevFilter]     = useState("all");
  const [search, setSearch]           = useState("");

  const data = mapScanRows(rows);

  useEffect(() => { setPage(0); }, [rows, statusFilter, sevFilter, search]);

  const filtered = useMemo(() => {
    let d = data;
    if (statusFilter === "untracked") d = d.filter((r) => r.status === "UNTRACKED");
    else if (statusFilter === "tracked") d = d.filter((r) => r.status !== "UNTRACKED");
    if (sevFilter !== "all") d = d.filter((r) => r.sev === sevFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      d = d.filter((r) => r.id.toLowerCase().includes(q) || r.pkg.toLowerCase().includes(q));
    }
    return d;
  }, [data, statusFilter, sevFilter, search]);

  const totalPages   = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageData     = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const untrackedCount = data.filter((r) => r.status === "UNTRACKED").length;

  return (
    <Card>
      <CardHeader
        title="Vulnerability Scan Results"
        right={
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            {untrackedCount > 0 ? <Pill color={T.orange}>{untrackedCount} untracked</Pill> : null}
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
              {loading
                ? "scanning…"
                : filtered.length < data.length
                  ? `${filtered.length} / ${data.length} CVEs`
                  : `${data.length} CVEs`}
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
        {/* Status filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ fontSize: 9, color: T.textMuted, fontFamily: T.mono, textTransform: "uppercase", letterSpacing: "0.08em", marginRight: 2 }}>Status</span>
          {[["all", "All"], ["untracked", "Untracked"], ["tracked", "Tracked"]].map(([id, label]) => (
            <ActionButton key={id} active={statusFilter === id} onClick={() => setStatusFilter(id)} style={{ padding: "4px 10px", fontSize: 10 }}>
              {label}
            </ActionButton>
          ))}
        </div>

        <div style={{ width: 1, height: 20, background: T.border, flexShrink: 0 }} />

        {/* Severity filter */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ fontSize: 9, color: T.textMuted, fontFamily: T.mono, textTransform: "uppercase", letterSpacing: "0.08em", marginRight: 2 }}>Severity</span>
          {SEV_FILTERS.map((v) => (
            <SevButton key={v} value={v} active={sevFilter === v} onClick={() => setSevFilter(v)} />
          ))}
        </div>

        <div style={{ width: 1, height: 20, background: T.border, flexShrink: 0 }} />

        {/* Search */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flex: "1 1 160px", minWidth: 140 }}>
          <span style={{ fontSize: 12, color: T.textMuted, flexShrink: 0 }}>🔍</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="CVE ID or package…"
            style={{
              flex: 1,
              padding: "4px 9px",
              background: T.inputBg,
              border: `1px solid ${search ? T.borderHover : T.border}`,
              borderRadius: 6,
              color: T.text,
              fontSize: 11,
              outline: "none",
              fontFamily: T.mono,
            }}
          />
          {search ? (
            <button
              type="button"
              onClick={() => setSearch("")}
              style={{ background: "none", border: "none", color: T.textMuted, cursor: "pointer", fontSize: 13, padding: 0, lineHeight: 1 }}
            >
              ×
            </button>
          ) : null}
        </div>
      </div>

      {loading && !data.length ? (
        <EmptyState message="Running vulnerability scan…" icon="◌" />
      ) : !filtered.length ? (
        <EmptyState message="No vulnerabilities match the current filters." />
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <div style={{ maxHeight: 460, overflowY: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    {["CVE ID", "Package", "Severity", "Summary", "Ticket", "Status", "Errors", "Actions"].map((h) => (
                      <th key={h} style={COL.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pageData.map((row, idx) => (
                    <TableRow key={`${row.id}-${idx}`} row={row} index={idx} onFocusPackage={onFocusPackage} onAskQuestion={onAskQuestion} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", borderTop: `1px solid ${T.border}`, gap: 12 }}>
            <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
              {page + 1}/{totalPages} · {filtered.length < data.length ? `${filtered.length} of ${data.length}` : filtered.length} CVEs
            </span>
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
