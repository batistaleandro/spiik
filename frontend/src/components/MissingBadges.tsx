import type { MissingSound } from "../api";

export default function MissingBadges({ missing }: { missing: MissingSound[] }) {
  const major = missing.filter((m) => !m.minor);
  const minor = missing.filter((m) => m.minor);
  return (
    <div className="badges">
      {major.map((m) => (
        <span key={m.ipa} className="badge major">
          /{m.ipa}/ doesn’t exist in your language — said as “{m.substitute_display}” · needs training
        </span>
      ))}
      {minor.map((m) => (
        <span key={m.ipa} className="badge minor">
          /{m.ipa}/ ≈ “{m.substitute_display}” ({m.substitute})
        </span>
      ))}
    </div>
  );
}
