# spiik.

Learn pronunciation by approximating a foreign language into your own. Spiik
compares the **International Phonetic Alphabet (IPA)** of both languages to:

1. **Write foreign words the way they sound to you** — `creation` → `cri-ei-chan`
   for a Brazilian Portuguese speaker; `think` → `sinc`.
2. **Show what the word means** — a translation into the learner's language
   (free providers: Google with MyMemory fallback, best-effort).
3. **Listen to your attempt and score every phoneme** — a wav2vec2 model
   recognizes the IPA sounds you actually produced, and a feature-weighted
   alignment against the expected IPA marks each sound correct / close / wrong / missing.
4. **Train the sounds your language doesn't have** — /θ/ doesn't exist in
   Portuguese? Spiik generates a drill card from the phoneme's IPA features
   (place, manner, voicing) with coaching text, minimal-pair examples and audio.

Any language pair works out of the box: the engine is driven by per-language
data files (phoneme inventory, native orthography, substitution preferences),
not per-pair tables.

## Stack

| Layer      | Technology                                                          |
|------------|---------------------------------------------------------------------|
| Backend    | Python 3.13, FastAPI                                                |
| Text→IPA   | espeak-ng via `phonemizer`                                          |
| Audio→IPA  | `facebook/wav2vec2-lv-60-espeak-cv-ft` (CTC, outputs IPA directly)  |
| Distances  | `panphon` feature-weighted phoneme distances                        |
| TTS        | edge-tts (free neural voices) with espeak-ng offline fallback       |
| Translate  | translate.google.com/m + MyMemory (both free, best-effort)          |
| Frontend   | Vite + React + TypeScript                                           |

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
