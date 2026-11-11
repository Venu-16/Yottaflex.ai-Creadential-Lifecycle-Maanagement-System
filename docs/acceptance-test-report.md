# Phase 8 Acceptance and Demo Readiness Report

## Result

**Overall status: PARTIAL.** The current MVP passed its tested lifecycle,
authorization, database, Compose, and browser scenarios. This is not a
production-security sign-off, and it does not close every original requirement.
The 11-phase roadmap remains open; Phase 11 is not complete.

The backend tests and live Compose demonstration used isolated PostgreSQL 17
databases. The synthetic dataset was neither selected as a connection target
nor modified. Synthetic volume and reproducibility claims below rely on the
checked-in validation reports; those comparatively expensive data-generation
runs were not repeated during this acceptance pass.

## Requirement-to-implementation traceability

`PASS` means implementation and supporting evidence were found. `PARTIAL`
means the feature is present but has a documented scope, policy, or evidence
gap. Historical data reports are identified explicitly rather than presented
as a fresh Phase 8 rerun.

| Requirement | Implementation location | Evidence | Status |
|---|---|---|---|
| Use the required React/Vite, FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT, Docker Compose stack. | `backend/`, `frontend/`, `docker-compose.yml` | Fresh Compose build/start, database health, frontend/API browser workflow; frontend production build. | PASS |
| Support the six named actors without inventing their permissions as approved policy. | `docs/DECISIONS.md` (IA-16), `backend/app/core/`, `frontend/src/App.jsx` | API tests cover Learner, Instructor, Academic Administrator, Support Staff, Platform Administrator, and anonymous verifier paths. IA-16 remains explicitly unapproved. | PARTIAL |
| Manage learners, courses, and issuers. | `backend/app/api/v1/endpoints/`, `frontend/src/pages/Workspace.jsx` | PostgreSQL integration tests; live browser created and edited learner/course and registered a disposable issuer. | PASS |
| Configure and version credential rules. | Rule endpoints and `backend/app/services/eligibility.py`; workspace rules page | Integration coverage for scheduled versions; browser created rule versions v1/v2. | PASS |
| Record enrollments, completions, and assessment attempts. | Completion endpoints and services; workspace learning-record page | Integration tests; browser recorded both a passing and below-threshold learner workflow. | PASS |
| Evaluate eligibility using operational evidence and preserve decision evidence/version. | `backend/app/services/eligibility.py`, eligibility schemas/models | Unit/integration assertions; browser displayed the selected rule version and a below-threshold reason. | PASS |
| Prevent issuance without completion/assessment requirements; reject unknown learner/rule. | `backend/app/services/credentials.py`, issuance endpoint | PostgreSQL integration checks assert 422 for issuance before completion and 404 for unknown learner/rule, with no credential row created. | PASS |
| Issue unique credentials idempotently and resist concurrent duplicate issuance. | Credential service, PostgreSQL constraints and issuance endpoint | Integration tests cover same-key retries, different keys for one award slot, concurrency, duplicate credential ID constraint, rollback, and `CRD-2026-000001` format. | PASS |
| Protect credential integrity with canonical JSON, SHA-256, and Ed25519. | `backend/app/services/credentials.py`, issuer key registry | Unit/API tests verify signing and tamper outcomes; disposable Compose flow issued an Ed25519 credential. | PASS |
| Provide independent third-party credential verification with minimal disclosure. | Public verification endpoints; `frontend/src/pages/verification/Verification.jsx` | Anonymous browser requests returned VALID, REVOKED, and not-found outcomes; public UI/API response contained no learner name or assessment evidence. | PASS |
| Support portable-payload verification. | `POST /api/v1/verification/portable` | Backend integration tests cover valid, tampered, invalid-signature, unknown-key, malformed-key, and historical-key cases. There is no portable-payload frontend screen. | PARTIAL |
| Revoke credentials and make revocation authoritative immediately. | Revocation service/endpoint and revocation page | Browser required confirmation, revoked the issued credential, and then received REVOKED; integration tests cover state and constraints. | PASS |
| Preserve immutable-style, attributable audit history. | Audit service, append-only event table, `GET /audit` | Browser and database confirmed issuance, rejection, verification, and revocation events. Application/API convention is append-only; cryptographic immutability and tamper-evident storage are not provided. | PARTIAL |
| Produce reports and dashboard metrics from backend data. | Reporting endpoints; dashboard and reports pages | Browser report reflected one issued, one revoked, and four verification requests. API does not expose learner/course totals; dashboard correctly does not fabricate them. | PARTIAL |
| Define all nine mandatory entities and their relational constraints. | `backend/app/models/domain.py`, initial Alembic migration, database design docs | PostgreSQL schema tests, migration and metadata check, foreign-key/unique/enum checks in stored validation report. | PASS |
| Generate required baseline volumes with seed `20261022`, using parameterized full/starter generation. | `backend/scripts/`, `data/generated/`, `docs/database/seed-data-guide.md` | Stored `data/validation/validation_summary.json` reports 20,000 learners, 1,000 courses, 10,000 credentials, and 5,000 verification requests. Not regenerated for this pass. | PASS |
| Demonstrate the four controlled anomaly cases. | `data/ground_truth/`, generator/validator, lifecycle tests | Stored validation report checks labelled fixtures; live/API tests prevent pre-completion issuance, reject duplicate IDs, ensure revoked credentials are not VALID, and detect altered payload/signature. | PASS |
| Validate keys/FKs, enums, dates, reconciliation, lifecycle, duplicates, and cross-entity consistency. | Synthetic validator, PostgreSQL constraints, backend tests | Stored full-profile validation reports all checks passed; fresh PostgreSQL integration suite and live lifecycle completed. | PASS |
| Keep ground truth out of application inputs and decision logic. | `data/ground_truth/`, generator, eligibility service | Stored validation confirms separate checksummed ground truth; source review found no decision-service dependency on labels. | PASS |
| Deliver schema, dictionary, generator instructions, manifest, validation, and reproducibility outputs. | `docs/`, `backend/scripts/`, `data/` | Required files are present and linked from the seed guide. | PASS |
| Reproduce IDs, counts, checksums, labels, and validation results across two same-seed runs. | Generator and `data/validation/reproducibility_summary.json` | Stored report says both runs matched with no differences. This two-run job was not repeated for Phase 8. | PASS |
| Document lawful data provenance. | Seed guide and source manifest | Stored manifest/validation reports synthetic-only data and no external dataset. | PASS |
| Measure realistic distributions and evaluation quality. | Seed generator, validation outputs, reporting API | Counts, integrity, reconciliation, and lifecycle outcomes are measured. No distribution-quality benchmark or complete comparative model evaluation is documented. | PARTIAL |
| Complete a demonstrable end-to-end lifecycle. | Frontend workspace + API + PostgreSQL | Fresh Compose browser run: learner/course/rule → enrollment/completion/score → eligible issue → VALID → confirmed revoke → REVOKED; an ineligible issuance was rejected. | PASS |
| Be production-ready and fully complete every acceptance criterion. | Project as a whole | Open items below include policy approval, object scope, abuse controls, key custody, and missing product features. | PARTIAL |

## Live acceptance scenarios

| Scenario | Evidence from this pass | Result |
|---|---|---|
| Incomplete learner cannot be issued a credential. | New PostgreSQL API assertion: issuance before completion returns 422 and leaves credential count unchanged. | PASS |
| Below-threshold learner cannot be issued a credential. | Live UI evaluation returned `ineligible` / `ASSESSMENT_BELOW_THRESHOLD`; attempted issuance returned 422 and created no credential. | PASS |
| Unknown learner or rule is rejected. | New API assertions return 404 for each; no credential row is created. | PASS |
| Duplicate credential IDs are rejected. | PostgreSQL integration test inserts a duplicate external ID and expects `IntegrityError`; row count remains unchanged. | PASS |
| Credential issued before completion is prevented. | Same pre-completion API attempt above. | PASS |
| Revoked credential never verifies as VALID. | Browser verified `VALID` before revocation and `REVOKED` after; database contains the revocation. | PASS |
| Altered payload/hash and invalid signature fail closed. | PostgreSQL API tests cover tampered credential payload and portable payload, invalid signature, unknown key, and malformed trust material. | PASS |
| Duplicate issuance does not create duplicate credentials. | Integration suite covers concurrent same-key retries and different-key same-award-slot conflict. | PASS |
| Issuance, verification, and revocation are audited. | Database query showed 23 audit events; UI history included issuance, rejection, verification, and revocation events. | PASS |

## Security and role validation

| Check | Evidence | Result |
|---|---|---|
| Missing, malformed, expired, wrong-signature JWT; invalid username/password; inactive user | PostgreSQL API authentication tests assert expected 401 responses. | PASS |
| Learner cannot issue/revoke; Support Staff denied operational routes | Existing API integration tests assert 403. | PASS |
| Instructor and Third-party Verifier cannot access internal workflows | New parameterized PostgreSQL integration tests assert 403 for learner/course/eligibility/issue/revoke routes. | PASS |
| Platform Administrator cannot issue/revoke; Academic Administrator can perform lifecycle operations | API role tests plus fresh browser issuance/revocation as Academic Administrator. Platform Administrator browser exposes neither issue nor revocation controls; API rejects those operations. | PASS |
| Public verification needs no login and minimizes disclosure | Logged out; protected learner route redirected to login while public verifier returned REVOKED. No learner name/evidence appeared in the response or UI. | PASS |
| Private signing seed is absent from responses, logs, database dump, and frontend production bundle | Compared the runtime-only disposable seed against each output; all checks were false. Database schema has no private-named column. | PASS |
| SQL injection, exception leakage, CORS, pagination, secret validation | Bounded source review and automated request-validation tests; configured CORS origin was the local frontend origin. No confirmed exploitable defect found in the exercised paths. | PARTIAL |
| Security readiness | No external penetration test; no public-endpoint rate limiting/body-size cap, production key custody, or independent timestamp authority. | PARTIAL |

Role grants are implementation assumption IA-16, not approved policy. Frontend
role gating is not a security boundary; backend denials were independently
tested. Do not treat this matrix as a full penetration test.

## Browser and fresh-setup results

The actual React app and FastAPI API ran from a fresh Docker Compose project
against PostgreSQL 17. The Compose database used a newly created namespaced
volume and did not connect to the test or synthetic database.

- Compose configuration and image builds passed; PostgreSQL reported healthy.
- Alembic applied the initial schema; bootstrap created separate temporary
  Platform and Academic Administrator demo identities.
- Backend `/health` returned `{"status":"ok"}`; frontend loaded at
  `http://localhost:5173`; OpenAPI generation exposed 34 paths.
- Browser exercised login/logout, protected-route redirect, role-dependent
  navigation/actions, learner create/update/details, course create/update,
  rule creation/versioning, enrollment, completion, assessment, passing and
  failing eligibility, failed and successful issuance, public VALID/REVOKED/
  not-found checks, revocation confirmation, audit history, and reports.
- At 390 px viewport width, the mobile drawer opened, navigated, and closed;
  document width was 375 px after navigation (no page-level horizontal
  overflow). Table content remains horizontally scrollable inside its table
  container.
- Empty credential state and the expected 422 ineligible-issuance error were
  observed. The browser console recorded that intentional 422 response; no
  unhandled JavaScript exception was observed. A dedicated loading-state
  timing assertion was not performed.
- Fresh DB snapshot after the workflow: 2 learners, 1 course, 1 rule, 1
  credential, 1 revocation, 4 verification requests, 23 audit events.
- First Compose bootstrap attempt exposed that the backend image omitted
  `scripts/`. This was fixed by copying `backend/scripts/` into the image; the
  rebuilt image successfully bootstrapped both demo roles.

The temporary test database was `credential_phase8_test` on PostgreSQL 17,
container `phase8-pg-demo`, host port 55437, using tmpfs. The fresh Compose demo
database was `phase8_acceptance` in the isolated `phase8acceptance` Compose
project. Both temporary environments were removed after validation.

## Commands executed

From `backend/`, with `API_TEST_DATABASE_URL` pointing only to the disposable
PostgreSQL test database:

```powershell
python -m pytest -q
python -m compileall -q app migrations scripts tests
```

Additional checks:

```powershell
python -m alembic upgrade head
python -m alembic check
npm run build
docker compose config -q
git diff --check
```

The final test run reported **29 passed, 0 failed**: 8 PostgreSQL API
integration cases, 13 authentication/cryptography unit cases, 3 schema tests,
4 synthetic-data tests, and 1 health test. The backend test fixture requires a
dedicated empty PostgreSQL database whose name contains `test`; do not point it
at a shared or synthetic dataset.

## Demo dataset recipe and sequence

Use a fresh local database and synthetic-only records; do not use the generated
full dataset for the short demo. A tested compact recipe is:

- Learner `LRN-800001` completes course `DEMO-COURSE-001`.
- Rule `DEMO-RULE-001` requires completion and a score of at least 70.
- Record a graded score of 85 for the successful path and 55 for the
  below-threshold path.
- The successful path issues `CRD-2026-000001`; verify it, revoke it with a
  reason, then verify the same ID again.
- Keep demo usernames, passwords, database password, JWT secret, and generated
  Ed25519 private seed local and out of version control. Provision the
  Platform Administrator and Academic Administrator with the documented
  `backend/scripts/bootstrap_demo_user.py` command. Register only the
  generated public key with the issuer API; keep its private seed in the
  backend environment.

### Local startup commands (PowerShell)

From the repository root, copy `.env.example` to `.env` and replace its
database password and JWT secret with local-only values. From a Python
environment with `backend/requirements.txt` installed, generate a fresh demo
keypair in memory and start the services. The private seed is assigned only to
the current process environment; do not print it or save it in source control.

```powershell
Copy-Item .env.example .env
# Edit .env: replace POSTGRES_PASSWORD and SECRET_KEY with local-only values.

$pair = python -c "import base64,json; from cryptography.hazmat.primitives import serialization; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; k=Ed25519PrivateKey.generate(); print(json.dumps({'private':base64.b64encode(k.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())).decode(),'public':base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()}))" | ConvertFrom-Json
$env:CREDENTIAL_SIGNING_ISSUER_CODE = "DEMO-ISSUER"
$env:CREDENTIAL_SIGNING_KEY_ID = "demo-key-1"
$env:CREDENTIAL_SIGNING_PRIVATE_KEY = $pair.private

docker compose up --build -d
docker compose run --rm backend alembic upgrade head

$secure = Read-Host "Local demo password (12+ characters)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $env:DEMO_USER_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    $env:DEMO_USER_PRINCIPAL_KEY = "demo-platform@example.test"
    $env:DEMO_USER_ROLE = "PLATFORM_ADMINISTRATOR"
    $env:DEMO_USER_DISPLAY_NAME = "Demo Platform Administrator"
    docker compose run --rm backend python scripts/bootstrap_demo_user.py

    $env:DEMO_USER_PRINCIPAL_KEY = "demo-academic@example.test"
    $env:DEMO_USER_ROLE = "ACADEMIC_ADMINISTRATOR"
    $env:DEMO_USER_DISPLAY_NAME = "Demo Academic Administrator"
    docker compose run --rm backend python scripts/bootstrap_demo_user.py
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    Remove-Item Env:DEMO_USER_PASSWORD, Env:DEMO_USER_ROLE, Env:DEMO_USER_PRINCIPAL_KEY, Env:DEMO_USER_DISPLAY_NAME -ErrorAction SilentlyContinue
}

$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/auth/login" `
    -ContentType "application/json" `
    -Body (@{ principal_key = "demo-platform@example.test"; password = "<the local password>" } | ConvertTo-Json)
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/issuers" `
    -Headers $headers -ContentType "application/json" `
    -Body (@{ issuer_code = "DEMO-ISSUER"; name = "Demo Issuer" } | ConvertTo-Json)
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/issuers/DEMO-ISSUER/signing-keys" `
    -Headers $headers -ContentType "application/json" `
    -Body (@{
        key_id = "demo-key-1"
        public_key_base64 = $pair.public
        algorithm = "Ed25519"
        valid_from = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json)
```

Replace `"<the local password>"` in the login body with the password supplied
at the secure prompt; do not save it in the repository. Open
`http://localhost:5173`. On later runs, the signing key must be supplied again
to the backend environment (or through a local secret manager). Use
`docker compose down` to stop services; omit `-v` to retain local demo data.

Recommended short demonstration:

1. Sign in as Academic Administrator and show the dashboard/audit trail.
2. Show the below-threshold evaluation and rejected issuance.
3. Show the eligible learner’s assessment, eligibility decision, and issue.
4. Verify the credential publicly as VALID without signing in.
5. Revoke with the confirmation step and verify the same ID as REVOKED.
6. Show the retained audit events and report counts.

## Remaining limitations

- The actor/permission policy IA-16 remains unapproved; instructor object
  scopes and account/role administration are not implemented.
- No production signing-key custody/rotation operations, rate limiting,
  request-body size limits, or independent trusted timestamp authority.
- Credential replacement is not implemented. Portable-payload verification is
  API-only. Health checks process availability, not database readiness.
- Audit events are append-only by application convention; no cryptographic
  tamper-evidence or immutable external storage.
- Learner/course aggregate dashboard totals and a distribution-quality
  benchmark are unavailable.
- A complete external security assessment, database-outage fault injection,
  and every original evaluation criterion remain outstanding.

No changes were committed. See `docs/development-progress.md` for roadmap
status and `AI_HANDOVER.md` for continuation notes.
