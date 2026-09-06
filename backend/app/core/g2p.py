"""Grapheme-to-phoneme conversion via espeak-ng (phonemizer)."""

from __future__ import annotations

import re
import threading

from phonemizer.backend import EspeakBackend

from app.core.languages import Language
from app.core.tokenizer import Token, tokenize_ipa

_WORD_SPLIT = re.compile(r"([\w'’-]+)", re.UNICODE)


class G2P:
    """Thread-safe cache of espeak backends per language voice."""

    def __init__(self) -> None:
        self._backends: dict[str, EspeakBackend] = {}
        self._lock = threading.Lock()

    def _backend(self, voice: str) -> EspeakBackend:
        with self._lock:
            if voice not in self._backends:
                self._backends[voice] = EspeakBackend(
                    voice, with_stress=True, language_switch="remove-flags"
                )
            return self._backends[voice]

    def words(self, text: str, lang: Language) -> list[list[Token]]:
        """Phonemize text; returns one token list per input word."""
        words = [w for w in _WORD_SPLIT.split(text) if w and _WORD_SPLIT.fullmatch(w)]
        if not words:
            return []
        backend = self._backend(lang.espeak_voice)
        rows = backend.phonemize(words)
        out = []
        for word, row in zip(words, rows):
            out.append([t for t in tokenize_ipa(row, inventory=lang.inventory)])
        return out

    def phonemize(self, text: str, lang: Language) -> list[Token]:
        tokens: list[Token] = []
        for i, word in enumerate(self.words(text, lang)):
            for t in word:
                t.word_index = i
                tokens.append(t)
        return tokens


_g2p: G2P | None = None


def get_g2p() -> G2P:
    global _g2p
    if _g2p is None:
        _g2p = G2P()
    return _g2p
