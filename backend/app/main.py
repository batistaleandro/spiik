"""Spiik API: pronunciation training via IPA approximation."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.audio import decode_to_16k_mono
from app.core.align import align, score, verdicts
from app.core.approx import approximate
from app.core.drills import build_drill
from app.core.g2p import get_g2p
from app.core.languages import load_language, list_languages
from app.engines.base import get_engine
from app.tts import synthesize

app = FastAPI(title="spiik", description="Pronunciation training via IPA approximation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# engine selection: SPIIK_ENGINE=local|azure (default local)
import os

ENGINE_NAME = os.environ.get("SPIIK_ENGINE", "local")


class AnalyzeRequest(BaseModel):
    native: str = Field(description="learner's language code, e.g. pt-br")
    target: str = Field(description="language being learned, e.g. en-us")
    text: str = Field(description="word or phrase to practice")


@app.get("/api/languages")
def get_languages():
    return [
        {"code": lang.code, "name": lang.name, "tts_voice": lang.tts_voice}
        for lang in list_languages()
    ]


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """Word/phrase → IPA + native-language approximation + missing sounds."""
    try:
        target = load_language(req.target)
        native = load_language(req.native)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    g2p = get_g2p()
    word_tokens = g2p.words(req.text, target)
    if not word_tokens or not any(word_tokens):
        raise HTTPException(422, f"could not phonemize: {req.text!r}")

    chunks: list[dict] = []
    missing_sounds: dict[str, dict] = {}
    expected_ipa: list[str] = []
    for word_index, tokens in enumerate(word_tokens):
        for token in tokens:
            token.word_index = word_index
        result = approximate(tokens, target, native)
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
        "text": req.text,
        "native": {"code": native.code, "name": native.name},
        "target": {"code": target.code, "name": target.name},
        "approximation": " ".join(words_out),
        "chunks": chunks,
        "missing_sounds": list(missing_sounds.values()),
        "expected_ipa": expected_ipa,
    }


@app.post("/api/assess")
async def assess(
    audio: UploadFile = File(...),
    expected_ipa: str = Form(...),
    native: str = Form(...),
    target: str = Form(...),
):
    """Score a recording against the expected IPA sequence."""
    try:
        target_lang = load_language(target)
        native_lang = load_language(native)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc

    data = await audio.read()
    if not data:
        raise HTTPException(422, "empty audio upload")
    try:
        samples, sr = decode_to_16k_mono(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if len(samples) < sr * 0.2:
        raise HTTPException(422, "recording too short — hold the button while speaking")

    expected = expected_ipa.split()
    engine = get_engine(ENGINE_NAME)
    try:
        recognized = engine.transcribe(samples, sr)
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc)) from exc

    if not recognized:
        return {
            "recognized_ipa": [],
            "score": 0,
            "verdicts": [],
            "message": "no speech detected — try again, a bit louder",
        }

    pairs = align(expected, recognized)
    verdict_list = verdicts(pairs, target_lang, native_lang)
    extras = sum(1 for p in pairs if p.expected is None)
    return {
        "recognized_ipa": recognized,
        "score": score(len(expected), verdict_list, extras),
        "verdicts": [v.to_dict() for v in verdict_list],
        "extra_sounds": [p.recognized for p in pairs if p.expected is None],
    }


@app.post("/api/tts")
async def tts(req: AnalyzeRequest):
    """Speak `text` with the voice of the `target` language."""
    try:
        target = load_language(req.target)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    body, media_type = await synthesize(req.text, target)
    return Response(content=body, media_type=media_type)


@app.get("/api/drill")
def drill(sound: str, target: str, native: str):
    """Training card for a sound missing in the learner's language."""
    try:
        target_lang = load_language(target)
        native_lang = load_language(native)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return build_drill(sound, target_lang, native_lang).to_dict()


# Serve the built frontend (production single-process deployment).
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
