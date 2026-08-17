# Peblo TV Mini — Platform Engineering Take-Home Submission

A production-minded, full-stack streaming content management and catalogue publishing platform built with **FastAPI**, **PostgreSQL**, **React**, **TypeScript**, and **Docker**.

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Tech Stack](#2-tech-stack)
3. [Quick Start & How to Run](#3-quick-start--how-to-run)
4. [Demo Credentials](#4-demo-credentials)
5. [Atomic Publishing Strategy](#5-atomic-publishing-strategy)
6. [Storage Abstraction & Cloudflare R2 Migration](#6-storage-abstraction--cloudflare-r2-migration)
7. [Catalogue Search & Scalability Roadmap](#7-catalogue-search--scalability-roadmap)
8. [Why Pre-Published Catalogue? (Trade-off Analysis)](#8-why-pre-published-catalogue-trade-off-analysis)
9. [Seed Data Validation Findings (Deliberate Defects Identified)](#9-seed-data-validation-findings)
10. [Authentication & Role-Based Authorization](#10-authentication--role-based-authorization)
11. [Artwork Validation Engine](#11-artwork-validation-engine)
12. [What was Intentionally Skipped](#12-what-was-intentionally-skipped)
13. [AI Usage Disclosure](#13-ai-usage-disclosure)
14. [Screen Recording Demo Walkthrough](#14-screen-recording-demo-walkthrough)

---

## 1. System Architecture

```text
┌────────────────┐        ┌────────────────┐
│   React CMS    │        │  React Viewer  │
│  (Port 3001)   │        │  (Port 3002)   │
└───────┬────────┘        └────────┬───────┘
        │ Admin & CRUD             │ GET /catalog
        │ + Auth Bearer            │ GET /catalog/search
        ▼                          ▼
┌──────────────────────────────────────────┐
│           FastAPI Backend (Port 8000)    │
│  ├─ Auth / RBAC (JWT + Bcrypt)           │
│  ├─ Server-side Artwork Validator        │
│  ├─ Validation Report Engine             │
│  └─ Atomic Catalogue Publisher           │
└───────┬──────────────────────────┬───────┘
        │                          │
        ▼                          ▼
┌────────────────┐        ┌─────────────────────────┐
│ PostgreSQL 16  │        │   Storage Abstraction   │
│ (Shows/Seasons/│        │ ├─ LocalStorage (/app/  │
│  Episodes/Runs)│        │ │   storage_data)       │
└────────────────┘        │ └─ Cloudflare R2 Ready  │
                          └─────────────────────────┘
```

### Key Architectural Invariants
* **Strict Viewer Isolation**: The Viewer UI consumes **only** `/catalog` and `/catalog/search`. It has zero access to `/admin/*` routes or direct database tables.
* **Server-Enforced Authorization**: Roles (`editor` vs `admin`) are verified cryptographically on every protected route. Editors can perform full CRUD, but only Admins can invoke the publishing engine.
* **Deterministic Content Model**: Season 0 is reserved strictly for trailers/extras and is segregated from regular seasons. Episodes sharing a `content_group` collapse into a single catalogue entry with multi-language audio tags.

---

## 2. Tech Stack

* **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (AsyncIO), Alembic (Migrations), Pydantic v2, PyJWT, Passlib (Bcrypt), Pillow (Image Validation), Pytest.
* **Database**: PostgreSQL 16 (Relational integrity, foreign keys with cascade rules, compound unique constraints, and B-tree indexes).
* **CMS**: React 18, TypeScript, Vite, TanStack Query v5, React Router v6.
* **Viewer**: React 18, TypeScript, Vite, TanStack Query v5, React Router v6 (Netflix-style dark aesthetic).
* **Infrastructure & CI**: Docker, Docker Compose, GitHub Actions.

---

## 3. Quick Start & How to Run

### Prerequisites
* Docker & Docker Compose installed.

### Launching the Stack
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd peblo
   ```

2. Copy the environment configuration:
   ```bash
   cp .env.example .env
   ```

3. Build and spin up the complete containerized stack:
   ```bash
   docker-compose up --build
   ```

4. Service Endpoints:
   * **Viewer Web App**: [http://localhost:3002](http://localhost:3002)
   * **CMS Web App**: [http://localhost:3001](http://localhost:3001)
   * **FastAPI Backend & Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
   * **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

*Note: Database migrations and seed data (including test users and initial catalogue) are applied automatically on startup.*

---

## 4. Demo Credentials

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@example.com` | `admin123` | Full CRUD + Validation Report + Catalogue Publishing |
| **Editor** | `editor@example.com` | `editor123` | Full CRUD + Validation Report (Publishing returns `403 Forbidden`) |

> **Production Note**: Never hardcode production secrets. In staging/production, JWT secret keys and DB credentials are dynamically injected via environment variables or secret managers (e.g., AWS Secrets Manager, HashiCorp Vault).

---

## 5. Atomic Publishing Strategy

### The Problem
Directly overwriting a live `catalogue.json` file risks exposing incomplete or corrupted JSON to concurrent viewer requests if the server process dies, crashes, or suffers an I/O interruption during writing.

### The Solution: Versioned Writes with Atomic Replacement
1. **Validation Gate**: Checks for all publish-blocking issues across shows and episodes. If blockers exist, publication is aborted immediately.
2. **Deterministic Build**:
   * Published shows are grouped by section and sorted alphabetically.
   * `content_group` language variants are collapsed into unified episode structures.
   * Season 0 episodes are extracted into a top-level `trailers` list.
   * Deterministic JSON is formatted with sorted keys.
   * A SHA-256 content hash is computed for idempotency tracking.
3. **Versioned Staging**: The full payload is written to a distinct file: `catalogue/catalogue.<run_id>.json`.
4. **Atomic Pointer Switch**:
   * For filesystem storage: Replaced atomically using `os.replace()` / atomic filesystem operations so readers either see the old complete file or the new complete file.
   * The live pointer `catalogue/current_catalogue.json` is updated.
5. **Audit Trail**: A `PublishRun` record is persisted in PostgreSQL with publisher metadata, timestamp, content hash, and item counts.

### Failure Mode Resilience Matrix

| Failure Point | System State / Consequence | Viewer Impact |
| :--- | :--- | :--- |
| **Dies before writing staged file** | DB transaction uncommitted; no file written. | Viewer continues reading previous valid catalogue. |
| **Dies mid-way through writing staged file** | Partial file exists at `catalogue.<run_id>.json`. | Viewer is completely unaffected (reads `current_catalogue.json`). |
| **Dies before updating live pointer** | Versioned file complete, but pointer untouched. | Viewer continues reading previous valid catalogue. |
| **Dies during pointer atomic swap** | `os.replace` is atomic at OS filesystem level. | Viewer sees either full old catalogue or full new catalogue—never corrupt data. |
| **Dies during metadata DB commit** | Catalogue is updated on storage; DB run record omitted. | Viewer receives new catalogue. Next admin publish reconciles run log. |

---

## 6. Storage Abstraction & Cloudflare R2 Migration

All file interactions (artwork uploads, catalogue storage) occur via the abstract `Storage` base class (`app.storage.base.Storage`):

```python
class Storage(ABC):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...
    async def get(self, key: str) -> Optional[bytes]: ...
    async def delete(self, key: str) -> bool: ...
    async def exists(self, key: str) -> bool: ...
    def get_public_url(self, key: str) -> str: ...
    async def atomic_rename(self, src_key: str, dst_key: str) -> bool: ...
```

### Migrating to Cloudflare R2 / AWS S3
To migrate to Cloudflare R2:
1. Implement `R2Storage(Storage)` using `aiobotocore` / `boto3` pointing to Cloudflare's S3-compatible API endpoint.
2. In `R2Storage`, atomic publishing is implemented by uploading the versioned object `catalogue/catalogue.<run_id>.json` and then uploading/copying to `catalogue/current_catalogue.json` (S3 object puts are atomic at the key level).
3. Switch `STORAGE_BACKEND=r2` in `.env`.
4. **Zero business logic or route handler code changes required.**

---

## 7. Catalogue Search & Scalability Roadmap

### Current Implementation
The Viewer executes searches through `GET /catalog/search?q=&category=&language=&section=`. The backend queries the current published in-memory catalogue snapshot.
* Searches show titles, episode titles, and categories (case-insensitive substring match).
* Filters for category, language (inspecting all audio tracks of collapsed episodes and trailers), and section compose with boolean `AND` logic.

### Scalability Limits & Transition Roadmap

| Scale Stage | Approximate Items | Recommended Technology | Rationale |
| :--- | :--- | :--- | :--- |
| **Stage 1 (Current)** | 1 – 2,000 shows | In-Memory Catalogue Filter | Sub-millisecond latency, zero database contention, edge-cacheable snapshot. |
| **Stage 2** | 2,000 – 100,000 shows | PostgreSQL Full-Text Search (`tsvector` + GIN Index) | Native relational indexing, typo tolerance with `pg_trgm`, faceted query support. |
| **Stage 3 (Enterprise)** | > 100,000 shows | OpenSearch / Elasticsearch / Algolia | Distributed tokenization, phonetics, fuzzy matching, dynamic merchandising, and multi-region search replicas. |

---

## 8. Why Pre-Published Catalogue? (Trade-off Analysis)

Instead of requiring every viewer browsing request to hit the PostgreSQL database with multi-table joins across shows, seasons, episodes, and artwork, Peblo TV serves a compiled, pre-published catalogue.

### Advantages
1. **Predictable Read Performance & High Concurrency**: Static/cached JSON can be distributed to Cloudflare/CloudFront edge nodes, absorbing millions of viewer requests with sub-10ms response times.
2. **Zero Viewer-Induced Database Load**: A spike in streaming traffic during a major premiere will never degrade CMS responsiveness or database connection pools.
3. **Resilience & Blast-Radius Containment**: If the PostgreSQL database or CMS goes down for maintenance, existing viewers experience zero interruption.
4. **Clean Domain Separation**: Separation of write-optimized transactional models (Alembic/PostgreSQL) from read-optimized view schemas.

### Trade-offs & Limitations
1. **Eventual Consistency**: Content changes saved in CMS drafts do not reflect for viewers until an Admin publishes a new release.
2. **Payload Size at Extreme Scale**: If a catalogue grows to tens of thousands of shows, a single monolithic JSON file becomes too large. (Solution: Paginated or per-section catalogue partitioning).

---

## 9. Seed Data Validation Findings

During inspection of the challenge seed data (`seed_shows.json`) and assets, the following deliberate imperfections were identified and handled:

| Item | Problem Identified | Severity | System Handling |
| :--- | :--- | :--- | :--- |
| **"Toon World"** | Missing `section` (empty string `""`). | 🚫 **Blocker** | Surfaced in Validation Report; blocks publication until editor selects a section. |
| **"The Discovery"** (Show: The Great Adventure) | Episode `duration` is `null`. | 🚫 **Blocker** | Surfaced in Validation Report; excluded from catalogue build; blocks publication. |
| **"Main Course Mayhem"** (Show: Cooking Masters) | Episode `duration` is `-300` (negative). | 🚫 **Blocker** | Flagged as invalid duration; blocks publication until corrected. |
| **"Dessert Duel"** (Show: Cooking Masters) | Episode `language` is `"xx"`. | 🚫 **Blocker** | Flagged as unrecognized language code; blocks publication. |
| **"Toon World" Episode 1** | Duplicate `(content_group="tw-s1e1", language="en")`. | 🚫 **Blocker** | Flagged by validation engine; database enforces uniqueness. |
| **"Planet Earth Reimagined"** | Empty `synopsis`. | ⚠️ **Warning** | Flagged in Validation Report for editor attention (non-blocking). |
| **"Cooking Masters"** | Category is `"REALITY"` (not in standard reference spec). | ⚠️ **Warning** | Flagged in Validation Report with valid category recommendations. |
| **"  Cooking Masters  "** | Leading/trailing whitespace in titles. | ⚠️ **Warning** | Flagged in Validation Report; automatically trimmed in published catalogue. |

### Provided Asset Analysis
* `banner_too_big.png` (2560×1440): Rejected by validator (width > 1920px max limit).
* `thumb_tiny.jpg` (160×90): Rejected by validator (width < 320px min limit).
* `poster_good.jpg` (600×900, 2:3): Accepted (valid dimensions, aspect ratio, < 200 KB).
* `thumb_good.jpg` (640×360, 16:9): Accepted (valid dimensions, aspect ratio, < 200 KB).

---

## 10. Authentication & Role-Based Authorization

* Passwords are encrypted using **bcrypt** with salt rounds.
* JWT bearer tokens are issued upon `POST /auth/login` containing user ID, email, and role.
* Fast, declarative dependency injection enforces permissions:
  * `require_role("editor")`: Allows show, season, episode, and artwork mutations.
  * `require_role("admin")`: Enforces privileges for catalogue publication (`POST /admin/catalog/publish`).
* If an `editor` attempts to invoke publishing, the backend responds with `403 Forbidden` (`"This action requires 'admin' role. Your role is 'editor'."`).

---

## 11. Artwork Validation Engine

All artwork uploads (`POST /admin/shows/{id}/artwork` and `POST /admin/episodes/{id}/artwork`) undergo server-side validation using Pillow:

1. **File Type**: Validated against allowed MIME types (`image/jpeg`, `image/png`, `image/webp`).
2. **File Size**: Strictly capped at **200 KB** (rejects oversized uploads with exact KB details).
3. **Dimensions**: Verified against reference min/max width bounds.
4. **Aspect Ratio**: Verified within a 5% tolerance window:
   * **Poster**: 2:3 (~600×900)
   * **Banner**: 16:9 (~1280×720)
   * **Thumbnail**: 16:9 (~640×360)
5. **Human-Readable Errors**: Rejections include helpful explanations (e.g., *"This banner is 800×800 (ratio 1.00), but banners must use a 16:9 aspect ratio (ratio 1.78). Please upload an image closer to 1280×720."*).

---

## 12. What was Intentionally Skipped

Prioritizing an honest, production-grade core over rushed superficial features:

1. **Real-time Video Transcoding / HLS Streaming**:
   * *Why*: The take-home focus is on metadata modelling, validation, and atomic publishing.
   * *Next Step*: Integrate AWS Elemental MediaConvert / Cloudflare Stream for HLS packaging and adaptive bitrate delivery.
2. **OAuth2 / SSO Social Providers**:
   * *Why*: JWT + Bcrypt provides a clean, secure, self-contained authentication experience for local evaluation.
   * *Next Step*: Integrate Google / Okta OpenID Connect (OIDC) providers.
3. **Client-side Image Cropping**:
   * *Why*: Server-side validation is mandatory for security and data correctness.
   * *Next Step*: Add a React canvas-based cropper to assist editors prior to submission.

---

## 13. AI Usage Disclosure

* **AI Assistance Used For**: Scaffolding repetitive boilerplate (Alembic configuration, CSS flexbox/grid layout styling, test parameter variations).
* **Where AI Was Overridden / Rejected**:
  * AI initially suggested writing directly to a static `catalogue.json` file. This was rejected in favor of the versioned staging and atomic rename strategy (`catalogue.<run_id>.json` + atomic pointer swap).
  * AI suggested client-only validation for aspect ratio checks. This was rejected in favor of strict Pillow-based server-side validation.
  * AI suggested querying PostgreSQL directly from the Viewer. This was rejected in favor of strict separation with `/catalog` endpoints.

---

## 14. Time Spent on Each Part

| Phase / Component | Focus Areas | Approximate Time Spent |
| :--- | :--- | :--- |
| **Part A: Backend & Data Modelling** | PostgreSQL relational schema, Alembic migrations, Pillow artwork validation engine, JWT RBAC, composable search, and 49 unit tests. | ~3.5 hours |
| **Part B: Internal CMS** | React + TypeScript forms, 3-slot labelled artwork uploaders with live previews, real-time validation report, and TanStack Query state management. | ~2.5 hours |
| **Part C: Viewer Streaming UI** | JioHotstar/Netflix aesthetic, auto-rotating hero showcase, miniature slider strip, horizontal section carousels, show detail modal, and search chips. | ~2.5 hours |
| **Part D: Pipeline, Docker & CI/CD** | 4-container `docker-compose` orchestration, GitHub Actions CI workflow, `.env.example`, and healthcheck/alerting reasoning. | ~1.5 hours |
| **Part E: Written Analysis & Resilience** | Atomic publishing failure matrix, Cloudflare R2 migration, search scalability roadmap, trade-off analysis, and documentation. | ~1.0 hour |
| **Total Time Invested** | **Comprehensive Full-Stack Implementation** | **~11.0 hours** |

---

## 15. Optional Stretch Goals

* **Versioned Catalogue & Audit Trail**: Every publish run is archived as `catalogue.<run_id>.json` in storage and logged to the `PublishRun` PostgreSQL table with timestamps, publisher email, total counts, and SHA-256 content hashes for instant point-in-time rollbacks and diffing.
* **JioHotstar Signature Viewer UX**: Auto-rotating hero showcase with crossfade transitions, synchronized thumbnail navigator strip, glowing active indicators, and high-density poster grid with hover scaling.

---

## 16. Demo Walkthrough

Follow this concise sequence when recording your demo video:

1. **Login as Editor**:
   * Navigate to `http://localhost:3001`
   * Log in with `editor@example.com` / `editor123`.
2. **Browse & Edit Content**:
   * Show the Shows list with pagination, search, and status filters.
   * Open `"The Great Adventure"` and inspect seasons/episodes.
3. **Demonstrate Artwork Validation**:
   * In Show Edit, upload `banner_too_big.png` or an invalid square image.
   * Point out the human-readable server validation error message.
   * Upload valid artwork (`poster_good.jpg`).
4. **Inspect Validation Report**:
   * Open the **Publish** page.
   * Show the Validation Report displaying identified blockers (e.g., "Toon World has no section", "The Discovery has no duration").
   * Point out that the **Publish** button is disabled with reasons, and highlight the editor permission warning.
5. **Switch to Admin & Resolve Blocker**:
   * Log out and log in as `admin@example.com` / `admin123`.
   * Edit `"Toon World"` and set its section to `"New Releases"`.
   * Edit `"The Discovery"` episode and set its duration to `2400`.
6. **Publish Catalogue**:
   * Return to the **Publish** page. Show that blocking issues are resolved.
   * Click **Publish Catalogue**.
   * Show the newly created entry in the **Publish History** table with timestamp and SHA-256 hash.
7. **Viewer Demonstration**:
   * Open `http://localhost:3002`.
   * Show the **Hero Banner** with gradient overlay and action CTA.
   * Scroll through the **Section Rows** displaying 2:3 poster cards.
   * Click on `"The Great Adventure"` to open the **Show Detail Modal**:
     * Show that **Season 0** is not listed in regular season tabs, but in **"🎬 Trailers & Extras"**.
     * Show that collapsed episodes display multi-language badges (`EN`, `HI`, `TA`).
   * Navigate to **Search & Browse** (`/search`):
     * Search for `"Roast"` to show episode matching.
     * Filter by Category (`Comedy`) and Language (`HI`) to demonstrate filter composition.
