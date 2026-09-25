# Find a Tutor

**Priority**: Paused / Deprioritized (P4)  
**Impact**: Low  
**Effort**: Very High  
**Quadrant**: Money Pit / Marketplace Distraction  

---

## Overview & Scope
Allow language learners to browse, connect with, and book human pronunciation and conversation tutors, accompanied by a dedicated tutor-facing management portal.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Very High.
- **Technical Architecture**:
  - Two-sided marketplace architecture.
  - Tutor onboarding, vetting, and profile management portal.
  - Calendar availability management with multi-timezone scheduling.
  - Booking lifecycle: requests, confirmations, cancellations, rescheduling.
  - Payment escrow, payouts, dispute management, and ratings/reviews system.
- **Operational Complexity**: Drastically increases the architectural footprint of Spiik, shifting it from a focused, self-hostable pronunciation tool into a complex marketplace backend.

### Visionary Perspective
- **Strategic Impact**: Low (Negative Strategic Value).
- **Brand Alignment (Anti-Pattern)**:
  - Diverts Spiik away from its unique, defensible mechanism: *"pronunciation approximation and scoring driven by per-language phoneme data files + wav2vec2 phoneme recognition"*.
  - Forces Spiik to compete directly with entrenched billion-dollar marketplace incumbents (italki, Preply, Cambly) where Spiik possesses neither the liquidity nor the network effects to win.

### Product Perspective
- **Product Value**: Low return on investment.
- **Recommendation**: **Paused indefinitely**. Instead of building a human tutor marketplace, position Spiik as the automated daily pronunciation trainer that learners use *between* their lessons with human tutors elsewhere.

---

## Action Items
1. [x] Deprioritize from active roadmap.
2. [ ] (Future Option) Consider simple read-only affiliate/referral links to established tutor platforms rather than building a custom native marketplace.
