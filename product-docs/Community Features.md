# Community Features

**Priority**: Split
- **Public Profiles with Streaks**: Medium (P2 — Exploring / Sprint 2)  
- **P2P Video Chat (Omegle Style)**: Paused / Deprioritized (P4)  

---

## 1. Public Profiles with Streaks (P2 — High Value / Low Effort)

### Scope
Allow learners to opt-in to a shareable public profile showing their target languages, current practice streak, words mastered, and phonetic badges.

### Multi-Perspective Evaluation
- **Engineering**: Low effort. Simple read-only endpoint (`GET /api/public/profile/{username}`) returning aggregated stats already calculated in SQLite (`streak`, `words_count`, `mastered_count`). Add an `is_public` toggle to the user profile.
- **Visionary**: Strong social proof and accountability mechanism without introducing moderation risks.
- **Product**: Great organic loop. Learners sharing streaks on Reddit, Twitter, or Discord acts as viral top-of-funnel acquisition for Spiik.

### Action Items
- [ ] Add `is_public: bool` to user profile preferences.
- [ ] Create public profile route `/u/:username` in frontend.
- [ ] Generate dynamic social preview / OpenGraph meta tags for shared streak links.

---

## 2. P2P Video Chat — Omegle Style (P4 — Paused / Strategy Trap)

### Scope
Real-time peer-to-peer random or paired video conversations for language practice.

### Multi-Perspective Evaluation
- **Engineering**: Very High effort. Requires WebRTC signaling servers, STUN/TURN traversal infrastructure, matchmaking state machine, and real-time connection telemetry. Heavy server and operational footprint.
- **Visionary**: **Negative Brand Impact**. Random video chat ("Omegle style") invites abuse, harassment, and severe moderation liabilities. Directly undermines Spiik's position as a serious, privacy-respecting, phonetic learning platform.
- **Product**: Low retention return. Pair matching in niche language pairs suffers from empty queues and mismatched proficiency.

### Recommendation
**Paused indefinitely**. Do not build Omegle-style video chat. Revisit structured, asynchronous audio exchanges or tandem practice loops only if demanded by a large, authenticated user base.
