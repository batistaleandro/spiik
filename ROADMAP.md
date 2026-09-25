# spiik Roadmap

> Learn pronunciation by approximating a foreign language into your own.

**How to read this file** (for humans and AI agents):

- Features are written as **user stories** — they are the product's source of
  truth for intent. Positioning, principles and constraints live in
  [PRODUCT.md](PRODUCT.md).
- `[x]` = shipped · `[ ]` = planned, not started. A version marked
  *(complete)* is fully shipped; the first unmarked version is the current
  working target.
- v0.1–v0.3 are retrospective labels for work shipped in September 2026 —
  the project had no version numbers before this roadmap. Automatic
  versioning arrives with v0.4.
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

## v0.5 — Operator tools & account care

> Priority: Medium. More people on one instance means the operator needs
> tools — and users need a way back in.

- [ ] **As an operator, I can manage the users on my instance** (admin panel)
  - [ ] View and manage user accounts (list, disable, remove)
- [ ] **As a user who forgot my password, I can get back into my account**
  - [ ] Self-hosted reset flow (an operator action — no email dependency)
- [ ] **As a user, I can delete my account and everything in it**
  - [ ] Account deletion removes the profile, saved words and review history

---

## v0.6 — Subscriptions & sharing

> Priority: Medium. Subscriptions unlock advanced features; sharing an
> affiliate link earns free subscription time. Affiliate work is blocked by
> the payment system.

- [ ] **As a user, I can subscribe to unlock advanced features** (payment
  system)
  - [ ] Subscription management
  - [ ] Feature blocking — capabilities gated by subscription tier
  - [ ] Crypto payment
- [ ] **As a user, I can share an affiliate link and unlock free subscription
  time** (affiliate and growth)
  - [ ] Affiliate link management — rewards by action (share a link / share a
    post → 1 week / 1 month / 1 year)
  - [ ] Depends on the payment system; partially on the admin panel

---

## v0.7 — Learn together

> Community, tutors, and a little motivation. Gamification is Low priority on
> the board — its smallest slice ships last.

- [ ] **As a learner, I can have a public profile showing my streak**
  (community)
- [ ] **As a learner, I can practice with another learner over video**
  (community — P2P video chat)
- [ ] **As a learner, I can find a tutor**
  - [ ] Needs a tutor-facing admin panel
- [ ] **As a learner, I can earn badges for milestones** (gamification)

---

## v0.8 — More of the world

> Niche languages with non-latin alphabets are where "reading in your
> language" is strongest (PRODUCT.md).

- [ ] **As a learner, I can practice Thai, Vietnamese and Georgian**
  - [ ] Thai (Partially implemented - Needs polish with the approximate pronunciation and phonetic alphabet generation)
  - [ ] Vietnamese
  - [ ] Georgian

Each language is a YAML data file following the documented workflow; the
non-latin scripts are where the spiik spelling shines.

---

## v0.9 — In your pocket

> Mobile is the platform frontier (Kanban + PRODUCT.md), together with the
> reach decisions still open: theme and UI language.

- [ ] **As a learner, I can install spiik on my phone and practice from
  there**
  - [ ] Mobile version — an installable PWA first
- [ ] **As a learner, I can switch to a light theme** (dark-only today)
- [ ] **As a learner, I can use spiik in my own language** (UI translations —
  commits the open i18n decision)
- [ ] **As a learner, the browser tab says spiik, not "frontend"** (page
  title)

---

## Exploring

> Ideas being explored — surfaced during development, not committed to a
> release yet.

- **Translation alternatives picker** — when the first translation isn't
  quite right, pick a better one before saving (explored during the
  offline-translation work)
- **Self-hosted LibreTranslate** — an additional translation provider for
  fully offline instances
- **Per-pair approximation quality overrides** — the mechanism is scaffolded
  (`data/overrides/`), no pairs curated yet

---

## Non-Goals (Explicit)

- **Required paid APIs or keys in the core loop** — the free, keyless
  analyze / listen / practice loop must degrade gracefully; cloud assessment
  (Azure) stays an opt-in add-on, never a requirement.
- **Privileged language pairs** — every shipped pair is first-class; the
  pt-BR → en-US defaults are conveniences only.
- **Copy the engine can't back** — phonetics-first honesty: espeak's IPA is
  an approximation, and the product says so.
- **Novelty over retention** — durable learning outcomes (spaced practice,
  streaks, honest scoring) outrank one-off novelty checks.
