# Synthetic Seed Data Guide

> **Note added in Phase 12.** The commands below are PowerShell. POSIX shell equivalents for the starter profile are in the [README](../../README.md#seed-data); they were run and the validator returned `passed` with 30 checks. Three things to know before running anything here:
>
> - `SECRET_KEY` must be exported and must be at least 32 bytes, or `--reset` fails.
> - Without `--output-dir`, `--ground-truth-dir` and `--report`, the scripts overwrite tracked files under `data/`.
> - On a Linux or macOS checkout the committed manifests do not verify. See D-01 to D-05 in [known-issues.md](../known-issues.md#seed-data-and-full-dataset-tools).

## Scope and safety

The generator loads deterministic, synthetic records into a migrated PostgreSQL
database and exports the same rows as a compressed JSON Lines file. It uses
SQLAlchemy Core bulk inserts and the existing model metadata; it does not change
the schema or migration.

Set `SYNTHETIC_DATABASE_URL` to a dedicated database, preferably named
`credential_synthetic`. Generation refuses to run if any application table is
non-empty. `--reset` is destructive: it drops the schema and reapplies the
current Alembic migration. Reset additionally requires the database name to
contain `synthetic` and the explicit confirmation variable shown below. Never
point these commands at development, staging, or production data.

The fixed seed is `20261022`. All IDs, generated outcomes, keypairs, canonical
payloads, signatures, exports, and ground-truth labels are deterministic for
the same profile and code version.

## Dataset profiles and implementation assumptions

The default `full` profile meets the stipulated minimum counts:

| Entity | Full profile | Starter profile |
|---|---:|---:|
| Learners | 20,000 | 1,000 |
| Courses | 1,000 | 100 |
| Credential rules | 100 | 10 |
| Issuers | 10 | 3 |
| Credentials / award slots | 10,000 | 500 |
| Verification requests | 5,000 | 250 |

The full profile also produces enrollments, completion records, assessment
attempts, one eligibility decision and reason per enrollment, evidence
snapshots, issuer keys, audit events, and revocations. Actual counts are
recorded in `data/generated/manifest.json`; enrollment and dependent volumes
are derived from the course-selection pattern rather than fixed targets.

These are synthetic-data assumptions, not approved business policy:

- Each learner receives five deterministic course enrollments, plus a
  credential-target enrollment where needed. Course completion rates vary
  across courses; incomplete and failed outcomes are represented.
- Each course has a course-specific rule version, with a synthetic score
  threshold from 60 through 80 on a 0–100 scale. The fixture evaluates the
  latest graded attempt. Exactly the target learner/course pairs pass; other
  score and completion combinations are ineligible.
- The full data contains one credential for each of 10,000 distinct learner
  and course-scope award slots. Five percent are revoked 60 days after issue.
- Half of the synthetic issuers have an audited profile-name change. Credential
  payloads retain the issuer name effective at their generated issue time.
- Verification requests occur after the fixture's revocation dates and cover
  credential-ID and portable-payload modes.
- Ed25519 test private keys are deterministically derived from the published
  seed, held only in process memory, and never written to the database or
  exports. This deliberately reproducible key material is **not secret and
  must never be used outside synthetic testing**. Only public keys are stored.
- All source data is synthetic; no external datasets or personal records are
  used. The output manifest records source hashes and provenance.

These rules exist only to make the fixture measurable and reproducible. They do
not settle production eligibility, revocation, issuer, or authorization policy.

## Prepare PostgreSQL and generate

Run from PowerShell in `backend/`. Set the URL to a dedicated database and use
the same URL for Alembic:

```powershell
$env:SYNTHETIC_DATABASE_URL = "postgresql+psycopg://<user>:<password>@localhost:5432/credential_synthetic"
$env:DATABASE_URL = $env:SYNTHETIC_DATABASE_URL
$env:SECRET_KEY = "<local-only-placeholder>"
python -m alembic upgrade head
python scripts\generate_seed_data.py
python scripts\validate_seed_data.py
```

For a quick smaller dataset, add `--profile starter`. The generation logic is
shared with the full profile.

To deliberately rebuild a disposable synthetic database:

```powershell
$env:CONFIRM_SYNTHETIC_DATABASE_RESET = "YES"
python scripts\generate_seed_data.py --profile full --reset
python scripts\validate_seed_data.py
```

The reset option uses the existing Alembic migration after clearing the
synthetic schema. It does not remove Docker volumes or files. If the database
name does not contain `synthetic`, or the explicit confirmation variable is
missing, reset is refused.

## Outputs

- `data/generated/seed_data.jsonl.gz` — deterministic, compressed JSON Lines
  for all operational seed rows. Binary values are base64-tagged; UUIDs,
  decimals, and timestamps have stable textual forms.
- `data/generated/manifest.json` — profile, seed, row counts, per-table
  checksums, export checksums, ground-truth checksums, and fixture check
  results.
- `data/generated/source_manifest.json` — hashes of generator, model,
  migration, and original-requirements files; declares synthetic-only
  provenance.
- `data/ground_truth/ground_truth.csv` and `ground_truth.json` — expected
  eligibility and verification outcomes, normal/revoked credential labels, and
  anomaly labels. These files are never inserted into application tables.
- `data/ground_truth/anomaly_fixtures.json` — isolated invalid candidates for
  ineligible issuance, early issuance, duplicate credential ID, revoked-as-
  active status, altered payload digest, and invalid signature.
- `data/validation/validation_summary.json` — validation checks and actual row
  counts.

The operational baseline remains valid. Anomaly candidates are represented
only in ground truth and test transactions; they do not weaken or modify
production constraints.

## Validation and anomaly checks

`validate_seed_data.py` checks exact target and manifest counts, primary and
unique keys, foreign keys, business ID formats, controlled status vocabularies,
timestamp ordering, rule-derived eligibility, assessment score boundaries,
assessment-attempt history, award uniqueness, completion-before-issuance,
revocation timing, issuer-key fingerprints, SHA-256 digests, Ed25519 signatures,
verification lifecycle outcomes, source/ground-truth separation, and output
checksums.

It also runs the duplicate credential-ID case inside a PostgreSQL savepoint,
checks that the real `uq_credentials_external_id` constraint rejects the
candidate, and rolls the entire test transaction back. The other anomaly
fixtures are evaluated without inserting invalid baseline records.

## Reproducibility

Use two output locations and validate each clean run separately. Each reset
requires the explicit safeguards above:

```powershell
python scripts\generate_seed_data.py --profile full --reset `
  --output-dir ..\data\generated\repro-run-1 `
  --ground-truth-dir ..\data\ground_truth\repro-run-1
python scripts\validate_seed_data.py `
  --manifest ..\data\generated\repro-run-1\manifest.json `
  --ground-truth-dir ..\data\ground_truth\repro-run-1 `
  --report ..\data\validation\repro-run-1.json

python scripts\generate_seed_data.py --profile full --reset `
  --output-dir ..\data\generated\repro-run-2 `
  --ground-truth-dir ..\data\ground_truth\repro-run-2
python scripts\validate_seed_data.py `
  --manifest ..\data\generated\repro-run-2\manifest.json `
  --ground-truth-dir ..\data\ground_truth\repro-run-2 `
  --report ..\data\validation\repro-run-2.json

python scripts\check_reproducibility.py `
  --first-manifest ..\data\generated\repro-run-1\manifest.json `
  --second-manifest ..\data\generated\repro-run-2\manifest.json `
  --first-validation ..\data\validation\repro-run-1.json `
  --second-validation ..\data\validation\repro-run-2.json `
  --report ..\data\validation\reproducibility_report.json
```

The comparison fails if profiles, entity counts, deterministic record
checksums, ground truth, source manifest, or validation results differ.

The full profile has been validated twice against clean disposable PostgreSQL
databases using seed `20261022`. Both runs produced matching manifests and
validation results with no differences. The baseline validation report is
`data/validation/validation_summary.json`; the comparison report is
`data/validation/reproducibility_summary.json`. Large compressed exports and
ground-truth row files are intentionally excluded from Git and can be
regenerated with the commands above.
