"""Audio decoding: any browser recording (webm/opus, mp4, wav) → 16 kHz mono float32."""

from __future__ import annotations

import io
import subprocess

import numpy as np
import soundfile as sf


def decode_to_16k_mono(data: bytes) -> tuple[np.ndarray, int]:
    """Decode arbitrary audio bytes via ffmpeg to 16 kHz mono float32."""
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-i", "pipe:0",
                "-ac", "1",
                "-ar", "16000",
                "-f", "wav",
                "pipe:1",
            ],
            input=data,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"could not decode audio: {exc.stderr.decode(errors='replace')[:200]}") from exc
    audio, sr = sf.read(io.BytesIO(proc.stdout), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio, sr
