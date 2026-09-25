import type { AssessResult } from "../api";

const STATUS_ICON: Record<string, string> = {
  correct: "✓",
  close: "≈",
  wrong: "✗",
  missing: "–",
};

export default function Feedback({ result }: { result: AssessResult }) {
  if (result.message) return <p className="message">{result.message}</p>;
  const grade =
    result.score >= 85 ? "great" : result.score >= 60 ? "ok" : "rough";
  return (
    <div className="feedback">
      <div className={`score ${grade}`}>
        <span className="score-num">{result.score}</span>
        <span className="score-label">/ 100</span>
      </div>
      <div className="verdicts">
        {result.verdicts.map((v, i) => (
          <span key={i} className={`verdict ${v.status}`} title={v.hint}>
            <span className="v-icon">{STATUS_ICON[v.status]}</span>
            <span className="v-expected">{v.expected}</span>
          </span>
        ))}
      </div>
      <ul className="hints">
        {result.verdicts
          .filter((v) => v.status !== "correct")
          .map((v, i) => (
            <li key={i} className={v.foreign ? "foreign-hint" : ""}>
              <span className={`v-icon ${v.status}`}>{STATUS_ICON[v.status]}</span>{" "}
              <code>/{v.expected}/</code> — {v.hint}
            </li>
          ))}
        {result.extra_sounds && result.extra_sounds.length > 0 && (
          <li className="extra">
            extra sound(s): <code>{result.extra_sounds.join(" ")}</code>
          </li>
        )}
      </ul>
    </div>
  );
}
