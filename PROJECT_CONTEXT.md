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

## Actual architecture and implementation

- The modular-monolith architecture baseline is approved by the user's 2026-11-11 direction; conservative business defaults are separately labeled implementation assumptions in `docs/DECISIONS.md`.
- `backend/app/` contains the FastAPI application, versioned API router, settings, SQLAlchemy PostgreSQL engine/session, and 23 MVP domain tables in `models/domain.py`.
- `backend/migrations/` contains Alembic revision `af6e5dad6637_create_credential_domain_schema.py`.
- `backend/scripts/` contains deterministic seed generation, validation, and reproducibility utilities.
- `backend/tests/` contains the health endpoint test and focused schema/data-generator tests; integration and e2e folders remain placeholders.
- `frontend/` contains a Vite React app with a minimal landing page, Tailwind setup, an Axios API client, and placeholder UI directories.
- `data/` contains the full synthetic export, separate ground truth/anomaly fixtures, validation results, and reproducibility report. Two clean full-profile generations matched.
- `docs/` contains initial architecture, database-design, data-dictionary, business-rules, API documentation, progress, decisions, and original problem statement documents.
- Root `docker-compose.yml` defines PostgreSQL, backend, and frontend services with PostgreSQL health checking and a named data volume.

The architecture baseline is approved; business services, endpoints, authentication behavior, and production signing-key custody remain unimplemented. Seed data and test-only signing keys are implemented.

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
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── domain.py
│   │   ├── repositories/__init__.py
│   │   ├── rules/__init__.py
│   │   ├── schemas/__init__.py
│   │   ├── services/__init__.py
│   │   └── utils/__init__.py
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── af6e5dad6637_create_credential_domain_schema.py
│   ├── scripts/
│   │   ├── check_reproducibility.py
│   │   ├── generate_seed_data.py
│   │   ├── seed_data_common.py
│   │   └── validate_seed_data.py
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── e2e/__init__.py
│       ├── integration/__init__.py
│       └── unit/
│           ├── test_domain_schema.py
│           └── test_seed_data.py
├── data/
│   ├── README.md
│   ├── generated/ (seed_data.jsonl.gz, manifest.json, source_manifest.json)
│   ├── ground_truth/ (ground_truth.csv, ground_truth.json, anomaly_fixtures.json)
│   └── validation/ (validation_summary.json, reproducibility_summary.json)
├── docs/
│   ├── DECISIONS.md
│   ├── api-documentation.md
│   ├── architecture.md
│   ├── business-rules.md
│   ├── database/
│   │   ├── data-dictionary.md
│   │   ├── entity-catalogue.md
│   │   └── relationship-specification.md
│   ├── data-dictionary.md
│   ├── database-design.md
│   ├── development-progress.md
│   ├── original-problem-statement.md
│   └── system-architecture.md
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

Implemented and verified:

- FastAPI application startup, environment-based settings, CORS, basic logging, and `GET /health`.
- PostgreSQL SQLAlchemy engine/session configuration, 23-table domain metadata, and Alembic schema migration.
- Eight backend tests (health, schema, and deterministic data-generator tests).
- Minimal React landing page, Vite/Tailwind configuration, and Axios client configuration.
- Docker Compose configuration for PostgreSQL, backend, and frontend.
- Initial project documentation and environment examples.
- Fixed-seed, parameterized synthetic data generator; full profile meets required entity volumes, exports separate ground truth and anomaly fixtures, and validates against a disposable PostgreSQL database.

Not implemented: login/JWT flows, enforced roles/permissions, business endpoints/services, credential lifecycle operations, and production signing-key custody. User/Role persistence tables exist, but no authentication or authorization behavior is wired.

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
- Alembic has initial revision `af6e5dad6637`; 23 MVP tables are defined. The migration has not been applied to a persistent project database.
- No local `.env` values are committed. Copy the relevant `.env.example` and supply local secrets before running the stack.
- Initial setup used Python 3.13.2, Node.js 22.12.0, npm 11.0.0, and Docker Compose 5.0.0-desktop.1. Other environments may differ.
- The scaffold and initial documentation baseline are committed on `main` as `f0b335b22fe9396f5affe5bebca3c76276afce0b`. The configured `origin/main` is unavailable. Check current Git status before assuming subsequent documentation or implementation work is committed.
- `AI_HANDOVER.md`, `docs/DECISIONS.md`, and `docs/original-problem-statement.md` were absent at first handover inspection; this documentation task creates them.

## Requirements, decisions, and unresolved questions

- **Original requirements:** User-mandated requirements preserved in [docs/original-problem-statement.md](docs/original-problem-statement.md). These are binding, not proposals.
- **Approved baseline:** The modular-monolith architecture and original requirements are approved for implementation by the user's 2026-11-11 instruction.
- **Implementation assumptions:** Time-boxed operational defaults are recorded as IA-01–IA-15 in [docs/DECISIONS.md](docs/DECISIONS.md). They are not user-approved business policy.
- **Unresolved decisions:** Authentication and actor permissions; entity relationships and lifecycle states; production rule/evaluation semantics; production key custody and verifier trust model; revocation semantics; and audit immutability guarantees. Synthetic-data fixture parameters are documented separately and are not business-policy decisions.

## Development roadmap

The authoritative 11-phase checklist and phase exit conditions are in [docs/development-progress.md](docs/development-progress.md). Roadmap Phases 1, 2, and 10 are complete; Phase 4 remains in progress. The current task's Phase 5 seed-data increment maps to completed roadmap Phase 10. Roadmap Phase 5 (eligibility-rule definition) remains pending.

## Phase 2 architecture proposal

[docs/system-architecture.md](docs/system-architecture.md) documents the approved modular-monolith baseline, responsibilities and dependencies, workflows, lifecycle, security guidance, representative versioned REST API groups, anomaly controls, audit/traceability, Mermaid diagrams, and risks/trade-offs. It does not imply those workflows are implemented.

Business/security choices remain unresolved except where an implementation assumption IA-01–IA-14 is recorded. Do not present an assumption as user approval or grant any actor access by inference.

## Phase 4 database design and implementation

[docs/database/entity-catalogue.md](docs/database/entity-catalogue.md), [docs/database/data-dictionary.md](docs/database/data-dictionary.md), and [docs/database/relationship-specification.md](docs/database/relationship-specification.md) contain the logical catalogue, PostgreSQL data dictionary, relationships, and ER diagram. The MVP schema implements 23 tables with `CredentialAward` uniqueness, replacement lineage, evidence snapshots, and issuer/key history. Revision `af6e5dad6637` passed disposable PostgreSQL upgrade/downgrade/re-upgrade and metadata-sync checks. Phase 4 remains in progress; no services/API or authentication behavior is implemented. LRN/CRD/VER formats are preserved and allocation assumptions are recorded.

## Synthetic seed data

The full profile contains 20,000 learners, 1,000 courses, 100 rules, 10 issuers, 10,000 credentials, and 5,000 verification requests, plus dependent lifecycle records. `data/generated/manifest.json` records actual entity counts and checksums; `data/ground_truth/` holds expected outcomes and isolated anomalies. Full PostgreSQL validation passed, including digest/signature checks and a rolled-back duplicate-ID constraint probe. Two clean full runs matched on manifests and validation results; see `data/validation/reproducibility_summary.json`. Large generated payload files are locally available but excluded from Git because they can be recreated deterministically. Follow [docs/database/seed-data-guide.md](docs/database/seed-data-guide.md) for guarded generation and reproducibility commands.

## Continuation instructions

Read [AI_HANDOVER.md](AI_HANDOVER.md), this file, [docs/DECISIONS.md](docs/DECISIONS.md), [docs/development-progress.md](docs/development-progress.md), and [docs/original-problem-statement.md](docs/original-problem-statement.md) before implementation. Preserve existing work, inspect Git status, proceed using documented assumptions, keep permissions deny-by-default, and do not weaken original requirements. Update progress and handover after each completed task; ask only when the choice is fundamental or creates irreversible data/security risk.
