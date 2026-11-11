# Security

How the Credential Lifecycle Management System protects accounts, authorizes requests, signs credentials and limits what a public verifier can learn. Each statement below is taken from the source file named beside it.

> **Status of this document.** It describes controls that exist in the code and tests that exercise them. The system has **not** had an independent security review, a penetration test or any certification, and this document does not claim one. It is a development and demonstration build. Read [Limitations](#limitations) and [Before production use](#before-production-use) before deploying it anywhere that matters.

## Contents

- [Summary of controls](#summary-of-controls)
- [Password hashing](#password-hashing)
- [JWT authentication](#jwt-authentication)
- [Role-based access control](#role-based-access-control)
- [Authorization boundaries](#authorization-boundaries)
- [Private and public key separation](#private-and-public-key-separation)
- [Ed25519 signing and verification](#ed25519-signing-and-verification)
- [Credential hash integrity](#credential-hash-integrity)
- [Revocation handling](#revocation-handling)
- [Public verification and data minimization](#public-verification-and-data-minimization)
- [Audit logging](#audit-logging)
- [Input handling](#input-handling)
- [Configuration and secrets](#configuration-and-secrets)
- [Security tests that exist](#security-tests-that-exist)
- [Limitations](#limitations)
- [Before production use](#before-production-use)

## Summary of controls

| Area | Control | Source |
|---|---|---|
| Passwords | PBKDF2-HMAC-SHA256, 600,000 iterations, random 16-byte salt, constant-time comparison | `backend/app/core/security.py` |
| Sessions | HS256 JWT, 30-minute default lifetime, `sub` and `exp` required | `backend/app/core/security.py` |
| Authorization | Deny by default; role checked against the database on every request | `backend/app/core/dependencies.py` |
| Duties | Key management and credential issuance are held by different roles | `backend/app/api/v1/endpoints/business.py` |
| Signing | Ed25519 over canonical JSON; private key only in the process environment | `backend/app/services/credentials.py` |
| Integrity | SHA-256 of the signed bytes stored and rechecked at verification | `backend/app/services/credentials.py` |
| Revocation | Append-only record; checked on every verification | `backend/app/services/credentials.py` |
| Privacy | Public verification returns a verdict and no learner data | `backend/app/schemas/api.py` (`VerificationResponse`) |
| Audit | Event written in the same transaction as each change | `backend/app/services/audit.py` |
| Configuration | Weak or placeholder `SECRET_KEY` rejected at start; wildcard CORS rejected | `backend/app/core/config.py` |

## Password hashing

| Property | Value |
|---|---|
| Algorithm | PBKDF2-HMAC-SHA256 (`hashlib.pbkdf2_hmac`) |
| Iterations | 600,000 |
| Salt | 16 random bytes per password (`secrets.token_bytes`) |
| Derived key | 32 bytes |
| Stored format | `pbkdf2_sha256$<iterations>$<salt, URL-safe base64>$<digest, URL-safe base64>` in `users.password_hash` |
| Minimum length | 12 characters, enforced by `hash_password` |
| Comparison | `hmac.compare_digest` (constant time) |

Verification fails closed: a missing hash, an unknown algorithm label, an iteration count outside 100,000 to 2,000,000, malformed base64 or a wrong salt or digest length all return `False` without raising.

Login (`POST /api/v1/auth/login`) returns the same `401 Invalid username or password.` for an unknown account, a wrong password and an inactive account, so the response does not reveal which accounts exist.

Plaintext passwords are never stored or logged by the application. The only place a password is supplied outside a login request is the `DEMO_USER_PASSWORD` environment variable read by `backend/scripts/bootstrap_demo_user.py`.

## JWT authentication

| Property | Value |
|---|---|
| Library | `python-jose` |
| Algorithm | HS256. `Settings` rejects any other value of `JWT_ALGORITHM`. |
| Signing secret | `SECRET_KEY`, at least 32 bytes; values containing `replace-with`, `change-me` or `your-secret` are rejected at start |
| Claims | `sub` (user UUID), `iat`, `exp` |
| Lifetime | `ACCESS_TOKEN_EXPIRE_MINUTES`, default 30; must be positive |
| Transport | `Authorization: Bearer <token>` |
| Decoding | Algorithm list pinned to the configured algorithm; `sub` and `exp` required |

The token carries **no roles**. On every request `get_current_user` decodes the token, then loads the user and requires `is_active = true`. Deactivating a user therefore takes effect on the next request, without waiting for the token to expire.

| Condition | Response |
|---|---|
| No `Authorization` header | `401 Bearer token required.` |
| Bad signature, malformed token, expired token, missing claim | `401 Invalid or expired access token.` |
| User deleted or inactive | `401 User is inactive or no longer exists.` |

There is no refresh token, no logout endpoint and no server-side token revocation list. A token stays valid until it expires or the user is deactivated.

## Role-based access control

Roles live in `roles` and are granted through `user_roles`. `require_roles(...)` loads the caller's active grants (`revoked_at IS NULL`, role `is_active`) on every request and returns `403` unless one of them is allowed for the route.

| Role | Granted by the API |
|---|---|
| `PLATFORM_ADMINISTRATOR` | Manage and read learners, courses, issuers, rules, enrollments, completions, attempts; evaluate eligibility; read credentials, revocations, verification history, audit and reports; **register and revoke signing keys** |
| `ACADEMIC_ADMINISTRATOR` | Everything above except signing keys; **issue and revoke credentials** |
| `LEARNER` | Read own profile (`GET /auth/me`) and own credentials (`GET /learners/me/credentials`) |
| `INSTRUCTOR`, `SUPPORT_STAFF`, `THIRD_PARTY_VERIFIER` | `GET /auth/me` only |

The exact role list for each of the 48 operations is in the [operation index](api-documentation.md#operation-index).

This matrix is an implementation assumption recorded as IA-16 in [DECISIONS.md](DECISIONS.md). It has not been approved as policy by a product owner.

## Authorization boundaries

| Boundary | How it is enforced |
|---|---|
| Deny by default | Every route in `business.py` declares either a role dependency or nothing; the only routes with no dependency are the two public verification routes, login and health. An integration test (`test_authentication_and_deny_by_default`) calls protected routes without a token and with a role that has no access, and expects `401` and `403`. |
| Separation of duties | `POST /credentials/issue` and `POST /revocations/{credential_id}` accept only `ACADEMIC_ADMINISTRATOR`. The two signing-key routes accept only `PLATFORM_ADMINISTRATOR`. Neither role can do both. Tests: `test_platform_administrator_cannot_issue_or_revoke`, `test_learner_cannot_issue_or_revoke_credentials`. |
| Learner isolation | `GET /learners/me/credentials` filters by the learner row whose `user_id` is the caller. A learner cannot name another learner in the request. Test: `test_learner_object_scope_account_isolation_and_public_disclosure`. |
| Unapproved roles | Instructor, Support Staff and Third-party Verifier accounts receive `403` on internal routes. Test: `test_unapproved_roles_cannot_access_internal_workflows`. |
| Frontend | `ProtectedRoute.jsx` and the navigation hide pages by role. This is a convenience only; the API is the enforcement point. |
| Cross-origin requests | CORS allows only the origins listed in `CORS_ORIGINS`; `*` is rejected at start. |

There is no finer-grained scope: an administrator can act on every learner, course and credential. There is no tenant, department or per-course restriction.

## Private and public key separation

| Key half | Where it lives | Who can provide it |
|---|---|---|
| Private (32 raw bytes, base64) | Only in the backend process, from the environment variable `CREDENTIAL_SIGNING_PRIVATE_KEY` | Whoever deploys the backend |
| Public (32 raw bytes) | Table `issuer_signing_keys.public_key`, with its SHA-256 in `fingerprint` | A Platform Administrator, through `POST /api/v1/issuers/{issuer_code}/signing-keys` |

Facts that follow from the code:

- No table has a column for a private key. A check constraint (`ck_issuer_keys_public_material_length`) limits the stored key to 32 bytes.
- No API request or response carries a private key.
- Before signing, `_configured_signing_material` derives the public key from the configured private key and compares it with the registered public key and fingerprint. A mismatch returns `503` and nothing is signed. A wrong or swapped key cannot silently produce credentials that fail verification later.
- The key must also be `active`, belong to the configured active issuer, and be inside its validity period.
- Verification needs only the public key, so the verification path never touches the private key.

Generate a key pair locally with the command in the [README](../README.md#5-generate-a-signing-key-pair). Never commit the private key, and never paste it into an issue, a log or a chat.

## Ed25519 signing and verification

**Signing** (`issue_credential`):

1. Build the payload (credential ID, payload version, key ID, learner ID, course code, issuer, rule version, issue time, completion time).
2. Serialise with `canonical_json`: sorted keys, separators `,` and `:`, UTF-8, non-ASCII kept as is, NaN and Infinity forbidden. The same payload always yields the same bytes.
3. `digest = SHA-256(bytes)`.
4. `signature = Ed25519.sign(private_key, bytes)` using the `cryptography` library.
5. Store `canonical_payload`, `sha256_digest` (32 bytes) and `signature` (64 bytes).

**Verification by credential ID** (`verify_credential_id`):

1. Recompute SHA-256 of the stored payload and compare with the stored digest. A difference is `TAMPERED`.
2. Verify the stored signature over the stored payload with the registered public key. A failure is `INVALID_SIGNATURE`.
3. Evaluate issuer trust at the recorded `issued_at`.
4. Look for an effective revocation.

**Verification by portable payload** (`verify_portable_payload`):

1. Canonicalise the submitted payload with the same function.
2. Look up the public key by the issuer code and key ID named in the payload. The payload is untrusted input; it only selects which registered key to try.
3. Verify the submitted signature over the canonical bytes.
4. If the claimed credential exists and its stored payload differs from the submitted bytes, the result is `TAMPERED`.
5. Evaluate issuer trust at the current time, because a self-asserted `issued_at` proves nothing.
6. Look for an effective revocation.

A portable payload that verifies cryptographically but whose credential is not in the registry is `UNVERIFIABLE`, not `VALID`: the registry is the authority on lifecycle state.

Database constraints back this up: `signature_algorithm` must be `Ed25519`, the signature must be 64 bytes, the digest 32 bytes.

## Credential hash integrity

Three SHA-256 digests are stored so that later changes can be detected:

| Digest | Column | Covers |
|---|---|---|
| Credential payload | `credentials.sha256_digest` | The exact bytes that were signed |
| Eligibility input | `eligibility_decisions.input_snapshot_digest` | The canonical JSON of the evidence snapshot the decision was based on |
| Evidence item | `eligibility_evidence.evidence_digest` | Each completion or attempt snapshot |

The credential digest is rechecked on every verification by ID. If someone edits `canonical_payload` in the database, the digest no longer matches and verification returns `TAMPERED`; if they edit both, the Ed25519 signature no longer verifies and the result is `INVALID_SIGNATURE`. Forging a consistent record requires the private key.

The eligibility digests are stored but no endpoint rechecks them. They support a manual or scripted audit.

## Revocation handling

| Property | Behaviour |
|---|---|
| Who | `ACADEMIC_ADMINISTRATOR` only |
| Record | One `revocations` row per credential (unique constraint); the credential row is untouched |
| Reason | `reason_code` required, `reason_detail` optional; both stored and audited |
| Effect | Immediate. `effective_at` is the server time and cannot be supplied by the caller. |
| Verification | Both verification modes query `revocations` on every call; there is no cache, so there is no window in which a revoked credential still verifies as `VALID` |
| Reversal | None. A second revocation returns `409`. |
| Holder's copy | A portable payload the holder kept still has a valid signature, but the API reports `REVOKED` because the registry is consulted |

Revoking a **signing key** is a separate operation with a wider effect: every credential signed by that key becomes `UNVERIFIABLE`. Use it for key compromise, not for withdrawing one credential.

## Public verification and data minimization

The two public routes return `VerificationResponse`:

| Field | Content |
|---|---|
| `verification_id` | Receipt `VER-YYYY-NNNNNN` |
| `overall_result` | `VALID`, `REVOKED`, `NOT_FOUND`, `INVALID_SIGNATURE`, `TAMPERED` or `UNVERIFIABLE` |
| `integrity_result`, `issuer_trust_result`, `lifecycle_result` | The three partial results |
| `credential_id` | The ID that was submitted |
| `issuer_code` | The issuer's code |
| `message` | A fixed sentence per result |

**Not returned:** learner name, learner ID, course, scores, completion date, enrollment data, revocation reason, who revoked, or the stored payload. A verifier who has only a credential ID learns whether it is valid and who issued it, and nothing about the holder.

The signed payload itself (held by the learner or an administrator) contains the pseudonymous `LRN-NNNNNN` identifier, the course code and the completion time. It contains no name, score or contact detail.

What the server keeps about a verification: the submitted credential ID, a SHA-256 of the input, the results, and timestamps. `requester_reference` is the constant `anonymous-verifier`. No IP address, user agent or other requester identity is stored.

Internal routes follow the same idea: `GET /credentials/{credential_id}` returns metadata without assessment evidence, and `GET /verification/requests` returns no learner details.

**Enumeration.** `NOT_FOUND` and `VALID` are distinguishable by design, and credential IDs are sequential within a year. Combined with the absence of rate limiting, a third party could count how many credentials were issued in a year and which are revoked. No personal data is exposed this way, but issuance volume is.

## Audit logging

`record_event` (`backend/app/services/audit.py`) adds an `audit_events` row to the same database session as the business change. Both commit together or not at all.

| Field | Content |
|---|---|
| `event_type` | One of 19 types, listed below |
| `outcome` | `success`, `rejected`, or the lower-case verification result |
| `actor_user_id`, `actor_reference` | The acting user's UUID, or `anonymous-verifier` |
| `target_type`, `target_reference` | For example `credential` and `CRD-2026-000001` |
| `reason_code` | Revocation reason or first rejection reason |
| `event_data` | Small JSON context, such as previous and new status |
| `occurred_at`, `correlation_id` | Server time; a UUID generated per event |

Event types: `learner.created`, `learner.updated`, `course.created`, `course.updated`, `issuer.created`, `issuer.profile_updated`, `issuer.signing_key_registered`, `issuer.signing_key_revoked`, `credential_rule.created`, `credential_rule.version_created`, `enrollment.created`, `completion.created`, `completion.status_updated`, `assessment_attempt.created`, `eligibility.evaluated`, `credential.issued`, `credential.issuance_rejected`, `credential.revoked`, `credential.verification`.

The API offers read access only (`GET /audit`, `GET /credentials/{credential_id}/history`); no route updates or deletes an event.

Not audited: logins (successful or failed), `401` and `403` responses, and read access to records.

## Input handling

| Control | Detail |
|---|---|
| Schema validation | Every request body is a Pydantic model with length and range limits (`backend/app/schemas/api.py`) |
| SQL | All queries go through SQLAlchemy with bound parameters; there is no string-built SQL in the request path |
| NUL characters | Rejected with `422` in the path, query string and JSON body on every `/api/v1` route |
| Timestamps | Must include a timezone and fall in the years 1900 to 2999 |
| Pagination | `limit` at most 100; `offset` at most 1,000,000,000 |
| Report ranges | At most 10 years |
| Untrusted portable payloads | A claimed credential ID that could not exist in the registry (longer than 15 characters, or containing NUL) is neither looked up nor stored |
| Database errors | Constraint violations are returned as `409`; the response never includes SQL or a stack trace |

A probe of 1,250 malformed requests against every route produced no `5xx` response after the Phase 10.2 fixes. That probe is a scratch tool and is not in the repository; the 53 tests in `backend/tests/integration/test_api_input_safety.py` cover the same classes of input.

## Configuration and secrets

| Rule | Where |
|---|---|
| `SECRET_KEY` shorter than 32 bytes or containing a placeholder marker stops the application at start | `Settings.validate_secret_key` |
| `CORS_ORIGINS` containing `*` stops the application at start | `Settings.validate_cors_origins` |
| `.env` files are ignored by Git; only `.env.example` files with placeholders are tracked | `.gitignore` |
| No default account, password, issuer or key ships with the code or the migration | `backend/scripts/bootstrap_demo_user.py`, migration `af6e5dad6637` |
| The synthetic dataset's keys are derived from the public seed and are for test data only | `backend/scripts/generate_seed_data.py` |

Do not reuse anything from the synthetic dataset as a real signing key: its key material can be reproduced by anyone with the repository.

## Security tests that exist

Counts are from the collected suite on 2026-11-11 (see [backend-testing.md](backend-testing.md)).

| File | Tests | What they cover |
|---|---|---|
| `backend/tests/unit/test_security_and_crypto.py` | 13 | Password round trip, malformed hashes failing closed, weak-secret rejection, JWT round trip, expiry, bad signatures, canonical JSON determinism, Ed25519 valid and invalid signatures |
| `backend/tests/integration/test_api_workflows.py` | 11 | Deny by default, role boundaries, learner isolation, public disclosure limits, expired and inactive tokens, concurrent award uniqueness, full lifecycle including tamper detection and revocation |
| `backend/tests/integration/test_issuance_business_rules.py` | 27 | Issuance preconditions: enrollment, completion before issue, future dates, empty rules |
| `backend/tests/integration/test_api_input_safety.py` | 53 | Malformed input returns `4xx`, never `5xx` |

These are functional tests written by the developers of the system. They are not a penetration test.

## Limitations

| # | Limitation | Consequence |
|---|---|---|
| 1 | No rate limiting or lockout on login or on public verification | Password guessing and credential-ID enumeration are not slowed |
| 2 | No request body size limit in the application | A very large JSON body is read into memory before validation |
| 3 | The private signing key is an environment variable | Anyone who can read the process environment or the `.env` file can sign credentials. There is no HSM, KMS or vault integration. |
| 4 | One signing key is configured per process | Key rotation needs a configuration change and a restart |
| 5 | Revoking a signing key makes all credentials it signed `UNVERIFIABLE` | There is no way to keep earlier credentials valid while distrusting later ones |
| 6 | No trusted timestamp | `issued_at` is the issuer's own claim; the system cannot prove to a third party when a credential was signed |
| 7 | JWT is stored in browser `localStorage` (`credential_access_token`) | A cross-site scripting flaw in the frontend would expose the token |
| 8 | No token revocation, refresh or logout on the server | A stolen token works until it expires (30 minutes by default) |
| 9 | No TLS in the provided setup | Compose serves plain HTTP on ports 8000 and 5173; tokens and passwords travel unencrypted unless a TLS proxy is added |
| 10 | No user or role administration API | Accounts are created by a script that reads a password from the environment; there is no password change or reset |
| 11 | Audit immutability is by convention | The application never updates or deletes audit rows, but the database does not prevent it (no trigger, no restricted role). The application connects as a single database user with full rights. |
| 12 | Logins and denied requests are not audited | Failed sign-in attempts leave no record |
| 13 | Administrators are not scoped | Any administrator can act on any learner, course or credential |
| 14 | `GET /health` does not check the database | It cannot be used to detect a database outage |
| 15 | Development servers in the containers | The backend image runs `uvicorn --reload` and the frontend image runs the Vite dev server |
| 16 | Backend dependencies are version ranges, not exact pins | `backend/requirements.txt` uses ranges such as `fastapi>=0.115,<1.0` and there is no lock file, so two installs can differ. `cryptography` is imported directly but is declared only through the `python-jose[cryptography]` extra. No dependency scan has been run. |
| 17 | Role matrix is an assumption (IA-16) | It has not been approved as policy |
| 18 | Portable payloads stop verifying after key rotation | Once a key is retired, a portable payload it signed returns `UNVERIFIABLE`, because trust for a portable payload is checked at the current time. Verification by credential ID still returns `VALID`. A holder's exported file therefore loses its value at the next rotation. |

## Before production use

This list is a starting point, not a complete hardening guide.

1. Commission an independent security review and penetration test.
2. Move the private key into a key-management service or HSM; plan rotation and compromise response.
3. Terminate TLS in front of both services; set `CORS_ORIGINS` to the real origin.
4. Add rate limiting and lockout for login; add rate limiting for public verification.
5. Add a request size limit at the proxy or in the application.
6. Replace the script-based account creation with managed identity (SSO or an administration workflow with password reset).
7. Give the application a database role that cannot `UPDATE` or `DELETE` on `audit_events`, `credentials`, `revocations` and `eligibility_decisions`, or enforce this with triggers.
8. Audit authentication events and denied requests.
9. Build production images: no `--reload`, static frontend build behind a web server, non-root user.
10. Pin exact dependency versions, declare `cryptography` directly, and scan dependencies.
11. Decide and approve the role matrix, retention periods and revocation policy with the product owner.
12. Move the token out of `localStorage` or add a strict Content Security Policy.
