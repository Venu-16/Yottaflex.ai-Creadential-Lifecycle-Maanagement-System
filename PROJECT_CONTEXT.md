# Project Context

## Purpose and source of truth

This is a hackathon project to build a working credential lifecycle management system. The full, binding requirements supplied by the user are preserved in [docs/original-problem-statement.md](docs/original-problem-statement.md). If this context, a proposal, or implementation conflicts with those requirements, the original problem statement takes precedence unless the user explicitly approves a change.

The objective is to define credential eligibility, capture course completion and assessment outcomes, evaluate eligibility, issue unique credentials only when requirements pass, create cryptographically verifiable records, support independent third-party verification and authorized revocation, preserve immutable-style audit history, expose decisions and exceptions, and produce measurable, reproducible evaluation outputs.

Success means meeting the original acceptance criteria, including required records and relationships, all four demonstrable anomaly scenarios, the required synthetic-data volumes and fixed seed, separate ground truth, data-quality validation, reproducibility checks, documentation, and a working end-to-end demonstration. The requirements are not reduced to the current scaffold.

## Actors

The original requirements identify five primary actors and one external actor:

1. Learner
2. Instructor
3. Academic Administrator
4. Support Staff
5. Platform Administrator
6. Third-party Verifier

Responsibilities, permissions, and access boundaries have not yet been agreed. See [docs/DECISIONS.md](docs/DECISIONS.md).

## Mandatory entities

The original problem statement requires these entities:

- Learner
- Course
- CredentialRule
- CompletionRecord
- Credential
- Issuer
- VerificationRequest
- Revocation
- AuditEvent

It permits additional supporting entities, including Enrollment, RuleCourse, and EligibilityDecision, when justified by the architecture. Every entity must have a primary key, appropriate foreign keys, documented cardinality, optional relationship definitions, lifecycle states, and effective dates where applicable. These are requirements, not implemented schema. Entity fields, relationships, and lifecycle vocabularies remain undecided.

## Technology stack

The required stack is:

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic, JWT authentication, Pytest
- **Frontend:** React.js, Vite, JavaScript, Tailwind CSS, React Router, Axios, Lucide React
- **Infrastructure:** Docker, Docker Compose, PostgreSQL container

The stack is a user requirement. Any additional library, service, or substitution needs justification and must not silently weaken an acceptance criterion.

## Actual initial architecture

- `backend/app/` contains the FastAPI application, versioned API router, settings, an empty SQLAlchemy declarative base, and PostgreSQL engine/session configuration.
- `backend/migrations/` contains Alembic environment and revision template setup. There are no generated revisions.
- `backend/tests/` contains one health endpoint test and empty unit, integration, and e2e packages.
- `frontend/` contains a Vite React app with a minimal landing page, Tailwind setup, an Axios API client, and placeholder UI directories.
- `data/` contains empty generated, ground-truth, and validation locations; no datasets are present.
- `docs/` contains initial architecture, database-design, data-dictionary, business-rules, API documentation, progress, decisions, and original problem statement documents.
- Root `docker-compose.yml` defines PostgreSQL, backend, and frontend services with PostgreSQL health checking and a named data volume.

This describes the scaffold, not a finalized domain architecture. No database schema, authentication flow, business API, data-generation design, cryptographic method, or audit implementation has been approved.

## Actual repository structure

```text
.
├── .env.example
├── .gitignore
├── AI_HANDOVER.md
├── PROJECT_CONTEXT.md
├── README.md
├── docker-compose.yml
├── backend/
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py
│   │   │       └── endpoints/__init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── exceptions.py
│   │   │   └── security.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── connection.py
│   │   ├── middleware/__init__.py
│   │   ├── models/__init__.py
│   │   ├── repositories/__init__.py
│   │   ├── rules/__init__.py
│   │   ├── schemas/__init__.py
│   │   ├── services/__init__.py
│   │   └── utils/__init__.py
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/.gitkeep
│   ├── scripts/.gitkeep
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── e2e/__init__.py
│       ├── integration/__init__.py
│       └── unit/__init__.py
├── data/
│   ├── README.md
│   ├── generated/.gitkeep
│   ├── ground_truth/.gitkeep
│   └── validation/.gitkeep
├── docs/
│   ├── DECISIONS.md
│   ├── api-documentation.md
│   ├── architecture.md
│   ├── business-rules.md
│   ├── data-dictionary.md
│   ├── database-design.md
│   ├── development-progress.md
│   └── original-problem-statement.md
└── frontend/
    ├── .dockerignore
    ├── .env.example
    ├── Dockerfile
    ├── index.html
    ├── package-lock.json
    ├── package.json
    ├── vite.config.js
    ├── public/.gitkeep
    └── src/
        ├── App.jsx
        ├── index.css
        ├── main.jsx
        ├── assets/.gitkeep
        ├── components/
        │   ├── common/.gitkeep
        │   ├── forms/.gitkeep
        │   └── layout/AppLayout.jsx
        ├── context/.gitkeep
        ├── hooks/.gitkeep
        ├── pages/
        │   ├── audit/.gitkeep
        │   ├── auth/.gitkeep
        │   ├── completions/.gitkeep
        │   ├── courses/.gitkeep
        │   ├── credential-rules/.gitkeep
        │   ├── credentials/.gitkeep
        │   ├── dashboard/.gitkeep
        │   ├── learners/.gitkeep
        │   ├── reports/.gitkeep
        │   ├── revocations/.gitkeep
        │   └── verification/.gitkeep
        ├── routes/.gitkeep
        ├── services/api.js
        └── utils/.gitkeep
```

## Current implementation state

**Phase 1 — Project foundation is complete.** This only means the initial scaffold and basic development setup exist. The product is not feature-complete.

Implemented and verified in the prior initialization task:

- FastAPI application startup, environment-based settings, CORS, basic logging, and `GET /health`.
- PostgreSQL SQLAlchemy engine/session configuration and empty declarative metadata base.
- Alembic environment setup; offline SQL generation produced an empty migration script.
- One passing backend health test.
- Minimal React landing page, Vite/Tailwind configuration, and Axios client configuration.
- Docker Compose configuration for PostgreSQL, backend, and frontend.
- Initial project documentation and environment examples.

Not implemented: login/JWT flows, roles/permissions, domain models or tables, generated migrations, business endpoints, credential lifecycle logic, synthetic data, anomaly fixtures, data validators, ground truth, or reproducibility tooling.

## Verified initialization results

The following checks were run during initial setup:

- `python -m pytest -q` in `backend/`: **1 passed** (one warning noted below).
- Python `compileall` for backend app, migrations, and tests: passed.
- `npm install` in `frontend/`: completed; npm reported **0 vulnerabilities**.
- `npm run build` in `frontend/`: passed.
- Local FastAPI `GET /health`: returned `{"status":"ok"}`.
- Local Vite frontend: returned HTTP 200 and served the expected page.
- `alembic upgrade --sql head`: generated an empty SQL migration script, confirming configuration only.
- `docker compose --env-file .env.example config --quiet`: passed.
- Isolated `docker compose up --build`: PostgreSQL health check passed; backend health returned `ok`; frontend returned HTTP 200. The test project and its named volume were removed afterward.

These are initialization checks, not tests of business workflows or database schema.

## Known warnings and limitations

- Pytest emitted a non-blocking Starlette deprecation warning: using `httpx` with `starlette.testclient` is deprecated and suggests `httpx2`. The health test still passed; no dependency change has been approved or made to address it.
- The scaffold has no real authentication, schema, product API, or domain behavior.
- `GET /health` checks application-process responsiveness only; it does not check database connectivity.
- Alembic has no revisions and the metadata has no domain tables.
- No local `.env` values are committed. Copy the relevant `.env.example` and supply local secrets before running the stack.
- Initial setup used Python 3.13.2, Node.js 22.12.0, npm 11.0.0, and Docker Compose 5.0.0-desktop.1. Other environments may differ.
- Git reported no commits on `main` and no available `origin/main`; scaffold files were untracked at inspection. Do not assume changes are committed.
- `AI_HANDOVER.md`, `docs/DECISIONS.md`, and `docs/original-problem-statement.md` were absent at first handover inspection; this documentation task creates them.

## Requirements, decisions, and unresolved questions

- **Original requirements:** User-mandated requirements preserved in [docs/original-problem-statement.md](docs/original-problem-statement.md). These are binding, not proposals.
- **Proposed architecture:** Any suggested design choices recorded as proposals in [docs/DECISIONS.md](docs/DECISIONS.md). They are not approved unless the user approves them.
- **Approved decisions:** No additional domain or architecture decision has been approved in the available project record. The required technology stack, entity list, data volumes, seed, anomaly scenarios, and acceptance criteria remain requirements.
- **Unresolved decisions:** Authentication and actor permissions; entity relationships and lifecycle states; rule representation and evaluation semantics; cryptographic method, key custody and verifier trust model; revocation semantics; audit immutability guarantees; data formats and generation strategy; exact data validation and reproducibility manifest formats. Clarify material business/security choices with the user before committing to them.

## Development roadmap

The authoritative 11-phase checklist and phase exit conditions are in [docs/development-progress.md](docs/development-progress.md). Phase 1 is the only completed phase; Phases 2–11 remain pending. The roadmap must continue to account for every original acceptance criterion, including synthetic-data generation and reproducibility.

## Continuation instructions

Read [AI_HANDOVER.md](AI_HANDOVER.md), this file, [docs/DECISIONS.md](docs/DECISIONS.md), [docs/development-progress.md](docs/development-progress.md), and [docs/original-problem-statement.md](docs/original-problem-statement.md) before implementation. Preserve existing working code, inspect the current repository and status, work incrementally, do not repeat Phase 1, and do not implement a future phase prematurely. Ask the user when unresolved business or security requirements materially affect design. Update progress and handover documentation after completing a task. Do not weaken the original requirements without explicit approval and a documented trade-off.
