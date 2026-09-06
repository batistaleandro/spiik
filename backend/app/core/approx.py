"""IPA → native-language orthographic approximation.

For a target-language word (as IPA tokens), every phoneme that exists in the
learner's native language is rendered with its native spelling; foreign
phonemes are substituted with the closest native sound and flagged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.languages import MINOR_DISTANCE, Language
from app.core.tokenizer import Token


@dataclass
class PhonemeOut:
    ipa: str
    status: str  # native | foreign
    display: str  # orthography in the learner's language
    substitute: str | None = None  # native sound used for a foreign phoneme
    minor: bool = False  # foreign but very close to a native sound
    stress: int = 0

    def to_dict(self) -> dict:
        return {
            "ipa": self.ipa,
            "status": self.status,
            "display": self.display,
            "substitute": self.substitute,
            "minor": self.minor,
            "stress": self.stress,
        }


@dataclass
class Chunk:
    """Display chunk = onset consonants + vowel nucleus + coda (cri-ei-chion)."""

    phonemes: list[PhonemeOut]
    text: str
    status: str  # native | foreign
    stressed: bool
    word_index: int

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "status": self.status,
            "stressed": self.stressed,
            "word_index": self.word_index,
            "phonemes": [p.to_dict() for p in self.phonemes],
        }


@dataclass
class MissingSound:
    ipa: str
    substitute: str
    substitute_display: str
    minor: bool
    distance: float

    def to_dict(self) -> dict:
        return {
            "ipa": self.ipa,
            "substitute": self.substitute,
            "substitute_display": self.substitute_display,
            "minor": self.minor,
            "distance": self.distance,
        }


@dataclass
class ApproxResult:
    chunks: list[Chunk] = field(default_factory=list)
    missing_sounds: list[MissingSound] = field(default_factory=list)

    @property
    def text(self) -> str:
        parts: list[str] = []
        word_chunks: list[str] = []
        word_index = 0
        for chunk in self.chunks:
            if chunk.word_index != word_index and word_chunks:
                parts.append("-".join(word_chunks))
                word_chunks = []
            word_index = chunk.word_index
            word_chunks.append(chunk.text)
        if word_chunks:
            parts.append("-".join(word_chunks))
        return " ".join(parts)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "chunks": [c.to_dict() for c in self.chunks],
            "missing_sounds": [m.to_dict() for m in self.missing_sounds],
        }


def _phoneme_out(token: Token, native: Language) -> PhonemeOut:
    if token.ipa in native.inventory:
        return PhonemeOut(
            ipa=token.ipa,
            status="native",
            display=native.orthography.get(token.ipa, token.ipa),
            stress=token.stress,
        )
    substitute, distance = native.closest_sound(token.ipa)
    sub_display = native.orthography.get(substitute or "", token.ipa)
    return PhonemeOut(
        ipa=token.ipa,
        status="foreign",
        display=sub_display,
        substitute=substitute,
        minor=bool(substitute)
        and (distance <= MINOR_DISTANCE or token.ipa in native.minor_foreign),
        stress=token.stress,
    )


def _group_chunks(
    tokens: list[PhonemeOut], raw: list[Token], vowels: set[str]
) -> list[Chunk]:
    """Group a word's phonemes into display chunks with onset maximization:
    consonants between two vowels start the next syllable's chunk, only
    word-final consonants are a coda of the previous one ("cri-ei-chan")."""
    chunks: list[Chunk] = []
    word_start = 0
    total = len(tokens)

    def close_word(end: int) -> None:
        nonlocal word_start
        word_tokens = list(range(word_start, end))
        if not word_tokens:
            word_start = end
            return
        vowel_positions = [i for i in word_tokens if raw[i].ipa in vowels]
        if not vowel_positions:
            chunks.append(_make_chunk(tokens, raw, word_tokens, word_tokens[0]))
            word_start = end
            return
        groups: list[list[int]] = []
        prev_vowel = None
        for vp in vowel_positions:
            if prev_vowel is None:
                groups.append(list(range(word_tokens[0], vp + 1)))
            else:
                # consonants after the previous vowel start this chunk
                groups.append(list(range(prev_vowel + 1, vp + 1)))
            prev_vowel = vp
        # trailing consonants after the last vowel: coda of the last chunk
        for i in range(prev_vowel + 1, word_tokens[-1] + 1):
            groups[-1].append(i)
        for group in groups:
            chunks.append(_make_chunk(tokens, raw, group, group[0]))
        word_start = end

    for i in range(total):
        if i + 1 == total or raw[i + 1].word_index != raw[i].word_index:
            close_word(i + 1)
    return chunks


def _make_chunk(
    tokens: list[PhonemeOut], raw: list[Token], indices: list[int], first_index: int
) -> Chunk:
    return Chunk(
        phonemes=[tokens[i] for i in indices],
        text="".join(tokens[i].display for i in indices),
        status="foreign"
        if any(tokens[i].status == "foreign" for i in indices)
        else "native",
        stressed=any(raw[i].stress == 1 for i in indices),
        word_index=raw[first_index].word_index,
    )


def approximate(tokens: list[Token], target: Language, native: Language) -> ApproxResult:
    vowels = set(target.vowels)
    phonemes = [_phoneme_out(t, native) for t in tokens]
    chunks = _group_chunks(phonemes, tokens, vowels)

    missing: dict[str, MissingSound] = {}
    for p in phonemes:
        if p.status == "foreign" and p.ipa not in missing:
            substitute, distance = native.closest_sound(p.ipa)
            missing[p.ipa] = MissingSound(
                ipa=p.ipa,
                substitute=substitute or p.ipa,
                substitute_display=native.orthography.get(substitute or "", p.ipa),
                minor=bool(substitute)
                and (distance <= MINOR_DISTANCE or p.ipa in native.minor_foreign),
                distance=round(distance, 3),
            )
    return ApproxResult(chunks=chunks, missing_sounds=list(missing.values()))
