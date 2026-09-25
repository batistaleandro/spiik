"""Best-effort translation into the learner's language.

Provider chain, first success wins, every failure degrades to None:

1. local Marian models (offline, when the weights are cached and
   SPIIK_TRANSLATE allows it) — see app/translate_local.py
2. Google's keyless endpoints (gtx JSON, falling back to Chrome's
   dict-chrome-ex when gtx rate-limits) — handles phrases
3. MyMemory (translation-memory matches, small anonymous quota)

Free providers only, no API keys. `SPIIK_TRANSLATE=auto|online|off`
selects how much of the chain runs (auto = local first when available).
"""

from __future__ import annotations

import html
import os
import re
import sys
import threading
from collections import OrderedDict

import requests

from app.core.languages import Language
from app import translate_local
from app.metrics import TRANSLATIONS

_TIMEOUT_S = 5.0
# the first local call in a process loads model weights (~seconds);
# hosted providers must answer inside the normal budget
_LOCAL_TIMEOUT_S = 60.0
_TRAILING_NOISE = re.compile(r"[\s.,;:!?\-…\"'“”«»()]+$")
_CACHE_MAX = 2048

# only successful results from the trusted providers are cached: failed
# calls and MyMemory TM matches must be retried on the next request, or a
# transient garbage answer would stick for the lifetime of the process
_cache: "OrderedDict[tuple, str]" = OrderedDict()
_cache_lock = threading.Lock()


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


def translate_for_practice(text: str, source: Language, target: Language) -> str | None:
    """Translate the learner's own word into the language being practiced.

    Unlike translate_word, an echo (same word in both languages, "hotel" →
    "hotel") is a valid result, and only the first candidate is kept —
    "сливки, сливочное масло" gives the practice word "сливки".
    """
    key = (
        text.strip(),
        source.translate.get("google", source.code),
        target.translate.get("google", target.code),
        source.translate.get("mymemory", ""),
        target.translate.get("mymemory", ""),
    )
    return _cached(*key, allow_echo=True)


def _cache_put(key: tuple, value: str) -> None:
    with _cache_lock:
        _cache[key] = value
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


def _cached(
    text: str,
    google_from: str,
    google_to: str,
    my_from: str,
    my_to: str,
    allow_echo: bool = False,
) -> str | None:
    """Provider chain with a success-only cache.

    `_cached.cache_clear()` is kept for the tests.
    """
    key = (text, google_from, google_to, my_from, my_to, allow_echo)
    mode = os.environ.get("SPIIK_TRANSLATE", "auto").strip().lower()
    if mode == "off":
        return None
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    providers: list[tuple[str, str, str]] = []
    if mode != "online" and translate_local.available():
        providers.append(("local", google_from, google_to))
    providers.append(("google", google_from, google_to))
    if my_from and my_to:
        providers.append(("mymemory", my_from, my_to))

    for name, src, dst in providers:
        result = _run_provider(name, text, src, dst, allow_echo=allow_echo)
        if result:
            if name in ("local", "google"):
                _cache_put(key, result)
            return result
    return None


_cached.cache_clear = _cache.clear  # type: ignore[attr-defined]


def _run_provider(
    name: str, text: str, src: str, dst: str, allow_echo: bool = False
) -> str | None:
    """Run one provider with a hard timeout so /api/analyze never hangs.

    A recording-time detail: the first local call in a process pays the
    model-weight load, so it gets a generous budget; hosted providers
    must answer inside the normal one.
    """
    box: list[str | None] = [None]
    timeout = _LOCAL_TIMEOUT_S if name == "local" else _TIMEOUT_S

    def work() -> None:
        try:
            if name == "local":
                from app.translate_local import translate as local_translate

                box[0] = local_translate(text, src, dst)
            elif name == "google":
                box[0] = _google(text, src, dst)
            else:
                from deep_translator import MyMemoryTranslator

                email = os.environ.get("SPIIK_MM_EMAIL") or None
                box[0] = MyMemoryTranslator(
                    source=src, target=dst, email=email
                ).translate(text)
        except Exception as exc:
            # best-effort chain: failures fall through, but land in the
            # server log so broken providers are visible
            print(f"[translate] {name} failed: {exc}", file=sys.stderr, flush=True)
            box[0] = None

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    thread.join(timeout)
    # first_only exists to pick one candidate word ("мир, свет" → "мир");
    # phrases must survive intact
    first_only = allow_echo and " " not in text.strip()
    result = clean_translation(
        box[0], text, allow_echo=allow_echo, first_only=first_only
    )
    TRANSLATIONS.labels(name, "ok" if result else "empty").inc()
    return result


def _google(text: str, src: str, dst: str) -> str | None:
    """Google's keyless endpoints. Primary: the gtx JSON endpoint
    (client=gtx) with per-sentence segments. It rate-limits hard by IP
    (429 for every request once flagged), so a failure falls back to the
    Chrome dict-chrome-ex endpoint, which has a separate quota and returns
    a plain JSON array of translated segments."""
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "dj": "1",
                "dt": "t",
                "sl": src,
                "tl": dst,
                "q": text,
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
        parsed = _parse_gtx(resp.json())
        if parsed:
            return parsed
    except requests.RequestException:
        pass
    resp = requests.get(
        "https://clients5.google.com/translate_a/t",
        params={"client": "dict-chrome-ex", "sl": src, "tl": dst, "q": text},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    return _parse_chrome(resp.json())


def _parse_gtx(data: dict) -> str | None:
    sentences = data.get("sentences") if isinstance(data, dict) else None
    if not sentences:
        return None
    out = "".join(s.get("trans", "") for s in sentences if isinstance(s, dict))
    return out or None


def _parse_chrome(data) -> str | None:
    """dict-chrome-ex answers ["สวัสดี"] or, for some responses, a list of
    ["trans", "orig", ...] rows — take the translated string of each."""
    if not isinstance(data, list):
        return None
    out = ""
    for item in data:
        if isinstance(item, str):
            out += item
        elif isinstance(item, list) and item and isinstance(item[0], str):
            out += item[0]
    return out or None


def clean_translation(
    value: str | None, source_text: str, allow_echo: bool = False, first_only: bool = False
) -> str | None:
    """Providers return noise: trailing punctuation, or an echo of the input.

    With first_only, multi-candidate answers ("мир, свет") are cut to the
    first candidate — used when picking the word to practice.
    """
    if not value:
        return None
    # providers leak HTML entities ("mundo&#xA0"), sometimes double-escaped —
    # unescape until stable before any other cleaning
    for _ in range(3):
        unescaped = html.unescape(value)
        if unescaped == value:
            break
        value = unescaped
    value = value.strip()
    if not value:
        return None
    if first_only:
        value = re.split(r"[,;/]", value)[0].strip()
        if not value:
            return None
    if not allow_echo and value.lower() == source_text.strip().lower():
        return None
    return _TRAILING_NOISE.sub("", value).strip() or None
