"""Local phoneme recognizer: facebook/wav2vec2-lv-60-espeak-cv-ft.

The model was trained on Common Voice data transcribed with espeak phonemes,
so its output tokens match the espeak G2P tokens used for the expected
pronunciation. First use downloads ~1.3 GB and is slow.
"""

from __future__ import annotations

import threading
import unicodedata

import numpy as np

MODEL_ID = "facebook/wav2vec2-lv-60-espeak-cv-ft"

# espeak emits these marks; the model never should — normalize anyway.
# 'H' is the espeak h-insertion flag, '.' the syllable dot in labels like i.5.
_STRIP_CHARS = {"H", "."}


class LocalEngine:
    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._blank_id: int | None = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            import torch
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

            self._processor = Wav2Vec2Processor.from_pretrained(MODEL_ID)
            self._model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID)
            self._model.eval()
            self._blank_id = self._processor.tokenizer.pad_token_id
            self._torch = torch

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> list[str]:
        self._ensure_loaded()
        assert self._processor is not None and self._model is not None
        torch = self._torch

        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sample_rate != 16000:
            import torchaudio.functional as AF

            audio = AF.resample(torch.from_numpy(audio).float(), sample_rate, 16000).numpy()
        audio = np.clip(audio, -1.0, 1.0).astype(np.float32)

        inputs = self._processor(
            audio, sampling_rate=16000, return_tensors="pt", padding=True
        )
        with torch.no_grad():
            logits = self._model(inputs.input_values).logits
        predicted = torch.argmax(logits, dim=-1)[0].tolist()

        # CTC decode: collapse repeats, drop blanks.
        tokens: list[str] = []
        prev = -1
        vocab = self._processor.tokenizer.convert_ids_to_tokens
        for idx in predicted:
            if idx != prev and idx != self._blank_id:
                label = vocab(idx)
                if label:
                    tokens.append(self._normalize_label(label))
            prev = idx
        return [t for t in tokens if t]

    @staticmethod
    def _normalize_label(label: str) -> str:
        # espeak digits (i5 = stressed i) and flag punctuation are dropped;
        # combining marks are kept attached via NFC.
        label = unicodedata.normalize("NFC", label)
        label = "".join(ch for ch in label if not ch.isdigit() and ch not in _STRIP_CHARS)
        return label.strip()
