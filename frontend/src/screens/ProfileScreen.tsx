import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword, fetchHealth, updateProfile } from "../api";
import { useAuth } from "../auth-context";

export default function ProfileScreen() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [version, setVersion] = useState("");

  useEffect(() => {
    fetchHealth()
      .then((h) => setVersion(h.version))
      .catch(() => setVersion(""));
  }, []);

  const [username, setUsername] = useState(user?.username ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [profileMsg, setProfileMsg] = useState("");
  const [profileErr, setProfileErr] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pwMsg, setPwMsg] = useState("");
  const [pwErr, setPwErr] = useState("");
  const [savingPw, setSavingPw] = useState(false);

  if (!user) return null;

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    setProfileMsg("");
    setProfileErr("");
    try {
      const updated = await updateProfile({
        username: username.trim(),
        email: email.trim(),
      });
      setUser(updated);
      setProfileMsg("profile updated ✓");
    } catch (err) {
      setProfileErr(String((err as Error).message ?? err));
    } finally {
      setSavingProfile(false);
    }
  };

  const savePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPwMsg("");
    setPwErr("");
    if (next !== confirm) {
      setPwErr("new passwords don’t match");
      return;
    }
    setSavingPw(true);
    try {
      await changePassword(current, next);
      setPwMsg("password changed ✓");
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setPwErr(String((err as Error).message ?? err));
    } finally {
      setSavingPw(false);
    }
  };

  return (
    <main>
      <section className="card">
        <h3>Profile</h3>
        <form className="stack" onSubmit={(e) => void saveProfile(e)}>
          <label className="field">
            <span>Username</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              minLength={3}
              maxLength={30}
              required
            />
          </label>
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          {profileMsg && <p className="ok-note">{profileMsg}</p>}
          {profileErr && <p className="error">⚠ {profileErr}</p>}
          <div>
            <button type="submit" disabled={savingProfile}>
              {savingProfile ? "…" : "Save changes"}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h3>Change password</h3>
        <form className="stack" onSubmit={(e) => void savePassword(e)}>
          <label className="field">
            <span>Current password</span>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <label className="field">
            <span>New password (min. 8 characters)</span>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              minLength={8}
              autoComplete="new-password"
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
              required
            />
          </label>
          {pwMsg && <p className="ok-note">{pwMsg}</p>}
          {pwErr && <p className="error">⚠ {pwErr}</p>}
          <div>
            <button type="submit" disabled={savingPw}>
              {savingPw ? "…" : "Change password"}
            </button>
          </div>
        </form>
      </section>

      <section className="card">
        <h3>Session</h3>
        <button
          className="danger"
          onClick={() => {
            logout();
            navigate("/");
          }}
        >
          Log out
        </button>
        {version && version !== "dev" && (
          <p className="ok-note">spiik {version}</p>
        )}
      </section>
    </main>
  );
}
