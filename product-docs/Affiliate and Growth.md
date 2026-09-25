# Growth & Viral Referral Loops

**Priority**: High (P1 / P2 — Viral Network Engine)  
**Impact**: High (Organic User Acquisition & K-Factor)  
**Effort**: Low to Medium  
**Quadrant**: Quick Win / Viral Loop (Decoupled from Payments)  

---

## Strategic Shift: Decoupling Growth from Payments
Previously, referral management was conceived purely as a paid subscription affiliate program, making it strictly blocked by [[Payment System]].

To achieve **viral network effects immediately**, referral and growth mechanisms are decoupled from monetization. Instead of waiting for billing infrastructure, referrals are tied to **social currency and content access**:

1. **Beta Language Unlocks**:
   - Example: *"Invite 2 friends who practice a word to unlock early access to the Thai/Vietnamese Beta."*
2. **Challenge Links ("Can you beat my score?")**:
   - When a user records a word and scores 90%+, they generate a challenge link: *"Leandro scored 92% on 'Здравствуйте'. Can you beat him?"*
   - When the recipient opens the link, records, and scores, both users receive a "Pronunciation Duel" milestone badge.
3. **Shared Deck Attribution**:
   - When a creator shares a word list (e.g., *"Top 100 Difficult Russian Words"*), their profile link is permanently embedded in the deck header.
4. **Future Subscription Ledger Hook**:
   - Store earned referral credits in the user model so when [[Payment System]] launches, past referral advocates automatically receive credited Pro time.

---

## Technical Architecture
- **Referral Tracking**:
  - `referral_code` on `users` table.
  - Attribution via URL query param: `?ref=username` or `?c=challenge_id`.
  - Stored in local cookie / session storage during anonymous trainer use, attached automatically upon registration.
- **Challenge Sessions Table**:
  - `challenge_id`, `creator_id`, `word`, `expected_ipa`, `creator_score`, `receiver_score`, `completed_at`.

---

## Action Items
1. [ ] Add `referral_code` generation to user registration in `backend/app/auth.py`.
2. [ ] Add `?ref=` attribution capture in frontend router.
3. [ ] Implement "Challenge a Friend" one-click button after scoring a pronunciation attempt.
4. [ ] Build "Invite Friends for Beta Language Access" banner.
