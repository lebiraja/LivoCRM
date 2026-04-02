# Development Guide: Production-Grade Full-Stack AI Platform Blueprint

## 1. Purpose and Scope

This guide documents how the system is implemented as a production-ready platform, focusing on architecture, engineering decisions, integration patterns, infrastructure, and operational practices.

It is intentionally implementation-centric, not feature-centric. The goal is to provide a reusable blueprint for building similar AI-enabled systems with:

- A web frontend and API backend
- AI inference and retrieval integration
- Polyglot persistence (transactional + relationship intelligence)
- Containerized deployment with reverse proxy entrypoint
- Security, reliability, and maintainability baked into architecture


## 2. System Topology

### 2.1 Runtime Components

- `nginx` as the public ingress, reverse proxy, and request-shaping layer
- `frontend` (Next.js App Router) for UI plus BFF-style API routes
- `backend` (FastAPI) for orchestration, analysis, auth APIs, and persistence
- `postgres` (source of truth for transactional state)
- `neo4j` (graph intelligence layer for relationship traversal and recommendations)
- `minio` (S3-compatible object storage for uploaded artifacts)
- Optional `cloudflared` for tunnel-based exposure

### 2.2 Request Entry and Routing

Public traffic enters through Nginx (`nginx/nginx.conf`) and is routed by URL namespace:

- `/api/auth/*`, `/api/analyze`, `/api/snapshots*` -> Next.js route handlers (cookie-aware BFF proxy)
- `/api/*` (general backend endpoints) -> FastAPI directly
- `/*` -> Next.js pages/assets

This split is a deliberate BFF pattern: browser-facing auth/session cookie handling stays in Next.js, while business and data orchestration stays in FastAPI.


## 3. Architecture Style and Design Principles

### 3.1 Architectural Style

- Layered modular monolith (backend modules under `backend/src`)
- BFF + API orchestration (Next.js route handlers as auth-aware proxy)
- Hybrid persistence (PostgreSQL + Neo4j)
- Graceful degradation for optional subsystems (graph, object storage, external AI service)

### 3.2 Key Principles Applied

- Single source of truth for transactional correctness (PostgreSQL)
- Intelligence as an additive layer (Neo4j mirrors relations, does not own core truth)
- Non-blocking optional integrations (graph/storage failures should not break primary flows)
- Explicit API contracts through Pydantic models and typed frontend calls
- Environment-driven configuration for portability across local/dev/prod


## 4. Backend Implementation Guide (FastAPI + Python)

### 4.1 Module Structure

- `backend/backend_api.py`: process entrypoint, app bootstrap, route registration, lifecycle startup
- `backend/src/auth/*`: OAuth and JWT handling
- `backend/src/db/*`: async SQLAlchemy engine, models, snapshot/growth routers
- `backend/src/core/*`: business services (resume parser, GitHub analyzer, mentor logic, graph sync, task pipeline, diff engine, storage)

This keeps transport concerns, domain logic, and persistence concerns separated while still maintaining low deployment complexity.

### 4.2 API Composition and Routing

Core API surfaces:

- `/api/analyze`: orchestrates resume parsing + GitHub analysis + mentor calls + persistence + graph/task pipelines
- `/api/chat`: RAG-enabled conversational endpoint using session context
- `/api/snapshots*`: authenticated historical analysis retrieval
- `/api/growth/*`: task, progress, timeline, and skill-gap endpoints
- `/auth/*`: Google OAuth and token lifecycle

The backend applies progressive capability loading (try-import flags such as `DB_AVAILABLE`, `GROWTH_AVAILABLE`, `RAG_AVAILABLE`). This allows controlled startup in partially provisioned environments.

### 4.3 Concurrency and Data Flow

On analysis request (`/api/analyze`):

1. Validate API key and optional JWT context.
2. Run resume parse and GitHub analysis concurrently (`asyncio.gather` + `to_thread`).
3. Generate structured mentor output via multi-prompt Bedrock orchestration.
4. Initialize per-session RAG index (session-scoped engine, not global singleton).
5. Persist snapshot in PostgreSQL if authenticated.
6. Upload resume artifact to MinIO when available.
7. Generate and persist actionable tasks (pipeline output).
8. Mirror benchmark/reanalysis state into Neo4j.
9. Return normalized response payload for frontend state hydration.

### 4.4 Domain Patterns Used

- Service object pattern: `GraphSyncService` wraps graph operations and fault tolerance.
- Pipeline pattern: `task_pipeline.py` composes deterministic scoring + template selection, optionally refined by LLM.
- Strategy/fallback behavior: LLM-first parsing/scoring with heuristic fallback in `resume_parser.py` and `project_evaluator.py`.
- Session state encapsulation: `session_manager.py` provides per-session state + TTL cleanup.

### 4.5 Error Handling and Fault Tolerance

- Integration failures (Neo4j, MinIO, LLM) are mostly non-fatal and logged.
- API surfaces return actionable HTTP errors for hard failures and controlled fallback for soft failures.
- Health endpoints expose service availability rather than binary process-only checks.

Trade-off:

- This increases availability and developer ergonomics, but can mask latent integration drift if observability is weak. Monitoring must alert on degraded mode frequency.


## 5. Frontend Implementation Guide (Next.js + TypeScript)

### 5.1 Frontend Architecture

- App Router structure under `frontend/app`
- Route-handler BFF under `frontend/app/api/*`
- Shared state via Context providers in `frontend/lib/AuthContext.tsx` and `frontend/lib/AnalysisContext.tsx`
- Feature-oriented UI composition under `frontend/components/*`

### 5.2 BFF Pattern in Practice

The frontend route handlers perform:

- Cookie extraction (`cw_access_token`)
- Header transformation to backend Bearer token
- Backend proxy calls with status passthrough
- Localized fallback behavior for select endpoints

This prevents JWT exposure to browser JavaScript and centralizes auth transport concerns.

### 5.3 State and Data Management

- `AuthProvider`: session restoration (`/api/auth/me`), login redirect orchestration, logout invalidation
- `AnalysisProvider`: latest snapshot prefetch for authenticated users, snapshot list and point-in-time loading
- Typed API helpers in `frontend/lib/api.ts` standardize request construction and error normalization

### 5.4 Frontend-to-Backend Data Flow

1. UI submits to Next.js route handler (same-origin).
2. Route handler enriches request (API key, bearer token from cookie).
3. FastAPI processes and returns normalized JSON.
4. Context providers hydrate dashboard and growth views.
5. Subsequent mutation endpoints (task status/project submission) use the same proxy pattern.


## 6. Persistence and Data Modeling

### 6.1 PostgreSQL (Transactional Source of Truth)

Key entities (`backend/src/db/models.py`):

- `User`
- `Snapshot` (versioned point-in-time analysis state)
- `TaskItem` (actionable improvement plan)
- `ProjectSubmission` (evidence and evaluation)
- `ResumeFile` (object storage pointer)
- `Recommendation` (legacy compatibility)

Design choices:

- JSON columns (`raw_analysis_json`, `skills_json`, `diff_json`) optimize schema agility for AI-shaped payloads.
- UUID primary keys for distributed-safe entity generation.
- Snapshot parent relation supports temporal diffing and growth timelines.

Trade-off:

- JSON-heavy schema accelerates iteration but reduces strict relational constraints and can complicate ad hoc analytics unless materialized views or ETL are added.

### 6.2 Neo4j (Intelligence Layer)

Graph models user-skill-role-task-project relationships for queries such as:

- skill gap analysis
- impact-weighted task prioritization
- task effectiveness feedback loops
- progress graph visualization

Critical principle: graph writes are downstream mirrors of PostgreSQL state, not authoritative mutations.

### 6.3 Object Storage (MinIO)

Resume binaries are externalized to object storage with metadata pointers in relational storage. This avoids bloating PostgreSQL and enables presigned retrieval.


## 7. AI and Integration Layer

### 7.1 AWS Bedrock Integration Pattern

The system integrates Bedrock via `boto3` clients for:

- LLM inference (mentor analysis, summarization, evaluator prompts)
- Embeddings (RAG retrieval indexing/search)

Configuration is environment-based (`AWS_*`, `BEDROCK_*`) and supports endpoint override for compatible proxies.

### 7.2 Prompt Architecture

Instead of one giant prompt, mentor generation uses focused prompts:

- role fit
- roadmap
- project suggestions
- final synthesis
- additional GitHub profile review

This pattern improves debuggability and response quality control, at the cost of higher call count and latency.

### 7.3 External API Integration

- GitHub: authenticated API access with bounded repository scan and targeted deep enrichment
- Google OAuth: code exchange server-side, JWT issuance internal to platform
- Email services: dual path support (legacy SMTP and Gmail API)

### 7.4 Retry/Fallback Strategy

- Hard dependencies (core backend logic) return explicit errors.
- Soft dependencies (graph, optional AI enrichment) degrade gracefully.
- Heuristic fallback logic preserves continuity when LLM output is malformed/unavailable.


## 8. Infrastructure and Deployment Blueprint

### 8.1 Containerization Strategy

- Backend image: slim Python base, system dependencies for document processing, non-root runtime, healthcheck
- Frontend image: multi-stage Next.js standalone build, minimal runtime image, non-root runtime, healthcheck
- Nginx image: immutable config baked into image

### 8.2 Environment Separation

- `docker-compose.local.yml`: full local parity with Neo4j + MinIO and exposed debug ports
- `docker-compose.yml`: primary stack with production-style networking and optional tunnel
- `deployment/docker-compose.prod.yml`: resource limits, production health checks, image-tag-oriented deployment

### 8.3 Reverse Proxy and Edge Behavior

Nginx responsibilities:

- route segmentation by endpoint class
- rate limiting (`limit_req_zone`) for API traffic
- security header injection
- body size constraints and timeout tuning per endpoint type

### 8.4 Deployment Workflow

Deployment scripts in `deployment/scripts` support image build/push and environment bring-up. Standard production flow:

1. Build/tag images.
2. Push to registry.
3. Deploy compose stack with environment-specific `.env`.
4. Validate health endpoints.
5. Monitor logs and resource consumption.


## 9. Security Architecture

### 9.1 Authentication and Session Security

- OAuth 2.0 with Google for identity bootstrapping
- Internal JWT access/refresh token model
- Access token stored in `httpOnly`, `sameSite=lax` cookies set by Next.js callback route
- Browser never directly handles bearer tokens in client-side storage

### 9.2 Service-to-Service Controls

- Internal API key gate for selected backend endpoints
- Network isolation via Docker bridge network
- Least-privilege runtime through non-root containers

### 9.3 Perimeter Hardening

- Nginx security headers
- Request size/time limits
- API rate limiting at ingress

Recommended next hardening:

- enforce TLS termination at ingress for all environments
- rotate secrets through managed secret store
- add scoped service identities and short-lived credentials


## 10. Scalability and Performance Engineering

### 10.1 Compute Scaling

- Stateless frontend and backend services are horizontally scalable behind ingress
- Uvicorn worker model improves backend throughput for mixed I/O workloads

### 10.2 Data Scaling

- PostgreSQL pooling configured in SQLAlchemy async engine
- Graph workload isolated to Neo4j, reducing pressure on transactional DB
- Binary payloads offloaded to object storage

### 10.3 Latency and Throughput Optimizations

- Parallelized resume/GitHub analysis
- Parallel LLM subtasks in mentor pipeline
- Bounded GitHub enrichment scope to control API latency and limits
- Session-local in-memory vector store to avoid persistent vector DB overhead for short-lived contexts

Trade-off:

- Session-local vector stores reduce complexity but do not provide long-term conversational memory or multi-node consistency without externalization.


## 11. Reliability, Observability, and Operations

### 11.1 Reliability Patterns

- Health checks at service and compose levels
- Startup-time best-effort initialization (DB, object storage)
- Non-fatal handling for optional subsystems

### 11.2 Logging and Diagnostics

- Service logs include startup capability status and warning-path events
- CSV-based response validation telemetry available in backend logs directory

Recommended production additions:

- structured JSON logging with correlation IDs
- centralized log aggregation (ELK/OpenSearch/Grafana stack)
- metrics and tracing (OpenTelemetry)
- SLO-based alerting (error rate, latency percentiles, degraded-mode events)


## 12. Maintainability and Extensibility Patterns

### 12.1 How New Services Are Added Safely

Use this sequence:

1. Define service interface in `core/` with deterministic fallback behavior.
2. Register feature flags or import-guard availability checks.
3. Integrate at orchestration points (`backend_api.py` routers/workflows).
4. Add frontend BFF route handlers if browser auth/cookies are involved.
5. Add persistence linkage (models + migration strategy).
6. Add health and observability signals.

### 12.2 API Evolution Strategy

- Keep response envelopes backward-compatible when possible.
- Use version markers in persisted analysis payloads (`analysis_version`).
- Isolate legacy compatibility in dedicated model fields/modules instead of duplicating logic globally.

### 12.3 Database Evolution Strategy

- Current implementation supports startup auto-create; production should transition to explicit Alembic migration workflows for controlled rollouts and rollback safety.


## 13. Engineering Trade-offs and Rationale Summary

- Next.js BFF + FastAPI core:
	- Chosen for secure cookie handling and clear separation of web/session concerns from compute-intensive backend logic.
- PostgreSQL + Neo4j hybrid:
	- Chosen to preserve transactional integrity while enabling relationship-native intelligence queries.
- JSON-rich relational payloads:
	- Chosen for fast iteration on AI-shaped schemas and evolving response structures.
- Multi-call AI orchestration:
	- Chosen for better quality decomposition and targeted prompt control.
- Graceful degradation approach:
	- Chosen for resilience and uptime in partially degraded external dependency conditions.


## 14. Reusable Reference Checklist

Use this as a template for similar production systems:

- Edge ingress with explicit route segmentation and API rate limiting
- BFF layer for secure cookie/token bridging
- Strongly typed API contracts and normalized error surfaces
- Async backend orchestration with bounded concurrency
- Separation of transactional storage, graph intelligence, and binary object storage
- Explicit fallback and degraded-mode behavior for optional integrations
- Containerized non-root services with health checks
- Environment-based configuration and secret discipline
- Observability plan that distinguishes functional success from degraded operation


## 15. Practical Next Improvements (if adopting this blueprint)

- Introduce Alembic-driven migrations and migration gates in CI/CD.
- Add centralized metrics/tracing and correlation IDs across Nginx -> Next.js -> FastAPI.
- Externalize session and vector state (Redis/vector store) for horizontal chat scaling.
- Implement circuit breakers and retry budgets for upstream APIs (GitHub/Bedrock).
- Add contract and integration tests for BFF proxy routes and auth cookie flows.

