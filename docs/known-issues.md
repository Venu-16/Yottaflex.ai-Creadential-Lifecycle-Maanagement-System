# Known Issues and Limitations

This is a list of defects, gaps and surprising behaviour found while testing and documenting the project. Nothing here was fixed as part of the documentation work. Security-specific limitations are listed in more detail in [security.md](security.md#limitations).

Each item states what happens, why it matters, and what to do about it for now.

## Contents

- [Backend and API](#backend-and-api)
- [Frontend](#frontend)
- [Seed data and full dataset tools](#seed-data-and-full-dataset-tools)
- [Configuration and deployment](#configuration-and-deployment)
- [Features that are not implemented](#features-that-are-not-implemented)
- [Open decisions](#open-decisions)

## Backend and API

| ID | Issue | Effect | For now |
|---|---|---|---|
| B-01 | No rate limit on `POST /auth/login` or the two public verification endpoints | Password guessing and request flooding are not slowed. Every verification request also writes two database rows. | Do not expose the API to the internet without a rate-limiting proxy. |
| B-02 | No request body size limit in the application | A very large JSON body is read into memory before it is rejected. | Set a limit in the reverse proxy. |
| B-03 | `GET /health` does not check the database | The endpoint returns `{"status":"ok"}` when PostgreSQL is down. | Do not use it as a readiness check. |
| B-04 | Settings are read once at start-up | A change to `.env`, including the signing key settings, has no effect until the backend restarts. Issuance returns `503` in the meantime. | Restart the backend after editing `.env`. |
| B-05 | Revoking a signing key makes every credential signed with it `UNVERIFIABLE` | A key revocation invalidates all earlier credentials from that key, including already revoked ones. Issuance returns `503` until a new active key is registered and configured. | To rotate a key normally, register the new key with `supersedes_key_id`; this retires the old key, and its credentials stay `VALID` when verified by credential ID (but see B-20). Revoke only for a compromised key. |
| B-06 | A completion timestamp slightly ahead of the server clock is stored but cannot be used yet | `completed_at` up to 5 minutes ahead is accepted. Eligibility then returns `COMPLETION_DATE_IN_FUTURE` until the server clock passes it. | Wait and evaluate again, or record a timestamp that is not ahead of the server. |
| B-07 | `started_at` on a completion and all timestamps on an assessment attempt are not checked against the future | Only `completed_at` has a future check at write time. A future `graded_at` is stored; eligibility rejects it later with `ASSESSMENT_DATE_IN_FUTURE`. | None needed for correctness. Validate in the client. |
| B-08 | Revocation `reason_code` is free text | Any string up to 64 characters is accepted, so reports group by whatever was typed. | Agree on a fixed list of codes and use them consistently. |
| B-09 | Most status columns have no database `CHECK` constraint | Values such as course status and completion status are validated in the service layer only. A direct database write can store any value. | Write through the API only. |
| B-10 | Audit, decision, credential and revocation rows are append-only by convention | The API offers no update or delete for them, but the database does not block a user with table privileges. | Restrict database privileges. Add triggers or revoke `UPDATE` and `DELETE` before production. |
| B-11 | Sign-in attempts and denied requests are not audited | `audit_events` has no record of failed logins or `403` responses. | Use the web server access log. |
| B-12 | No endpoint lists signing keys | A registered key can be created and revoked but not read back through the API. | Query the `issuer_signing_keys` table. |
| B-13 | No `GET /courses/{course_id}` | Courses can be listed, created and updated, but not fetched one at a time. `scripts/exercise_full_dataset_api.py` calls this route and gets `405`. `GET /courses` accepts only `limit` and `offset`, so there is no search by course code either. | Page through `GET /courses`. |
| B-14 | A learner's linked account (`user_id`) can be set only when the learner is created | `PATCH /learners/{learner_id}` does not accept `user_id`. | Create the learner with `user_id`, or update the row in the database. |
| B-15 | A learner cannot download their own portable credential | `GET /credentials/{credential_id}/portable` is limited to the two administrator roles. | An administrator downloads it for the learner. |
| B-16 | `/learners/me/credentials` returns `403` to an administrator before it validates `offset` | Harmless, but the order of checks differs from other list endpoints. | None. |
| B-17 | `_course_code_for_scope` in `backend/app/services/credentials.py` contains an unreachable branch that refers to an undefined name | If the branch were ever reached it would raise `NameError` and return `500`. No test or probe reached it. | Remove or correct the branch. |
| B-18 | Report date ranges are capped at 10 years | A wider range returns `422`. | Query in smaller ranges. |
| B-19 | `backend/requirements.txt` uses version ranges and there is no lock file | Two installs made at different times can resolve different versions. `cryptography` is imported directly but declared only through `python-jose[cryptography]`. | Pin versions before a release. |
| B-20 | After a key rotation, portable payloads signed with the retired key verify as `UNVERIFIABLE` | Trust for a portable payload is evaluated at the current time, and a retired key is no longer valid at the current time. The same credential verified by credential ID is still `VALID`. An integration test asserts both results. Also, from reading `register_signing_key`: the old key's `valid_until` is set to the new key's `valid_from`, which only has to be later than the old key's `valid_from`. If the new `valid_from` is earlier than the issue time of existing credentials, those credentials fall outside the old key's validity period and would not verify by ID either. This second case was not tested. | After a rotation, verify by credential ID. Set the new key's `valid_from` to the current time, not to a past time. |
| B-21 | The test run prints one deprecation warning | With current library versions, Starlette reports that using `httpx` with its test client is deprecated. Tests pass. A future Starlette release may remove the support. | Pin versions, or follow the library's migration advice when upgrading. |

## Frontend

| ID | Issue | Effect | For now |
|---|---|---|---|
| F-01 | No automated frontend tests | Regressions in the interface are found only by hand. | Follow [demo-guide.md](demo-guide.md) after changes. |
| F-02 | No screen for issuers or signing keys | The Platform Administrator must register the issuer and the public key with the API. | Use the calls in [demo-guide.md](demo-guide.md#step-1-register-the-issuer-and-its-public-key). |
| F-03 | No screen for portable-payload verification | The public page verifies by credential ID only. | Use `POST /api/v1/verification/portable`. |
| F-04 | The learner form cannot link a learner to a login account | A learner created in the browser never appears under **My credentials** for any account. | Create the learner with the API and pass `user_id`. |
| F-05 | The verification page placeholder shows `CRD-00000001` | The real format is `CRD-YYYY-NNNNNN`, for example `CRD-2026-000001`. The placeholder suggests a format that never matches. | Enter the ID exactly as issued. |
| F-06 | When a learner opens **My credentials**, the page also requests `/learners` and `/credential-rules` | Both return `403`. The page still shows the learner's credentials and no error, but the browser console and the server log record the refused requests. | None needed. |
| F-07 | The access token is kept in `localStorage` | Any script running on the page can read it. | See [security.md](security.md#limitations). |
| F-08 | The API address is fixed at build time | `VITE_API_BASE_URL` is compiled into the bundle and Vite has no proxy configured. The browser must be able to reach that address directly, and that origin must be in `CORS_ORIGINS`. | Rebuild with the right value for each environment. |

## Seed data and full dataset tools

**Status: validation of the full seed dataset is not complete.** Do not describe the full dataset as validated.

What is known:

- The starter profile was generated and validated for this documentation: `passed`, 30 of 30 checks.
- The committed `data/validation/full_dataset_validation_report.json`, produced by the project author, records `failed`: 29 of 30 checks passed, and `source_file_hashes_match` failed for the migration file.
- The committed `data/validation/validation_summary.json` records 30 of 30 for an earlier baseline run, and `reproducibility_summary.json` records `passed`.
- During the audit, the full dataset was regenerated outside the repository, imported into a scratch database (839,400 rows) and checked: import verification passed, validation passed 30 of 30, and 28 analytics values matched direct SQL. That run used regenerated data and regenerated manifests, not the committed ones, so it does not replace a validation of the committed artifacts.

| ID | Issue | Effect | For now |
|---|---|---|---|
| D-01 | The committed manifests do not verify on a checkout with LF line endings | `data/generated/source_manifest.json` records SHA-256 hashes of seven source files as they were on the author's Windows checkout. On Linux or macOS, `import_full_dataset.py`, `verify_full_dataset.py` and `run_full_dataset_validation.py` stop with `Source-manifest SHA-256 does not match the dataset manifest` or report hash mismatches. | Regenerate the dataset and manifests locally and pass their paths with `--manifest`, `--dataset` and `--report`. |
| D-02 | The large generated files are not in the repository | `seed_data.jsonl.gz`, `ground_truth.csv` and `ground_truth.json` are ignored by Git. A fresh clone cannot import the full dataset without generating it. | Run `generate_seed_data.py --profile full`. |
| D-03 | Seven files must not be edited without regenerating the manifests | `docs/original-problem-statement.md`, `backend/app/models/domain.py`, the migration file, and `backend/scripts/{check_reproducibility, generate_seed_data, seed_data_common, validate_seed_data}.py` are hashed in `source_manifest.json`. Any edit, even whitespace, makes the hash check fail. | Regenerate after an intended change; otherwise leave them unchanged. |
| D-04 | `generate_seed_data.py --reset` fails unless `SECRET_KEY` is exported in the shell | `seed_data_common.py` sets a default `SECRET_KEY` that is shorter than 32 bytes. The settings validator rejects it, and the value in `.env` is not used because the environment variable takes precedence. | `export SECRET_KEY=<32 bytes or more>` before running. |
| D-05 | Scripts write into tracked files by default | Without explicit output and report paths, the generator, validator, importer and benchmark overwrite files under `data/`. | Always pass `--output-dir`, `--ground-truth-dir` and `--report` paths outside the repository unless you mean to replace the committed files. |
| D-06 | `scripts/exercise_full_dataset_api.py` cannot pass as shipped | Run as `python scripts/exercise_full_dataset_api.py` it fails with `ModuleNotFoundError: No module named 'app'`. With `PYTHONPATH=.` it stops at `Representative course detail request failed.` because it calls `GET /courses/{id}`, which does not exist (`405`). It also expects the data-quality report to be `failed`. | Treat it as unfinished. |
| D-07 | No API performance report is committed | `scripts/benchmark_api.py` works: run against the scratch full-dataset database with the current code, it returned `passed` (20 of 20 requests `200`). But no `data/validation/api_performance_report.json` is in the repository, so `GET /reports/performance` returns `not_measured`. The benchmark is a short read-only timing run, not a load test. | Run the benchmark against a full-dataset database, write the report outside `data/` or commit it deliberately, and set `API_PERFORMANCE_REPORT_PATH`. |
| D-08 | `scripts/bootstrap_demo_user.py` has no argument parser | `--help` does not print help; the script runs. | Read the [README](../README.md#4-create-demo-users). |
| D-09 | The full-dataset importer accepts only a database named `credential_fullscale_integration` and refuses a non-empty one | This is a safety guard, but the name is fixed in `full_dataset_common.py`. | Create a database with exactly that name. |
| D-10 | `GET /reports/data-quality` returns `not_configured` by default | It needs the four `FULL_DATASET_*_PATH` settings, which are absent from every `.env.example` and from `docker-compose.yml`. | Set the four paths in `backend/.env`. |

## Configuration and deployment

| ID | Issue | Effect | For now |
|---|---|---|---|
| C-01 | Docker Compose was not run while preparing this documentation | The Compose instructions were checked against the files only. The last recorded Compose run is the author's, in [acceptance-test-report.md](acceptance-test-report.md). | Run `docker compose up --build` and report any difference. |
| C-02 | Compose runs development servers | The backend starts with `uvicorn --reload` and the frontend with `npm run dev`. | Do not use the Compose file for production. |
| C-03 | Compose does not apply migrations | A new stack has an empty database until `alembic upgrade head` is run. | Run the command in the [README](../README.md#docker-compose). |
| C-04 | Compose publishes PostgreSQL on host port 5432 | The database is reachable from the host network. | Remove the port mapping if it is not needed. |
| C-05 | PostgreSQL versions differ between environments | The Compose image is PostgreSQL 17. The last full test run used 16.2. | Run the suite on 17 before relying on it. |
| C-06 | The `.env.example` placeholder for `SECRET_KEY` is rejected | This is intended, but the backend exits at start-up until the value is replaced. | Generate a key as shown in the [README](../README.md#2-configure-the-backend). |
| C-07 | The Phase 10.2 changes were merged without an independent code review | Nine modified files and four new test files changed backend behaviour. They are covered by the 122 tests, but no second person reviewed the diff. | Review `git diff bf13481 -- backend frontend`. |

## Features that are not implemented

| Feature | Note |
|---|---|
| Credential replacement or re-issue | The column `replacement_of_credential_id` exists; no endpoint uses it. A revoked credential cannot be re-issued for the same learner and course. |
| Credential expiry | No expiry column or check. |
| User and role administration | Users are created only by `bootstrap_demo_user.py`. No sign-up, password change or password reset. |
| Token refresh and logout | A token is valid until it expires. Deactivating the user is the only way to cut it short. |
| Permissions for `INSTRUCTOR`, `SUPPORT_STAFF`, `THIRD_PARTY_VERIFIER` | The roles exist and can sign in. No route accepts them. Third-party verification is anonymous instead. |
| Production key custody | The private key is an environment variable. No vault, KMS or HSM. |
| Trusted timestamps | All timestamps come from the server clock. |
| Enrollment cancellation | The status `cancelled` is read by eligibility, but no endpoint sets it. |

## Open decisions

- **Role matrix.** The permissions in the code follow implementation assumption IA-16 in [DECISIONS.md](DECISIONS.md). The problem statement names six actors and does not define their permissions. The matrix has not been approved.
- **Phase numbering.** The repository roadmap in [development-progress.md](development-progress.md) calls Phase 10 "synthetic data" and Phase 11 "end-to-end evaluation, hardening, and delivery". The later work plan uses Phase 10.2 for the backend fixes, Phase 11 for "full seed dataset testing and validation", and Phase 12 for this documentation. Phase 11 in the later sense is still open.
- **Other assumptions.** IA-01 to IA-21 in [DECISIONS.md](DECISIONS.md) are conservative defaults chosen during implementation. Each one should be confirmed or replaced.
