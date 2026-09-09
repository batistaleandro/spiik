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

WORKDIR /opt/spiik
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1

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

# bake the wav2vec2 phoneme model
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('facebook/wav2vec2-lv-60-espeak-cv-ft')"

RUN useradd -m spiik \
    && mkdir -p /cache/huggingface \
    && chown -R spiik:spiik /opt/spiik /cache/huggingface
USER spiik

WORKDIR /opt/spiik/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -sf http://localhost:8000/api/languages >/dev/null || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
