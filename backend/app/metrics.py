"""Prometheus metrics for spiik.

Every metric is registered here exactly once at import; the /metrics
endpoint in main.py exposes the default registry. Importing this module
is cheap and side-effect free (no model loading, no I/O) — safe for
tests and scripts.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "spiik_http_requests_total",
    "HTTP requests processed.",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "spiik_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
HTTP_IN_FLIGHT = Gauge(
    "spiik_http_requests_in_flight",
    "HTTP requests currently being served.",
)

ASSESS_LATENCY = Histogram(
    "spiik_assess_duration_seconds",
    "Pronunciation assessment latency (decode + recognize + align).",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
ASR_LATENCY = Histogram(
    "spiik_asr_duration_seconds",
    "Phoneme recognition (model inference) latency.",
    ["model"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
MODEL_LOADS = Counter(
    "spiik_model_loads_total",
    "Model weight loads (first use per process).",
    ["model", "outcome"],
)
MODEL_LOAD_SECONDS = Histogram(
    "spiik_model_load_duration_seconds",
    "Time spent loading model weights.",
    ["model"],
    buckets=(1, 5, 10, 30, 60, 120, 300),
)

TRANSLATIONS = Counter(
    "spiik_translations_total",
    "Translation provider attempts and their outcome.",
    ["provider", "outcome"],
)
TTS_SYNTH = Counter(
    "spiik_tts_total",
    "Speech synthesis by provider.",
    ["provider"],
)

BUILD_INFO = Gauge(
    "spiik_build_info",
    "Build metadata, always 1.",
    ["version", "engine"],
)


def record_build_info(version: str, engine: str) -> None:
    BUILD_INFO.labels(version, engine).set(1)
