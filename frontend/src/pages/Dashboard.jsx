/**
 * Authenticated dashboard shell — Detect · Actions · Timeline tabs.
 * Implements the full DETECT → RECOMMEND → ACT agent workflow.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useApi } from "../hooks/useApi.js";
import { useTheme } from "../theme/ThemeContext.jsx";
import ActionsPanel from "../components/ActionsPanel.jsx";
import Clock from "../components/Clock.jsx";
import CommandBar from "../components/CommandBar.jsx";
import CorrelationView from "../components/CorrelationView.jsx";
import DashboardHeader from "../components/DashboardHeader.jsx";
import GithubPrs from "../components/GithubPrs.jsx";
import PostureOverview from "../components/PostureOverview.jsx";
import QueryConsole from "../components/QueryConsole.jsx";
import ScanTable from "../components/ScanTable.jsx";
import SourceStatus from "../components/SourceStatus.jsx";
import SqlViewer from "../components/SqlViewer.jsx";
import Timeline from "../components/Timeline.jsx";
import { T } from "../theme/tokens.js";

const DEFAULT_FILTERS = {
  ecosystem:    "PyPI",
  packages:     "django,requests,pillow,celery",
  since:        "1d",
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
function toPrParams(f) {
  return {
    since: "90d",
    ...(f.github_owner ? { github_owner: f.github_owner } : {}),
    ...(f.github_repo  ? { github_repo:  f.github_repo  } : {}),
  };
}

// `refresh` busts the backend Coral cache so explicit Refresh / Run buttons force
// fresh reads. Passive navigation and initial load omit it, so they reuse cached
// results (the Actions tab reuses the Detect tab's scan/correlate reads).
function withRefresh(params, refresh) { return refresh ? { ...params, refresh: 1 } : params; }

/**
 * Security command center — main application component.
 * @returns {import('react').ReactElement}
 */
export default function Dashboard() {
  const {
    loading, error, lastSql,
    getIntegrations, getPosture, getScan, getCorrelate, getTimeline, getGithubPrs,
    postAsk, postSql, postRootCause, connectSource, testSource, removeSource,
    getActions, approveAction, approveAllActions, dismissAction,
  } = useApi();
  const { theme, toggleTheme } = useTheme();

  const [tab, setTab]                   = useState("detect");
  const [filters, setFilters]           = useState(DEFAULT_FILTERS);
  const [integrations, setIntegrations] = useState([]);
  const [posture, setPosture]           = useState(null);
  const [scanRows, setScanRows]         = useState([]);
  const [correlateRows, setCorrelateRows] = useState([]);
  const [timelineRows, setTimelineRows] = useState([]);
  const [prRows, setPrRows]             = useState([]);
  const [queryResult, setQueryResult]   = useState(null);
  const [consoleSeed, setConsoleSeed]   = useState({ id: 0, text: "" });
  const [sourceMessage, setSourceMessage] = useState("");
  const [busySource, setBusySource]     = useState("");
  const queryConsoleRef                 = useRef(null);
  // Actions tab state
  const [actions, setActions]           = useState([]);
  const [actionsLoaded, setActionsLoaded]   = useState(false);
  const [timelineLoaded, setTimelineLoaded] = useState(false);
  const [approving, setApproving]           = useState(null); // action id being approved

  const loadIntegrations = useCallback(async () => {
    try { const d = await getIntegrations(); setIntegrations(d.integrations || []); } catch { /* surfaced via useApi */ }
  }, [getIntegrations]);

  const loadPosture = useCallback(async (f, { refresh = false } = {}) => {
    try { const d = await getPosture(withRefresh(toScanParams(f), refresh)); setPosture(d); } catch { /* surfaced */ }
  }, [getPosture]);

  const loadScan = useCallback(async (f, { refresh = false } = {}) => {
    try { const d = await getScan(withRefresh(toScanParams(f), refresh)); setScanRows(d.data || []); } catch { /* surfaced */ }
  }, [getScan]);

  const loadCorrelate = useCallback(async (f, { refresh = false } = {}) => {
    try { const d = await getCorrelate(withRefresh(toCorrelateParams(f), refresh)); setCorrelateRows(d.data || []); } catch { /* surfaced */ }
  }, [getCorrelate]);

  const loadGithubPrs = useCallback(async (f, { refresh = false } = {}) => {
    try { const d = await getGithubPrs(withRefresh(toPrParams(f), refresh)); setPrRows(d.data || []); } catch { /* surfaced */ }
  }, [getGithubPrs]);

  const loadTimeline = useCallback(async (f, { refresh = false } = {}) => {
    try { const d = await getTimeline(withRefresh(toTimelineParams(f), refresh)); setTimelineRows(d.data || []); } catch { /* surfaced */ }
    finally { setTimelineLoaded(true); }
  }, [getTimeline]);

  const loadActions = useCallback(async (f, { refresh = false } = {}) => {
    try {
      const d = await getActions(withRefresh(toScanParams(f), refresh));
      setActions(d.actions || []);
      setActionsLoaded(true);
    } catch { /* surfaced */ }
  }, [getActions]);

  const refreshAll = useCallback((f) => {
    loadIntegrations();
    loadPosture(f, { refresh: true });
    loadScan(f, { refresh: true });
    loadCorrelate(f, { refresh: true });
    loadGithubPrs(f, { refresh: true });
    loadTimeline(f, { refresh: true });
    setActionsLoaded(false);
    setTimelineLoaded(false);
  }, [loadCorrelate, loadGithubPrs, loadIntegrations, loadPosture, loadScan, loadTimeline]);

  // Initial load — guarded so React StrictMode's dev double-invoke doesn't fetch twice.
  const didInit = useRef(false);
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;
    loadIntegrations(); loadPosture(DEFAULT_FILTERS); loadScan(DEFAULT_FILTERS); loadCorrelate(DEFAULT_FILTERS); loadGithubPrs(DEFAULT_FILTERS);
  }, [loadIntegrations, loadPosture, loadScan, loadCorrelate, loadGithubPrs]);

  // Lazy-load Actions and Timeline once — use loaded flags to avoid re-fetching
  useEffect(() => {
    if (tab === "actions"  && !actionsLoaded)  loadActions(filters);
    if (tab === "timeline" && !timelineLoaded) loadTimeline(filters);
  }, [tab, actionsLoaded, timelineLoaded, loadActions, loadTimeline, filters]);

  const handleFilterChange = (k, v) => setFilters((c) => ({ ...c, [k]: v }));
  const handleRunScan      = async () => { setTab("detect");  await Promise.all([loadPosture(filters, { refresh: true }), loadScan(filters, { refresh: true }), loadCorrelate(filters, { refresh: true }), loadGithubPrs(filters, { refresh: true })]); };
  const handleRunCorrelate = async () => { setTab("detect");  await loadCorrelate(filters, { refresh: true }); };
  const handleRunTimeline  = async () => { setTab("timeline"); await loadTimeline(filters, { refresh: true }); };
  const handleAsk          = async (q) => {
    try { setQueryResult(await postAsk(q)); } catch { setQueryResult(null); }
  };
  const handleSql = async (q) => {
    try { setQueryResult(await postSql(q)); } catch { setQueryResult(null); }
  };
  const handleRootCause = async (row) => {
    const cve = row?.cve && row.cve !== "-" ? row.cve : undefined;
    const pkg = row?.pkg && row.pkg !== "-" ? row.pkg : undefined;
    if (!pkg) return;
    setTimeout(() => queryConsoleRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }), 50);
    try {
      setQueryResult(await postRootCause({ cve, package: pkg, ecosystem: filters.ecosystem, since: filters.since }));
    } catch { setQueryResult(null); }
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

  const seedQuestion = (text) => {
    setConsoleSeed((c) => ({ id: c.id + 1, text }));
    setTimeout(() => {
      queryConsoleRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  };

  const statusColor = loading ? T.yellow : error ? T.red : T.green;
  const statusLabel = loading ? "QUERYING" : error ? "ERROR" : "ONLINE";

  return (
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
            <Clock />
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
                  onRootCause={handleRootCause}
                />
                <GithubPrs
                  rows={prRows} loading={loading}
                  onRefresh={() => loadGithubPrs(filters, { refresh: true })}
                />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
                  <SqlViewer sql={lastSql} mode="detect" />
                  <div ref={queryConsoleRef}>
                    <QueryConsole
                      onAsk={handleAsk} onSql={handleSql}
                      loading={loading} result={queryResult} seedQuery={consoleSeed}
                      onSwitchTab={() => { setTab("actions"); if (!actionsLoaded) loadActions(filters); }}
                    />
                  </div>
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
                  onRefresh={() => { setActionsLoaded(false); loadActions(filters, { refresh: true }); }}
                />
                <SqlViewer sql={lastSql} mode="actions" />
              </>
            )}

            {/* Timeline tab */}
            {tab === "timeline" && (
              <Timeline
                rows={timelineRows}
                loading={loading}
                onRefresh={() => { setTimelineLoaded(false); loadTimeline(filters, { refresh: true }); }}
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
  );
}
