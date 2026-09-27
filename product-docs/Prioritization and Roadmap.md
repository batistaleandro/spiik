# Spiik Product Priorities & Impact/Effort Evaluation

This document details the multi-perspective evaluation of features from the [[Kanban]] board across **Engineering**, **Visionary**, and **Product** profiles, updated with the strategic directive prioritizing **community development, crowdsourced data, viral network effects, and infrastructure scalability**.

---

## 1. Executive Summary: Prioritization Matrix

```
       HIGH IMPACT
            ▲
            │  [[Community Features]] (Crowdsourcing/Cards)  [[Mobile Version]] (PWA)
            │  [[Affiliate and Growth]] (Viral Duels)        [[Basic Devops]] (CI/CD)
            │  Public Profiles & Streaks                     [[Add additional Language Support]]
            │                                                [[Horizontal Scalability]] (Multi-Node)
            │  ─────────────────────────────────────────────┼──────────────────────────────
            │  [[Admin Panel]]                              [[Payment System]]
            │  [[Gamification Features]] (Badges)           
            │  ─────────────────────────────────────────────┼──────────────────────────────
            │                                               [[Find a Tutor]]
            │                                               P2P Video Chat (Omegle-style)
            ▼
       LOW IMPACT
       ◄──────────────────────────────────────────────────────────────────────────►
       LOW EFFORT                                                     HIGH EFFORT
```

| Quadrant | Items | Strategic Rationale |
| :--- | :--- | :--- |
| **Viral Growth & Quick Wins** *(High Impact, Low/Med Effort)* | [[Community Features]] (Share Cards, Crowdsourcing), [[Affiliate and Growth]] (Duels, Referrals) | **Top Immediate Priority**. Creates organic K-factor acquisition and crowdsources phonetic approximations to unblock language scaling. |
| **Major Foundations** *(High Impact, Med/High Effort)* | [[Basic Devops]] (CI/CD), [[Mobile Version]] (PWA), [[Add additional Language Support]], [[Horizontal Scalability]] (Postgres, Workers, Cloud) | **Core Platform Rigor & Scale**. Mobile unlocks daily practice; DevOps enables rapid shipping; crowdsourced data feeds back into language models; Horizontal Scalability decouples DB and inference for high concurrency and cloud readiness. |
| **Operational Fill-Ins** *(Med Impact, Low/Med Effort)* | [[Admin Panel]], [[Gamification Features]] (Phonetic Badges) | **Sprint 2**. Moderation and achievement loops. |
| **Deferred / Avoid** *(Low Impact, High Effort)* | [[Payment System]] (Deferred until cloud launch), [[Find a Tutor]] (Avoid marketplace trap), P2P Video Chat | **Pause/Shelve**. High operational drag. |

---

## 2. Strategic Flywheel: Community Data & Network Effects

The fundamental insight from manual language curation (such as Thai) is that **a single developer cannot hand-craft cross-linguistic phonetic approximations for 50+ languages alone**. The community must power the engine:

```
        1. Learner practices a word and scores their pronunciation
                                │
                                ▼
        2. Learner shares a viral phonetic card or "Pronunciation Duel"
                                │
                                ▼
        3. Native speakers / friends click the link to attempt the word
                                │
                                ▼
        4. Community suggests / upvotes better phonetic spellings
                                │
                                ▼
        5. Language YAML files improve automatically via crowd data
```

---

## 3. Multi-Perspective Evaluation (Updated)

### 1. [[Community Features]] & Crowdsourced Data
- **Priority**: High (P1 — Immediate Up Next)
- **Engineer**: Med effort. Build suggestion/voting schema in SQLite; generate dynamic social sharing cards (OpenGraph/Canvas) with deep links back to the practiced word.
- **Visionary**: Transformational. Establishes a defensible, proprietary dataset of cross-linguistic phonetic approximations validated by thousands of native speakers.
- **Product**: Core Viral Engine. Turns single-player pronunciation practice into an organic, multiplayer acquisition loop.

### 2. [[Affiliate and Growth]] (Decoupled from Payments)
- **Priority**: High (P1 — Immediate Up Next)
- **Engineer**: Low–Med effort. Referral code attribution, "Pronunciation Duel" challenge links (`?c=challenge_id`), and beta language access gating.
- **Visionary**: High impact. Word-of-mouth loops driven by competitive pronunciation challenges and social bragging rights.
- **Product**: Quick Win. Drives organic top-of-funnel without requiring complex payment gateways.

### 3. [[Basic Devops]]
- **Priority**: High (P1 — Immediate Up Next)
- **Engineer**: Med effort. GitHub Actions CI for running test suite, linting, and automated Docker image publishing.
- **Visionary**: High impact. Operational foundation supporting community self-hosters and contributors.
- **Product**: Major Enabler. Prevents regressions in the core audio scoring pipeline.

### 4. [[Mobile Version]]
- **Priority**: High (P1 — Immediate Up Next)
- **Engineer**: Med effort (PWA/Responsive Web). Mobile viewport optimization and robust iOS/Android `MediaRecorder` audio capture.
- **Visionary**: High impact. Viral share links received on mobile chat apps (WhatsApp, Telegram) must open seamlessly on mobile.
- **Product**: Major Project. Spaced repetition and viral link opening are mobile-first behaviors.

### 5. [[Add additional Language Support]] (Crowdsourced)
- **Priority**: Medium (P2 — R&D / Crowdsourced Pipeline)
- **Engineer**: High effort if done manually; significantly eased once the community suggestion/voting pipeline is live.
- **Visionary**: Deep long-term moat. Community-contributed language packs allow scaling into Thai, Vietnamese, Georgian, and beyond.
- **Product**: Shift strategy: Launch Thai with a "Community Beta / Help improve approximations" banner to let native speakers refine it.

### 6. [[Horizontal Scalability]] (Decoupled DB, Async Inference & Multi-Node Support)
- **Priority**: Medium-High (P2 — Infrastructure Enabler for Hosted Cloud & High Concurrency)
- **Engineer**: Med–High effort. Abstract database access to support PostgreSQL alongside SQLite via SQLAlchemy/Alembic; extract wav2vec2/Marian inference into an asynchronous worker queue (Redis + Celery) or internal gRPC inference service; enable stateless API tier behind a load balancer.
- **Visionary**: High impact. Essential for scaling beyond single-host constraints to power a resilient multi-tenant cloud offering (Spiik Cloud) and survive viral traffic surges without breaking self-hosting defaults.
- **Product**: Major Enabler. Guarantees fast audio scoring latency under concurrent load and unblocks commercial hosted tiers.

### 7. [[Admin Panel]]
- **Priority**: Medium (P2)
- **Engineer**: Low–Med effort. Role-based auth, user management, and moderation of community-submitted phonetic suggestions.
- **Visionary & Product**: Essential operational governance.

### 8. [[Gamification Features]]
- **Priority**: Medium (P2)
- **Engineer & Product**: Low effort. Phonetic badges and shared milestone celebrations linked to viral cards.

### 9. [[Payment System]]
- **Priority**: Low / Deferred (P3)
- **Recommendation**: Defer until community size and organic retention justify a hosted commercial offering.

### 10. [[Find a Tutor]]
- **Priority**: Paused (P4)
- **Recommendation**: Avoid the two-sided marketplace trap. Focus resources on automated AI phonetics and crowdsourced community learning.

---

## 4. Revised Sprint Roadmap

- **Sprint 1 (Viral Growth & Community Data Engine)**:
  1. **Viral Share Cards & Challenge Links**: 1-click shareable image/link for pronunciation scores and approximations ("Can you beat my score?").
  2. **Crowdsourced Phonetic Suggestions**: "Suggest a better spelling" button on words and drill cards with upvoting.
  3. **Basic DevOps Hardening**: Automated CI/CD (GitHub Actions) for backend tests and container builds.
  4. **Mobile Audio Audit**: Ensure challenge links and recording work smoothly on iOS Safari and mobile Chrome.

- **Sprint 2 (Crowdsourced Language Scaling & Community Profiles)**:
  1. **Community Beta for Thai**: Release Thai with crowdsourced correction tools to let the community polish approximation rules.
  2. **Public Profiles & Streak Bragging**: Shareable learner profiles `/u/:username` with social preview cards.
  3. **Shared Word Decks**: Enable learners and tutors to create and publish curated word lists with deep links.
  4. **Horizontal Scalability Architecture Spike**: Design PostgreSQL abstraction alongside SQLite and plan inference worker decoupling for multi-container deployments.

- **Sprint 3 (Governance, Scaling & Gamification)**:
  1. **Admin Moderation Panel**: Approve/merge crowdsourced phonetic contributions into language YAML files.
  2. **Decoupled Worker Queue & Postgres Migration**: Ship production multi-node Compose/Helm blueprint with separate inference workers and external DB support.
  3. **Phonetic Achievement Badges**: Milestone rewards tied to social share cards.
