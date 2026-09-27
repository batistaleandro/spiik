# Horizontal Scalability

**Priority**: Medium-High (P2 — Infrastructure Enabler for Hosted Cloud & High Concurrency)  
**Impact**: High  
**Effort**: Medium–High  
**Quadrant**: Major Foundation / Enabler  

---

## Overview & Scope
Enable Spiik to scale horizontally across multiple compute nodes and containers. While v0.4 addressed vertical scaling for single-node self-hosters (worker concurrency, event loop offloading, SQLite WAL), handling high-concurrency viral traffic and powering a hosted multi-tenant edition (Spiik Cloud) requires decoupling stateful components, externalizing the database, and separating heavy machine learning inference into independent worker tiers.

---

## Architectural Challenges & Bottlenecks
1. **Database Layer (SQLite)**: SQLite is bound to a single local filesystem and cannot safely coordinate concurrent writes across distributed replicas without locking or data corruption.
2. **Coupled Model Inference Memory**: Loading ~1.3 GB wav2vec2 acoustic models and Marian translation models into every API worker causes memory duplication (~2.5 GB RAM per replica) and prevents efficient autoscaling of lightweight HTTP endpoints.
3. **Session & Transient State**: Rate limiting, challenge duel matchmaking, P2P video signaling, and caching currently lack a shared backing store across instances.

---

## Multi-Perspective Evaluation

### Engineering Perspective
- **Effort**: Medium to High.
- **Technical Breakdown**:
  1. **Pluggable Database Engine**:
     - Maintain zero-config SQLite for single-process self-hosters.
     - Add PostgreSQL support via SQLAlchemy connection string configuration (`SPIIK_DATABASE_URL`).
     - Standardize database migrations using Alembic.
  2. **Decoupled ML Inference Tier**:
     - Split HTTP API gateway from phoneme scoring and translation workers.
     - Implement an asynchronous task queue (e.g., Redis + Celery/RQ) or internal gRPC inference microservice.
     - Allow API nodes to scale rapidly on lightweight compute while inference workers scale based on queue depth / GPU availability.
  3. **Shared Distributed State & Ingress**:
     - Use Redis for distributed caching, token revocation, and rate limiting.
     - Provide reverse proxy / ingress configurations (Traefik, Nginx) with stateless load balancing.
     - Publish a production-ready multi-node Docker Compose setup and Kubernetes Helm chart.

### Visionary Perspective
- **Strategic Impact**: High.
- **Brand Alignment**: Preserves the core principle (Principle 5: *"Self-hosting is a feature: single process, no paid APIs or keys"*) for individual self-hosters by keeping SQLite as default, while unlocking enterprise-grade scalability and the commercial Spiik Cloud platform.

### Product Perspective
- **Product Value**: Critical technical foundation. Protects user experience during viral traffic surges (e.g. viral "Pronunciation Duels" and social share cards) and unblocks the subscription-based hosted SaaS model (v0.6).

---

## Action Items
1. [ ] Abstract database layer to support external PostgreSQL alongside local SQLite via SQLAlchemy and Alembic.
2. [ ] Decouple wav2vec2 scoring and Marian translation into a dedicated background worker / inference service.
3. [ ] Introduce Redis backing for distributed caching, task queues, and rate limiting.
4. [ ] Create production clustering templates (multi-service Docker Compose and Kubernetes Helm chart).
