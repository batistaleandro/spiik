"""Scoring engine interface (hybrid: local wav2vec2 now, Azure later)."""

from __future__ import annotations

from typing import Protocol

import numpy as np


class ScoringEngine(Protocol):
    """A phoneme recognizer: audio → IPA phoneme strings."""

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> list[str]:
        """Return recognized IPA phoneme tokens for 16 kHz mono audio."""
        ...


def get_engine(name: str):
    if name == "azure":
        from app.engines.azure import AzureEngine

        return AzureEngine()
    from app.engines.local import LocalEngine

    return LocalEngine()
