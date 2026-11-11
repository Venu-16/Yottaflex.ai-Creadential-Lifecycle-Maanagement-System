# Credential Lifecycle Management System

A hackathon project scaffold for managing learners, courses, eligibility rules, course completion, credentials, verification, revocation, audit history, and reporting. This repository currently contains initialization code only; domain workflows and database tables have not been implemented.

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
3. Run `docker compose up --build`.
4. Open the frontend at <http://localhost:5173> and the health check at <http://localhost:8000/health>.
5. Stop the services with `docker compose down`. Add `-v` only if you intend to delete the local PostgreSQL data volume.

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
uvicorn app.main:app --reload
```

The health endpoint is available at <http://localhost:8000/health>. Run backend tests from `backend/` with `pytest`.

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
- `data/` — reserved locations for future project data
- `docs/` — architecture and planning documentation
- `docker-compose.yml` — local PostgreSQL, backend, and frontend services

See [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md) for scope and constraints, and [docs/development-progress.md](./docs/development-progress.md) for the phase checklist.
