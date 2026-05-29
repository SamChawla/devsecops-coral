/**
 * Signup screen. Creates an organization and its first (owner) user, then sets
 * the session cookie and redirects to the dashboard.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import AuthCard, { AuthError, Field, SubmitButton } from "../components/AuthCard.jsx";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [org, setOrg] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await signup(email.trim(), password, org.trim());
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err.message || "Signup failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard
      variant="signup"
      title="Create your workspace"
      subtitle="Set up an organization and you'll be its first member."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "var(--t-text)", fontWeight: 600 }}>
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit}>
        <AuthError message={error} />
        <Field
          label="Organization name"
          type="text"
          required
          value={org}
          onChange={(e) => setOrg(e.target.value)}
          placeholder="Acme Security"
        />
        <Field
          label="Work email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
        />
        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="At least 8 characters"
        />
        <SubmitButton disabled={busy}>{busy ? "Creating…" : "Create workspace"}</SubmitButton>
      </form>
    </AuthCard>
  );
}
