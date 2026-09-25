# Community Features & Crowdsourced Data

**Priority**: High (P1 — Core Growth Engine & Data Flywheel)  
**Impact**: Transformational (Viral K-Factor & Solves Language Curation Bottleneck)  
**Effort**: Medium  
**Quadrant**: Major Strategic Bet / Viral Flywheel  

---

## Strategic Vision: The Community Data Flywheel
Manual linguistic curation (as demonstrated by the Thai implementation) is a severe scaling bottleneck for a solo team. By introducing **crowdsourced phonetic corrections** and **viral social loops**, Spiik turns learners into co-creators, building an insurmountable proprietary dataset while driving organic network effects.

```
       [Learner Practices / Shares Word]
                       │
                       ▼
       [Viral Shareable Phonetic Card] ──► (Attracts new learners/natives)
                       │                                  │
                       ▼                                  ▼
       [Community Suggests/Votes on Approximations] ◄─────┘
                       │
                       ▼
       [Language Engine Improves Automatically]
```

---

## Core Pillars & Functional Requirements

### 1. Crowdsourced Phonetic Data & Corrections (Bottleneck Solver)
* **Problem**: Espeak G2P and initial YAML rules for non-Latin / complex languages (Thai, Vietnamese, etc.) contain flawed approximations and missing sound substitutions.
* **Feature**:
  - **"Suggest Better Spelling"**: A 1-click button on analyzed words and drill cards allowing native speakers and advanced learners to submit a better phonetic approximation in their language.
  - **Community Validation / Upvoting**: Allow users to upvote or confirm the best native spelling (e.g. for Russian "эй" vs "ей", or Thai tone representation).
  - **Crowdsourced Data Export**: Community-approved corrections can be reviewed and automatically merged into `backend/data/languages/*.yaml`.
* **Technical Architecture**:
  - Table `approximation_suggestions`: `word`, `lang_pair`, `suggested_spelling`, `contributor_id`, `upvotes`, `status`.
  - Endpoint `POST /api/community/suggest`: Submit alternate orthographic approximation.
  - Endpoint `POST /api/community/vote`: Upvote/downvote suggestions.

### 2. Viral Shareable Cards (K-Factor Engine)
* **Problem**: Spiik is a single-player tool today; there is no natural social loop bringing in new users.
* **Mechanism**: Phonetic approximations and pronunciation scores are inherently funny, surprising, and shareable.
* **Feature**:
  - **"Share this Spiik"**: Generates a beautiful, high-contrast visual card (PNG/Canvas or dynamic OpenGraph preview):
    - Example: *"How English 'Creation' looks in Brazilian Portuguese: kri-ei-chan"*
    - Example: *"I scored 96% pronouncing 'Здравствуйте' in Russian on spiik."*
  - 1-click share to WhatsApp, X (Twitter), Instagram Stories, Reddit, Telegram.
  - Includes a direct link `/t/:share_id` that opens Spiik with that exact word pre-loaded for the recipient to try and beat the score.

### 3. Public Profiles & Streak Bragging Rights
* **Feature**:
  - Shareable profile `/u/:username` displaying target languages, daily streak, sound inventory mastered, and phonetic achievement badges.
  - Generates dynamic OpenGraph metadata with real-time streak badges for Discord/social previews.

### 4. Shared Decks & Community Word Lists
* **Feature**:
  - Users can create, publish, and share curated practice decks (e.g. *"50 Essential Thai Street Food Words"*, *"Russian Soft Consonants Pack"*).
  - Anyone clicking the link can clone the deck into their local Spiik spaced repetition queue with one click.
  - Creates creator engagement and organic backlinking across language forums.

---

## Paused / Deprioritized Components
* **P2P Video Chat (Omegle Style)**: **Paused (P4)**.
  - High moderation liability, toxic content risk, and complex WebRTC server costs. Asynchronous audio feedback (crowdsourced peer review) will replace real-time video in future phases.

---

## Action Items
1. [ ] Build backend schema for `approximation_suggestions` and voting in SQLite.
2. [ ] Add "Suggest Better Approximation" UI modal on `TrainerScreen.tsx` and `PracticeScreen.tsx`.
3. [ ] Implement social share card generator (Canvas / OpenGraph image) with deep link to the practiced word.
4. [ ] Implement shareable public profile route `/u/:username` with streak visualizer.
5. [ ] Build shared word list import/export endpoint (`/api/decks/share/:id`).
