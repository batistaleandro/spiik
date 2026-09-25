"""TTS: edge-tts (neural, free) with espeak-ng offline fallback."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

from app.core.languages import Language
from app.metrics import TTS_SYNTH


async def synthesize(text: str, lang: Language) -> tuple[bytes, str]:
    """Return (audio_bytes, media_type) for `text` spoken in `lang`."""
    try:
        audio = await _edge_tts(text, lang.tts_voice)
        TTS_SYNTH.labels("edge-tts").inc()
        return audio, "audio/mpeg"
    except Exception:
        TTS_SYNTH.labels("espeak").inc()
        return _espeak_tts(text, lang.espeak_voice), "audio/wav"


async def _edge_tts(text: str, voice: str) -> bytes:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    if not chunks:
        raise RuntimeError("edge-tts produced no audio")
    return b"".join(chunks)


def _espeak_tts(text: str, voice: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        subprocess.run(
            ["espeak-ng", "-v", voice, "-s", "140", "-w", str(path), text],
            check=True,
            capture_output=True,
        )
        return path.read_bytes()
    finally:
        path.unlink(missing_ok=True)


def run_async(coro):
    """Run an async coroutine from sync code (FastAPI calls the async path
    directly; this helper exists for scripts/tests)."""
    return asyncio.run(coro)
