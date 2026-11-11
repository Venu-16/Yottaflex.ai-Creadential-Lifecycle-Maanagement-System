# Credential Lifecycle Management System

A hackathon project for managing learners, courses, eligibility rules, course completion, credentials, verification, revocation, audit history, and reporting. The repository includes an initial 23-table SQLAlchemy schema, Alembic migration, and a first working backend lifecycle API. Product authorization and security semantics remain implementation assumptions pending review.

## Technology stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Pydantic Settings, JWT dependency, Pytest
- **Frontend:** React, Vite, JavaScript, Tailwind CSS, React Router, Axios, Lucide React
- **Infrastructure:** Docker, Docker Compose, PostgreSQL

## Prerequisites

- Python 3.11 or newer
- Node.js 20.19+ or 22.12+
- npm
- Docker with the Docker Compose plugin (for the containerized setup)

## Start with Docker Compose

From the repository root:

1. Copy `.env.example` to `.env`.
2. Replace `POSTGRES_PASSWORD` and `SECRET_KEY` with local values. Do not commit `.env`.
3. Run `docker compose up --build -d`.
4. Apply the database schema with `docker compose run --rm backend alembic upgrade head`.
5. To provision a local demonstration account, set the `DEMO_USER_*` values in `.env` and run `docker compose run --rm backend python scripts/bootstrap_demo_user.py`. Use a local-only password and do not commit `.env`.
6. Open the frontend at <http://localhost:5173> and the health check at <http://localhost:8000/health>.
7. Stop the services with `docker compose down`. Add `-v` only if you intend to delete the local PostgreSQL data volume.

Compose starts PostgreSQL first and waits for its health check before starting the backend. The backend and frontend are reachable by the service names `backend` and `frontend` on the Compose network.

## Run backend independently

In a terminal:

```powershell
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `backend/.env` to a running PostgreSQL instance and replace `SECRET_KEY` with a random value of at least 32 bytes. Then run:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

The health endpoint is available at <http://localhost:8000/health>; Swagger UI is at <http://localhost:8000/docs>. Run the backend suite against a dedicated disposable PostgreSQL test database; see [docs/backend-testing.md](./docs/backend-testing.md). The schema is defined in `app/models/domain.py`; the initial migration is under `migrations/versions/`.

### Bootstrap local demo users

The API intentionally has no public user or role administration route. In
`backend/`, provide a local demo identity and role through environment
variables, then run the bootstrap command. It reads no default password and
never prints or returns the password/hash:

```powershell
$env:DEMO_USER_PRINCIPAL_KEY = "admin@example.test"
$secure = Read-Host "Local demo password (12+ characters)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:DEMO_USER_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    $env:DEMO_USER_ROLE = "ACADEMIC_ADMINISTRATOR"
    python scripts\bootstrap_demo_user.py
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    Remove-Item Env:DEMO_USER_PASSWORD, Env:DEMO_USER_ROLE, Env:DEMO_USER_PRINCIPAL_KEY -ErrorAction SilentlyContinue
}
```

Use a separate `PLATFORM_ADMINISTRATOR` account to register issuer keys and
manage signing trust. The Academic Administrator account is the only role
allowed to issue/revoke. Learners can access only their linked credential list;
unapproved Instructor/Support Staff permissions are denied. These restrictive
role assignments are temporary implementation assumptions, not an approved
authorization matrix.

### Configure an issuer signing key

Issuance fails closed until an active issuer and corresponding Ed25519 public
key are registered and the matching base64-encoded 32-byte private seed is
provided in `CREDENTIAL_SIGNING_PRIVATE_KEY`. Set
`CREDENTIAL_SIGNING_ISSUER_CODE` and `CREDENTIAL_SIGNING_KEY_ID` to match the
registered records. Keep private material only in an ignored local secret
environment; never commit it or use the deterministic synthetic test keys.
The key registration endpoint accepts public key material only. See
[docs/api-documentation.md](./docs/api-documentation.md) for the routes,
verification trust behavior, outcomes, and remaining limitations.

## Run frontend independently

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The Vite development server is available at <http://localhost:5173>. `VITE_API_BASE_URL` configures the API client base URL.

The frontend provides login/session handling, a responsive role-aware academic
workspace, learner and course catalogues, versioned eligibility rules,
enrollment/completion/assessment entry, eligibility evaluation, credential
issuance and revocation, public credential verification, audit history, and
reports. Navigation uses the assigned roles returned by `GET /api/v1/auth/me`;
the API remains the authorization boundary. Public verification is available
without an account.

Dashboard figures and reports are read from reporting endpoints. The API does
not currently expose aggregate learner or course totals, so the dashboard does
not fabricate them. Replacement credential issuance, user/role administration,
instructor object scopes, and production signing-key custody are not implemented.

For frontend changes, run `npm run build` in `frontend/`. The backend regression
suite is `python -m pytest -q` in `backend/`; PostgreSQL integration cases
require a separate empty disposable database via `API_TEST_DATABASE_URL` and
must not use the synthetic dataset.

## Project layout

- `backend/` — FastAPI application, database and migration setup, tests, and scripts
- `frontend/` — Vite application and UI/service module boundaries
- `data/` — deterministic synthetic exports, separate ground truth, and validation reports
- `docs/` — architecture and planning documentation
- `docker-compose.yml` — local PostgreSQL, backend, and frontend services

See [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md) for scope and constraints, and [docs/development-progress.md](./docs/development-progress.md) for the phase checklist.

## Synthetic seed data

The deterministic PostgreSQL seed generator, validation commands, output
formats, reset safeguards, and two-run reproducibility procedure are documented
in [docs/database/seed-data-guide.md](./docs/database/seed-data-guide.md).

## Backend API scope

Implemented API groups include authentication/RBAC, learner and course
management, issuers and public signing-key registry, versioned credential
rules, enrollments, completions, assessment attempts, eligibility evaluation,
credential issuance, both verification modes, revocation, read-only audit, and
basic reports. Business workflows are covered by PostgreSQL integration tests.
The backend is not production-ready: the actor matrix, replacement workflow,
rate limiting, external trusted timestamps, and production key custody remain
open. See [docs/api-documentation.md](./docs/api-documentation.md) and
[docs/DECISIONS.md](./docs/DECISIONS.md).
