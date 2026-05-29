/**
 * Syntax-highlighted SQL code block with line numbers.
 *
 * Pure presentation — wrap it in a Card/header where needed. Used by both
 * SqlViewer and the Query Console's "Coral SQL" tab.
 */
import { T } from "../../theme/tokens.js";
import { tokenizeSql } from "../../utils/sqlTokens.js";

/**
 * @param {{ text: string, maxHeight?: number, padded?: boolean }} props
 *   - text: SQL source to render.
 *   - maxHeight: scroll cap in px (default 360).
 *   - padded: add vertical padding (default true).
 */
export default function SqlCode({ text, maxHeight = 360, padded = true }) {
  const lines = (text || "").split("\n");
  return (
    <pre
      style={{
        margin: 0,
        padding: padded ? "14px 0" : 0,
        fontSize: 12,
        lineHeight: 1.75,
        fontFamily: T.mono,
        overflowX: "auto",
        maxHeight,
        overflowY: "auto",
        background: T.codeBg,
      }}
    >
      {lines.map((line, lineIdx) => {
        const segments = tokenizeSql(line);
        return (
          <div key={lineIdx} style={{ display: "flex", minHeight: "1.75em" }}>
            <span
              style={{
                display: "inline-block",
                width: 44,
                textAlign: "right",
                paddingRight: 16,
                color: T.textMuted,
                fontSize: 10,
                userSelect: "none",
                flexShrink: 0,
                opacity: 0.5,
              }}
            >
              {lineIdx + 1}
            </span>
            <span>
              {segments.map((seg, si) => (
                <span key={si} style={{ color: seg.color || T.textSecondary }}>
                  {seg.text}
                </span>
              ))}
            </span>
          </div>
        );
      })}
    </pre>
  );
}
