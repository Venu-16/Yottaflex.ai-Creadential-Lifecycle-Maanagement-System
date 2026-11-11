# Backend Testing and Hardening

## Current validation

The Phase 9 regression ran the full backend suite against a fresh, disposable
PostgreSQL 17 database:

- **30 passed, 0 failed**
- 9 PostgreSQL API integration cases, including anonymous and role-denial
  checks, learner object scope, account isolation, and public disclosure
- 13 unit tests for authentication primitives and cryptography
- 3 PostgreSQL schema metadata tests
- 4 synthetic-data fixture tests
- 1 health endpoint test

The PostgreSQL run used the disposable `phase9-pg-test` container, a tmpfs
database named `credential_phase9_test`, and host port `55437`; it was removed
after validation. The synthetic dataset was not used or modified.

The integration suite verifies authentication failures and inactive accounts,
deny-by-default permissions for learner, Instructor, Support Staff, Platform
Administrator, and third-party internal access, master-data and lifecycle
routes, eligibility evidence and attempt selection, pre-completion/unknown
learner/unknown rule issuance rejection, scheduled rule versions, idempotency,
concurrent duplicate award protection, key rotation and historical
verification behavior, revocation, audit/reporting, public-response
minimization, database constraints, and rollback on signing and database
failures.

Phase 9 authorization checks additionally confirmed:

- Anonymous access to the tested protected operations returns `401`;
  disallowed authenticated roles and learners attempting privileged operations
  receive `403`.
- A learner sees only credentials linked to the authenticated user; another
  learner's self-credential list is empty. The API has no user lookup/update
  endpoint (`/users/{id}` is `404`; mutating `/auth/me` is `405`).
- Public credential-ID verification returns only the documented verification
  fields and omits learner names, learner IDs, and assessment evidence.
- The observed behavior matches the restrictive IA-16 assumption. This does
  not approve the role matrix or implement instructor object scopes.

The configured signing private key is read from backend environment settings
and consumed by the signing service. Source inspection found no private-key
field in API request/response schemas or ORM records, no private-key reference
in frontend source or the production bundle, and no logging call that emits
the configured key. The public-key registration response is also tested not
to expose private material. These checks are bounded source/response checks,
not a production key-custody audit. Production requires a managed secret
store or KMS/HSM-backed signing boundary, least-privilege workload access,
audited rotation/revocation, and tested recovery procedures; environment
variables alone do not provide production key custody.

Additional checks passed:

- `python -m compileall -q app migrations scripts tests`
- Alembic `upgrade head` and `check` against the disposable PostgreSQL database
- OpenAPI generation: 34 paths, with the HTTP bearer scheme present
- Docker Compose configuration validation
- Frontend production build
- `git diff --check`

The documented Compose startup, migration, and demo-user bootstrap commands
were run against a separate fresh project. PostgreSQL became healthy; the
backend health check and frontend returned HTTP 200; the Academic
Administrator bootstrap succeeded twice; login, `/auth/me`, and the database
role assignment were verified. The project, network, and named database volume
were removed afterward. See
[acceptance-test-report.md](acceptance-test-report.md) for the full matrix and
fresh-setup results.

## Run tests safely (PowerShell)

Run from the repository root. This creates a named container with a temporary
in-memory database directory, separate from any project or synthetic-data
database. The integration fixture refuses to run unless its database name
contains `test` and the schema is empty.

```powershell
$pgPassword = "phase65-disposable-only"
docker run -d --name phase65-pg-test `
  --tmpfs /var/lib/postgresql/data:rw,size=512m `
  -e POSTGRES_USER=phase65_test `
  -e "POSTGRES_PASSWORD=$pgPassword" `
  -e POSTGRES_DB=credential_phase65_test `
  -p 127.0.0.1:55435:5432 postgres:17-alpine

for ($i = 0; $i -lt 30; $i++) {
  docker exec phase65-pg-test pg_isready -q -U phase65_test -d credential_phase65_test
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Seconds 2
}
if ($LASTEXITCODE -ne 0) { throw "Disposable PostgreSQL did not become ready" }

Set-Location .\backend
$env:API_TEST_DATABASE_URL = "postgresql+psycopg://phase65_test:$pgPassword@127.0.0.1:55435/credential_phase65_test"
python -m pytest -q
python -m compileall -q app migrations scripts tests

$env:DATABASE_URL = $env:API_TEST_DATABASE_URL
$env:SECRET_KEY = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
python -m alembic upgrade head
python -m alembic check

@'
from app.main import app
schema = app.openapi()
print("OpenAPI paths:", len(schema["paths"]))
print("Bearer auth scheme:", "HTTPBearer" in schema["components"]["securitySchemes"])
'@ | python -

Set-Location ..
docker compose --env-file .env.example config --quiet
git diff --check
```

After validation, stop and remove only the disposable container created above:

```powershell
docker rm -f phase65-pg-test
```

Do not point `API_TEST_DATABASE_URL` or `DATABASE_URL` at the synthetic seed
database, a shared development database, or any database containing data.
Alembic validation applies the project schema to the disposable container;
removing that container discards the database.

## Findings fixed in this pass

- Malformed PBKDF2 hashes with empty or incorrect-length digests could be
  accepted for an empty password; hash decoding now validates base64 and
  requires the configured salt and digest lengths.
- A zero-minute JWT override previously fell through to the configured default;
  non-positive token lifetimes are rejected, including invalid configuration.
- Long-lived access-token configuration now rejects zero/negative lifetimes.
- Documented placeholder JWT secrets and wildcard CORS origins are rejected by
  settings validation.
- A future-effective rule version previously marked the current version
  superseded immediately, leaving no effective rule until the scheduled start.
  Selection now honors effective timestamps while both scheduled versions
  remain selectable in their respective periods.
- Portable verification now rejects non-JSON values, safely handles malformed
  issuer/key claims, and reports a known credential payload mismatch as
  `TAMPERED`.
- Signing failures now return a sanitized service error and roll back all
  issuance-side rows. PostgreSQL constraint failures are also checked for
  rollback and sanitized responses.
- Enrollment, completion, course, rule, and signing-key timestamps now reject
  timezone-naive inputs.
- Issuer and learner-self credential list endpoints now enforce bounded
  pagination.
- The integration fixture now uses a fresh SQLAlchemy session per request and
  rolls it back on exceptions, matching the production dependency behavior.

## Remaining gaps and integration impact

This is a focused hardening/test pass, **not a complete penetration test or
production security sign-off**. SQL injection was checked by source inspection
of the API/service query paths; automated tests do not substitute for external
penetration testing.

- Role assignments remain implementation assumption IA-16, not an approved
  actor matrix. Frontend authorization must not be treated as a security
  boundary; backend roles remain authoritative.
- No request rate limiter or explicit request-body size limit is implemented.
  Public verification and login should not be exposed to untrusted Internet
  traffic until abuse controls are added.
- Production signing-key custody, external trusted timestamps, credential
  replacement, and user/role administration remain out of scope.
- Instructor and Support Staff object-level access is not implemented.
- Database-unavailable behavior is fail-closed by the request path, but was
  not fault-injected in this pass.
- The frontend integrates login and core lifecycle screens, but does not yet
  provide portable-payload verification, account/role administration, or the
  production controls listed above. The UI remains subject to backend
  authorization; it is not a security boundary.

These remaining items do not change the original requirements and do not mark
any roadmap phase complete.
