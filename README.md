# spiik.

Learn pronunciation by approximating a foreign language into your own. Spiik
compares the **International Phonetic Alphabet (IPA)** of both languages to:

1. **Write foreign words the way they sound to you** — `creation` → `kri-ei-chan`
   for a Brazilian Portuguese speaker; `think` → `sinc`.
2. **Show what the word means** — a translation into the learner's language
   (free providers: Google with MyMemory fallback, best-effort).
3. **Listen to your attempt and score every phoneme** — a wav2vec2 model
   recognizes the IPA sounds you actually produced, and a feature-weighted
   alignment against the expected IPA marks each sound correct / close / wrong / missing.
4. **Train the sounds your language doesn't have** — /θ/ doesn't exist in
   Portuguese? Spiik generates a drill card from the phoneme's IPA features
   (place, manner, voicing) with coaching text, minimal-pair examples and audio.
5. **Remember the words you learn** — create an account, save words, and
   review them with spaced repetition (simplified SM-2): rate each word
   Again / Hard / Good / Easy and spiik schedules the next review, tracking
   your confidence and progress per word.

Any language pair works out of the box: the engine is driven by per-language
data files (phoneme inventory, native orthography, substitution preferences),
not per-pair tables.

Shipped features and what's planned next live in the
[roadmap](ROADMAP.md).

## Stack

| Layer      | Technology                                                          |
|------------|---------------------------------------------------------------------|
| Backend    | Python 3.13, FastAPI                                                |
| Text→IPA   | espeak-ng via `phonemizer`                                          |
| Audio→IPA  | `facebook/wav2vec2-lv-60-espeak-cv-ft` (CTC, outputs IPA directly)  |
| Distances  | `panphon` feature-weighted phoneme distances                        |
| TTS        | edge-tts (free neural voices) with espeak-ng offline fallback       |
| Translate  | offline Marian (Opus-MT) → Google gtx → MyMemory (best-effort chain) |
| Frontend   | Vite + React + TypeScript                                           |
| Accounts   | SQLite (SQLAlchemy), bcrypt passwords, JWT bearer sessions          |

## Setup

```bash
# system deps (macOS)
brew install espeak-ng ffmpeg

# backend
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt

# frontend
cd ../frontend
npm install
npm run build        # served by the backend at /
```

## Run

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --port 8900
# open http://localhost:8900
```

First pronunciation check loads the ~1.3 GB wav2vec2 model into memory
(already downloaded to the HuggingFace cache on first use) and is slow;
afterwards inference is a couple of seconds.

For frontend development with hot reload:

```bash
cd frontend && npm run dev   # proxies /api to localhost:8900
```

## Docker

```bash
docker compose up --build
# open http://localhost:8900
```

The image is multi-stage: Node builds the frontend, then a python:3.13-slim
runtime installs espeak-ng + ffmpeg, CPU-only PyTorch, bakes in the wav2vec2
model, and serves both the API and the built frontend on port 8000
(mapped to 8900 by compose). The model is also kept in a named volume
(`hf-cache`), so it survives image rebuilds.

```bash
PORT=9000 docker compose up -d          # different host port
SPIIK_ENGINE=azure docker compose up    # with AZURE_SPEECH_KEY/REGION set
```

## Scaling

The backend is a single FastAPI app; model-heavy inference (wav2vec2
assessment, Marian translation) is CPU-bound and lazy-loaded.

- **Workers** — `WEB_CONCURRENCY=N` runs N uvicorn worker processes (compose
  passes it through; the Dockerfile defaults to 1). Requests are already
  kept off the event loop (assessment runs in a threadpool), so workers
  help most when inference saturates one CPU core. Each worker loads its
  own copy of every model it uses: ~1.5–2 GB RAM once the ASR model is
  warm, plus up to ~1 GB per loaded Marian model (LRU of 2). 2–4 workers
  is the sensible range on a typical 4-core host.
- **SQLite** — the database runs in WAL mode with a 5 s busy timeout, so
  concurrent workers and readers don't block each other. For multi-host
  scaling, move the database first; everything else is stateless.
- **Vertical first** — a bigger instance with more `WEB_CONCURRENCY` is
  the intended scaling path; there is no shared state between requests.

## Observability

The backend exposes Prometheus metrics at `/metrics` (request counts and
latency by route, in-flight requests, assessment/recognition latency,
model loads, translation provider outcomes, TTS provider, process
CPU/RSS). `/api/health` reports liveness plus the running version and
scoring engine — the Docker healthcheck uses it.

Grafana + Prometheus ship as an opt-in compose profile, pre-provisioned
with a spiik dashboard (request rate/latency, error rate, assessment
latency, model loads, translation outcomes, process resources):

```bash
docker compose --profile observability up -d
# Prometheus: http://localhost:9090 · Grafana: http://localhost:3000 (admin/admin — change it)
```

Config lives in `observability/` (scrape config, Grafana provisioning and
the dashboard JSON); Prometheus/Grafana data go into named volumes.

## Releases & versioning

The git tag is the version. Pushing `v0.4.0` triggers the release
workflow, which builds the full image (models baked in), publishes it to
GHCR as `v0.4.0` / `0.4` / `0` / `latest`, and creates a GitHub release
with generated notes. The tag is baked into the image as `SPIIK_VERSION`
— `/api/health` reports it and logged-in users see it on the Profile
screen (`dev` builds hide it).

```bash
git tag v0.4.0 && git push origin v0.4.0   # cut a release
```

Self-hosters can pin a release without building:

```bash
SPIIK_IMAGE=ghcr.io/batistaleandro/spiik:v0.4.0 docker compose up -d
```

CI (`.github/workflows/ci.yml`) runs the backend tests, frontend lint +
build and a Docker build (models skipped via `BAKE_MODELS=false`) on
every push and PR.

## Accounts & spaced repetition

The trainer (analyze / listen / record) works without an account. Creating
one (free, self-hosted — no email verification) unlocks:

- **Saving words** — hit “Save to practice” on any analyzed word; the server
  re-runs the analysis and stores word + translation + IPA as a card.
- **Practice screen** — a daily queue of due cards (plus up to 20 new cards
  per day). Recall the word, reveal the answer (meaning, spiik spelling,
  native audio), optionally record & score your attempt, then rate yourself
  **Again / Hard / Good / Easy** — a simplified SM-2 schedule picks the next
  interval (10 min → 1 d → 6 d → interval × ease; ease adapts 1.3–2.8).
- **Progress tracking** — the Words screen shows saved words with a
  confidence bar per word (new → learning → familiar → confident → mastered
  at 21+ day intervals), a 30-day review history, a 7-day due forecast and
  a practice streak.

Storage & config:

- SQLite database at `SPIIK_DB` (default `backend/data/spiik.db`;
  `/data/spiik.db` in Docker, mounted as the `spiik-data` volume).
- JWT sessions are signed with `SPIIK_SECRET`; if unset, a random secret is
  generated once and kept next to the database. Set a long random
  `SPIIK_SECRET` in `docker-compose` for real deployments.

## Tests

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```

## How it works

- **Per-language data** (`backend/data/languages/*.yaml`): every language has
  an espeak voice, a phoneme inventory, how each IPA sound is written natively
  (`orthography`), preferred `substitutions` for foreign sounds,
  `minor_foreign` sounds (foreign-but-equivalent, e.g. schwa ≈ /ɐ/ in
  Portuguese), `foreign_display` for multi-letter renderings of foreign
  sounds (en eɪ → ru "эй"), `recognized_aliases` to normalize wav2vec2/espeak
  token drift, and `drill_words` for training examples. Ships with:
  English (US), Portuguese (BR), Spanish, German, French, Italian, Russian.
- **Approximation** (`app/core/approx.py`): target IPA tokens are checked
  against the learner's inventory; native sounds render in their native
  spelling, foreign sounds are substituted with the closest native sound
  (curated candidates first, panphon distance fallback) and flagged. Tokens
  are grouped into display chunks with onset maximization → `cri-ei-chan`.
- **Scoring** (`app/core/align.py`): Needleman-Wunsch alignment of expected
  vs. recognized phonemes with panphon feature distances, so /θ/→/s/ is a
  near miss while /θ/→/m/ is a far miss. Verdicts + hints reference the
  learner's orthography.
- **Drills** (`app/core/drills.py`): training cards auto-generated from IPA
  feature vectors, with example words from the target language's `drill_words`.

### Adding a language

Probe the tokens espeak actually emits, then write a YAML file:

```bash
cd backend && .venv/bin/python -m scripts.probe_espeak fr-fr
```

Copy an existing YAML as a template, fill in `inventory`/`orthography` from
the probe output (curate the interesting ones), add `tts_voice` (edge-tts
voice name) and you're done — any pair with any other language works. See
`data/languages/ru.yaml` for the conventions to watch for: espeak marks
stress differently per language (`"`/`^` in Russian), emits palatalization
as a standalone `ʲ` token, and the wav2vec2 model may emit variant tokens
(handled via `recognized_aliases`).

### Translation

Phrases and words are translated by a best-effort provider chain — first
success wins, every failure degrades to no translation:

1. **Offline Marian models** (Helsinki-NLP Opus-MT, one small model per
   pair, pivoting through English for the rest) — no network, no rate
   limits, under a second per phrase on CPU. Apache-2.0 / CC-BY-4.0.
2. **Google's keyless gtx endpoint** — Google quality; unofficial, may
   rate-limit (especially from datacenter IPs).
3. **MyMemory** — translation-memory matches with a small anonymous quota.

(Microsoft's keyless Edge endpoint was evaluated and dropped — its auth
URL is gone; the short-LLM idea lost to dedicated MT models on
faithfulness, speed and footprint — see the repo history.)

`SPIIK_TRANSLATE=auto|online|off` controls how much of the chain runs
(`auto` = local models first when their weights are cached, the default).
The Docker image bakes the models; for local development pre-download
them once with `python -m scripts.download_translation_models`.
`SPIIK_MM_EMAIL` lifts MyMemory's anonymous quota tenfold.

### Hybrid scoring engine

`SPIIK_ENGINE=local` (default) uses wav2vec2. `SPIIK_ENGINE=azure` routes to
`app/engines/azure.py` — a stub for Azure's Pronunciation Assessment, which
returns per-phoneme accuracy out of the box; implement `transcribe` there
(reduce its output to IPA strings) and set `AZURE_SPEECH_KEY`/`AZURE_SPEECH_REGION`.

## Known limitations

- espeak's IPA is an approximation of real phonetics for some languages; since
  the same G2P generates both the reference and the model's training domain,
  comparisons stay internally consistent.
- Approximation quality varies by language pair (generic engine); curated
  `substitutions` entries improve the pairs you care about.
- Assessments of *attempted* foreign pronunciations are inherently noisy;
  feature-weighted alignment absorbs most of it.
