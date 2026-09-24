# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Language learners practicing pronunciation in any language pair — every shipped pair is equally first-class (confirmed). The pt-br → en-us defaults in the UI are conveniences only, not a product-story privilege (confirmed). A learner speaks one of the shipped native languages and practices one of the shipped target languages (inferred from the per-language data shipped: en-us, pt-br, es, de, fr-fr, it, ru). The product is self-hosted (Docker or local uvicorn); the operator is typically also a learner or provides the instance to a small group (inferred from repo deployment docs).

## Product Purpose

spiik helps learners pronounce foreign words by writing them the way they sound in the learner's own language: it compares the IPA of the target word against the learner's phoneme inventory, rendering native sounds in native spelling and foreign sounds as closest-native approximations (e.g. "creation" → "kri-ei-chan" for a Brazilian Portuguese speaker). Learners listen (neural TTS), record themselves, and get phoneme-level scoring of what they actually said; sounds their language lacks become generated drill cards. Saved words enter a spaced-repetition practice loop so pronunciation work sticks over time.

Success means real learning outcomes (confirmed): words retained through spaced practice, practice streaks, and honest pronunciation scoring — not one-off novelty checks.

## Positioning

The mechanism a neighboring product could not truthfully copy: pronunciation approximation and scoring driven by per-language phoneme data files (IPA inventory + native orthography + substitution preferences) rather than per-pair tables — so any pair of shipped languages works out of the box — combined with wav2vec2 phoneme recognition that scores real attempts against the expected IPA, all on free, keyless services a self-hoster can run (espeak-ng, edge-tts, panphon, free translation providers).

## Operating Context

- Self-hosted, single process: FastAPI serves both API and built frontend (locally on :8900; Docker maps `${PORT:-8900}`); SQLite at `SPIIK_DB`.
- Free/keyless providers with graceful degradation: Google/MyMemory translation (best-effort), edge-tts voices with an espeak-ng offline fallback.
- The first pronunciation check loads a ~1.3 GB wav2vec2 model into memory (baked into the Docker image).
- Recording requires browser microphone permission (MediaRecorder/webm); practice is fully usable without a mic (listen + self-rated confidence).
- The engine compares espeak-ng IPA on both sides; its IPA is an approximation of real phonetics, but internally consistent because the same G2P drives the reference and the model's recognition domain.

## Capabilities and Constraints

Confirmed capabilities:

- Analyze any word/phrase: IPA + native-orthography approximation + missing-sound flags (major = needs training, minor ≈ equivalent sound).
- Translate the practiced word into the learner's language (best-effort), or translate learner input into the target language before practicing.
- Score recordings 0–100 with per-phoneme verdicts (correct/close/wrong/missing) and hints written in the learner's orthography.
- Auto-generated drill cards for sounds the learner's language lacks (IPA features + coaching + example words + audio).
- Accounts (username/email/password, bcrypt + JWT) with saved words, SM-2 spaced repetition (Again/Hard/Good/Easy; 10 min → 1 d → 6 d → interval × ease; ease 1.3–2.8; ≤ 20 new cards/day), progress dashboard (streak, 30-day review history, 7-day due forecast, per-word confidence tiers), and profile management.
- The trainer (analyze/listen/record) works without an account; saving, practice, and progress require one.

Constraints:

- Shipped languages: English (US), Portuguese (BR), Spanish, German, French, Italian, Russian. Adding a language means writing a YAML data file (documented workflow in the README).
- espeak's IPA quality varies by pair; curated `substitutions` entries improve the pairs that matter.
- No email verification, password-reset emails, or account deletion (explicitly undecided product facts — open, not promised).
- UI language is English; no i18n framework (open decision, not a commitment).

## Brand Commitments

- The name "spiik." is binding (confirmed).
- Tone of voice, tagline, and copy style are explicitly open to refinement (confirmed). The current lowercase wordmark with an accent-colored dot is existing treatment, not a constraint beyond the name.

## Evidence on Hand

- README.md documents the mechanism, stack, deployment, and known limitations.
- Per-language data files at `backend/data/languages/*.yaml` (real phoneme inventories, orthographies, substitution preferences, drill words).
- Original architecture/plan document: `.zcode/plans/plan-sess_1e7fd6a3-e6eb-4ded-bfa1-9e6cfe5cc435.md`.
- Working pytest suite (46 passing) and a runnable Docker deployment.
- No marketing assets, testimonials, user research, or press exist — future design work must not fabricate them.

## Product Principles

1. Every language pair is first-class — no pair may be privileged in the product story; UI defaults are conveniences only.
2. Optimize for durable learning outcomes: spaced retention, streaks, and honest scoring outrank novelty and one-off checks.
3. Phonetics-first honesty: the IPA comparison engine is the source of truth; features and copy must stay consistent with what it can actually claim.
4. Degrade gracefully: free providers may fail — the core analyze/listen/practice loop must survive without translation or neural TTS.
5. Self-hosting is a feature: single process, no paid APIs or keys, learner data stays with the operator.
