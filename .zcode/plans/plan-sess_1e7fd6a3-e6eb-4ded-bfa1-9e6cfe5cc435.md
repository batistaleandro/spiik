# Spiik — pronunciation trainer via IPA approximation

Web app that takes any target-language word, shows it as an orthographic approximation in the user's native language (IPA-driven), listens to the user's attempt, and gives per-phoneme feedback plus drills for sounds the native language doesn't have.

**Stack:** Vite + React + TypeScript frontend · Python FastAPI backend · espeak-ng (phonemizer) for text→IPA · `facebook/wav2vec2-lv-60-espeak-cv-ft` (CTC, outputs IPA phonemes directly) for user-audio→phonemes · `panphon` for phoneme feature distances · edge-tts (free neural voices) for TTS. Azure Pronunciation Assessment can later plug into the same scoring interface (hybrid choice).

## Core design: per-language data, not per-pair

Each language ships one YAML file (`backend/data/languages/pt.yaml`):

```yaml
code: pt
inventory: [p, b, t, d, k, g, f, v, s, z, ʃ, ʒ, m, n, ɲ, ʎ, ɾ, ʁ, i, e, ɛ, a, ɔ, o, u, ...]
diphthongs: [aj, ej, oj, ew, iw]
orthography:            # how each IPA sound is written natively
  ʃ: ch
  ʒ: j
  ej: ei
  ...
substitutions:          # foreign sounds → closest native sound(s)
  θ: [t, s]
  ð: [d]
  æ: [ɛ]
  ...
```

Approximation algorithm: G2P the target word → IPA token sequence (diphthongs/affricates as single units) → each unit is either **native** (render in green using `orthography`) or **foreign** (pick the substitution with lowest panphon feature distance, render flagged). Optional per-pair override files (`data/overrides/en-pt.yaml`) refine chunking for quality-critical pairs. This makes any target→native combination work, matching your "any pair" choice.

## Backend (`backend/app/`)

- `core/g2p.py` — phonemizer/espeak-ng → IPA with stress, normalized across accents (en-US/en-GB selectable)
- `core/approx.py` — tokenization + inventory check + substitution + join; returns chunks `{ipa, text, status: native|foreign, substitute_of}`
- `core/align.py` — feature-weighted Levenshtein/DTW alignment of expected vs recognized phoneme sequence (panphon distances, so /θ/ vs /s/ counts as near-miss, /θ/ vs /m/ as far miss)
- `engines/local.py` — wav2vec2 phoneme recognizer (16 kHz mono WAV in → IPA sequence out); `engines/azure.py` — stub behind the same `ScoringEngine` protocol
- `tts.py` — edge-tts (word audio + drill examples), also behind an interface
- `drills.py` — auto-generated training cards for foreign phonemes from IPA features: articulation text ("voiceless dental fricative — tongue lightly between the teeth, push air out"), TTS-rendered minimal pairs
- API: `POST /api/g2p` (word+pair → chunks + missing phonemes), `POST /api/assess` (audio + expected IPA → per-phoneme verdicts), `POST /api/tts`, `GET /api/languages`
- ffmpeg for decoding browser audio (webm/opus → wav)

## Frontend (`frontend/`)

- Language pair picker (native first, target second), word input
- **Approximation display**: word rendered as native-orthography chunks, green = native sound, red/highlighted = foreign sound with tooltip "this sound doesn't exist in Portuguese — see drill"
- Playback button (TTS), record button (MediaRecorder → WAV → assess)
- **Per-phoneme feedback bar**: each phoneme marked correct / close / wrong / missing, with error hints in native terms ("you said 'a' — correct /eɪ/ sounds like 'ei' in 'feira'")
- **Drill card** for foreign phonemes: articulation instructions, listen-to-model / record-and-rescore loop

## Implementation phases

1. **Phonetics core + data** — `g2p.py`, language file format, `approx.py`, en + pt data, pytest (e.g., "creation"→"cri-ei-chion" chunks; "think" flags /θ/ as foreign). Verified via CLI.
2. **API + TTS** — FastAPI endpoints, edge-tts, curl-verifiable.
3. **Frontend practice loop** — pair picker, word input, approximation display, TTS playback.
4. **Assessment** — browser recording, wav2vec2 recognition, alignment, per-phoneme feedback UI.
5. **Drills** — auto-generated phoneme cards + minimal pairs.
6. **Breadth** — seed `es`, `de`, `fr`, `it` language files; Azure adapter stub.

Verification: pytest for the engine, curl for the API, then a browser pass (web GUI tester) on the full loop before finishing.

## Known limitations (accepted for v1)

- wav2vec2 model download ~1.5 GB and slow first inference; espeak's IPA is approximate for some languages; approximation quality will vary by pair (generic engine) — curated pairs improve via override files.
- STT recognition of *attempted* foreign pronunciations is inherently noisy; feature-weighted alignment tolerates this.