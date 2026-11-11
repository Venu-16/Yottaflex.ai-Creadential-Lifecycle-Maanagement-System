# Original Hackathon Problem Statement and Project Goals

> **Source of truth:** This document preserves the original user-provided requirements. It is not an architecture proposal. Do not remove, weaken, or silently reinterpret mandatory requirements. Any proposed simplification that affects an acceptance criterion requires explicit approval and a documented trade-off.

## 1. Business Context

Issue credentials after completion requirements are met and support revocation and third-party verification.

## 2. Primary Objective

Build a working end-to-end solution that:

1. Defines credential eligibility requirements.
2. Records course completion and assessment results.
3. Evaluates whether learners satisfy credential requirements.
4. Issues unique credentials only after all applicable requirements pass.
5. Creates verifiable signed-record metadata or deterministic cryptographic hashes.
6. Supports third-party credential verification.
7. Supports authorized credential revocation.
8. Preserves immutable-style audit history.
9. Exposes important business decisions and exceptions.
10. Produces measurable evaluation outputs.

## 3. Primary Actors

- Learner
- Instructor
- Academic Administrator
- Support Staff
- Platform Administrator
- Third-party Verifier

The first five are the primary internal actors; the Third-party Verifier is the external verification actor. Their detailed responsibilities and permission matrix are not specified here and must not be invented as approved requirements.

## 4. Mandatory Business Workflow

1. Generate master data: Learner, Course, CredentialRule, CompletionRecord and Credential.
2. Generate dependent transaction and event records using valid parent IDs.
3. Define credential requirements.
4. Generate course completion and assessment records.
5. Evaluate eligibility using documented business rules.
6. Issue unique credential IDs only after requirements pass.
7. Generate verifiable signed-record metadata or deterministic hashes.
8. Simulate third-party verification requests.
9. Simulate credential revocations.
10. Preserve immutable audit history.
11. Persist important state changes as explicit records or events.
12. Generate derived outcomes and ground-truth labels from documented rules.

## 5. Mandatory Entities

Learner, Course, CredentialRule, CompletionRecord, Credential, Issuer, VerificationRequest, Revocation and AuditEvent.

Additional supporting entities such as Enrollment, RuleCourse and EligibilityDecision may be introduced when justified by the architecture.

Every entity must have:

- Primary key.
- Appropriate foreign keys.
- Documented cardinality.
- Optional relationship definitions.
- Lifecycle states.
- Effective dates where applicable.

## 6. Mandatory Synthetic Data Requirements

Baseline data volume:

| Entity | Required count |
|---|---:|
| Learners | 20,000 |
| Courses | 1,000 |
| Credentials | 10,000 |
| Verification requests | 5,000 |

Include:

- Revoked credentials.
- Duplicate learner names.
- Incomplete courses.
- Issuer changes.
- Credential lifecycle variations.

Use a fixed seed: **20261022**.

The generator must be parameterized so starter and full datasets use the same generation logic.

Generate valid baseline records first, then inject labelled edge cases.

## 7. Mandatory Anomaly Scenarios

1. Credential issued before completion.
2. Duplicate credential ID.
3. Revoked credential verifies as active.
4. Altered payload hash not detected.

These scenarios must be demonstrable through controlled test fixtures and validation results.

Do not silently corrupt unrelated baseline records.

## 8. Mandatory Data Quality Requirements

Validate:

- Primary-key uniqueness.
- Foreign-key integrity.
- Allowed enumeration values.
- Date ordering.
- Arithmetic reconciliation.
- Lifecycle transitions.
- Duplicate records.
- Consistency across entity relationships.

## 9. Ground Truth Requirements

Produce a separate ground_truth.csv or ground_truth.json containing:

- Known anomaly labels.
- Expected eligibility decisions.
- Expected verification results.
- Expected business rule outcomes.

Never leak ground-truth labels into application input features or decision logic.

## 10. Required Deliverables

Generate:

- CSV/JSON/SQL seed data.
- Database schema.
- Data dictionary.
- Synthetic data generator.
- Ground-truth files.
- README documentation.
- Generator execution command.
- Fixed seed documentation.
- Source manifest.
- Validation summary.
- Reproducibility report.

## 11. Reproducibility Requirements

Run the data generator twice with the same seed.

Compare:

- Row counts.
- Record identifiers.
- File checksums.
- Ground-truth labels.
- Validation results.

Both executions must produce identical deterministic outputs.

## 12. Lawful Data Provenance

External datasets are optional.

If used, document:

- Source URL.
- Dataset version.
- Retrieval date.
- License and terms.
- Attribution.
- Transformations.
- Fields discarded.

Use synthetic data if licensing or suitability is unclear.

## 13. Hackathon Evaluation Criteria

The solution will be evaluated on:

1. Realistic data distributions and meaningful variation.
2. Consistent IDs and valid joins.
3. Dependency and lifecycle consistency.
4. Correct derived values and reconciliation.
5. Normal, boundary, failure and exception coverage.
6. Separate ground-truth data.
7. Fixed-seed reproducibility.
8. Complete documentation.
9. Lawful data provenance.
10. Correct credential issuance, verification and revocation.

## 14. Definition of Success

The project is considered successfully implemented when:

- Eligible learners receive valid credentials.
- Ineligible learners cannot receive credentials.
- Credential identifiers are unique.
- Third parties can independently verify authenticity.
- Altered credentials are detected.
- Revoked credentials cannot verify as active.
- All important operations are traceable.
- Mandatory anomaly scenarios are demonstrated.
- Required synthetic data volumes can be generated.
- Data integrity and reproducibility validations pass.
- The complete workflow can be demonstrated end to end.
