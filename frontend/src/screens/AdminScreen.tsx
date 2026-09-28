import { useEffect, useMemo, useState } from "react";
import {
  adminDeleteUser,
  adminListUsers,
  adminResetPassword,
  adminToggleUser,
  type AdminUser,
} from "../api";
import { useAuth } from "../auth-context";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

export default function AdminScreen() {
  const { user } = useAuth();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = () => {
    adminListUsers()
      .then(setUsers)
      .catch((err) => setError(String((err as Error).message ?? err)));
  };

  useEffect(load, []);

  const visible = useMemo(() => {
    if (!users) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) => u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
    );
  }, [users, filter]);

  if (!users) {
    return (
      <main>
        <section className="card">
          {error ? <p className="error">⚠ {error}</p> : <p className="message">loading users…</p>}
        </section>
      </main>
    );
  }

  const run = async (id: number, action: () => Promise<string | null>) => {
    setBusyId(id);
    setError("");
    setNotice("");
    try {
      const done = await action();
      if (done) setNotice(done);
      load();
    } catch (err) {
      setError(String((err as Error).message ?? err));
    } finally {
      setBusyId(null);
    }
  };

  const toggle = (u: AdminUser) => {
    void run(u.id, async () => {
      const next = await adminToggleUser(u.id);
      return `${u.username} ${next.is_active ? "enabled" : "disabled"}`;
    });
  };

  const remove = (u: AdminUser) => {
    if (
      !window.confirm(
        `Remove ${u.username} permanently? Their profile, saved words and review history are deleted — there is no undo.`
      )
    ) {
      return;
    }
    void run(u.id, async () => {
      await adminDeleteUser(u.id);
      return `${u.username} removed`;
    });
  };

  const resetPassword = (u: AdminUser) => {
    if (
      !window.confirm(
        `Reset ${u.username}'s password? spiik generates a one-time password for you to hand over — it is shown only once.`
      )
    ) {
      return;
    }
    void run(u.id, async () => {
      const generated = await adminResetPassword(u.id);
      return generated
        ? `${u.username}'s new password: ${generated} — show it to them now, it won't be displayed again.`
        : `${u.username}'s password was reset.`;
    });
  };

  return (
    <main>
      <section className="card">
        <div className="words-head">
          <h3>Users</h3>
          <input
            className="words-filter"
            placeholder="search users…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <p className="message">
          {users.length} account{users.length === 1 ? "" : "s"} on this instance
        </p>
        {notice && <p className="ok-note">{notice}</p>}
        {error && <p className="error">⚠ {error}</p>}
        <table className="words-table admin-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Registered</th>
              <th>Words</th>
              <th>Last practice</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((u) => (
              <tr key={u.id}>
                <td className="cell-word">
                  {u.username}
                  <span className="cell-ipa">{u.email}</span>
                  {u.is_admin && <span className="admin-tag">operator</span>}
                </td>
                <td className="cell-dim">{fmtDate(u.created_at)}</td>
                <td className="cell-dim">{u.word_count}</td>
                <td className="cell-dim">{fmtDate(u.last_review_at)}</td>
                <td className={u.is_active ? "cell-dim" : "cell-due"}>
                  {u.is_active ? "active" : "disabled"}
                </td>
                <td className="admin-actions">
                  {u.id !== user?.id && (
                    <>
                      <button
                        className="ghost-link"
                        disabled={busyId === u.id}
                        onClick={() => toggle(u)}
                      >
                        {u.is_active ? "Disable" : "Enable"}
                      </button>
                      <button
                        className="ghost-link"
                        disabled={busyId === u.id}
                        onClick={() => resetPassword(u)}
                      >
                        Reset password
                      </button>
                      <button
                        className="remove"
                        disabled={busyId === u.id}
                        onClick={() => remove(u)}
                      >
                        Remove
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
