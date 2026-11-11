# Credential Lifecycle Management System

A web application that issues course credentials only after a learner meets the configured requirements, signs each credential with Ed25519, lets anyone verify a credential without an account, supports revocation, and keeps an audit trail of every decision.

This is a hackathon MVP. It runs locally and has an automated backend test suite. It is not hardened for production.

## Contents

- [Problem statement](#problem-statement)
- [Objectives](#objectives)
- [Features](#features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Docker Compose](#docker-compose)
- [Run the tests](#run-the-tests)
- [Seed data](#seed-data)
- [Demonstration](#demonstration)
- [Documentation](#documentation)
- [Known limitations](#known-limitations)
- [Project status](#project-status)

## Problem statement

> Issue credentials after completion requirements are met and support revocation and third-party verification.

The full, unmodified requirements are in [docs/original-problem-statement.md](docs/original-problem-statement.md). That file is the source of truth for scope.

## Objectives

The problem statement lists ten objectives. The table shows where each one is implemented.

| # | Objective | Where it is implemented |
|---|---|---|
| 1 | Define credential eligibility requirements | Versioned credential rules: `POST /api/v1/credential-rules` and `POST /api/v1/credential-rules/{rule_code}/versions` |
| 2 | Record course completion and assessment results | `POST /api/v1/enrollments`, `/completions`, `/assessment-attempts` |
| 3 | Evaluate whether learners satisfy the requirements | `POST /api/v1/eligibility/evaluate` (`backend/app/services/eligibility.py`) |
| 4 | Issue unique credentials only after all requirements pass | `POST /api/v1/credentials/issue` re-evaluates eligibility inside the issuing transaction |
| 5 | Create verifiable signed-record metadata or deterministic hashes | Canonical JSON, SHA-256 digest, Ed25519 signature stored with each credential |
| 6 | Support third-party verification | `POST /api/v1/verification/credential-id` and `/verification/portable`, no account needed |
| 7 | Support authorized revocation | `POST /api/v1/revocations/{credential_id}`, Academic Administrator only |
| 8 | Preserve immutable-style audit history | Append-only `audit_events` table, `GET /api/v1/audit`, `GET /api/v1/credentials/{credential_id}/history` |
| 9 | Expose important business decisions and exceptions | Stored eligibility decisions with reason codes; rejected issuance is recorded |
| 10 | Produce measurable evaluation outputs | Report endpoints under `/api/v1/reports/*`, the Analytics page, and the validation reports in `data/validation/` |

## Features

**Records and rules**

- Learners, courses, issuers, and course enrollments.
- Credential rules with numbered versions and effective dates. A rule can require course completion, a minimum score, or both.
- Completion records and assessment attempts. A new attempt never overwrites an earlier one.

**Eligibility and issuance**

- Eligibility decisions store the outcome, the reason codes, the rule version used, and a snapshot of the evidence.
- Issuance evaluates eligibility again at the moment of issuing. An ineligible learner gets `422` and no credential.
- Credential IDs have the form `CRD-YYYY-NNNNNN` and are unique.
- One credential per learner and course. A retry with the same `Idempotency-Key` returns the same credential.

**Integrity and verification**

- Each credential payload is serialized as canonical JSON, hashed with SHA-256, and signed with Ed25519.
- The private key stays in the backend environment. The database stores only public keys.
- Public verification returns one of `VALID`, `REVOKED`, `TAMPERED`, `INVALID_SIGNATURE`, `UNVERIFIABLE`, or `NOT_FOUND`.
- The public response contains no learner name and no score.

**Control and visibility**

- Password login with JWT bearer tokens and role checks on every protected route.
- Revocation with a reason. A revoked credential verifies as `REVOKED` immediately.
- 19 audit event types covering record changes, decisions, issuance, verification, and revocation.
- Reports on issuance, revocation, verification, eligibility, courses, and scores.

**Data**

- A deterministic synthetic data generator (seed `20261022`) with a small `starter` profile and a `full` profile of 839,400 rows.
- Separate ground-truth labels, validation checks, and a reproducibility report.

## Architecture

The system is a modular monolith: one React application, one FastAPI application, one PostgreSQL database.

```mermaid
flowchart LR
    subgraph Users
        ADMIN[Academic and Platform Administrators]
        LEARNER[Learner]
        VERIFIER[Third-party verifier, no account]
    end

    subgraph Frontend["Frontend: React 19 + Vite"]
        UI[Workspace pages]
        PUB[Public verification page]
    end

    subgraph Backend["Backend: FastAPI"]
        AUTH[Authentication and role checks]
        API[REST API /api/v1]
        ELIG[Eligibility service]
        CRED[Credential service: issue, verify, revoke]
        AUD[Audit service]
    end

    DB[(PostgreSQL: 23 tables)]
    KEY[/Ed25519 private key in environment/]

    ADMIN --> UI
    LEARNER --> UI
    VERIFIER --> PUB
    UI -->|JWT bearer token| AUTH
    PUB -->|no token| API
    AUTH --> API
    API --> ELIG
    API --> CRED
    ELIG --> DB
    CRED --> DB
    CRED --> AUD
    ELIG --> AUD
    AUD --> DB
    KEY -.-> CRED
```

The credential lifecycle in order:

```mermaid
flowchart LR
    A[Learner registered] --> B[Enrolled in course]
    B --> C[Completion recorded]
    C --> D[Assessment recorded]
    D --> E{Eligible?}
    E -- no --> F[Decision stored with reason codes]
    E -- yes --> G[Credential issued and signed]
    G --> H[Public verification: VALID]
    G --> I[Revoked]
    I --> J[Public verification: REVOKED]
```

More detail: [docs/system-architecture.md](docs/system-architecture.md) (design baseline) and [docs/credential-lifecycle.md](docs/credential-lifecycle.md) (behaviour as implemented).

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React 19, React Router 7, Vite 6, Tailwind CSS 4, Axios |
| Backend | Python, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings |
| Database | PostgreSQL |
| Authentication | PBKDF2-HMAC-SHA256 password hashes, HS256 JWT (`python-jose`) |
| Credential signing | Ed25519 (`cryptography`) |
| Tests | Pytest, FastAPI `TestClient` |
| Containers | Docker Compose (`postgres:17-alpine`, `python:3.13-slim`, `node:22-alpine`) |

## Repository layout

```text
backend/
  app/
    main.py                  application, CORS, error handlers
    core/                    settings, security, role checks, errors
    database/                engine and session
    models/domain.py         all 23 tables
    schemas/api.py           request and response models
    services/                audit, credentials, eligibility, management
    api/v1/endpoints/        auth.py, business.py
  migrations/                Alembic, one revision (af6e5dad6637)
  scripts/                   demo users, seed data, full-dataset tools
  tests/                     unit and integration tests
frontend/
  src/                       pages, components, API client
data/
  generated/                 dataset manifests
  ground_truth/              anomaly fixtures
  validation/                validation and reproducibility reports
docs/                        project documentation
docker-compose.yml
```

## Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Python | 3.11 or newer | Backend |
| Node.js and npm | Node 22 | Frontend |
| PostgreSQL | 16 or newer | Database |
| `curl` and `jq` | any | Optional, for the command-line demonstration |
| Docker with Compose | any recent | Optional, alternative to local installs |

Versions checked for this document: Python 3.11.2, Node 22.22.3, npm 10.9.8, PostgreSQL 16.2. The Docker images use Python 3.13 and PostgreSQL 17.

## Setup

Commands are written for a POSIX shell (Linux, macOS, Git Bash, WSL). Where PowerShell differs, the difference is noted.

### 1. Create the database

Create an empty PostgreSQL database and a user that owns it. Example with the standard client tools:

```bash
createdb credential_management
```

If you prefer Docker for the database only, `docker compose up -d db` starts PostgreSQL 17 on port 5432 with the credentials from the root `.env` file (see [Docker Compose](#docker-compose)).

### 2. Configure the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
```

Edit `backend/.env`:

| Variable | Required | Value |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+psycopg://USER:PASSWORD@localhost:5432/credential_management` |
| `SECRET_KEY` | yes | At least 32 bytes. The placeholder in `.env.example` is rejected at start-up. |
| `JWT_ALGORITHM` | no | Must be `HS256` (default) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Default `30` |
| `CORS_ORIGINS` | no | Comma-separated origins, default `http://localhost:5173`. `*` is rejected. |
| `CREDENTIAL_SIGNING_ISSUER_CODE`, `CREDENTIAL_SIGNING_KEY_ID`, `CREDENTIAL_SIGNING_PRIVATE_KEY` | for issuance | See step 5 |
| `DEMO_USER_PRINCIPAL_KEY`, `DEMO_USER_PASSWORD`, `DEMO_USER_ROLE`, `DEMO_USER_DISPLAY_NAME` | for step 4 | See step 4 |

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

`.env` is ignored by Git. Never commit it.

### 3. Apply migrations

From `backend/` with the virtual environment active:

```bash
alembic upgrade head
alembic current
```

`alembic current` prints `af6e5dad6637 (head)`.

### 4. Create demo users

The application has no sign-up or user administration screen. `scripts/bootstrap_demo_user.py` creates one user with one role each time it runs. It reads the four `DEMO_USER_*` settings, and running it again with the same values changes nothing.

The demonstration needs three users. Set the password once in `.env` (12 characters or more), then run the script three times with a different name and role:

```bash
DEMO_USER_PRINCIPAL_KEY=demo-admin    DEMO_USER_ROLE=ACADEMIC_ADMINISTRATOR DEMO_USER_DISPLAY_NAME="Demo Academic Administrator" python scripts/bootstrap_demo_user.py
DEMO_USER_PRINCIPAL_KEY=demo-platform DEMO_USER_ROLE=PLATFORM_ADMINISTRATOR DEMO_USER_DISPLAY_NAME="Demo Platform Administrator" python scripts/bootstrap_demo_user.py
DEMO_USER_PRINCIPAL_KEY=demo-learner  DEMO_USER_ROLE=LEARNER                DEMO_USER_DISPLAY_NAME="Demo Learner"                python scripts/bootstrap_demo_user.py
```

In PowerShell, set each variable with `$env:DEMO_USER_PRINCIPAL_KEY = "demo-admin"` before running the script.

Each run prints `Bootstrapped user '<name>' with role <ROLE>.` The script has no `--help` option; any argument is ignored and the script runs.

What each role can do:

| Role | Access |
|---|---|
| `ACADEMIC_ADMINISTRATOR` | All record keeping, eligibility, reports, audit; the only role that can issue and revoke credentials |
| `PLATFORM_ADMINISTRATOR` | All record keeping, eligibility, reports, audit; the only role that can register and revoke signing keys |
| `LEARNER` | Own credentials only |
| `INSTRUCTOR`, `SUPPORT_STAFF`, `THIRD_PARTY_VERIFIER` | Can sign in; no route grants them access |

### 5. Generate a signing key pair

Issuance needs an Ed25519 key pair. The private key goes into `backend/.env`; the public key is registered through the API.

```bash
python -c "import base64; from cryptography.hazmat.primitives import serialization as s; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as K; k=K.generate(); print('CREDENTIAL_SIGNING_PRIVATE_KEY='+base64.b64encode(k.private_bytes(s.Encoding.Raw,s.PrivateFormat.Raw,s.NoEncryption())).decode()); print('PUBLIC_KEY_BASE64='+base64.b64encode(k.public_key().public_bytes(s.Encoding.Raw,s.PublicFormat.Raw)).decode())"
```

Add these three lines to `backend/.env`, using the private key that was printed:

```text
CREDENTIAL_SIGNING_ISSUER_CODE=DEMO-ISSUER
CREDENTIAL_SIGNING_KEY_ID=demo-key-1
CREDENTIAL_SIGNING_PRIVATE_KEY=<printed private key>
```

Keep the printed `PUBLIC_KEY_BASE64` value for the demonstration, where the Platform Administrator registers it for issuer `DEMO-ISSUER` as key `demo-key-1`.

Settings are read once when the backend starts. Restart the backend after any change to `.env`. Until the issuer and public key are registered and match the private key, `POST /credentials/issue` returns `503`.

### 6. Start the backend

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check it:

```bash
curl http://localhost:8000/health
```

The response is `{"status":"ok"}`. Interactive API documentation is at <http://localhost:8000/docs>.

### 7. Start the frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
npm ci
npm run dev
```

Open <http://localhost:5173> and sign in as `demo-admin`.

`VITE_API_BASE_URL` in `frontend/.env` is the backend address the browser calls (default `http://localhost:8000/api/v1`). The frontend origin must be listed in the backend's `CORS_ORIGINS`. `npm run build` creates a production build in `frontend/dist`.

## Docker Compose

`docker-compose.yml` defines three services: `db` (PostgreSQL 17, port 5432), `backend` (port 8000) and `frontend` (port 5173).

```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD and a SECRET_KEY of at least 32 bytes.
docker compose up --build -d
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python scripts/bootstrap_demo_user.py
```

- Compose does not apply migrations by itself; the `alembic upgrade head` command is required.
- The bootstrap command reads the `DEMO_USER_*` values from the root `.env`. To create the three demo users, pass different values per run with `-e`, for example `docker compose run --rm -e DEMO_USER_PRINCIPAL_KEY=demo-platform -e DEMO_USER_ROLE=PLATFORM_ADMINISTRATOR backend python scripts/bootstrap_demo_user.py`.
- After changing signing settings in `.env`, recreate the backend with `docker compose up -d backend`.
- `docker compose down` stops the services. Adding `-v` also deletes the database volume.

Docker was not available in the environment where this documentation was last verified. The Compose commands above were checked against `docker-compose.yml` and the two Dockerfiles, but were not run. An earlier Compose run by the project author is recorded in [docs/acceptance-test-report.md](docs/acceptance-test-report.md).

## Run the tests

From `backend/` with the virtual environment active:

```bash
python -m pytest
```

Without a test database, 25 tests run and 97 are skipped. To run all 122, point `API_TEST_DATABASE_URL` at an **empty** PostgreSQL database whose name contains `test`:

```bash
createdb credential_api_test
API_TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/credential_api_test python -m pytest
```

The result is `122 passed` in about 75 seconds. The tests create and drop all tables for every test, so never point this variable at a database that holds data you want to keep. The test fixtures refuse a database that is not empty or is not named for testing.

The frontend has no automated tests. Details: [docs/backend-testing.md](docs/backend-testing.md).

## Seed data

The generator writes synthetic data into a separate database and exports it. No real personal data is used. Run it from `backend/` with the virtual environment active. `/tmp/seed` below stands for any directory outside the repository.

```bash
createdb credential_synthetic
export SYNTHETIC_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/credential_synthetic
export CONFIRM_SYNTHETIC_DATABASE_RESET=YES
export SECRET_KEY=<any value of at least 32 bytes>

python scripts/generate_seed_data.py --profile starter --reset \
  --output-dir /tmp/seed --ground-truth-dir /tmp/seed
python scripts/validate_seed_data.py \
  --manifest /tmp/seed/manifest.json --ground-truth-dir /tmp/seed --report /tmp/seed/validation.json
```

- The database name must contain `synthetic`. `--reset` drops and recreates every table in it.
- `SECRET_KEY` must be exported in the shell for `--reset`; the value in `.env` is not enough.
- Without `--output-dir`, `--ground-truth-dir` and `--report`, the scripts write into the tracked `data/` directory and overwrite the committed reports. Use separate paths unless you intend to replace them.
- The validator prints `passed` with 30 checks for the starter profile.
- `--profile full` produces 839,400 rows (20,000 learners, 1,000 courses, 10,000 credentials, 5,000 verification requests).

Details: [docs/database/seed-data-guide.md](docs/database/seed-data-guide.md). See [Project status](#project-status) for what has and has not been validated on the full dataset.

## Demonstration

[docs/demo-guide.md](docs/demo-guide.md) walks through the complete lifecycle: register an issuer key, create a learner, course and rule, record a completion and a score, issue a credential, verify it, tamper with it, revoke it, and read the audit history. The guide gives each step as an API call and names the screen that does the same in the browser.

## Documentation

| Document | Content |
|---|---|
| [docs/api-documentation.md](docs/api-documentation.md) | All 48 API operations with roles, parameters, examples and errors |
| [docs/database/database-schema.md](docs/database/database-schema.md) | All 23 tables, columns, keys, constraints and indexes |
| [docs/credential-lifecycle.md](docs/credential-lifecycle.md) | The ten lifecycle steps, sequence and state diagrams, failure handling |
| [docs/security.md](docs/security.md) | Security controls, their limits, and work needed before production |
| [docs/backend-testing.md](docs/backend-testing.md) | Test suite contents and how to run it |
| [docs/demo-guide.md](docs/demo-guide.md) | Step-by-step demonstration |
| [docs/known-issues.md](docs/known-issues.md) | Known defects and limitations |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Design decisions and implementation assumptions IA-01 to IA-21 |
| [docs/system-architecture.md](docs/system-architecture.md) | Architecture baseline |
| [docs/original-problem-statement.md](docs/original-problem-statement.md) | Original requirements |
| [docs/database/seed-data-guide.md](docs/database/seed-data-guide.md) | Synthetic data generation |
| [AI_HANDOVER.md](AI_HANDOVER.md), [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) | Handover notes for the next developer or AI assistant |

## Known limitations

The main ones are listed here. The full list is in [docs/known-issues.md](docs/known-issues.md) and [docs/security.md](docs/security.md#limitations).

- No rate limiting on login or public verification, and no request size limit.
- The signing private key is read from an environment variable. There is no key vault or hardware module.
- No user administration, sign-up, password reset, token refresh or logout endpoint.
- Three of the six roles (`INSTRUCTOR`, `SUPPORT_STAFF`, `THIRD_PARTY_VERIFIER`) have no permissions. The role matrix is an implementation assumption (IA-16), not an approved policy.
- Credential replacement and credential expiry are not implemented.
- Audit rows are append-only by application convention. The database does not prevent an administrator with database access from changing them.
- The frontend has no automated tests and no screen for signing keys or portable-payload verification.
- Revoking a signing key makes every credential signed with it `UNVERIFIABLE`.
- After a signing key is rotated, credentials signed with the old key still verify by credential ID, but their exported portable files verify as `UNVERIFIABLE`.

## Project status

| Area | Status |
|---|---|
| Backend lifecycle API | Implemented; 122 automated tests pass |
| Frontend | Implemented; production build succeeds; no automated tests |
| Database migration | One revision; upgrade and `alembic check` are clean |
| Starter seed data | Generated and validated (30 of 30 checks) |
| Full seed dataset validation | **Not complete.** The committed `data/validation/full_dataset_validation_report.json` records `failed` (29 of 30 checks). See [docs/known-issues.md](docs/known-issues.md#seed-data-and-full-dataset-tools). |
| Docker Compose | Defined; not re-run for this documentation |
| Production readiness | Not ready; see [docs/security.md](docs/security.md#before-production-use) |
