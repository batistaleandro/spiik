# Payment System

**Priority**: Low / Deferred (P3 — Paused until SaaS / Hosting Strategy is Formalized)  
**Impact**: Medium  
**Effort**: High  
**Quadrant**: Major Project (Phase 3)  

---

## Overview & Scope
Implement subscription management, payment processing (including crypto payments), and tier-based feature gating.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: High.
- **Technical Breakdown**:
  - Payment Gateway Integration: Crypto gateway (BTCPay Server / Coinbase Commerce / NOWPayments) or traditional processor (Stripe).
  - Webhook processing pipeline with idempotent event handling and signature verification.
  - Subscription lifecycle management: trial, active, past_due, canceled, expired.
  - Feature-gating middleware in FastAPI: `@require_tier("pro")` decorators protecting premium routes.
- **Risks**: Crypto payment confirmations are asynchronous and subject to block latency, network fees, and transaction reconciliation edge cases. Maintaining feature-blocking in an open-source self-hosted codebase requires clear boundaries (e.g. core open-source vs hosted cloud SaaS edition).

### Visionary Perspective
- **Strategic Impact**: Medium.
- **Brand Alignment**: Spiik's self-hosting principle emphasizes privacy and independence (Principle 5: *"Learner data stays with the operator"*). Gating self-hosted instances with paywalls creates community friction. Monetization belongs primarily on a managed cloud hosted instance.

### Product Perspective
- **Product Value**: Premature monetization before reaching solid organic retention and complete non-Latin language coverage will stall user acquisition.
- **Prerequisites**: Must define exactly what is "Free/Open" vs "Pro" (e.g., cloud sync, premium Azure pronunciation assessment engine, unlimited AI drills) before building payment plumbing.

---

## Action Items
1. [ ] Define commercial packaging: Self-hosted Community Edition (free) vs Spiik Cloud (hosted Pro).
2. [ ] Map out specific gated capabilities (e.g. Azure Pronunciation Assessment API key provisioning, automated cross-device cloud sync).
3. [ ] Select payment provider and design webhook schema.
