"""Offline Marian translation (Helsinki-NLP Opus-MT), the primary provider.

One small model per language pair; pairs without a direct model pivot
through English (pt→de = pt→en + en→de), which covers every combination
of the shipped languages with 12 models. All models are Apache-2.0 or
CC-BY-4.0 and translate a phrase comfortably under a second on CPU.

Models are loaded lazily and kept in a small LRU so RAM stays bounded
(~0.3-1 GB per loaded model). When the weights are not in the local HF
cache the translator reports unavailable and the hosted chain takes over
— pre-download them with `python -m scripts.download_translation_models`
(the Docker image bakes them).
"""

from __future__ import annotations

import threading
from collections import OrderedDict

# (source, target) google codes → (model id, source token, target token).
# Tokens are the `>>id<<` sentence-initial labels some grouped Marian
# models require; single-pair models need none.
_MODELS: dict[tuple[str, str], tuple[str, str | None, str | None]] = {
    ("en", "pt"): ("Helsinki-NLP/opus-mt-tc-big-en-pt", None, "pob"),
    ("pt", "en"): ("Helsinki-NLP/opus-mt-ROMANCE-en", None, None),
    ("en", "es"): ("Helsinki-NLP/opus-mt-en-es", None, None),
    ("es", "en"): ("Helsinki-NLP/opus-mt-es-en", None, None),
    ("en", "de"): ("Helsinki-NLP/opus-mt-en-de", None, None),
    ("de", "en"): ("Helsinki-NLP/opus-mt-de-en", None, None),
    ("en", "fr"): ("Helsinki-NLP/opus-mt-en-fr", None, None),
    ("fr", "en"): ("Helsinki-NLP/opus-mt-fr-en", None, None),
    ("en", "it"): ("Helsinki-NLP/opus-mt-en-it", None, None),
    ("it", "en"): ("Helsinki-NLP/opus-mt-it-en", None, None),
    ("en", "ru"): ("Helsinki-NLP/opus-mt-en-ru", None, None),
    ("ru", "en"): ("Helsinki-NLP/opus-mt-ru-en", None, None),
}

MODEL_IDS = sorted({model for model, _, _ in _MODELS.values()})

MAX_LOADED_MODELS = 2
MAX_NEW_TOKENS = 128


def pair_plan(src: str, dst: str) -> list[tuple[str, str | None, str | None]]:
    """Model hops for a pair: direct when one exists, else pivot via English."""
    if src == dst:
        return []
    direct = _MODELS.get((src, dst))
    if direct:
        return [direct]
    via_en = _MODELS.get((src, "en"))
    back = _MODELS.get(("en", dst))
    if via_en and back:
        return [via_en, back]
    return []


class MarianTranslator:
    """Lazy, LRU-cached Marian MT models."""

    def __init__(self, max_loaded: int = MAX_LOADED_MODELS) -> None:
        self._cache: OrderedDict[str, tuple] = OrderedDict()
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()
        self._max_loaded = max_loaded

    def _load(self, model_id: str):
        from transformers import MarianMTModel, MarianTokenizer

        tokenizer = MarianTokenizer.from_pretrained(model_id)
        model = MarianMTModel.from_pretrained(model_id)
        model.eval()
        return model, tokenizer

    def _get(self, model_id: str):
        with self._lock:
            hit = self._cache.get(model_id)
            if hit is not None:
                self._cache.move_to_end(model_id)
                return hit
        with self._load_lock:
            with self._lock:
                hit = self._cache.get(model_id)
                if hit is not None:
                    self._cache.move_to_end(model_id)
                    return hit
            pair = self._load(model_id)
            with self._lock:
                self._cache[model_id] = pair
                self._cache.move_to_end(model_id)
                while len(self._cache) > self._max_loaded:
                    self._cache.popitem(last=False)
            return pair

    def _generate(
        self,
        model,
        tokenizer,
        text: str,
        src_token: str | None,
        dst_token: str | None,
    ) -> str:
        import torch

        prefix = ""
        if src_token:
            prefix += f">>{src_token}<< "
        if dst_token:
            prefix += f">>{dst_token}<< "
        batch = tokenizer(
            [prefix + text], return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            generated = model.generate(
                **batch, max_new_tokens=MAX_NEW_TOKENS, num_beams=4
            )
        return tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def translate(self, text: str, src: str, dst: str) -> str | None:
        plan = pair_plan(src, dst)
        if not plan:
            return None
        for model_id, src_token, dst_token in plan:
            model, tokenizer = self._get(model_id)
            text = self._generate(model, tokenizer, text, src_token, dst_token)
            if not text:
                return None
        return text or None


_translator: MarianTranslator | None = None
_translator_lock = threading.Lock()


def _translator_instance() -> MarianTranslator:
    global _translator
    with _translator_lock:
        if _translator is None:
            _translator = MarianTranslator()
        return _translator


def available() -> bool:
    """True when at least one pair model is already in the local HF cache.

    Without this guard, offline machines would stall the request path on
    a multi-minute download; pre-fetch instead (Docker bakes the models).
    """
    try:
        from huggingface_hub import try_to_load_from_cache

        for model_id in MODEL_IDS:
            if try_to_load_from_cache(model_id, "config.json") is not None:
                return True
    except Exception:
        return False
    return False


def translate(text: str, src: str, dst: str) -> str | None:
    """Marian translation; None when the pair is unsupported or the
    models are not cached locally."""
    if not text.strip() or src == dst:
        return None
    return _translator_instance().translate(text, src, dst)
