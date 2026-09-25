"""Spiik API: pronunciation training via IPA approximation."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.audio import decode_to_16k_mono
from app.core.align import align, score, verdicts
from app.core.drills import build_drill
from app.core.g2p import get_g2p
from app.core.languages import load_language, list_languages
from app.db import init_db
from app.engines.base import get_engine
from app.metrics import (
    ASSESS_LATENCY,
    HTTP_IN_FLIGHT,
    HTTP_LATENCY,
    HTTP_REQUESTS,
    record_build_info,
)
from app.pipeline import run_analysis
from app.routers.auth import router as auth_router
from app.routers.pronunciation import router as pronunciation_router
from app.routers.words import router as words_router
from app.tts import synthesize
from app.version import VERSION

init_db()

app = FastAPI(
    title="spiik",
    description="Pronunciation training via IPA approximation",
    version=VERSION,
)
app.include_router(auth_router)
app.include_router(words_router)
app.include_router(pronunciation_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# engine selection: SPIIK_ENGINE=local|azure (default local)
import os

ENGINE_NAME = os.environ.get("SPIIK_ENGINE", "local")
record_build_info(VERSION, ENGINE_NAME)


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    """Count and time every request by templated route.

    /metrics itself is excluded so scraping doesn't pollute the series
    it reads.
    """
    HTTP_IN_FLIGHT.inc()
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        HTTP_IN_FLIGHT.dec()
        if request.url.path != "/metrics":
            route = getattr(request.scope.get("route"), "path", "unmatched")
            HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            HTTP_LATENCY.labels(request.method, route).observe(
                time.perf_counter() - start
            )


class AnalyzeRequest(BaseModel):
    native: str = Field(description="learner's language code, e.g. pt-br")
    target: str = Field(description="language being learned, e.g. en-us")
    text: str = Field(description="word or phrase to practice")
    input_lang: str = Field(
        default="target",
        description="which language `text` is in: 'target' (default) or 'native' — "
        "when 'native', text is translated into the target language first",
    )


@app.get("/api/health")
def health():
    """Liveness + build identity; used by the Docker healthcheck."""
    return {"status": "ok", "version": VERSION, "engine": ENGINE_NAME}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/languages")
def get_languages():
    return [
        {"code": lang.code, "name": lang.name, "tts_voice": lang.tts_voice}
        for lang in list_languages()
    ]


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """Word/phrase → IPA + native-language approximation + missing sounds.

    With input_lang='native', `text` is translated from the learner's
    language into the target language first; the response carries both the
    original query and the practice word.
    """
    return run_analysis(req.native, req.target, req.text, req.input_lang)


@app.post("/api/assess")
async def assess(
    audio: UploadFile = File(...),
    expected_ipa: str = Form(...),
    native: str = Form(...),
    target: str = Form(...),
):
    """Score a recording against the expected IPA sequence."""
    try:
        load_language(target)
        load_language(native)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc

    data = await audio.read()
    if not data:
        raise HTTPException(422, "empty audio upload")

    # decode + torch inference + alignment are CPU-bound; keep them off
    # the event loop so slow recognitions can't stall the whole app
    with ASSESS_LATENCY.time():
        result = await run_in_threadpool(
            _assess_bytes, data, expected_ipa, native, target
        )
    if isinstance(result, tuple):  # (status_code, detail) error
        raise HTTPException(result[0], result[1])
    return result


def _assess_bytes(
    data: bytes, expected_ipa: str, native: str, target: str
) -> dict | tuple[int, str]:
    try:
        target_lang = load_language(target)
        native_lang = load_language(native)
    except KeyError as exc:
        return (404, str(exc))

    try:
        samples, sr = decode_to_16k_mono(data)
    except ValueError as exc:
        return (422, str(exc))
    if len(samples) < sr * 0.2:
        return (
            422,
            "recording too short — hold the button while speaking",
        )

    expected = expected_ipa.split()
    engine = get_engine(ENGINE_NAME)
    try:
        recognized = engine.transcribe(samples, sr)
    except NotImplementedError as exc:
        return (501, str(exc))

    # normalize espeak-version token drift (e.g. model sʲ ≈ G2P s + ʲ)
    expanded: list[str] = []
    for token in recognized:
        expanded.extend(target_lang.recognized_aliases.get(token, [token]))
    recognized = expanded

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
# The catch-all falls back to index.html so SPA routes like /practice
# survive a page refresh; real files (assets, favicon) are served as-is.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.exists():
    if (_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path:
            candidate = (_DIST / full_path).resolve()
            if candidate.is_file() and str(candidate).startswith(str(_DIST)):
                return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
