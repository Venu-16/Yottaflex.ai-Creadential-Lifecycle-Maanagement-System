# Logical Entity Catalogue — Step 4.1

**Status: DRAFT FOR REVIEW.** This is a logical database proposal prepared for Phase 4 Step 4.1. It is not an approved schema, SQLAlchemy model set, migration, or database implementation. Phase 2 architecture remains **IN REVIEW** and Phase 3 identity/access implementation is not present. Original requirements in [original-problem-statement.md](../original-problem-statement.md) remain binding. Unresolved design choices below are **PENDING USER APPROVAL** and must not be inferred from this proposal.

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
| `Credential` | Mandatory | Immutable issued credential artifact, identifiers, issuer/rule/evidence references, digest/signature metadata, and replacement link. | Current status is derived from immutable revocation records; do not make a mutable status column the only source of truth. |
| `Issuer` | Mandatory | Stable identity of an organization/authority that issues credentials. | Issuer changes must not rewrite historical credential attribution. |
| `VerificationRequest` | Mandatory | Append-only record of a credential-ID or portable-payload verification request and its separate outcomes. | Minimize requester/subject data; do not retain raw portable payload by default. |
| `Revocation` | Mandatory | Authorized revocation event, actor, reason, effective time, and recorded time. | Append-only; a credential's revocation must not be overwritten. Reinstatement/correction behavior is unresolved. |
| `AuditEvent` | Mandatory | Attributed, append-only business/security event for traceability. | No cascading deletion. A generic target reference is not a foreign key; domain rows must also keep their own integrity. |

## 3. Supporting entities evaluated

| Entity | Proposed status | Why it is needed / when optional | Key relationships |
|---|---|---|---|
| `User` | Optional, recommended if local authentication is approved | Stores account identity, password hash or external subject, and account state; keep separate from learner identity because staff, verifiers, and learners have different account lifecycles. Authentication/account model is pending. | Optional one-to-one learner link; roles, audit attribution, enrollment/attempt/issuer actions. |
| `Role` | Optional, recommended with `User` | Controlled role vocabulary for the six required actors; does not itself settle permissions. | Many-to-many with User through UserRole. |
| `UserRole` | Optional, recommended with `User`/`Role` | Effective-dated grant/revocation history; avoids a comma-separated roles field and permits auditable changes. | Belongs to one User and one Role. |
| `Enrollment` | Proposed supporting entity | Captures learner-course participation and effective lifecycle independently from eventual completion. Include if enrollment is part of the approved workflow. | Learner-Course bridge; optional parent of CompletionRecord. |
| `AssessmentAttempt` | Proposed supporting entity | Preserves every assessment sitting, score/result, grading time, and correction/supersession reference. Necessary to meet retry-history requirements without overwriting earlier attempts. | Child of CompletionRecord; referenced by EligibilityEvidence. |
| `CredentialRuleVersion` | Proposed supporting entity | Gives eligibility rules immutable version/effective-date identity for decisions and issued credentials. | Child of CredentialRule; references CredentialScope; joined to required courses via RuleCourse. |
| `RuleCourse` | Conditional bridge | Needed when a rule version covers one or more courses or a program. If rules are strictly single-course, a direct FK might suffice, but that scope is not approved. | Many-to-many CredentialRuleVersion-Course bridge. |
| `EligibilityDecision` | Proposed supporting entity | Preserves each evaluation outcome, timestamp, rule version, learner, reasons, and evidence snapshot references. New decision IDs do not define issuance uniqueness. | Learner and rule version; one normal credential at most per decision; evidence/reason children. |
| `EligibilityReason` | Proposed supporting child | Normalized reason codes and safe explanatory detail for a decision, instead of an opaque list field. | Many reasons per EligibilityDecision. |
| `EligibilityEvidence` | Proposed supporting child | Normalized, traceable links from a decision to the exact completion and assessment records considered/selected. | Belongs to EligibilityDecision; points to a CompletionRecord or AssessmentAttempt. Exactly-one evidence-source rule. |
| `CredentialScope` | Proposed supporting entity | Stable award identity used by both rule versions and credentials; allows issuance uniqueness to survive rule-version/decision changes. | Represents a course or program scope; referenced by CredentialRuleVersion and Credential. |
| `Program` | Conditional supporting entity | Required only if program-level credentials are approved. | ProgramCourse bridge and CredentialScope. |
| `ProgramCourse` | Conditional bridge | Represents program composition if a Program entity is adopted. | Many-to-many Program-Course. |
| `IssuerSigningKey` | Proposed supporting entity | Public-key trust registry metadata for issuer/key ID, validity, state, and rotation history. | Child of Issuer; referenced by signed Credential. Private keys are excluded. |
| `CredentialTimestampEvidence` | Conditional supporting entity | Separates independent trusted timestamp proof from ordinary recorded issuance time; needed only if such a timestamp service/evidence is approved. | Child of Credential; retains proof reference/bytes and validation result. |
| `IdempotencyRecord` | Proposed supporting entity | Makes issuance retries safe and detects same-key/different-request reuse. It complements, not replaces, business uniqueness constraints. | Unique caller/operation/key digest; optional reference to resulting Credential. |

## 4. Additional identity, lifecycle, and uniqueness notes

1. **Credential scope and business uniqueness:** `CredentialScope` is a stable award target, distinct from `CredentialRuleVersion` and `EligibilityDecision`. Proposed normal issuance uniqueness is `(learner_id, credential_scope_id)` unless an approved repeatable award-cycle dimension is added. A replacement/reissue is a separate approved exception with a distinct credential ID and predecessor reference; it is not enabled by changing a decision, rule, issuer, or idempotency key. The actual scope and replacement policy are **PENDING USER APPROVAL**.
2. **Assessment history:** A CompletionRecord contains course-level progress/completion. Each AssessmentAttempt is append-only; corrections point to a superseded attempt rather than erasing it. `latest`, `highest`, `any_pass`, scale normalization, tie handling, and missing/ungraded-attempt behavior remain **PENDING USER APPROVAL**.
3. **Credential status:** No mutable credential status is required as the authoritative fact. Effective revocation is derived from the Revocation record and agreed time policy; a cached status, if later needed, is a controlled denormalization and must be reconciled atomically.
4. **Timestamps:** `issued_at` and audit/database timestamps preserve recorded chronology. They do not independently prove signing time. Only separately validated trusted timestamp evidence can support that stronger claim; its source and adoption are **PENDING USER APPROVAL**.
5. **Duplicate-ID anomaly:** Keep production unique constraints. Represent the duplicate pair in an isolated pre-ingestion data fixture and validate both records before loading; separately assert a second insert fails in a disposable test database with the production constraint enabled.

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

## 6. Implementation boundary

This catalogue and its companion [data dictionary](data-dictionary.md) and [relationship specification](relationship-specification.md) are logical proposals only. No database table, SQL initialization script, ORM model, or migration has been created. Phase 2 remains **IN REVIEW**; this Step 4.1 documentation is not approval of any pending decision and does not complete Phase 4.
