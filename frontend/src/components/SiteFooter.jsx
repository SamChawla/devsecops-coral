/**
 * Shared public site footer used on the landing, login, and signup pages.
 */
import { T } from "../theme/tokens.js";

export default function SiteFooter() {
  return (
    <footer
      style={{
        borderTop: `1px solid ${T.border}`,
        padding: "24px 28px",
        textAlign: "center",
        fontSize: 11.5,
        fontFamily: T.mono,
        color: T.textMuted,
        letterSpacing: "0.04em",
      }}
    >
      🪸 coral reads → agent analyzes → human approves → agent acts
    </footer>
  );
}
