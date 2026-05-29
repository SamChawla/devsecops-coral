/**
 * Minimal, dependency-free Markdown renderer.
 *
 * Supports the subset the agent analysis emits: headings, bold/italic,
 * inline code, ordered/unordered lists, GFM tables, horizontal rules, and
 * paragraphs. Styled with the dashboard theme tokens. Intentionally small —
 * we avoid pulling in react-markdown to keep the bundle lean.
 */
import { T } from "../../theme/tokens.js";

const INLINE_RE = /(\*\*([^*]+)\*\*|`([^`]+)`|\*([^*\n]+)\*)/g;

/** Inline code chip styling shared across renderers. */
const codeStyle = {
  fontFamily: T.mono,
  fontSize: "0.85em",
  color: T.accent,
  background: "rgba(255,107,53,0.1)",
  border: "1px solid rgba(255,107,53,0.18)",
  borderRadius: 4,
  padding: "1px 5px",
  whiteSpace: "nowrap",
};

/**
 * Render inline markdown (bold, italic, code) into React nodes.
 * @param {string} text
 * @param {string} keyPrefix - Unique key namespace for the produced nodes.
 * @returns {Array<import('react').ReactNode>}
 */
function renderInline(text, keyPrefix) {
  const nodes = [];
  let lastIndex = 0;
  let match;
  let i = 0;
  INLINE_RE.lastIndex = 0;
  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    if (match[2] !== undefined) {
      nodes.push(
        <strong key={`${keyPrefix}-b-${i}`} style={{ color: T.text, fontWeight: 700 }}>
          {match[2]}
        </strong>,
      );
    } else if (match[3] !== undefined) {
      nodes.push(
        <code key={`${keyPrefix}-c-${i}`} style={codeStyle}>
          {match[3]}
        </code>,
      );
    } else if (match[4] !== undefined) {
      nodes.push(
        <em key={`${keyPrefix}-i-${i}`} style={{ color: T.textSecondary }}>
          {match[4]}
        </em>,
      );
    }
    lastIndex = INLINE_RE.lastIndex;
    i += 1;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

/** Split a markdown table row into trimmed cells. */
function splitRow(row) {
  return row
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

const isSeparator = (line) =>
  line != null && /^\s*\|?[\s:|-]+\|?\s*$/.test(line) && line.includes("-");

/**
 * Parse markdown text into a flat list of block descriptors.
 * @param {string} md
 * @returns {Array<object>}
 */
function parseBlocks(md) {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      i += 1;
      continue;
    }
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(line.trim())) {
      blocks.push({ type: "hr" });
      i += 1;
      continue;
    }
    if (line.trim().startsWith("|") && isSeparator(lines[i + 1])) {
      const header = splitRow(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        rows.push(splitRow(lines[i]));
        i += 1;
      }
      blocks.push({ type: "table", header, rows });
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }
    const para = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,6})\s+/.test(lines[i]) &&
      !/^(-{3,}|\*{3,}|_{3,})$/.test(lines[i].trim()) &&
      !lines[i].trim().startsWith("|") &&
      !/^\s*([-*]|\d+\.)\s+/.test(lines[i])
    ) {
      para.push(lines[i]);
      i += 1;
    }
    blocks.push({ type: "p", text: para.join(" ") });
  }
  return blocks;
}

const HEADING_SIZE = { 1: 18, 2: 16, 3: 14, 4: 13, 5: 12, 6: 12 };

/**
 * Render agent/markdown text with dashboard styling.
 * @param {{ text: string }} props
 */
export default function Markdown({ text }) {
  const blocks = parseBlocks(text || "");
  return (
    <div style={{ fontSize: 13, color: T.textSecondary, lineHeight: 1.7 }}>
      {blocks.map((block, bi) => {
        const key = `blk-${bi}`;
        if (block.type === "heading") {
          return (
            <div
              key={key}
              style={{
                fontSize: HEADING_SIZE[block.level] || 13,
                fontWeight: 700,
                color: T.text,
                margin: bi === 0 ? "0 0 8px" : "16px 0 8px",
                letterSpacing: "-0.01em",
              }}
            >
              {renderInline(block.text, key)}
            </div>
          );
        }
        if (block.type === "hr") {
          return (
            <div
              key={key}
              style={{ height: 1, background: T.border, margin: "14px 0", opacity: 0.7 }}
            />
          );
        }
        if (block.type === "list") {
          const Tag = block.ordered ? "ol" : "ul";
          return (
            <Tag
              key={key}
              style={{ margin: "4px 0 10px", paddingLeft: 22, display: "flex", flexDirection: "column", gap: 4 }}
            >
              {block.items.map((item, ii) => (
                <li key={`${key}-${ii}`} style={{ lineHeight: 1.6 }}>
                  {renderInline(item, `${key}-${ii}`)}
                </li>
              ))}
            </Tag>
          );
        }
        if (block.type === "table") {
          return (
            <div
              key={key}
              style={{
                margin: "8px 0 12px",
                overflowX: "auto",
                border: `1px solid ${T.border}`,
                borderRadius: 8,
              }}
            >
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ background: T.surfaceAlt }}>
                    {block.header.map((cell, ci) => (
                      <th
                        key={`${key}-h-${ci}`}
                        style={{
                          padding: "7px 11px",
                          textAlign: "left",
                          color: T.textMuted,
                          fontWeight: 700,
                          borderBottom: `1px solid ${T.border}`,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {renderInline(cell, `${key}-h-${ci}`)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, ri) => (
                    <tr key={`${key}-r-${ri}`} style={{ borderBottom: `1px solid ${T.border}` }}>
                      {row.map((cell, ci) => (
                        <td
                          key={`${key}-r-${ri}-${ci}`}
                          style={{ padding: "6px 11px", color: T.textSecondary, verticalAlign: "top" }}
                        >
                          {renderInline(cell, `${key}-r-${ri}-${ci}`)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return (
          <p key={key} style={{ margin: "0 0 10px" }}>
            {renderInline(block.text, key)}
          </p>
        );
      })}
    </div>
  );
}
