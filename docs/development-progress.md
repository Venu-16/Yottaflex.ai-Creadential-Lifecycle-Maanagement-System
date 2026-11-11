# Development Progress and 11-Phase Roadmap

The original hackathon problem statement at [original-problem-statement.md](original-problem-statement.md) is the source of truth. This checklist tracks product work, not merely folder creation. Mark a phase complete only when its work and stated checks are implemented and verified. Do not mark a mandatory acceptance criterion out of scope without explicit user approval and a documented trade-off.

## Status summary

- **Last completed phase:** Phase 1 — Project foundation and initialization.
- **Current product phase:** Phase 2 — System architecture design (**IN REVIEW**, not completed; recommendations and business decisions await user review).
- **Completed checklist items:** Phase 1 only.
- **Remaining:** Phases 2–11.
- **Documentation status:** Project context, AI handover, this roadmap, decisions log, and the complete original requirements document are established. The Phase 2 architecture proposal is in `docs/system-architecture.md`; it is not approved and its recommendations are pending user approval. Documentation work does not itself complete a product phase.

## Phases

- [x] **Phase 1 — Project foundation and initialization.** Create the repository scaffold; initialize FastAPI and React/Vite; configure environment, PostgreSQL/SQLAlchemy, Alembic, CORS, logging, health check, Pytest, Tailwind, API client, Docker Compose, and initial documentation. **Verified:** one health test passes, frontend production build succeeds, local health/page checks succeed, Alembic offline generation is empty, Compose config validates, and isolated PostgreSQL/backend/frontend Compose services passed their checks. No schema or domain behavior is included.

- [ ] **Phase 2 — System architecture and requirements design (IN REVIEW).** Review the modular-monolith architecture proposal, component boundaries/dependencies, workflows, lifecycle, security, API groups, audit, anomaly handling, and risks. Resolve business decisions with the user and distinguish approved choices from proposals in `docs/DECISIONS.md`. **Current:** proposal documented; awaiting user review. **Exit checks:** user-approved architecture/decisions are recorded; no recommendation is treated as approved merely because it appears in the proposal. This phase is not completed.

- [ ] **Phase 3 — Identity, authentication, and authorization.** Clarify account ownership, authentication requirements, actor responsibilities, permission boundaries (Learner, Instructor, Academic Administrator, Support Staff, Platform Administrator, Third-party Verifier), and verifier access. Implement only after Phase 2 requirements are resolved. **Exit checks:** authentication and authorization tests demonstrate allowed and denied access for agreed roles; secrets are not committed.

- [ ] **Phase 4 — Domain model and master data.** Agree and document schema before implementation. Implement mandatory Learner, Course, CredentialRule, CompletionRecord, Credential, Issuer, VerificationRequest, Revocation, and AuditEvent entities and justified supporting entities such as Enrollment, RuleCourse, or EligibilityDecision. Define primary/foreign keys, cardinalities, optional relationships, lifecycle states, effective dates where applicable, and generate/review Alembic migrations. **Exit checks:** schema review, migration upgrade/downgrade checks, and key/relationship integrity tests. No tables currently exist.

- [ ] **Phase 5 — Credential eligibility rule definition.** Agree the rule format, course relationships, effective dates, versions, assessment-attempt semantics, and validation semantics; implement rule management. **Exit checks:** documented business rules, rule validation, and tests for normal, boundary, and invalid rules. Preserve all requirements; do not silently simplify.

- [ ] **Phase 6 — Course completion and assessment tracking.** Capture course completion and assessment outcomes for valid learner/course IDs, including incomplete courses. **Exit checks:** referential integrity, allowed values, date ordering, and assessment/completion validation tests.

- [ ] **Phase 7 — Eligibility evaluation and business decisions.** Evaluate each learner against applicable credential requirements, persist explicit eligibility decisions/outcomes, and expose important decisions and exceptions. **Exit checks:** deterministic rule outcomes have tests and ground-truth comparisons; ineligible learners cannot proceed to issuance.

- [ ] **Phase 8 — Credential issuance and cryptographic integrity.** Issue unique credential identifiers only after all applicable requirements pass. Agree and implement signed-record metadata or deterministic cryptographic hashes and key handling. **Exit checks:** uniqueness and eligibility enforcement; valid data verifies; altered payloads are detected; issuance decisions and events are traceable.

- [ ] **Phase 9 — Verification, revocation, and audit.** Implement third-party credential verification and request tracking, authorized revocation, and immutable-style audit history. **Exit checks:** valid, revoked, altered, unknown, and unavailable-key cases are distinguishable; permitted lifecycle transitions and authorization are enforced; revoked credentials cannot verify as active; event completeness is demonstrated.

- [ ] **Phase 10 — Synthetic data, quality, ground truth, and reproducibility.** Implement parameterized generators using fixed seed **20261022**; produce at least 20,000 learners, 1,000 courses, 10,000 credentials, and 5,000 verification requests, with dependent records using valid parent IDs. Generate valid baseline data first, then inject only labelled edge cases. Include duplicate learner names, incomplete courses, issuer changes, lifecycle variations, and all four mandatory anomaly scenarios. Produce separate ground truth, seed data, source manifest, validation summary, and reproducibility report. **Exit checks:** primary-key/FK, enum, date, arithmetic, lifecycle, duplicate, and cross-entity validations; two same-seed runs match row counts, IDs, checksums, ground-truth labels, and validation results. No synthetic data or generator currently exists.

- [ ] **Phase 11 — End-to-end evaluation, hardening, and delivery.** Complete frontend/backend workflows and demonstrate the original business flow; review security, tests, observability, deployment, docs, and operational instructions. **Exit checks:** every original definition-of-success criterion is demonstrated; mandatory anomaly fixtures and measurable evaluation outputs pass; deliverables and lawful provenance/reproducibility documentation are complete. No production-ready claim until verified.

## Cross-phase acceptance tracking

Keep each original requirement traceable to code, a test or data-validation check, and documentation. At minimum, the final review must verify:

- all mandatory entities and relationship/lifecycle metadata;
- all six actors and agreed permissions;
- eligibility, completion/assessment, issuance, signature/hash, independent verification, authorization, revocation, and audit workflows;
- unique credential IDs and enforcement that ineligible learners cannot receive credentials;
- the four controlled anomaly scenarios without unrelated baseline corruption;
- required dataset volumes, fixed seed, separate ground truth, data-quality checks, and two-run reproducibility;
- generated seed data, schema, data dictionary, generator command, source manifest, validation summary, and reproducibility report;
- lawful provenance documentation for any external data (or synthetic-only data where provenance is unclear).

## Change log

- **2026-11-11:** Phase 1 status and initialization results reconciled against the repository. Added the complete roadmap and explicit data/reproducibility acceptance tracking. No application behavior changed.
- **2026-11-11:** Phase 2 architecture proposal documented and set to **IN REVIEW**, not completed. Its recommendations and business decisions are pending user approval; no application behavior changed.
