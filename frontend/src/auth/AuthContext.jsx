/**
 * Authentication context for the SaaS shell.
 *
 * Talks to the FastAPI `/api/auth/*` endpoints. The session lives in an
 * httpOnly cookie set by the backend (never localStorage), so this layer only
 * tracks the resolved identity: the signed-in user and their organization.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

const AuthContext = createContext(null);

async function authFetch(path, body) {
  const resp = await fetch(path, {
    method: body ? "POST" : "GET",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || `Request failed (${resp.status})`);
  }
  return data;
}

/**
 * Provides authentication state and actions to the app.
 * @param {{ children: import('react').ReactNode }} props
 */
export function AuthProvider({ children }) {
  const [status, setStatus] = useState("loading"); // loading | authed | anon
  const [user, setUser] = useState(null);
  const [org, setOrg] = useState(null);

  const apply = useCallback((data) => {
    setUser(data.user || null);
    setOrg(data.org || null);
    setStatus(data.user ? "authed" : "anon");
  }, []);

  useEffect(() => {
    let active = true;
    authFetch("/api/auth/me")
      .then((data) => active && apply(data))
      .catch(() => active && setStatus("anon"));
    return () => {
      active = false;
    };
  }, [apply]);

  const login = useCallback(
    async (email, password) => apply(await authFetch("/api/auth/login", { email, password })),
    [apply],
  );

  const signup = useCallback(
    async (email, password, org_name) =>
      apply(await authFetch("/api/auth/signup", { email, password, org_name })),
    [apply],
  );

  const logout = useCallback(async () => {
    try {
      await authFetch("/api/auth/logout", {});
    } catch {
      /* ignore */
    }
    setUser(null);
    setOrg(null);
    setStatus("anon");
  }, []);

  const value = useMemo(
    () => ({ status, user, org, login, signup, logout }),
    [status, user, org, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access auth state and actions. */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

/**
 * Route guard: redirects to /login when the visitor is not authenticated.
 * @param {{ children: import('react').ReactNode }} props
 */
export function ProtectedRoute({ children }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "var(--t-bg)",
          color: "var(--t-text-muted)",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13,
          letterSpacing: "0.08em",
        }}
      >
        AUTHENTICATING…
      </div>
    );
  }

  if (status !== "authed") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}
