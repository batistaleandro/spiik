# Add Additional Language Support

**Priority**: Medium (P2 — Exploring / Deep R&D)  
**Impact**: High / Transformational  
**Effort**: High (Re-evaluated from Low/Med)  
**Quadrant**: Major Strategic Bet / High-Complexity R&D (Downgraded from Quick Win)  

---

## Overview & Scope
Expand the shipped language catalog to cover high-value target languages with non-Latin scripts, as outlined in [[PRODUCT]]:
- **Russian** (shipped)
- **Thai** (partially implemented — blocked on phonetic/approximation polish)
- **Vietnamese** (target — deferred)
- **Georgian** (target — deferred)

The primary value proposition of Spiik is strongest when learners are confronted with foreign scripts they cannot easily read phonetically. However, the linguistic and technical effort required to deliver accurate approximation and scoring for complex non-Latin scripts was significantly underestimated.

---

## Post-Mortem & Real-World Complexity Findings (Thai Implementation)

Initial assumptions that adding a language was a "low/medium effort YAML curation task" failed to account for real-world G2P and phonetic realities:

1. **Script Structure & Word Boundaries**:
   - Unlike Latin or Cyrillic alphabets, Thai is an abugida script written without spaces between words. Relying on espeak-ng for accurate word boundary segmentation and G2P conversion introduces severe acoustic and IPA errors.
2. **Tonal Phonology vs. Native Approximation**:
   - Representing tonal contours in native orthographies (e.g., rendering Thai tones into Brazilian Portuguese or English phonetic spelling) cannot be solved with basic 1:1 phoneme substitution tables.
   - Without tone-aware heuristics in `approx.py`, the generated spelling either misleads learners or produces illegible approximations.
3. **CTC Model (wav2vec2) Discrepancies**:
   - Significant token drift exists between espeak's emitted IPA for tonal languages and what the `facebook/wav2vec2-lv-60-espeak-cv-ft` model actually recognizes. Extensive alias mapping (`recognized_aliases`) and feature distance weighting are required.
4. **Tooling Gaps**:
   - A single probe script (`probe_espeak`) is insufficient for validating end-to-end alignment, drills, and audio playback quality across complex scripts.

---

## Multi-Perspective Evaluation (Revised)

### Engineering Perspective
- **Effort**: High.
- **Architecture Needs**:
  - Deep linguistic research and empirical validation for each target language pair.
  - Dedicated test harnesses in `backend/tests/` evaluating approximation outputs across a corpus of common phrases, not just individual words.
  - Enhancements to the core approximation engine (`app/core/approx.py`) to support tone indicators or syllable-level grouping rules.

### Visionary Perspective
- **Strategic Impact**: Transformational, but only if accurate.
- **Brand Integrity Warning**: Delivering buggy approximations or broken phonetics for non-Latin languages undermines the core mission of being an "anti-AI slop, honest phonetics platform". Getting Thai right matters more than shipping it fast.

### Product Perspective
- **Priority**: Medium.
- **Sequencing**:
  - Stabilize and polish Thai approximate pronunciation and phonetic alphabet generation before starting Vietnamese or Georgian.
  - Clear technical prerequisites (DevOps, mobile baseline) so the team is not debugging infrastructure while simultaneously debugging phonetic engines.

---

## Action Items
1. [x] Probe espeak for Thai (`th`) and draft `backend/data/languages/th.yaml`.
2. [ ] Polish Thai approximate pronunciation rules and phonetic alphabet generation in `approx.py`.
3. [ ] Build an automated test suite verifying Thai phoneme alignment and scoring against edge-tts audio.
4. [ ] Defer Vietnamese (`vi`) and Georgian (`ka`) until the Thai pipeline is production-grade.
