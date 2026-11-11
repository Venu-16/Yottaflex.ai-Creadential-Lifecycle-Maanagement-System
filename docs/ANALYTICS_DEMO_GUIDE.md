# Full-Dataset Analytics Demo

This guide covers the isolated full-profile PostgreSQL import and the live
Data & Analytics page. It does not modify the source export, generated
manifests, ground-truth files, existing Compose services, or existing database
volumes.

## Safety boundaries

- Use only a newly created disposable PostgreSQL database named
  `credential_fullscale_integration`.
- The importer refuses a different database name, non-PostgreSQL databases,
  a non-empty schema, an unexpected Alembic revision, or missing explicit
  import confirmation.
- Bind any local PostgreSQL test port to `127.0.0.1`; never use the trust-auth
  example outside a disposable local environment.
- Do not configure or expose `data/ground_truth/` to the application. The
  validator may read ground truth for quality checks; the importer and
  analytics API do not.
- Run backend regression tests against a separate empty database whose name
  includes `test`, never against the imported dataset.
- Do not stop or remove unrelated containers or volumes. Do not run
  `docker compose down -v` as part of this procedure.

## Create and migrate an isolated database

In a dedicated terminal, start a temporary PostgreSQL 17 container with no
named volume. This example publishes only to loopback:

```powershell
docker run --rm --name credential-fullscale-postgres `
  -p 127.0.0.1:55438:5432 `
  -e POSTGRES_DB=credential_fullscale_integration `
  -e POSTGRES_HOST_AUTH_METHOD=trust `
  postgres:17-alpine
```

In a second terminal:

```powershell
cd backend
$env:FULL_DATASET_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55438/credential_fullscale_integration"
$env:DATABASE_URL = $env:FULL_DATASET_DATABASE_URL
$env:SECRET_KEY = "<local random value of at least 32 bytes>"
python -m alembic upgrade head
$env:CONFIRM_FULL_DATASET_IMPORT = "YES"
python -m scripts.import_full_dataset
Remove-Item Env:CONFIRM_FULL_DATASET_IMPORT
python -m scripts.verify_full_dataset --report ..\data\validation\full_dataset_database_verification.json
python -m scripts.run_full_dataset_validation
```

Use the import confirmation only after verifying that the configured URL
points to the new disposable database. The importer streams the compressed
export, checks its manifest and table checksums, inserts in one transaction,
and verifies every table count before committing. Its report and the two
verification reports are written under `data/validation/`; existing baseline
reports are preserved.

The source manifest is immutable for this task. If the current source checkout
differs from a file hash captured when the export was generated, preserve that
failure in the validation output and report it as provenance drift; do not
rewrite the manifest or regenerate the dataset to make the check pass.

## Start the API and provision a local analytics user

In `backend/`, keep the database URL, a local-only random JWT secret, and the
report paths in the same process environment:

```powershell
$env:DATABASE_URL = $env:FULL_DATASET_DATABASE_URL
$env:SECRET_KEY = "<local random value of at least 32 bytes>"
$env:CORS_ORIGINS = "http://localhost:5178"
$env:FULL_DATASET_MANIFEST_PATH = "..\data\generated\manifest.json"
$env:FULL_DATASET_IMPORT_REPORT_PATH = "..\data\validation\full_dataset_import_report.json"
$env:FULL_DATASET_VALIDATION_REPORT_PATH = "..\data\validation\full_dataset_validation_report.json"
$env:FULL_DATASET_VERIFICATION_REPORT_PATH = "..\data\validation\full_dataset_database_verification.json"
$env:API_PERFORMANCE_REPORT_PATH = "..\data\validation\api_performance_report.json"
$env:DEMO_USER_PRINCIPAL_KEY = "analytics-admin@example.test"
$env:DEMO_USER_PASSWORD = "<temporary local password>"
$env:DEMO_USER_ROLE = "ACADEMIC_ADMINISTRATOR"
python scripts\bootstrap_demo_user.py
Remove-Item Env:DEMO_USER_PASSWORD
uvicorn app.main:app --host 127.0.0.1 --port 18080
```

The API reads the reports as configured; no dataset or credential metric is
fabricated by the UI. Do not use the test JWT key or account outside the
disposable local environment.

In another terminal:

```powershell
cd frontend
$env:VITE_API_BASE_URL = "http://127.0.0.1:18080/api/v1"
npm run dev -- --host 127.0.0.1 --port 5178 --strictPort
```

Open <http://127.0.0.1:5178>, sign in with the local Academic Administrator,
and select **Data & analytics**. The page shows live database totals and
rates, credential/eligibility/verification distributions, course activity,
assessment ranges, import/validation status, row-count reconciliation, and
measured response times. Date, course UUID, credential status, and verification
outcome filters are sent to the server only on endpoints that support them.
Overview rates are explicitly labeled all-time.

## API exercise and benchmark

With the API running, set the same temporary local account credentials:

```powershell
cd backend
$env:FULL_DATASET_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55438/credential_fullscale_integration"
$env:ANALYTICS_API_BASE_URL = "http://127.0.0.1:18080/api/v1"
$env:ANALYTICS_DEMO_USER = "analytics-admin@example.test"
$env:ANALYTICS_DEMO_PASSWORD = "<temporary local password>"
python -m scripts.exercise_full_dataset_api
python -m scripts.benchmark_api --repeats 3
Remove-Item Env:ANALYTICS_DEMO_PASSWORD
```

The API exercise reads records from the start, middle, and end of the learner,
course, and credential tables; checks bounded paging and unknown IDs; queries
the other populated entity lists; and verifies active, revoked, and unknown
credential IDs without authentication. Its only database-side lookup is
read-only and selects IDs for the verification requests. Public API
verification itself records verification/audit events, so the live row count
may exceed the original import snapshot afterward.

The benchmark runs bounded, sequential read requests with one warm-up per
route and saves raw timings, status distribution, average, median, p95,
maximum, and slowest route to
`data/validation/api_performance_report.json`. It is a local demonstration
measurement, not a production capacity claim. Refresh the analytics page to
read the measured report.

## Regression suite

Create a separate empty integration-test database in the disposable container,
then run from `backend/`:

```powershell
$env:API_TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:55438/credential_api_test"
python -m pytest -q
python -m compileall -q app scripts tests
python -m alembic check
```

Integration tests require an empty database named with `test`; their fixture
creates and drops tables in that database. Never point `API_TEST_DATABASE_URL`
at `credential_fullscale_integration`.

## Demo sequence

1. Sign in as the disposable Academic Administrator.
2. Open Data & analytics and review the imported learner/course/credential
   totals and explicit rates.
3. Use date and course filters on lifecycle/academic charts; use outcome
   filters on verification outcomes.
4. Review the expected/imported/current count table and any source-provenance
   warnings without concealing failed validation checks.
5. Review the measured API response summary after the benchmark has completed.
6. Open public verification and verify an active and revoked imported
   credential; confirm public responses contain no learner details.

The demo is not production-ready. Authorization policy remains an
implementation assumption; production signing-key custody, rate limiting,
replacement issuance, and trusted timestamps remain unresolved.
