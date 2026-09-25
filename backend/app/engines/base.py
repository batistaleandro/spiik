"""Scoring engine interface (hybrid: local wav2vec2 now, Azure later)."""

from __future__ import annotations

import threading
from typing import Protocol

import numpy as np


class ScoringEngine(Protocol):
    """A phoneme recognizer: audio → IPA phoneme strings."""

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> list[str]:
        """Return recognized IPA phoneme tokens for 16 kHz mono audio."""
        ...


# one engine instance per process: weights load lazily on first use and
# must never be reloaded per request (the local engine is ~1.3 GB)
_engine_lock = threading.Lock()
_engines: dict[str, object] = {}


def get_engine(name: str):
    with _engine_lock:
        engine = _engines.get(name)
        if engine is None:
            engine = _create_engine(name)
            _engines[name] = engine
        return engine


def _create_engine(name: str):
    if name == "azure":
        from app.engines.azure import AzureEngine

        return AzureEngine()
    from app.engines.local import LocalEngine

    return LocalEngine()
