# AI Coding Assistant Handover

## Read first

Before changing code, read these project documents in order:

1. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — actual architecture, repository tree, current state, and verified setup.
2. This file — continuation rules and handover status.
3. [docs/development-progress.md](docs/development-progress.md) — authoritative 11-phase roadmap and acceptance checks.
4. [docs/DECISIONS.md](docs/DECISIONS.md) — binding requirements versus proposals, approvals, and unresolved questions.
5. [docs/original-problem-statement.md](docs/original-problem-statement.md) — full, binding hackathon requirements.

The original problem statement is the source of truth. Do not remove, weaken, silently reinterpret, or omit a requirement. A proposed simplification that changes an acceptance criterion requires explicit user approval and a documented trade-off.

## Handover snapshot

- **Last completed product phase:** Phase 1 — project foundation and initialization.
- **Current product phase:** Phase 2 — identity, authentication, and authorization; not started.
- **Current task:** The documentation/handover system has been completed and reconciled with the repository. This documentation task does not constitute a product feature or advance the product phase.
- **Implementation state:** Scaffold only. No application behavior beyond health check and static landing page; no authentication, domain models, tables, generated migrations, credential lifecycle functionality, or synthetic data.
- **Next step:** Do not start implementation without the user's approval. Once approved, resolve the relevant open questions in `docs/DECISIONS.md`, starting with actor permissions and identity/access requirements, then proceed incrementally through the roadmap.

## Repository facts

- Backend: FastAPI under `backend/app/`; settings in `app/core/config.py`; database engine/session in `app/database/connection.py`; empty SQLAlchemy base in `app/database/base.py`; only `GET /health` is registered.
- Alembic uses `backend/migrations/`; no revision exists. The offline SQL check generated no DDL.
- Backend tests: one `backend/tests/test_health.py`; unit, integration, and e2e folders are placeholders.
- Frontend: Vite React app in `frontend/src/`; `App.jsx` is a minimal status page; `services/api.js` is only an Axios configuration.
- Data: `data/generated/`, `data/ground_truth/`, and `data/validation/` are empty placeholders.
- Docker Compose defines `db`, `backend`, and `frontend`, uses a PostgreSQL health check and named volume. It has been built and tested locally.
- Existing setup docs are in `README.md`; detailed context and actual tree are in `PROJECT_CONTEXT.md`.
- The initial repository inspection showed no commits on `main`, no available `origin/main`, and all scaffold files untracked. Check git status before editing; do not assume there are no subsequent user changes.

## Verified baseline and caveats

During initialization: backend health test passed (1 test); Python compile check passed; frontend dependency install and production build passed; local FastAPI returned `{"status":"ok"}`; local frontend returned HTTP 200; Compose config validated; Alembic offline SQL rendered an empty script; an isolated Compose run reported PostgreSQL healthy and both application services responded. Test containers, volume, and temporary environment file were cleaned up.

Known warning: pytest passed with a non-blocking Starlette deprecation warning about `httpx` use with `starlette.testclient` and a suggestion to use `httpx2`. Do not change dependencies without evaluating compatibility and need.

The prior environment used Python 3.13.2, Node 22.12.0, npm 11.0.0, and Docker Compose 5.0.0-desktop.1. `.env` files and secrets are intentionally not committed. `GET /health` does not test the database.

## Requirements that must remain visible

- Preserve all six actors, all nine mandatory entities, their required keys/relationship/lifecycle documentation, and any justified supporting entities.
- Preserve required volumes (20,000 learners; 1,000 courses; 10,000 credentials; 5,000 verification requests), seed `20261022`, parameterized generation, valid-baseline-first workflow, and labelled edge cases.
- Demonstrate all four controlled anomalies: issued before completion, duplicate credential ID, revoked credential reported active, and undetected altered payload hash.
- Keep ground-truth labels separate from application inputs/decision logic.
- Validate identifiers/relationships, enumerations, dates, arithmetic, lifecycle transitions, duplicates, and cross-entity consistency.
- Reproduce row counts, IDs, checksums, labels, and validation results across two runs with the same seed.
- Deliver seed data, schema, data dictionary, generator command, fixed-seed documentation, source manifest, validation summary, and reproducibility report.
- Make eligible issuance, ineligible rejection, uniqueness, independent authenticity verification, revoked-status behavior, traceable operations, anomaly demonstration, required volumes, and reproducibility demonstrable end to end.

The complete text and remaining original criteria are in [docs/original-problem-statement.md](docs/original-problem-statement.md).

## Working rules for the next assistant

1. Inspect current `git status` and relevant files before editing; preserve user changes.
2. Work one task/phase at a time. Do not repeat Phase 1, build future phases prematurely, or alter unrelated code.
3. Check `docs/DECISIONS.md` before settling any business, identity, security, lifecycle, cryptographic, audit, or data-generation behavior.
4. Treat proposed items as unapproved. Ask the user when an unresolved choice materially affects behavior or acceptance.
5. Use the existing required stack and module boundaries unless the user approves a justified change.
6. Make precise changes, add focused tests, and run the smallest relevant verification; report actual results and warnings, not assumptions.
7. After an approved task is complete, update `docs/development-progress.md`, `PROJECT_CONTEXT.md`, and this handover where status or facts changed. Record explicit decisions in `docs/DECISIONS.md`.
8. Never add real secrets, include ground-truth labels in application inputs, or silently corrupt baseline records.
9. Do not mark a phase complete until its exit checks and all mapped original requirements are actually verified.

## Current approval boundary

No follow-on product implementation is authorized by this handover. Wait for the user to approve the next task. The immediate recommended task is to clarify identity/access requirements and actor permissions before Phase 2 implementation; see the unresolved-question register.
