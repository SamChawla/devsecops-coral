/**
 * Root dashboard shell — orchestrates tabs, filters, source management, and API data loading.
 */
import { useCallback, useEffect, useState } from "react";
import { useApi } from "./hooks/useApi.js";
import DashboardHeader from "./components/DashboardHeader.jsx";
import CommandBar from "./components/CommandBar.jsx";
import SourceStatus from "./components/SourceStatus.jsx";
import PostureOverview from "./components/PostureOverview.jsx";
import ScanTable from "./components/ScanTable.jsx";
import CorrelationView from "./components/CorrelationView.jsx";
import Timeline from "./components/Timeline.jsx";
import QueryConsole from "./components/QueryConsole.jsx";
import SqlViewer from "./components/SqlViewer.jsx";
import { T, GLOBAL_STYLES } from "./theme/tokens.js";

const DEFAULT_FILTERS = {
  ecosystem: "PyPI",
  packages:  "django,flask,requests,celery",
  since:     "7d",
  github_owner: "",
  github_repo:  "",
};

const TABS = [
  { id: "scan",      label: "Vulnerability Scan", icon: "◈" },
  { id: "correlate", label: "Correlate",          icon: "◎" },
  { id: "timeline",  label: "Timeline",           icon: "◐" },
];

/** Build query params for GET /api/scan and /api/posture. */
function toScanParams(f)      { return { ecosystem: f.ecosystem, packages: f.packages }; }
/** Build query params for GET /api/correlate. */
function toCorrelateParams(f) { return { ecosystem: f.ecosystem, packages: f.packages, since: f.since }; }
/** Build query params for GET /api/timeline. */
function toTimelineParams(f)  {
  return {
    since: f.since,
    ...(f.github_owner ? { github_owner: f.github_owner } : {}),
    ...(f.github_repo  ? { github_repo:  f.github_repo  } : {}),
  };
}

/** Read persisted theme preference from localStorage. */
function getInitialTheme() {
  try { return localStorage.getItem("coral-theme") || "dark"; } catch { return "dark"; }
}

/**
 * Security command center dashboard — main application component.
 * @returns {import('react').ReactElement}
 */
export default function App() {
  const {
    loading, error, lastSql,
    getIntegrations, getPosture, getScan, getCorrelate, getTimeline,
    postAsk, postSql, connectSource, testSource, removeSource,
  } = useApi();

  const [theme, setTheme]               = useState(getInitialTheme);
  const [tab, setTab]                   = useState("scan");
  const [time, setTime]                 = useState(new Date());
  const [filters, setFilters]           = useState(DEFAULT_FILTERS);
  const [integrations, setIntegrations] = useState([]);
  const [posture, setPosture]           = useState(null);
  const [scanRows, setScanRows]         = useState([]);
  const [correlateRows, setCorrelateRows] = useState([]);
  const [timelineRows, setTimelineRows] = useState([]);
  const [queryResult, setQueryResult]   = useState(null);
  const [consoleSeed, setConsoleSeed]   = useState({ id: 0, text: "" });
  const [sourceMessage, setSourceMessage] = useState("");
  const [busySource, setBusySource]     = useState("");

  /* Apply theme to <html> element so CSS vars activate */
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("coral-theme", theme); } catch { /* ignore */ }
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const loadIntegrations = useCallback(async () => {
    try { const d = await getIntegrations(); setIntegrations(d.integrations || []); } catch { /* surfaced via useApi */ }
  }, [getIntegrations]);

  const loadPosture = useCallback(async (f) => {
    try { const d = await getPosture(toScanParams(f)); setPosture(d); } catch { /* surfaced via useApi */ }
  }, [getPosture]);

  const loadScan = useCallback(async (f) => {
    try { const d = await getScan(toScanParams(f)); setScanRows(d.data || []); } catch { /* surfaced via useApi */ }
  }, [getScan]);

  const loadCorrelate = useCallback(async (f) => {
    try { const d = await getCorrelate(toCorrelateParams(f)); setCorrelateRows(d.data || []); } catch { /* surfaced via useApi */ }
  }, [getCorrelate]);

  const loadTimeline = useCallback(async (f) => {
    try { const d = await getTimeline(toTimelineParams(f)); setTimelineRows(d.data || []); } catch { /* surfaced via useApi */ }
  }, [getTimeline]);

  const refreshAll = useCallback((f) => {
    loadIntegrations(); loadPosture(f); loadScan(f); loadCorrelate(f); loadTimeline(f);
  }, [loadCorrelate, loadIntegrations, loadPosture, loadScan, loadTimeline]);

  useEffect(() => {
    loadIntegrations(); loadPosture(DEFAULT_FILTERS); loadScan(DEFAULT_FILTERS);
  }, [loadIntegrations, loadPosture, loadScan]);

  useEffect(() => {
    if (tab === "correlate" && !correlateRows.length) loadCorrelate(filters);
    if (tab === "timeline"  && !timelineRows.length)  loadTimeline(filters);
  }, [tab, correlateRows.length, timelineRows.length, loadCorrelate, loadTimeline, filters]);

  const handleFilterChange = (k, v) => setFilters((c) => ({ ...c, [k]: v }));
  const handleRunScan      = async () => { setTab("scan");      await Promise.all([loadPosture(filters), loadScan(filters)]); };
  const handleRunCorrelate = async () => { setTab("correlate"); await loadCorrelate(filters); };
  const handleRunTimeline  = async () => { setTab("timeline");  await loadTimeline(filters); };
  const handleAsk          = async (q) => { try { setQueryResult(await postAsk(q)); } catch { setQueryResult(null); } };
  const handleSql          = async (q) => { try { setQueryResult(await postSql(q)); } catch { setQueryResult(null); } };

  const handleSourceAction = async (action, name, values = {}) => {
    try {
      setBusySource(name); setSourceMessage("");
      const res = action === "connect"
        ? await connectSource(name, values)
        : action === "test"
          ? await testSource(name)
          : await removeSource(name);
      setSourceMessage(res.message);
      await loadIntegrations();
    } finally { setBusySource(""); }
  };

  const focusPackage = (pkg) => {
    const f = { ...filters, packages: pkg };
    setFilters(f); setTab("scan"); loadPosture(f); loadScan(f);
  };

  const seedQuestion = (text) => setConsoleSeed((c) => ({ id: c.id + 1, text }));

  const statusColor = loading ? T.yellow : error ? T.red : T.green;
  const statusLabel = loading ? "QUERYING" : error ? "ERROR" : "ONLINE";

  return (
    <>
      <style>{GLOBAL_STYLES}</style>

      {/* Full-height shell */}
      <div style={{
        color: T.text, fontFamily: T.sans, minHeight: "100vh",
        display: "flex", flexDirection: "column",
        animation: "theme-fade 0.25s ease",
      }}>

        {/* ── Full-width banner (spans sidebar + main) ─────────────── */}
        <DashboardHeader theme={theme} onToggleTheme={toggleTheme} />

        {/* ── Below-banner: sidebar + main side by side ───────────── */}
        <div style={{ flex: 1, display: "flex", minHeight: 0 }}>

          {/* ── Fixed sidebar ──────────────────────────────────────── */}
          <aside style={{
            position: "fixed",
            left: 0,
            top: T.bannerHeight,    // start below the banner
            bottom: 0,
            width: T.sidebarWidth,
            background: `linear-gradient(180deg, var(--t-sidebar-top) 0%, var(--t-surface) 50%, var(--t-bg) 100%)`,
            borderRight: `1px solid ${T.border}`,
            display: "flex", flexDirection: "column",
            zIndex: 40,
            boxShadow: `4px 0 24px rgba(0,0,0,0.18), inset -1px 0 0 ${T.border}`,
          }}>

            {/* Status row */}
            <div style={{
              padding: "10px 16px",
              borderBottom: `1px solid ${T.border}`,
              flexShrink: 0,
              display: "flex", alignItems: "center", gap: 7,
            }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%",
                background: statusColor,
                boxShadow: `0 0 10px ${statusColor}`,
                animation: loading ? "blink-dot 1.2s ease-in-out infinite" : "none",
                flexShrink: 0,
              }} />
              <span style={{ fontSize: 10, color: statusColor, fontFamily: T.mono, fontWeight: 700, letterSpacing: "0.08em" }}>
                {statusLabel}
              </span>
              <span style={{ fontSize: 10, color: T.textMuted, fontFamily: T.mono, marginLeft: "auto" }}>
                {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            </div>

            {/* Source manager */}
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
              <SourceStatus
                sources={integrations}
                loading={loading}
                busySource={busySource}
                actionMessage={busySource ? `Working on ${busySource}…` : sourceMessage}
                onConnect={(n, v) => handleSourceAction("connect", n, v)}
                onTest={(n) => handleSourceAction("test", n)}
                onRemove={(n) => handleSourceAction("remove", n)}
              />
            </div>

            {/* Bottom tag */}
            <div style={{
              padding: "8px 16px",
              borderTop: `1px solid ${T.border}`,
              flexShrink: 0,
              display: "flex", justifyContent: "space-between",
              fontSize: 10, color: T.textMuted, fontFamily: T.mono,
            }}>
              <span>Coral SQL</span>
              <span>hackathon · 2026</span>
            </div>
          </aside>

          {/* ── Main content ──────────────────────────────────────── */}
          <div style={{
            marginLeft: T.sidebarWidth,
            flex: 1,
            display: "flex", flexDirection: "column",
            minWidth: 0,
          }}>

            {/* Sticky tab bar */}
            <header style={{
              position: "sticky", top: T.bannerHeight, zIndex: 30,
              borderBottom: `1px solid ${T.border}`,
              background: T.frosted,
              backdropFilter: "blur(20px) saturate(1.3)",
              WebkitBackdropFilter: "blur(20px) saturate(1.3)",
              display: "flex", alignItems: "stretch",
              justifyContent: "space-between",
              paddingRight: 24,
              height: T.headerHeight,
              flexShrink: 0,
              boxShadow: `0 1px 0 ${T.border}, 0 4px 16px rgba(0,0,0,0.12)`,
            }}>
              <nav style={{ display: "flex" }}>
                {TABS.map((item) => {
                  const active = tab === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setTab(item.id)}
                      style={{
                        padding: "0 20px",
                        height: "100%",
                        background: "transparent",
                        border: "none",
                        borderBottom: `2px solid ${active ? T.accent : "transparent"}`,
                        color: active ? T.text : T.textMuted,
                        fontSize: 13,
                        fontWeight: active ? 600 : 400,
                        cursor: "pointer",
                        transition: "color 0.15s, border-color 0.15s",
                        letterSpacing: "-0.01em",
                        fontFamily: T.sans,
                        display: "flex", alignItems: "center", gap: 7,
                      }}
                    >
                      <span style={{ fontFamily: T.mono, fontSize: 11, color: active ? T.accent : T.textMuted }}>
                        {item.icon}
                      </span>
                      {item.label}
                    </button>
                  );
                })}
              </nav>

              {/* Coral status chip */}
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "5px 11px",
                  background: T.btnBase,
                  border: `1px solid ${T.border}`,
                  borderRadius: 8,
                }}>
                  <div style={{
                    width: 5, height: 5, borderRadius: "50%",
                    background: statusColor,
                    boxShadow: `0 0 6px ${statusColor}`,
                    animation: loading ? "blink-dot 1.2s ease-in-out infinite" : "none",
                  }} />
                  <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
                    {loading ? "querying…" : error ? "coral error" : "coral · connected"}
                  </span>
                </div>
              </div>
            </header>

            {/* Page body */}
            <main style={{
              padding: "22px 26px 48px",
              display: "flex", flexDirection: "column", gap: 18,
              animation: "fade-in 0.3s ease",
            }}>
              {error ? (
                <div style={{
                  padding: "10px 16px",
                  background: "rgba(239,68,68,0.06)",
                  border: "1px solid rgba(239,68,68,0.2)",
                  borderLeft: `3px solid ${T.red}`,
                  borderRadius: 10,
                  fontSize: 13, color: T.red,
                }}>
                  {error}
                </div>
              ) : null}

              <PostureOverview
                posture={posture}
                scanRows={scanRows}
                loading={loading}
                onRefresh={() => refreshAll(filters)}
              />

              <CommandBar
                filters={filters}
                onChange={handleFilterChange}
                onRunScan={handleRunScan}
                onRunCorrelate={handleRunCorrelate}
                onRunTimeline={handleRunTimeline}
                onRefreshAll={() => refreshAll(filters)}
                loading={loading}
              />

              {tab === "scan"      && <ScanTable       rows={scanRows}      loading={loading} onFocusPackage={focusPackage} onAskQuestion={seedQuestion} />}
              {tab === "correlate" && <CorrelationView  rows={correlateRows} loading={loading} onFocusPackage={focusPackage} onAskQuestion={seedQuestion} />}
              {tab === "timeline"  && <Timeline         rows={timelineRows}  loading={loading} />}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
                <SqlViewer sql={lastSql} />
                <QueryConsole onAsk={handleAsk} onSql={handleSql} loading={loading} result={queryResult} seedQuery={consoleSeed} />
              </div>
            </main>
          </div>
        </div>
      </div>
    </>
  );
}
