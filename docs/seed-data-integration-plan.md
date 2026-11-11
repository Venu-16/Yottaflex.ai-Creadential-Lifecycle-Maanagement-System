# Full Seed Data Integration Plan

## Scope and safety

This plan describes a read-only inspection and a proposed import/analytics
validation path for the existing deterministic synthetic export. The source
dataset, ground-truth files, development database, and existing Docker volumes
must remain unchanged.

The local PostgreSQL and API ports `5432` and `8000` are already occupied. Use
a separately named PostgreSQL container/database on an unused port, with
independent credentials. The importer will require an explicit
`FULL_DATASET_DATABASE_URL`, a dedicated database name
`credential_fullscale_integration`, and an explicit confirmation variable.
It will reject an unmigrated or non-empty application schema, use the existing
Alembic revision, and run all inserts and count reconciliation in one
transaction. A duplicate import will fail before inserting any rows.

## Inspected source artifacts

The full-profile operational file currently present is
`data/generated/seed_data.jsonl.gz` (88,215,494 bytes). Its compressed SHA-256
is `6336d13c26a606a5c4dbb22945ec2a3fdf98efeb4ca2d275220a7c7aeeaa433c`,
matching `data/generated/manifest.json`. The export contains 839,400 JSONL
records. The manifest declares seed `20261022`, profile `full`, generator
version `1.0`, per-table row counts/checksums, and the compressed export hash.

`data/generated/source_manifest.json` is 1,044 bytes and declares synthetic-
only provenance; the manifest's source-manifest SHA-256 is
`c46e439787a2428883df2050adaa58c93c52aa2ee27f937b61054eb4fade098c`.
The generated manifest is 4,035 bytes. The separately stored ground-truth
artifacts are `data/ground_truth/ground_truth.csv` (45,779,588 bytes),
`ground_truth.json` (64,778,067 bytes), and `anomaly_fixtures.json` (4,305
bytes). They must not be read by the importer or exposed by API responses.

The manifest reports these operational counts (all are pre-import source
counts, not yet counts from a fresh imported database):

| Entity/table | Expected rows |
|---|---:|
| learners | 20,000 |
| courses | 1,000 |
| credential_rules | 100 |
| credential_rule_versions | 1,000 |
| credential_scopes | 1,000 |
| rule_courses | 1,000 |
| issuers | 10 |
| issuer_signing_keys | 10 |
| enrollments | 109,920 |
| completion_records | 109,920 |
| assessment_attempts | 137,909 |
| eligibility_decisions | 109,920 |
| eligibility_reasons | 109,920 |
| eligibility_evidence | 201,686 |
| credential_awards | 10,000 |
| credentials | 10,000 |
| revocations | 500 |
| verification_requests | 5,000 |
| audit_events | 10,505 |
| users, roles, user_roles, idempotency_records | 0 each |
| **Total records** | **839,400** |

These source counts agree with the checked-in
`data/validation/validation_summary.json`.

The export and source-manifest checksums match the generated manifest. One
historical source-manifest entry does not match the current checkout:
`backend/migrations/versions/af6e5dad6637_create_credential_domain_schema.py`
has current SHA-256
`966785c7e7635e17b25b9d88df0f9643dbe0b70a9a63eef6875a6a603355ab34`, while
the source manifest records `3ddeb0a1e5943642c8f502c1937a45355a0b36872c6ac4ee7903e331b7e8250d`.
The importer reports this as source-code provenance drift rather than rewriting
the source manifest or seed export. Schema/table compatibility is checked
separately, and the existing full validator's `source_file_hashes_match` result
must remain visible as a failure unless the discrepancy is resolved without
changing the source data.

## Model mapping and insertion order

Every `table`/`record` pair in the compressed JSONL export maps directly to
the same-named SQLAlchemy `Base.metadata` table. The existing generator
normalizes UUIDs, timezone-aware timestamps, decimals, bytes as a `$base64`
marker, and JSON values. The importer must restore SQLAlchemy-native UUID,
datetime, `Decimal`, and binary values without interpreting or inserting
ground-truth labels.

The export is streamed table-by-table in its generated dependency order:

1. Empty authentication/idempotency tables; courses, rules, issuers, learners.
2. Credential scopes and issuer keys; rule versions and rule-course links.
3. Enrollments, completions, assessment attempts, eligibility decisions,
   reasons, and evidence.
4. Credential awards and credentials; revocations, verification requests,
   then audit events.

The implementation must verify table names, complete column sets, contiguous
table groups, source checksums, and table counts before database writes. It
must preserve all exported primary/business identifiers and foreign-key
relationships. Use batches bounded in size but one transaction for safe
rollback; reconcile every manifest table count before commit.

## Validation and API exercise

After import, run the existing seed-data validator against the isolated
database with a new report path, preserving the checked-in baseline validation
report. Add a separate verifier for manifest-to-database table counts and
foreign-key integrity. Record measured import and validation durations,
expected/actual counts, failures, warnings, and source checksum references in
`docs/full-dataset-validation-report.md`.

Exercise the running FastAPI instance against this imported database using
bounded requests and representative records from the start, middle, and end of
the dataset. Include normal and unknown IDs, bounded/invalid pagination,
revoked and active credentials, verification/audit, eligibility, and reports.
Record per-request timings and status codes, average/median/p95/maximum,
request totals, and slowest route in
`docs/api-performance-report.md`. Do not run uncontrolled concurrency or
claim a performance threshold without evidence.

## Analytics and UI plan

Extend the existing `/reports/*` routes, which require the current
`AUDIT_READERS` roles (Platform Administrator and Academic Administrator).
Use bounded SQL aggregates and typed response schemas for:

- All-time totals and rates with explicit denominators.
- Credential status, issue and revocation time buckets, and eligibility
  outcomes.
- Verification request outcomes/modes using values actually emitted by the
  service, including `NOT_FOUND`, `TAMPERED`, `INVALID_SIGNATURE`,
  `UNVERIFIABLE`, `REVOKED`, and `VALID`.
- Course enrollment/completion distributions and assessment score buckets,
  without learner-level details.
- Data quality, based on the verified import/validation artifact plus live
  aggregate counts. Ground-truth labels remain unavailable to these routes.
- Performance measurements loaded only from an actual saved benchmark report;
  otherwise return an explicit “not yet measured” state.

Add a dedicated role-protected Data & Analytics page using the existing
React/Tailwind components and Axios client. Avoid a new chart dependency unless
the existing conventions require one; any charts must render actual endpoint
data, support real server-side filters, and show empty/loading/error states.

## Acceptance evidence still required

- Fresh isolated PostgreSQL migration, import, full validation, and count/FK
  reconciliation.
- API integration and repeatable bounded performance measurements against
  the imported database.
- Correctness/RBAC/filtering/empty-dataset tests for analytics.
- Frontend production build and browser check against the imported-dataset API.
- Import/validation and performance reports with actual measurements.
- A three-minute dashboard walkthrough in
  `docs/ANALYTICS_DEMO_GUIDE.md`.

Do not mark Phase 10 complete unless the full export was imported, validated,
queried through the application, and displayed in the dashboard. Historical
generator counts and previous synthetic-data validation do not substitute for
this run.
