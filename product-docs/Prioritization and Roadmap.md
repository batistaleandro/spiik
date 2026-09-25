# Spiik Product Priorities & Impact/Effort Evaluation

This document details the multi-perspective evaluation of features from the [[Kanban]] board across **Engineering**, **Visionary**, and **Product** profiles.

---

## 1. Executive Summary: Prioritization Matrix

```
       HIGH IMPACT
            ▲
            │  [[Add additional Language Support]]   [[Mobile Version]] (PWA)
            │  (Thai, Vietnamese, Georgian)         [[Basic Devops]] (CI/CD)
            │  ─────────────────────────────────────┼──────────────────────────────
            │  [[Community Features]] (Profiles)    [[Payment System]]
            │  [[Admin Panel]]                      
            │  [[Gamification Features]] (Badges)   
            │  ─────────────────────────────────────┼──────────────────────────────
            │                                       [[Affiliate and Growth]]
            │                                       [[Find a Tutor]]
            │                                       P2P Video Chat (Omegle-style)
            ▼
       LOW IMPACT
       ◄──────────────────────────────────────────────────────────────────────────►
       LOW EFFORT                                                     HIGH EFFORT
```

| Quadrant | Items | Recommendation |
| :--- | :--- | :--- |
| **Quick Wins** *(High Impact, Low/Med Effort)* | [[Add additional Language Support]], [[Community Features]] (Public Profiles) | **Execute immediately**. Validates core moat and expands market. |
| **Major Strategic Projects** *(High Impact, Med/High Effort)* | [[Mobile Version]] (PWA focus), [[Basic Devops]] (CI/CD) | **Core technical investments**. Enables daily habit and stability. |
| **Operational Fill-Ins** *(Med Impact, Low/Med Effort)* | [[Admin Panel]], [[Gamification Features]] (Phonetic Badges) | **Sprint 2**. Unblocks management and boosts day-30 retention. |
| **Deferred / Avoid** *(Low Impact, High Effort)* | [[Payment System]], [[Affiliate and Growth]], [[Find a Tutor]], P2P Video Chat | **Pause/Shelve**. High operational drag; premature before PMF. |

---

## 2. Multi-Perspective Evaluation

### 1. [[Add additional Language Support]]
- **Priority**: High (P1)
- **Engineer**: Low–Med effort. Core engine is data-driven via `backend/data/languages/*.yaml`. Need espeak probe, YAML curation, and edge-tts voice config.
- **Visionary**: Transformational. Core mission is phonetic approximation for non-Latin scripts (Thai, Vietnamese, Georgian). Directly widens the unique moat.
- **Product**: Quick Win. High organic acquisition in underserved language communities.

### 2. [[Basic Devops]]
- **Priority**: High (P1)
- **Engineer**: Med effort. Multi-stage Docker is ready. Need automated CI (GitHub Actions), test runner, and semantic release pipeline. Keep observability lightweight.
- **Visionary**: High impact. Upholds brand principle: self-hosting is a first-class feature that must be rock solid.
- **Product**: Major Enabler. Eliminates deploy friction and prevents regressions in the PyTorch/audio pipeline.

### 3. [[Mobile Version]]
- **Priority**: High (P1)
- **Engineer**: Med effort (PWA/Responsive Web) vs Very High (Native). Focus on mobile viewport and iOS Safari `MediaRecorder` audio recording compatibility.
- **Visionary**: High impact. Daily pronunciation practice is an on-the-go micro-habit.
- **Product**: Major Project. Unlocks daily spaced repetition retention loops.

### 4. [[Admin Panel]]
- **Priority**: Medium (P2)
- **Engineer**: Low–Med effort. Requires role-based auth flag (`is_admin`), user audit endpoints, and a simple React dashboard.
- **Visionary**: Neutral utility. Necessary for operators running instances for groups.
- **Product**: Operational Enabler. Prerequisites for multi-tenant and support operations.

### 5. [[Gamification Features]]
- **Priority**: Medium (P2)
- **Engineer**: Low–Med effort. Event hooks, user badge relations, and frontend achievement cards.
- **Visionary**: Low–Med impact. Must focus strictly on phonetic milestones (e.g. "Mastered Palatalization") to avoid generic "AI slop".
- **Product**: Retention Booster. Enhances streak motivation for day-14 and day-30 cohorts.

### 6. [[Community Features]]
- **Priority**: Split — Public Profiles (P2 / High Value); P2P Video Chat (P4 / Paused).
- **Engineer**: Public profiles are Low effort (read-only SQLite query). P2P Video is Very High effort (WebRTC signaling, STUN/TURN, moderation).
- **Visionary**: Random Omegle chat degrades product trust and invites abuse. Public profile streak sharing reinforces accountability.
- **Product**: Extract Public Profiles to P2; archive P2P Video Chat.

### 7. [[Payment System]]
- **Priority**: Low / Deferred (P3)
- **Engineer**: High effort. Crypto webhook reconciliation, subscription states, and feature gating middleware.
- **Visionary**: Medium impact. Premature paywalls before deep organic traction impede growth.
- **Product**: Defer until cloud-hosted SaaS strategy is formalized.

### 8. [[Affiliate and Growth]]
- **Priority**: Low / Deferred (P3)
- **Engineer**: Med–High effort. Hard dependency on [[Payment System]] and [[Admin Panel]].
- **Visionary**: Low impact. Secondary distribution mechanic; pointless without a strong paid conversion funnel.
- **Product**: Sequenced strictly after payments.

### 9. [[Find a Tutor]]
- **Priority**: Paused (P4)
- **Engineer**: Very High effort. Full two-sided marketplace (scheduling, availability, messaging, escrow).
- **Visionary**: Low impact / Strategy Trap. Turns Spiik into a commodity marketplace competing against italki/Preply.
- **Product**: Distraction from core AI phonetics engine. Deprioritize.

---

## 3. Recommended Sprint Roadmap

- **Sprint 1 (Immediate Execution)**:
  1. Add Thai & Vietnamese language support via YAML definitions.
  2. Implement GitHub Actions CI/CD for automated testing and image packaging.
  3. Mobile PWA audit & mobile browser microphone testing.
- **Sprint 2 (Retention & Management)**:
  1. User Management Admin Panel.
  2. Public Profiles with streak and sound-inventory sharing.
  3. Phonetic milestone badges.
- **Sprint 3 (Commercialization & Expansion)**:
  1. Define self-hosted vs cloud tier boundaries.
  2. Implement payment gateway and subscription tiers.
