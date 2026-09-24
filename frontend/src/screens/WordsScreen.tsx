import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  deleteWord,
  fetchProgress,
  fetchWords,
  type Progress,
  type SavedWord,
} from "../api";
import { untilStr } from "../time";

function Stat({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

function Bars({
  data,
  highlightLast,
}: {
  data: { date: string; count: number }[];
  highlightLast?: boolean;
}) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="bars">
      {data.map((d, i) => (
        <div
          key={d.date}
          className={`bar${highlightLast && i === data.length - 1 ? " today" : ""}`}
          style={{ height: `${Math.max(6, (d.count / max) * 100)}%` }}
          title={`${d.date}: ${d.count} review${d.count === 1 ? "" : "s"}`}
        />
      ))}
    </div>
  );
}

export default function WordsScreen() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [words, setWords] = useState<SavedWord[] | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => {
    Promise.all([fetchProgress(), fetchWords()])
      .then(([p, w]) => {
        setProgress(p);
        setWords(w);
      })
      .catch((e) => setError(String((e as Error).message ?? e)));
  }, []);

  const remove = async (word: SavedWord) => {
    if (!window.confirm(`remove “${word.text}” from your words?`)) return;
    try {
      await deleteWord(word.id);
      setWords((ws) => (ws ? ws.filter((w) => w.id !== word.id) : ws));
      setProgress(await fetchProgress());
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  };

  const visible = useMemo(() => {
    if (!words) return [];
    const q = filter.trim().toLowerCase();
    if (!q) return words;
    return words.filter(
      (w) =>
        w.text.toLowerCase().includes(q) ||
        (w.translated ?? "").toLowerCase().includes(q)
    );
  }, [words, filter]);

  if (error) {
    return (
      <main>
        <p className="error">⚠ {error}</p>
      </main>
    );
  }

  if (!progress || !words) {
    return (
      <main>
        <section className="card">
          <p className="message">loading your words…</p>
        </section>
      </main>
    );
  }

  return (
    <main>
      <section className="stats-row">
        <Stat value={progress.total} label="words saved" />
        <Stat value={progress.due_now} label="due now" />
        <Stat value={progress.mastered} label="mastered" />
        <Stat value={progress.streak} label="day streak" />
      </section>

      <section className="card charts">
        <div className="chart">
          <h3>Reviews · last 30 days</h3>
          <Bars data={progress.reviews_last_30d} highlightLast />
        </div>
        <div className="chart">
          <h3>Coming up · next 7 days</h3>
          <Bars data={progress.forecast} highlightLast />
        </div>
      </section>

      <section className="card">
        <div className="words-head">
          <h3>Your words</h3>
          <input
            className="words-filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="filter…"
            aria-label="Filter words"
          />
        </div>

        {words.length === 0 ? (
          <p className="empty-note">
            no words saved yet — <Link to="/">analyze a word</Link> and hit “Save
            to practice”, or start a <Link to="/practice">practice session</Link>.
          </p>
        ) : (
          <table className="words-table">
            <thead>
              <tr>
                <th>word</th>
                <th>meaning</th>
                <th>confidence</th>
                <th>due</th>
                <th aria-label="remove" />
              </tr>
            </thead>
            <tbody>
              {visible.map((w) => (
                <tr key={w.id}>
                  <td className="cell-word">
                    {w.text}
                    <span className="cell-ipa">/ {w.expected_ipa.join(" ")} /</span>
                  </td>
                  <td className="cell-dim">{w.translated ?? "—"}</td>
                  <td>
                    <div className="conf">
                      <div className="conf-bar">
                        <div
                          className="conf-fill"
                          style={{ width: `${w.srs.confidence.percent}%` }}
                        />
                      </div>
                      <span className={`conf-label conf-${w.srs.confidence.label}`}>
                        {w.srs.confidence.label}
                      </span>
                    </div>
                  </td>
                  <td className={w.srs.due ? "cell-due" : "cell-dim"}>
                    {w.srs.due ? "due now" : untilStr(w.srs.due_at ?? "")}
                  </td>
                  <td>
                    <button
                      className="remove"
                      title={`remove ${w.text}`}
                      aria-label={`remove ${w.text}`}
                      onClick={() => void remove(w)}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
