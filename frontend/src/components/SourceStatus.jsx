/**
 * Sidebar source manager — lists integrations, credential forms, and connect/test/remove actions.
 */
import { useEffect, useMemo, useState } from "react";
import { T, SOURCE_META, SRC_CLR } from "../theme/tokens.js";
import { ActionButton } from "./ui/Primitives.jsx";

/**
 * Clickable row in the source list sidebar.
 * @param {{ source: object, active: boolean, onSelect: (name: string) => void }} props
 */
function SourceItem({ source, active, onSelect }) {
  const [hovered, setHovered] = useState(false);
  const name = source.name?.toLowerCase() || "";
  const meta = SOURCE_META[name] || { icon: "◉", type: "Source", label: source.name };
  const srcColor = SRC_CLR[name] || T.textMuted;
  const label = meta.label || (source.name.charAt(0).toUpperCase() + source.name.slice(1));

  return (
    <button
      type="button"
      onClick={() => onSelect(source.name)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        width: "100%", padding: "8px 10px", borderRadius: 8,
        border: `1px solid ${active ? `${srcColor}35` : hovered ? T.borderHover : "transparent"}`,
        background: active
          ? `linear-gradient(90deg, ${srcColor}12 0%, transparent 70%)`
          : hovered ? T.btnHover : "transparent",
        color: T.text, textAlign: "left", cursor: "pointer",
        transition: "all 0.15s",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span style={{
            fontSize: 13, color: source.connected ? srcColor : T.textMuted,
            fontFamily: T.mono, width: 18, textAlign: "center",
            textShadow: source.connected ? `0 0 10px ${srcColor}88` : "none",
            transition: "color 0.3s, text-shadow 0.3s",
          }}>
            {meta.icon}
          </span>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: active ? T.text : T.textSecondary }}>{label}</div>
            <div style={{ fontSize: 10, color: T.textMuted, marginTop: 1, fontFamily: T.mono }}>
              {source.kind} · {source.table_count || 0}t
            </div>
          </div>
        </div>

        {/* Status dot */}
        <div style={{
          width: 7, height: 7, borderRadius: "50%", flexShrink: 0,
          background: source.connected ? srcColor : T.borderStrong,
          boxShadow: source.connected ? `0 0 8px ${srcColor}, 0 0 16px ${srcColor}44` : "none",
          animation: source.connected ? "none" : "blink-dot 2.5s ease-in-out infinite",
          transition: "background 0.3s, box-shadow 0.3s",
        }} />
      </div>
    </button>
  );
}

/**
 * Coral data source connection panel for the dashboard sidebar.
 * @param {{ sources: Array<object>, loading: boolean, busySource: string, actionMessage: string, onConnect: Function, onTest: Function, onRemove: Function }} props
 */
export default function SourceStatus({ sources, loading, busySource, actionMessage, onConnect, onTest, onRemove }) {
  const list = sources || [];
  const connectedCount = list.filter((s) => s.connected).length;
  const [selectedName, setSelectedName] = useState(list[0]?.name || "");
  const [formValues, setFormValues] = useState({});

  useEffect(() => {
    if (!list.some((s) => s.name === selectedName)) setSelectedName(list[0]?.name || "");
  }, [list, selectedName]);

  const selected = useMemo(
    () => list.find((s) => s.name === selectedName) || list[0] || null,
    [list, selectedName],
  );

  useEffect(() => {
    if (!selected) { setFormValues({}); return; }
    const next = {};
    selected.inputs?.forEach((inp) => { next[inp.key] = inp.default || ""; });
    setFormValues(next);
  }, [selected]);

  const submit = () => selected && onConnect(selected.name, formValues);

  const selectedSrcColor = SRC_CLR[selected?.name?.toLowerCase()] || T.accent;
  const allConnected = list.length > 0 && connectedCount === list.length;

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      {/* Header */}
      <div style={{ padding: "11px 12px 9px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.12em", color: T.textMuted }}>
            Data Sources
          </span>
          <span style={{
            fontSize: 11, fontWeight: 700, fontFamily: T.mono,
            color: allConnected ? T.green : connectedCount > 0 ? T.yellow : T.textMuted,
          }}>
            {connectedCount}/{list.length}
          </span>
        </div>

        {/* Connectivity bar */}
        {list.length > 0 && (
          <div style={{ display: "flex", gap: 3, marginTop: 7 }}>
            {list.map((s) => {
              const c = SRC_CLR[s.name?.toLowerCase()] || T.textMuted;
              return (
                <div key={s.name} title={s.name} style={{
                  flex: 1, height: 3, borderRadius: 2,
                  background: s.connected ? c : T.border,
                  boxShadow: s.connected ? `0 0 6px ${c}88` : "none",
                  transition: "background 0.3s, box-shadow 0.3s",
                }} />
              );
            })}
          </div>
        )}
      </div>

      {/* Source list */}
      <div style={{ padding: "5px", overflowY: "auto", flex: "0 0 auto", maxHeight: 220 }}>
        {loading && !list.length ? (
          <div style={{ padding: "20px 12px", color: T.textMuted, fontSize: 12 }}>Loading sources…</div>
        ) : (
          list.map((s) => (
            <SourceItem key={s.name} source={s} active={s.name === selected?.name} onSelect={setSelectedName} />
          ))
        )}
      </div>

      {/* Selected source detail */}
      {selected && (
        <div style={{
          flex: 1,
          borderTop: `1px solid ${T.border}`,
          padding: "12px 12px",
          display: "flex", flexDirection: "column", gap: 10,
          overflowY: "auto",
          background: `linear-gradient(180deg, ${selectedSrcColor}05 0%, transparent 40%)`,
        }}>
          {/* Name + docs link */}
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                <div style={{
                  width: 7, height: 7, borderRadius: "50%",
                  background: selected.connected ? selectedSrcColor : T.borderStrong,
                  boxShadow: selected.connected ? `0 0 8px ${selectedSrcColor}` : "none",
                  flexShrink: 0,
                }} />
                <div style={{ fontSize: 12, fontWeight: 700, color: T.text }}>
                  {selected.name.charAt(0).toUpperCase() + selected.name.slice(1)}
                </div>
              </div>
              {selected.description && (
                <div style={{ fontSize: 11, color: T.textMuted, lineHeight: 1.5, paddingLeft: 13 }}>
                  {selected.description}
                </div>
              )}
            </div>
            {selected.docs_url && (
              <a href={selected.docs_url} target="_blank" rel="noreferrer" style={{
                fontSize: 11, color: T.accent, textDecoration: "none", fontWeight: 600, flexShrink: 0,
              }}>
                Docs ↗
              </a>
            )}
          </div>

          {/* Credential inputs */}
          {selected.inputs?.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {selected.inputs.map((inp) => (
                <label key={inp.key} style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                  <span style={{ fontSize: 10, color: T.textMuted, fontWeight: 700, letterSpacing: "0.06em" }}>
                    {inp.label}{inp.required ? " *" : ""}
                  </span>
                  <input
                    type={inp.secret ? "password" : "text"}
                    value={formValues[inp.key] || ""}
                    placeholder={inp.placeholder || inp.default || ""}
                    onChange={(e) => setFormValues((c) => ({ ...c, [inp.key]: e.target.value }))}
                    style={{
                      padding: "7px 10px",
                      background: T.inputBg,
                      border: `1px solid ${T.border}`,
                      borderRadius: 7,
                      color: T.text,
                      fontSize: 12,
                      outline: "none",
                      fontFamily: T.sans,
                      width: "100%",
                    }}
                  />
                  {inp.help_text && <span style={{ fontSize: 10, color: T.textMuted }}>{inp.help_text}</span>}
                </label>
              ))}
            </div>
          ) : (
            <div style={{
              fontSize: 11, color: T.green,
              padding: "7px 10px",
              background: "rgba(16,185,129,0.06)",
              border: "1px solid rgba(16,185,129,0.18)",
              borderRadius: 8,
            }}>
              No credentials needed — connect directly.
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            <ActionButton
              tone="accent"
              onClick={submit}
              disabled={loading || busySource === selected.name}
              style={{ width: "100%", justifyContent: "center" }}
            >
              {selected.connected ? "↻ Update connection" : "Connect source"}
            </ActionButton>
            <div style={{ display: "flex", gap: 5 }}>
              <ActionButton
                onClick={() => onTest(selected.name)}
                disabled={loading || busySource === selected.name || !selected.connected}
                style={{ flex: 1, justifyContent: "center" }}
              >
                Test
              </ActionButton>
              <ActionButton
                tone="danger"
                onClick={() => onRemove(selected.name)}
                disabled={loading || busySource === selected.name || !selected.connected}
                style={{ flex: 1, justifyContent: "center" }}
              >
                Remove
              </ActionButton>
            </div>
          </div>

          {/* Status message */}
          {actionMessage && (
            <div style={{
              fontSize: 11, color: T.textSecondary,
              padding: "7px 10px",
              background: "rgba(59,130,246,0.06)",
              border: "1px solid rgba(59,130,246,0.16)",
              borderRadius: 8, lineHeight: 1.5,
            }}>
              {actionMessage}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
