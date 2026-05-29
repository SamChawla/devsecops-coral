/**
 * App-wide theme provider. Lifts the dark/light theme out of the dashboard so
 * the landing page, auth screens, and dashboard all share one palette. Sets the
 * `data-theme` attribute on <html> (which drives the CSS custom properties in
 * globals.css) and injects the shared keyframes once.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { GLOBAL_STYLES } from "./tokens.js";

const ThemeContext = createContext({ theme: "dark", toggleTheme: () => {} });

function getInitialTheme() {
  try {
    return localStorage.getItem("coral-theme") || "dark";
  } catch {
    return "dark";
  }
}

/**
 * Provides `{ theme, toggleTheme }` to the whole app and persists the choice.
 * @param {{ children: import('react').ReactNode }} props
 */
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("coral-theme", theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const value = useMemo(
    () => ({ theme, toggleTheme: () => setTheme((t) => (t === "dark" ? "light" : "dark")) }),
    [theme],
  );

  return (
    <ThemeContext.Provider value={value}>
      <style>{GLOBAL_STYLES}</style>
      {children}
    </ThemeContext.Provider>
  );
}

/** Access the current theme and a toggle function. */
export function useTheme() {
  return useContext(ThemeContext);
}
