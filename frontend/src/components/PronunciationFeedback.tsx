import { useEffect, useState, type ReactNode } from "react";
import {
  fetchPronunciationFeedback,
  getToken,
  suggestPronunciation,
  votePronunciation,
  type PronunciationFeedback as FeedbackData,
} from "../api";

interface Props {
  native: string;
  target: string;
  text: string;
  // the system-generated approximation: the edit prefill, and the fallback
  // display when no suggestion is effective for this user
  systemApproximation: string;
  // payload already fetched with the card (practice queue) — skips the fetch
  initial?: FeedbackData;
  children: ReactNode;
}

export default function PronunciationFeedback({
  native,
  target,
  text,
  systemApproximation,
  initial,
  children,
}: Props) {
  const [fb, setFb] = useState<FeedbackData | null>(initial ?? null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    // feedback needs the signed-in user — stay hidden when logged out so the
    // public analyze flow never triggers an authed call
    if (initial || !getToken()) return;
    let alive = true;
    fetchPronunciationFeedback(native, target, text)
      .then((res) => {
        if (alive) setFb(res);
      })
      .catch(() => {
        /* the feedback row stays hidden on failure */
      });
    return () => {
      alive = false;
    };
  }, [native, target, text, initial]);

  // all hooks must run before this — the row simply stays hidden while the
  // payload is missing
  if (!fb) return <>{children}</>;

  const displayed =
    fb.effective.source === "suggestion"
      ? fb.suggestions.find((s) => s.id === fb.effective.suggestion_id) ?? null
      : null;
  const suggestionId =
    fb.effective.source === "suggestion" ? fb.effective.suggestion_id : null;
  const up = displayed ? displayed.up : fb.system.up;
  const down = displayed ? displayed.down : fb.system.down;
  const myVote = displayed ? displayed.my_vote : fb.system.my_vote;

  async function doVote(vote: "up" | "down") {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      setFb(await votePronunciation(native, target, text, suggestionId, vote));
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  function startEdit() {
    setDraft(displayed ? displayed.text : systemApproximation);
    setSubmitted(false);
    setError("");
    setEditing(true);
  }

  async function save() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      setFb(await suggestPronunciation(native, target, text, draft));
      setEditing(false);
      setSubmitted(true);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pron-block">
      {editing ? (
        <span className="pron-edit">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            maxLength={255}
            autoFocus
            aria-label="Approximate pronunciation"
          />
          <button onClick={() => void save()} disabled={busy || !draft.trim()}>
            {busy ? "…" : "Save"}
          </button>
          <button
            className="pron-cancel"
            onClick={() => setEditing(false)}
            disabled={busy}
          >
            Cancel
          </button>
        </span>
      ) : displayed ? (
        <p className="approx-plain pron-suggested">
          {displayed.text}
          <span className="pron-mark">
            {displayed.mine ? " · your suggestion" : " · suggested by the community"}
          </span>
        </p>
      ) : (
        children
      )}

      {!editing && (
        <div className="pron-row">
          {myVote === "down" ? (
            <button className="pron-suggest" onClick={startEdit} disabled={busy}>
              Suggest Alternative Pronunciation
            </button>
          ) : (
            <>
              <button
                className={`pron-icon${myVote === "up" ? " pron-voted" : ""}`}
                onClick={() => void doVote("up")}
                disabled={busy}
                title="this pronunciation reads well"
              >
                👍 <span className="pron-count">{up}</span>
              </button>
              <button
                className="pron-icon"
                onClick={() => void doVote("down")}
                disabled={busy}
                title="this pronunciation misleads me"
              >
                👎 <span className="pron-count">{down}</span>
              </button>
            </>
          )}
          {submitted && <span className="pron-note">✓ suggestion submitted</span>}
          {error && <span className="pron-note pron-error">⚠ {error}</span>}
        </div>
      )}
    </div>
  );
}
