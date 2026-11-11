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
