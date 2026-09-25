# Basic DevOps

**Priority**: High (P1 — Immediate Up Next)  
**Impact**: High  
**Effort**: Medium  
**Quadrant**: Major Foundation / Enabler  

---

## Overview & Scope
Ensure Spiik is reproducible, automated, reliable, and easily deployable for self-hosters and team developers alike.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Medium.
- **Technical Breakdown**:
  1. **CI/CD Pipeline (GitHub Actions)**:
     - Run backend test suite (`pytest tests/ -q` — 46 passing tests).
     - Run frontend lint and build (`oxlint`, `tsc`, `npm run build`).
     - Automated Docker image builds with caching for the ~1.3 GB HuggingFace wav2vec2 model layer.
     - Automated semantic release / tagging on main branch.
  2. **Deployability & Scaling**:
     - Single-process Docker compose is already functional.
     - Document resource limits (RAM requirements: ~2.5GB minimum recommended for PyTorch + wav2vec2 model in memory).
     - Provide standard systemd service template for bare-metal hosters alongside docker compose.
  3. **Observability**:
     - Keep it lightweight. Full Prometheus/Grafana stack is overkill for a single-node self-hosted app.
     - Recommend structured JSON logging in FastAPI, healthcheck endpoints (`/api/health`), and optional Sentry DSN configuration.

### Visionary Perspective
- **Strategic Impact**: High.
- **Brand Alignment**: Self-hosting is a core product principle (Principle 5: *"Self-hosting is a feature: single process, no paid APIs or keys, learner data stays with the operator"*). If setup is fragile or breaks easily, self-hosters abandon the project.

### Product Perspective
- **Product Value**: Essential infrastructure. Prevents regressions in the core phonetics and audio scoring pipeline during rapid iteration.

---

## Action Items
1. [ ] Create `.github/workflows/ci.yml` for automated linting, backend tests, and frontend build.
2. [ ] Add automated Docker image build and push to container registry (e.g., GitHub Packages / Docker Hub).
3. [ ] Add `/api/health` endpoint returning model loaded status, DB status, and version.
4. [ ] Implement structured request logging and error handling.
