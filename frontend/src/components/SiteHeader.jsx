/**
 * Shared public site header used on the landing, login, and signup pages so the
 * chrome stays consistent. The brand mark always links back to the homepage.
 */
import { Link } from "react-router-dom";
import { T } from "../theme/tokens.js";
import { useTheme } from "../theme/ThemeContext.jsx";

const linkStyle = {
  fontSize: 13,
  color: T.textSecondary,
  textDecoration: "none",
  padding: "0 10px",
};

const ghostButton = {
  padding: "8px 14px",
  fontSize: 13,
  fontWeight: 600,
  color: T.text,
  textDecoration: "none",
  border: `1px solid ${T.border}`,
  borderRadius: 8,
};

const solidButton = {
  padding: "8px 16px",
  fontSize: 13,
  fontWeight: 700,
  color: "#fff",
  textDecoration: "none",
  borderRadius: 8,
  background: `linear-gradient(135deg, ${T.accent} 0%, ${T.accentHover} 100%)`,
  boxShadow: `0 0 18px ${T.accentGlow}`,
};

/**
 * @param {{ variant?: "landing" | "login" | "signup" }} props
 */
export default function SiteHeader({ variant = "landing" }) {
  const { theme, toggleTheme } = useTheme();
  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 28px",
        background: T.frosted,
        backdropFilter: "blur(20px) saturate(1.3)",
        WebkitBackdropFilter: "blur(20px) saturate(1.3)",
        borderBottom: `1px solid ${T.border}`,
      }}
    >
      <Link
        to="/"
        style={{ display: "flex", alignItems: "center", gap: 11, textDecoration: "none" }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 9,
            background: `linear-gradient(135deg, ${T.accent} 0%, #ff8555 100%)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 15,
            fontWeight: 900,
            color: "#fff",
            fontFamily: T.mono,
            boxShadow: `0 0 18px ${T.accentGlow}`,
          }}
        >
          ◈
        </div>
        <span style={{ fontSize: 16, fontWeight: 800, letterSpacing: "-0.03em", color: T.text }}>
          Coral<span style={{ color: T.accent }}>Sentinel</span>
        </span>
      </Link>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {variant === "landing" && (
          <>
            <a href="#how" style={linkStyle}>
              How it works
            </a>
            <a href="#sources" style={linkStyle}>
              Sources
            </a>
          </>
        )}

        <button
          type="button"
          onClick={toggleTheme}
          title="Toggle theme"
          style={{
            padding: "7px 11px",
            background: T.btnBase,
            border: `1px solid ${T.border}`,
            borderRadius: 8,
            color: T.textSecondary,
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>

        {variant !== "login" && (
          <Link to="/login" style={ghostButton}>
            Log in
          </Link>
        )}
        {variant !== "signup" && (
          <Link to="/signup" style={solidButton}>
            Get started
          </Link>
        )}
      </div>
    </nav>
  );
}
