# Decisions and Requirements Register

This register distinguishes binding user requirements from architecture proposals, user-approved decisions, and unresolved questions. A proposal is not an approval. Do not implement a proposal as settled fact without user approval when it materially affects business behavior, security, data, or acceptance.

## Binding original requirements (not architecture decisions)

The full text is preserved at [original-problem-statement.md](original-problem-statement.md). Requirements include:

- Required technology stack: Python/FastAPI/SQLAlchemy/PostgreSQL/Alembic/Pydantic/JWT/Pytest; React/Vite/JavaScript/Tailwind/React Router/Axios/Lucide React; Docker and Docker Compose.
- Six actors: Learner, Instructor, Academic Administrator, Support Staff, Platform Administrator, and Third-party Verifier.
- Nine mandatory entities: Learner, Course, CredentialRule, CompletionRecord, Credential, Issuer, VerificationRequest, Revocation, and AuditEvent. Supporting entities may be justified. Every entity needs a primary key, appropriate foreign keys, documented cardinality, optional relationship definitions, lifecycle states, and effective dates where applicable.
- Data volumes: 20,000 learners, 1,000 courses, 10,000 credentials, and 5,000 verification requests.
- Fixed generator seed: `20261022`; parameterized generation; valid baseline first and labelled edge cases afterward.
- Mandatory anomalies: credential issued before completion; duplicate credential ID; revoked credential verifies as active; altered payload hash not detected.
- Data quality, separate ground truth, deliverables, lawful provenance, two-run reproducibility, evaluation criteria, and success criteria as fully enumerated in the source statement.

These requirements are binding regardless of whether an implementation decision is still pending.

## Approved decisions

The user explicitly directed on 2026-11-11 to use the existing architecture and original problem statement as the implementation baseline. The modular-monolith architecture and required technology stack are therefore the approved project baseline. This does **not** approve every business recommendation in `system-architecture.md`; unresolved semantics below are implementation assumptions only and remain subject to later user review.

The listed stack, actor names, entities, volumes, seed, anomaly scenarios, deliverables, and acceptance criteria are user-mandated requirements; they are not inferred approvals of unprovided implementation details.

## Approved architecture baseline

The following baseline is approved by the user's 2026-11-11 instruction:

1. Use the existing modular-monolith architecture and scaffold as the implementation baseline.
2. Preserve all requirements in the original problem statement.
3. Keep ground truth separate from application inputs and decision logic.
4. Trace acceptance criteria to implementation and automated verification.

Unresolved business/security choices below are not silently approved by this baseline.

## Time-boxed implementation assumptions (not user approvals)

To keep delivery moving, use these conservative defaults until the user changes them. They are implementation assumptions, not approved business policy, and must not be described as user-approved decisions.

| ID | Implementation assumption | Scope and safety rationale |
|---|---|---|
| IA-01 | First demonstrable credential scope is an individual course; retain an extensible scope reference and defer program awards. | Minimizes MVP scope while preserving original course requirements. |
| IA-02 | Credential rules are immutable, versioned, and data-configurable; score thresholds are explicit per rule and scale. | Avoids hidden hard-coded eligibility semantics. Do not invent a universal passing score. |
| IA-03 | When a rule uses attempts, select the latest graded, non-superseded attempt for that assessment; deterministic ordering is `(graded_at, attempt_number, id)`. | Avoids selecting a learner's best result after a later failure. The selected policy is snapshotted per evaluation. |
| IA-04 | Only an authorized Academic Administrator may initiate issuance in the MVP; evaluate eligibility before the request and re-check in the issuance transaction. | Conservative manual authority; role grant is seeded/configured, not self-assigned. |
| IA-05 | Public verification returns authenticity/trust and lifecycle outcomes with minimal issuer/course data; no learner name or assessment data. | Data minimization; caller authentication/disclosure policy remains an open product decision. |
| IA-06 | Revocation is terminal for an issued credential. A replacement is a new credential in the same award lineage, requires predecessor revocation and a distinct ID, and cannot create a second award slot. | Preserves history and prevents duplicate awards. Reinstatement is not supported in the MVP. |
| IA-07 | Use SHA-256 over canonical payload bytes plus an Ed25519 signature; require 32-byte public keys and 64-byte signatures; keep private keys outside PostgreSQL and frontend assets. | Provides compact issuer authentication and tamper detection using the existing cryptography-enabled dependency; key custody remains deployment-specific. |
| IA-08 | Use internal UUID keys plus the stipulated external ID formats. `CRD-YYYY-NNNNNN` uses the UTC issuance year and an atomic per-year sequence; learner/verification counters are globally allocated and never recycled. | Preserves formats and prevents race-prone `MAX(id)+1` allocation. |
| IA-09 | One immutable credential award slot exists per learner and course scope. Replacement credentials belong to that slot, reference the immediate predecessor, and each predecessor has at most one successor. | Uniqueness is independent of evaluation/rule snapshots, issuer, and idempotency key. |
| IA-10 | Preserve the evaluated rule version, evaluator version, selected evidence IDs, and a canonical evidence snapshot/digest with each decision. | Enables reproducible investigation even after source records are corrected. |
| IA-11 | Issuer identity is stable. Profile changes create append-only audit snapshots containing the prior and new public profile; credential payload preserves the issuance-time issuer name/code. | Satisfies issuer-change traceability without mutating historical credential attribution. |
| IA-12 | Use database checks/unique/FK constraints for single-row invariants; enforce cross-row invariants in one transaction with row locks and test concurrent conflicts. | PostgreSQL `CHECK` constraints cannot safely enforce conditions across rows. |
| IA-13 | Audit events are append-only by application convention and database privileges; do not claim cryptographic immutability or non-repudiation. | Practical MVP assurance; stronger tamper-evidence is deferred. |
| IA-14 | Omit program, trusted timestamp-evidence, and external authentication-provider tables from the first schema; add them only when their features are approved. | Avoids unused conditional structures and speculative migrations. |
| IA-15 | Synthetic seed generation uses a required-volume `full` profile, a smaller `starter` profile, deterministic test-only identities and keys, and separate ground-truth exports. Synthetic thresholds, status distributions, revocation rates, and issuer changes are fixture parameters, not production policy. | Makes the mandated data and anomaly checks repeatable without turning test distributions into approved business rules. Test private keys derived from the public seed are never suitable for real credentials. |
| IA-16 | Until the actor matrix is approved, deny operational access to roles without an explicit conservative grant. Academic Administrators may manage lifecycle records, evaluate, issue, and revoke; Platform Administrators may manage master data and signing-key trust but may not issue; Learners may list only credentials linked to their own account; only those two admin roles may read learner records/audit/reporting. Instructor and Support Staff operational permissions remain denied. Third-party verification is anonymous and returns only minimal verification metadata. | Avoids inferring broad privileges or object scopes that the schema cannot enforce. This is a temporary restrictive implementation mapping, not approval of the role matrix or anonymous disclosure policy. |
| IA-17 | Hash passwords with salted PBKDF2-HMAC-SHA256 (600,000 iterations), sign JWTs with HS256, and use the configured 30-minute token lifetime. Require at least 32 bytes for the JWT secret; resolve active user and role assignments on every request. | Uses the existing Python/JWT stack and fails closed on account deactivation or role revocation. Password hashing/JWT/session transport remain subject to security review and user policy approval. |
| IA-18 | Require an `Idempotency-Key` for credential issuance; scope its SHA-256 digest by principal and operation for 24 hours, and bind it to a request fingerprint. Identical retries return the original credential. Award-slot uniqueness independently prevents a second root credential even with a new evaluation or idempotency key. | Makes legitimate retries safe without weakening the stable learner/scope uniqueness constraint. Replacement issuance is not exposed until its approval workflow is implemented. |
| IA-19 | Register only Ed25519 public keys; keep the issuer private key in deployment configuration. Credential-ID verification may trust an issuer-registry historical key when the issuer's recorded issue time falls within that key's validity interval. This ordinary database/payload timestamp is not independent trusted-time evidence. Portable verification accepts only a currently trusted key because a signed `issued_at` claim alone cannot prove when a signature was created. Revoked, unavailable, or out-of-period keys fail closed; database unavailability returns an error, not a valid-shaped response. | Supports key rotation and historical database lookup while avoiding trust in client-controlled signing times. Independent timestamp authority, bootstrap of production issuer trust, and stronger key custody remain open. |
| IA-20 | The MVP does not implement credential replacement/reissue. A second issuance for an occupied learner/course award slot is rejected, including after a new evaluation or with a different idempotency key. | Prevents silent overwrite or duplicate awards until an authorized replacement policy is defined and tested. |
| IA-21 | Credential expiration is not supported because the current credential schema and approved policy define no expiry field or lifecycle rule; `EXPIRED` is therefore not emitted. | Avoids inventing an expiry rule or returning an unsupported outcome. |

These assumptions may be changed after review. Changing an assumption that affects stored data requires a migration and must preserve existing history.

## Unresolved decisions requiring clarification

Resolve these with the user when they affect the next implementation:

### Identity and access

- What is the account/login model and identity source?
- Which create/read/update/issue/revoke/verify actions belong to each of the five internal actors?
- What data and operations may a Third-party Verifier access, and is verification anonymous or authenticated?

### Domain and business semantics

- What are the exact entity attributes, ID formats, cardinalities, and delete/update policies?
- How are learners associated with courses and issuers? Is Enrollment required?
- Can a credential rule target one course or multiple courses? How are rule versions and effective dates applied?
- What completion statuses, assessment scales/thresholds, missing-result policies, and date boundaries apply?
- When exactly is eligibility evaluated and how are decision snapshots, re-evaluation, and exceptions persisted?
- Which credential lifecycle states and transitions are permitted? How do issuer changes affect existing credentials?
- What authorization, reason, and effective-time rules govern revocation?

### Cryptography, verification, and audit

- Does the acceptance require a digital signature, deterministic hash, or both? What canonical payload, algorithm, key custody/rotation, issuer trust, and key publication are required for independent verification?
- What does “immutable-style” audit mean for this project: append-only application behavior, database permissions/triggers, hash chaining, or another assurance? What threat model is expected?
- Which verification outcomes and request fields must be recorded, and how should unavailable/unknown issuers or keys be represented?

### Synthetic data and evaluation

- Which output formats (CSV, JSON, SQL) and identifier conventions are required for each dataset?
- What does “starter and full datasets” mean for expected parameters/row counts beyond the stated baseline, if both are needed?
- How should each labelled anomaly fixture be isolated from valid baseline records, and how should expected outcomes be presented?
- What exact source-manifest and reproducibility-report fields are expected? If external data is considered, confirm licensing and provenance before use.

If requirements remain ambiguous, do not silently pick a behavior that changes an acceptance criterion. Ask a focused question and record the answer and date here.

## Decision record format

Add decisions below only after explicit approval. Include date, decision, rationale, alternatives/trade-offs, affected requirements, and approval source.

| Date | ID | Decision | Status | Rationale / trade-off |
|---|---|---|---|---|
| 2026-11-11 | ARCH-BASELINE | Use the existing modular-monolith architecture and original requirements as the implementation baseline. | **APPROVED BY USER** | User direction: proceed using the existing approved architecture; use conservative documented assumptions for unresolved choices. This does not approve each business/security assumption. |

## Architecture and business decision register

The baseline architecture is approved as above. Business/security recommendations in [system-architecture.md](system-architecture.md) remain **PENDING USER APPROVAL** unless separately recorded. Time-boxed defaults are implementation assumptions IA-01–IA-14, not user approval.

The stipulated external identifier formats `LRN-000001` and `CRD-2026-000001` are requirements to preserve, not pending decisions. ARCH-30 tracks only their unresolved year/sequence allocation, padding/overflow, and other entity-format details.

| ID | Topic | Status |
|---|---|---|
| ARCH-00 | Architecture/deployment style: modular monolith versus microservices | **APPROVED BASELINE: modular monolith** |
| ARCH-01 | Credential scope: individual course, program, or both | **PENDING USER APPROVAL** |
| ARCH-02 | Eligibility policy: fixed thresholds, configurable versioned rules, or hybrid | **PENDING USER APPROVAL** |
| ARCH-03 | Assessment attempt selection: latest, highest, any passing, or configurable | **PENDING USER APPROVAL** |
| ARCH-04 | Issuance authority: administrator, dual approval, or automated approval | **PENDING USER APPROVAL** |
| ARCH-05 | Verification disclosure: authenticity/status, issuer/course details, or learner-consented details | **PENDING USER APPROVAL** |
| ARCH-06 | Revocation: permanent, reinstatement, or replacement credential | **PENDING USER APPROVAL** |
| ARCH-07 | Cryptographic approach: SHA-256 only, signature plus SHA-256, or blockchain anchoring | **PENDING USER APPROVAL** |
| ARCH-08 | Authentication: predefined demo accounts, admin-provisioned demo users, or full registration/management | **PENDING USER APPROVAL** |
| ARCH-09 | Actor permission matrix and object-level scope for all six actors | **PENDING USER APPROVAL** |
| ARCH-10 | Learner identity fields, PII, privacy and retention; preserve stipulated `LRN-000001` format | **PENDING USER APPROVAL** |
| ARCH-11 | Issuer ownership, multiplicity, change history, and key attribution | **PENDING USER APPROVAL** |
| ARCH-12 | Enrollment need, relationship cardinalities, effective dates, and delete/update policy | **PENDING USER APPROVAL** |
| ARCH-13 | Rule versions, overlapping applicability, retroactivity, and effective dates | **PENDING USER APPROVAL** |
| ARCH-14 | CompletionRecord versus AssessmentAttempt history, statuses, scales, thresholds, missing results, and corrections | **PENDING USER APPROVAL** |
| ARCH-15 | Evaluation trigger, evidence snapshot/freshness, expiry, supersession, and re-evaluation | **PENDING USER APPROVAL** |
| ARCH-16 | Preserve `CRD-2026-000001`; decide allocation semantics, learner/scope uniqueness, retry/idempotency behavior, and replacement handling | **PENDING USER APPROVAL** |
| ARCH-17 | Signature algorithm/library, canonical payload, issuer-to-key trust registry, key custody/rotation, and trust bootstrap | **PENDING USER APPROVAL** |
| ARCH-18 | Separate credential-ID and portable-payload verification modes, authentication, disclosure, retention, unknown-ID behavior, and rate limits | **PENDING USER APPROVAL** |
| ARCH-19 | Revocation authority, reason, effective time, future dating, and reinstatement/replacement semantics | **PENDING USER APPROVAL** |
| ARCH-20 | Audit immutability threat model, retention, access, clock, and tamper evidence | **PENDING USER APPROVAL** |
| ARCH-21 | Failed/denied operation logging and behavior when audit persistence is unavailable | **PENDING USER APPROVAL** |
| ARCH-22 | API error envelope, pagination, idempotency, and status-code contract | **PENDING USER APPROVAL** |
| ARCH-23 | Synthetic data formats, starter/full profiles, and output layout | **PENDING USER APPROVAL** |
| ARCH-24 | Anomaly fixture isolation and regression/mutant demonstration approach | **PENDING USER APPROVAL** |
| ARCH-25 | Validation report, source manifest, checksum scope, and reproducibility report schemas | **PENDING USER APPROVAL** |
| ARCH-26 | External data provenance or synthetic-only source policy | **PENDING USER APPROVAL** |
| ARCH-27 | Deployment security operations: TLS, gateway, secrets, backups, monitoring, recovery | **PENDING USER APPROVAL** |
| ARCH-28 | Password-hashing algorithm, JWT claims/expiry/revocation, and browser token transport/CSRF controls | **PENDING USER APPROVAL** |
| ARCH-29 | Rate-limit mechanism, thresholds, request sizes, and public verification enumeration policy | **PENDING USER APPROVAL** |
| ARCH-30 | Preserve stipulated `LRN-000001` and `CRD-2026-000001` formats; confirm only year/sequence allocation, padding/overflow, and other entity formats | **PENDING USER APPROVAL** |
| ARCH-31 | Separate course-level CompletionRecord from per-attempt history and choose configurable attempt-selection behavior | **PENDING USER APPROVAL** |
| ARCH-32 | Issuer-to-public-key trust registry, bootstrap, key validity, rotation, historical retention, and compromise policy | **PENDING USER APPROVAL** |
| ARCH-33 | Credential-ID lookup versus portable signed-payload verification guarantees and response contract | **PENDING USER APPROVAL** |
| ARCH-34 | Unavailable/expired/retired/compromised key handling, independently trusted historical timestamp evidence, and unavailable revocation status | **PENDING USER APPROVAL** |
| ARCH-35 | Learner/credential-scope issuance uniqueness independent of decision snapshots, CRD allocation, idempotency, and separately authorized replacement/reissue | **PENDING USER APPROVAL** |

The options, consequences, and recommendations for these decisions are described in Sections 1, 3, 5, 6, and 11 of `system-architecture.md`. The eight minimum business decisions (ARCH-01 through ARCH-08) have explicit option comparisons there; ARCH-00 documents the architecture-style trade-off. Recommendations must not be copied into an approved-decision record until the user explicitly accepts them; record approval date, decision, rationale/trade-off, and approval source.
