import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../api";

export default function ForgotPasswordScreen() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (err) {
      setError(String((err as Error).message ?? err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <section className="card auth-card">
        <h2>Reset your password</h2>
        {sent ? (
          <>
            <p className="ok-note">Check your inbox — the link is valid for one hour.</p>
            <p className="auth-switch">
              <Link to="/login">Back to log in</Link>
            </p>
          </>
        ) : (
          <>
            <p className="auth-sub">we'll email you a one-time reset link</p>
            <form onSubmit={(e) => void submit(e)}>
              <label className="field">
                <span>Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  autoFocus
                  required
                />
              </label>
              {error && <p className="error">⚠ {error}</p>}
              <button type="submit" disabled={busy} className="auth-submit">
                {busy ? "…" : "Send recovery email"}
              </button>
            </form>
            <p className="auth-switch">
              <Link to="/login">Back to log in</Link>
            </p>
          </>
        )}
      </section>
    </main>
  );
}
