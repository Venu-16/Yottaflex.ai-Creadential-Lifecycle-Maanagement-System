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

- **Verified roadmap phases:** Phase 1 — project foundation; Phase 2 — approved architecture baseline; Phase 10 — synthetic data, quality, ground truth, and reproducibility.
- **Current product phase:** Phase 4 — the initial database model and migration exist; application workflows are not implemented. The task-level Phase 5 seed-data increment maps to roadmap Phase 10 and is complete.
- **Current task:** The seed-data generation, validation, and two-run reproducibility checks are complete. Roadmap Phase 5 (eligibility-rule definition) remains pending.
- **Implementation state:** FastAPI health endpoint and minimal frontend remain. SQLAlchemy has 23 MVP tables in `backend/app/models/domain.py`; initial Alembic revision is `backend/migrations/versions/af6e5dad6637_create_credential_domain_schema.py`. Seed generation, validation, ground-truth, and anomaly fixtures exist. No business APIs, auth flow, credential service, or production signing-key custody exists.
- **Next step:** Continue remaining product work without treating synthetic fixture assumptions as approved policy. Keep authorization deny-by-default. Do not mark Phase 4 complete.

## Repository facts

- Backend: FastAPI under `backend/app/`; settings in `app/core/config.py`; database engine/session in `app/database/connection.py`; SQLAlchemy domain metadata in `app/models/domain.py`; only `GET /health` is registered.
- Alembic uses `backend/migrations/`; revision `af6e5dad6637` creates 23 MVP tables.
- Backend tests include `backend/tests/test_health.py`, schema checks, and deterministic data/anomaly fixture checks; integration and e2e folders otherwise remain placeholders.
- Frontend: Vite React app in `frontend/src/`; `App.jsx` is a minimal status page; `services/api.js` is only an Axios configuration.
- Data: the full synthetic profile is in `data/generated/`; separate ground-truth and anomaly files are in `data/ground_truth/`; validation reports are in `data/validation/`. The detailed runbook is `docs/database/seed-data-guide.md`.
- Docker Compose defines `db`, `backend`, and `frontend`, uses a PostgreSQL health check and named volume. It has been built and tested locally.
- Existing setup docs are in `README.md`; detailed context and actual tree are in `PROJECT_CONTEXT.md`.
- Phase 4 logical design is in `docs/database/entity-catalogue.md`, `docs/database/data-dictionary.md`, and `docs/database/relationship-specification.md`; the root database-design and data-dictionary pages index the model and migration.
- Initial scaffold commit: `f0b335b22fe9396f5affe5bebca3c76276afce0b` (`chore: initialize credential lifecycle project and documentation`). The branch is `main`; the configured `origin/main` is unavailable. Check current Git status before editing; do not assume there are no subsequent user changes.

## Verified baseline and caveats

During initialization: backend health test, Python compile check, frontend production build, local health/page checks, and Compose validation passed. For schema work, `pytest` passed, compileall passed, Alembic reported no metadata drift, and a disposable PostgreSQL 17 instance passed migration upgrade/downgrade/re-upgrade plus duplicate award-slot and credential-ID rejection checks. Two clean full-profile seed-data generations passed PostgreSQL/data validation at all required volumes, including referential integrity, source-derived eligibility, SHA-256/Ed25519 verification, ground-truth checks, and an isolated duplicate-ID savepoint probe. The reproducibility report records identical manifests and validation results.

Known warning: pytest passed with a non-blocking Starlette deprecation warning about `httpx` use with `starlette.testclient` and a suggestion to use `httpx2`. Do not change dependencies without evaluating compatibility and need.

The prior environment used Python 3.13.2, Node 22.12.0, npm 11.0.0, and Docker Compose 5.0.0-desktop.1. `.env` files and secrets are intentionally not committed. `GET /health` does not test the database.

## Requirements that must remain visible

- Preserve all six actors, all nine mandatory entities, their required keys/relationship/lifecycle documentation, and any justified supporting entities.
- Preserve required volumes (20,000 learners; 1,000 courses; 10,000 credentials; 5,000 verification requests), seed `20261022`, parameterized generation, valid-baseline-first workflow, and labelled edge cases.
- Demonstrate all four controlled anomalies: issued before completion, duplicate credential ID, revoked credential reported active, and undetected altered payload hash.
- Keep ground-truth labels separate from application inputs/decision logic.
- Validate identifiers/relationships, enumerations, dates, arithmetic, lifecycle transitions, duplicates, and cross-entity consistency.
- Reproduce row counts, IDs, checksums, labels, and validation results across two runs with the same seed (verified for seed `20261022`).
- Deliver seed data, schema, data dictionary, generator command, fixed-seed documentation, source manifest, validation summary, and reproducibility report.
- Make eligible issuance, ineligible rejection, uniqueness, independent authenticity verification, revoked-status behavior, traceable operations, anomaly demonstration, required volumes, and reproducibility demonstrable end to end.

The complete text and remaining original criteria are in [docs/original-problem-statement.md](docs/original-problem-statement.md). The architecture baseline is approved; implementation assumptions remain separate from user-approved policy in [docs/DECISIONS.md](docs/DECISIONS.md).

## Synthetic seed data implementation

- Run from `backend/` with `SYNTHETIC_DATABASE_URL` and `DATABASE_URL` set to a dedicated PostgreSQL database. The default profile is full; `--profile starter` uses the same logic at reduced volumes.
- Generation requires an empty schema. `--reset` is destructive, is restricted to a database name containing `synthetic`, and additionally requires `CONFIRM_SYNTHETIC_DATABASE_RESET=YES`. It drops/reapplies the existing Alembic schema; it does not remove Docker volumes.
- The full data export is `data/generated/seed_data.jsonl.gz`; checksums/counts are in its manifest. Ground truth and anomalies are separate from operational rows.
- Test Ed25519 private material is derived from the public seed and held only in memory. It is intentionally not secret and must never be reused for real credentials.
- Read [docs/database/seed-data-guide.md](docs/database/seed-data-guide.md) for generation, validation, and reproducibility commands. Do not call synthetic status distributions or thresholds approved product policy.

## Working rules for the next assistant

1. Inspect current `git status` and relevant files before editing; preserve user changes.
2. Work one task/phase at a time. Do not repeat Phase 1, build future phases prematurely, or alter unrelated code.
3. Check `docs/DECISIONS.md` before settling any business, identity, security, lifecycle, cryptographic, audit, or data-generation behavior.
4. Treat implementation assumptions as safe defaults, not user approvals. Ask only when an unresolved choice fundamentally changes the product or creates irreversible data/security risk.
5. Use the existing required stack and module boundaries unless the user approves a justified change.
6. Make precise changes, add focused tests, and run the smallest relevant verification; report actual results and warnings, not assumptions.
7. After an approved task is complete, update `docs/development-progress.md`, `PROJECT_CONTEXT.md`, and this handover where status or facts changed. Record explicit decisions in `docs/DECISIONS.md`.
8. Never add real secrets, include ground-truth labels in application inputs, or silently corrupt baseline records.
9. Do not mark a phase complete until its exit checks and all mapped original requirements are actually verified.

## Current approval boundary

The user approved the existing architecture as the implementation baseline on 2026-11-11 and directed the team to proceed using conservative documented assumptions. Keep unapproved business/security semantics explicit; do not infer permission grants or claim assumptions are user-approved.

The Phase 4 logical design and initial physical schema exist. Phase 3 authentication/authorization behavior is not implemented, despite the User/Role persistence tables. No credential APIs or production signing-key custody exist. The deterministic synthetic-data generator and validators are present under `backend/scripts/`; see `docs/database/seed-data-guide.md`. Preserve the stipulated LRN, CRD, and VER formats and the documented MVP allocation assumption. Keep all other unresolved decisions explicit and do not mark Phase 4 complete prematurely.
