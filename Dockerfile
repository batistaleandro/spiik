# spiik — pronunciation trainer via IPA approximation
#
# Multi-stage image: Node builds the frontend, Python runs the backend
# (which serves the built frontend). The wav2vec2 phoneme model (~1.3 GB)
# is baked in so the first request doesn't pay the download.

# ---- frontend build ---------------------------------------------------------
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- runtime ----------------------------------------------------------------
FROM python:3.13-slim

# SPIIK_VERSION: the release workflow passes the git tag; "dev" otherwise.
# BAKE_MODELS=false skips the ~2.5 GB model download (used by CI builds,
# which only verify that the image builds).
ARG SPIIK_VERSION=dev
ARG BAKE_MODELS=true
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 \
    SPIIK_VERSION=${SPIIK_VERSION}

LABEL org.opencontainers.image.title="spiik" \
    org.opencontainers.image.description="Pronunciation training via IPA approximation" \
    org.opencontainers.image.version="${SPIIK_VERSION}" \
    org.opencontainers.image.source="https://github.com/batistaleandro/spiik"

WORKDIR /opt/spiik

# espeak-ng: G2P + offline TTS fallback; ffmpeg: decode browser recordings.
# build-essential is needed only because editdistance (panphon dep) has no
# aarch64 wheel — installed and purged in the same layer as the pip build.
COPY backend/requirements.txt backend/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng ffmpeg curl build-essential \
    && pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r backend/requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# app code (layout mirrors the repo: backend resolves ../frontend/dist)
COPY backend/app backend/app
COPY backend/data backend/data
COPY backend/scripts backend/scripts
COPY backend/tests backend/tests
COPY --from=frontend-build /app/frontend/dist frontend/dist

# bake the wav2vec2 phoneme model + the Marian translation models
# (offline phrase translation) — skipped when BAKE_MODELS=false.
# PYTHONPATH: the app package lives at /opt/spiik/backend/app and the
# working directory here is /opt/spiik
RUN if [ "$BAKE_MODELS" = "true" ]; then \
        python -c "from huggingface_hub import snapshot_download; snapshot_download('facebook/wav2vec2-lv-60-espeak-cv-ft')" \
        && PYTHONPATH=backend python -c "from app.translate_local import MODEL_IDS; \
from huggingface_hub import snapshot_download; \
[snapshot_download(model_id) for model_id in MODEL_IDS]"; \
    fi

RUN useradd -m spiik \
    && mkdir -p /cache/huggingface /data \
    && chown -R spiik:spiik /opt/spiik /cache/huggingface /data

# accounts + saved words live in SQLite at /data (mounted as a volume)
ENV SPIIK_DB=/data/spiik.db
USER spiik

WORKDIR /opt/spiik/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -sf http://localhost:8000/api/health >/dev/null || exit 1

# WEB_CONCURRENCY scales CPU-bound inference across worker processes
# (each worker loads its own model copies — see README "Scaling")
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
