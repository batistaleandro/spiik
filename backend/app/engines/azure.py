"""Azure Speech pronunciation-assessment adapter (stub for the hybrid design).

To enable: set AZURE_SPEECH_KEY + AZURE_SPEECH_REGION and implement
`transcribe` by calling the pronunciation assessment API, which returns
per-phoneme accuracy directly. The result should still be reduced to a
list of IPA phoneme strings so the alignment layer stays unchanged.
"""

from __future__ import annotations

import numpy as np


class AzureEngine:
    def __init__(self) -> None:
        import os

        self.key = os.environ.get("AZURE_SPEECH_KEY")
        self.region = os.environ.get("AZURE_SPEECH_REGION")

    @property
    def configured(self) -> bool:
        return bool(self.key and self.region)

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> list[str]:
        raise NotImplementedError(
            "Azure engine is not implemented yet; use engine=local "
            "(set AZURE_SPEECH_KEY/AZURE_SPEECH_REGION and implement "
            "app/engines/azure.py to enable it)."
        )
