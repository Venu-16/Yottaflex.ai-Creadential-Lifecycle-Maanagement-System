# Logical Entity Catalogue — Step 4.1

**Status: MVP DESIGN BASELINE.** This catalogue informs the initial SQLAlchemy schema and Alembic migration. The modular-monolith architecture baseline is approved; implementation assumptions remain separate from user-approved policy in [DECISIONS.md](../DECISIONS.md). The original requirements in [original-problem-statement.md](../original-problem-statement.md) remain binding.

## 1. Design scope and modeling principles

- Keep internal primary keys (proposed PostgreSQL `UUID`) separate from external identifiers. Preserve stipulated formats `LRN-000001`, `CRD-2026-000001`, and `VER-2026-000001`. Only allocation semantics such as year source, sequence scope, padding/overflow, and identifiers for other entities are pending.
- Preserve decisions, attempts, issuance artifacts, revocations, verification requests, key history, and audit events. Prefer archival/soft deactivation and `ON DELETE RESTRICT`; do not cascade-delete audit or lifecycle history.
- Do not let a new eligibility-decision or rule-version ID bypass normal credential-issuance uniqueness. Proposed uniqueness is by learner and stable credential scope; repeatable award cycles require explicit approval.
- Represent assessment sittings separately from course-level completion. Record the chosen attempt/evidence references on an eligibility decision, without selecting a final attempt policy here.
- Never store private signing keys in PostgreSQL. A public-key trust registry is proposed; key algorithm, custody, bootstrap, timestamp evidence, and compromise policy remain unresolved.
- Treat the canonical signed payload as bytes, not a reserialized JSON object. A stored `issued_at` or database `recorded_at` is not independently trusted evidence of signing time.
- Use `JSONB` only for versioned rule expressions and bounded/redacted event or reason details. Keep entities, relationships, and evidence references relational.

## 2. Mandatory core entities

| Entity | Required? | Purpose and lifecycle | Design notes |
|---|---|---|---|
| `Learner` | Mandatory | Person receiving credentials; externally visible learner identifier and permitted learner profile data. | Names are not unique; duplicate learner names are explicitly required. Link to a login account only if approved. |
| `Course` | Mandatory | Course catalogue item, lifecycle, and effective dates. | Course business-code format and repeat offering/term model are unresolved. |
| `CredentialRule` | Mandatory | Stable identity for a named eligibility rule family. | Rule changes are represented by child `CredentialRuleVersion` records, not edits to a version relied on historically. |
| `CompletionRecord` | Mandatory | Learner/course-level progress or completion outcome with provenance and dates. | Distinct from assessment attempts; proposed to belong to one enrollment when enrollment is used. |
| `Credential` | Mandatory | Immutable issued credential artifact, identifiers, issuer/rule/evidence references, digest/signature metadata, and replacement link. | Current status is derived from immutable revocation records; all artifact revisions belong to one CredentialAward. |
| `Issuer` | Mandatory | Stable identity of an organization/authority that issues credentials. | Issuer identity stays stable; profile changes append before/after profile snapshots to AuditEvent, while each credential payload preserves its issuance-time issuer details. |
| `VerificationRequest` | Mandatory | Append-only record of a credential-ID or portable-payload verification request and its separate outcomes. | Minimize requester/subject data; do not retain raw portable payload by default. |
| `Revocation` | Mandatory | Authorized revocation event, actor, reason, effective time, and recorded time. | Append-only; a credential's revocation must not be overwritten. Reinstatement/correction behavior is unresolved. |
| `AuditEvent` | Mandatory | Attributed, append-only business/security event for traceability. | No cascading deletion. A generic target reference is not a foreign key; domain rows must also keep their own integrity. |

## 3. Supporting entities evaluated

| Entity | Proposed status | Why it is needed / when optional | Key relationships |
|---|---|---|---|
| `User` | MVP supporting entity; authentication is not implemented | Stores account identity, optional password hash/external subject, and account state; separate from learner identity. | Optional one-to-one learner link; roles and audit attribution. |
| `Role` | MVP supporting entity; permissions remain deny-by-default | Controlled role vocabulary for the six required actors; storing roles does not grant application access. | Many-to-many with User through UserRole. |
| `UserRole` | MVP supporting entity; no role-management API yet | Effective-dated grant/revocation history; avoids a delimited roles field and supports later audit. | Belongs to one User and one Role. |
| `Enrollment` | Proposed supporting entity | Captures learner-course participation and effective lifecycle independently from eventual completion. Include if enrollment is part of the approved workflow. | Learner-Course bridge; optional parent of CompletionRecord. |
| `AssessmentAttempt` | Proposed supporting entity | Preserves every assessment sitting, score/result, grading time, and correction/supersession reference. Necessary to meet retry-history requirements without overwriting earlier attempts. | Child of CompletionRecord; referenced by EligibilityEvidence. |
| `CredentialRuleVersion` | Proposed supporting entity | Gives eligibility rules immutable version/effective-date identity for decisions and issued credentials. | Child of CredentialRule; references CredentialScope; joined to required courses via RuleCourse. |
| `RuleCourse` | MVP supporting bridge | Allows a course award rule to specify required/prerequisite courses without embedding IDs in JSON. | Many-to-many CredentialRuleVersion-Course bridge. |
| `EligibilityDecision` | Proposed supporting entity | Preserves each evaluation outcome, timestamp, rule version, learner, reasons, and evidence snapshot references. New decision IDs do not define issuance uniqueness. | Learner and rule version; one normal credential at most per decision; evidence/reason children. |
| `EligibilityReason` | Proposed supporting child | Normalized reason codes and safe explanatory detail for a decision, instead of an opaque list field. | Many reasons per EligibilityDecision. |
| `EligibilityEvidence` | Proposed supporting child | Normalized, traceable links from a decision to the exact completion and assessment records considered/selected. | Belongs to EligibilityDecision; points to a CompletionRecord or AssessmentAttempt. Exactly-one evidence-source rule. |
| `CredentialScope` | MVP supporting entity | Stable course award identity used by rules, decisions, awards, and credentials; decouples uniqueness from rule/evaluation versions. | One row per course in the MVP; program scopes are deferred. |
| `CredentialAward` | Proposed supporting entity; MVP | One stable award entitlement per learner and scope, independent of evaluations or rule versions. | Unique `(learner_id, credential_scope_id)`; original and replacement Credential artifacts share this slot. |
| `Program` | Conditional supporting entity | Required only if program-level credentials are approved. | ProgramCourse bridge and CredentialScope. |
| `ProgramCourse` | Conditional bridge | Represents program composition if a Program entity is adopted. | Many-to-many Program-Course. |
| `IssuerSigningKey` | MVP supporting entity | Public-key trust registry metadata for issuer/key ID, validity, state, and rotation history. | Child of Issuer; referenced by every signed Credential. MVP Ed25519 public keys are 32 bytes; private keys are excluded. |
| `CredentialTimestampEvidence` | Conditional supporting entity | Separates independent trusted timestamp proof from ordinary recorded issuance time; needed only if such a timestamp service/evidence is approved. | Child of Credential; retains proof reference/bytes and validation result. |
| `IdempotencyRecord` | Proposed supporting entity | Makes issuance retries safe and detects same-key/different-request reuse. It complements, not replaces, business uniqueness constraints. | Unique caller/operation/key digest; optional reference to resulting Credential. |

## 4. Additional identity, lifecycle, and uniqueness notes

1. **Credential scope and business uniqueness:** MVP scope is course-only: one stable `CredentialScope` per course. One `CredentialAward` row is unique by `(learner_id, credential_scope_id)` and is created transactionally with the first passing issuance. Every original/replacement credential artifact references that award. A replacement requires a revoked predecessor, has a distinct credential ID, stays in the same award, and each predecessor has at most one successor. Reinstatement and repeatable award cycles are disabled. These are implementation assumptions IA-01/06/09, not user-approved business policy.
2. **Assessment history:** A CompletionRecord contains course-level progress/completion. Each AssessmentAttempt is append-only; corrections point to a superseded attempt rather than erasing it. `latest`, `highest`, `any_pass`, scale normalization, tie handling, and missing/ungraded-attempt behavior remain **PENDING USER APPROVAL**.
3. **Credential status:** No mutable credential status is required as the authoritative fact. Effective revocation is derived from the Revocation record and agreed time policy; a cached status, if later needed, is a controlled denormalization and must be reconciled atomically.
4. **Timestamps:** `issued_at` and audit/database timestamps preserve recorded chronology. They do not independently prove signing time. Only separately validated trusted timestamp evidence can support that stronger claim; its source and adoption are **PENDING USER APPROVAL**.
5. **Evidence and issuer snapshots:** Each immutable EligibilityDecision stores evaluator/rule-format versions and canonical evidence JSON plus SHA-256 digest; child EligibilityEvidence rows retain per-source snapshots/digests. Issuer profile edits append before/after values to AuditEvent, and credentials preserve issuer-at-issue details in their canonical payload.
6. **Duplicate-ID anomaly:** Keep production unique constraints. Represent the duplicate pair in an isolated pre-ingestion data fixture and validate both records before loading; separately assert a second insert fails in a disposable test database with the production constraint enabled.

## 5. Pending design decisions and database impact

| Topic | Status | Database impact if unresolved |
|---|---|---|
| Credential scope: course, program, or both | **PENDING USER APPROVAL** | Determines whether Program/ProgramCourse are needed and the shape of CredentialScope and RuleCourse. |
| Credential business uniqueness and repeatable award cycles | **PENDING USER APPROVAL** | Determines the scope uniqueness index; decision/rule IDs must not be used to bypass normal uniqueness. |
| Replacement, reissue, reinstatement, and revocation corrections | **PENDING USER APPROVAL** | Determines Credential self-reference/unique policy and whether Revocation can have only one effective row or needs append-only correction events. |
| Attempt-selection and assessment semantics | **PENDING USER APPROVAL** | Affects CredentialRuleVersion policy fields and EligibilityEvidence selection references; never overwrites attempts. |
| Enrollment requirement and course offerings | **PENDING USER APPROVAL** | Determines whether Enrollment is mandatory and whether enrollment uniqueness includes a term/attempt cycle. |
| User/account model and actor permissions | **PENDING USER APPROVAL** | Determines User identity columns, nullable learner link, Role grants, and actor FKs. |
| Signature algorithm, canonicalization, key bootstrap/rotation/compromise policy | **PENDING USER APPROVAL** | Determines which signature fields are required and key validity constraints; private keys remain outside ordinary tables. |
| Independent timestamp evidence | **PENDING USER APPROVAL** | Determines whether CredentialTimestampEvidence is implemented and what proof is accepted. A database timestamp alone is insufficient. |
| Verification authentication, disclosure, retention, and availability response | **PENDING USER APPROVAL** | Determines nullable requester references, metadata retention, payload retention (default none), and response outcome vocabularies. |
| Entity status vocabularies and effective-date semantics | **PENDING USER APPROVAL** | Determines enum/check/lookup constraints and transition validation; do not invent final enum lists here. |
| Domain identifier allocation semantics | **PENDING USER APPROVAL** | Formats LRN-000001, CRD-2026-000001, and VER-2026-000001 are preserved; year source, sequence scope, padding/overflow, and other entity identifiers remain open. |
| Audit threat model, retention, and hard immutability guarantees | **PENDING USER APPROVAL** | Determines storage, privilege, retention, tamper-evidence, and export controls; append-only application behavior alone is not absolute immutability. |

## 6. Normalization assessment

- **First Normal Form (1NF):** Store one value per relational column. Course membership, user roles, assessment attempts, eligibility reasons, and evaluation evidence use separate rows rather than delimited lists. `JSONB` is limited to versioned rule expressions and bounded/redacted event details; it must not replace relational IDs or repeating evidence relations.
- **Second Normal Form (2NF):** Bridge-table attributes (for example `RuleCourse` or `ProgramCourse`) describe the full composite relationship key. Do not put course-specific rule values on a rule family when they depend on a particular course/version link.
- **Third Normal Form (3NF):** Keep learner, course, issuer, key, rule-family/version, decision, credential, revocation, verification, and audit facts in their owning entities. Credential lifecycle status is derived from revocation facts rather than copied as an independently writable status.
- **Deliberate denormalization candidate:** `Credential` repeats learner, stable credential scope, rule version, and eligibility-decision references needed to retrieve and enforce issuance invariants directly and to reconstruct the signed award. Use composite FKs/transaction validation to ensure those references agree; treat issued payload bytes as immutable. Any cached lifecycle status or report aggregate would be a separately justified, reconciled projection, not source of truth.

## 7. Implementation boundary

This catalogue and its companion [data dictionary](data-dictionary.md) and [relationship specification](relationship-specification.md) describe the logical baseline. Twenty-three MVP entities are implemented as SQLAlchemy tables with Alembic revision `af6e5dad6637`; Program, ProgramCourse, and CredentialTimestampEvidence are deferred. The schema does not complete Phase 4 or approve pending product decisions.
