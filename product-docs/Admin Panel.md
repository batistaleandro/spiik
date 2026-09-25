# Admin Panel

**Priority**: Medium (P2 — Exploring / Sprint 2)  
**Impact**: Medium  
**Effort**: Low to Medium  
**Quadrant**: Operational Fill-In / Unblocker  

---

## Overview & Scope
Provide administrative oversight for instance operators to manage user accounts, review usage metrics, and support multi-user self-hosted or managed deployments.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Low to Medium.
- **Technical Architecture**:
  - Add `is_admin` boolean column to `User` model in `backend/app/models.py`.
  - Add admin authentication dependency in `backend/app/auth.py` verifying JWT token claims and admin status.
  - Implement admin REST endpoints:
    - `GET /api/admin/users`: List users with registration date, word count, last practice date, and active status.
    - `POST /api/admin/users/{id}/deactivate`: Toggle account status.
    - `DELETE /api/admin/users/{id}`: Purge user data (fulfills open privacy/deletion requirement).
    - `POST /api/admin/users/{id}/reset-password`: Manual password reset by operator.
  - Build simple React administrative dashboard view under `/admin`.

### Visionary Perspective
- **Strategic Impact**: Medium.
- **Brand Alignment**: Operators who host Spiik for friends, family, or small study groups need basic governance without manually executing SQLite CLI queries.

### Product Perspective
- **Product Value**: Unblocks basic user support and data management. Serves as a foundational prerequisite for future commercial / multi-tenant capabilities.

---

## Action Items
1. [ ] Add `is_admin: bool = False` to database schema and migrations.
2. [ ] Add `get_current_admin` dependency in FastAPI backend.
3. [ ] Implement user list, search, deactivate, and password reset endpoints.
4. [ ] Create Admin Screen in frontend navigation accessible only to admin users.
