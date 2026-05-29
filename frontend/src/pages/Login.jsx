/**
 * Login screen. On success the backend sets an httpOnly session cookie and we
 * redirect to the dashboard.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import AuthCard, { AuthError, Field, SubmitButton } from "../components/AuthCard.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard
      variant="login"
      title="Welcome back"
      subtitle="Log in to your organization's security command center."
      footer={
        <>
          No account?{" "}
          <Link to="/signup" style={{ color: "var(--t-text)", fontWeight: 600 }}>
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit}>
        <AuthError message={error} />
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
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
        />
        <SubmitButton disabled={busy}>{busy ? "Signing in…" : "Log in"}</SubmitButton>
      </form>
    </AuthCard>
  );
}
