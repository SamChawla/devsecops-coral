/**
 * Lightweight Coral SQL tokenizer for syntax highlighting.
 *
 * Shared by SqlViewer and the Query Console SQL tab so both render the
 * generated cross-source query with identical colors.
 */

const TOKENS = [
  { re: /\b(SELECT|FROM|LEFT JOIN|JOIN|INNER JOIN|WHERE|ORDER BY|GROUP BY|HAVING|UNION ALL|AND|OR|ON|AS|LIMIT|OFFSET|DISTINCT|CASE|WHEN|THEN|ELSE|END)\b/, color: "#60a5fa" },
  { re: /\b(osv|github|sentry|jira|grafana|coral|slack|notion)\b/,                                                                                           color: "#f97316" },
  { re: /\b(search_vulnerabilities|vulnerability_detail|issues|pulls|events|alerts|tables|columns|table_functions)\b/,                                        color: "#a78bfa" },
  { re: /'[^']*'/,                                                                                                                                             color: "#34d399" },
  { re: /--.*$/,                                                                                                                                               color: "#64748b" },
  { re: /\b(\d+)\b/,                                                                                                                                           color: "#fbbf24" },
];

/**
 * Split a single SQL line into colored segments.
 * @param {string} line - One line of SQL.
 * @returns {{ text: string, color: string|null }[]} Ordered highlight segments.
 */
export function tokenizeSql(line) {
  if (!line.trim()) return [{ text: line, color: null }];
  const segments = [];
  let remaining = line;
  let safety = 0;
  while (remaining.length > 0 && safety++ < 500) {
    let earliest = null;
    let earliestIndex = Infinity;
    let earliestMatch = null;
    for (const tok of TOKENS) {
      const m = tok.re.exec(remaining);
      if (m && m.index < earliestIndex) {
        earliest = tok;
        earliestIndex = m.index;
        earliestMatch = m;
      }
    }
    if (!earliest) {
      segments.push({ text: remaining, color: null });
      break;
    }
    if (earliestIndex > 0) segments.push({ text: remaining.slice(0, earliestIndex), color: null });
    segments.push({ text: earliestMatch[0], color: earliest.color });
    remaining = remaining.slice(earliestIndex + earliestMatch[0].length);
  }
  return segments;
}
