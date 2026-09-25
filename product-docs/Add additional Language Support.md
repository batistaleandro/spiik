# Add Additional Language Support

**Priority**: High (P1 — Immediate Up Next)  
**Impact**: High / Transformational  
**Effort**: Low to Medium  
**Quadrant**: Quick Win / Core Differentiator  

---

## Overview & Scope
Expand the shipped language catalog to cover high-value target languages with non-Latin scripts, as outlined in [[PRODUCT]]:
- **Russian** (shipped)
- **Thai** (implemented)
- **Vietnamese** (target)
- **Georgian** (target)

The primary value proposition of Spiik is strongest when learners are confronted with foreign scripts they cannot easily read phonetically.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Low to Medium per language.
- **Architecture**:
  - The pronunciation engine is already decoupled and data-driven via YAML files in `backend/data/languages/*.yaml`.
  - Process per language:
    1. Probe espeak tokens: `python -m scripts.probe_espeak <lang_code>`
    2. Write YAML definition: `inventory`, `orthography`, `substitutions`, `minor_foreign`, `foreign_display`, `drill_words`.
    3. Configure neural TTS voice in `edge-tts` with offline `espeak-ng` fallback.
    4. Validate against wav2vec2 CTC outputs and handle token variations via `recognized_aliases`.
- **Risks**: Tonal nuances (Thai tones, Vietnamese tones) and diacritics in orthography rendering.

### Visionary Perspective
- **Strategic Impact**: Transformational.
- **Brand Alignment**: Fulfills the anti-"AI slop" promise by delivering genuine linguistic depth. Every new non-Latin language drastically increases the product's defensible moat against generic vocabulary apps.

### Product Perspective
- **User Value**: Extremely high for serious language learners.
- **Acquisition**: Tap into passionate, underserved language learning communities (e.g., learners of Thai, Vietnamese, Georgian).

---

## Action Items
1. [x] Probe espeak for Thai (`th`) and draft `backend/data/languages/th.yaml`.
2. [ ] Probe espeak for Vietnamese (`vi`) and draft `backend/data/languages/vi.yaml`.
3. [ ] Probe espeak for Georgian (`ka`) and draft `backend/data/languages/ka.yaml`.
4. [ ] Curate phoneme substitution rules and native orthographic hints for each.
5. [ ] Add test cases to `backend/tests/` verifying alignment and scoring.
