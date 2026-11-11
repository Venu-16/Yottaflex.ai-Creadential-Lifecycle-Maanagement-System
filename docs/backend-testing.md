# Testing

This document describes the automated tests, how to run them, what they cover, and what they do not cover.

**Current result: 122 passed, 0 failed, 0 skipped** when a test database is configured (about 75 seconds). Without a test database: 25 passed, 97 skipped.

Last run for this document: Python 3.11.2, PostgreSQL 16.2, from a clean copy of the code.

## Contents

- [Test layout](#test-layout)
- [How to run](#how-to-run)
- [Test database safety rules](#test-database-safety-rules)
- [What the tests cover](#what-the-tests-cover)
- [Other checks](#other-checks)
- [What is not tested](#what-is-not-tested)
- [History](#history)

## Test layout

All tests are in `backend/tests/` and run with Pytest. Configuration is in `backend/pytest.ini`.

| File | Tests | Needs PostgreSQL | Subject |
|---|---:|---|---|
| `test_health.py` | 1 | no | `GET /health` |
| `unit/test_security_and_crypto.py` | 13 | no | Password hashing, settings validation, JWT, canonical JSON, SHA-256, Ed25519 |
| `unit/test_domain_schema.py` | 3 | no | Table registration and PostgreSQL DDL compilation |
| `unit/test_seed_data.py` | 4 | no | Seed generator determinism, volumes, anomaly fixtures |
| `unit/test_full_dataset_import.py` | 4 | no | Import value conversion, count and checksum checks, database-name guard |
| `integration/test_api_workflows.py` | 11 | yes | Authentication, role denial, full lifecycle, concurrency, reports |
| `integration/test_issuance_business_rules.py` | 27 | yes | Conditions under which a credential may or may not be issued |
| `integration/test_api_input_safety.py` | 53 | yes | Malformed, oversized and out-of-range input |
| `integration/test_credential_lifecycle_analytics.py` | 6 | yes | Credential lifecycle report |
| **Total** | **122** | | |

Supporting files:

- `conftest.py` sets placeholder `DATABASE_URL` and `SECRET_KEY` values so that the application can be imported without a `.env` file.
- `integration/support.py` holds the shared `Workspace` helper, which signs in an administrator and builds learners, courses, rules, completions and credentials through the API.
- `tests/e2e/` is an empty package. There are no end-to-end tests.

The counts include parametrized cases. A test function that runs with five inputs counts as five tests.

## How to run

From `backend/` with the virtual environment active (see the [README](../README.md#2-configure-the-backend)).

**Unit tests only.** No database is needed:

```bash
python -m pytest
```

Expected: `25 passed, 97 skipped, 1 warning`. Each skipped test reports `API_TEST_DATABASE_URL must point to a dedicated disposable test database.`

**All tests.** Create an empty database whose name contains `test`, then set `API_TEST_DATABASE_URL`:

```bash
createdb credential_api_test
export API_TEST_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/credential_api_test
python -m pytest
```

PowerShell: `$env:API_TEST_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@localhost:5432/credential_api_test"`.

Expected: `122 passed, 1 warning`.

The warning is a `StarletteDeprecationWarning` from the test client (`Using httpx with starlette.testclient is deprecated`). It comes from the installed library versions and does not affect the results.

**A subset:**

```bash
python -m pytest tests/unit
python -m pytest tests/integration/test_issuance_business_rules.py
python -m pytest -k "idempotency"
```

A disposable PostgreSQL container also works as the test database:

```bash
docker run -d --name credential-pg-test --tmpfs /var/lib/postgresql/data \
  -e POSTGRES_USER=test -e POSTGRES_PASSWORD=local-test-only -e POSTGRES_DB=credential_api_test \
  -p 127.0.0.1:55432:5432 postgres:17-alpine
export API_TEST_DATABASE_URL=postgresql+psycopg://test:local-test-only@127.0.0.1:55432/credential_api_test
python -m pytest
docker rm -f credential-pg-test
```

The container commands were not run for this document because Docker was not available. The project author used the same approach with PostgreSQL 17.

## Test database safety rules

The integration fixture (`api_database` in `integration/test_api_workflows.py`) creates every table before each test and **drops every table after it**. It protects other databases in three ways:

1. It uses only `API_TEST_DATABASE_URL`. It never uses `DATABASE_URL`.
2. It fails if the database name does not contain `test`.
3. It fails if the database already contains any table: `API integration test database must be empty before the test run.`

Rules for whoever runs the tests:

- Never point `API_TEST_DATABASE_URL` at the application database, a synthetic-data database, or any database with data you need.
- Do not run two test sessions against the same test database at the same time. The second one finds tables and fails.
- If a run is interrupted and leaves tables behind, drop and recreate the test database (`dropdb credential_api_test && createdb credential_api_test`).
- The tests build the schema from the SQLAlchemy models, not from the Alembic migration. Check the migration separately (see [Other checks](#other-checks)).

## What the tests cover

### Authentication and authorization

- Wrong password, missing token, malformed token, bad signature, expired token and inactive account all return `401`.
- A signed-in user whose role has no access gets `403`. This is tested for `SUPPORT_STAFF`, `INSTRUCTOR`, `THIRD_PARTY_VERIFIER` and `LEARNER`.
- A Platform Administrator cannot issue or revoke credentials. A learner cannot issue or revoke.
- A learner sees only credentials linked to their own account. A second learner sees an empty list.
- Password hashes round-trip, reject wrong passwords, and reject malformed stored hashes.
- Settings reject a short `SECRET_KEY` and a zero or negative token lifetime.

### Lifecycle

`test_lifecycle_issue_idempotency_portable_verification_and_revocation` exercises the whole flow in one test: master data, rule versions, completion, assessment, eligibility, issuance, idempotent retry, portable verification, tampering, key rotation, revocation, audit history and reports.

### Issuance rules

Each of these must **not** produce a credential:

- Completion dated in the future, on create and on update.
- A stored completion that is still ahead of the server clock.
- A score-only rule when the course is not completed.
- A rule with no requirement at all (rejected on create; a stored empty rule never grants eligibility).
- No enrollment, an enrollment in a different course, or a cancelled enrollment.
- An enrollment with no completion record, or a completion with status `in_progress`, `incomplete` or `failed`.
- A missing or ungraded assessment, or a grade dated in the future.

The same file checks that complete evidence still produces a credential, that an issued credential is never dated before its completion, and that a rejection leaves existing credentials and audit history unchanged.

### Uniqueness and concurrency

- The same `Idempotency-Key` with the same body returns the same credential.
- A different key for the same learner and course returns `409`.
- `test_credential_award_uniqueness_is_enforced_concurrently_by_postgresql` inserts the same award row from two PostgreSQL sessions and confirms that only one succeeds.

### Verification and integrity

- Canonical JSON and SHA-256 are deterministic.
- Ed25519 accepts a valid signature and rejects an altered one.
- Portable verification returns `VALID` for a real payload and `TAMPERED` for an altered one.
- The public verification response contains no learner name, learner ID or assessment data.

### Input safety

- NUL characters in a path, query string or JSON body return `422` on every route, including login and public verification.
- Text that only looks like a NUL escape is accepted.
- Timestamps outside the supported range and timestamps without a timezone return `422`.
- Report date ranges outside the supported range return `422`.
- Page offsets are bounded.
- Unknown identifiers return `404`.
- No response contains database driver text, SQL type names or a stack trace.

### Reports

- Reports return zeros, not errors, on an empty database.
- The credential lifecycle report is correct for zero, one active, one revoked and several credentials, and with filters applied.
- An unknown status filter returns `422`.

## Other checks

These are not part of the Pytest suite. Each was run by hand for this document.

| Check | Command | Result |
|---|---|---|
| Migration applies | `alembic upgrade head` | Revision `af6e5dad6637` applied |
| Models match migration | `alembic check` | `No new upgrade operations detected.` |
| Frontend builds | `npm ci && npm run build` in `frontend/` | Build succeeded |
| API walkthrough | The `curl` sequence in [demo-guide.md](demo-guide.md) | Issued `CRD-2026-000001`; verification returned `VALID`, `VALID`, `TAMPERED`, then `REVOKED` after revocation |
| Starter seed data | `generate_seed_data.py --profile starter --reset`, then `validate_seed_data.py` | `passed`, 30 checks |
| Frontend in a browser | Headless browser, three demo roles, every route; learner, eligibility, issuance and verification forms submitted | Pages rendered; role-restricted routes redirected; forms returned the expected results. Minor defects: see [known-issues.md](known-issues.md#frontend) |

## What is not tested

- **Frontend.** There are no component, unit or end-to-end tests. The manual browser check listed above did not submit the course, rule, enrollment, completion, assessment or revocation forms.
- **Docker Compose.** Not run for this document.
- **Full seed dataset.** No test in the suite loads the 839,400-row dataset. Its validation status is described in [known-issues.md](known-issues.md#seed-data-and-full-dataset-tools).
- **Load and performance.** No load test exists. `scripts/benchmark_api.py` is a short read-only timing run (20 list and report requests); it returned `passed` against a scratch full-dataset database, and no result is committed.
- **Database outage.** Behaviour when PostgreSQL is unreachable is not tested.
- **Concurrent issuance through the API.** Concurrency is tested at the database constraint, not with parallel HTTP requests.
- **Security testing.** No penetration test, dependency scan or static security analysis has been run. See [security.md](security.md#limitations).
- **PostgreSQL 17.** The last full run used PostgreSQL 16.2. The Docker image uses 17.

## History

| When | Result | Notes |
|---|---|---|
| Phase 9 (project author) | 30 passed | PostgreSQL 17 in a disposable container; OpenAPI had 34 paths |
| Before Phase 10.2 | 1 failed, 35 passed | Baseline at commit `bf13481` |
| After Phase 10.2 | 122 passed | 86 tests added; the failing test was fixed; OpenAPI has 40 paths and 48 operations |

The Phase 10.2 changes and the three new test files were merged together with this documentation.
