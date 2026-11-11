# Handover

This file tells the next developer or AI assistant where the project stands, what is safe to change, and what to do next. Facts about the system itself are in [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

Last updated at the end of Phase 12 (documentation). Phases 10.2 and 12 were developed on branch `arena/99b942bb-yottaflex-ai-creadential-lifec`, based on commit `bf13481`, and merged into `main` together.

## Read first

1. [README.md](README.md): what the system does and how to run it.
2. [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md): structure, facts and conventions.
3. This file: status, rules and next steps.
4. [docs/known-issues.md](docs/known-issues.md): defects and gaps that are already known.
5. [docs/DECISIONS.md](docs/DECISIONS.md): decisions and the assumptions IA-01 to IA-21.
6. [docs/original-problem-statement.md](docs/original-problem-statement.md): the binding requirements.

The original problem statement is the source of truth. Do not remove, weaken or reinterpret a requirement without the user's explicit approval.

## Status snapshot

| Item | State |
|---|---|
| Commit before this work | `bf13481` "feat: integrate full dataset analytics and validation" |
| Added on top of it | One commit with the Phase 10.2 code and tests (9 modified files, 4 new test files), one commit with the Phase 12 documentation |
| Backend tests | 122 passed with a test database; 25 passed and 97 skipped without one |
| OpenAPI | 40 paths, 48 operations, 49 schemas |
| Database | 23 tables, one Alembic revision `af6e5dad6637` |
| Frontend | Builds; no automated tests |
| Docker Compose | Not run in the last two phases |
| Full seed dataset validation (Phase 11) | **Open** |

Run `git log --oneline` to see the two commits. Neither phase had an independent code review before the merge; reviewing the Phase 10.2 diff is a reasonable first action for whoever continues.

### Files changed in Phases 10.2 and 12

Phase 10.2, code:

```text
backend/app/api/v1/endpoints/business.py
backend/app/core/dependencies.py
backend/app/main.py
backend/app/schemas/api.py
backend/app/services/credentials.py
backend/app/services/eligibility.py
backend/app/services/management.py
backend/tests/integration/test_api_workflows.py
frontend/src/pages/analytics/Analytics.jsx
```

Phase 10.2, new tests:

```text
backend/tests/integration/support.py
backend/tests/integration/test_api_input_safety.py
backend/tests/integration/test_credential_lifecycle_analytics.py
backend/tests/integration/test_issuance_business_rules.py
```

Phase 12, documentation: `README.md`, `AI_HANDOVER.md`, `PROJECT_CONTEXT.md`, and files under `docs/`. No code was changed in Phase 12.

## What each phase delivered

The repository roadmap in [docs/development-progress.md](docs/development-progress.md) and the later work plan number the phases differently. This table uses the later work plan.

| Phase | Content | Result |
|---|---|---|
| 1 to 9 | Scaffold, architecture, authentication, schema, rules, completions, eligibility, issuance, verification, revocation, audit | Implemented by the project author. Recorded in `docs/development-progress.md` and `docs/acceptance-test-report.md`. |
| 10 | Synthetic data generator, ground truth, reproducibility | Implemented by the project author. Reports in `data/validation/`. |
| 10.1 | Read-only audit of the repository | Baseline: 1 test failed, 35 passed; a probe with malformed input produced 189 server errors out of 1,250 requests. |
| 10.2 | Backend fixes and tests | 122 tests pass; the same probe produces 0 server errors; issuance rules tightened. |
| 11 | Full seed dataset testing and validation | **Not done.** See below. |
| 12 | Documentation and handover | This set of documents. |

### What Phase 10.2 changed

- Malformed input no longer causes `500`. NUL characters, out-of-range timestamps, timestamps without a timezone, oversized offsets and wrong claim types now return `422`.
- A credential cannot be issued unless the evidence contains a completion dated on or before the evaluation time. This also applies to rules that only require a score.
- A rule with no requirement is rejected when it is created, and a stored empty rule never grants eligibility.
- A completion dated in the future is rejected on create and update (5-minute tolerance).
- The credential lifecycle report was corrected and covered by tests for empty, single and filtered data. The Analytics page now lists months that have revocations but no issuances.

### What Phase 11 still has to do

1. Generate the full profile on the target machine, or obtain the author's generated files.
2. Resolve the manifest hash problem (D-01 in [docs/known-issues.md](docs/known-issues.md)): either regenerate and commit manifests produced with LF line endings, or add a `.gitattributes` rule so the hashed files have the same bytes on every platform.
3. Import into a database named `credential_fullscale_integration`, then run `verify_full_dataset.py` and `run_full_dataset_validation.py`.
4. Decide what to do with `exercise_full_dataset_api.py`, which cannot pass as written (D-06).
5. Run `benchmark_api.py` and store the report where `API_PERFORMANCE_REPORT_PATH` points.
6. Replace the committed `full_dataset_validation_report.json`, which records `failed`, with a passing report, or document why it fails.

A scratch run of steps 1 to 3 was done during the audit with regenerated data and passed (839,400 rows, 30 of 30 checks). It did not use the committed manifests, so it does not close Phase 11.

## Rules for changing this repository

### Do not edit these files without regenerating the dataset manifests

`data/generated/source_manifest.json` stores SHA-256 hashes of seven files. Any change to them, including whitespace and line endings, breaks import and validation of the full dataset.

```text
docs/original-problem-statement.md
backend/app/models/domain.py
backend/migrations/versions/af6e5dad6637_create_credential_domain_schema.py
backend/scripts/check_reproducibility.py
backend/scripts/generate_seed_data.py
backend/scripts/seed_data_common.py
backend/scripts/validate_seed_data.py
```

A schema change therefore needs a new migration **and** a regenerated dataset with new manifests.

### Do not overwrite files under `data/`

The seed, import, verification, validation and benchmark scripts write to tracked files under `data/` unless given other paths. Always pass `--output-dir`, `--ground-truth-dir`, `--manifest`, `--dataset` and `--report` pointing outside the repository, unless replacing the committed reports is the goal.

### Protect databases

- Integration tests drop every table. `API_TEST_DATABASE_URL` must name an empty database whose name contains `test`.
- `generate_seed_data.py --reset` drops every table in `SYNTHETIC_DATABASE_URL`. The name must contain `synthetic`.
- `alembic downgrade base` deletes all data in `DATABASE_URL`.
- Do not run two test sessions against one test database at the same time.
- Do not weaken the name and emptiness guards in the test fixture or the scripts.

### Keep secrets out of Git

`.env` files are ignored. Never commit a `SECRET_KEY`, a database password or a signing private key, and never paste them into documentation. The key derived from the public seed in the synthetic data generator is deliberately not secret and must never sign real credentials.

### Keep the documentation generated where it is generated

`docs/api-documentation.md` and `docs/database/database-schema.md` were produced from the running application and a migrated PostgreSQL database, not written by hand. The generator scripts were kept outside the repository and are not part of this handover. If the API or schema changes, update these two files from the OpenAPI schema (`/openapi.json`) and from the database, and re-check every example.

### General working rules

1. Run `git status` before editing. Preserve changes you did not make.
2. Work on one task at a time and do not alter unrelated code.
3. Check [docs/DECISIONS.md](docs/DECISIONS.md) before deciding any business, security, lifecycle or data question. Treat the IA assumptions as defaults, not approvals.
4. Add a test with every behaviour change and run the suite. Report real results.
5. Ground-truth labels must never be read by application code.
6. After a change, update the document that describes the changed behaviour.
7. Do not mark a phase complete until its checks have actually been run.

## Requirements that must stay visible

From the original problem statement:

- Six actors: Learner, Instructor, Academic Administrator, Support Staff, Platform Administrator, Third-party Verifier.
- Nine mandatory entities: Learner, Course, CredentialRule, CompletionRecord, Credential, Issuer, VerificationRequest, Revocation, AuditEvent.
- Dataset volumes: 20,000 learners, 1,000 courses, 10,000 credentials, 5,000 verification requests; fixed seed `20261022`; parameterized generation.
- Four controlled anomalies that must be detectable: a credential issued before completion, a duplicate credential ID, a revoked credential reported as active, and an altered payload hash that goes unnoticed.
- Ground truth kept separate from application inputs.
- Two runs with the same seed must produce the same row counts, IDs, checksums, labels and validation results.
- Deliverables: seed data, schema, data dictionary, generator command, source manifest, validation summary, reproducibility report.

## Suggested next steps, in order

1. Review the Phase 10.2 diff (`git diff bf13481 -- backend frontend`).
2. Run `docker compose up --build` and confirm the README instructions (C-01).
3. Complete Phase 11 as listed above.
4. Get the role matrix (IA-16) approved or corrected.
5. Fix the small defects: F-04 (link a learner to an account in the UI), F-05 (placeholder), F-06 (refused requests on the learner page), B-17 (unreachable branch), D-04 (`SECRET_KEY` default in the generator), D-08 (`--help`).
6. Add rate limiting and a request size limit (B-01, B-02).
7. Add frontend tests.
8. Before any real use, work through [docs/security.md](docs/security.md#before-production-use).

## How the Phase 12 documentation was verified

Every command in the README, the testing document and the demonstration guide was run from a clean copy of the code as merged, with these exceptions, which are also stated where they occur:

- Docker and Docker Compose commands were not run (Docker was not available).
- PostgreSQL was 16.2, not the 17 used by the Compose file.
- PowerShell variants of the commands were not run.
- The full-profile seed generation command was not re-run in Phase 12.

API examples in `docs/api-documentation.md` are real responses captured from the running backend. Table, column and constraint names in `docs/database/database-schema.md` come from PostgreSQL after `alembic upgrade head`.
