# Mobile Version

**Priority**: High (P1 — Immediate Up Next)  
**Impact**: Very High  
**Effort**: Medium (PWA / Responsive Web) | Very High (Native App)  
**Quadrant**: Major Strategic Bet  

---

## Overview & Scope
Provide a first-class mobile user experience for Spiik learners. Pronunciation practice and spaced repetition are micro-habits performed in short daily sessions on mobile devices.

Recommended Strategy: Focus on **Mobile Web / Progressive Web App (PWA)** first to deliver immediate value without App Store friction or native build maintenance.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Medium (PWA) vs Very High (React Native / Flutter / Native iOS & Android).
- **Technical Breakdown**:
  - Audit and polish responsive UI layouts in Vite + React (`TrainerScreen`, `PracticeScreen`, `WordsScreen`).
  - Add web app manifest (`manifest.json`), service worker, and home-screen install metadata.
  - **Audio Recording & Safari Constraints**:
    - Mobile iOS Safari has strict `MediaRecorder` limitations (MIME types, sample rates, autoplay restrictions on audio contexts).
    - Ensure recorded audio streams reliably encode to formats supported by the FastAPI backend (`audio/webm`, `audio/wav`, or transcode via ffmpeg).
  - Audio playback: Handle iOS user-gesture autoplay policies for TTS audio playback.

### Visionary Perspective
- **Strategic Impact**: High.
- **Brand Alignment**: Spiik is designed for real learning outcomes (Principle 2: *"Durable learning outcomes: spaced retention, streaks, and honest scoring outrank novelty"*). A desktop-only spaced repetition app creates friction and kills daily streaks.

### Product Perspective
- **User Value**: Essential for Day 1–Day 30 retention.
- **Roadmap Placement**:
  - Phase 1: Responsive mobile web + PWA installation + rock-solid mobile audio recording.
  - Phase 2 (Future): Evaluate Capacitor/Tauri wrapper if native background audio or notifications become necessary.

---

## Action Items
1. [ ] Test mobile audio recording across iOS Safari and Android Chrome using `useRecorder.ts`.
2. [ ] Add PWA manifest and mobile meta tags to `frontend/index.html`.
3. [ ] Audit mobile viewport styling on `PracticeScreen` and `TrainerScreen` for touch targets and audio waveforms.
