# Project Context

This file holds the facts a developer or AI assistant needs before working on the code: what the project is, how it is built, where things are, and which conventions apply. Status and next steps are in [AI_HANDOVER.md](AI_HANDOVER.md). Setup commands are in [README.md](README.md).

Everything here describes the repository at the end of Phase 12.

## Contents

- [Purpose](#purpose)
- [Actors and roles](#actors-and-roles)
- [Entities](#entities)
- [Technology stack](#technology-stack)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Backend conventions](#backend-conventions)
- [Core behaviour](#core-behaviour)
- [Frontend](#frontend)
- [Configuration](#configuration)
- [Data and scripts](#data-and-scripts)
- [Verified state](#verified-state)
- [Environment differences](#environment-differences)
- [Documentation map](#documentation-map)

## Purpose

A hackathon project: a working credential lifecycle management system. It defines eligibility rules, records course completion and assessment results, evaluates eligibility, issues unique signed credentials only when the rules pass, supports third-party verification and authorized revocation, and keeps an audit history.

The binding requirements are in [docs/original-problem-statement.md](docs/original-problem-statement.md). If any other document disagrees with it, the problem statement wins.

## Actors and roles

The problem statement names six actors and does not define their permissions. The code implements the following, which is implementation assumption IA-16 and has not been approved.

| Actor | Role code | What the code allows |
|---|---|---|
| Academic Administrator | `ACADEMIC_ADMINISTRATOR` | Manage learners, courses, issuers and rules; record enrollments, completions and attempts; evaluate eligibility; read audit and reports; **issue and revoke credentials** |
| Platform Administrator | `PLATFORM_ADMINISTRATOR` | Same record keeping and read access; **register and revoke signing keys**; cannot issue or revoke credentials |
| Learner | `LEARNER` | `GET /learners/me/credentials` only |
| Instructor | `INSTRUCTOR` | Can sign in; no route accepts the role |
| Support Staff | `SUPPORT_STAFF` | Can sign in; no route accepts the role |
| Third-party Verifier | `THIRD_PARTY_VERIFIER` | The role exists but is not used. Verification is public and needs no account. |

Role groups are defined in `backend/app/core/roles.py`.

## Entities

The nine mandatory entities and the tables that hold them:

| Entity | Table |
|---|---|
| Learner | `learners` |
| Course | `courses` |
| CredentialRule | `credential_rules`, `credential_rule_versions`, `rule_courses` |
| CompletionRecord | `completion_records` |
| Credential | `credentials` |
| Issuer | `issuers`, `issuer_signing_keys` |
| VerificationRequest | `verification_requests` |
| Revocation | `revocations` |
| AuditEvent | `audit_events` |

Supporting tables bring the total to 23: users and roles, enrollments, assessment attempts, credential scopes and awards, eligibility decisions with reasons and evidence, idempotency records, and yearly ID sequences. The full list is in [docs/database/database-schema.md](docs/database/database-schema.md).

## Technology stack

The stack is a user requirement.

- **Backend:** Python, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings, `python-jose` (JWT), `cryptography` (Ed25519), Pytest
- **Frontend:** React 19, Vite 6, JavaScript, Tailwind CSS 4, React Router 7, Axios
- **Database:** PostgreSQL
- **Infrastructure:** Docker Compose with three services

## Architecture

A modular monolith. One FastAPI process serves a REST API under `/api/v1`. One React single-page application calls it from the browser. One PostgreSQL database stores everything except the signing private key, which is read from the environment.

Request path in the backend: route function in `api/v1/endpoints/` → role check from `core/dependencies.py` → service function in `services/` → SQLAlchemy models in `models/domain.py`. Services write audit events in the same transaction as the change they describe.

Diagrams: [README.md](README.md#architecture) (overview), [docs/system-architecture.md](docs/system-architecture.md) (design baseline), [docs/credential-lifecycle.md](docs/credential-lifecycle.md) (sequence and state diagrams of the implemented behaviour).

## Repository structure

```text
.
├── README.md                     setup and overview
├── AI_HANDOVER.md                status, rules, next steps
├── PROJECT_CONTEXT.md            this file
├── docker-compose.yml            db, backend, frontend
├── .env.example                  variables for Docker Compose
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── .env.example
│   ├── app/
│   │   ├── main.py               app, CORS, exception handlers, /health
│   │   ├── core/
│   │   │   ├── config.py         Settings (environment and .env)
│   │   │   ├── security.py       password hashing, JWT
│   │   │   ├── dependencies.py   current user, role checks, NUL rejection
│   │   │   ├── roles.py          role codes and groups
│   │   │   └── errors.py         ServiceError
│   │   ├── database/             engine, session factory, get_db
│   │   ├── models/domain.py      all 23 tables              (hashed, see below)
│   │   ├── schemas/api.py        request and response models
│   │   ├── services/
│   │   │   ├── audit.py          record_event
│   │   │   ├── management.py     learners, courses, issuers, keys, enrollments, completions, attempts
│   │   │   ├── eligibility.py    rules, rule versions, evaluation
│   │   │   └── credentials.py    issuance, signing, verification, revocation
│   │   └── api/v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── auth.py       login, /auth/me
│   │           └── business.py   every other route, including reports
│   ├── migrations/
│   │   └── versions/af6e5dad6637_create_credential_domain_schema.py   (hashed)
│   ├── scripts/
│   │   ├── bootstrap_demo_user.py
│   │   ├── generate_seed_data.py          (hashed)
│   │   ├── validate_seed_data.py          (hashed)
│   │   ├── seed_data_common.py            (hashed)
│   │   ├── check_reproducibility.py       (hashed)
│   │   ├── full_dataset_common.py
│   │   ├── import_full_dataset.py
│   │   ├── verify_full_dataset.py
│   │   ├── run_full_dataset_validation.py
│   │   ├── exercise_full_dataset_api.py
│   │   └── benchmark_api.py
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── unit/                 4 files, 24 tests, no database
│       └── integration/          support.py and 4 test files, 97 tests, PostgreSQL
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── .env.example
│   └── src/
│       ├── App.jsx               routes and role gating
│       ├── services/api.js       Axios client, token header
│       ├── context/AuthContext.jsx
│       ├── hooks/useResource.js
│       ├── components/           layout, shared UI, ProtectedRoute
│       └── pages/
│           ├── Workspace.jsx     learners, courses, rules, records, eligibility, credentials, revocations, audit, reports
│           ├── analytics/Analytics.jsx
│           ├── dashboard/Dashboard.jsx
│           ├── auth/Login.jsx
│           └── verification/Verification.jsx
├── data/
│   ├── generated/                manifest.json, source_manifest.json
│   ├── ground_truth/             anomaly_fixtures.json
│   └── validation/               seven report files
└── docs/                         see Documentation map
```

"(hashed)" marks files whose SHA-256 is recorded in `data/generated/source_manifest.json`. `docs/original-problem-statement.md` is hashed too. Do not edit these seven files unless you regenerate the dataset manifests. See [AI_HANDOVER.md](AI_HANDOVER.md#do-not-edit-these-files-without-regenerating-the-dataset-manifests).

The packages `backend/app/middleware`, `repositories`, `rules` and `utils`, the file `core/exceptions.py`, the directory `backend/tests/e2e`, and several `frontend/src/pages/*` directories are empty placeholders from the scaffold.

Three of the integration test files and `support.py` were added in Phase 10.2.

## Backend conventions

- **Errors.** Services raise `ServiceError(status_code, detail)`. `main.py` turns it into a JSON response `{"detail": "..."}`. A database `IntegrityError` becomes `409` with a fixed message. A NUL character anywhere in a request becomes `422`. Validation errors from FastAPI are `422` with a list in `detail`.
- **Transactions.** One session per request from `get_db`. The service commits. On an exception the session is rolled back. The single deliberate exception: a rejected issuance commits the decision and the rejection event, then returns `422`.
- **Audit.** `record_event` in `services/audit.py` adds a row to `audit_events` in the caller's session, so the event is committed or rolled back together with the change.
- **Identifiers.** Every table has a single UUID primary key, except `rule_courses`, whose key is the pair `rule_version_id` and `course_id`. Business identifiers are separate columns: `LRN-NNNNNN` for learners, `CRD-YYYY-NNNNNN` for credentials, `VER-YYYY-NNNNNN` for verification requests. Credential and verification numbers come from `yearly_identifier_sequences` under a PostgreSQL advisory lock.
- **Timestamps.** All are timezone-aware and stored as `timestamp with time zone`. Input without a timezone is rejected.
- **Pagination.** List endpoints take `limit` (1 to 100) and a bounded `offset`. They return a plain JSON array, not an envelope.
- **Settings.** `get_settings()` is cached. Values are read once at process start.
- **Status values.** Most are checked in the service layer, not by database constraints.

## Core behaviour

Details and diagrams are in [docs/credential-lifecycle.md](docs/credential-lifecycle.md). The essentials:

- **Eligibility** (`credential-eligibility-v1`): picks the newest rule version in effect, the latest completion from a non-cancelled enrollment, and the latest graded, non-superseded attempt. Outcomes are `eligible`, `ineligible` and `needs_review`, with reason codes such as `MISSING_ENROLLMENT`, `COURSE_INCOMPLETE` and `ASSESSMENT_BELOW_THRESHOLD`. Every evaluation is stored.
- **Issuance:** requires an `Idempotency-Key` header, checks the signing configuration, evaluates eligibility again, enforces one credential per learner and course, then builds the payload, serializes it as canonical JSON, computes SHA-256, signs with Ed25519, and stores payload, digest and signature in one transaction.
- **Verification:** public, always `200`. Result precedence: `TAMPERED`, `INVALID_SIGNATURE`, `UNVERIFIABLE`, `REVOKED`, `VALID`; an unknown ID gives `NOT_FOUND`. Every request is stored and audited.
- **Revocation:** inserts a `revocations` row. The `credentials` table has no status column; a credential is revoked if a revocation row exists for it.
- **Authentication:** PBKDF2-HMAC-SHA256 with 600,000 iterations; HS256 JWT with a 30-minute default lifetime; the user's active flag and roles are read from the database on every request.

## Frontend

- Routes: `/login` and `/verification` are public. `/`, `/learners`, `/courses`, `/rules`, `/completions`, `/eligibility`, `/audit`, `/reports` and `/analytics` need either administrator role. `/credentials` is for both administrators and learners. `/revocations` is for the Academic Administrator.
- The token is stored in `localStorage` under `credential_access_token` and sent as a bearer header by `services/api.js`.
- The API address comes from `VITE_API_BASE_URL` at build time. Vite has no proxy.
- Role gating in the frontend is for presentation only. The backend enforces access.
- There are no screens for issuers, signing keys or portable-payload verification, and no automated tests.

## Configuration

Backend settings (`backend/app/core/config.py`), read from the environment or `backend/.env`:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://...` |
| `SECRET_KEY` | yes | At least 32 bytes; placeholder values are rejected |
| `JWT_ALGORITHM` | no | Only `HS256` is accepted |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Default 30; must be positive |
| `CORS_ORIGINS` | no | Default `http://localhost:5173`; `*` is rejected |
| `CREDENTIAL_SIGNING_ISSUER_CODE`, `CREDENTIAL_SIGNING_KEY_ID`, `CREDENTIAL_SIGNING_PRIVATE_KEY` | for issuance | Private key is base64 of the 32 raw Ed25519 bytes |
| `DEMO_USER_PRINCIPAL_KEY`, `DEMO_USER_PASSWORD`, `DEMO_USER_ROLE`, `DEMO_USER_DISPLAY_NAME` | for `bootstrap_demo_user.py` | |
| `FULL_DATASET_MANIFEST_PATH`, `FULL_DATASET_IMPORT_REPORT_PATH`, `FULL_DATASET_VALIDATION_REPORT_PATH`, `FULL_DATASET_VERIFICATION_REPORT_PATH` | for `GET /reports/data-quality` | Not in any `.env.example` |
| `API_PERFORMANCE_REPORT_PATH` | for `GET /reports/performance` | Not in any `.env.example` |

Variables read only by scripts and tests:

| Variable | Used by |
|---|---|
| `API_TEST_DATABASE_URL` | Integration tests |
| `SYNTHETIC_DATABASE_URL`, `CONFIRM_SYNTHETIC_DATABASE_RESET` | Seed generator and validator |
| `FULL_DATASET_DATABASE_URL`, `CONFIRM_FULL_DATASET_IMPORT` | Full-dataset import and verification |
| `ANALYTICS_API_BASE_URL`, `ANALYTICS_DEMO_USER`, `ANALYTICS_DEMO_PASSWORD` | `benchmark_api.py`, `exercise_full_dataset_api.py` |

Frontend: `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).

Docker Compose (root `.env`): `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, plus the backend variables above except the `FULL_DATASET_*` and performance paths.

## Data and scripts

- The synthetic data generator uses seed `20261022`. Profile `starter` is small; profile `full` produces 839,400 rows, including 20,000 learners, 1,000 courses, 100 rules, 10 issuers, 10,000 credentials, 500 revocations and 5,000 verification requests.
- Ground-truth labels and the anomaly fixtures are stored separately under `data/ground_truth/` and are never read by the application.
- The large generated files (`seed_data.jsonl.gz`, `ground_truth.csv`, `ground_truth.json`) are ignored by Git. The repository contains only manifests and reports.
- Scripts run from `backend/` as `python scripts/<name>.py`. Their default output paths are tracked files under `data/`.
- Guide: [docs/database/seed-data-guide.md](docs/database/seed-data-guide.md). Problems: [docs/known-issues.md](docs/known-issues.md#seed-data-and-full-dataset-tools).

## Verified state

Run at the end of Phase 12 from a clean copy of the code as merged:

| Check | Result |
|---|---|
| `pip install -r requirements.txt` | Succeeded |
| `alembic upgrade head`, `alembic current`, `alembic check` | Revision `af6e5dad6637 (head)`; no pending changes |
| `python -m pytest` with a test database | 122 passed |
| `python -m pytest` without a test database | 25 passed, 97 skipped |
| `npm ci`, `npm run build` | Succeeded |
| Starter seed generation and validation | `passed`, 30 checks |
| API walkthrough in [docs/demo-guide.md](docs/demo-guide.md) | Ran exactly as written |
| Browser check of all pages for three roles | Passed, with the minor defects F-05 and F-06 |

Not verified: Docker Compose, PowerShell command variants, full seed dataset validation with the committed manifests.

## Environment differences

| Item | Project author | Last verification |
|---|---|---|
| Operating system | Windows | Linux |
| Python | 3.13 | 3.11.2 |
| PostgreSQL | 17 (Docker) | 16.2 |
| Node.js | 22 | 22.22.3 |
| Docker Compose | Used | Not available |

The line-ending difference between Windows and Linux is the cause of the manifest hash problem (D-01).

## Documentation map

Current and maintained:

| File | Content |
|---|---|
| `README.md` | Overview, setup, tests, seed data |
| `docs/api-documentation.md` | API reference (48 operations) |
| `docs/database/database-schema.md` | Schema reference (23 tables) |
| `docs/credential-lifecycle.md` | Lifecycle steps, diagrams, failure handling |
| `docs/security.md` | Controls and limitations |
| `docs/backend-testing.md` | Tests |
| `docs/demo-guide.md` | Demonstration |
| `docs/known-issues.md` | Defects and gaps |
| `docs/business-rules.md` | One-page summary of the enforced rules |
| `docs/DECISIONS.md` | Decisions and assumptions |
| `docs/original-problem-statement.md` | Requirements (do not edit) |
| `docs/database/seed-data-guide.md` | Seed data |

Design-time or historical. These were correct when written and have not been brought up to date; where they disagree with the files above, the files above are right:

| File | What it is |
|---|---|
| `docs/system-architecture.md` | Approved architecture baseline, written before implementation |
| `docs/database/entity-catalogue.md`, `data-dictionary.md`, `relationship-specification.md` | Logical database design |
| `docs/development-progress.md` | The author's 11-phase roadmap, last updated before Phase 10.2 |
| `docs/acceptance-test-report.md` | The author's Phase 8 acceptance report, including a Compose run |
| `docs/ANALYTICS_DEMO_GUIDE.md` | The author's guide to the Analytics page on the full dataset (PowerShell) |
| `docs/seed-data-integration-plan.md` | Plan for importing the full dataset |
| `docs/architecture.md`, `database-design.md`, `data-dictionary.md` | Short index pages that point to the documents above |
