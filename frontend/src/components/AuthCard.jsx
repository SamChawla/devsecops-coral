/**
 * Card shell used by the Login and Signup screens. Wraps the form with the
 * shared site header + footer so the public pages stay visually consistent.
 */
import { T } from "../theme/tokens.js";
import SiteHeader from "./SiteHeader.jsx";
import SiteFooter from "./SiteFooter.jsx";

/**
 * @param {{ variant?: "login" | "signup", title: string, subtitle: string,
 *           children: import('react').ReactNode, footer: import('react').ReactNode }} props
 */
export default function AuthCard({ variant, title, subtitle, children, footer }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: T.bg,
        color: T.text,
        fontFamily: T.sans,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <SiteHeader variant={variant} />

      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        <div style={{ width: "100%", maxWidth: 400 }}>
          <div
            style={{
              background: T.surface,
              border: `1px solid ${T.border}`,
              borderRadius: 16,
              padding: 28,
              boxShadow: T.shadowElevated,
            }}
          >
            <h1
              style={{ fontSize: 21, fontWeight: 800, letterSpacing: "-0.03em", margin: "0 0 6px" }}
            >
              {title}
            </h1>
            <p
              style={{
                fontSize: 13.5,
                color: T.textSecondary,
                margin: "0 0 22px",
                lineHeight: 1.5,
              }}
            >
              {subtitle}
            </p>
            {children}
          </div>

          <div style={{ textAlign: "center", marginTop: 18, fontSize: 13, color: T.textMuted }}>
            {footer}
          </div>
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}

/** Styled text input used in the auth forms. */
export function Field({ label, ...props }) {
  return (
    <label style={{ display: "block", marginBottom: 14 }}>
      <span
        style={{
          display: "block",
          fontSize: 12,
          fontWeight: 600,
          color: T.textSecondary,
          marginBottom: 6,
        }}
      >
        {label}
      </span>
      <input
        {...props}
        style={{
          width: "100%",
          padding: "11px 13px",
          background: T.inputBg,
          border: `1px solid ${T.border}`,
          borderRadius: 9,
          color: T.text,
          fontSize: 14,
          fontFamily: T.sans,
          outline: "none",
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = T.accentBorder;
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = T.border;
        }}
      />
    </label>
  );
}

/** Primary submit button for the auth forms. */
export function SubmitButton({ children, disabled }) {
  return (
    <button
      type="submit"
      disabled={disabled}
      style={{
        width: "100%",
        padding: "12px 16px",
        marginTop: 6,
        fontSize: 14.5,
        fontWeight: 700,
        color: "#fff",
        border: "none",
        borderRadius: 10,
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.6 : 1,
        background: `linear-gradient(135deg, ${T.accent} 0%, ${T.accentHover} 100%)`,
        boxShadow: `0 0 22px ${T.accentGlow}`,
      }}
    >
      {children}
    </button>
  );
}

/** Inline error banner for failed auth attempts. */
export function AuthError({ message }) {
  if (!message) return null;
  return (
    <div
      style={{
        padding: "9px 13px",
        marginBottom: 14,
        background: "rgba(239,68,68,0.07)",
        border: "1px solid rgba(239,68,68,0.25)",
        borderRadius: 9,
        fontSize: 13,
        color: T.red,
      }}
    >
      {message}
    </div>
  );
}
