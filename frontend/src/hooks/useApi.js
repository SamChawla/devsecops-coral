import { useCallback, useState } from "react";
import { mergeSourcesIntoCatalog } from "../utils/integrationCatalog.js";

const API_BASE = "";

/**
 * Fetch JSON from the dashboard API and throw on non-2xx responses.
 * @param {string} path - API path (e.g. `/api/scan`).
 * @param {RequestInit} [options] - Fetch options.
 * @returns {Promise<object>} Parsed JSON body.
 */
async function fetchJson(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    const error = new Error(err.detail || `Request failed: ${resp.status}`);
    error.status = resp.status;
    error.detail = err.detail || "";
    throw error;
  }
  return resp.json();
}

/**
 * React hook for devsecops-coral REST API calls.
 * Tracks loading state, last executed SQL, and surfaces request errors.
 * @returns {object} API client methods and shared request state.
 */
export function useApi() {
  const [pendingCount, setPendingCount] = useState(0);
  const [error, setError] = useState(null);
  const [lastSql, setLastSql] = useState("");
  const loading = pendingCount > 0;

  const request = useCallback(async (path, options) => {
    setPendingCount((count) => count + 1);
    setError(null);
    try {
      const data = await fetchJson(path, options);
      if (data.sql) setLastSql(data.sql);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setPendingCount((count) => Math.max(0, count - 1));
    }
  }, []);

  const getSources = useCallback(() => request("/api/sources"), [request]);
  const getIntegrations = useCallback(async () => {
    try {
      return await request("/api/integrations");
    } catch (err) {
      if (err?.status !== 404) {
        throw err;
      }
    }

    const sourcesData = await request("/api/sources");
    return {
      integrations: mergeSourcesIntoCatalog(sourcesData.sources || []),
      fallback: true,
    };
  }, [request]);
  const getPosture = useCallback(
    (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/posture?${qs}`);
    },
    [request],
  );
  const getScan = useCallback(
    (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/scan?${qs}`);
    },
    [request],
  );
  const getCorrelate = useCallback(
    (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/correlate?${qs}`);
    },
    [request],
  );
  const getTimeline = useCallback(
    (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/timeline?${qs}`);
    },
    [request],
  );
  const getGithubPrs = useCallback(
    (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/github-prs?${qs}`);
    },
    [request],
  );
  const postAsk = useCallback(
    (query) =>
      request("/api/ask", { method: "POST", body: JSON.stringify({ query }) }),
    [request],
  );
  const postSql = useCallback(
    (query) =>
      request("/api/sql", { method: "POST", body: JSON.stringify({ query }) }),
    [request],
  );
  const postRootCause = useCallback(
    ({ cve, package: pkg, ecosystem, since } = {}) =>
      request("/api/root-cause", {
        method: "POST",
        body: JSON.stringify({ cve, package: pkg, ecosystem, since }),
      }),
    [request],
  );
  const connectSource = useCallback(
    (name, values = {}) =>
      request("/api/sources/connect", {
        method: "POST",
        body: JSON.stringify({ name, values }),
      }),
    [request],
  );
  const testSource = useCallback(
    (name) => request(`/api/sources/${encodeURIComponent(name)}/test`, { method: "POST" }),
    [request],
  );
  const removeSource = useCallback(
    (name) => request(`/api/sources/${encodeURIComponent(name)}`, { method: "DELETE" }),
    [request],
  );

  const getActions = useCallback(
    (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/actions?${qs}`);
    },
    [request],
  );

  const getRecommend = useCallback(
    (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return request(`/api/recommend?${qs}`);
    },
    [request],
  );

  const approveAction = useCallback(
    (id) => request(`/api/actions/${id}/approve`, { method: "POST" }),
    [request],
  );

  const approveAllActions = useCallback(
    () => request("/api/actions/approve-all", { method: "POST" }),
    [request],
  );

  const dismissAction = useCallback(
    (id) => request(`/api/actions/${id}/dismiss`, { method: "POST" }),
    [request],
  );

  return {
    loading,
    error,
    lastSql,
    setLastSql,
    getSources,
    getIntegrations,
    getPosture,
    getScan,
    getCorrelate,
    getTimeline,
    getGithubPrs,
    postAsk,
    postSql,
    postRootCause,
    connectSource,
    testSource,
    removeSource,
    getActions,
    getRecommend,
    approveAction,
    approveAllActions,
    dismissAction,
  };
}
