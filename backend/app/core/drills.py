"""Training cards for phonemes the learner's language doesn't have.

Descriptions are generated from panphon's feature vectors (place, manner,
voicing for consonants; height/backness/rounding for vowels), so any IPA
sound gets a card. Example words come from the target language's
`drill_words` data when available.
"""

from __future__ import annotations

from dataclasses import dataclass

import panphon

from app.core.g2p import get_g2p
from app.core.languages import Language
from app.core.tokenizer import tokenize_ipa

_FT = panphon.featuretable.FeatureTable()

_MANNER_HINTS = {
    "stop": "block the airflow completely, then release it",
    "fricative": "push a continuous stream of air through a narrow gap",
    "fricative (sibilant)": "push a continuous stream of air through a narrow gap, making a hissing sound",
    "nasal": "let the air come out through your nose",
    "approximant": "shape the sound without blocking or hissing the airflow",
    "lateral": "let the air flow over the sides of your tongue",
}

_PLACE_HINTS = {
    "labial": "bring your lips or lip and teeth together",
    "dental": "let the tip of your tongue touch or poke slightly between your upper teeth",
    "interdental": "let the tip of your tongue rest lightly between your teeth",
    "alveolar": "put the tip of your tongue on the ridge behind your upper teeth",
    "postalveolar": "put your tongue just behind the ridge above your upper teeth",
    "palatal": "raise the middle of your tongue toward the roof of your mouth",
    "velar": "raise the back of your tongue toward your soft palate",
    "glottal": "let the airflow pass through your open throat",
}


@dataclass
class Drill:
    sound: str
    description: str
    how_to: str
    native_note: str
    examples: list[dict]  # {word, ipa}

    def to_dict(self) -> dict:
        return {
            "sound": self.sound,
            "description": self.description,
            "how_to": self.how_to,
            "native_note": self.native_note,
            "examples": self.examples,
        }


def _describe_consonant(seg) -> tuple[str, str]:
    voi = "voiced" if seg["voi"] > 0 else "voiceless"
    if seg["cg"] > 0:
        place = "glottal"
    elif seg["lab"] > 0:
        place = "labial"
    elif seg["cor"] > 0:
        if seg["ant"] > 0:
            place = "dental"
        elif seg["distr"] > 0:
            place = "postalveolar"
        elif seg["hi"] > 0:
            place = "palatal"
        else:
            place = "alveolar"
    elif seg["hi"] > 0 and seg["back"] > 0:
        place = "velar"
    else:
        place = "alveolar"
    if seg["nas"] > 0:
        manner = "nasal"
    elif seg["lat"] > 0 and seg["son"] > 0:
        manner = "lateral"
    elif seg["cont"] > 0 and seg["strid"] > 0:
        manner = "fricative (sibilant)"
    elif seg["cont"] > 0:
        manner = "fricative"
    elif seg["son"] > 0:
        manner = "approximant"
    else:
        manner = "stop"
    return f"{voi} {place} {manner}", place


def _describe_vowel(seg) -> str:
    height = "close" if seg["hi"] > 0 else "open" if seg["lo"] > 0 else "mid"
    backness = "front" if seg["back"] < 0 else "back" if seg["back"] > 0 else "central"
    rounding = "rounded" if seg["round"] > 0 else "unrounded"
    nasal = " nasalized" if seg["nas"] > 0 else ""
    return f"{height} {backness} {rounding}{nasal} vowel"


def describe_sound(sound: str) -> str:
    """'θ' → 'voiceless dental fricative'; 'y' → 'close front rounded vowel'."""
    try:
        seg = _FT.fts(sound, normalize=False)
        if not seg:
            return sound
        if seg["syl"] > 0:
            return _describe_vowel(seg)
        desc, _ = _describe_consonant(seg)
        return desc
    except Exception:
        return sound


def _how_to(sound: str) -> str:
    try:
        seg = _FT.fts(sound, normalize=False)
        if not seg:
            return ""
        if seg["syl"] > 0:
            parts = []
            if seg["hi"] > 0:
                parts.append("raise your tongue high in your mouth")
            elif seg["lo"] > 0:
                parts.append("open your mouth wide and keep your tongue low")
            else:
                parts.append("keep your tongue at a middle height")
            if seg["back"] < 0:
                parts.append("toward the front")
            elif seg["back"] > 0:
                parts.append("toward the back")
            if seg["round"] > 0:
                parts.append("and round your lips")
            if seg["nas"] > 0:
                parts.append("let the air flow through your nose")
            return ", ".join(parts).capitalize()
        desc, place = _describe_consonant(seg)
        manner = desc.split()[-1]
        parts = [p for p in (_PLACE_HINTS.get(place, ""), _MANNER_HINTS.get(manner, "")) if p]
        return "; ".join(parts).capitalize() if parts else ""
    except Exception:
        return ""


def build_drill(sound: str, target: Language, native: Language) -> Drill:
    description = describe_sound(sound)
    how_to = _how_to(sound)
    substitute, _ = native.closest_sound(sound)
    sub_disp = native.orthography.get(substitute or "", substitute or sound)
    native_note = (
        f"{native.name} does not have this sound — the closest is “{sub_disp}” "
        f"(/ {substitute or sound} /), but swapping it changes the meaning of words."
    )
    examples = []
    words = target.drill_words.get(sound, [])[:3]
    if words:
        g2p = get_g2p()
        for word, tokens in zip(words, g2p.words(" ".join(words), target)):
            examples.append({"word": word, "ipa": " ".join(t.ipa for t in tokens)})
    return Drill(
        sound=sound,
        description=description,
        how_to=how_to,
        native_note=native_note,
        examples=examples,
    )
