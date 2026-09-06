"""Best-effort translation of the practiced word into the learner's language.

Free providers only, no API keys: Google (translate.google.com/m, parsed
directly — deep-translator's scraper is stale) first, MyMemory as fallback.
Every failure degrades to None — the app works fine without translations.
"""

from __future__ import annotations

import functools
import re
import threading

import requests

from app.core.languages import Language

_TIMEOUT_S = 5.0
_TRAILING_NOISE = re.compile(r"[\s.,;:!?\-…\"'“”«»()]+$")
_GOOGLE_RESULT = re.compile(r'class="(?:t0|result-container)"[^>]*>([^<]+)<')


def translate_word(text: str, source: Language, target: Language) -> str | None:
    """Translate `text` from the target language into the learner's language."""
    key = (
        text.strip(),
        source.translate.get("google", source.code),
        target.translate.get("google", target.code),
        source.translate.get("mymemory", ""),
        target.translate.get("mymemory", ""),
    )
    return _cached(*key)


@functools.lru_cache(maxsize=2048)
def _cached(text: str, google_from: str, google_to: str, my_from: str, my_to: str) -> str | None:
    providers: list[tuple[str, str, str]] = []
    if google_from and google_to:
        providers.append(("google", google_from, google_to))
    if my_from and my_to:
        providers.append(("mymemory", my_from, my_to))

    for name, src, dst in providers:
        result = _run_provider(name, text, src, dst)
        if result:
            return result
    return None


def _run_provider(name: str, text: str, src: str, dst: str) -> str | None:
    """Run one provider with a hard timeout so /api/analyze never hangs."""
    box: list[str | None] = [None]

    def work() -> None:
        try:
            if name == "google":
                box[0] = _google(text, src, dst)
            else:
                from deep_translator import MyMemoryTranslator

                box[0] = MyMemoryTranslator(source=src, target=dst).translate(text)
        except Exception:
            box[0] = None

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(_TIMEOUT_S)
    return clean_translation(box[0], text)


def _google(text: str, src: str, dst: str) -> str | None:
    resp = requests.get(
        "https://translate.google.com/m",
        params={"sl": src, "tl": dst, "q": text},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    match = _GOOGLE_RESULT.search(resp.text)
    return match.group(1) if match else None


def clean_translation(value: str | None, source_text: str) -> str | None:
    """Providers return noise: trailing punctuation, or an echo of the input."""
    if not value:
        return None
    value = value.strip()
    if not value or value.lower() == source_text.strip().lower():
        return None
    return _TRAILING_NOISE.sub("", value).strip() or None
