# Affiliate and Growth

**Priority**: Low / Deferred (P3 — Paused)  
**Impact**: Low to Medium  
**Effort**: Medium to High  
**Quadrant**: Sequenced After Payment System  

---

## Overview & Scope
Implement affiliate marketing and referral management allowing users to share unique links to unlock free subscription packages (1 week, 1 month, 1 year) based on referred signups or social actions.

---

## Dependencies & Blockers
- **Strictly Blocked by**: [[Payment System]] (Requires existing subscription tiers and entitlement mechanisms to grant "free subscription time").
- **Partially Blocked by**: [[Admin Panel]] (Requires admin visibility to monitor payouts, audit referral fraud, and manage campaign parameters).

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Medium to High.
- **Technical Architecture**:
  - Referral token generator and attribution cookie tracking.
  - User referral relationship table: `referrer_id`, `referred_id`, `status`, `reward_granted`.
  - Fraud prevention checks: IP/device fingerprinting to prevent self-referrals.
  - Ledger hook: Incrementing user subscription duration upon successful referral milestones.

### Visionary Perspective
- **Strategic Impact**: Low.
- **Brand Alignment**: Referral mechanics are secondary distribution engines. If the underlying phonetic engine doesn't produce "aha!" moments, viral invites will not convert.

### Product Perspective
- **Sequencing**: Must strictly follow [[Payment System]] and [[Admin Panel]]. Building referral code systems before the monetization tiers exist results in orphaned code.

---

## Action Items
1. [ ] Revisit after [[Payment System]] implementation.
2. [ ] Define referral reward rules (e.g. "Invite 3 friends who complete a 7-day streak → get 1 month Pro").
