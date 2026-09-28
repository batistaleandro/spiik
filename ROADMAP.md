# spiik Roadmap

> Learn pronunciation by approximating a foreign language into your own.

**How to read this file** (for humans and AI agents):

- Features are written as **user stories** — they are the product's source of
  truth for intent. Positioning, principles and constraints live in
  [PRODUCT.md](PRODUCT.md).
- `[x]` = shipped · `[ ]` = planned, not started. A version marked
  *(complete)* is fully shipped; the first unmarked version is the current
  working target.
- v0.1–v0.4 are retrospective labels for work shipped in September 2026.
- **Exploring** holds ideas being explored that are not committed to a
  release yet — don't fold them into a version without the owner asking.
- **Non-Goals** are explicit decisions the product will not make.

---

## v0.1 — Train the sound *(complete — September 2026)*

> Write foreign words the way they sound to you. spiik shows exactly which
> sounds you're missing — and trains them.

The core loop: analyze → listen → record → drill.

### Trainer

- [x] **As a learner, I can type any foreign word and see it spelled the way
  I'd say it in my own language** (`creation` → `kri-ei-chan` for a Brazilian
  Portuguese speaker)
  - [x] Approximation is driven by per-language data files (IPA inventory +
    native orthography + substitution preferences), not per-pair tables —
    any pair of shipped languages works out of the box
- [x] **As a learner, I can add a word by typing it in my own language** and
  get it translated into the language I'm learning first (native mode)
- [x] **As a learner, I can see what the word means** — a translation into my
  language, shown on the card (best-effort free providers)
- [x] **As a learner, I can hear how the word should sound** (neural TTS per
  language, with an offline espeak-ng fallback)
- [x] **As a learner, I can record myself and get scored phoneme by phoneme**
  — wav2vec2 recognizes the IPA I actually produced; a feature-weighted
  alignment marks each sound correct / close / wrong / missing, with hints
  written in my orthography
  - [x] An opt-in hybrid scoring engine is scaffolded — `SPIIK_ENGINE=azure`
    routes to a stub for Azure's Pronunciation Assessment
- [x] **As a learner, I can train the sounds my language doesn't have** —
  auto-generated drill cards from the phoneme's IPA features (place, manner,
  voicing), with coaching text, minimal-pair examples and audio; tapping an
  example re-practices that word
- [x] **As a learner, I can work with 7 languages** — English (US),
  Portuguese (BR), Spanish, German, French, Italian, Russian
  - [x] Runs as a single Docker container with the models baked in;
    self-hosted, no paid APIs or keys

### Fixes

- [x] **As a learner, the trainer controls stay aligned and readable on small
  screens** (aligned grid, no wrapping buttons or labels)
- [x] **As a learner, Brazilian Portuguese words map to the right sounds**
  (orthography fix)

---

## v0.2 — Remember it *(complete — September 2026)*

> A word you don't review is a word you lose. Accounts + spaced repetition
> make pronunciation work stick.

### Accounts

- [x] **As a learner, I can create a free account and log in with my username
  or email** (self-hosted; sessions survive restarts)
- [x] **As a learner, I can try the trainer without an account** — analyze /
  listen / record need no login; saving and practice unlock with one
- [x] **As a learner, I can update my profile and change my password**

### Practice

- [x] **As a learner, I can save any analyzed word to my practice deck**
  (word, translation and IPA stored as a card)
- [x] **As a learner, I can review with a two-sided flashcard** — recall the
  word's sound on side A (with a recording check), flip to side B for the
  meaning and how my attempt scored
- [x] **As a learner, I can rate myself Again / Hard / Good / Easy** and spiik
  schedules the next review (simplified SM-2: 10 min → 1 d → 6 d →
  interval × ease; up to 20 new cards a day; "again" cards re-queue at
  session end)
- [x] **As a learner, I can see my progress** — per-word confidence
  (new → learning → familiar → confident → mastered), a 30-day review
  history, a 7-day due forecast and a practice streak
- [x] **As a learner, I can move between Train, Practice, Words and Profile**
  in one app (multi-screen SPA with deep links)
- [x] **As a learner without a microphone, I can still practice** — recall +
  self-rating is a full loop on its own

---

## v0.3 — Say it offline, save what you saw *(complete — September 2026)*

> Translations shouldn't depend on someone else's rate limits — and a saved
> word should keep the meaning I actually saw.

- [x] **As a learner, my translations work offline** — local Marian models
  (one per language pair, pivoting through English) run before the free
  online providers; no network, no rate limits
  - [x] `SPIIK_TRANSLATE=auto|online|off` controls how much of the chain
    runs; the Docker image ships with the models baked in
- [x] **As a learner, spiik remembers my languages and my word across
  visits** (persisted selections, validated against the installed languages)
- [x] **As a learner, my saved word keeps the meaning I saw on the card** —
  native-mode saves no longer re-translate behind the scenes; re-saving a
  word updates its card without losing practice state
- [x] **As a learner, I get a clear error instead of a mystery when something
  is already taken** — duplicate words, usernames and emails collide cleanly
  (Unicode-safe case-folding)

---

## v0.4 — Foundations for growth *(complete — September 2026)*

> Priority: High. Everything queued after this — payments, community, more
> learners — needs an app that deploys easily, scales when it must, and
> releases itself.

- [x] **As a self-hoster, I can deploy spiik with confidence and scale its
  backend as more learners join**
  - [x] Make the backend services easy to deploy and scale as needed
    (CPU-bound assessment moved off the event loop, per-request engine
    reloads fixed, `WEB_CONCURRENCY` worker scaling, SQLite WAL,
    versioned GHCR images via `SPIIK_IMAGE`)
- [x] **As an operator, I can watch how my instance is doing without digging
  through logs**
  - [x] Observability — Prometheus metrics on `/metrics` + opt-in
    Grafana/Prometheus compose profile with a pre-provisioned spiik
    dashboard; `/api/health` for liveness + build identity
- [x] **As a contributor, I get versioned releases automatically**
  - [x] CI/CD for automatic versioning and release (git tags + Docker image
    tags) — making the versions in this roadmap real

---

## v0.5 — Operator Tools & Account Care *(complete — September 2026)*

> Priority: High. Provide essential governance, user management, and privacy controls
> so instance operators can manage accounts and users can recover or purge their data.

### Account Care & Administration

- [x] **As an operator, I can manage the users on my instance** (admin panel)
  - [x] View and manage user accounts (list, disable, remove)
- [x] **As a user who forgot my password, I can get back into my account**
  - [x] Email recovery flow — one-time reset link (valid 1 h, single use)
    sent over any plain SMTP account (`SPIIK_SMTP_*`); without SMTP config
    the link is logged, and the admin panel keeps an operator-assisted
    one-time password as fallback
- [x] **As a user, I can delete my account and everything in it**
  - [x] Account deletion removes the profile, saved words and review history

---

## v0.6 — Vertical Efficiency, Subscriptions & Affiliates

> Priority: High. Optimize per-node inference to minimize RAM/CPU footprints
> before scaling out, introduce self-sustaining monetization, and bootstrap viral distribution.

### Vertical Inference Optimization

- [ ] **As an operator, I can run 4–6 worker processes on a low-spec host without running out of RAM**
  - [ ] Export wav2vec2 to ONNX with INT8 CPU quantization, reducing model memory from ~1.3 GB to ~350 MB and cutting inference latency by 2x
  - [ ] Client-side Web Speech API offloading for word audio playback to bypass backend TTS compute and network transfer
  - [ ] Enforce memory-lean online translation pipelines (`SPIIK_TRANSLATE=online`) with rate-limit circuit breakers

### Subscriptions & Feature Gating

- [ ] **As a user, I can subscribe to unlock unlimited practice and premium features**
  - [ ] Stripe Checkout and Customer Portal integration for recurring monthly ($4.99) and annual ($39.99) billing - Pricing strategy still needs to be defined
  - [ ] Feature limiter: enforce daily velocity caps on free accounts (e.g., 15 drills/day) while granting unlimited access to Spiik Pro
  - [ ] Support crypto checkout options alongside standard payment rails

### Affiliate & Referral Engine

- [ ] **As a creator, tutor, or user, I can earn revenue or free Pro time by sharing spiik**
  - [ ] Unique referral code generation and cookie/JWT attribution tracking on user signup
  - [ ] Tutor & Influencer affiliate dashboard with performance tracking and recurring revenue-share payouts
  - [ ] In-app peer referral mechanism: give 1 week of Pro for every friend referred who completes their first practice streak

---

## v0.7 — Learn together

> Priority: Medium. Community, peer motivation, and tutor-led learning paths.

- [ ] **As a learner, I can have a public profile showing my streak** (community)
- [ ] **As a learner, I can practice with another learner over video** (community — P2P video chat)
- [ ] **As a learner, I can find a tutor**
  - [ ] Tutor-facing marketplace and scheduling profile
- [ ] **As a learner, I can earn badges for milestones** (gamification)

---

## v0.8 — More of the world

> Priority: Medium. Niche languages with non-latin alphabets are where "reading in your language" is strongest ([PRODUCT.md](PRODUCT.md)).

- [ ] **As a learner, I can practice Thai, Vietnamese and Georgian**
  - [ ] Thai (polishing phonetic generation and tone approximations)
  - [ ] Vietnamese
  - [ ] Georgian

Each language is a YAML data file following the documented workflow; the non-latin scripts are where the spiik spelling shines.

---

## v0.9 — In your pocket

> Priority: Medium-Low. Cross-platform mobile presence and internationalization.

- [ ] **As a learner, I can install spiik on my phone and practice from there** (React Native)
- [ ] **As a learner, I can use spiik in my own language** (UI internationalization)
- [ ] **As a learner, the browser tab displays contextual titles instead of generic placeholders**
- [ ] **As a learner, I experience a refreshed, modernized visual design across all screens** (UI/UX Design Revamp)
  - [ ] Low-priority, medium-effort design overhaul: unified typography, updated component styling, refined card spacing, and consistent design tokens across Trainer, Practice, Words, and Profile screens (prioritized as low impact / low priority relative to core phonetic learning features)

---

## v0.10 — Production Deployment, Scalability & Clustered Infrastructure

> Priority: Low / Deferred to End of Roadmap. Production deployment and multi-node clustering
> moved to the end of the roadmap, activating after application features and single-node efficiency are complete.

### Production Infrastructure & Deployment

- [ ] **As an operator, I can deploy spiik to OCI Always-Free ARM compute at $0/month hosting cost**
  - [ ] Multi-arch release pipeline building and publishing `linux/arm64` images alongside `linux/amd64` to GHCR
  - [ ] Production compose stack bundling automated TLS reverse proxy (Caddy / Cloudflare SSL) to enable the browser WebRTC microphone capture API over HTTPS
- [ ] **As an operator, my SQLite database is continuously backed up offsite without paid databases**
  - [ ] Integrated Litestream sidecar streaming WAL frames in real time to Cloudflare R2 object storage
  - [ ] Documented automated disaster recovery and point-in-time restore procedures (`scripts/restore_db.sh`)

### Horizontal Scalability & Distributed State

- [ ] **As an operator, I can scale spiik horizontally across multiple nodes and clusters** (Scale-Triggered at >25,000 MAU)
  - [ ] Pluggable database layer: support PostgreSQL via SQLAlchemy/Alembic migrations while preserving zero-config SQLite for single-node setups (`SPIIK_DATABASE_URL`)
  - [ ] Decoupled ML inference tier: asynchronous scoring via Celery/Redis workers to keep frontend API gateways fully stateless
  - [ ] Production Helm charts and multi-region deployment blueprints

---

## Exploring

> Ideas being explored — surfaced during development, not committed to a release yet.

- **Translation alternatives picker** — choose alternative phrase meanings before saving (explored during offline translation work)
- **Self-hosted LibreTranslate** — fallback option for fully air-gapped environments
- **Per-pair approximation quality overrides** — curated phoneme substitution tweaks (scaffolded at `data/overrides/`)

---

## Non-Goals (Explicit)

- **Required paid APIs or keys in the core loop** — free assessment must always remain functional without third-party API dependencies (Azure stays an opt-in add-on, never a requirement).
- **Premature distributed infrastructure** — no mandatory multi-node clustering or managed databases prior to maximizing single-node efficiency.
- **Privileged language pairs** — all language pairs remain first-class citizens; the pt-BR → en-US defaults are conveniences only.
- **Copy the engine can't back** — phonetics-first honesty: espeak's IPA is an approximation, and the product says so.
- **Novelty over retention** — spaced repetition and phonetic accuracy take priority over cosmetic features (durable learning outcomes outrank one-off novelty checks).
