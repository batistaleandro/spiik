import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "../api";

export default function ResetPasswordScreen() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();

  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      setError("passwords don’t match");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await resetPassword(token, next);
      navigate("/login", { replace: true });
    } catch (err) {
      setError(String((err as Error).message ?? err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main>
      <section className="card auth-card">
        <h2>Choose a new password</h2>
        {!token ? (
          <>
            <p className="error">⚠ this link is missing its reset token</p>
            <p className="auth-switch">
              <Link to="/forgot-password">Request a new email</Link>
            </p>
          </>
        ) : (
          <>
            <p className="auth-sub">min. 8 characters</p>
            <form onSubmit={(e) => void submit(e)}>
              <label className="field">
                <span>New password</span>
                <input
                  type="password"
                  value={next}
                  onChange={(e) => setNext(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  autoFocus
                  required
                />
              </label>
              <label className="field">
                <span>Repeat new password</span>
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
              </label>
              {error && <p className="error">⚠ {error}</p>}
              <button type="submit" disabled={busy} className="auth-submit">
                {busy ? "…" : "Save password"}
              </button>
            </form>
          </>
        )}
      </section>
    </main>
  );
}
