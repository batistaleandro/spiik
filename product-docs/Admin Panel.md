# Admin Panel & Account Care

**Priority**: High (P1 — v0.5 Target)  
**Impact**: High  
**Effort**: Low to Medium  
**Quadrant**: Operational Fill-In / Essential Governance & Account Care  

---

## Overview & Scope
Provide administrative oversight and user self-service account controls for instance operators and learners. As more learners join an instance, operators require management and support tools, and users require account recovery and privacy controls.

---

## v0.5 Target Capabilities
1. **Operator Administration Panel**:
   - View and manage user accounts (search, list, deactivate/disable, remove).
   - View registration dates, last practice timestamps, review word counts, and confidence distributions.
2. **Account Care & Recovery**:
   - Operator password reset mechanism for locked-out learners.
   - Clean self-service password update for logged-in users.
3. **Privacy & Account Deletion**:
   - Self-service account deletion (`DELETE /api/users/me`) permanently purging user credentials, review records, saved words, and pronunciation attempt history.
   - Admin purge capability for orphaned or abusive accounts.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Low to Medium.
- **Technical Architecture**:
  - Add `is_admin: bool = False` column to `User` model in `backend/app/models.py`.
  - Add admin authentication dependency `get_current_admin` in `backend/app/auth.py` verifying JWT token claims and admin status.
  - Implement REST endpoints:
    - `GET /api/admin/users`: List users with registration date, word count, last practice date, and active status.
    - `POST /api/admin/users/{id}/deactivate`: Toggle account status.
    - `DELETE /api/admin/users/{id}`: Admin purge user data.
    - `POST /api/admin/users/{id}/reset-password`: Operator-assisted password reset.
    - `DELETE /api/users/me`: Authenticated user self-deletion endpoint with cascade deletion of user cards, reviews, and recordings.
  - Build responsive React administrative view under `/admin` and account deletion dialog in Profile settings.

### Visionary Perspective
- **Strategic Impact**: High.
- **Brand Alignment**: Fulfills the open privacy and data ownership commitment. Self-hosters sharing instances with study groups, classrooms, or friends need basic oversight without manual SQLite CLI intervention.

### Product Perspective
- **Product Value**: Solves operational friction. Closes the open question regarding account deletion and password recovery while maintaining zero external email dependencies.

---

## Action Items
1. [x] Add `is_admin: bool = False` to database schema and migrations.
2. [x] Add `get_current_admin` dependency in FastAPI backend.
3. [x] Implement user list, search, deactivate, and admin password reset endpoints.
4. [x] Implement self-service account deletion endpoint (`DELETE /api/users/me`).
5. [x] Create Admin Screen in frontend navigation accessible only to admin users.
6. [x] Add \"Delete Account\" confirmation modal to `ProfileScreen.tsx`.
