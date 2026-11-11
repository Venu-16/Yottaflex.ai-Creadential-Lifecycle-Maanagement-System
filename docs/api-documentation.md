# API Documentation

The backend is a modular FastAPI application with SQLAlchemy services and
versioned routes under `/api/v1`. The OpenAPI document is generated from the
request/response schemas and route descriptions. Visit `/docs` for Swagger UI
and `/openapi.json` for the schema. `GET /health` reports application-process
availability; it does not assert database readiness.

## Local startup

From `backend/`, configure `DATABASE_URL` and a random `SECRET_KEY` of at least
32 bytes in `.env`, apply the existing schema, and start the API:

```powershell
python -m alembic upgrade head
uvicorn app.main:app --reload
```

The API is at <http://localhost:8000>, Swagger UI at
<http://localhost:8000/docs>, and health at
<http://localhost:8000/health>.

## Authentication and current MVP authorization

`POST /api/v1/auth/login` accepts JSON containing `principal_key` and
`password`, and returns a short-lived HS256 bearer token. Use that token as
`Authorization: Bearer <token>`. `GET /api/v1/auth/me` returns the active
account. Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, never
returned by the API.

There is deliberately no public user/role administration endpoint. Bootstrap
local demo accounts using environment variables and `python
scripts\bootstrap_demo_user.py` from `backend/`; see the root README. Role
assignments are checked on each protected request, and ungranted roles are
denied. Until the architecture actor matrix is approved, the implementation
uses restrictive assumption IA-16 in `docs/DECISIONS.md`; in particular,
Instructor and Support Staff have no learner-record mutation/read grant,
Platform Administrators cannot issue credentials, and only Academic
Administrators can issue/revoke. Learners can list credentials linked to their
own account. Third-party verification is anonymous and reveals no learner
name or assessment evidence. These are implementation assumptions, not
approved permissions.

## Endpoint groups

All list routes accept bounded `limit` and `offset` where applicable. Mutations
are audited; master-data deletion and audit editing/deletion are not exposed.

| Group | Routes |
|---|---|
| Auth | `POST /auth/login`, `GET /auth/me` |
| Learners | `GET/POST /learners`, `GET/PATCH /learners/{id}`, `GET /learners/me/credentials` |
| Courses | `GET/POST /courses`, `PATCH /courses/{id}` |
| Issuers | `GET/POST /issuers`, `PATCH /issuers/{code}`, `POST /issuers/{code}/signing-keys`, `POST /issuers/{code}/signing-keys/{key}/revoke` |
| Credential rules | `GET/POST /credential-rules`, `POST /credential-rules/{code}/versions` |
| Completion tracking | `GET/POST /enrollments`, `GET/POST /completions`, `PATCH /completions/{id}`, `GET/POST /assessment-attempts` |
| Eligibility | `POST /eligibility/evaluate` |
| Credentials | `GET /credentials`, `GET /credentials/{id}`, `GET /credentials/{id}/portable`, `GET /credentials/{id}/history`, `POST /credentials/issue` |
| Verification | `POST /verification/credential-id`, `POST /verification/portable`, `GET /verification/requests` |
| Revocations | `GET /revocations`, `POST /revocations/{credential_id}` |
| Audit | `GET /audit` |
| Reports | `GET /reports/summary`, `/reports/issuance`, `/reports/revocations`, `/reports/verification` |

## Example requests

Login and capture the returned token:

```json
{
  "principal_key": "admin@example.test",
  "password": "<locally configured password>"
}
```

Evaluate eligibility (the API re-reads operational evidence; it never consumes
synthetic ground truth):

```json
{
  "learner_id": "00000000-0000-0000-0000-000000000001",
  "rule_code": "COURSE-101"
}
```

Issue using an idempotency key:

```http
POST /api/v1/credentials/issue
Authorization: Bearer <token>
Idempotency-Key: <random-client-generated-key>
Content-Type: application/json
```

```json
{
  "learner_id": "00000000-0000-0000-0000-000000000001",
  "rule_code": "COURSE-101"
}
```

Issuance re-evaluates inside the request transaction, locks the award slot,
signs the canonical JSON payload with Ed25519, records the decision/credential/
audit event atomically, and returns the original credential for an identical
retry. A different request using the same key is rejected. Award-slot
uniqueness prevents duplicate root issuance independently of decision IDs.
Replacement is not available in this MVP.

## Verification and trust behavior

- Credential-ID lookup checks the registered public key, payload SHA-256,
  Ed25519 signature, and current revocation record.
- Portable verification canonicalizes the supplied payload, resolves the
  issuer/key registry, and checks current key trust. It uses the credential
  registry for revocation when the ID is known. Unknown lifecycle state is
  `UNVERIFIABLE`, not `VALID`.
- Outcomes include `VALID`, `REVOKED`, `NOT_FOUND`, `INVALID_SIGNATURE`,
  `TAMPERED`, and `UNVERIFIABLE`. `EXPIRED` is not supported by the schema.
- Missing/revoked/expired keys are not treated as trusted. If authoritative
  database status is unavailable, the request fails rather than returning a
  success-shaped result.
- Public responses expose only credential ID and issuer code; they do not
  return learner names, scores, or completion evidence.
- A normal database `issued_at` is an issuer-recorded value, not independent
  trusted timestamp evidence. Portable payload timestamps cannot establish
  that a signature was created during a historical key-validity interval.

Issuer signing key registration accepts public key material only. Configure the
corresponding private Ed25519 seed as `CREDENTIAL_SIGNING_PRIVATE_KEY` (base64,
32 bytes) in a local secret environment; never put it in PostgreSQL, source
control, frontend code, or synthetic exports. Configure the exact issuer code
and key ID as well. If signing configuration is missing or does not match the
registered public-key fingerprint, issuance returns a service-unavailable
error.

## Testing

The backend tests require a dedicated empty PostgreSQL test database; do not
use the synthetic-data database. The complete setup, exact test command,
coverage, latest validation results, and remaining hardening gaps are in
[docs/backend-testing.md](backend-testing.md).

## Error behavior and limitations

Validation errors return FastAPI's structured `detail` response; missing
authentication returns `401`, insufficient role returns `403`, missing
records return `404`, conflicting uniqueness/state returns `409`, and
ineligible issuance returns `422`. There is no global rate limiter, refresh
token/logout flow, account-management API, or external timestamp authority in
this increment. These need explicit security/product review before deployment.
