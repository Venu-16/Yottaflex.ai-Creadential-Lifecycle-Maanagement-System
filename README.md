# Credential Lifecycle Management System

A hackathon project for managing learners, courses, eligibility rules, course completion, credentials, verification, revocation, audit history, and reporting. The repository has an initial 23-table SQLAlchemy schema and Alembic migration; domain services and business APIs are still in progress.

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
5. Open the frontend at <http://localhost:5173> and the health check at <http://localhost:8000/health>.
6. Stop the services with `docker compose down`. Add `-v` only if you intend to delete the local PostgreSQL data volume.

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

Set `DATABASE_URL` in `backend/.env` to a running PostgreSQL instance and replace `SECRET_KEY`. Then run:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

The health endpoint is available at <http://localhost:8000/health>. Run backend tests from `backend/` with `pytest`. The schema is defined in `app/models/domain.py`; the initial migration is under `migrations/versions/`.

## Run frontend independently

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The Vite development server is available at <http://localhost:5173>. `VITE_API_BASE_URL` configures the API client base URL.

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
