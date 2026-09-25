"""Shared analyze pipeline: text → IPA + native-language approximation.

Used by both POST /api/analyze and POST /api/words (saving a word runs
the same deterministic analysis server-side so cards are self-contained).
"""

from __future__ import annotations

from fastapi import HTTPException

from app.core.approx import approximate
from app.core.g2p import get_g2p
from app.core.languages import load_language
from app.translate import translate_for_practice, translate_word


def run_analysis(
    native: str,
    target: str,
    text: str,
    input_lang: str = "target",
    translated_override: str | None = None,
) -> dict:
    """Analyze `text` for a native/target pair.

    `translated_override` carries the translation the client already
    showed the user (the trainer chip) so saving a word doesn't depend on
    a second provider round-trip.
    """
    try:
        target_lang = load_language(target)
        native_lang = load_language(native)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    g2p = get_g2p()

    query = text.strip()
    if input_lang == "native":
        try:
            practice_text = translate_for_practice(query, native_lang, target_lang)
        except Exception:
            practice_text = None
        if not practice_text:
            raise HTTPException(
                422,
                f"could not translate “{query}” into {target_lang.name} — "
                f"try typing the word in {target_lang.name} directly",
            )
        translated = query  # the chip shows the word the user typed
    else:
        practice_text = query
        translated = None
        if translated_override is None:
            # no meaning came from the client — resolve one; when it did,
            # a fresh provider round-trip can only add latency and garbage
            try:
                translated = translate_word(query, target_lang, native_lang)
            except Exception:
                translated = None
    if translated_override is not None:
        # the client already showed the user this translation — it wins
        # over a fresh (possibly flaky) provider round-trip
        translated = translated_override

    word_tokens = g2p.words(practice_text, target_lang)
    if not word_tokens or not any(word_tokens):
        raise HTTPException(422, f"could not phonemize: {practice_text!r}")

    chunks: list[dict] = []
    missing_sounds: dict[str, dict] = {}
    expected_ipa: list[str] = []
    for word_index, tokens in enumerate(word_tokens):
        for token in tokens:
            token.word_index = word_index
        result = approximate(tokens, target_lang, native_lang)
        chunks.extend(c.to_dict() for c in result.chunks)
        for m in result.missing_sounds:
            missing_sounds.setdefault(m.ipa, m.to_dict())
        expected_ipa.extend(t.ipa for t in tokens)

    # group chunk texts by word: "cri-ei-chan" for each word, words joined by space
    words_out: list[str] = []
    current_word: list[str] = []
    current_index = 0
    for chunk in chunks:
        if chunk["word_index"] != current_index and current_word:
            words_out.append("-".join(current_word))
            current_word = []
        current_index = chunk["word_index"]
        current_word.append(chunk["text"])
    if current_word:
        words_out.append("-".join(current_word))

    return {
        "text": practice_text,
        "query": query,
        "input_lang": input_lang,
        "native": {"code": native_lang.code, "name": native_lang.name},
        "target": {"code": target_lang.code, "name": target_lang.name},
        "translated": translated,
        "approximation": " ".join(words_out),
        "chunks": chunks,
        "missing_sounds": list(missing_sounds.values()),
        "expected_ipa": expected_ipa,
    }
