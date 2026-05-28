/** Map API response rows to dashboard display shapes */

/**
 * Normalize scan API rows for ScanTable rendering.
 * @param {Array<object>} rows - Raw /api/scan data rows.
 * @returns {Array<object>} Display-shaped scan rows.
 */
export function mapScanRows(rows) {
  return (rows || []).map((row) => {
    const untracked = row.cve && !row.jira_ticket;
    return {
      id: row.cve || "-",
      pkg: row.package || "-",
      sev: (row.severity || "UNKNOWN").toUpperCase(),
      sum: row.summary || "-",
      ticket: row.jira_ticket || null,
      status: untracked ? "UNTRACKED" : row.jira_status || (row.cve ? "Tracked" : "Clean"),
      errs: row.error_count ?? 0,
    };
  });
}

/**
 * Normalize correlate API rows for CorrelationView rendering.
 * @param {Array<object>} rows - Raw /api/correlate data rows.
 * @returns {Array<object>} Display-shaped correlation rows.
 */
export function mapCorrelateRows(rows) {
  return (rows || []).map((row) => ({
    cve: row.cve || "-",
    pkg: row.package || "-",
    sev: (row.severity || "UNKNOWN").toUpperCase(),
    errs: row.error_count ?? 0,
    errLvl: row.error_level || "-",
    sig: row.signal || "unknown",
    pr: row.pr_title || null,
    author: row.author || null,
    summary: row.summary || row.error_title || "",
  }));
}

const SENTRY_LEVEL_TO_SEV = {
  fatal: "CRITICAL",
  error: "HIGH",
  warning: "MEDIUM",
  info: "INFO",
  debug: "LOW",
};
const JIRA_PRIORITY_TO_SEV = {
  highest: "CRITICAL",
  high: "HIGH",
  medium: "MEDIUM",
  low: "LOW",
  lowest: "LOW",
};

/**
 * Normalize timeline API rows for Timeline rendering.
 * @param {Array<object>} rows - Raw /api/timeline data rows.
 * @returns {Array<object>} Display-shaped timeline events.
 */
export function mapTimelineRows(rows) {
  return (rows || []).map((row) => {
    let ts = "-";
    if (row.event_time) {
      const date = new Date(row.event_time);
      ts = Number.isNaN(date.getTime())
        ? String(row.event_time).slice(11, 16) || String(row.event_time).slice(0, 5)
        : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }
    const src = (row.source || "unknown").toLowerCase();
    const detail = row.detail ? ` - ${row.detail}` : "";

    let sev = "INFO";
    if (row.severity) {
      const raw = row.severity.toUpperCase();
      if (["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].includes(raw)) {
        sev = raw;
      } else {
        sev =
          SENTRY_LEVEL_TO_SEV[row.severity.toLowerCase()] ||
          JIRA_PRIORITY_TO_SEV[row.severity.toLowerCase()] ||
          "INFO";
      }
    } else if (src === "sentry" && row.detail) {
      sev = SENTRY_LEVEL_TO_SEV[row.detail.toLowerCase()] || "HIGH";
    }

    return {
      ts,
      src,
      evt: `${row.title || row.event_type || "event"}${detail}`,
      sev,
    };
  });
}

/**
 * Build posture KPI counts from API posture payload or scan rows fallback.
 * @param {object|null} posture - /api/posture response.
 * @param {Array<object>} scanRows - Raw scan rows used when posture is absent.
 * @returns {{ counts: object, total: number, untracked: number }}
 */
export function postureFromApi(posture, scanRows) {
  if (posture) {
    return {
      counts: {
        CRITICAL: posture.critical ?? 0,
        HIGH: posture.high ?? 0,
        MEDIUM: posture.medium ?? 0,
        LOW: posture.low ?? 0,
      },
      total: posture.total ?? 0,
      untracked: posture.untracked ?? 0,
    };
  }
  const mapped = mapScanRows(scanRows);
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  mapped.forEach((row) => {
    if (counts[row.sev] !== undefined && row.id !== "-") counts[row.sev] += 1;
  });
  return {
    counts,
    total: mapped.filter((row) => row.id !== "-").length,
    untracked: mapped.filter((row) => row.status === "UNTRACKED").length,
  };
}
