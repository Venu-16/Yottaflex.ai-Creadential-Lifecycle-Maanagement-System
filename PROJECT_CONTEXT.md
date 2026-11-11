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
- `backend/app/` contains the FastAPI application, versioned auth/business routes, JWT/RBAC dependencies, SQLAlchemy session dependency, 23 MVP domain tables, request/response schemas, and service-layer lifecycle operations.
- `backend/migrations/` contains Alembic revision `af6e5dad6637_create_credential_domain_schema.py`.
- `backend/scripts/` contains deterministic seed generation, validation, and reproducibility utilities.
- `backend/tests/` contains health, schema, synthetic-data, and PostgreSQL API integration tests. Integration tests require a dedicated empty `API_TEST_DATABASE_URL` with `test` in its database name.
- `frontend/` contains the Vite/React/Tailwind dashboard, React Router protected routes, bearer-token Axios client, role-aware navigation, workflow pages, and shared UI components. `GET /auth/me` returns active role codes for UI presentation; backend RBAC remains authoritative.
- `data/` contains the full synthetic export, separate ground truth/anomaly fixtures, validation results, and reproducibility report. Two clean full-profile generations matched.
- `docs/` contains initial architecture, database-design, data-dictionary, business-rules, API documentation, progress, decisions, and original problem statement documents.
- Root `docker-compose.yml` defines PostgreSQL, backend, and frontend services with PostgreSQL health checking and a named data volume.

The architecture baseline is approved. A first backend API/workflow increment is implemented and tested; role permissions, key custody, and other open semantics remain implementation assumptions, not approved policy. Synthetic seed keys are test-only and are not used by API issuance.

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
│   │       │   └── endpoints/
│   │       │       ├── auth.py
│   │       │       └── business.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   ├── errors.py
│   │   │   ├── exceptions.py
│   │   │   ├── roles.py
│   │   │   └── security.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── connection.py
│   │   │   └── dependencies.py
│   │   ├── middleware/__init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── domain.py
│   │   ├── repositories/__init__.py
│   │   ├── rules/__init__.py
│   │   ├── schemas/api.py
│   │   ├── services/
│   │   │   ├── audit.py
│   │   │   ├── credentials.py
│   │   │   ├── eligibility.py
│   │   │   └── management.py
│   │   └── utils/__init__.py
│   ├── migrations/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── af6e5dad6637_create_credential_domain_schema.py
│   ├── scripts/
│   │   ├── bootstrap_demo_user.py
│   │   ├── check_reproducibility.py
│   │   ├── generate_seed_data.py
│   │   ├── seed_data_common.py
│   │   └── validate_seed_data.py
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── e2e/__init__.py
│       ├── integration/test_api_workflows.py
│       └── unit/
│           ├── test_domain_schema.py
│           ├── test_seed_data.py
│           └── test_security_and_crypto.py
├── data/
│   ├── README.md
│   ├── generated/ (seed_data.jsonl.gz, manifest.json, source_manifest.json)
│   ├── ground_truth/ (ground_truth.csv, ground_truth.json, anomaly_fixtures.json)
│   └── validation/ (validation_summary.json, reproducibility_summary.json)
├── docs/
│   ├── DECISIONS.md
│   ├── api-documentation.md
│   ├── backend-testing.md
│   ├── acceptance-test-report.md
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
        │   ├── common/{ProtectedRoute.jsx, ui.jsx}
        │   └── layout/AppLayout.jsx
        ├── context/AuthContext.jsx
        ├── hooks/useResource.js
        ├── pages/
        │   ├── Workspace.jsx
        │   ├── auth/Login.jsx
        │   ├── dashboard/Dashboard.jsx
        │   └── verification/Verification.jsx
        └── services/api.js
```

## Current implementation state

**Current implementation is partial; no Phase 3–9 checklist is marked complete and Phase 11 remains in progress.** The user-requested Phase 8 final acceptance pass found strong evidence for the MVP lifecycle but also documented open requirements and production risks in [docs/acceptance-test-report.md](docs/acceptance-test-report.md).

Implemented and verified:

- FastAPI application startup, environment-based settings, CORS, basic logging, and `GET /health`.
- PostgreSQL SQLAlchemy engine/session configuration, 23-table domain metadata, and Alembic schema migration.
- Backend tests for health, schema, deterministic seed generation, authentication/role denial, and a PostgreSQL credential lifecycle workflow.
- React/Vite/Tailwind workspace with login/logout, session restoration/expiry handling, protected routes, role-aware navigation, public verification, operational data entry, eligibility evaluation, credential issuance/revocation, audit and reports.
- Docker Compose configuration for PostgreSQL, backend, and frontend.
- Initial project documentation and environment examples.
- Fixed-seed, parameterized synthetic data generator; full profile meets required entity volumes, exports separate ground truth and anomaly fixtures, and validates against a disposable PostgreSQL database.
- Authenticated APIs for master data, versioned rules, enrollment/completion/assessment, eligibility, issuance, public verification, revocation, audit, and basic reports.

The Phase 9 backend suite passed 30/30 against a separate temporary PostgreSQL 17 test database (9 API integration, 13 authentication/cryptography unit, 3 schema, 4 seed-data, and 1 health test). New integration coverage checks anonymous 401s, disallowed-role/learner 403s, linked-learner credential isolation, absence of user lookup/update routes, and public verification disclosure. Python compileall, Alembic upgrade/check, OpenAPI generation (34 paths), Compose configuration, and the frontend production build passed. A fresh Compose project ran the documented migration and demo-user bootstrap commands twice, passed backend/frontend HTTP checks and login, and verified the Academic Administrator role assignment in PostgreSQL before removing its temporary volume. The earlier browser workflow exercised learner/course/rule and completion/assessment management, ineligible rejection, eligible issuance, public VALID → REVOKED verification, audit/report views, protected navigation, login/logout, and mobile navigation. An initial fresh bootstrap exposed a missing `scripts/` Docker image copy; it was fixed and verified. These checks do not constitute a complete original-criteria acceptance review or production sign-off.

Not implemented or incomplete: production-approved role matrix and any additional object scopes, account and role administration beyond a local bootstrap script, production key custody, issuance replacement, rate limiting/body-size limits, trusted timestamps, portable-verification UI, distribution-quality benchmarking, and complete original-criteria acceptance coverage. Aggregate learner/course dashboard counts are not exposed by the API and are not fabricated. The application is not production-ready.

## Verified initialization results

The following checks were run during initial setup (historical scaffold checks, not current workflow coverage):

- `python -m pytest -q` in `backend/`: **1 passed** (one warning noted below).
- Python `compileall` for backend app, migrations, and tests: passed.
- `npm install` in `frontend/`: completed; npm reported **0 vulnerabilities**.
- `npm run build` in `frontend/`: passed.
- Local FastAPI `GET /health`: returned `{"status":"ok"}`.
- Local Vite frontend: returned HTTP 200 and served the expected page.
- `alembic upgrade --sql head`: generated an empty SQL migration script, confirming configuration only.
- `docker compose --env-file .env.example config --quiet`: passed.
- Isolated `docker compose up --build`: PostgreSQL health check passed; backend health returned `ok`; frontend returned HTTP 200. The test project and its named volume were removed afterward.

The latest acceptance evidence and exact temporary database details are in [docs/acceptance-test-report.md](docs/acceptance-test-report.md) and [AI_HANDOVER.md](AI_HANDOVER.md).

## Known warnings and limitations

- Initial pytest runs emitted a non-blocking Starlette deprecation warning about `httpx` with `starlette.testclient`; no dependency change was made.
- API auth uses local PBKDF2-hashed passwords and HS256 bearer tokens; temporary role mapping IA-16 remains unapproved.
- `GET /health` checks application-process responsiveness only; it does not check database connectivity.
- Alembic has initial revision `af6e5dad6637`; 23 MVP tables are defined. Migrations are tested only against disposable databases, not a persistent project database.
- No local `.env` values are committed. Copy the relevant `.env.example` and supply local secrets before running the stack.
- Initial setup used Python 3.13.2, Node.js 22.12.0, npm 11.0.0, and Docker Compose 5.0.0-desktop.1. Other environments may differ.
- The scaffold and initial documentation baseline are committed on `main` as `f0b335b22fe9396f5affe5bebca3c76276afce0b`. The configured `origin/main` is unavailable. Check current Git status before assuming subsequent documentation or implementation work is committed.
- `AI_HANDOVER.md`, `docs/DECISIONS.md`, and `docs/original-problem-statement.md` were created after the initial scaffold.

## Requirements, decisions, and unresolved questions

- **Original requirements:** User-mandated requirements preserved in [docs/original-problem-statement.md](docs/original-problem-statement.md). These are binding, not proposals.
- **Approved baseline:** The modular-monolith architecture and original requirements are approved for implementation by the user's 2026-11-11 instruction.
- **Implementation assumptions:** Time-boxed operational defaults are recorded as IA-01–IA-21 in [docs/DECISIONS.md](docs/DECISIONS.md). They are not user-approved business policy.
- **Unresolved decisions:** Authentication and actor permissions; entity relationships and lifecycle states; production rule/evaluation semantics; production key custody and verifier trust model; revocation semantics; and audit immutability guarantees. Synthetic-data fixture parameters are documented separately and are not business-policy decisions.

## Development roadmap

The authoritative 11-phase checklist and phase exit conditions are in [docs/development-progress.md](docs/development-progress.md). Roadmap Phases 1, 2, and 10 are complete; Phases 3–9 and 11 remain unchecked. The current product task is Phase 11 acceptance and hardening; the user-requested final acceptance phase has evidence but is not complete.

## Phase 2 architecture proposal

[docs/system-architecture.md](docs/system-architecture.md) documents the approved modular-monolith baseline, responsibilities and dependencies, workflows, lifecycle, security guidance, representative versioned REST API groups, anomaly controls, audit/traceability, Mermaid diagrams, and risks/trade-offs. It does not imply those workflows are implemented.

Business/security choices remain unresolved except where an implementation assumption IA-01–IA-21 is recorded. Do not present an assumption as user approval or grant any actor access by inference.

## Phase 4 database design and implementation

[docs/database/entity-catalogue.md](docs/database/entity-catalogue.md), [docs/database/data-dictionary.md](docs/database/data-dictionary.md), and [docs/database/relationship-specification.md](docs/database/relationship-specification.md) contain the logical catalogue, PostgreSQL data dictionary, relationships, and ER diagram. The MVP schema implements 23 tables with `CredentialAward` uniqueness, replacement lineage, evidence snapshots, and issuer/key history. Revision `af6e5dad6637` passed disposable PostgreSQL upgrade/downgrade/re-upgrade and metadata-sync checks. Phase 4 remains in progress; APIs now use the existing schema, with no migration added for this implementation increment. LRN/CRD/VER formats are preserved.

## Backend API and lifecycle implementation

The versioned API exposes auth/RBAC, learner/course/issuer/rule management,
enrollment/completion/assessment records, eligibility evaluation, idempotent
credential issuance, credential-ID and portable verification, revocation,
read-only audit, and basic reports. Services reside in `backend/app/services/`;
API request/response schemas are in `backend/app/schemas/api.py`. Issuance
requires an externally configured Ed25519 private key matching an issuer
public-key registry entry. Verification fails closed for unavailable or
untrusted keys and unknown portable-payload lifecycle state. Use
[docs/api-documentation.md](docs/api-documentation.md) for routes and setup.
The end-to-end flow has PostgreSQL integration coverage, but Phases 3–9 are
not complete until all listed checks, policy reviews, and security gaps close.

## Synthetic seed data

The full profile contains 20,000 learners, 1,000 courses, 100 rules, 10 issuers, 10,000 credentials, and 5,000 verification requests, plus dependent lifecycle records. `data/generated/manifest.json` records actual entity counts and checksums; `data/ground_truth/` holds expected outcomes and isolated anomalies. Full PostgreSQL validation passed, including digest/signature checks and a rolled-back duplicate-ID constraint probe. Two clean full runs matched on manifests and validation results; see `data/validation/reproducibility_summary.json`. Large generated payload files are locally available but excluded from Git because they can be recreated deterministically. Follow [docs/database/seed-data-guide.md](docs/database/seed-data-guide.md) for guarded generation and reproducibility commands.

## Continuation instructions

Read [AI_HANDOVER.md](AI_HANDOVER.md), this file, [docs/DECISIONS.md](docs/DECISIONS.md), [docs/development-progress.md](docs/development-progress.md), and [docs/original-problem-statement.md](docs/original-problem-statement.md) before implementation. Preserve existing work, inspect Git status, proceed using documented assumptions, keep permissions deny-by-default, and do not weaken original requirements. Update progress and handover after each completed task; ask only when the choice is fundamental or creates irreversible data/security risk.
