import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  analyze,
  assess,
  fetchDrill,
  fetchLanguages,
  saveWord,
  tts,
  type AnalyzeResult,
  type AssessResult,
  type Chunk,
  type Drill,
  type LanguageInfo,
} from "../api";
import { useAuth } from "../auth-context";
import Feedback from "../components/Feedback";
import MissingBadges from "../components/MissingBadges";
import { useRecorder } from "../useRecorder";

const DEFAULT_NATIVE = "pt-br";
const DEFAULT_TARGET = "en-us";
const DEFAULT_WORD = "creation";

// the chosen language pair and the train inputs survive reloads
const NATIVE_KEY = "spiik_native";
const TARGET_KEY = "spiik_target";
const WORD_KEY = "spiik_word";
const INPUT_LANG_KEY = "spiik_input_lang";

function storedLang(key: string, fallback: string): string {
  return localStorage.getItem(key) ?? fallback;
}

function storedInputLang(): "target" | "native" {
  return localStorage.getItem(INPUT_LANG_KEY) === "native" ? "native" : "target";
}

function LanguageSelect({
  languages,
  value,
  onChange,
  label,
}: {
  languages: LanguageInfo[];
  value: string;
  onChange: (code: string) => void;
  label: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {languages.map((l) => (
          <option key={l.code} value={l.code}>
            {l.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function ChunkChip({ chunk }: { chunk: Chunk }) {
  const cls = chunk.status === "foreign" ? "chunk foreign-major" : "chunk";
  const ipa = chunk.phonemes.map((p) => p.ipa).join(" ");
  const foreign = chunk.phonemes.filter((p) => p.status === "foreign");
  const tip = foreign.length
    ? `${ipa} — no ${foreign.map((p) => `/${p.ipa}/`).join(", ")} in your language (said as “${chunk.text}”)`
    : `${ipa}`;
  return (
    <span className={`${cls}${chunk.stressed ? " stressed" : ""}`} title={tip}>
      {chunk.text}
    </span>
  );
}

function DrillCard({
  sound,
  target,
  native,
  onPractice,
}: {
  sound: string;
  target: string;
  native: string;
  onPractice: (word: string) => void;
}) {
  const [drill, setDrill] = useState<Drill | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setDrill(null);
    setError("");
    fetchDrill(sound, target, native)
      .then((d) => alive && setDrill(d))
      .catch((e) => alive && setError(String(e.message ?? e)));
    return () => {
      alive = false;
    };
  }, [sound, target, native]);

  const play = async (word: string) => {
    try {
      const url = await tts(word, target);
      new Audio(url).play();
    } catch {
      /* ignore */
    }
  };

  if (error) return <div className="drill-card">⚠ {error}</div>;
  if (!drill) return <div className="drill-card">loading drill…</div>;
  return (
    <div className="drill-card">
      <div className="drill-head">
        <span className="drill-sound">/{drill.sound}/</span>
        <span className="drill-desc">{drill.description}</span>
      </div>
      {drill.how_to && <p className="drill-how">{drill.how_to}.</p>}
      <p className="drill-note">{drill.native_note}</p>
      {drill.examples.length > 0 && (
        <div className="drill-examples">
          {drill.examples.map((ex) => (
            <button
              key={ex.word}
              className="example"
              title={ex.ipa}
              onClick={() => {
                void play(ex.word);
                onPractice(ex.word);
              }}
            >
              🔊 {ex.word}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TrainerScreen() {
  const { user } = useAuth();
  const [languages, setLanguages] = useState<LanguageInfo[]>([]);
  const [native, setNative] = useState(() =>
    storedLang(NATIVE_KEY, DEFAULT_NATIVE)
  );
  const [target, setTarget] = useState(() =>
    storedLang(TARGET_KEY, DEFAULT_TARGET)
  );
  const [inputLang, setInputLang] = useState<"target" | "native">(() =>
    storedInputLang()
  );
  const [word, setWord] = useState(() =>
    storedLang(WORD_KEY, DEFAULT_WORD)
  );
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [feedback, setFeedback] = useState<AssessResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [scoring, setScoring] = useState(false);
  const { recording, start, stop } = useRecorder();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let alive = true;
    // validate what was restored from storage at mount — a persisted
    // selection may reference a language this install lacks
    const savedNative = storedLang(NATIVE_KEY, DEFAULT_NATIVE);
    const savedTarget = storedLang(TARGET_KEY, DEFAULT_TARGET);
    fetchLanguages()
      .then((langs) => {
        if (!alive) return;
        setLanguages(langs);
        if (!langs.some((l) => l.code === savedNative)) {
          const fallback = langs.some((l) => l.code === DEFAULT_NATIVE)
            ? DEFAULT_NATIVE
            : langs[0]?.code;
          if (fallback) setNative((cur) => (cur === savedNative ? fallback : cur));
        }
        if (!langs.some((l) => l.code === savedTarget)) {
          const fallback = langs.some((l) => l.code === DEFAULT_TARGET)
            ? DEFAULT_TARGET
            : langs[0]?.code;
          if (fallback) setTarget((cur) => (cur === savedTarget ? fallback : cur));
        }
      })
      .catch((e) => alive && setError(String(e.message ?? e)));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    localStorage.setItem(NATIVE_KEY, native);
  }, [native]);

  useEffect(() => {
    localStorage.setItem(TARGET_KEY, target);
  }, [target]);

  useEffect(() => {
    localStorage.setItem(WORD_KEY, word);
  }, [word]);

  useEffect(() => {
    localStorage.setItem(INPUT_LANG_KEY, inputLang);
  }, [inputLang]);

  const doAnalyze = useCallback(
    async (text?: string, langOverride?: "target" | "native") => {
      const query = (text ?? word).trim();
      if (!query) return;
      const lang = langOverride ?? inputLang;
      setLoading(true);
      setError("");
      setFeedback(null);
      setSaved(false);
      try {
        const result = await analyze(native, target, query, lang);
        setAnalysis(result);
        if (text) setWord(text);
      } catch (e) {
        setError(String((e as Error).message ?? e));
      } finally {
        setLoading(false);
      }
    },
    [word, native, target, inputLang]
  );

  const doListen = useCallback(async () => {
    // speak the practice word (analysis.text), not the raw query
    const toSpeak = (analysis?.text ?? word).trim();
    if (!toSpeak) return;
    try {
      const url = await tts(toSpeak, target);
      new Audio(url).play();
    } catch {
      setError("could not generate audio — check your connection");
    }
  }, [word, analysis, target]);

  const startRecording = useCallback(async () => {
    setError("");
    try {
      await start(async (blob) => {
        if (blob.size < 2000) {
          setError("recording too short — hold the button while you speak");
          return;
        }
        if (!analysis) return;
        setScoring(true);
        try {
          const result = await assess(
            blob,
            analysis.expected_ipa,
            analysis.native.code,
            analysis.target.code
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
  }, [start, analysis]);

  const doSave = useCallback(async () => {
    if (!analysis) return;
    setSaving(true);
    setError("");
    try {
      await saveWord(
        analysis.text,
        analysis.native.code,
        analysis.target.code,
        analysis.translated
      );
      setSaved(true);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  }, [analysis]);

  const practiceWord = useCallback(
    (w: string) => {
      // drill examples are always target-language words
      setWord(w);
      setInputLang("target");
      void doAnalyze(w, "target");
    },
    [doAnalyze]
  );

  const majorMissing = analysis?.missing_sounds.filter((m) => !m.minor) ?? [];

  return (
    <>
      <section className="controls">
        <LanguageSelect
          languages={languages}
          value={native}
          onChange={setNative}
          label="I speak"
        />
        <LanguageSelect
          languages={languages}
          value={target}
          onChange={setTarget}
          label="I’m learning"
        />
        <form
          className="field word-field"
          onSubmit={(e) => {
            e.preventDefault();
            void doAnalyze();
          }}
        >
          <div className="mode-toggle">
            <span>word in</span>
            <button
              type="button"
              className={inputLang === "target" ? "active" : ""}
              onClick={() => setInputLang("target")}
            >
              {languages.find((l) => l.code === target)?.name ?? "target"}
            </button>
            <button
              type="button"
              className={inputLang === "native" ? "active" : ""}
              onClick={() => setInputLang("native")}
            >
              {languages.find((l) => l.code === native)?.name ?? "native"}
            </button>
          </div>
          <div className="word-input-row">
            <input
              value={word}
              onChange={(e) => setWord(e.target.value)}
              placeholder={
                inputLang === "native"
                  ? `type a word in your language, get it in ${
                      languages.find((l) => l.code === target)?.name ?? "the target language"
                    }`
                  : "type a word to pronounce"
              }
              autoFocus
            />
            <button type="submit" disabled={loading}>
              {loading ? "…" : "Show sounds"}
            </button>
          </div>
        </form>
      </section>

      {error && <p className="error">⚠ {error}</p>}

      {analysis && (
        <main>
          <section className="word-card">
            <div className="word-row">
              <h2 className="word">{analysis.text}</h2>
              <span className="ipa">/ {analysis.expected_ipa.join(" ")} /</span>
              {analysis.translated && (
                <span
                  className="translation"
                  title={
                    analysis.input_lang === "native"
                      ? "the word you typed"
                      : `in ${analysis.native.name}`
                  }
                >
                  {analysis.input_lang === "native" ? "→ " : ""}
                  {analysis.translated}
                </span>
              )}
            </div>
            <div className="approx">
              {analysis.chunks.map((c, i) => (
                <ChunkChip key={i} chunk={c} />
              ))}
            </div>
            <p className="approx-caption">
              how it sounds to you, written in {analysis.native.name} · underlined = stressed
            </p>
            <MissingBadges missing={analysis.missing_sounds} />
            <div className="actions">
              <button className="listen" onClick={() => void doListen()}>
                🔊 Listen
              </button>
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
              {user ? (
                <button
                  className="save"
                  onClick={() => void doSave()}
                  disabled={saving || saved}
                >
                  {saved ? "✓ Saved" : saving ? "…" : "＋ Save to practice"}
                </button>
              ) : (
                <Link className="save login-to-save" to="/login">
                  Log in to save &amp; practice
                </Link>
              )}
            </div>
            {recording && (
              <p className="recording-note">listening… say the word, then stop</p>
            )}
          </section>

          {feedback && (
            <section className="card">
              <h3>Your attempt</h3>
              <Feedback result={feedback} />
              <p className="recognized">
                heard: <code>/ {feedback.recognized_ipa.join(" ")} /</code>
              </p>
            </section>
          )}

          {majorMissing.length > 0 && (
            <section className="card">
              <h3>Train the sounds your language doesn’t have</h3>
              {majorMissing.map((m) => (
                <DrillCard
                  key={m.ipa}
                  sound={m.ipa}
                  target={target}
                  native={native}
                  onPractice={practiceWord}
                />
              ))}
            </section>
          )}
        </main>
      )}

      {!analysis && !error && (
        <main>
          <section className="card intro">
            <p>
              Type a word in the language you’re learning. Spiik writes it out
              the way it <em>sounds</em> in your language — by comparing the
              international phonetic alphabet (IPA) of both.
            </p>
            <p>
              Then record yourself. Spiik tells you which sounds hit the mark
              and trains you on the ones your language doesn’t even have.
            </p>
            <p>
              Save the words you’re learning and spiik schedules spaced
              repetition practice so they stick.
            </p>
            <p className="example-hint">
              try:{" "}
              <button onClick={() => practiceWord("creation")}>creation</button>
              <button onClick={() => practiceWord("think")}>think</button>
              <button onClick={() => practiceWord("world")}>world</button>
            </p>
          </section>
        </main>
      )}
    </>
  );
}
