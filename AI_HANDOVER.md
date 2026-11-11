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
- **Current product phase:** Backend lifecycle APIs plus Phase 7 frontend development/integration. Phases 3–9 and 11 remain unchecked and incomplete.
- **Current task:** Frontend dashboard and API integration. The production frontend build passed; the backend suite passed 27 tests against a separate temporary PostgreSQL 17 test database. The live browser lifecycle workflow passed against disposable PostgreSQL, including VALID then REVOKED verification.
- **Implementation state:** FastAPI exposes auth/RBAC, master-data, enrollment/completion/assessment, eligibility, credential issuance, verification, revocation, audit, and reporting routes. SQLAlchemy has 23 MVP tables in `backend/app/models/domain.py`; no migration was added for this task. Seed generation/validation/reproducibility remains complete. Test-only signing material is never reused in the API.
- **Next step:** Continue remaining lifecycle/security acceptance work and complete broader original-criteria evaluation. Open items include an approved actor matrix, object-level scopes, account lifecycle, rate/body-size controls, production key custody, replacement issuance, trusted timestamps, and database-outage fault injection. Do not mark Phase 3–9 or 11 complete or claim production security sign-off.

## Repository facts

- Backend: FastAPI under `backend/app/`; settings in `app/core/config.py`; SQLAlchemy session dependency in `app/database/dependencies.py`; bearer auth/RBAC in `app/core/`; lifecycle services under `app/services/`; OpenAPI request/response models in `app/schemas/api.py`.
- Alembic uses `backend/migrations/`; revision `af6e5dad6637` creates 23 MVP tables.
- Backend tests include health, schema, synthetic-data, security unit tests, and PostgreSQL API integration coverage in `backend/tests/integration/test_api_workflows.py` (requires a dedicated empty `API_TEST_DATABASE_URL` with `test` in its database name). See `docs/backend-testing.md`.
- Frontend: Vite React app in `frontend/src/`; `App.jsx` configures login, public verification, protected role-gated routes, and shared workspace. The dashboard and workflow pages use the centralized Axios client and actual `/api/v1` endpoints. `GET /auth/me` includes current role codes for UI-only gating.
- Data: the full synthetic profile is in `data/generated/`; separate ground-truth and anomaly files are in `data/ground_truth/`; validation reports are in `data/validation/`. The detailed runbook is `docs/database/seed-data-guide.md`.
- Docker Compose defines `db`, `backend`, and `frontend`, uses a PostgreSQL health check and named volume. It has been built and tested locally.
- Existing setup docs are in `README.md`; detailed context and actual tree are in `PROJECT_CONTEXT.md`.
- Phase 4 logical design is in `docs/database/entity-catalogue.md`, `docs/database/data-dictionary.md`, and `docs/database/relationship-specification.md`; the root database-design and data-dictionary pages index the model and migration.
- Initial scaffold commit: `f0b335b22fe9396f5affe5bebca3c76276afce0b` (`chore: initialize credential lifecycle project and documentation`). The branch is `main`; the configured `origin/main` is unavailable. Check current Git status before editing; do not assume there are no subsequent user changes.

## Verified baseline and caveats

During initialization: backend health test, Python compile check, frontend production build, local health/page checks, and Compose validation passed. For schema work, pytest passed, compileall passed, Alembic reported no metadata drift, and disposable PostgreSQL checks passed. Two clean full-profile seed-data generations passed PostgreSQL/data validation at all required volumes. In the Phase 6.5 pass, `python -m pytest -q` passed **27 tests** (6 PostgreSQL integration, 13 auth/crypto unit, 3 schema, 4 seed-data, 1 health) against a newly created PostgreSQL 17 container with a tmpfs database. Compileall passed; OpenAPI generated **34 paths** including HTTP bearer auth; Alembic upgrade/check reported no metadata drift; Compose configuration and `git diff --check` passed. The test container was separate from the synthetic dataset and was removed after validation. Full coverage, individual commands, findings, and limitations are in `docs/backend-testing.md`.

An earlier scaffold run reported a Starlette/httpx deprecation warning; the latest full test run completed without warnings. Do not change dependencies without evaluating compatibility and need.

The prior environment used Python 3.13.2, Node 22.12.0, npm 11.0.0, and Docker Compose 5.0.0-desktop.1. `.env` files and secrets are intentionally not committed. `GET /health` does not test the database.

The current role mapping is IA-16 and remains unapproved. Academic Administrators issue/revoke; Platform Administrators manage master data/signing trust; Learners can list only their own linked credentials; Instructor/Support Staff are denied operational routes; verifier lookup is anonymous but minimized. Production key custody, rate limiting, object-level instructor scopes, replacement issuance, and independent trusted timestamps are not implemented.

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

The Phase 4 logical design and initial physical schema exist. Initial authentication/authorization and credential lifecycle APIs are now implemented, but remain incomplete and subject to review; no production signing-key custody exists. The deterministic synthetic-data generator and validators are present under `backend/scripts/`; see `docs/database/seed-data-guide.md`. Preserve the stipulated LRN, CRD, and VER formats and the documented MVP allocation assumption. Keep all other unresolved decisions explicit and do not mark Phases 3–9 complete prematurely.
