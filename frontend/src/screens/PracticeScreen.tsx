import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  assess,
  fetchPractice,
  reviewWord,
  type AssessResult,
  type PracticeQueue,
  type Rating,
  type SavedWord,
} from "../api";
import Feedback from "../components/Feedback";
import MissingBadges from "../components/MissingBadges";
import { untilStr } from "../time";
import { useRecorder } from "../useRecorder";

const RATINGS: { key: Rating; label: string; cls: string }[] = [
  { key: "again", label: "Again", cls: "rate-again" },
  { key: "hard", label: "Hard", cls: "rate-hard" },
  { key: "good", label: "Good", cls: "rate-good" },
  { key: "easy", label: "Easy", cls: "rate-easy" },
];

export default function PracticeScreen() {
  const [queue, setQueue] = useState<SavedWord[] | null>(null);
  const [queueInfo, setQueueInfo] = useState<PracticeQueue | null>(null);
  const [idx, setIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [feedback, setFeedback] = useState<AssessResult | null>(null);
  const [scoring, setScoring] = useState(false);
  const [reviews, setReviews] = useState(0);
  const [agains, setAgains] = useState(0);
  const [requeued, setRequeued] = useState<Set<number>>(new Set());
  const [error, setError] = useState("");
  const [rating, setRating] = useState(false);
  const { recording, start, stop } = useRecorder();

  const loadQueue = useCallback(async () => {
    try {
      const res = await fetchPractice();
      setQueueInfo(res);
      setQueue(res.items);
      setIdx(0);
      setRevealed(false);
      setFeedback(null);
      setReviews(0);
      setAgains(0);
      setRequeued(new Set());
      setError("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  const card = queue && idx < queue.length ? queue[idx] : null;
  const done = queue !== null && !card;

  const doRate = useCallback(
    async (r: Rating) => {
      if (!card || rating) return;
      setRating(true);
      setError("");
      try {
        const updated = await reviewWord(card.id, r);
        setReviews((n) => n + 1);
        if (r === "again") setAgains((n) => n + 1);
        if (r === "again" && !requeued.has(card.id)) {
          // come back to it at the end of this session
          setRequeued((prev) => new Set(prev).add(card.id));
          setQueue((q) => (q ? [...q, updated] : q));
        }
        setIdx((i) => i + 1);
        setRevealed(false);
        setFeedback(null);
      } catch (e) {
        setError(String((e as Error).message ?? e));
      } finally {
        setRating(false);
      }
    },
    [card, rating, requeued]
  );

  const startRecording = useCallback(async () => {
    if (!card) return;
    setError("");
    try {
      await start(async (blob) => {
        if (blob.size < 2000) {
          setError("recording too short — hold the button while you speak");
          return;
        }
        setScoring(true);
        try {
          const result = await assess(
            blob,
            card.expected_ipa,
            card.native,
            card.target
          );
          setFeedback(result);
        } catch (e) {
          setError(String((e as Error).message ?? e));
        } finally {
          setScoring(false);
        }
      });
    } catch {
      setError("microphone access denied — allow mic access in your browser");
    }
  }, [start, card]);

  if (error && !queue) {
    return (
      <main>
        <p className="error">⚠ {error}</p>
      </main>
    );
  }

  if (queue === null) {
    return (
      <main>
        <section className="card">
          <p className="message">loading practice…</p>
        </section>
      </main>
    );
  }

  if (done) {
    const practiced = queueInfo?.counts ?? { due: 0, new: 0 };
    if (practiced.due + practiced.new === 0 && reviews === 0) {
      return (
        <main>
          <section className="card practice-empty">
            <h2>All caught up 🎉</h2>
            <p>
              Nothing to review right now.
              {queueInfo?.next_due
                ? ` Next card is due ${untilStr(queueInfo.next_due)}.`
                : ""}
            </p>
            <p className="practice-empty-hint">
              <Link to="/">Analyze a word</Link> and hit “Save to practice” to
              grow your deck, or check <Link to="/words">your words</Link>.
            </p>
          </section>
        </main>
      );
    }
    return (
      <main>
        <section className="card practice-summary">
          <h2>Session complete 🎉</h2>
          <p>
            <strong>{reviews}</strong> review{reviews === 1 ? "" : "s"}
            {agains > 0 && (
              <>
                {" "}
                · <strong>{agains}</strong> came back for another look
              </>
            )}
          </p>
          <div className="actions">
            <button onClick={() => void loadQueue()}>Practice again</button>
            <Link className="ghost-link" to="/words">
              See your words &amp; progress
            </Link>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main>
      {error && <p className="error">⚠ {error}</p>}
      <section className="card practice-card">
        <div className="practice-meta">
          <span>
            card {idx + 1} of {queue!.length}
          </span>
          <span className={`state-pill ${card!.srs.state}`}>{card!.srs.state}</span>
        </div>

        {!revealed ? (
          // side A: the word, how to say it, and the recording
          <>
            <h2 className="practice-word">{card!.text}</h2>
            <p className="approx-plain">{card!.approximation}</p>
            <p className="approx-caption">how it sounds in your language</p>
            <MissingBadges missing={card!.missing_sounds} />

            <div className="actions">
              {scoring ? (
                <button className="record scoring" disabled>
                  checking…
                </button>
              ) : recording ? (
                <button className="record recording" onClick={stop}>
                  ⏹ Stop &amp; check
                </button>
              ) : (
                <button className="record" onClick={() => void startRecording()}>
                  🎙 Record
                </button>
              )}
              <button onClick={() => setRevealed(true)}>Show answer</button>
            </div>
            {recording && (
              <p className="recording-note">listening… say the word, then stop</p>
            )}
            {feedback && !recording && !scoring && (
              <p className="recording-note">
                recording checked — show the answer for your score
              </p>
            )}
          </>
        ) : (
          // side B: the meaning, the recording result, and self-evaluation
          <>
            <h2 className="practice-word">
              {card!.translated ?? card!.text}
            </h2>
            {card!.translated && (
              <div className="practice-answer">
                <span className="translation">{card!.text}</span>
              </div>
            )}

            {feedback ? (
              <div className="practice-feedback">
                <Feedback result={feedback} />
                {feedback.recognized_ipa.length > 0 && (
                  <p className="recognized">
                    heard: <code>/ {feedback.recognized_ipa.join(" ")} /</code>
                  </p>
                )}
              </div>
            ) : (
              <p className="practice-hint">
                no recording on this card — rate how well you knew it
              </p>
            )}

            <div className="rate-row">
              {RATINGS.map(({ key, label, cls }) => (
                <button
                  key={key}
                  className={`rate ${cls}`}
                  onClick={() => void doRate(key)}
                  disabled={rating}
                >
                  {label}
                  <span className="rate-interval">
                    {card!.srs.next_intervals[key]}
                  </span>
                </button>
              ))}
            </div>
            <p className="rate-caption">how well did you know it?</p>
          </>
        )}
      </section>
    </main>
  );
}
