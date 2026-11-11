# Demonstration Guide

This guide takes one credential through its whole life: issue, verify, tamper, revoke, audit. It takes about ten minutes.

Every command in this guide was run against a freshly migrated database, and the outputs shown are the real outputs of that run. Timestamps and UUIDs will differ on your machine.

## Contents

- [Before you start](#before-you-start)
- [Part 1: Command-line walkthrough](#part-1-command-line-walkthrough)
- [Part 2: The same flow in the browser](#part-2-the-same-flow-in-the-browser)
- [Part 3: Things worth showing](#part-3-things-worth-showing)
- [Reset the demonstration](#reset-the-demonstration)
- [Troubleshooting](#troubleshooting)

## Before you start

Complete the seven setup steps in the [README](../README.md#setup). At the end of them you have:

| Item | Value used in this guide |
|---|---|
| Backend | `http://localhost:8000` |
| Frontend | `http://localhost:5173` |
| Academic Administrator | `demo-admin` |
| Platform Administrator | `demo-platform` |
| Learner | `demo-learner` |
| Password for all three | The `DEMO_USER_PASSWORD` you set |
| Issuer code in `backend/.env` | `DEMO-ISSUER` |
| Key ID in `backend/.env` | `demo-key-1` |
| Public key | The `PUBLIC_KEY_BASE64` value printed in [setup step 5](../README.md#5-generate-a-signing-key-pair) |

The backend must have been restarted after the signing settings were added to `.env`.

Part 1 needs `curl` and `jq` in a POSIX shell (Linux, macOS, Git Bash or WSL).

## Part 1: Command-line walkthrough

### Set variables and sign in

```bash
API=http://localhost:8000/api/v1
export DEMO_USER_PASSWORD='<your demo password>'
export PUBLIC_KEY_BASE64='<public key from setup step 5>'

login() {
  curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
    -d "{\"principal_key\":\"$1\",\"password\":\"$DEMO_USER_PASSWORD\"}" | jq -r .access_token
}
ACADEMIC=$(login demo-admin)
PLATFORM=$(login demo-platform)
LEARNER_TOKEN=$(login demo-learner)

curl -s http://localhost:8000/health
curl -s "$API/auth/me" -H "Authorization: Bearer $ACADEMIC" | jq -c '{principal_key,roles}'
```

```text
{"status":"ok"}
{"principal_key":"demo-admin","roles":["ACADEMIC_ADMINISTRATOR"]}
```

Tokens expire after 30 minutes by default. If a later command returns `401`, run the three `login` lines again.

### Step 1: Register the issuer and its public key

Role: Platform Administrator. This step has no screen in the frontend.

```bash
curl -s -X POST "$API/issuers" -H "Authorization: Bearer $PLATFORM" -H 'Content-Type: application/json' \
  -d '{"issuer_code":"DEMO-ISSUER","name":"Demo Academy"}' | jq -c '{issuer_code,status}'

curl -s -X POST "$API/issuers/DEMO-ISSUER/signing-keys" -H "Authorization: Bearer $PLATFORM" -H 'Content-Type: application/json' \
  -d "{\"key_id\":\"demo-key-1\",\"public_key_base64\":\"$PUBLIC_KEY_BASE64\",\"algorithm\":\"Ed25519\",\"valid_from\":\"2026-01-01T00:00:00Z\"}" | jq -c '{key_id,status}'
```

```text
{"issuer_code":"DEMO-ISSUER","status":"active"}
{"key_id":"demo-key-1","status":"active"}
```

Only the public key is sent. The private key never leaves `backend/.env`.

### Step 2: Create a learner, a course and a rule

Role: Academic Administrator. The learner is linked to the `demo-learner` account so that the learner can later see the credential.

```bash
LEARNER_USER_ID=$(curl -s "$API/auth/me" -H "Authorization: Bearer $LEARNER_TOKEN" | jq -r .id)

LEARNER=$(curl -s -X POST "$API/learners" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d "{\"display_name\":\"Demo Learner\",\"user_id\":\"$LEARNER_USER_ID\"}" | jq -r .id)

COURSE=$(curl -s -X POST "$API/courses" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d '{"course_code":"PY-101","title":"Python Fundamentals"}' | jq -r .id)

curl -s -X POST "$API/credential-rules" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d "{\"rule_code\":\"PY-101-CERT\",\"name\":\"Python Fundamentals Certificate\",\"course_id\":\"$COURSE\",\"criteria\":{\"requires_completion\":true,\"minimum_score\":70},\"effective_from\":\"2026-01-01T00:00:00Z\"}" | jq -c '{rule_code,version_number,criteria}'
```

```text
{"rule_code":"PY-101-CERT","version_number":1,"criteria":{"minimum_score":70,"requires_completion":true,"attempt_selection_policy":"latest_graded"}}
```

The rule says: the course must be completed and the latest graded score must be at least 70.

### Step 3: Record enrollment, completion and a score

```bash
ENROLLMENT=$(curl -s -X POST "$API/enrollments" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d "{\"learner_id\":\"$LEARNER\",\"course_id\":\"$COURSE\"}" | jq -r .id)

COMPLETION=$(curl -s -X POST "$API/completions" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d "{\"enrollment_id\":\"$ENROLLMENT\",\"status\":\"completed\",\"completed_at\":\"2026-11-01T10:00:00Z\"}" | jq -r .id)

curl -s -X POST "$API/assessment-attempts" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d "{\"completion_record_id\":\"$COMPLETION\",\"assessment_key\":\"final-exam\",\"score\":\"88\",\"status\":\"graded\",\"submitted_at\":\"2026-10-30T10:00:00Z\",\"graded_at\":\"2026-10-31T10:00:00Z\"}" | jq -c '{attempt_number,score,status}'
```

```text
{"attempt_number":1,"score":"88.0000","status":"graded"}
```

`completed_at` must not be in the future. If you run this guide before 1 November 2026, use an earlier date for the three timestamps.

### Step 4: Evaluate eligibility

```bash
curl -s -X POST "$API/eligibility/evaluate" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d "{\"learner_id\":\"$LEARNER\",\"rule_code\":\"PY-101-CERT\"}" | jq -c '{outcome,reason_codes}'
```

```text
{"outcome":"eligible","reason_codes":[]}
```

The decision is stored together with the rule version and a snapshot of the evidence.

### Step 5: Issue the credential

Role: Academic Administrator only. The `Idempotency-Key` header is required (8 to 200 characters).

```bash
CREDENTIAL_ID=$(curl -s -X POST "$API/credentials/issue" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-issue-py101-0001' \
  -d "{\"learner_id\":\"$LEARNER\",\"rule_code\":\"PY-101-CERT\"}" | jq -r .credential_id)
echo "issued: $CREDENTIAL_ID"

curl -s "$API/credentials/$CREDENTIAL_ID/portable" -H "Authorization: Bearer $ACADEMIC" > portable.json

curl -s "$API/learners/me/credentials" -H "Authorization: Bearer $LEARNER_TOKEN" | jq -c '[.[].credential_id]'
```

```text
issued: CRD-2026-000001
["CRD-2026-000001"]
```

`portable.json` now holds the signed payload and its signature (`payload` and `signature_base64`). This is the file a learner would hand to an employer. The last command shows that the learner account sees its own credential.

If `issued:` prints `null`, see [Troubleshooting](#troubleshooting).

### Step 6: Verify as a third party

No token is sent. Anyone can make these calls.

```bash
# By credential ID
curl -s -X POST "$API/verification/credential-id?credential_id=$CREDENTIAL_ID" | jq -c '{verification_id,overall_result}'

# By the portable file
curl -s -X POST "$API/verification/portable" -H 'Content-Type: application/json' -d @portable.json | jq -c '{verification_id,overall_result}'
```

```text
{"verification_id":"VER-2026-000001","overall_result":"VALID"}
{"verification_id":"VER-2026-000002","overall_result":"VALID"}
```

### Step 7: Tamper with the credential

Change the course code in a copy of the file and verify the copy.

```bash
jq '.payload.course_code = "PY-999"' portable.json > tampered.json
curl -s -X POST "$API/verification/portable" -H 'Content-Type: application/json' -d @tampered.json | jq -c '{verification_id,overall_result,message}'
```

```text
{"verification_id":"VER-2026-000003","overall_result":"TAMPERED","message":"Stored credential payload digest does not match."}
```

### Step 8: Revoke, then verify again

Role: Academic Administrator only.

```bash
curl -s -X POST "$API/revocations/$CREDENTIAL_ID" -H "Authorization: Bearer $ACADEMIC" -H 'Content-Type: application/json' \
  -d '{"reason_code":"ISSUED_IN_ERROR","reason_detail":"Demonstration revocation."}' | jq -c '{reason_code,effective_at}'

curl -s -X POST "$API/verification/credential-id?credential_id=$CREDENTIAL_ID" | jq -c '{verification_id,overall_result}'
```

```text
{"reason_code":"ISSUED_IN_ERROR","effective_at":"2026-11-11T12:32:11.642008Z"}
{"verification_id":"VER-2026-000004","overall_result":"REVOKED"}
```

The signature is still valid. The result is `REVOKED` because revocation takes precedence over a valid signature.

### Step 9: Read the audit history and the report

```bash
curl -s "$API/credentials/$CREDENTIAL_ID/history" -H "Authorization: Bearer $ACADEMIC" | jq -c '[.[] | "\(.event_type):\(.outcome)"]'

curl -s "$API/reports/overview" -H "Authorization: Bearer $ACADEMIC" | jq -c '{total_learners,total_credentials_issued,total_revoked_credentials,total_verification_requests}'
```

```text
["credential.issued:success","credential.verification:valid","credential.verification:valid","credential.verification:tampered","credential.revoked:success","credential.verification:revoked"]
{"total_learners":1,"total_credentials_issued":1,"total_revoked_credentials":1,"total_verification_requests":4}
```

Every verification request, including the anonymous ones, is in the history.

## Part 2: The same flow in the browser

Open <http://localhost:5173>.

Two things cannot be done in the browser and must be done with the API first:

- **Step 1 of Part 1** (register the issuer and its public key). There is no signing-key screen.
- **Linking a learner to a login account.** The learner form does not have this field. A learner created in the browser cannot see their credential when signed in as `demo-learner`. To show the learner view, create the learner with the API call in Step 2 of Part 1.

Sign in as `demo-admin` and follow the left-hand menu:

| Order | Menu item | Action | What to point out |
|---|---|---|---|
| 1 | Learners | Fill in **Add a learner**, press **Create learner** | The learner ID `LRN-NNNNNN` is generated |
| 2 | Courses | Fill in **Add a course**, press **Create course** | |
| 3 | Credential rules | Fill in **Configure a rule** with the course and a minimum score, press **Create rule** | The rule is stored as version 1; **Create a version** adds version 2 without changing version 1 |
| 4 | Learning records | **Enroll learner**, then **Record completion**, then **Assessment attempt** | Three separate records |
| 5 | Eligibility | Choose the learner and rule, press **Evaluate eligibility** | Outcome and reason codes |
| 6 | Credentials | Choose the learner and rule under **Issue a credential**, press **Issue credential** | The credential ID, the SHA-256 digest and the signature algorithm in the table |
| 7 | Public verification | Enter the credential ID, press **Verify credential** | Result `VALID`; no learner name is shown |
| 8 | Revocations | Choose the credential, enter a reason, press **Continue to confirmation**, confirm | A confirmation step is required |
| 9 | Public verification | Verify the same ID again | Result `REVOKED` |
| 10 | Audit history | Filter by the credential ID | Issued, verified, revoked, verified |
| 11 | Reports, Data & analytics | Open both | Counts match what you just did |

Then show the role differences:

- Sign in as `demo-platform`. The **Revocations** menu item is absent and the Credentials page has no issue form.
- Sign in as `demo-learner`. The menu contains only **Credentials** and **Public verification**. The page is titled **My credentials**.
- Sign out and open <http://localhost:5173/learners>. The application redirects to the sign-in page.
- Open <http://localhost:5173/verification> while signed out. Verification works without an account.

What was checked in a headless browser for this guide:

- Every page loads for each of the three roles, the menus differ by role as described, and protected routes redirect.
- Submitted through the forms: create learner (row 1), evaluate eligibility for an ineligible learner (row 5, shows `ineligible` and the failed requirement), issue for an ineligible learner (row 6, shows `Learner is not eligible for issuance: ASSESSMENT_BELOW_THRESHOLD`), and public verification (rows 7 and 9).
- The learner page lists the credential issued in Part 1.

Not re-submitted through the browser for this guide: the course, rule, enrollment, completion, assessment and revocation forms, and a successful issuance. Those operations were run through the API in Part 1. An earlier full browser run by the project author is recorded in [acceptance-test-report.md](acceptance-test-report.md).

## Part 3: Things worth showing

Each of these shows a rule being enforced. All six were run directly after Part 1 for this guide; the results are the ones the API returned.

| Demonstration | How | Result |
|---|---|---|
| Retry is safe | Repeat the issue call from Step 5 with the same `Idempotency-Key` | `201` with the same credential ID |
| No duplicate credential | Repeat the issue call with a different `Idempotency-Key` | `409` |
| Wrong role | Send the issue call with `$PLATFORM` in place of `$ACADEMIC` | `403` |
| No token | `curl -s -o /dev/null -w '%{http_code}\n' "$API/learners"` | `401` |
| Ineligible learner | Create a second learner, enroll, record a completion and a score of `40`, then issue | `422` `Learner is not eligible for issuance: ASSESSMENT_BELOW_THRESHOLD`; no credential is created, and a `credential.issuance_rejected` event appears in the audit history |
| Unknown credential | Verify `CRD-2026-999999` | `200` with `overall_result` `NOT_FOUND` |

## Reset the demonstration

To start again with an empty database, stop the backend and run from `backend/`:

```bash
alembic downgrade base
alembic upgrade head
```

**This deletes all data in the database named in `DATABASE_URL`**, including the demo users. Create the users again ([setup step 4](../README.md#4-create-demo-users)), start the backend, and remove `portable.json` and `tampered.json`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Backend exits at start with `SECRET_KEY must contain at least 32 bytes` or `must not use a documented placeholder value` | `SECRET_KEY` is too short or is still the example value | Set a generated value in `backend/.env` |
| `issued: null`; the issue call returns `503` `Credential signing is unavailable; configure issuer, key ID, and private key.` | The backend was started before the signing settings were added | Restart the backend |
| Issue returns `503` `Configured active signing issuer is unavailable.` or `Configured active issuer signing key is not registered.` | Step 1 was skipped, or the issuer code or key ID differ from `.env` | Run Step 1 with the same code and key ID as in `.env` |
| Issue returns `503` `Configured private key does not match the registered key.` | The registered public key belongs to a different key pair | Generate a new pair and register it under a new key ID |
| Issue returns `422` with `Field required` for `Idempotency-Key` | The header is missing | Send the header |
| Issue returns `400` | `Idempotency-Key` is shorter than 8 or longer than 200 characters | Use a key of 8 to 200 characters |
| Completion returns `422` `completed_at cannot be in the future.` | The date is ahead of the server clock | Use a past timestamp |
| Any call returns `401` | Token expired | Sign in again |
| Browser shows a network error on sign-in | The frontend origin is not in `CORS_ORIGINS`, or `VITE_API_BASE_URL` is wrong | Use `http://localhost:5173`, or add your origin to `CORS_ORIGINS` and restart the backend |
| Bootstrap fails with `relation "users" does not exist` | Migrations were not applied | `alembic upgrade head` |
| Step 1 returns `409` on a second run | The issuer or key already exists | Continue; or reset |
