/**
 * Root dashboard shell — Detect · Actions · Timeline tabs.
 * Implements the full DETECT → RECOMMEND → ACT agent workflow.
 */
import { useCallback, useEffect, useState } from "react";
import { useApi } from "./hooks/useApi.js";
import ActionsPanel from "./components/ActionsPanel.jsx";
import CommandBar from "./components/CommandBar.jsx";
import CorrelationView from "./components/CorrelationView.jsx";
import DashboardHeader from "./components/DashboardHeader.jsx";
import PostureOverview from "./components/PostureOverview.jsx";
import QueryConsole from "./components/QueryConsole.jsx";
import ScanTable from "./components/ScanTable.jsx";
import SourceStatus from "./components/SourceStatus.jsx";
import SqlViewer from "./components/SqlViewer.jsx";
import Timeline from "./components/Timeline.jsx";
import { T, GLOBAL_STYLES } from "./theme/tokens.js";

const DEFAULT_FILTERS = {
  ecosystem:    "PyPI",
  packages:     "django,flask,requests,celery,pillow",
  since:        "7d",
  github_owner: "",
  github_repo:  "",
};

const TABS = [
  { id: "detect",  label: "Detect",  desc: "Scan & Correlate", icon: "◈" },
  { id: "actions", label: "Actions", desc: "Approve & Act",     icon: "◉" },
  { id: "timeline",label: "Timeline",desc: "Event history",     icon: "◐" },
];

function toScanParams(f)      { return { ecosystem: f.ecosystem, packages: f.packages }; }
function toCorrelateParams(f) { return { ecosystem: f.ecosystem, packages: f.packages, since: f.since }; }
function toTimelineParams(f)  {
  return {
    since: f.since,
    ...(f.github_owner ? { github_owner: f.github_owner } : {}),
    ...(f.github_repo  ? { github_repo:  f.github_repo  } : {}),
  };
}

function getInitialTheme() {
  try { return localStorage.getItem("coral-theme") || "dark"; } catch { return "dark"; }
}

/**
 * Security command center — main application component.
 * @returns {import('react').ReactElement}
 */
export default function App() {
  const {
    loading, error, lastSql,
    getIntegrations, getPosture, getScan, getCorrelate, getTimeline,
    postAsk, postSql, connectSource, testSource, removeSource,
    getActions, approveAction, approveAllActions, dismissAction,
  } = useApi();

  const [theme, setTheme]               = useState(getInitialTheme);
  const [tab, setTab]                   = useState("detect");
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
  // Actions tab state
  const [actions, setActions]           = useState([]);
  const [actionsLoaded, setActionsLoaded] = useState(false);
  const [approving, setApproving]       = useState(null); // action id being approved

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
    try { const d = await getPosture(toScanParams(f)); setPosture(d); } catch { /* surfaced */ }
  }, [getPosture]);

  const loadScan = useCallback(async (f) => {
    try { const d = await getScan(toScanParams(f)); setScanRows(d.data || []); } catch { /* surfaced */ }
  }, [getScan]);

  const loadCorrelate = useCallback(async (f) => {
    try { const d = await getCorrelate(toCorrelateParams(f)); setCorrelateRows(d.data || []); } catch { /* surfaced */ }
  }, [getCorrelate]);

  const loadTimeline = useCallback(async (f) => {
    try { const d = await getTimeline(toTimelineParams(f)); setTimelineRows(d.data || []); } catch { /* surfaced */ }
  }, [getTimeline]);

  const loadActions = useCallback(async (f) => {
    try {
      const d = await getActions(toScanParams(f));
      setActions(d.actions || []);
      setActionsLoaded(true);
    } catch { /* surfaced */ }
  }, [getActions]);

  const refreshAll = useCallback((f) => {
    loadIntegrations(); loadPosture(f); loadScan(f); loadCorrelate(f); loadTimeline(f);
    setActionsLoaded(false); // force reload next time Actions tab opens
  }, [loadCorrelate, loadIntegrations, loadPosture, loadScan, loadTimeline]);

  // Initial load
  useEffect(() => {
    loadIntegrations(); loadPosture(DEFAULT_FILTERS); loadScan(DEFAULT_FILTERS); loadCorrelate(DEFAULT_FILTERS);
  }, [loadIntegrations, loadPosture, loadScan, loadCorrelate]);

  // Lazy-load Actions and Timeline when their tab is first opened
  useEffect(() => {
    if (tab === "actions"  && !actionsLoaded) loadActions(filters);
    if (tab === "timeline" && !timelineRows.length) loadTimeline(filters);
  }, [tab, actionsLoaded, timelineRows.length, loadActions, loadTimeline, filters]);

  const handleFilterChange = (k, v) => setFilters((c) => ({ ...c, [k]: v }));
  const handleRunScan      = async () => { setTab("detect");  await Promise.all([loadPosture(filters), loadScan(filters), loadCorrelate(filters)]); };
  const handleRunCorrelate = async () => { setTab("detect");  await loadCorrelate(filters); };
  const handleRunTimeline  = async () => { setTab("timeline"); await loadTimeline(filters); };
  const handleAsk          = async (q) => {
    try { setQueryResult(await postAsk(q)); } catch { setQueryResult(null); }
  };
  const handleSql = async (q) => {
    try { setQueryResult(await postSql(q)); } catch { setQueryResult(null); }
  };

  // Approve a single action (optimistic executing state)
  const handleApprove = async (id) => {
    setApproving(id);
    setActions((prev) => prev.map((a) => a.id === id ? { ...a, status: "executing" } : a));
    try {
      const updated = await approveAction(id);
      setActions((prev) => prev.map((a) => a.id === id ? updated : a));
    } catch {
      setActions((prev) => prev.map((a) => a.id === id ? { ...a, status: "failed" } : a));
    } finally { setApproving(null); }
  };

  // Approve all pending actions
  const handleApproveAll = async () => {
    setApproving(-1); // -1 = bulk in progress
    try {
      const d = await approveAllActions();
      setActions(d.actions || []);
    } catch { /* surfaced */ }
    finally { setApproving(null); }
  };

  // Dismiss without executing
  const handleDismiss = async (id) => {
    try {
      const updated = await dismissAction(id);
      setActions((prev) => prev.map((a) => a.id === id ? updated : a));
    } catch { /* surfaced */ }
  };

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
    setFilters(f); setTab("detect"); loadPosture(f); loadScan(f); loadCorrelate(f);
  };

  const seedQuestion = (text) => setConsoleSeed((c) => ({ id: c.id + 1, text }));

  const statusColor = loading ? T.yellow : error ? T.red : T.green;
  const statusLabel = loading ? "QUERYING" : error ? "ERROR" : "ONLINE";

  return (
    <>
      <style>{GLOBAL_STYLES}</style>
      <div style={{
        color: T.text, fontFamily: T.sans, minHeight: "100vh",
        display: "flex", flexDirection: "column",
        animation: "theme-fade 0.25s ease",
      }}>

        {/* Full-width banner */}
        <DashboardHeader theme={theme} onToggleTheme={toggleTheme} />

        {/* Sidebar + main */}
        <div style={{ flex: 1, display: "flex", minHeight: 0 }}>

          {/* Fixed sidebar */}
          <aside style={{
            position: "fixed", left: 0, top: T.bannerHeight, bottom: 0,
            width: T.sidebarWidth,
            background: `linear-gradient(180deg, var(--t-sidebar-top) 0%, var(--t-surface) 50%, var(--t-bg) 100%)`,
            borderRight: `1px solid ${T.border}`,
            display: "flex", flexDirection: "column",
            zIndex: 40,
            boxShadow: `4px 0 24px rgba(0,0,0,0.18), inset -1px 0 0 ${T.border}`,
          }}>
            <div style={{
              padding: "10px 16px", borderBottom: `1px solid ${T.border}`,
              flexShrink: 0, display: "flex", alignItems: "center", gap: 7,
            }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%",
                background: statusColor, boxShadow: `0 0 10px ${statusColor}`,
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
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
              <SourceStatus
                sources={integrations} loading={loading} busySource={busySource}
                actionMessage={busySource ? `Working on ${busySource}…` : sourceMessage}
                onConnect={(n, v) => handleSourceAction("connect", n, v)}
                onTest={(n) => handleSourceAction("test", n)}
                onRemove={(n) => handleSourceAction("remove", n)}
              />
            </div>
            <div style={{
              padding: "8px 16px", borderTop: `1px solid ${T.border}`, flexShrink: 0,
              display: "flex", justifyContent: "space-between",
              fontSize: 10, color: T.textMuted, fontFamily: T.mono,
            }}>
              <span>Coral SQL</span>
              <span>hackathon · 2026</span>
            </div>
          </aside>

          {/* Main content */}
          <div style={{ marginLeft: T.sidebarWidth, flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

            {/* Sticky tab bar */}
            <header style={{
              position: "sticky", top: T.bannerHeight, zIndex: 30,
              borderBottom: `1px solid ${T.border}`,
              background: T.frosted,
              backdropFilter: "blur(20px) saturate(1.3)",
              WebkitBackdropFilter: "blur(20px) saturate(1.3)",
              display: "flex", alignItems: "stretch", justifyContent: "space-between",
              paddingRight: 24, height: T.headerHeight, flexShrink: 0,
              boxShadow: `0 1px 0 ${T.border}, 0 4px 16px rgba(0,0,0,0.12)`,
            }}>
              <nav style={{ display: "flex" }}>
                {TABS.map((item) => {
                  const active = tab === item.id;
                  return (
                    <button key={item.id} type="button" onClick={() => setTab(item.id)} style={{
                      padding: "0 20px", height: "100%",
                      background: "transparent", border: "none",
                      borderBottom: `2px solid ${active ? T.accent : "transparent"}`,
                      color: active ? T.text : T.textMuted,
                      fontSize: 13, fontWeight: active ? 600 : 400,
                      cursor: "pointer", transition: "color 0.15s, border-color 0.15s",
                      letterSpacing: "-0.01em", fontFamily: T.sans,
                      display: "flex", alignItems: "center", gap: 7,
                    }}>
                      <span style={{ fontFamily: T.mono, fontSize: 11, color: active ? T.accent : T.textMuted }}>
                        {item.icon}
                      </span>
                      {item.label}
                    </button>
                  );
                })}
              </nav>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "5px 11px", background: T.btnBase,
                  border: `1px solid ${T.border}`, borderRadius: 8,
                }}>
                  <div style={{
                    width: 5, height: 5, borderRadius: "50%",
                    background: statusColor, boxShadow: `0 0 6px ${statusColor}`,
                    animation: loading ? "blink-dot 1.2s ease-in-out infinite" : "none",
                  }} />
                  <span style={{ fontSize: 11, color: T.textMuted, fontFamily: T.mono }}>
                    {loading ? "querying…" : error ? "coral error" : "coral · connected"}
                  </span>
                </div>
              </div>
            </header>

            {/* Page body */}
            <main style={{ padding: "22px 26px 0", display: "flex", flexDirection: "column", gap: 18, animation: "fade-in 0.3s ease" }}>
              {error && (
                <div style={{
                  padding: "10px 16px",
                  background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
                  borderLeft: `3px solid ${T.red}`, borderRadius: 10, fontSize: 13, color: T.red,
                }}>
                  {error}
                </div>
              )}

              {/* PostureOverview always visible */}
              <PostureOverview
                posture={posture} scanRows={scanRows}
                loading={loading} onRefresh={() => refreshAll(filters)}
              />

              {/* CommandBar always visible */}
              <CommandBar
                filters={filters} onChange={handleFilterChange}
                onRunScan={handleRunScan} onRunCorrelate={handleRunCorrelate}
                onRunTimeline={handleRunTimeline} onRefreshAll={() => refreshAll(filters)}
                loading={loading}
              />

              {/* Detect tab */}
              {tab === "detect" && (
                <>
                  <ScanTable
                    rows={scanRows} loading={loading}
                    onFocusPackage={focusPackage} onAskQuestion={seedQuestion}
                  />
                  <CorrelationView
                    rows={correlateRows} loading={loading}
                    onFocusPackage={focusPackage} onAskQuestion={seedQuestion}
                  />
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
                    <SqlViewer sql={lastSql} mode="detect" />
                    <QueryConsole
                      onAsk={handleAsk} onSql={handleSql}
                      loading={loading} result={queryResult} seedQuery={consoleSeed}
                      onSwitchTab={() => { setTab("actions"); if (!actionsLoaded) loadActions(filters); }}
                    />
                  </div>
                </>
              )}

              {/* Actions tab */}
              {tab === "actions" && (
                <>
                  <ActionsPanel
                    actions={actions}
                    loading={loading}
                    approving={approving}
                    onApprove={handleApprove}
                    onDismiss={handleDismiss}
                    onApproveAll={handleApproveAll}
                    onRefresh={() => { setActionsLoaded(false); loadActions(filters); }}
                  />
                  <SqlViewer sql={lastSql} mode="actions" />
                </>
              )}

              {/* Timeline tab */}
              {tab === "timeline" && (
                <Timeline
                  rows={timelineRows}
                  loading={loading}
                  onRefresh={() => loadTimeline(filters)}
                />
              )}
            </main>

            {/* Footer tagline */}
            <footer style={{
              padding: "20px 26px 24px",
              marginLeft: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <span style={{
                fontSize: 11, fontFamily: T.mono, color: T.textMuted,
                letterSpacing: "0.04em", opacity: 0.6,
              }}>
                🪸 coral reads → agent analyzes → human approves → agent acts
              </span>
            </footer>

          </div>
        </div>
      </div>
    </>
  );
}
