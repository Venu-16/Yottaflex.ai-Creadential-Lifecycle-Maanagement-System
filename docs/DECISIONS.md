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

**No project-specific architecture or business decisions are recorded as approved** in the inspected repository or available handover record.

The listed stack, actor names, entities, volumes, seed, anomaly scenarios, deliverables, and acceptance criteria are user-mandated requirements; they are not inferred approvals of unprovided implementation details.

## Proposed architecture direction (not approved)

These are planning proposals only, not decisions:

1. Retain the existing modular FastAPI, versioned API, SQLAlchemy/Alembic, React/Vite, and Docker Compose scaffold, since it matches the required stack.
2. Keep the mandatory entities as the domain vocabulary and introduce supporting entities only when relationships or workflows justify them.
3. Treat generation, ground truth, validation, and reproducibility as explicit data-pipeline components rather than mixing ground-truth labels into application decision logic or features.
4. Trace each acceptance criterion to implementation and automated verification before declaring completion.

No cryptographic algorithm/key scheme, auth provider, role-permission matrix, database relationship design, audit immutability mechanism, generator format, or rule DSL is proposed as finalized here.

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
| — | — | No approved project-specific decision recorded. | — | — |

## Phase 2 architecture proposal register — pending approval

The proposal is documented in [system-architecture.md](system-architecture.md). Each recommendation remains **PENDING USER APPROVAL** and is not an approved decision. The architecture document describes options, consequences, recommendations, component boundaries, workflows, API groups, lifecycle, security, audit, risks, and diagrams. No recommendation authorizes implementation by itself.

The stipulated external identifier formats `LRN-000001` and `CRD-2026-000001` are requirements to preserve, not pending decisions. ARCH-30 tracks only their unresolved year/sequence allocation, padding/overflow, and other entity-format details.

| ID | Topic | Status |
|---|---|---|
| ARCH-00 | Architecture/deployment style: modular monolith versus microservices | **PENDING USER APPROVAL** |
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
