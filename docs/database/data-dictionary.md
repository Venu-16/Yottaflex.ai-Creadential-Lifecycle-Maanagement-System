# Logical Data Dictionary — Step 4.1

**Status: MVP DESIGN BASELINE.** This dictionary documents the implemented PostgreSQL-oriented schema and its constraints. Product assumptions remain explicitly distinguished from user-approved policy in [DECISIONS.md](../DECISIONS.md). Requirements remain governed by [original-problem-statement.md](../original-problem-statement.md).

## Conventions

- Unless noted otherwise, entity `id` is `UUID PRIMARY KEY NOT NULL DEFAULT gen_random_uuid()`. Confirm the deployed PostgreSQL major version supports this built-in before implementation.
- `created_at`, `recorded_at`, and similar operational timestamps use `TIMESTAMPTZ` in UTC with `DEFAULT CURRENT_TIMESTAMP`. PostgreSQL/database time is recorded chronology, not independently trusted signing-time evidence.
- FKs should use `ON DELETE RESTRICT` by default. Prefer inactive/archive states over hard deletion. Never cascade-delete audit, issuance, verification, key-history, or revocation records.
- `UNIQUE` below applies to the listed column(s) or partial index. `CHECK` conditions are logical proposals; exact allowed status/reason values remain pending. Do not introduce PostgreSQL ENUMs until vocabularies are approved.
- Required external formats: `Learner.learner_id` = `LRN-000001`; `Credential.credential_id` = `CRD-2026-000001`; `VerificationRequest.verification_id` = `VER-2026-000001`. Format checks validate shape. MVP allocation assumption IA-08 uses UTC issuance year and an atomic per-year credential sequence; learner/verification counters are globally allocated and never recycled.
- `BYTEA` stores exact bytes (digests, signature, canonical payload, cryptographic evidence). A 32-byte SHA-256 digest should be length-checked. Private signing keys are never stored.
- Nullable/unique/default/check rules are proposals where the associated business decision remains open. Conditions that require cross-table comparison may need composite FKs or transactional application validation at implementation.

## 1. Learner

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal learner key. |
| `learner_id` | VARCHAR(10) | No | — | No | Yes | `CHECK (learner_id ~ '^LRN-[0-9]{6}$')` | Required external ID; allocation order is not represented by this string alone. |
| `display_name` | VARCHAR(200) | No | — | No | No | Trim/non-empty validation | Learner name as permitted by the approved privacy model; duplicates are allowed. |
| `user_id` | UUID | No | User | Yes | Yes when non-null | `ON DELETE RESTRICT` | Optional account link; one account per learner profile if account linkage is approved. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Profile creation time. |
| `updated_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Profile maintenance time; audit changes separately. |
| `archived_at` | TIMESTAMPTZ | No | — | Yes | No | — | Soft archival; do not delete learner history. |

## 2. Course

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal course key. |
| `course_code` | VARCHAR(64) | No | — | No | Yes | Trim/non-empty; format pending | Course business identifier; no external format is stipulated. |
| `title` | VARCHAR(200) | No | — | No | No | Trim/non-empty | Course display title. |
| `description` | TEXT | No | — | Yes | No | — | Optional course description. |
| `status` | VARCHAR(24) | No | — | No | No | Approved vocabulary pending | Course lifecycle state; do not finalize enum values yet. |
| `effective_from` | TIMESTAMPTZ | No | — | Yes | No | — | Start of course validity where applicable. |
| `effective_to` | TIMESTAMPTZ | No | — | Yes | No | `CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from)` | End of course validity. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Record creation time. |

## 3. CredentialScope

Stable course-award scope shared by rules and issued credentials. The MVP supports course scope only; program credentials are deferred.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal scope key. |
| `course_id` | UUID | No | Course | No | Yes | `ON DELETE RESTRICT` | Exactly one stable scope per course in the MVP. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Scope identity creation time. |

## 3.1 CredentialAward

Stable award entitlement, separate from an evaluation and from each immutable credential artifact. One award slot is unique per learner and course scope. Replacements remain in the same slot.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal award key. |
| `learner_id` | UUID | No | Learner | No | Composite unique | `ON DELETE RESTRICT` | Award recipient. |
| `credential_scope_id` | UUID | No | CredentialScope | No | Composite unique | `ON DELETE RESTRICT` | Stable award scope. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Award-slot creation time. |
| — | — | — | — | — | `UNIQUE (learner_id, credential_scope_id)` | Composite unique | Prevents another award slot for the same learner/scope regardless of decision, rule version, issuer, or idempotency key. |

## 4. Program (deferred)

Not included in the MVP. Add only when program-level credentials are required.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal program key. |
| `program_code` | VARCHAR(64) | No | — | No | Yes | Trim/non-empty | Program business identifier. |
| `name` | VARCHAR(200) | No | — | No | No | Trim/non-empty | Program name. |
| `status` | VARCHAR(24) | No | — | No | No | Approved vocabulary pending | Program lifecycle state. |
| `effective_from` | TIMESTAMPTZ | No | — | Yes | No | — | Program effective start. |
| `effective_to` | TIMESTAMPTZ | No | — | Yes | No | Greater than `effective_from` if both set | Program effective end. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Record creation time. |

## 5. ProgramCourse (conditional bridge)

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `program_id` | UUID | Yes (composite) | Program | No | Composite | `ON DELETE RESTRICT` | Program member. |
| `course_id` | UUID | Yes (composite) | Course | No | Composite | `ON DELETE RESTRICT` | Course member. |
| `effective_from` | TIMESTAMPTZ | No | — | Yes | No | — | Membership start if time-varying membership is approved. |
| `effective_to` | TIMESTAMPTZ | No | — | Yes | No | Greater than `effective_from` if both set | Membership end. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Link creation time. |

## 6. CredentialRule

Stable rule family; version-specific criteria belong in CredentialRuleVersion.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal rule-family key. |
| `rule_code` | VARCHAR(64) | No | — | No | Yes | Stable, non-empty | Human-readable rule identity across versions. |
| `name` | VARCHAR(200) | No | — | No | No | Trim/non-empty | Rule name. |
| `description` | TEXT | No | — | Yes | No | — | Purpose and scope description. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Rule-family creation time. |
| `archived_at` | TIMESTAMPTZ | No | — | Yes | No | — | Soft archival; prior versions remain referenced. |

## 7. CredentialRuleVersion

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Immutable version key. |
| `rule_id` | UUID | No | CredentialRule | No | Composite unique | `ON DELETE RESTRICT` | Stable rule family. |
| `version_number` | INTEGER | No | — | No | Composite unique | `CHECK (version_number > 0)` | Monotonically increasing version within family. |
| `credential_scope_id` | UUID | No | CredentialScope | No | No | `ON DELETE RESTRICT` | Stable award scope shared by evaluations and issuance. |
| `criteria` | JSONB | No | — | No | No | `CHECK (jsonb_typeof(criteria)='object')`; validate against versioned schema | Structured rule expression; JSONB is used only for flexible rule clauses, not relational evidence. |
| `attempt_selection_policy` | VARCHAR(24) | No | — | Yes | No | Candidate `latest` / `highest` / `any_pass`; pending | Rule-specific policy if assessment attempts are used. |
| `effective_from` | TIMESTAMPTZ | No | — | No | No | — | Version activation time. |
| `effective_to` | TIMESTAMPTZ | No | — | Yes | No | `CHECK (effective_to IS NULL OR effective_to > effective_from)` | Version end time. |
| `status` | VARCHAR(24) | No | — | No | No | Approved vocabulary pending | Draft/active/retired semantics require approval. |
| `created_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Actor that created the version, if user management is approved. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Version creation time. |
| — | — | — | — | — | `UNIQUE (rule_id, version_number)` | — | Prevent duplicate version numbers in a family. |

## 8. RuleCourse

Bridge between a rule version and each course requirement. If approved rules are strictly single-course, this bridge may be simplified after review.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `rule_version_id` | UUID | Yes (composite) | CredentialRuleVersion | No | Composite | `ON DELETE RESTRICT` | Rule version side. |
| `course_id` | UUID | Yes (composite) | Course | No | Composite | `ON DELETE RESTRICT` | Required or considered course side. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Link creation time. |

## 9. User

Optional until the authentication/account model is approved.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal principal key. |
| `principal_key` | VARCHAR(200) | No | — | No | Yes | Stable, normalized; format depends on identity provider | Login/external subject identifier; exact account model pending. |
| `password_hash` | TEXT | No | — | Yes | No | Null only for external-auth accounts | Adaptive password hash only; never plaintext/password encryption. |
| `display_name` | VARCHAR(200) | No | — | Yes | No | — | Optional account display name. |
| `is_active` | BOOLEAN | No | — | No | No | `TRUE` | Account activation flag; deactivation preserves history. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Account creation time. |
| `disabled_at` | TIMESTAMPTZ | No | — | Yes | No | — | Account disable time. |

## 10. Role

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal role key. |
| `role_code` | VARCHAR(64) | No | — | No | Yes | Controlled by approved role vocabulary | Role identity; does not encode permissions by itself. |
| `description` | TEXT | No | — | Yes | No | — | Role description. |
| `is_active` | BOOLEAN | No | — | No | No | `TRUE` | Soft-deactivation flag. |

## 11. UserRole

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Grant record key. |
| `user_id` | UUID | No | User | No | Partial unique | `ON DELETE RESTRICT` | Account receiving role. |
| `role_id` | UUID | No | Role | No | Partial unique | `ON DELETE RESTRICT` | Granted role. |
| `granted_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Grant time. |
| `granted_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Granting principal. |
| `revoked_at` | TIMESTAMPTZ | No | — | Yes | No | Must be `>= granted_at` | Revocation time; retain grant history. |
| `revoked_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Revoking principal. |
| — | — | — | — | — | `UNIQUE (user_id, role_id) WHERE revoked_at IS NULL` | Partial unique index | Prevent duplicate active grants while allowing historical grant rows. |

## 12. Enrollment

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Enrollment key. |
| `learner_id` | UUID | No | Learner | No | No | `ON DELETE RESTRICT` | Enrolled learner. |
| `course_id` | UUID | No | Course | No | No | `ON DELETE RESTRICT` | Enrolled course. |
| `status` | VARCHAR(24) | No | — | No | No | Approved vocabulary pending | Enrollment lifecycle state. |
| `enrolled_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Enrollment time. |
| `effective_from` | TIMESTAMPTZ | No | — | Yes | No | — | Enrollment validity start. |
| `effective_to` | TIMESTAMPTZ | No | — | Yes | No | Greater than start if both set | Enrollment validity end. |
| `recorded_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Recording actor if accounts are implemented. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Record creation time. |
| — | — | — | — | — | `UNIQUE (id, learner_id, course_id)` | Composite unique key | Supports a composite FK from CompletionRecord to ensure enrollment/learner/course agree. |

## 13. CompletionRecord

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Course-level completion key. |
| `learner_id` | UUID | No | Learner | No | No | `ON DELETE RESTRICT` | Learner whose course progress is recorded. |
| `course_id` | UUID | No | Course | No | No | `ON DELETE RESTRICT` | Course being completed. |
| `enrollment_id` | UUID | No | Enrollment | Yes | No | `ON DELETE RESTRICT`; composite FK `(enrollment_id, learner_id, course_id)` if present | Optional enrollment provenance; necessity remains pending. |
| `status` | VARCHAR(24) | No | — | No | No | Approved vocabulary pending | Course-level progress/completion state; not an assessment score. |
| `started_at` | TIMESTAMPTZ | No | — | Yes | No | — | Course start time. |
| `completed_at` | TIMESTAMPTZ | No | — | Yes | No | `CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)` | Completion time. |
| `recorded_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | System-recorded time, not external trusted evidence. |
| `recorded_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Recording actor. |
| `source_reference` | VARCHAR(200) | No | — | Yes | No | — | External/import provenance reference, not an unvalidated URL or raw payload. |
| — | — | — | — | — | `UNIQUE (id, learner_id)` | Composite unique key | Supports learner-consistency FKs where needed. |
| — | — | — | — | — | `UNIQUE (enrollment_id)` | Unique; NULL values remain distinct | At most one completion record per enrollment; completions without enrollment remain allowed. |

## 14. AssessmentAttempt

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Individual sitting key. |
| `completion_record_id` | UUID | No | CompletionRecord | No | Composite unique | `ON DELETE RESTRICT` | Parent learner/course completion context. |
| `learner_id` | UUID | No | Learner | No | Composite FK | Composite FK with `completion_record_id`; must match parent learner | Duplicated for declarative learner/evidence consistency. |
| `attempt_number` | INTEGER | No | — | No | Composite unique | `CHECK (attempt_number > 0)` | Stable attempt order within the agreed assessment key. |
| `assessment_key` | VARCHAR(100) | No | — | No | Composite unique | Non-empty; vocabulary/scope pending | Assessment identity within course. |
| `score` | NUMERIC(10,4) | No | — | Yes | No | Range check depends on the approved scale; no universal lower/upper bound is assumed | Precise score. |
| `score_scale` | VARCHAR(40) | No | — | Yes | No | Required when a score is present by application validation | Scale/unit for interpreting score. |
| `result_code` | VARCHAR(32) | No | — | Yes | No | Approved values pending | Optional outcome such as pass/fail after policy is agreed. |
| `status` | VARCHAR(24) | No | — | No | No | Approved vocabulary pending | Attempt lifecycle/grading state. |
| `submitted_at` | TIMESTAMPTZ | No | — | No | No | — | Attempt submission time. |
| `graded_at` | TIMESTAMPTZ | No | — | Yes | No | `CHECK (graded_at IS NULL OR graded_at >= submitted_at)` | Grading time. |
| `recorded_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Record creation time. |
| `recorded_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Recording/grading actor. |
| `supersedes_attempt_id` | UUID | No | AssessmentAttempt | Yes | No | `ON DELETE RESTRICT`; same-completion consistency check | Correction/void linkage; prior attempt remains unchanged. |
| — | — | — | — | — | `UNIQUE (completion_record_id, assessment_key, attempt_number)` | Composite unique | Prevent duplicate attempt sequence per assessment/completion. |

## 15. EligibilityDecision

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Evaluation snapshot key. |
| `learner_id` | UUID | No | Learner | No | Composite unique | `ON DELETE RESTRICT` | Evaluated learner. |
| `rule_version_id` | UUID | No | CredentialRuleVersion | No | Composite unique | `ON DELETE RESTRICT` | Exact applicable rule version. |
| `evaluated_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Evaluation time recorded by the system. |
| `outcome` | VARCHAR(24) | No | — | No | No | Candidate `eligible`, `ineligible`, `needs_review`; pending | Decision outcome; final vocabulary pending. |
| `evaluator_type` | VARCHAR(24) | No | — | No | No | Candidate `user`, `service`; pending | Identifies human/service evaluation principal type. |
| `evaluator_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Human evaluator if applicable. |
| `evaluator_reference` | VARCHAR(200) | No | — | Yes | No | — | Non-user service/principal reference. |
| `input_snapshot_digest` | BYTEA | No | — | No | No | Exactly 32 bytes | SHA-256 digest of the immutable evaluation/evidence snapshot. |
| `evaluator_version` | VARCHAR(40) | No | — | No | No | Versioned evaluator identifier | Identifies the evaluation implementation/semantics used. |
| `attempt_selection_policy` | VARCHAR(24) | No | — | Yes | No | MVP assumption `latest`; exact policy is stored with each decision | Policy applied to assessment attempts. |
| `evidence_snapshot` | JSONB | No | — | No | No | Canonical, versioned object; exclude ground-truth labels | Immutable evidence values used during the evaluation. |
| `credential_scope_id` | UUID | No | CredentialScope | No | Composite unique | `ON DELETE RESTRICT` | Scope to which this exact rule evaluation applies. |
| `supersedes_decision_id` | UUID | No | EligibilityDecision | Yes | No | `ON DELETE RESTRICT` | Links a later evaluation to prior snapshot without overwriting it. |
| — | — | — | — | — | `UNIQUE (id, learner_id)` | Composite unique key | Supports learner-consistency FK from EligibilityEvidence. |
| — | — | — | — | — | `UNIQUE (id, learner_id, rule_version_id, credential_scope_id)` | Composite unique key | Supports context-consistency FK from Credential. |

## 16. EligibilityReason

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Reason record key. |
| `eligibility_decision_id` | UUID | No | EligibilityDecision | No | No | `ON DELETE RESTRICT` | Parent decision. |
| `reason_code` | VARCHAR(64) | No | — | No | No | Controlled vocabulary pending | Stable machine-readable explanation code. |
| `message` | TEXT | No | — | Yes | No | Avoid unnecessary learner PII | Human-readable explanation. |
| `details` | JSONB | No | — | Yes | No | Object only if present; strict allowlist | Bounded supplementary facts, not ground-truth labels. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Reason capture time. |

## 17. EligibilityEvidence

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Evidence-link key. |
| `eligibility_decision_id` | UUID | No | EligibilityDecision | No | No | `ON DELETE RESTRICT` | Decision using the evidence. |
| `completion_record_id` | UUID | No | CompletionRecord | Conditional | No | `ON DELETE RESTRICT` | Completion evidence when source is completion. |
| `assessment_attempt_id` | UUID | No | AssessmentAttempt | Conditional | No | `ON DELETE RESTRICT` | Attempt evidence when source is an assessment sitting. |
| `selection_role` | VARCHAR(24) | No | — | No | No | Candidate `selected`, `considered`; final semantics pending | How evaluator used the evidence. |
| `evidence_digest` | BYTEA | No | — | No | No | Exactly 32 bytes | SHA-256 digest of the evidence snapshot. |
| `evidence_snapshot` | JSONB | No | — | No | No | Canonical source values, versioned and redacted | Preserves the exact source facts considered. |
| `captured_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Time evidence was linked/snapshotted. |
| — | — | — | — | — | `CHECK ((completion_record_id IS NOT NULL AND assessment_attempt_id IS NULL) OR (completion_record_id IS NULL AND assessment_attempt_id IS NOT NULL))` | Exactly one source | Evidence is a CompletionRecord or AssessmentAttempt, never both/neither. |
| — | — | — | — | — | Unique decision/source tuple | Conditional | Prevent duplicate links; exact selected/considered rules pending. |

## 18. Issuer

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal issuer key. |
| `issuer_code` | VARCHAR(64) | No | — | No | Yes | Stable, non-empty | Issuer business identity. |
| `name` | VARCHAR(200) | No | — | No | No | Trim/non-empty | Issuer display name. |
| `status` | VARCHAR(24) | No | — | No | No | Approved vocabulary pending | Issuer lifecycle/trust status. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Issuer registration time. |
| `archived_at` | TIMESTAMPTZ | No | — | Yes | No | — | Soft archival; historical credentials retain issuer reference. |

## 19. IssuerSigningKey

Public trust metadata only. Private key material must live outside ordinary database tables.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal key-record key. |
| `issuer_id` | UUID | No | Issuer | No | Composite unique | `ON DELETE RESTRICT` | Issuer bound to this key. |
| `key_id` | VARCHAR(128) | No | — | No | Composite unique | Non-empty | Key identifier carried in signed credentials. |
| `public_key` | BYTEA | No | — | No | No | `octet_length(public_key)=32` for MVP Ed25519 | Public key bytes. |
| `fingerprint` | BYTEA | No | — | No | Composite unique | 32-byte SHA-256 fingerprint | Public-key fingerprint. |
| `algorithm` | VARCHAR(40) | No | — | No | No | MVP check `algorithm='Ed25519'` | Signature algorithm under assumption IA-07. |
| `key_purpose` | VARCHAR(32) | No | — | No | No | Approved vocabulary pending | Intended use, e.g. credential signing. |
| `valid_from` | TIMESTAMPTZ | No | — | No | No | — | Start of key signing-validity interval. |
| `valid_until` | TIMESTAMPTZ | No | — | Yes | No | Must be greater than `valid_from` if set | End of signing-validity interval. |
| `status` | VARCHAR(24) | No | — | No | No | Candidate `pending`, `active`, `retired`, `revoked`, `compromised`; pending | Trust state; exact transition/compromise policy pending. |
| `supersedes_key_id` | UUID | No | IssuerSigningKey | Yes | No | `ON DELETE RESTRICT` | Prior key in rotation chain. |
| `registered_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Registrar, if user system exists. |
| `approved_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Trust approver; bootstrap policy pending. |
| `registered_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Registry-record time, not proof of key possession/issuance time. |
| `revoked_at` | TIMESTAMPTZ | No | — | Yes | No | — | Registry revocation/compromise record time. |
| — | — | — | — | — | `UNIQUE (issuer_id, key_id)` | Composite unique | Key ID unique within issuer. |

## 20. Credential

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal credential key. |
| `credential_id` | VARCHAR(15) | No | — | No | Yes | `CHECK (credential_id ~ '^CRD-[0-9]{4}-[0-9]{6}$')` | Required externally visible credential ID. |
| `award_id` | UUID | No | CredentialAward | No | No | `ON DELETE RESTRICT`; composite context FK | Stable uniqueness/replacement lineage. |
| `learner_id` | UUID | No | Learner | No | Scope unique | `ON DELETE RESTRICT` | Credential subject. |
| `credential_scope_id` | UUID | No | CredentialScope | No | Scope unique | `ON DELETE RESTRICT` | Stable award scope, not a rule/decision version. |
| `issuer_id` | UUID | No | Issuer | No | No | `ON DELETE RESTRICT` | Historical issuer of record; never rewritten after issue. |
| `rule_version_id` | UUID | No | CredentialRuleVersion | No | No | `ON DELETE RESTRICT` | Rule version referenced by the issuance snapshot. |
| `eligibility_decision_id` | UUID | No | EligibilityDecision | No | Yes | `ON DELETE RESTRICT`; composite consistency FK | Passing decision authorizing at most one artifact; cannot define award uniqueness. |
| `replacement_of_credential_id` | UUID | No | Credential | Yes | Conditional | `ON DELETE RESTRICT`; replacement policy pending | Predecessor for an explicitly authorized replacement/reissue. |
| `issued_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Recorded system issue time; not independently trusted signing-time proof. |
| `payload_version` | VARCHAR(32) | No | — | No | No | Approved canonical format version | Canonical serialization/schema version. |
| `canonical_payload` | BYTEA | No | — | No | No | Exact canonical signed bytes; protect access | Preserves bytes used for digest/signature verification. |
| `sha256_digest` | BYTEA | No | — | No | No | `CHECK (octet_length(sha256_digest)=32)` | SHA-256 digest of canonical payload bytes. |
| `signature` | BYTEA | No | — | No | No | Required by MVP assumption IA-07 | Digital signature bytes. |
| `signature_algorithm` | VARCHAR(40) | No | — | No | No | `Ed25519`; signature is 64 bytes | Algorithm identifier. |
| `signing_key_id` | UUID | No | IssuerSigningKey | No | No | `ON DELETE RESTRICT`; must belong to issuer | Historical signing key reference. |
| — | — | — | — | — | `UNIQUE (award_id) WHERE replacement_of_credential_id IS NULL` | Partial unique index | Allows one root credential per award; replacements stay in the same award and require an immediate predecessor. |
| — | — | — | — | — | `UNIQUE (replacement_of_credential_id)` | Unique | Each credential can have at most one replacement successor; replacement requires a revoked predecessor in the same award. |
| — | — | — | — | — | Signature/key integrity | All three signature fields are `NOT NULL`; composite issuer/key FK | Requires a signed artifact and binds its signing key to the issuer. |
| — | — | — | — | — | Issuer/key consistency | Composite FK | Ensures `signing_key_id` belongs to `issuer_id`. |

## 21. CredentialTimestampEvidence (conditional)

Only include if an independent trusted timestamp source/evidence mechanism is approved. An ordinary database timestamp is not a substitute.

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Evidence record key. |
| `credential_id` | UUID | No | Credential | No | No | `ON DELETE RESTRICT` | Credential/signature to which evidence applies. |
| `evidence_type` | VARCHAR(40) | No | — | No | No | Approved evidence type pending | Trusted timestamp/attestation scheme. |
| `provider_reference` | VARCHAR(200) | No | — | Yes | No | — | External provider/receipt identifier. |
| `proof_bytes` | BYTEA | No | — | Yes | No | Retention and size policy pending | Verifiable token/proof, if permitted. |
| `asserted_signing_time` | TIMESTAMPTZ | No | — | No | No | Must be supported by proof | Time asserted by evidence provider, not a DB insertion timestamp. |
| `subject_digest` | BYTEA | No | — | No | No | Digest contract pending | Digest bound to timestamp proof. |
| `validation_status` | VARCHAR(24) | No | — | No | No | Candidate `valid`, `invalid`, `unavailable`; pending | Verification result for proof. |
| `validated_at` | TIMESTAMPTZ | No | — | Yes | No | — | Time evidence was checked. |

## 22. VerificationRequest

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Internal request key. |
| `verification_id` | VARCHAR(15) | No | — | No | Yes | `CHECK (verification_id ~ '^VER-[0-9]{4}-[0-9]{6}$')` | Required externally visible request ID. |
| `mode` | VARCHAR(24) | No | — | No | No | Candidate `credential_id`, `signed_payload`; pending | Distinguishes lookup from portable payload mode. |
| `submitted_credential_id` | VARCHAR(16) | No | — | Conditional | No | Format check when present | Credential ID supplied by caller; may be unknown. |
| `credential_id_fk` | UUID | No | Credential | Yes | No | `ON DELETE RESTRICT` | Resolved registry credential, null for unknown/self-contained payload. |
| `resolved_issuer_id` | UUID | No | Issuer | Yes | No | `ON DELETE RESTRICT` | Issuer identity resolved for verification, when known. |
| `resolved_signing_key_id` | UUID | No | IssuerSigningKey | Yes | No | `ON DELETE RESTRICT` | Historical key record used to verify this request, when resolved. |
| `input_digest` | BYTEA | No | — | Yes | No | 32 bytes if present | Digest of submitted input for correlation without retaining raw payload. |
| `integrity_result` | VARCHAR(24) | No | — | No | No | Approved values pending | Digest/payload integrity result. |
| `issuer_trust_result` | VARCHAR(24) | No | — | No | No | Approved values pending | Signature/key/issuer trust result. |
| `lifecycle_result` | VARCHAR(24) | No | — | No | No | Approved values pending | Active/revoked/unknown/unavailable dimension. |
| `overall_result` | VARCHAR(32) | No | — | No | No | Approved values pending | Aggregated public/business result, never active on unavailable required checks. |
| `requester_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Authenticated requester if applicable. |
| `requester_reference` | VARCHAR(200) | No | — | Yes | No | Minimize and redact | Non-user verifier/client reference if approved. |
| `requested_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Request receipt time. |
| `completed_at` | TIMESTAMPTZ | No | — | Yes | No | `CHECK (completed_at IS NULL OR completed_at >= requested_at)` | Processing completion time. |
| `correlation_id` | UUID | No | — | Yes | No | — | Request tracing identifier. |

## 23. Revocation

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Revocation-event key. |
| `credential_id` | UUID | No | Credential | No | Unique for one-time terminal revocation proposal | `ON DELETE RESTRICT` | Credential affected; repeated request behavior pending. |
| `reason_code` | VARCHAR(64) | No | — | No | No | Controlled vocabulary pending | Machine-readable reason. |
| `reason_detail` | TEXT | No | — | Yes | No | Restricted access; no public disclosure by default | Optional private explanation. |
| `recorded_by_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | Human actor when applicable. |
| `actor_reference` | VARCHAR(200) | No | — | No | No | Non-empty service or actor identity | Preserved attribution even for non-user actors. |
| `effective_at` | TIMESTAMPTZ | No | — | No | No | Required; immediate/future semantics pending | Time revocation takes effect. |
| `recorded_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Time revocation was stored; do not overwrite. |
| `correlation_id` | UUID | No | — | Yes | No | — | Request/event correlation. |

## 24. IdempotencyRecord

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Idempotency record key. |
| `principal_key` | VARCHAR(200) | No | — | No | Composite unique | Stable caller/service identity; not raw token | Idempotency principal scope. |
| `operation` | VARCHAR(100) | No | — | No | Composite unique | Non-empty versioned operation name | Operation namespace. |
| `idempotency_key_digest` | BYTEA | No | — | No | Composite unique | Hash raw key; do not store/log raw key | Client retry key digest. |
| `request_fingerprint` | BYTEA | No | — | No | No | 32 bytes if SHA-256 chosen | Canonical request fingerprint; same-key/different-request conflict. |
| `credential_id_fk` | UUID | No | Credential | Yes | No | `ON DELETE RESTRICT` | Resulting credential reference, if committed. |
| `state` | VARCHAR(24) | No | — | No | No | Candidate `in_progress`, `completed`, `failed`; pending | Retry processing state. |
| `created_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | First request time. |
| `expires_at` | TIMESTAMPTZ | No | — | No | No | Greater than creation; retention pending | Idempotency record retention end. |
| — | — | — | — | — | `UNIQUE (principal_key, operation, idempotency_key_digest)` | Composite unique | Prevent duplicate operation key in its principal scope. |

## 25. AuditEvent

| Attribute | PostgreSQL type | PK | FK → entity | Nullable | Unique | Default / validation / constraint | Description / business meaning |
|---|---|---:|---|---:|---:|---|---|
| `id` | UUID | Yes | — | No | Yes | `gen_random_uuid()` | Audit event key. |
| `event_type` | VARCHAR(100) | No | — | No | No | Controlled event vocabulary; extend by versioning | Business/security action. |
| `outcome` | VARCHAR(24) | No | — | No | No | Candidate success/denied/failed; pending | Result category. |
| `actor_user_id` | UUID | No | User | Yes | No | `ON DELETE RESTRICT` | User actor when available; service actors may have no user row. |
| `actor_reference` | VARCHAR(200) | No | — | No | No | Non-empty | Immutable actor/principal snapshot. |
| `target_type` | VARCHAR(64) | No | — | Yes | No | Controlled entity vocabulary | Type for generic aggregate reference. |
| `target_reference` | VARCHAR(200) | No | — | Yes | No | Stable external/business ID where available | Generic target reference; deliberately not a polymorphic FK. |
| `occurred_at` | TIMESTAMPTZ | No | — | No | No | `CURRENT_TIMESTAMP` | Recorded event time; not independently trusted timestamp proof. |
| `correlation_id` | UUID | No | — | Yes | No | — | Groups events from one request/workflow. |
| `reason_code` | VARCHAR(64) | No | — | Yes | No | Controlled vocabulary pending | Safe reason reference. |
| `event_data` | JSONB | No | — | Yes | No | Object only; strict allowlist; redact secrets/PII | Bounded immutable event details and version references. |

## 26. Proposed indexes and cross-table constraints

These are logical candidates; actual plans must be confirmed against query patterns and the selected PostgreSQL version.

| Table | Candidate index/constraint | Purpose / caveat |
|---|---|---|
| `Learner` | Unique `learner_id`; non-unique normalized name/search index only if needed | Required ID integrity; duplicate names must remain possible. |
| `Course` | Unique `course_code`; index status/effective dates if filtered | Catalogue lookup. |
| `CredentialScope` | Unique `course_id` | MVP permits one immutable course scope per course. Program scopes are deferred. |
| `CredentialAward` | Unique `(learner_id, credential_scope_id)` | Stable award identity independent of decision/rule/issuer/idempotency; original and replacements share one award slot. |
| `Enrollment` | `(learner_id, course_id, enrolled_at DESC)` | Learner-course history; do not assume one enrollment ever unless approved. |
| `CompletionRecord` | `(learner_id, course_id, completed_at)`; unique `enrollment_id` only if enrollment semantics approved | Eligibility lookups and completion history. |
| `AssessmentAttempt` | Unique `(completion_record_id, assessment_key, attempt_number)`; index `(completion_record_id, assessment_key, submitted_at)` | Preserve attempts and support deterministic policy evaluation. |
| `CredentialRuleVersion` | Unique `(rule_id, version_number)`; `(credential_scope_id, effective_from, effective_to)` | Rule lookup; prevent overlapping active versions only after overlap semantics are approved. |
| `EligibilityDecision` | `(learner_id, evaluated_at DESC)`; `(rule_version_id, evaluated_at DESC)` | Investigation and decision history. |
| `Credential` | Unique `credential_id`; unique decision; one root per award (partial unique); one successor per predecessor | ID verification and award-lineage integrity. Award identity is enforced by CredentialAward. |
| `IssuerSigningKey` | Unique `(issuer_id, key_id)` and `(issuer_id, fingerprint)`; validity lookup | Trust resolution and rotation history. |
| `VerificationRequest` | Unique `verification_id`; `(credential_id_fk, requested_at DESC)`; `(requested_at DESC)` | Audit/analytics. Keep requester/IP data out unless approved. |
| `Revocation` | Unique `credential_id` for one-time revocation proposal; index `(effective_at)` | Current status lookup. Revocation correction/reinstatement policy may change this. |
| `AuditEvent` | `(target_type, target_reference, occurred_at)`; `(correlation_id)`; `(occurred_at)` | Timeline reconstruction and reporting; append-only access patterns. |
| `IdempotencyRecord` | Unique `(principal_key, operation, idempotency_key_digest)`; `(expires_at)` | Safe retry and expiry cleanup under approved retention policy. |

**Cross-table integrity:** Enforce learner/scope/rule/decision consistency for each Credential, issuer/key ownership, attempt/completion consistency, and evidence/decision learner consistency using composite foreign keys where practical. Where a declarative FK is not practical, validate within the same transaction and test against concurrent changes. Never rely on a new `eligibility_decision_id` to bypass the Credential uniqueness constraint.

## 27. Status vocabularies, transitions, and pending constraints

Use `VARCHAR` plus approved `CHECK` constraints or lookup tables after business review; do not settle enum lists in this draft. At minimum the implementation must validate allowed values and lifecycle transitions for course, enrollment, completion, attempt, rule version, eligibility decision, issuer, signing key, verification outcome, revocation, and user/role state. Timestamp order and score boundaries are constrained where independent of unresolved policy. Further constraints (allowed score maximum, assessment result vocabulary, rule overlap, future revocation, retry retention, replacement chain, compromised-key cutoff) are **PENDING USER APPROVAL**.

## 28. Privacy and data-retention notes

- Learner name and signed credential payload can be sensitive; minimize payload claims and restrict access.
- Do not store raw portable verification payloads or raw idempotency keys by default. Store a digest and outcome, subject to approved retention requirements.
- Verification requester metadata, IP address, consent, and retention are unresolved; omit IP from this baseline logical schema.
- Audit event data must use a field allowlist and redact credentials, secrets, private keys, raw payloads, and unnecessary PII.
- Public signing keys may be stored; private keys must remain in protected key custody outside ordinary tables.
