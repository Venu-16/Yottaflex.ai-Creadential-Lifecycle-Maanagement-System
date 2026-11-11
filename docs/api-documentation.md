# API Documentation

Reference for every HTTP operation the backend exposes: **48 operations on 40 paths**. This file is generated from the running FastAPI application, so paths, roles, parameters and schemas match the code. Every example request and response was recorded from a real run of the API against an empty PostgreSQL test database on 2026-11-11; identifiers and timestamps will differ on your machine.

Related documents: [credential lifecycle](credential-lifecycle.md), [security](security.md), [database schema](database/database-schema.md).

## Contents

- [Operation index](#operation-index)
- [Conventions](#conventions)
- [System](#system)
- [Authentication](#authentication)
- [Learners](#learners)
- [Courses](#courses)
- [Issuers and signing keys](#issuers-and-signing-keys)
- [Credential rules](#credential-rules)
- [Enrollments, completions and assessment attempts](#enrollments-completions-and-assessment-attempts)
- [Eligibility](#eligibility)
- [Credentials](#credentials)
- [Public verification](#public-verification)
- [Revocation](#revocation)
- [Audit](#audit)
- [Reports and analytics](#reports-and-analytics)
- [Schemas](#schemas)

## Operation index

| # | Method | Path | Authentication | Roles |
|---|---|---|---|---|
| 1 | `GET` | [`/health`](#get-health) | none | public |
| 2 | `POST` | [`/api/v1/auth/login`](#post-apiv1authlogin) | none | public |
| 3 | `GET` | [`/api/v1/auth/me`](#get-apiv1authme) | Bearer | any authenticated |
| 4 | `GET` | [`/api/v1/learners`](#get-apiv1learners) | Bearer | Academic, Platform |
| 5 | `POST` | [`/api/v1/learners`](#post-apiv1learners) | Bearer | Academic, Platform |
| 6 | `GET` | [`/api/v1/learners/{learner_id}`](#get-apiv1learnerslearner_id) | Bearer | Academic, Platform |
| 7 | `PATCH` | [`/api/v1/learners/{learner_id}`](#patch-apiv1learnerslearner_id) | Bearer | Academic, Platform |
| 8 | `GET` | [`/api/v1/learners/me/credentials`](#get-apiv1learnersmecredentials) | Bearer | Learner |
| 9 | `GET` | [`/api/v1/courses`](#get-apiv1courses) | Bearer | Academic, Platform |
| 10 | `POST` | [`/api/v1/courses`](#post-apiv1courses) | Bearer | Academic, Platform |
| 11 | `PATCH` | [`/api/v1/courses/{course_id}`](#patch-apiv1coursescourse_id) | Bearer | Academic, Platform |
| 12 | `GET` | [`/api/v1/issuers`](#get-apiv1issuers) | Bearer | Academic, Platform |
| 13 | `POST` | [`/api/v1/issuers`](#post-apiv1issuers) | Bearer | Academic, Platform |
| 14 | `PATCH` | [`/api/v1/issuers/{issuer_code}`](#patch-apiv1issuersissuer_code) | Bearer | Academic, Platform |
| 15 | `POST` | [`/api/v1/issuers/{issuer_code}/signing-keys`](#post-apiv1issuersissuer_codesigning-keys) | Bearer | Platform |
| 16 | `POST` | [`/api/v1/issuers/{issuer_code}/signing-keys/{key_id}/revoke`](#post-apiv1issuersissuer_codesigning-keyskey_idrevoke) | Bearer | Platform |
| 17 | `GET` | [`/api/v1/credential-rules`](#get-apiv1credential-rules) | Bearer | Academic, Platform |
| 18 | `POST` | [`/api/v1/credential-rules`](#post-apiv1credential-rules) | Bearer | Academic, Platform |
| 19 | `POST` | [`/api/v1/credential-rules/{rule_code}/versions`](#post-apiv1credential-rulesrule_codeversions) | Bearer | Academic, Platform |
| 20 | `GET` | [`/api/v1/enrollments`](#get-apiv1enrollments) | Bearer | Academic, Platform |
| 21 | `POST` | [`/api/v1/enrollments`](#post-apiv1enrollments) | Bearer | Academic, Platform |
| 22 | `GET` | [`/api/v1/completions`](#get-apiv1completions) | Bearer | Academic, Platform |
| 23 | `POST` | [`/api/v1/completions`](#post-apiv1completions) | Bearer | Academic, Platform |
| 24 | `PATCH` | [`/api/v1/completions/{completion_id}`](#patch-apiv1completionscompletion_id) | Bearer | Academic, Platform |
| 25 | `GET` | [`/api/v1/assessment-attempts`](#get-apiv1assessment-attempts) | Bearer | Academic, Platform |
| 26 | `POST` | [`/api/v1/assessment-attempts`](#post-apiv1assessment-attempts) | Bearer | Academic, Platform |
| 27 | `POST` | [`/api/v1/eligibility/evaluate`](#post-apiv1eligibilityevaluate) | Bearer | Academic, Platform |
| 28 | `POST` | [`/api/v1/credentials/issue`](#post-apiv1credentialsissue) | Bearer | Academic |
| 29 | `GET` | [`/api/v1/credentials`](#get-apiv1credentials) | Bearer | Academic, Platform |
| 30 | `GET` | [`/api/v1/credentials/{credential_id}`](#get-apiv1credentialscredential_id) | Bearer | Academic, Platform |
| 31 | `GET` | [`/api/v1/credentials/{credential_id}/portable`](#get-apiv1credentialscredential_idportable) | Bearer | Academic, Platform |
| 32 | `GET` | [`/api/v1/credentials/{credential_id}/history`](#get-apiv1credentialscredential_idhistory) | Bearer | Academic, Platform |
| 33 | `POST` | [`/api/v1/verification/credential-id`](#post-apiv1verificationcredential-id) | none | public |
| 34 | `POST` | [`/api/v1/verification/portable`](#post-apiv1verificationportable) | none | public |
| 35 | `GET` | [`/api/v1/verification/requests`](#get-apiv1verificationrequests) | Bearer | Academic, Platform |
| 36 | `POST` | [`/api/v1/revocations/{credential_id}`](#post-apiv1revocationscredential_id) | Bearer | Academic |
| 37 | `GET` | [`/api/v1/revocations`](#get-apiv1revocations) | Bearer | Academic, Platform |
| 38 | `GET` | [`/api/v1/audit`](#get-apiv1audit) | Bearer | Academic, Platform |
| 39 | `GET` | [`/api/v1/reports/summary`](#get-apiv1reportssummary) | Bearer | Academic, Platform |
| 40 | `GET` | [`/api/v1/reports/issuance`](#get-apiv1reportsissuance) | Bearer | Academic, Platform |
| 41 | `GET` | [`/api/v1/reports/revocations`](#get-apiv1reportsrevocations) | Bearer | Academic, Platform |
| 42 | `GET` | [`/api/v1/reports/verification`](#get-apiv1reportsverification) | Bearer | Academic, Platform |
| 43 | `GET` | [`/api/v1/reports/overview`](#get-apiv1reportsoverview) | Bearer | Academic, Platform |
| 44 | `GET` | [`/api/v1/reports/credential-lifecycle`](#get-apiv1reportscredential-lifecycle) | Bearer | Academic, Platform |
| 45 | `GET` | [`/api/v1/reports/verification-analytics`](#get-apiv1reportsverification-analytics) | Bearer | Academic, Platform |
| 46 | `GET` | [`/api/v1/reports/academic-analytics`](#get-apiv1reportsacademic-analytics) | Bearer | Academic, Platform |
| 47 | `GET` | [`/api/v1/reports/data-quality`](#get-apiv1reportsdata-quality) | Bearer | Academic, Platform |
| 48 | `GET` | [`/api/v1/reports/performance`](#get-apiv1reportsperformance) | Bearer | Academic, Platform |

## Conventions

### Base URL and interactive documentation

| Item | Value |
|---|---|
| Base URL (local) | `http://localhost:8000` |
| API prefix | `/api/v1` (all routes except `GET /health`) |
| Swagger UI | `http://localhost:8000/docs` |
| OpenAPI document | `http://localhost:8000/openapi.json` (OpenAPI 3.1.0) |
| Content type | `application/json` for request and response bodies |

### Sending the access token

Obtain a token from `POST /api/v1/auth/login` and send it on every protected request:

```http
Authorization: Bearer <access_token>
```

The examples below assume the token is in a shell variable:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"principal_key":"<account>","password":"<password>"}' | jq -r .access_token)
```

### Roles

Six role codes exist in `backend/app/core/roles.py`. Only three of them are accepted by any route other than `GET /auth/me`.

| Role | What the API allows |
|---|---|
| `PLATFORM_ADMINISTRATOR` | Everything an Academic Administrator can read and manage, plus signing-key registration and revocation. **Cannot** issue or revoke credentials. |
| `ACADEMIC_ADMINISTRATOR` | All management, reporting and audit routes, plus credential issuance and revocation. **Cannot** register or revoke signing keys. |
| `LEARNER` | `GET /auth/me` and `GET /learners/me/credentials` only. |
| `INSTRUCTOR`, `SUPPORT_STAFF`, `THIRD_PARTY_VERIFIER` | `GET /auth/me` only. No route grants these roles anything else. Verification is public and needs no account. |

### Common status codes

| Status | Meaning | Body |
|---|---|---|
| `200` / `201` | Success. `201` is used by the create routes and by issuance. | The documented response |
| `400` | `Idempotency-Key` length outside 8 to 200 characters | `{"detail": "..."}` |
| `401` | Missing, malformed, invalid or expired token; inactive account; wrong login | `{"detail": "Bearer token required."}` or `{"detail": "Invalid or expired access token."}` |
| `403` | Authenticated, but the account lacks a required role | `{"detail": "The authenticated user lacks the required role."}` |
| `404` | The referenced record does not exist or is archived | `{"detail": "..."}` |
| `409` | Conflict with existing state or a database constraint | `{"detail": "..."}` |
| `422` | Validation failure. Two body shapes exist (see below). | See below |
| `503` | Signing material or a configured report file is unavailable | `{"detail": "..."}` |

**Two `422` shapes.** Schema validation by FastAPI returns a list:

```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": [
        "body",
        "learner_id"
      ],
      "msg": "String should match pattern '^LRN-[0-9]{6}$'",
      "input": "42",
      "ctx": {
        "pattern": "^LRN-[0-9]{6}$"
      }
    }
  ]
}
```

Business-rule validation by the services returns a string:

```json
{
  "detail": "completed_at cannot be in the future."
}
```

Clients must handle both. The frontend does (`getErrorMessage` in `frontend/src/services/api.js`).

### Pagination

List routes take `limit` (1 to 100, default 50) and `offset` (0 to 1,000,000,000, default 0). They return a bare JSON array with no total count and no next-page link. An `offset` above the maximum returns `422`.

### Input rules that apply to every `/api/v1` route

| Rule | Result when violated |
|---|---|
| No NUL character (`\u0000`) in the path, the query string or any JSON string | `422` `{"detail": "Request contains an unsupported NUL character."}` |
| Request timestamps must include a timezone | `422` `<field> must include a timezone.` |
| Request timestamps must fall in the years 1900 to 2999 | `422` (schema validation) |
| Report dates (`date_from`, `date_to`) must fall in the years 1900 to 2999, in order, and span at most 10 years | `422` |

### Identifiers

| Identifier | Format | Where it is used |
|---|---|---|
| Internal ID | UUID | `id` fields; path values for learners, courses and completions; `learner_id` and `course_id` in request bodies |
| Learner ID | `LRN-NNNNNN` | Display and audit references; signed payload |
| Credential ID | `CRD-YYYY-NNNNNN` | Path values for credential, portable, history and revocation routes; public verification |
| Verification ID | `VER-YYYY-NNNNNN` | Receipt for each verification request |

> In request bodies, `learner_id` means the learner's internal **UUID**. In the `LearnerResponse` and in the signed payload, `learner_id` is the `LRN-NNNNNN` identifier. The field name is shared; the value type differs.

## System

### `GET /health`

**Purpose.** Report that the API process is running.

| Authentication | Roles | Success status |
|---|---|---|
| None (public) | Not applicable | `200` |

Liveness only. It returns a fixed body and does not query the database, so it stays `200` when PostgreSQL is down.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** object

**Error cases.** None defined.

**Example request**

```bash
curl -s "http://localhost:8000/health"
```

**Example response (`200`)**

```json
{
  "status": "ok"
}
```

## Authentication

### `POST /api/v1/auth/login`

**Purpose.** Exchange credentials for a JWT.

| Authentication | Roles | Success status |
|---|---|---|
| None (public) | Not applicable | `200` |

The same `401` message is returned for an unknown account, a wrong password, and an inactive account. The token is an HS256 JWT with `sub` (user UUID), `iat` and `exp`; lifetime is `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30). There is no refresh or logout endpoint.

**Parameters.** None.

**Request body.** [`LoginRequest`](#loginrequest)

**Response body (`200`).** [`TokenResponse`](#tokenresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Invalid username or password. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"principal_key": "academic-admin@example.test", "password": "<local demo password>"}'
```

**Example response (`200`)**

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer"
}
```

**Further example: wrong password**

```bash
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"principal_key": "academic-admin@example.test", "password": "wrong-password-000"}'
```

Response (`401`):

```json
{
  "detail": "Invalid username or password."
}
```

### `GET /api/v1/auth/me`

**Purpose.** Return the authenticated user.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | Any authenticated, active account | `200` |

Roles are read from `user_roles` on every request, so a role change takes effect without a new token.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** [`UserResponse`](#userresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "id": "3c4dd050-d8df-4260-a416-7dec25095b3c",
  "principal_key": "academic-admin@example.test",
  "display_name": "Academic Admin",
  "is_active": true,
  "roles": [
    "ACADEMIC_ADMINISTRATOR"
  ]
}
```

**Further example: no token**

```bash
curl -s "http://localhost:8000/api/v1/auth/me"
```

Response (`401`):

```json
{
  "detail": "Bearer token required."
}
```

**Further example: invalid token**

```bash
curl -s "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer not-a-valid-token"
```

Response (`401`):

```json
{
  "detail": "Invalid or expired access token."
}
```

## Learners

### `GET /api/v1/learners`

**Purpose.** List learners.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Ordered by `learner_id`. Archived learners are included; check `archived_at`.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`LearnerResponse`](#learnerresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/learners?limit=2&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
    "learner_id": "LRN-000001",
    "display_name": "Asha Verma",
    "user_id": "3652e3b6-31c6-454a-bc2d-3d55d29e8e1e",
    "archived_at": null
  },
  {
    "id": "0ce9f96e-d66f-438d-9a69-8fbf44fd7b25",
    "learner_id": "LRN-000042",
    "display_name": "Ravi Kumar",
    "user_id": null,
    "archived_at": null
  }
]
```

**Further example: a role without access (Instructor)**

```bash
curl -s "http://localhost:8000/api/v1/learners" \
  -H "Authorization: Bearer $TOKEN"
```

Response (`403`):

```json
{
  "detail": "The authenticated user lacks the required role."
}
```

### `POST /api/v1/learners`

**Purpose.** Create a learner.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

`learner_id` is optional. When omitted, the next `LRN-NNNNNN` value is allocated. `user_id` links the learner to a login account so that account can use `GET /learners/me/credentials`; it can only be set here, because `LearnerUpdate` has no `user_id` field.

**Parameters.** None.

**Request body.** [`LearnerCreate`](#learnercreate)

**Response body (`201`).** [`LearnerResponse`](#learnerresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Linked user was not found. |
| `409` | Learner ID sequence is exhausted.<br>The requested change conflicts with an existing record or database constraint. |
| `422` | Learner ID must match LRN-000001.<br>Learner display name cannot be empty.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/learners" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Asha Verma", "user_id": "3652e3b6-31c6-454a-bc2d-3d55d29e8e1e"}'
```

**Example response (`201`)**

```json
{
  "id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "learner_id": "LRN-000001",
  "display_name": "Asha Verma",
  "user_id": "3652e3b6-31c6-454a-bc2d-3d55d29e8e1e",
  "archived_at": null
}
```

**Further example: malformed learner ID**

```bash
curl -s -X POST "http://localhost:8000/api/v1/learners" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "42", "display_name": "Bad Id"}'
```

Response (`422`):

```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": [
        "body",
        "learner_id"
      ],
      "msg": "String should match pattern '^LRN-[0-9]{6}$'",
      "input": "42",
      "ctx": {
        "pattern": "^LRN-[0-9]{6}$"
      }
    }
  ]
}
```

### `GET /api/v1/learners/{learner_id}`

**Purpose.** Retrieve a learner profile.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

The path value is the learner's internal UUID (`id`), not the `LRN-NNNNNN` identifier.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `learner_id` | path | string (uuid) | yes |  |

**Request body.** None.

**Response body (`200`).** [`LearnerResponse`](#learnerresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Learner was not found. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/learners/10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "learner_id": "LRN-000001",
  "display_name": "Asha Verma",
  "user_id": "3652e3b6-31c6-454a-bc2d-3d55d29e8e1e",
  "archived_at": null
}
```

**Further example: unknown learner**

```bash
curl -s "http://localhost:8000/api/v1/learners/00000000-0000-4000-8000-000000000000" \
  -H "Authorization: Bearer $TOKEN"
```

Response (`404`):

```json
{
  "detail": "Learner was not found."
}
```

### `PATCH /api/v1/learners/{learner_id}`

**Purpose.** Update a learner profile without changing its external identifier.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

`archived: true` sets `archived_at`; `archived: false` clears it. An archived learner cannot be enrolled, evaluated, or issued a credential (`404 Active learner was not found.`). The external `learner_id` cannot be changed.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `learner_id` | path | string (uuid) | yes |  |

**Request body.** [`LearnerUpdate`](#learnerupdate)

**Response body (`200`).** [`LearnerResponse`](#learnerresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Learner was not found. |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Learner display name cannot be empty.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/learners/0ce9f96e-d66f-438d-9a69-8fbf44fd7b25" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Ravi K. Kumar"}'
```

**Example response (`200`)**

```json
{
  "id": "0ce9f96e-d66f-438d-9a69-8fbf44fd7b25",
  "learner_id": "LRN-000042",
  "display_name": "Ravi K. Kumar",
  "user_id": null,
  "archived_at": null
}
```

**Further example: archive a learner**

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/learners/0ce9f96e-d66f-438d-9a69-8fbf44fd7b25" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"archived": true}'
```

Response (`200`):

```json
{
  "id": "0ce9f96e-d66f-438d-9a69-8fbf44fd7b25",
  "learner_id": "LRN-000042",
  "display_name": "Ravi K. Kumar",
  "user_id": null,
  "archived_at": "2026-11-11T12:36:19.403562Z"
}
```

### `GET /api/v1/learners/me/credentials`

**Purpose.** List credentials belonging to the authenticated learner.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `LEARNER` | `200` |

Only the `LEARNER` role is accepted; administrators receive `403`. The account must be linked to a learner through `learners.user_id`.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`CredentialResponse`](#credentialresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | No learner profile is linked to this account. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/learners/me/credentials" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "2d5b18bc-724e-4d5c-a75c-745935a171c4",
    "credential_id": "CRD-2026-000001",
    "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
    "issuer_id": "72ba20f2-2806-4ad1-9858-e0cfb47153f7",
    "rule_version_id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
    "issued_at": "2026-11-11T12:36:18.948349Z",
    "payload_version": "credential-v1",
    "sha256_digest": "a68054766b4212ffd3dd66982d954c16b7ffadd70f11624b2966e163344ee676",
    "signature_algorithm": "Ed25519",
    "signing_key_id": "c2b2c7f4-bea4-4594-8635-28c9e40a5e9e",
    "replacement_of_credential_id": null
  }
]
```

**Further example: an administrator calling the learner-only route**

```bash
curl -s "http://localhost:8000/api/v1/learners/me/credentials" \
  -H "Authorization: Bearer $TOKEN"
```

Response (`403`):

```json
{
  "detail": "The authenticated user lacks the required role."
}
```

## Courses

### `GET /api/v1/courses`

**Purpose.** List courses.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Ordered by `course_code`.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`CourseResponse`](#courseresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/courses?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "f5033ba6-df79-4853-abac-57fca879ed6a",
    "course_code": "PY-101",
    "title": "Python Fundamentals (2026)",
    "description": "Introductory programming course.",
    "status": "active",
    "effective_from": "2026-08-13T12:36:18Z",
    "effective_to": null
  }
]
```

### `POST /api/v1/courses`

**Purpose.** Create a course.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

`status` must be `active`, `inactive` or `archived`.

**Parameters.** None.

**Request body.** [`CourseCreate`](#coursecreate)

**Response body (`201`).** [`CourseResponse`](#courseresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Course code and title cannot be empty.<br>Course effective_to must be later than effective_from.<br>Course status is invalid.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/courses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"course_code": "PY-101", "title": "Python Fundamentals", "description": "Introductory programming course.", "status": "active", "effective_from": "2026-08-13T12:36:18+00:00"}'
```

**Example response (`201`)**

```json
{
  "id": "f5033ba6-df79-4853-abac-57fca879ed6a",
  "course_code": "PY-101",
  "title": "Python Fundamentals",
  "description": "Introductory programming course.",
  "status": "active",
  "effective_from": "2026-08-13T12:36:18Z",
  "effective_to": null
}
```

**Further example: duplicate course code**

```bash
curl -s -X POST "http://localhost:8000/api/v1/courses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"course_code": "PY-101", "title": "Duplicate"}'
```

Response (`409`):

```json
{
  "detail": "The requested change conflicts with an existing record."
}
```

### `PATCH /api/v1/courses/{course_id}`

**Purpose.** Update catalog metadata while retaining the course record.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

`course_code` cannot be changed. There is no `GET /courses/{course_id}` route; read a course from the list.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `course_id` | path | string (uuid) | yes |  |

**Request body.** [`CourseUpdate`](#courseupdate)

**Response body (`200`).** [`CourseResponse`](#courseresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Course was not found. |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Course effective_to must be later than effective_from.<br>Course status is invalid.<br>Course title cannot be empty.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/courses/f5033ba6-df79-4853-abac-57fca879ed6a" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Python Fundamentals (2026)"}'
```

**Example response (`200`)**

```json
{
  "id": "f5033ba6-df79-4853-abac-57fca879ed6a",
  "course_code": "PY-101",
  "title": "Python Fundamentals (2026)",
  "description": "Introductory programming course.",
  "status": "active",
  "effective_from": "2026-08-13T12:36:18Z",
  "effective_to": null
}
```

## Issuers and signing keys

### `GET /api/v1/issuers`

**Purpose.** List credential issuers.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

The response does not list signing keys. There is no endpoint that lists registered keys.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`IssuerResponse`](#issuerresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/issuers?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "72ba20f2-2806-4ad1-9858-e0cfb47153f7",
    "issuer_code": "DEMO-ISSUER",
    "name": "Demo Academy of Technology",
    "status": "active",
    "archived_at": null
  }
]
```

### `POST /api/v1/issuers`

**Purpose.** Create an issuer.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

New issuers are created with status `active`.

**Parameters.** None.

**Request body.** [`IssuerCreate`](#issuercreate)

**Response body (`201`).** [`IssuerResponse`](#issuerresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Issuer code and name are required.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/issuers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"issuer_code": "DEMO-ISSUER", "name": "Demo Academy"}'
```

**Example response (`201`)**

```json
{
  "id": "72ba20f2-2806-4ad1-9858-e0cfb47153f7",
  "issuer_code": "DEMO-ISSUER",
  "name": "Demo Academy",
  "status": "active",
  "archived_at": null
}
```

**Further example: duplicate issuer code**

```bash
curl -s -X POST "http://localhost:8000/api/v1/issuers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"issuer_code": "DEMO-ISSUER", "name": "Demo Academy"}'
```

Response (`409`):

```json
{
  "detail": "The requested change conflicts with an existing record."
}
```

### `PATCH /api/v1/issuers/{issuer_code}`

**Purpose.** Update an issuer profile with an audit snapshot.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

`status` must be `active`, `suspended` or `archived`. An archived issuer cannot be edited again. The change is audited as `issuer.profile_updated` with the previous values.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `issuer_code` | path | string | yes |  |

**Request body.** [`IssuerUpdate`](#issuerupdate)

**Response body (`200`).** [`IssuerResponse`](#issuerresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Issuer was not found. |
| `409` | Archived issuer profiles cannot be reactivated or edited.<br>The requested change conflicts with an existing record or database constraint. |
| `422` | Issuer name cannot be empty.<br>Issuer status is invalid.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/issuers/DEMO-ISSUER" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo Academy of Technology"}'
```

**Example response (`200`)**

```json
{
  "id": "72ba20f2-2806-4ad1-9858-e0cfb47153f7",
  "issuer_code": "DEMO-ISSUER",
  "name": "Demo Academy of Technology",
  "status": "active",
  "archived_at": null
}
```

### `POST /api/v1/issuers/{issuer_code}/signing-keys`

**Purpose.** Register an issuer public signing key.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `PLATFORM_ADMINISTRATOR` | `201` |

Registers the **public** half of an Ed25519 key pair (raw 32 bytes, base64). The API never receives or stores a private key. The response `fingerprint_sha256` is the SHA-256 of the public key. To be used for issuance, the `key_id` must equal `CREDENTIAL_SIGNING_KEY_ID` and the public key must match `CREDENTIAL_SIGNING_PRIVATE_KEY`. To rotate, pass the UUID of the current active key in `supersedes_key_id`: the old key becomes `retired` and its `valid_until` is set to the new key's `valid_from`, which must be later than the old key's `valid_from`. After a rotation, credentials signed with the old key still verify by credential ID, but their portable payloads verify as `UNVERIFIABLE`.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `issuer_code` | path | string | yes |  |

**Request body.** [`SigningKeyCreate`](#signingkeycreate)

**Response body (`201`).** object

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Active issuer was not found. |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Ed25519 public keys must contain exactly 32 bytes.<br>Key valid_until must be later than valid_from.<br>Only Ed25519 issuer keys are supported.<br>Public key must be valid base64.<br>Rotation must reference a later key belonging to the same active issuer.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/issuers/DEMO-ISSUER/signing-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key_id": "demo-key-2026", "public_key_base64": "BPwOcnTlXRxS+qhs/7XmPTZbPwYQxyDw9QMDRFeO8PE=", "algorithm": "Ed25519", "valid_from": "2026-11-10T12:36:18+00:00"}'
```

**Example response (`201`)**

```json
{
  "id": "c2b2c7f4-bea4-4594-8635-28c9e40a5e9e",
  "issuer_code": "DEMO-ISSUER",
  "key_id": "demo-key-2026",
  "algorithm": "Ed25519",
  "fingerprint_sha256": "d1b4146fee3a573409bcbefee5e2a135ed465730ac1438ef9502aa816b18d5cd",
  "status": "active"
}
```

**Further example: Academic Administrator attempting key registration**

```bash
curl -s -X POST "http://localhost:8000/api/v1/issuers/DEMO-ISSUER/signing-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key_id": "x", "public_key_base64": "BPwOcnTlXRxS+qhs/7XmPTZbPwYQxyDw9QMDRFeO8PE=", "valid_from": "2026-11-11T12:36:18+00:00"}'
```

Response (`403`):

```json
{
  "detail": "The authenticated user lacks the required role."
}
```

**Further example: public key that is not 32 bytes**

```bash
curl -s -X POST "http://localhost:8000/api/v1/issuers/DEMO-ISSUER/signing-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key_id": "short-key", "public_key_base64": "AAAA", "valid_from": "2026-11-11T12:36:18+00:00"}'
```

Response (`422`):

```json
{
  "detail": "Ed25519 public keys must contain exactly 32 bytes."
}
```

### `POST /api/v1/issuers/{issuer_code}/signing-keys/{key_id}/revoke`

**Purpose.** Revoke an issuer public key while preserving its historical record.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `PLATFORM_ADMINISTRATOR` | `200` |

Sets the key status to `revoked`. **Consequence, confirmed by a recorded run:** every credential signed with that key then verifies as `UNVERIFIABLE` (`issuer_trust_result: untrusted`), and issuance returns `503` until a new active key is registered and configured.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `issuer_code` | path | string | yes |  |
| `key_id` | path | string | yes |  |

**Request body.** None.

**Response body (`200`).** object

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Issuer signing key was not found. |
| `409` | Issuer signing key is already revoked.<br>The requested change conflicts with an existing record or database constraint. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/issuers/DEMO-ISSUER/signing-keys/demo-key-2025/revoke" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "issuer_code": "DEMO-ISSUER",
  "key_id": "demo-key-2025",
  "status": "revoked"
}
```

**Further example: key already revoked**

```bash
curl -s -X POST "http://localhost:8000/api/v1/issuers/DEMO-ISSUER/signing-keys/demo-key-2025/revoke" \
  -H "Authorization: Bearer $TOKEN"
```

Response (`409`):

```json
{
  "detail": "Issuer signing key is already revoked."
}
```

**Further example: verifying a credential after its signing key was revoked**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/credential-id?credential_id=CRD-2026-000001"
```

Response (`200`):

```json
{
  "verification_id": "VER-2026-000008",
  "overall_result": "UNVERIFIABLE",
  "integrity_result": "valid",
  "issuer_trust_result": "untrusted",
  "lifecycle_result": "revoked",
  "credential_id": "CRD-2026-000001",
  "issuer_code": "DEMO-ISSUER",
  "message": "Issuer trust, signing key, or authoritative lifecycle status could not be established."
}
```

## Credential rules

### `GET /api/v1/credential-rules`

**Purpose.** List credential rule versions.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Returns one item per rule **version**, not per rule.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`RuleResponse`](#ruleresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/credential-rules?limit=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "355aa3a0-a8d4-4920-b35c-e342e8c1ee1f",
    "rule_id": "f61794fd-1efc-4a70-b8f7-50160c273eae",
    "version_number": 2,
    "credential_scope_id": "0f85dbfe-f3af-48c7-9404-14dc1ccc2467",
    "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
    "rule_code": "PY-101-CERT",
    "name": "Python Fundamentals Certificate",
    "criteria": {
      "minimum_score": 75,
      "requires_completion": true,
      "attempt_selection_policy": "latest_graded"
    },
    "attempt_selection_policy": "latest_graded",
    "effective_from": "2027-05-10T12:36:18Z",
    "effective_to": null,
    "status": "active"
  },
  {
    "id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
    "rule_id": "f61794fd-1efc-4a70-b8f7-50160c273eae",
    "version_number": 1,
    "credential_scope_id": "0f85dbfe-f3af-48c7-9404-14dc1ccc2467",
    "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
    "rule_code": "PY-101-CERT",
    "name": "Python Fundamentals Certificate",
    "criteria": {
      "score_scale": "0-100",
      "minimum_score": 70,
      "requires_completion": true,
      "attempt_selection_policy": "latest_graded"
    },
    "attempt_selection_policy": "latest_graded",
    "effective_from": "2026-10-12T12:36:18Z",
    "effective_to": "2027-05-10T12:36:18Z",
    "status": "active"
  }
]
```

### `POST /api/v1/credential-rules`

**Purpose.** Create a credential rule and its first immutable version.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

Creates the rule, its credential scope for the course, and version 1. `criteria` accepts only `requires_completion` (boolean, default true), `minimum_score` (0 to 100), `score_scale` (`0-100`) and `attempt_selection_policy` (`latest_graded`). A rule that requires neither completion nor a minimum score is rejected.

**Parameters.** None.

**Request body.** [`RuleCreate`](#rulecreate)

**Response body (`201`).** [`RuleResponse`](#ruleresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Active course was not found. |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | A credential rule must require course completion, a minimum score, or both.<br>MVP score thresholds must use the 0-100 scale.<br>MVP supports only the latest_graded attempt policy.<br>Rule code and name cannot be empty.<br>Rule criteria contain unsupported fields.<br>minimum_score must be between 0 and 100.<br>minimum_score must be numeric.<br>requires_completion must be boolean.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credential-rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rule_code": "PY-101-CERT", "name": "Python Fundamentals Certificate", "description": "Completion plus a final score of at least 70.", "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a", "criteria": {"requires_completion": true, "minimum_score": 70, "score_scale": "0-100"}, "attempt_selection_policy": "latest_graded", "effective_from": "2026-10-12T12:36:18+00:00"}'
```

**Example response (`201`)**

```json
{
  "id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
  "rule_id": "f61794fd-1efc-4a70-b8f7-50160c273eae",
  "version_number": 1,
  "credential_scope_id": "0f85dbfe-f3af-48c7-9404-14dc1ccc2467",
  "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
  "rule_code": "PY-101-CERT",
  "name": "Python Fundamentals Certificate",
  "criteria": {
    "requires_completion": true,
    "minimum_score": 70,
    "score_scale": "0-100",
    "attempt_selection_policy": "latest_graded"
  },
  "attempt_selection_policy": "latest_graded",
  "effective_from": "2026-10-12T12:36:18Z",
  "effective_to": null,
  "status": "active"
}
```

**Further example: rule with no completion or score requirement**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credential-rules" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rule_code": "EMPTY-RULE", "name": "No requirements", "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a", "criteria": {"requires_completion": false}, "effective_from": "2026-11-10T12:36:18+00:00"}'
```

Response (`422`):

```json
{
  "detail": "A credential rule must require course completion, a minimum score, or both."
}
```

### `POST /api/v1/credential-rules/{rule_code}/versions`

**Purpose.** Create a new immutable version of an existing credential rule.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

Versions are immutable. The new `effective_from` must be later than the previous version's; the previous version's `effective_to` is closed at that time. Evaluation uses the active version in effect at evaluation time.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `rule_code` | path | string | yes |  |

**Request body.** [`RuleVersionCreate`](#ruleversioncreate)

**Response body (`201`).** [`RuleResponse`](#ruleresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Active course was not found.<br>Credential rule was not found. |
| `409` | Credential rule has no prior version.<br>The requested change conflicts with an existing record or database constraint. |
| `422` | A credential rule must require course completion, a minimum score, or both.<br>MVP score thresholds must use the 0-100 scale.<br>MVP supports only the latest_graded attempt policy.<br>New rule version must start after the previous version.<br>New version cannot overlap the previous effective period.<br>Rule criteria contain unsupported fields.<br>minimum_score must be between 0 and 100.<br>minimum_score must be numeric.<br>requires_completion must be boolean.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credential-rules/PY-101-CERT/versions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"course_id": "f5033ba6-df79-4853-abac-57fca879ed6a", "criteria": {"requires_completion": true, "minimum_score": 75}, "attempt_selection_policy": "latest_graded", "effective_from": "2027-05-10T12:36:18+00:00"}'
```

**Example response (`201`)**

```json
{
  "id": "355aa3a0-a8d4-4920-b35c-e342e8c1ee1f",
  "rule_id": "f61794fd-1efc-4a70-b8f7-50160c273eae",
  "version_number": 2,
  "credential_scope_id": "0f85dbfe-f3af-48c7-9404-14dc1ccc2467",
  "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
  "rule_code": "PY-101-CERT",
  "name": "Python Fundamentals Certificate",
  "criteria": {
    "requires_completion": true,
    "minimum_score": 75,
    "attempt_selection_policy": "latest_graded"
  },
  "attempt_selection_policy": "latest_graded",
  "effective_from": "2027-05-10T12:36:18Z",
  "effective_to": null,
  "status": "active"
}
```

## Enrollments, completions and assessment attempts

### `GET /api/v1/enrollments`

**Purpose.** List enrollments.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Optional filters `learner_id` and `course_id` are internal UUIDs.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `learner_id` | query | string (uuid), nullable | no |  |
| `course_id` | query | string (uuid), nullable | no |  |
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`EnrollmentResponse`](#enrollmentresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/enrollments?learner_id=10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "e2849751-8ebc-4188-a635-30dc6653a3d8",
    "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
    "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
    "status": "active",
    "enrolled_at": "2026-11-11T12:36:18.691974Z",
    "effective_from": null,
    "effective_to": null
  }
]
```

### `POST /api/v1/enrollments`

**Purpose.** Enroll a learner in a course.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

One active enrollment is allowed per learner and course.

**Parameters.** None.

**Request body.** [`EnrollmentCreate`](#enrollmentcreate)

**Response body (`201`).** [`EnrollmentResponse`](#enrollmentresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Active course was not found.<br>Active learner was not found. |
| `409` | An active enrollment already exists for this learner and course.<br>The requested change conflicts with an existing record or database constraint. |
| `422` | `<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/enrollments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a"}'
```

**Example response (`201`)**

```json
{
  "id": "e2849751-8ebc-4188-a635-30dc6653a3d8",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
  "status": "active",
  "enrolled_at": "2026-11-11T12:36:18.691974Z",
  "effective_from": null,
  "effective_to": null
}
```

**Further example: duplicate enrollment**

```bash
curl -s -X POST "http://localhost:8000/api/v1/enrollments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a"}'
```

Response (`409`):

```json
{
  "detail": "An active enrollment already exists for this learner and course."
}
```

**Further example: archived learner**

```bash
curl -s -X POST "http://localhost:8000/api/v1/enrollments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "0ce9f96e-d66f-438d-9a69-8fbf44fd7b25", "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a"}'
```

Response (`404`):

```json
{
  "detail": "Active learner was not found."
}
```

### `GET /api/v1/completions`

**Purpose.** List course completion records.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `learner_id` | query | string (uuid), nullable | no |  |
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`CompletionResponse`](#completionresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/completions?learner_id=10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673",
    "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
    "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
    "enrollment_id": "e2849751-8ebc-4188-a635-30dc6653a3d8",
    "status": "completed",
    "started_at": "2026-10-22T12:36:18Z",
    "completed_at": "2026-11-09T12:36:18Z",
    "recorded_at": "2026-11-11T12:36:18.732432Z"
  }
]
```

### `POST /api/v1/completions`

**Purpose.** Record course completion status.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

`status` must be `in_progress`, `completed`, `incomplete` or `failed`. `completed_at` is required when the status is `completed` and forbidden otherwise. `completed_at` may not be more than five minutes ahead of the server clock. One completion record is allowed per enrollment (`409` on a second).

**Parameters.** None.

**Request body.** [`CompletionCreate`](#completioncreate)

**Response body (`201`).** [`CompletionResponse`](#completionresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Enrollment was not found. |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Completion status is invalid.<br>completed_at cannot precede started_at.<br>completed_at is allowed only for completed records.<br>completed_at is required for completed records.<br>`<field>` cannot be in the future.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/completions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enrollment_id": "e2849751-8ebc-4188-a635-30dc6653a3d8", "status": "in_progress", "started_at": "2026-10-22T12:36:18+00:00"}'
```

**Example response (`201`)**

```json
{
  "id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
  "enrollment_id": "e2849751-8ebc-4188-a635-30dc6653a3d8",
  "status": "in_progress",
  "started_at": "2026-10-22T12:36:18Z",
  "completed_at": null,
  "recorded_at": "2026-11-11T12:36:18.732432Z"
}
```

### `PATCH /api/v1/completions/{completion_id}`

**Purpose.** Update a completion status while retaining assessment history.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Same status and date rules as creation. Assessment attempts are kept when the status changes.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `completion_id` | path | string (uuid) | yes |  |

**Request body.** [`CompletionStatusUpdate`](#completionstatusupdate)

**Response body (`200`).** [`CompletionResponse`](#completionresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Completion record was not found. |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Completion status is invalid.<br>completed_at cannot precede started_at.<br>completed_at is allowed only for completed records.<br>completed_at is required for completed records.<br>`<field>` cannot be in the future.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/completions/0fe3dbe5-08ce-4f52-890f-870bd2eaa673" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "completed_at": "2026-11-09T12:36:18+00:00"}'
```

**Example response (`200`)**

```json
{
  "id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
  "enrollment_id": "e2849751-8ebc-4188-a635-30dc6653a3d8",
  "status": "completed",
  "started_at": "2026-10-22T12:36:18Z",
  "completed_at": "2026-11-09T12:36:18Z",
  "recorded_at": "2026-11-11T12:36:18.732432Z"
}
```

**Further example: completion dated in the future**

```bash
curl -s -X PATCH "http://localhost:8000/api/v1/completions/0fe3dbe5-08ce-4f52-890f-870bd2eaa673" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "completed_at": "2026-12-11T12:36:18+00:00"}'
```

Response (`422`):

```json
{
  "detail": "completed_at cannot be in the future."
}
```

### `GET /api/v1/assessment-attempts`

**Purpose.** List assessment attempts without collapsing retry history.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Every attempt is returned, including retries; nothing is collapsed.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `completion_record_id` | query | string (uuid), nullable | no |  |
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`AssessmentAttemptResponse`](#assessmentattemptresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/assessment-attempts?completion_record_id=0fe3dbe5-08ce-4f52-890f-870bd2eaa673" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "a5289ee8-cca5-49fd-8e02-505e54ce7d31",
    "completion_record_id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673",
    "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
    "assessment_key": "final-exam",
    "attempt_number": 2,
    "score": "88.0000",
    "score_scale": "0-100",
    "result_code": null,
    "status": "graded",
    "submitted_at": "2026-11-08T12:36:18Z",
    "graded_at": "2026-11-09T11:36:18Z",
    "supersedes_attempt_id": null
  },
  {
    "id": "f962cffe-9b20-400c-9307-bed92875aa84",
    "completion_record_id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673",
    "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
    "assessment_key": "final-exam",
    "attempt_number": 1,
    "score": "55.0000",
    "score_scale": "0-100",
    "result_code": null,
    "status": "graded",
    "submitted_at": "2026-11-06T12:36:18Z",
    "graded_at": "2026-11-07T12:36:18Z",
    "supersedes_attempt_id": null
  }
]
```

### `POST /api/v1/assessment-attempts`

**Purpose.** Record a new assessment attempt.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `201` |

`attempt_number` is allocated per completion record and `assessment_key`. `status` must be `submitted`, `graded` or `voided`; a `graded` attempt needs `score` and `graded_at`. Scores use the `0-100` scale.

**Parameters.** None.

**Request body.** [`AssessmentAttemptCreate`](#assessmentattemptcreate)

**Response body (`201`).** [`AssessmentAttemptResponse`](#assessmentattemptresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Completion record was not found. |
| `409` | The requested change conflicts with an existing record or database constraint. |
| `422` | Assessment attempt status is invalid.<br>Graded attempts require score and graded_at.<br>Score must be between 0 and 100.<br>Scores must use the declared 0-100 scale.<br>Superseded attempt must belong to this completion.<br>graded_at cannot precede submitted_at.<br>`<field>` must include a timezone.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/assessment-attempts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"completion_record_id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673", "assessment_key": "final-exam", "score": "88", "score_scale": "0-100", "status": "graded", "submitted_at": "2026-11-08T12:36:18+00:00", "graded_at": "2026-11-09T11:36:18+00:00"}'
```

**Example response (`201`)**

```json
{
  "id": "a5289ee8-cca5-49fd-8e02-505e54ce7d31",
  "completion_record_id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "assessment_key": "final-exam",
  "attempt_number": 2,
  "score": "88",
  "score_scale": "0-100",
  "result_code": null,
  "status": "graded",
  "submitted_at": "2026-11-08T12:36:18Z",
  "graded_at": "2026-11-09T11:36:18Z",
  "supersedes_attempt_id": null
}
```

**Further example: score above 100**

```bash
curl -s -X POST "http://localhost:8000/api/v1/assessment-attempts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"completion_record_id": "0fe3dbe5-08ce-4f52-890f-870bd2eaa673", "assessment_key": "final-exam", "score": "140", "status": "graded", "submitted_at": "2026-11-06T12:36:18+00:00", "graded_at": "2026-11-07T12:36:18+00:00"}'
```

Response (`422`):

```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": [
        "body",
        "score"
      ],
      "msg": "Input should be less than or equal to 100",
      "input": "140",
      "ctx": {
        "le": 100
      }
    }
  ]
}
```

## Eligibility

### `POST /api/v1/eligibility/evaluate`

**Purpose.** Evaluate current evidence and persist an immutable eligibility decision.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Every call stores a new immutable row in `eligibility_decisions` (with `eligibility_reasons` and `eligibility_evidence`) and an `eligibility.evaluated` audit event. `outcome` is `eligible`, `ineligible` or `needs_review`. Reason codes: `MISSING_ENROLLMENT`, `MISSING_COMPLETION`, `COURSE_INCOMPLETE`, `COMPLETION_DATE_IN_FUTURE`, `MISSING_ASSESSMENT`, `ASSESSMENT_DATE_IN_FUTURE`, `ASSESSMENT_BELOW_THRESHOLD`, `UNSUPPORTED_ATTEMPT_SELECTION_POLICY`, `RULE_HAS_NO_REQUIREMENTS`. The last two give `needs_review`. Evaluation does not issue a credential.

**Parameters.** None.

**Request body.** [`EligibilityRequest`](#eligibilityrequest)

**Response body (`200`).** [`EligibilityResponse`](#eligibilityresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Active learner was not found.<br>Credential rule was not found. |
| `409` | No effective active version exists for this rule.<br>Rule contains an invalid minimum_score value.<br>Rule minimum_score must be between 0 and 100.<br>The active rule version has no course requirements.<br>The requested change conflicts with an existing record or database constraint.<br>The rule version references unavailable course data. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/eligibility/evaluate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

**Example response (`200`)**

```json
{
  "decision_id": "5383bb60-c4f9-4139-9807-f6a5c3c09afe",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "rule_code": "PY-101-CERT",
  "rule_version_id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
  "outcome": "ineligible",
  "reason_codes": [
    "ASSESSMENT_BELOW_THRESHOLD"
  ],
  "evaluated_at": "2026-11-11T12:36:18.799405Z"
}
```

**Further example: eligible outcome**

```bash
curl -s -X POST "http://localhost:8000/api/v1/eligibility/evaluate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

Response (`200`):

```json
{
  "decision_id": "9bc6808f-45ce-4a66-8275-ab1ddf19716e",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "rule_code": "PY-101-CERT",
  "rule_version_id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
  "outcome": "eligible",
  "reason_codes": [],
  "evaluated_at": "2026-11-11T12:36:18.903062Z"
}
```

**Further example: unknown rule**

```bash
curl -s -X POST "http://localhost:8000/api/v1/eligibility/evaluate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "NO-SUCH-RULE"}'
```

Response (`404`):

```json
{
  "detail": "Credential rule was not found."
}
```

## Credentials

### `POST /api/v1/credentials/issue`

**Purpose.** Evaluate current evidence and issue a signed credential atomically.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR` | `201` |

Runs a fresh eligibility evaluation, then signs and stores the credential in one transaction. The `Idempotency-Key` header is required (8 to 200 characters) and is scoped to the calling user and this operation for 24 hours: a repeat with the same key and body returns the **same credential, again with `201`**; the same key with a different body returns `409`. A key whose earlier attempt was rejected can be reused (the request is evaluated again). A rejection stores the decision and a `credential.issuance_rejected` audit event before returning `422`. Only one credential may exist per learner and course scope.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `Idempotency-Key` | header | string | yes | 8 to 200 characters (checked by the service; `400` otherwise) |

**Request body.** [`IssueRequest`](#issuerequest)

**Response body (`201`).** [`CredentialResponse`](#credentialresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `400` | Idempotency-Key must be between 8 and 200 characters. |
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Active learner was not found.<br>Credential rule was not found. |
| `409` | A credential already occupies this learner and credential-scope award slot.<br>An equivalent issuance request is already in progress.<br>Credential cannot be issued before course completion.<br>Credential scope references an unavailable course.<br>Idempotency record points to a missing credential.<br>Idempotency-Key was already used for a different request.<br>No effective active version exists for this rule.<br>Rule contains an invalid minimum_score value.<br>Rule minimum_score must be between 0 and 100.<br>The active rule version has no course requirements.<br>The requested change conflicts with an existing record or database constraint.<br>The rule version references unavailable course data.<br>Credential ID sequence for `<year>` is exhausted. |
| `422` | Learner is not eligible for issuance: `<reason codes>`<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |
| `503` | Configured Ed25519 private key is invalid.<br>Configured active issuer signing key is not registered.<br>Configured active signing issuer is unavailable.<br>Configured issuer signing key is outside its validity period.<br>Configured private key does not match the registered key.<br>Credential signing failed.<br>Credential signing is unavailable; configure issuer, key ID, and private key.<br>Idempotency record could not be established. |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: issue-asha-py101-attempt-2" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

**Example response (`201`)**

```json
{
  "id": "2d5b18bc-724e-4d5c-a75c-745935a171c4",
  "credential_id": "CRD-2026-000001",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "issuer_id": "72ba20f2-2806-4ad1-9858-e0cfb47153f7",
  "rule_version_id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
  "issued_at": "2026-11-11T12:36:18.948349Z",
  "payload_version": "credential-v1",
  "sha256_digest": "a68054766b4212ffd3dd66982d954c16b7ffadd70f11624b2966e163344ee676",
  "signature_algorithm": "Ed25519",
  "signing_key_id": "c2b2c7f4-bea4-4594-8635-28c9e40a5e9e",
  "replacement_of_credential_id": null
}
```

**Further example: learner not eligible**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: issue-asha-py101-attempt-1" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

Response (`422`):

```json
{
  "detail": "Learner is not eligible for issuance: ASSESSMENT_BELOW_THRESHOLD"
}
```

**Further example: Platform Administrator attempting issuance**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: issue-asha-py101-attempt-2" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

Response (`403`):

```json
{
  "detail": "The authenticated user lacks the required role."
}
```

**Further example: missing `Idempotency-Key` header**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

Response (`422`):

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "header",
        "Idempotency-Key"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

**Further example: `Idempotency-Key` shorter than 8 characters**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: short" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

Response (`400`):

```json
{
  "detail": "Idempotency-Key must be between 8 and 200 characters."
}
```

**Further example: same `Idempotency-Key` with a different body**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: issue-asha-py101-attempt-2" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "0ce9f96e-d66f-438d-9a69-8fbf44fd7b25", "rule_code": "PY-101-CERT"}'
```

Response (`409`):

```json
{
  "detail": "Idempotency-Key was already used for a different request."
}
```

**Further example: learner already holds this credential**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: issue-asha-py101-attempt-3" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

Response (`409`):

```json
{
  "detail": "A credential already occupies this learner and credential-scope award slot."
}
```

**Further example: configured signing key is revoked**

```bash
curl -s -X POST "http://localhost:8000/api/v1/credentials/issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: issue-asha-py101-attempt-9" \
  -H "Content-Type: application/json" \
  -d '{"learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4", "rule_code": "PY-101-CERT"}'
```

Response (`503`):

```json
{
  "detail": "Configured active issuer signing key is not registered."
}
```

### `GET /api/v1/credentials`

**Purpose.** List credentials.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Optional filter `learner_id` is the internal UUID. `sha256_digest` is hex. The response has no status field; revocation state is read from `GET /revocations` or from verification.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `learner_id` | query | string (uuid), nullable | no |  |
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`CredentialResponse`](#credentialresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/credentials?learner_id=10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "2d5b18bc-724e-4d5c-a75c-745935a171c4",
    "credential_id": "CRD-2026-000001",
    "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
    "issuer_id": "72ba20f2-2806-4ad1-9858-e0cfb47153f7",
    "rule_version_id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
    "issued_at": "2026-11-11T12:36:18.948349Z",
    "payload_version": "credential-v1",
    "sha256_digest": "a68054766b4212ffd3dd66982d954c16b7ffadd70f11624b2966e163344ee676",
    "signature_algorithm": "Ed25519",
    "signing_key_id": "c2b2c7f4-bea4-4594-8635-28c9e40a5e9e",
    "replacement_of_credential_id": null
  }
]
```

### `GET /api/v1/credentials/{credential_id}`

**Purpose.** Retrieve credential metadata without exposing assessment evidence.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

The path value is the public identifier (`CRD-YYYY-NNNNNN`).

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `credential_id` | path | string | yes |  |

**Request body.** None.

**Response body (`200`).** [`CredentialResponse`](#credentialresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Credential was not found. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/credentials/CRD-2026-000001" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "id": "2d5b18bc-724e-4d5c-a75c-745935a171c4",
  "credential_id": "CRD-2026-000001",
  "learner_id": "10d9e2cf-b4da-4ff8-b405-567e2b7a5ea4",
  "issuer_id": "72ba20f2-2806-4ad1-9858-e0cfb47153f7",
  "rule_version_id": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
  "issued_at": "2026-11-11T12:36:18.948349Z",
  "payload_version": "credential-v1",
  "sha256_digest": "a68054766b4212ffd3dd66982d954c16b7ffadd70f11624b2966e163344ee676",
  "signature_algorithm": "Ed25519",
  "signing_key_id": "c2b2c7f4-bea4-4594-8635-28c9e40a5e9e",
  "replacement_of_credential_id": null
}
```

**Further example: unknown credential**

```bash
curl -s "http://localhost:8000/api/v1/credentials/CRD-2026-999999" \
  -H "Authorization: Bearer $TOKEN"
```

Response (`404`):

```json
{
  "detail": "Credential was not found."
}
```

### `GET /api/v1/credentials/{credential_id}/portable`

**Purpose.** Return the signed portable credential payload to an authorized caller.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Returns the exact signed payload and the base64 Ed25519 signature. This is the document a holder can pass to a verifier. It is restricted to administrators; a learner cannot download their own portable payload through the API.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `credential_id` | path | string | yes |  |

**Request body.** None.

**Response body (`200`).** [`PortableCredentialResponse`](#portablecredentialresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Credential was not found. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |
| `500` | Stored credential payload is malformed. |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/credentials/CRD-2026-000001/portable" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "payload": {
    "completion": {
      "completed_at": "2026-11-09T12:36:18+00:00"
    },
    "course_code": "PY-101",
    "credential_id": "CRD-2026-000001",
    "issued_at": "2026-11-11T12:36:18.948349+00:00",
    "issuer": {
      "issuer_code": "DEMO-ISSUER",
      "issuer_name": "Demo Academy of Technology"
    },
    "learner_id": "LRN-000001",
    "payload_version": "credential-v1",
    "rule_version": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0",
    "signing_key_id": "demo-key-2026"
  },
  "signature_base64": "uN//hWyhul+LpcEgQfWiQhDKWnzs/Z7h3NBBsFknTloeGI2Zd0BRURy4epqEy76P/hpbprQ0qLfQhF2zvTn+AQ=="
}
```

### `GET /api/v1/credentials/{credential_id}/history`

**Purpose.** Read credential issuance, verification, and revocation history.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Audit events whose target is this credential, oldest first: issuance, each verification, and revocation. `limit` defaults to 100 here; there is no `offset`.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `credential_id` | path | string | yes |  |
| `limit` | query | integer | no | min `1`, max `100`, default `100` |

**Request body.** None.

**Response body (`200`).** array of [`AuditEventResponse`](#auditeventresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Credential was not found. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/credentials/CRD-2026-000001/history" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "33d0eeee-5c6c-4ab0-89aa-5ea1f68c6530",
    "event_type": "credential.issued",
    "outcome": "success",
    "actor_reference": "3c4dd050-d8df-4260-a416-7dec25095b3c",
    "target_type": "credential",
    "target_reference": "CRD-2026-000001",
    "occurred_at": "2026-11-11T12:36:18.931682Z",
    "reason_code": null,
    "event_data": {
      "rule_code": "PY-101-CERT",
      "learner_id": "LRN-000001"
    }
  },
  {
    "id": "88780309-9f86-44da-a570-c48eec967ec2",
    "event_type": "credential.verification",
    "outcome": "valid",
    "actor_reference": "anonymous-verifier",
    "target_type": "credential",
    "target_reference": "CRD-2026-000001",
    "occurred_at": "2026-11-11T12:36:19.039570Z",
    "reason_code": null,
    "event_data": {
      "mode": "credential_id",
      "trust": "trusted",
      "integrity": "valid",
      "lifecycle": "active"
    }
  }
]
```

_The recorded response contained 7 items; the first 2 are shown._

## Public verification

### `POST /api/v1/verification/credential-id`

**Purpose.** Verify a credential ID against the authoritative credential registry.

| Authentication | Roles | Success status |
|---|---|---|
| None (public) | Not applicable | `200` |

Public; no token. The credential ID is a **query parameter**, not a body. A lookup always returns `200`; the result is in `overall_result` (`VALID`, `REVOKED`, `NOT_FOUND`, `INVALID_SIGNATURE`, `TAMPERED`, `UNVERIFIABLE`). The stored payload digest and signature are re-checked on every call. Every call writes a `verification_requests` row and a `credential.verification` audit event. No learner data is returned.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `credential_id` | query | string | yes | min length `1`, max length `15` |

**Request body.** None.

**Response body (`200`).** [`VerificationResponse`](#verificationresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `409` | The requested change conflicts with an existing record or database constraint.<br>Verification ID sequence for `<year>` is exhausted. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/credential-id?credential_id=CRD-2026-000001"
```

**Example response (`200`)**

```json
{
  "verification_id": "VER-2026-000001",
  "overall_result": "VALID",
  "integrity_result": "valid",
  "issuer_trust_result": "trusted",
  "lifecycle_result": "active",
  "credential_id": "CRD-2026-000001",
  "issuer_code": "DEMO-ISSUER",
  "message": "Credential signature and current lifecycle status are valid."
}
```

**Further example: unknown credential ID**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/credential-id?credential_id=CRD-2026-999999"
```

Response (`200`):

```json
{
  "verification_id": "VER-2026-000002",
  "overall_result": "NOT_FOUND",
  "integrity_result": "not_found",
  "issuer_trust_result": "unavailable",
  "lifecycle_result": "unknown",
  "credential_id": "CRD-2026-999999",
  "issuer_code": null,
  "message": "Credential was not found."
}
```

**Further example: revoked credential**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/credential-id?credential_id=CRD-2026-000001"
```

Response (`200`):

```json
{
  "verification_id": "VER-2026-000006",
  "overall_result": "REVOKED",
  "integrity_result": "valid",
  "issuer_trust_result": "trusted",
  "lifecycle_result": "revoked",
  "credential_id": "CRD-2026-000001",
  "issuer_code": "DEMO-ISSUER",
  "message": "Credential signature is valid, but the credential is revoked."
}
```

**Further example: credential ID longer than 15 characters**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/credential-id?credential_id=CRD-2026-0000000001"
```

Response (`422`):

```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": [
        "query",
        "credential_id"
      ],
      "msg": "String should have at most 15 characters",
      "input": "CRD-2026-0000000001",
      "ctx": {
        "max_length": 15
      }
    }
  ]
}
```

### `POST /api/v1/verification/portable`

**Purpose.** Verify a portable signed payload using the issuer public-key registry.

| Authentication | Roles | Success status |
|---|---|---|
| None (public) | Not applicable | `200` |

Public; no token. The payload is canonicalised and its signature is checked against the registered public key named by `payload.issuer.issuer_code` and `payload.signing_key_id`. If the claimed credential exists and the submitted payload differs from the stored one, the result is `TAMPERED`. A payload whose issuer or key is not registered, or whose credential is not in the registry, is `UNVERIFIABLE`. Issuer and key trust is evaluated at the **current time**, because the `issued_at` inside a portable payload is self-asserted. A payload signed with a key that has since been retired by rotation is therefore `UNVERIFIABLE`, while the same credential verified by credential ID is still `VALID`.

**Parameters.** None.

**Request body.** [`PortableVerificationRequest`](#portableverificationrequest)

**Response body (`200`).** [`VerificationResponse`](#verificationresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `409` | The requested change conflicts with an existing record or database constraint.<br>Verification ID sequence for `<year>` is exhausted. |
| `422` | Portable credential payload must contain valid JSON values.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/portable" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"completion": {"completed_at": "2026-11-09T12:36:18+00:00"}, "course_code": "PY-101", "credential_id": "CRD-2026-000001", "issued_at": "2026-11-11T12:36:18.948349+00:00", "issuer": {"issuer_code": "DEMO-ISSUER", "issuer_name": "Demo Academy of Technology"}, "learner_id": "LRN-000001", "payload_version": "credential-v1", "rule_version": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0", "signing_key_id": "demo-key-2026"}, "signature_base64": "uN//hWyhul+LpcEgQfWiQhDKWnzs/Z7h3NBBsFknTloeGI2Zd0BRURy4epqEy76P/hpbprQ0qLfQhF2zvTn+AQ=="}'
```

**Example response (`200`)**

```json
{
  "verification_id": "VER-2026-000003",
  "overall_result": "VALID",
  "integrity_result": "valid",
  "issuer_trust_result": "trusted",
  "lifecycle_result": "active",
  "credential_id": "CRD-2026-000001",
  "issuer_code": "DEMO-ISSUER",
  "message": "Credential signature and current lifecycle status are valid."
}
```

**Further example: payload altered after signing**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/portable" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"completion": {"completed_at": "2026-11-09T12:36:18+00:00"}, "course_code": "PY-999", "credential_id": "CRD-2026-000001", "issued_at": "2026-11-11T12:36:18.948349+00:00", "issuer": {"issuer_code": "DEMO-ISSUER", "issuer_name": "Demo Academy of Technology"}, "learner_id": "LRN-000001", "payload_version": "credential-v1", "rule_version": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0", "signing_key_id": "demo-key-2026"}, "signature_base64": "uN//hWyhul+LpcEgQfWiQhDKWnzs/Z7h3NBBsFknTloeGI2Zd0BRURy4epqEy76P/hpbprQ0qLfQhF2zvTn+AQ=="}'
```

Response (`200`):

```json
{
  "verification_id": "VER-2026-000004",
  "overall_result": "TAMPERED",
  "integrity_result": "tampered",
  "issuer_trust_result": "trusted",
  "lifecycle_result": "active",
  "credential_id": "CRD-2026-000001",
  "issuer_code": "DEMO-ISSUER",
  "message": "Stored credential payload digest does not match."
}
```

**Further example: unregistered issuer and key**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/portable" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"credential_id": "CRD-2026-000777", "issuer": {"issuer_code": "UNKNOWN-ISSUER"}, "signing_key_id": "no-such-key"}, "signature_base64": "AA=="}'
```

Response (`200`):

```json
{
  "verification_id": "VER-2026-000005",
  "overall_result": "UNVERIFIABLE",
  "integrity_result": "unavailable",
  "issuer_trust_result": "unavailable",
  "lifecycle_result": "unknown",
  "credential_id": "CRD-2026-000777",
  "issuer_code": "UNKNOWN-ISSUER",
  "message": "Issuer trust, signing key, or authoritative lifecycle status could not be established."
}
```

**Further example: authentic payload of a revoked credential**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/portable" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"completion": {"completed_at": "2026-11-09T12:36:18+00:00"}, "course_code": "PY-101", "credential_id": "CRD-2026-000001", "issued_at": "2026-11-11T12:36:18.948349+00:00", "issuer": {"issuer_code": "DEMO-ISSUER", "issuer_name": "Demo Academy of Technology"}, "learner_id": "LRN-000001", "payload_version": "credential-v1", "rule_version": "245d8ecf-0218-4d5d-bfee-adbb6d30f3f0", "signing_key_id": "demo-key-2026"}, "signature_base64": "uN//hWyhul+LpcEgQfWiQhDKWnzs/Z7h3NBBsFknTloeGI2Zd0BRURy4epqEy76P/hpbprQ0qLfQhF2zvTn+AQ=="}'
```

Response (`200`):

```json
{
  "verification_id": "VER-2026-000007",
  "overall_result": "REVOKED",
  "integrity_result": "valid",
  "issuer_trust_result": "trusted",
  "lifecycle_result": "revoked",
  "credential_id": "CRD-2026-000001",
  "issuer_code": "DEMO-ISSUER",
  "message": "Credential signature is valid, but the credential is revoked."
}
```

**Further example: NUL character in the payload**

```bash
curl -s -X POST "http://localhost:8000/api/v1/verification/portable" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"credential_id": "CRD\u0000"}, "signature_base64": "AA=="}'
```

Response (`422`):

```json
{
  "detail": "Request contains an unsupported NUL character."
}
```

### `GET /api/v1/verification/requests`

**Purpose.** Read verification request history without learner details.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Newest first. `outcome` filters on `overall_result` (exact match). The response is an untyped list of objects; fields are shown in the example.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `outcome` | query | string, nullable | no |  |
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of object

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/verification/requests?outcome=REVOKED" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "verification_id": "VER-2026-000007",
    "mode": "portable_payload",
    "submitted_credential_id": "CRD-2026-000001",
    "integrity_result": "valid",
    "issuer_trust_result": "trusted",
    "lifecycle_result": "revoked",
    "overall_result": "REVOKED",
    "requested_at": "2026-11-11T12:36:19.141757Z",
    "completed_at": "2026-11-11T12:36:19.141757Z"
  },
  {
    "verification_id": "VER-2026-000006",
    "mode": "credential_id",
    "submitted_credential_id": "CRD-2026-000001",
    "integrity_result": "valid",
    "issuer_trust_result": "trusted",
    "lifecycle_result": "revoked",
    "overall_result": "REVOKED",
    "requested_at": "2026-11-11T12:36:19.132345Z",
    "completed_at": "2026-11-11T12:36:19.132345Z"
  }
]
```

## Revocation

### `POST /api/v1/revocations/{credential_id}`

**Purpose.** Revoke a credential without deleting its record.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR` | `200` |

Returns **`200`**, not `201`. Revocation takes effect immediately (`effective_at` is the server time), is permanent, and never deletes the credential. `reason_code` is free text up to 64 characters; no fixed vocabulary is enforced. In the response, `credential_id` is the credential's internal UUID.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `credential_id` | path | string | yes |  |

**Request body.** [`RevocationCreate`](#revocationcreate)

**Response body (`200`).** [`RevocationResponse`](#revocationresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `404` | Credential was not found. |
| `409` | Credential has already been revoked.<br>The requested change conflicts with an existing record or database constraint. |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s -X POST "http://localhost:8000/api/v1/revocations/CRD-2026-000001" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason_code": "ISSUED_IN_ERROR", "reason_detail": "Assessment record was corrected after issuance."}'
```

**Example response (`200`)**

```json
{
  "id": "f10003b5-6707-4df8-99d0-842acdfe6552",
  "credential_id": "2d5b18bc-724e-4d5c-a75c-745935a171c4",
  "reason_code": "ISSUED_IN_ERROR",
  "reason_detail": "Assessment record was corrected after issuance.",
  "actor_reference": "3c4dd050-d8df-4260-a416-7dec25095b3c",
  "effective_at": "2026-11-11T12:36:19.097758Z",
  "recorded_at": "2026-11-11T12:36:19.097758Z"
}
```

**Further example: Platform Administrator attempting revocation**

```bash
curl -s -X POST "http://localhost:8000/api/v1/revocations/CRD-2026-000001" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason_code": "ISSUED_IN_ERROR"}'
```

Response (`403`):

```json
{
  "detail": "The authenticated user lacks the required role."
}
```

**Further example: credential already revoked**

```bash
curl -s -X POST "http://localhost:8000/api/v1/revocations/CRD-2026-000001" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason_code": "ISSUED_IN_ERROR"}'
```

Response (`409`):

```json
{
  "detail": "Credential has already been revoked."
}
```

**Further example: unknown credential**

```bash
curl -s -X POST "http://localhost:8000/api/v1/revocations/CRD-2026-999999" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason_code": "ISSUED_IN_ERROR"}'
```

Response (`404`):

```json
{
  "detail": "Credential was not found."
}
```

### `GET /api/v1/revocations`

**Purpose.** List immutable revocation records.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Newest first.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`RevocationResponse`](#revocationresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/revocations" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "f10003b5-6707-4df8-99d0-842acdfe6552",
    "credential_id": "2d5b18bc-724e-4d5c-a75c-745935a171c4",
    "reason_code": "ISSUED_IN_ERROR",
    "reason_detail": "Assessment record was corrected after issuance.",
    "actor_reference": "3c4dd050-d8df-4260-a416-7dec25095b3c",
    "effective_at": "2026-11-11T12:36:19.097758Z",
    "recorded_at": "2026-11-11T12:36:19.097758Z"
  }
]
```

## Audit

### `GET /api/v1/audit`

**Purpose.** Read append-only audit events.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Newest first. `target_reference` is an exact match, for example a credential ID, learner ID, course code or rule code.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `target_reference` | query | string, nullable | no |  |
| `limit` | query | integer | no | min `1`, max `100`, default `50` |
| `offset` | query | integer | no | min `0`, max `1000000000`, default `0` |

**Request body.** None.

**Response body (`200`).** array of [`AuditEventResponse`](#auditeventresponse)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/audit?target_reference=CRD-2026-000001" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
[
  {
    "id": "4ede036b-8ee4-40f8-97b8-35a8bb74e202",
    "event_type": "credential.verification",
    "outcome": "revoked",
    "actor_reference": "anonymous-verifier",
    "target_type": "credential",
    "target_reference": "CRD-2026-000001",
    "occurred_at": "2026-11-11T12:36:19.139822Z",
    "reason_code": null,
    "event_data": {
      "mode": "portable_payload",
      "trust": "trusted",
      "integrity": "valid",
      "lifecycle": "revoked"
    }
  },
  {
    "id": "ef580b48-ccc3-475d-9ec2-3f2c94e67cef",
    "event_type": "credential.verification",
    "outcome": "revoked",
    "actor_reference": "anonymous-verifier",
    "target_type": "credential",
    "target_reference": "CRD-2026-000001",
    "occurred_at": "2026-11-11T12:36:19.130109Z",
    "reason_code": null,
    "event_data": {
      "mode": "credential_id",
      "trust": "trusted",
      "integrity": "valid",
      "lifecycle": "revoked"
    }
  }
]
```

_The recorded response contained 7 items; the first 2 are shown._

## Reports and analytics

### `GET /api/v1/reports/summary`

**Purpose.** Summarize credential, revocation, and verification volumes.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** [`ReportSummary`](#reportsummary)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/summary" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "credentials_by_status": {
    "revoked": 1,
    "active": 0
  },
  "total_credentials": 1,
  "total_revocations": 1,
  "total_verifications": 7
}
```

### `GET /api/v1/reports/issuance`

**Purpose.** Count credential issuance by UTC year.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Untyped object: `by_year` maps a UTC year to a count.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** object

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/issuance" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "by_year": {
    "2026": 1
  }
}
```

### `GET /api/v1/reports/revocations`

**Purpose.** Summarize revocations by reason code.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Untyped object: `by_reason` maps a reason code to a count.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** object

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/revocations" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "by_reason": {
    "ISSUED_IN_ERROR": 1
  }
}
```

### `GET /api/v1/reports/verification`

**Purpose.** Summarize verification outcomes and modes.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Untyped object: `groups` lists counts per mode and outcome.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** object

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/verification" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "groups": [
    {
      "mode": "credential_id",
      "outcome": "NOT_FOUND",
      "count": 1
    },
    {
      "mode": "credential_id",
      "outcome": "REVOKED",
      "count": 1
    },
    {
      "mode": "credential_id",
      "outcome": "VALID",
      "count": 1
    }
  ]
}
```

_Long lists are cut to their first 3 items: `groups` (7 items)._

### `GET /api/v1/reports/overview`

**Purpose.** Return database-backed academic and credential lifecycle KPIs.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

All-time totals. Each rate carries its numerator, denominator and definition. The issuance rate is issued learner and course slots divided by slots that have an eligible decision.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** [`AnalyticsOverview`](#analyticsoverview)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/overview" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "as_of": "2026-11-11T12:36:19.230860Z",
  "total_learners": 2,
  "total_courses": 1,
  "total_enrollments": 1,
  "total_completed_records": 1,
  "total_eligible_learners": 1,
  "total_credentials_issued": 1,
  "total_revoked_credentials": 1,
  "total_verification_requests": 7,
  "credential_issuance_rate": {
    "percent": 100.0,
    "numerator": 1,
    "denominator": 1,
    "definition": "Distinct issued learner/course credential slots divided by all distinct learner/course slots with an eligible decision (all time)."
  },
  "revocation_rate": {
    "percent": 100.0,
    "numerator": 1,
    "denominator": 1,
    "definition": "Credentials with a revocation effective as of the report timestamp divided by all issued credentials (all time)."
  },
  "verification_success_rate": {
    "percent": 28.57,
    "numerator": 2,
    "denominator": 7,
    "definition": "Verification requests whose overall result is VALID divided by all verification requests (all time)."
  },
  "completion_rate": {
    "percent": 100.0,
    "numerator": 1,
    "denominator": 1,
    "definition": "Distinct enrollments with a completed completion record divided by all enrollments (all time)."
  }
}
```

**Further example: Learner calling a report**

```bash
curl -s "http://localhost:8000/api/v1/reports/overview" \
  -H "Authorization: Bearer $TOKEN"
```

Response (`403`):

```json
{
  "detail": "The authenticated user lacks the required role."
}
```

### `GET /api/v1/reports/credential-lifecycle`

**Purpose.** Aggregate credential issuance, revocation, and eligibility trends.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Monthly buckets (`YYYY-MM`). Dates must fall in the years 1900 to 2999 and the range may not exceed 10 years.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `date_from` | query | string (date), nullable | no |  |
| `date_to` | query | string (date), nullable | no |  |
| `course_id` | query | string (uuid), nullable | no |  |
| `credential_status` | query | string, nullable | no | pattern `^(active\|revoked)$` |

**Request body.** None.

**Response body (`200`).** [`CredentialLifecycleAnalytics`](#credentiallifecycleanalytics)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Date range cannot exceed 10 years.<br>date_to must be on or after date_from.<br>Dates must fall between the years 1900 and 2999.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/credential-lifecycle?credential_status=revoked" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "as_of": "2026-11-11T12:36:19.253007Z",
  "credential_status": [
    {
      "key": "revoked",
      "count": 1
    }
  ],
  "issuance_over_time": [
    {
      "period": "2026-11",
      "outcome": null,
      "count": 1
    }
  ],
  "revocations_over_time": [
    {
      "period": "2026-11",
      "outcome": null,
      "count": 1
    }
  ],
  "eligibility_outcomes": [
    {
      "key": "eligible",
      "count": 2
    },
    {
      "key": "ineligible",
      "count": 4
    }
  ]
}
```

**Further example: date range in the wrong order**

```bash
curl -s "http://localhost:8000/api/v1/reports/credential-lifecycle?date_from=2026-06-01&date_to=2026-01-01" \
  -H "Authorization: Bearer $TOKEN"
```

Response (`422`):

```json
{
  "detail": "date_to must be on or after date_from."
}
```

### `GET /api/v1/reports/verification-analytics`

**Purpose.** Aggregate verification results and trends.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Same date rules as the lifecycle report.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `date_from` | query | string (date), nullable | no |  |
| `date_to` | query | string (date), nullable | no |  |
| `outcome` | query | string, nullable | no | min length `1`, max length `32` |

**Request body.** None.

**Response body (`200`).** [`VerificationAnalytics`](#verificationanalytics)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Date range cannot exceed 10 years.<br>date_to must be on or after date_from.<br>Dates must fall between the years 1900 and 2999.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/verification-analytics" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "as_of": "2026-11-11T12:36:19.275938Z",
  "total_requests": 7,
  "outcome_counts": [
    {
      "key": "NOT_FOUND",
      "count": 1
    },
    {
      "key": "REVOKED",
      "count": 2
    },
    {
      "key": "TAMPERED",
      "count": 1
    }
  ],
  "mode_counts": [
    {
      "key": "credential_id",
      "count": 3
    },
    {
      "key": "portable_payload",
      "count": 4
    }
  ],
  "outcomes_over_time": [
    {
      "period": "2026-11",
      "outcome": "NOT_FOUND",
      "count": 1
    },
    {
      "period": "2026-11",
      "outcome": "REVOKED",
      "count": 2
    },
    {
      "period": "2026-11",
      "outcome": "TAMPERED",
      "count": 1
    }
  ]
}
```

_Long lists are cut to their first 3 items: `outcome_counts` (5 items), `outcomes_over_time` (5 items)._

### `GET /api/v1/reports/academic-analytics`

**Purpose.** Aggregate enrollments, completions, assessment scores, and eligibility.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

`limit` bounds the number of courses returned (default 20). Same date rules as the lifecycle report.

**Parameters**

| Name | In | Type | Required | Constraints |
|---|---|---|---|---|
| `date_from` | query | string (date), nullable | no |  |
| `date_to` | query | string (date), nullable | no |  |
| `course_id` | query | string (uuid), nullable | no |  |
| `limit` | query | integer | no | min `1`, max `100`, default `20` |

**Request body.** None.

**Response body (`200`).** [`AcademicAnalytics`](#academicanalytics)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `422` | Date range cannot exceed 10 years.<br>date_to must be on or after date_from.<br>Dates must fall between the years 1900 and 2999.<br>Schema validation failure (missing or malformed field, value out of range, NUL character) |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/academic-analytics?limit=5" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "as_of": "2026-11-11T12:36:19.293417Z",
  "course_distribution": [
    {
      "course_id": "f5033ba6-df79-4853-abac-57fca879ed6a",
      "course_code": "PY-101",
      "title": "Python Fundamentals (2026)",
      "enrolled_learners": 1,
      "completed_records": 1
    }
  ],
  "assessment_score_distribution": [
    {
      "score_scale": "0-100",
      "range": "0-59",
      "count": 1
    },
    {
      "score_scale": "0-100",
      "range": "80-89",
      "count": 1
    }
  ],
  "eligibility_outcomes": [
    {
      "key": "eligible",
      "count": 2
    },
    {
      "key": "ineligible",
      "count": 4
    }
  ]
}
```

### `GET /api/v1/reports/data-quality`

**Purpose.** Compare live database counts with imported dataset and validation reports.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Reads the dataset manifest and the import, verification and validation report files named by the four `FULL_DATASET_*_PATH` settings and compares them with live row counts. With those settings unset it returns `status: not_configured` (as in the example). It never runs an import or a validation itself.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** [`DataQualityReport`](#dataqualityreport)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `503` | Configured `<name>` report is unavailable. |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/data-quality" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "status": "not_configured",
  "seed": null,
  "generation_timestamp": null,
  "dataset_sha256": null,
  "total_expected_rows": null,
  "total_imported_rows": null,
  "missing_reference_count": null,
  "last_successful_validation_at": null,
  "row_counts": [],
  "checks": [],
  "warnings": [
    "Configure the full-dataset report paths to show import and validation status."
  ]
}
```

### `GET /api/v1/reports/performance`

**Purpose.** Return measured API benchmark results or an explicit not-measured state.

| Authentication | Roles | Success status |
|---|---|---|
| Bearer token | `ACADEMIC_ADMINISTRATOR`, `PLATFORM_ADMINISTRATOR` | `200` |

Reads the file named by `API_PERFORMANCE_REPORT_PATH`. With that setting unset it returns `status: not_measured` (as in the example). No performance report is checked in.

**Parameters.** None.

**Request body.** None.

**Response body (`200`).** [`PerformanceReport`](#performancereport)

**Error cases**

| Status | Condition or `detail` message |
|---|---|
| `401` | Token missing, invalid or expired; account inactive |
| `403` | Account lacks a required role |
| `503` | Configured `<name>` report is unavailable. |

**Example request**

```bash
curl -s "http://localhost:8000/api/v1/reports/performance" \
  -H "Authorization: Bearer $TOKEN"
```

**Example response (`200`)**

```json
{
  "status": "not_measured",
  "measured": false,
  "average_response_ms": null,
  "median_response_ms": null,
  "p95_response_ms": null,
  "maximum_response_ms": null,
  "slowest_endpoint": null,
  "total_tested_requests": null,
  "successful_request_percent": null,
  "last_tested_at": null,
  "status_distribution": null
}
```

## Schemas

Field definitions for every request and response model, taken from `backend/app/schemas/api.py` through the OpenAPI document. A field marked required has no default.

### AcademicAnalytics

| Field | Type | Required | Constraints |
|---|---|---|---|
| `as_of` | string (date-time) | yes |  |
| `course_distribution` | array of [`CourseAnalytics`](#courseanalytics) | yes |  |
| `assessment_score_distribution` | array of [`AssessmentScoreBucket`](#assessmentscorebucket) | yes |  |
| `eligibility_outcomes` | array of [`AnalyticsBucket`](#analyticsbucket) | yes |  |

### AnalyticsBucket

| Field | Type | Required | Constraints |
|---|---|---|---|
| `key` | string | yes |  |
| `count` | integer | yes |  |

### AnalyticsOverview

| Field | Type | Required | Constraints |
|---|---|---|---|
| `as_of` | string (date-time) | yes |  |
| `total_learners` | integer | yes |  |
| `total_courses` | integer | yes |  |
| `total_enrollments` | integer | yes |  |
| `total_completed_records` | integer | yes |  |
| `total_eligible_learners` | integer | yes |  |
| `total_credentials_issued` | integer | yes |  |
| `total_revoked_credentials` | integer | yes |  |
| `total_verification_requests` | integer | yes |  |
| `credential_issuance_rate` | [`AnalyticsRate`](#analyticsrate) | yes |  |
| `revocation_rate` | [`AnalyticsRate`](#analyticsrate) | yes |  |
| `verification_success_rate` | [`AnalyticsRate`](#analyticsrate) | yes |  |
| `completion_rate` | [`AnalyticsRate`](#analyticsrate) | yes |  |

### AnalyticsRate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `percent` | number, nullable | yes |  |
| `numerator` | integer | yes |  |
| `denominator` | integer | yes |  |
| `definition` | string | yes |  |

### AnalyticsTimeBucket

| Field | Type | Required | Constraints |
|---|---|---|---|
| `period` | string | yes |  |
| `outcome` | string, nullable | no |  |
| `count` | integer | yes |  |

### AssessmentAttemptCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `completion_record_id` | string (uuid) | yes |  |
| `assessment_key` | string | yes | min length `1`, max length `100` |
| `score` | number or string, nullable | no | min `0`, max `100` |
| `score_scale` | string, nullable | no | default `0-100` |
| `result_code` | string, nullable | no | max length `32` |
| `status` | string | no | default `graded` |
| `submitted_at` | string (date-time) | yes |  |
| `graded_at` | string (date-time), nullable | no |  |
| `supersedes_attempt_id` | string (uuid), nullable | no |  |

### AssessmentAttemptResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `completion_record_id` | string (uuid) | yes |  |
| `learner_id` | string (uuid) | yes |  |
| `assessment_key` | string | yes |  |
| `attempt_number` | integer | yes |  |
| `score` | string, nullable | yes |  |
| `score_scale` | string, nullable | yes |  |
| `result_code` | string, nullable | yes |  |
| `status` | string | yes |  |
| `submitted_at` | string (date-time) | yes |  |
| `graded_at` | string (date-time), nullable | yes |  |
| `supersedes_attempt_id` | string (uuid), nullable | yes |  |

### AssessmentScoreBucket

| Field | Type | Required | Constraints |
|---|---|---|---|
| `score_scale` | string | yes |  |
| `range` | string | yes |  |
| `count` | integer | yes |  |

### AuditEventResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `event_type` | string | yes |  |
| `outcome` | string | yes |  |
| `actor_reference` | string | yes |  |
| `target_type` | string, nullable | yes |  |
| `target_reference` | string, nullable | yes |  |
| `occurred_at` | string (date-time) | yes |  |
| `reason_code` | string, nullable | yes |  |
| `event_data` | object, nullable | yes |  |

### CompletionCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `enrollment_id` | string (uuid) | yes |  |
| `status` | string | no | default `in_progress` |
| `started_at` | string (date-time), nullable | no |  |
| `completed_at` | string (date-time), nullable | no |  |
| `source_reference` | string, nullable | no | max length `200` |

### CompletionResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `learner_id` | string (uuid) | yes |  |
| `course_id` | string (uuid) | yes |  |
| `enrollment_id` | string (uuid), nullable | yes |  |
| `status` | string | yes |  |
| `started_at` | string (date-time), nullable | yes |  |
| `completed_at` | string (date-time), nullable | yes |  |
| `recorded_at` | string (date-time) | yes |  |

### CompletionStatusUpdate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `status` | string | yes |  |
| `completed_at` | string (date-time), nullable | no |  |

### CourseAnalytics

| Field | Type | Required | Constraints |
|---|---|---|---|
| `course_id` | string (uuid) | yes |  |
| `course_code` | string | yes |  |
| `title` | string | yes |  |
| `enrolled_learners` | integer | yes |  |
| `completed_records` | integer | yes |  |

### CourseCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `course_code` | string | yes | min length `1`, max length `64` |
| `title` | string | yes | min length `1`, max length `200` |
| `description` | string, nullable | no |  |
| `status` | string | no | default `active` |
| `effective_from` | string (date-time), nullable | no |  |
| `effective_to` | string (date-time), nullable | no |  |

### CourseResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `course_code` | string | yes |  |
| `title` | string | yes |  |
| `description` | string, nullable | yes |  |
| `status` | string | yes |  |
| `effective_from` | string (date-time), nullable | yes |  |
| `effective_to` | string (date-time), nullable | yes |  |

### CourseUpdate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `title` | string, nullable | no | min length `1`, max length `200` |
| `description` | string, nullable | no |  |
| `status` | string, nullable | no |  |
| `effective_from` | string (date-time), nullable | no |  |
| `effective_to` | string (date-time), nullable | no |  |

### CredentialLifecycleAnalytics

| Field | Type | Required | Constraints |
|---|---|---|---|
| `as_of` | string (date-time) | yes |  |
| `credential_status` | array of [`AnalyticsBucket`](#analyticsbucket) | yes |  |
| `issuance_over_time` | array of [`AnalyticsTimeBucket`](#analyticstimebucket) | yes |  |
| `revocations_over_time` | array of [`AnalyticsTimeBucket`](#analyticstimebucket) | yes |  |
| `eligibility_outcomes` | array of [`AnalyticsBucket`](#analyticsbucket) | yes |  |

### CredentialResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `credential_id` | string | yes |  |
| `learner_id` | string (uuid) | yes |  |
| `issuer_id` | string (uuid) | yes |  |
| `rule_version_id` | string (uuid) | yes |  |
| `issued_at` | string (date-time) | yes |  |
| `payload_version` | string | yes |  |
| `sha256_digest` | string | yes |  |
| `signature_algorithm` | string | yes |  |
| `signing_key_id` | string (uuid) | yes |  |
| `replacement_of_credential_id` | string (uuid), nullable | yes |  |

### DataQualityReport

| Field | Type | Required | Constraints |
|---|---|---|---|
| `status` | string | yes |  |
| `seed` | integer, nullable | yes |  |
| `generation_timestamp` | string (date-time), nullable | yes |  |
| `dataset_sha256` | string, nullable | yes |  |
| `total_expected_rows` | integer, nullable | yes |  |
| `total_imported_rows` | integer, nullable | yes |  |
| `missing_reference_count` | integer, nullable | yes |  |
| `last_successful_validation_at` | string (date-time), nullable | yes |  |
| `row_counts` | array of [`DatasetRowCount`](#datasetrowcount) | yes |  |
| `checks` | array of [`DatasetCheck`](#datasetcheck) | yes |  |
| `warnings` | array of string | yes |  |

### DatasetCheck

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | string | yes |  |
| `passed` | boolean | yes |  |
| `details` | string, nullable | no |  |

### DatasetRowCount

| Field | Type | Required | Constraints |
|---|---|---|---|
| `table` | string | yes |  |
| `expected` | integer | yes |  |
| `imported` | integer, nullable | yes |  |
| `current` | integer | yes |  |
| `matches` | boolean, nullable | yes |  |

### EligibilityRequest

| Field | Type | Required | Constraints |
|---|---|---|---|
| `learner_id` | string (uuid) | yes |  |
| `rule_code` | string | yes | min length `1`, max length `64` |

### EligibilityResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `decision_id` | string (uuid) | yes |  |
| `learner_id` | string (uuid) | yes |  |
| `rule_code` | string | yes |  |
| `rule_version_id` | string (uuid) | yes |  |
| `outcome` | string | yes |  |
| `reason_codes` | array of string | yes |  |
| `evaluated_at` | string (date-time) | yes |  |

### EnrollmentCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `learner_id` | string (uuid) | yes |  |
| `course_id` | string (uuid) | yes |  |
| `effective_from` | string (date-time), nullable | no |  |

### EnrollmentResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `learner_id` | string (uuid) | yes |  |
| `course_id` | string (uuid) | yes |  |
| `status` | string | yes |  |
| `enrolled_at` | string (date-time) | yes |  |
| `effective_from` | string (date-time), nullable | yes |  |
| `effective_to` | string (date-time), nullable | yes |  |

### IssueRequest

| Field | Type | Required | Constraints |
|---|---|---|---|
| `learner_id` | string (uuid) | yes |  |
| `rule_code` | string | yes | min length `1`, max length `64` |

### IssuerCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `issuer_code` | string | yes | min length `1`, max length `64` |
| `name` | string | yes | min length `1`, max length `200` |

### IssuerResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `issuer_code` | string | yes |  |
| `name` | string | yes |  |
| `status` | string | yes |  |
| `archived_at` | string (date-time), nullable | yes |  |

### IssuerUpdate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | string, nullable | no | min length `1`, max length `200` |
| `status` | string, nullable | no |  |

### LearnerCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `learner_id` | string, nullable | no | pattern `^LRN-[0-9]{6}$` |
| `display_name` | string | yes | min length `1`, max length `200` |
| `user_id` | string (uuid), nullable | no |  |

### LearnerResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `learner_id` | string | yes |  |
| `display_name` | string | yes |  |
| `user_id` | string (uuid), nullable | yes |  |
| `archived_at` | string (date-time), nullable | yes |  |

### LearnerUpdate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `display_name` | string, nullable | no | min length `1`, max length `200` |
| `archived` | boolean, nullable | no |  |

### LoginRequest

| Field | Type | Required | Constraints |
|---|---|---|---|
| `principal_key` | string | yes | min length `1`, max length `200` |
| `password` | string | yes | min length `1`, max length `1024` |

### PerformanceReport

| Field | Type | Required | Constraints |
|---|---|---|---|
| `status` | string | yes |  |
| `measured` | boolean | yes |  |
| `average_response_ms` | number, nullable | yes |  |
| `median_response_ms` | number, nullable | yes |  |
| `p95_response_ms` | number, nullable | yes |  |
| `maximum_response_ms` | number, nullable | yes |  |
| `slowest_endpoint` | string, nullable | yes |  |
| `total_tested_requests` | integer, nullable | yes |  |
| `successful_request_percent` | number, nullable | yes |  |
| `last_tested_at` | string (date-time), nullable | yes |  |
| `status_distribution` | object, nullable | yes |  |

### PortableCredentialResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `payload` | object | yes |  |
| `signature_base64` | string | yes |  |

### PortableVerificationRequest

| Field | Type | Required | Constraints |
|---|---|---|---|
| `payload` | object | yes |  |
| `signature_base64` | string | yes |  |

### ReportSummary

| Field | Type | Required | Constraints |
|---|---|---|---|
| `credentials_by_status` | object | yes |  |
| `total_credentials` | integer | yes |  |
| `total_revocations` | integer | yes |  |
| `total_verifications` | integer | yes |  |

### RevocationCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `reason_code` | string | yes | min length `1`, max length `64` |
| `reason_detail` | string, nullable | no |  |

### RevocationResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `credential_id` | string (uuid) | yes |  |
| `reason_code` | string | yes |  |
| `reason_detail` | string, nullable | yes |  |
| `actor_reference` | string | yes |  |
| `effective_at` | string (date-time) | yes |  |
| `recorded_at` | string (date-time) | yes |  |

### RuleCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `rule_code` | string | yes | min length `1`, max length `64` |
| `name` | string | yes | min length `1`, max length `200` |
| `description` | string, nullable | no |  |
| `course_id` | string (uuid) | yes |  |
| `criteria` | object | yes |  |
| `attempt_selection_policy` | string, nullable | no | default `latest_graded` |
| `effective_from` | string (date-time) | yes |  |

### RuleResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `rule_id` | string (uuid) | yes |  |
| `version_number` | integer | yes |  |
| `credential_scope_id` | string (uuid) | yes |  |
| `course_id` | string (uuid) | yes |  |
| `rule_code` | string | yes |  |
| `name` | string | yes |  |
| `criteria` | object | yes |  |
| `attempt_selection_policy` | string, nullable | yes |  |
| `effective_from` | string (date-time) | yes |  |
| `effective_to` | string (date-time), nullable | yes |  |
| `status` | string | yes |  |

### RuleVersionCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `course_id` | string (uuid) | yes |  |
| `criteria` | object | yes |  |
| `attempt_selection_policy` | string, nullable | no | default `latest_graded` |
| `effective_from` | string (date-time) | yes |  |

### SigningKeyCreate

| Field | Type | Required | Constraints |
|---|---|---|---|
| `key_id` | string | yes | min length `1`, max length `128` |
| `public_key_base64` | string | yes |  |
| `algorithm` | string | no | default `Ed25519` |
| `valid_from` | string (date-time) | yes |  |
| `valid_until` | string (date-time), nullable | no |  |
| `supersedes_key_id` | string (uuid), nullable | no |  |

### TokenResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `access_token` | string | yes |  |
| `token_type` | string | no | default `bearer` |

### UserResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `id` | string (uuid) | yes |  |
| `principal_key` | string | yes |  |
| `display_name` | string, nullable | yes |  |
| `is_active` | boolean | yes |  |
| `roles` | array of string | yes |  |

### VerificationAnalytics

| Field | Type | Required | Constraints |
|---|---|---|---|
| `as_of` | string (date-time) | yes |  |
| `total_requests` | integer | yes |  |
| `outcome_counts` | array of [`AnalyticsBucket`](#analyticsbucket) | yes |  |
| `mode_counts` | array of [`AnalyticsBucket`](#analyticsbucket) | yes |  |
| `outcomes_over_time` | array of [`AnalyticsTimeBucket`](#analyticstimebucket) | yes |  |

### VerificationResponse

| Field | Type | Required | Constraints |
|---|---|---|---|
| `verification_id` | string, nullable | no |  |
| `overall_result` | string | yes |  |
| `integrity_result` | string | yes |  |
| `issuer_trust_result` | string | yes |  |
| `lifecycle_result` | string | yes |  |
| `credential_id` | string, nullable | no |  |
| `issuer_code` | string, nullable | no |  |
| `message` | string | yes |  |

### HTTPValidationError

FastAPI's standard validation error: `{"detail": [{"type", "loc", "msg", "input", "ctx"}]}`. See [Common status codes](#common-status-codes).
