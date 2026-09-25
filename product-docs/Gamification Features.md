# Gamification Features

**Priority**: Medium (P2 — Exploring / Sprint 2)  
**Impact**: Medium  
**Effort**: Low  
**Quadrant**: Operational Fill-In / Retention Delight  

---

## Overview & Scope
Implement achievement badges and milestone celebrations that encourage continuous spaced repetition practice without descending into superficial gamification gimmicks.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Low.
- **Technical Architecture**:
  - `Badge` definition catalog (static JSON/enum): ID, title, description, criteria type, icon asset.
  - `UserBadge` relation table in SQLite: `user_id`, `badge_id`, `awarded_at`.
  - Event hooks: Check milestone conditions inside existing mutations:
    - Post-practice hook (`backend/app/routers/practice.py`): streak thresholds (7-day, 30-day, 100-day), total words reviewed (50, 250, 1000).
    - Post-drill hook (`backend/app/routers/drill.py`): foreign phonemes trained (e.g. 5 missing sounds conquered).
  - Lightweight frontend badge showcase component on `ProfileScreen`.

### Visionary Perspective
- **Strategic Impact**: Low to Medium.
- **Brand Alignment (Critical Constraint)**:
  - Must avoid generic "AI slop" badges. Principle 2: *"Durable learning outcomes outrank novelty"*.
  - Badges should celebrate genuine **phonetic and pronunciation milestones**:
    - *"Palatalization Prodigy"* (Russian soft consonants mastered)
    - *"Tone Pioneer"* (Thai/Vietnamese tones conquered)
    - *"Dental Fricative Defeated"* (/θ/ and /ð/ consistently scored >90)
    - *"30-Day Spaced Repetition Keeper"*

### Product Perspective
- **Product Value**: Boosts Day-14 and Day-30 retention cohorts. Complements the confidence tiers and streak mechanics already present on the Words screen.

---

## Action Items
1. [ ] Define initial set of 8–10 phonetic & consistency achievement badges.
2. [ ] Add `user_badges` table to SQLite schema.
3. [ ] Implement badge evaluation service on practice session completion.
4. [ ] Render earned badges and progress bars on `ProfileScreen.tsx`.
