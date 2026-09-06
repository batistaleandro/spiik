"""Language data loading and phoneme distance/substitution logic."""

from __future__ import annotations

import functools
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import panphon
import panphon.distance
import yaml

from app.core.tokenizer import Token, tokenize_ipa

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# A foreign sound whose best substitute is at most this distance away is
# marked as a "minor" adjustment; anything farther is highlighted as needing
# training. (Sounds like schwa in Portuguese are handled per-language via
# the minor_foreign list, since panphon's absolute scale is inconsistent.)
MINOR_DISTANCE = 0.4

_GED = panphon.distance.Distance()
_FT = panphon.featuretable.FeatureTable()

# panphon has no features for some espeak tokens; distance for unknown
# segments falls back to these defaults.
UNKNOWN_PENALTY = 2.5


@dataclass
class Language:
    code: str
    name: str
    espeak_voice: str
    tts_voice: str
    consonants: list[str]
    vowels: list[str]
    orthography: dict[str, str]
    substitutions: dict[str, list[str]] = field(default_factory=dict)
    drill_words: dict[str, list[str]] = field(default_factory=dict)
    # Foreign sounds that are effectively present in the language under
    # another guise (e.g. schwa ≈ /ɐ/ in Brazilian Portuguese).
    minor_foreign: list[str] = field(default_factory=list)
    # How to spell foreign sounds natively when a single substitute sound
    # isn't enough (en eɪ → ru "эй", en ŋ → ru "нг"); takes precedence over
    # the substitute's orthography for display.
    foreign_display: dict[str, str] = field(default_factory=dict)
    # Model-output tokens that mean the same sound as a G2P token but differ
    # by espeak-version convention (model ɐ ≈ G2P a, attached sʲ ≈ s + ʲ).
    # Applied to recognized sequences before alignment.
    recognized_aliases: dict[str, list[str]] = field(default_factory=dict)
    # Translation provider codes: {"google": "en", "mymemory": "en-US"}.
    translate: dict[str, str] = field(default_factory=dict)

    @property
    def inventory(self) -> set[str]:
        return set(self.consonants) | set(self.vowels)

    def native_display(self, ipa: str, _depth: int = 0) -> str:
        """How this language writes `ipa` — substituting a native sound when
        the language does not have it (e.g. θ → 't' for a Portuguese speaker)."""
        if ipa in self.orthography:
            return self.orthography[ipa]
        if ipa in self.foreign_display:
            return self.foreign_display[ipa]
        if _depth < 3 and ipa in self.substitutions:
            for candidate in self.substitutions[ipa]:
                if candidate in self.inventory:
                    return self.native_display(candidate, _depth + 1)
        best, _ = self.closest_sound(ipa)
        if best is not None and _depth < 3:
            return self.native_display(best, _depth + 1)
        return ipa

    def closest_sound(self, token: str) -> tuple[str | None, float]:
        """Closest native sound for a foreign token, by panphon distance.
        Hard-coded substitutions are tried first in curated order — a candidate
        that is a reasonable match (< 1.0) wins immediately, so panphon's
        feature ties (a == ʌ) can't override linguistic judgment. Falls back
        to automatic search over the whole inventory."""
        if token in self.inventory:
            return token, 0.0
        best: str | None = None
        best_d = float("inf")
        for candidate in self.substitutions.get(token, []):
            if candidate in self.inventory:
                d = segment_distance(token, candidate)
                if d < 1.0:
                    return candidate, d
                if d < best_d:
                    best, best_d = candidate, d
        if best is not None:
            return best, best_d
        for candidate in self.inventory:
            d = segment_distance(token, candidate)
            if d < best_d:
                best, best_d = candidate, d
        return best, best_d


def _known(seg: str) -> bool:
    return bool(seg) and _FT.seg_known(seg)


def _base(seg: str) -> str:
    """Strip diacritics and modifier letters so panphon finds the base segment."""
    nfd = unicodedata.normalize("NFD", seg)
    stripped = "".join(ch for ch in nfd if not unicodedata.combining(ch) and ch not in "˞ˑ")
    return stripped


def _subsegments(ipa: str) -> list[str]:
    """Split a token into panphon-recognizable sub-segments.

    Diphthongs (eɪ) and affricates (tʃ) become two segments; diacritics stay
    attached to their base character. Unknown multi-char runs are split apart
    so at least the base characters score.
    """
    nfc = unicodedata.normalize("NFC", ipa)
    segs: list[str] = []
    cur = ""
    for ch in nfc:
        if cur and (ch.isalnum() or ch in "ɐɑøœæɛɪʊɔʌɤʉɞɝɜ"):
            if _known(cur + ch):
                cur += ch
                continue
            segs.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        segs.append(cur)
    return segs


def _seg_pair_distance(a: str, b: str) -> float:
    for x, y in ((a, b), (_base(a), b), (a, _base(b)), (_base(a), _base(b))):
        if _known(x) and _known(y):
            return _GED.weighted_feature_edit_distance(x, y)
    return UNKNOWN_PENALTY


def segment_distance(a: str, b: str) -> float:
    """Feature-weighted distance between two phoneme tokens.

    Multi-character tokens are aligned as sub-segment sequences so that
    eɪ↔e counts as a partial mismatch instead of panphon's whole-token blowup.
    """
    if a == b:
        return 0.0
    # Palatalization ʲ is not in panphon; hand-distance it against the
    # palatal glide and the vowel it colors.
    pair = frozenset((a, b))
    if pair == frozenset(("ʲ", "j")):
        return 0.25
    if pair == frozenset(("ʲ", "i")):
        return 0.5
    sa, sb = _subsegments(a), _subsegments(b)
    if len(sa) == 1 and len(sb) == 1:
        return _seg_pair_distance(sa[0], sb[0])
    return _align_distance(sa, sb)


def _align_distance(sa: list[str], sb: list[str]) -> float:
    """Needleman-Wunsch over sub-segments with panphon distances."""
    gap = 0.75
    n, m = len(sa), len(sb)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + gap
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + gap
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = dp[i - 1][j - 1] + _seg_pair_distance(sa[i - 1], sb[j - 1])
            dele = dp[i - 1][j] + gap
            ins = dp[i][j - 1] + gap
            dp[i][j] = min(sub, dele, ins)
    return dp[n][m]


@functools.lru_cache(maxsize=None)
def load_language(code: str) -> Language:
    path = DATA_DIR / "languages" / f"{code}.yaml"
    if not path.exists():
        raise KeyError(f"unknown language: {code}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Language(
        code=raw["code"],
        name=raw["name"],
        espeak_voice=raw["espeak_voice"],
        tts_voice=raw["tts_voice"],
        consonants=list(raw.get("consonants", [])),
        vowels=list(raw.get("vowels", [])),
        orthography=dict(raw.get("orthography", {})),
        substitutions={k: list(v) for k, v in raw.get("substitutions", {}).items()},
        drill_words={k: list(v) for k, v in raw.get("drill_words", {}).items()},
        minor_foreign=list(raw.get("minor_foreign", [])),
        foreign_display=dict(raw.get("foreign_display", {})),
        recognized_aliases={k: list(v) for k, v in raw.get("recognized_aliases", {}).items()},
        translate=dict(raw.get("translate", {})),
    )


@functools.lru_cache(maxsize=1)
def list_languages() -> list[Language]:
    langs = []
    for path in sorted((DATA_DIR / "languages").glob("*.yaml")):
        langs.append(load_language(path.stem))
    return langs


def token_is_vowel(token: Token, lang: Language) -> bool:
    return token.ipa in set(lang.vowels)
