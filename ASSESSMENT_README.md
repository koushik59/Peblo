# Peblo TV Mini — Engineering Assessment Submission

**Candidate:** Rapolu Koushik  
**Role:** Full-Stack Platform Engineer (Python/FastAPI + React)  
**Repository:** [https://github.com/koushik59/Peblo](https://github.com/koushik59/Peblo)  
**CI/CD Status:** GitHub Actions Passing ✅ (49/49 Pytest, Flake8 Clean, Frontend Builds, Docker Validated)

---

## 1. System Architecture

```text
                 ┌─────────────────┐
                 │   React CMS     │
                 │   Port 3001     │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ FastAPI Backend │
                 │ Port 8000       │
                 │ JWT-based RBAC  │
                 └───────┬─────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       ┌─────────────┐       ┌─────────────┐
       │ PostgreSQL  │       │   Storage   │
       │ Database    │       │ Local / R2  │
       └─────────────┘       └──────┬──────┘
                                    │
                              catalogue.json
                                    │
                                    ▼
                           ┌─────────────────┐
                           │  React Viewer   │
                           │  Port 3002      │
                           └─────────────────┘
```

### Key Invariants
* **Strict Viewer Isolation**: The Viewer UI consumes only the public `/catalog` and `/catalog/search` endpoints. It has zero access to admin routes, internal write APIs, or direct database connections.
* **Server-Side Artwork Validation**: Built with Pillow on FastAPI. Enforces Poster (`2:3`, ~600×900), Banner (`16:9`, ~1280×720), Thumbnail (`16:9`, ~640×360), 5% aspect ratio tolerance, and a strict 200 KB ceiling with human-readable error messages for non-technical editors.
* **Season 0 Trailer Convention**: Season 0 is strictly isolated from regular season numbering and displayed in a dedicated **"🎬 Trailers & Extras"** tab in the Viewer.
* **`content_group` Language Variant Collapse**: Episodes sharing a `content_group` (e.g., English and Hindi audio variants) collapse into a single unified catalogue entry with a `languages: ["en", "hi"]` array.
* **JWT-based RBAC**: Roles (`editor` vs `admin`) are verified on protected routes via signed JWT claims. Editors can create and edit content, while invoking catalogue publication is strictly restricted to Admins (returning `403 Forbidden` for editors).

---

## 2. Quick Start & How to Run

### Prerequisites
* Docker & Docker Compose installed.

### Launching the Application
```bash
# 1. Clone repository
git clone https://github.com/koushik59/Peblo.git
cd Peblo

# 2. Copy environment file
cp .env.example .env

# 3. Build and launch all services
docker compose up --build
```

### Live Service Endpoints
* **Viewer Web Application (JioHotstar / Netflix Aesthetic):** [http://localhost:3002](http://localhost:3002)
* **Internal CMS Web Application:** [http://localhost:3001](http://localhost:3001)
* **FastAPI Backend Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### Demo Credentials
| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@example.com` | `admin123` | Full CRUD + Validation Report + Catalogue Publishing |
| **Editor** | `editor@example.com` | `editor123` | Full CRUD + Validation Report (Publishing returns `403 Forbidden`) |

---

## 3. Key API Endpoints

```text
Authentication
  POST   /auth/login                  - Authenticate and receive JWT token

CMS / Admin
  GET    /admin/shows                 - List shows (search, filter, pagination)
  POST   /admin/shows                 - Create new show
  GET    /admin/shows/{id}            - Get show details and seasons
  PATCH  /admin/shows/{id}            - Update show metadata
  DELETE /admin/shows/{id}            - Delete show (cascades)
  POST   /admin/shows/{id}/artwork    - Upload show poster or banner
  POST   /admin/episodes/{id}/artwork - Upload episode thumbnail

Publishing Pipeline
  GET    /admin/validation-report     - Pre-publish audit (blockers vs warnings)
  POST   /admin/catalog/publish       - Build & publish atomic catalogue (Admin only)
  GET    /admin/publish-runs          - List previous publish run history

Viewer (Public)
  GET    /catalog                     - Fetch current published catalogue snapshot
  GET    /catalog/search              - Search & filter published catalogue (q, category, language, section)
  GET    /health                      - System health check (DB + storage status)
```

---

## 4. Technical Written Responses (Part E)

### Q1: How you made publishing atomic — and what happens if the process dies mid-publish?
Publishing avoids direct in-place modification of the live catalogue by using an **immutable staging and pointer strategy**:

```text
Generate catalogue.<run_id>.json
              ↓
    Verify complete write
              ↓
Update published pointer / reference (current_catalogue.json)
              ↓
Viewer reads uninterrupted from previous version until swap completes
              ↓
Expose newly verified catalogue
```

1. **Compilation**: Active published shows are compiled into deterministic JSON and hashed via SHA-256 for idempotency.
2. **Versioned Staging**: The JSON is written to a unique, immutable versioned file: `catalogue/catalogue.<run_id>.json`.
3. **Atomic Pointer Update**: On local filesystem storage, `os.replace()` atomically swaps the live pointer `catalogue/current_catalogue.json`. On object storage (R2/S3), the published reference is updated only after the staged object has been fully written and verified.
4. **Audit Trail**: A `PublishRun` record is persisted in PostgreSQL with publisher metadata, timestamp, content hash, and item counts.

#### Failure Mode Resilience Matrix
| Failure Point | System State | Viewer Impact |
| :--- | :--- | :--- |
| **Dies before writing staged file** | DB transaction uncommitted; no file written. | Viewer continues reading previous valid catalogue. |
| **Dies mid-way through writing staged file** | Partial file exists at `catalogue.<run_id>.json`. | Viewer is completely unaffected (reads `current_catalogue.json`). |
| **Dies before updating live pointer** | Versioned file complete, but pointer untouched. | Viewer continues reading previous valid catalogue. |
| **Dies during pointer atomic swap** | `os.replace` is atomic at OS filesystem level. | Viewer sees either full old catalogue or full new catalogue—never corrupt data. |
| **Dies during metadata DB commit** | Catalogue updated on storage; DB run record omitted. | Viewer receives new catalogue. Next publish run reconciles history. |

> **Conclusion:** A failed publish therefore never replaces the last known-good catalogue.

---

### Q2: Storage abstraction: what changes to move from local disk to Cloudflare R2?
The application depends solely on the abstract `Storage` protocol (`app.storage.base.Storage`):
```python
class Storage(ABC):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...
    async def get(self, key: str) -> Optional[bytes]: ...
    async def delete(self, key: str) -> bool: ...
    async def exists(self, key: str) -> bool: ...
    def get_public_url(self, key: str) -> str: ...
    async def atomic_rename(self, src_key: str, dst_key: str) -> bool: ...
```

* **Local Storage**: Uses filesystem paths and `os.replace()` for atomic pointer updates.
* **Cloudflare R2**: Uses S3-compatible APIs (`boto3`/`aioboto3`), immutable versioned object keys (`catalogue.<run_id>.json`), and a publication-pointer update strategy appropriate for object stores.
* **Migration**: To switch to Cloudflare R2 in production, set `STORAGE_BACKEND=r2` and provide standard R2 credentials in `.env`. **Application routes and business logic remain unchanged.**

---

### Q3: Search: how did you implement it, at what catalogue size does it stop working, and what would you do next?
* **Current Implementation**: `GET /catalog/search?q=&category=&language=&section=` performs composable multi-field filtering over the active in-memory published snapshot. It matches show titles, episode titles, and categories simultaneously.
* **Scalability Roadmap**:
  * **Stage 1 (Initial Scale)**: In-memory catalogue filtering. Simple, sub-millisecond on small-to-moderate datasets, and completely eliminates database contention. Exact thresholds would be determined through production profiling.
  * **Stage 2 (Mid Scale)**: PostgreSQL Full-Text Search using `tsvector` + GIN Index + `pg_trgm` for typo tolerance, phonetic matching, and relational facet aggregation.
  * **Stage 3 (Enterprise Scale)**: Dedicated distributed search cluster (OpenSearch / Elasticsearch / Algolia) with fuzzy tokenization, dynamic merchandising, and multi-region search replicas.

---

### Q4: Why serve a pre-published catalogue file at all instead of querying the database per request? Where does that choice bite you?
* **Why Pre-Publish?**
  1. **Low-Latency Edge Reads**: The published JSON can be cached and distributed through a CDN without requiring a database query per viewer request.
  2. **Zero DB Contention**: High streaming traffic spikes will never exhaust database connection pools or degrade CMS editor responsiveness.
  3. **Decoupled Availability**: If the PostgreSQL database is temporarily undergoing maintenance, the published catalogue can continue serving browsing traffic independently of the CMS database.
* **Where It Bites Us**:
  1. **Eventual Consistency**: Changes made in the CMS do not reflect in the Viewer until an Admin publishes a new release.
  2. **Monolithic Payload Size**: At massive scale (tens of thousands of shows), a single monolithic JSON file becomes too heavy and requires section-based or paginated partitioning.

---

### Q5: What was left out and why? AI tools usage disclosure.
* **What Was Intentionally Skipped**:
  * *Actual Video File Upload & Transcoding Pipeline*: Not implemented because the challenge explicitly specifies artwork uploads and catalogue metadata rather than a media ingestion pipeline. Adding HLS/DASH transcoding would increase infrastructure scope without improving the evaluated CMS/catalogue/publishing requirements.
  * *OAuth2 / SSO Social Logins*: Implemented self-contained JWT + Bcrypt for easy local evaluation.
* **AI Usage Disclosure**:
  * *Accepted*: AI assistance for scaffolding repetitive boilerplate (Alembic migration templates, CSS layout styling, test parameter variations).
  * *Rejected / Overridden*: Overrode AI suggestions to query PostgreSQL directly from the Viewer; rejected client-only validation in favor of strict server-side Pillow verification; rejected direct file overwriting in favor of versioned immutable staging.

---

## 5. Time Spent Breakdown

| Phase / Component | Focus Areas | Approximate Time Spent |
| :--- | :--- | :--- |
| **Part A: Backend & Data Modelling** | PostgreSQL relational schema, Alembic migrations, Pillow artwork validation, JWT RBAC, search, and 49 unit tests. | ~3.5 hours |
| **Part B: Internal CMS** | React + TypeScript forms, 3-slot artwork uploaders with live previews, validation report, and TanStack Query state management. | ~2.5 hours |
| **Part C: Viewer Streaming UI** | JioHotstar/Netflix aesthetic, auto-rotating hero showcase, miniature slider strip, section carousels, show detail modal, and search chips. | ~2.5 hours |
| **Part D: Pipeline, Docker & CI/CD** | 4-container Docker Compose stack, GitHub Actions CI workflow, `.env.example`, and healthcheck/alerting reasoning. | ~1.5 hours |
| **Part E: Written Analysis & Resilience** | Atomic publishing failure matrix, Cloudflare R2 migration, search scalability roadmap, trade-off analysis, and documentation. | ~1.0 hour |
| **Total Time Invested** | **Comprehensive Full-Stack Implementation** | **~11.0 hours** |

---

## 6. Operability & Health Alerting

* **Health Endpoint:** `GET /health` tests PostgreSQL connectivity (`SELECT 1`) and storage read/write status.
* **Primary Production Alert:** `publish_job_failure_count > 0` OR `publish_duration_seconds > 10s`.
  * *Reasoning:* The publish pipeline is the single critical bridge between CMS content creation and viewer delivery. Alerting immediately catches database locks, storage network timeouts, or serialization errors before viewers experience stale or broken catalogues.
