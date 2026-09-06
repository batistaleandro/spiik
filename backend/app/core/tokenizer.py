"""IPA tokenizer.

espeak emits IPA strings with stress marks (ˈ ˌ), length marks (ː),
combining diacritics (nasal tilde, etc.) and multi-character phonemes
(diphthongs like eɪ, affricates like tʃ).

Tokens are produced by longest-match against an optional inventory of
multi-character units; anything else falls back to single characters.
Stress marks attach to the following phoneme.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PRIMARY_STRESS = "ˈ"
SECONDARY_STRESS = "ˌ"
# espeak's Russian voice marks stress with ASCII " and ^.
EXTRA_PRIMARY_STRESS = '"'
EXTRA_SECONDARY_STRESS = "^"

# Combining diacritics that stay attached to the base phoneme.
_COMBINING = set("̡̢̥̪̬̰̼̜̞̘̙͈̃̈̽̆̆̎̂̌ͅ")

# Multi-character units seen in espeak IPA output across languages.
# The inventory of a specific language should be preferred when available.
DEFAULT_MULTI = [
    "aɪ",
    "aʊ",
    "eɪ",
    "ɔɪ",
    "oʊ",
    "əʊ",
    "ɑː",
    "ɔː",
    "ɜː",
    "iː",
    "uː",
    "yː",
    "ɛː",
    "æː",
    "ɐː",
    "eː",
    "oː",
    "øː",
    "ɛ̃",
    "ɑ̃",
    "ɔ̃",
    "œ̃",
    "ẽ",
    "ĩ",
    "õ",
    "ũ",
    "ɐ̃",
    "ɪ̃",
    "ʊ̃",
    "õː",
    "ɐ̃ʊ̃",
    "tʃ",
    "dʒ",
    "ts",
    "dz",
    "pf",
    "kv",
    "tɕ",
    "dʑ",
    "ʈʂ",
    "ɖʐ",
    "ɐ̃ʊ̃",
]


@dataclass
class Token:
    ipa: str
    stress: int = 0  # 0 = none, 1 = primary, 2 = secondary
    unknown: bool = False  # not part of the reference inventory
    word_index: int = 0


def _normalize(text: str) -> str:
    # espeak emits a trailing space and sometimes tie-bars; drop both.
    # NFC so precomposed ũ/õ and u+combining-tilde tokenize identically.
    import unicodedata

    return unicodedata.normalize("NFC", text.strip().replace("͡", "").replace("͜", ""))


def tokenize_ipa(text: str, inventory: list[str] | None = None) -> list[Token]:
    """Tokenize an IPA string into phoneme tokens with stress attachment."""
    text = _normalize(text)
    multi = list(inventory) if inventory else []
    multi += [m for m in DEFAULT_MULTI if m not in multi]
    # Longest first so eɪ wins over e, ɐ̃ʊ̃ wins over ɐ̃.
    multi.sort(key=len, reverse=True)

    tokens: list[Token] = []
    pending_stress = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in (PRIMARY_STRESS, SECONDARY_STRESS, EXTRA_PRIMARY_STRESS, EXTRA_SECONDARY_STRESS):
            pending_stress = 1 if ch in (PRIMARY_STRESS, EXTRA_PRIMARY_STRESS) else 2
            i += 1
            continue
        if ch.isspace():
            i += 1
            continue
        if ch == "ː" and tokens:
            # Length mark attaches to the previous phoneme.
            tokens[-1].ipa += "ː"
            i += 1
            continue
        matched = None
        for unit in multi:
            if text.startswith(unit, i):
                matched = unit
                break
        if matched is None:
            matched = ch
        # Absorb combining diacritics following the token (unless already in it).
        j = i + len(matched)
        while j < len(text) and text[j] in _COMBINING:
            matched += text[j]
            j += 1
        tokens.append(Token(ipa=matched, stress=pending_stress))
        pending_stress = 0
        i = j
    return tokens


def vowel_nuclei(tokens: list[Token], vowels: set[str]) -> list[int]:
    """Indices of tokens that act as syllable nuclei."""
    return [k for k, t in enumerate(tokens) if t.ipa in vowels]
