import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth-context";

export default function AuthScreen({ mode }: { mode: "login" | "register" }) {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") {
        await login(username.trim(), password);
      } else {
        await register(username.trim(), email.trim(), password);
      }
      navigate(from, { replace: true });
    } catch (err) {
      setError(String((err as Error).message ?? err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <section className="card auth-card">
        <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
        <p className="auth-sub">
          {mode === "login"
            ? "log in to practice your saved words"
            : "save words and train them with spaced repetition"}
        </p>
        <form onSubmit={(e) => void submit(e)}>
          <label className="field">
            <span>Username{mode === "login" ? " or email" : ""}</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </label>
          {mode === "register" && (
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>
          )}
          <label className="field">
            <span>Password{mode === "register" ? " (min. 8 characters)" : ""}</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
            />
          </label>
          {error && <p className="error">⚠ {error}</p>}
          <button type="submit" disabled={busy} className="auth-submit">
            {busy ? "…" : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
        <p className="auth-switch">
          {mode === "login" ? (
            <>
              no account yet? <Link to="/register">Create one</Link>
            </>
          ) : (
            <>
              already registered? <Link to="/login">Log in</Link>
            </>
          )}
        </p>
      </section>
    </main>
  );
}
