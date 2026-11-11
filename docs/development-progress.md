# Development Progress and 11-Phase Roadmap

The original hackathon problem statement at [original-problem-statement.md](original-problem-statement.md) is the source of truth. This checklist tracks product work, not merely folder creation. Mark a phase complete only when its work and stated checks are implemented and verified. Do not mark a mandatory acceptance criterion out of scope without explicit user approval and a documented trade-off.

## Status summary

- **Verified completed phases:** Phase 1 — Project foundation and initialization; Phase 2 — approved architecture baseline; Phase 10 — synthetic data, quality, ground truth, and reproducibility.
- **Current product phase:** Phase 4 — Domain model and master data (initial database model and migration implemented; application workflows are not implemented).
- **Completed checklist items:** Phases 1, 2, and 10. Unresolved business choices are handled through documented implementation assumptions, not treated as user approvals.
- **Remaining:** Phases 3–9 and 11.
- **Documentation status:** Project context, AI handover, this roadmap, decisions log, and complete original requirements are established. The architecture baseline is approved; open business/security choices and time-boxed implementation assumptions are distinguished in `docs/DECISIONS.md`.

## Phases

- [x] **Phase 1 — Project foundation and initialization.** Create the repository scaffold; initialize FastAPI and React/Vite; configure environment, PostgreSQL/SQLAlchemy, Alembic, CORS, logging, health check, Pytest, Tailwind, API client, Docker Compose, and initial documentation. **Verified:** one health test passes, frontend production build succeeds, local health/page checks succeed, Alembic offline generation is empty, Compose config validates, and isolated PostgreSQL/backend/frontend Compose services passed their checks. No schema or domain behavior is included.

- [x] **Phase 2 — System architecture and requirements design.** The modular-monolith architecture baseline and original requirements are approved for implementation by the user's 2026-11-11 direction. Unresolved product/security semantics are not approved; conservative defaults are recorded as implementation assumptions in `docs/DECISIONS.md` and must remain distinguishable from user-approved policy.

- [ ] **Phase 3 — Identity, authentication, and authorization.** Define account ownership, actor responsibilities, permission boundaries (Learner, Instructor, Academic Administrator, Support Staff, Platform Administrator, Third-party Verifier), and verifier access using documented assumptions where needed. **Exit checks:** authentication and authorization tests demonstrate allowed and denied access; permissions default to deny; secrets are not committed.

- [ ] **Phase 4 — Domain model and master data (IN PROGRESS).** Implement mandatory Learner, Course, CredentialRule, CompletionRecord, Credential, Issuer, VerificationRequest, Revocation, and AuditEvent entities and justified supporting entities. **Step 4.1:** logical catalogue, dictionary, and relationship specification corrected; MVP assumptions are recorded separately from approvals. Initial SQLAlchemy metadata and Alembic revision `af6e5dad6637` define 23 tables. PostgreSQL upgrade/downgrade/re-upgrade, metadata sync, and focused uniqueness checks passed on a disposable database. Still required: verify all constraints against workflows, implement services/APIs, test integration in project setup, and review outstanding schema assumptions. Phase 4 is not complete.

- [ ] **Phase 5 — Credential eligibility rule definition.** Agree the rule format, course relationships, effective dates, versions, assessment-attempt semantics, and validation semantics; implement rule management. **Exit checks:** documented business rules, rule validation, and tests for normal, boundary, and invalid rules. Preserve all requirements; do not silently simplify.

- [ ] **Phase 6 — Course completion and assessment tracking.** Capture course completion and assessment outcomes for valid learner/course IDs, including incomplete courses. **Exit checks:** referential integrity, allowed values, date ordering, and assessment/completion validation tests.

- [ ] **Phase 7 — Eligibility evaluation and business decisions.** Evaluate each learner against applicable credential requirements, persist explicit eligibility decisions/outcomes, and expose important decisions and exceptions. **Exit checks:** deterministic rule outcomes have tests and ground-truth comparisons; ineligible learners cannot proceed to issuance.

- [ ] **Phase 8 — Credential issuance and cryptographic integrity.** Issue unique credential identifiers only after all applicable requirements pass. Agree and implement signed-record metadata or deterministic cryptographic hashes and key handling. **Exit checks:** uniqueness and eligibility enforcement; valid data verifies; altered payloads are detected; issuance decisions and events are traceable.

- [ ] **Phase 9 — Verification, revocation, and audit.** Implement third-party credential verification and request tracking, authorized revocation, and immutable-style audit history. **Exit checks:** valid, revoked, altered, unknown, and unavailable-key cases are distinguishable; permitted lifecycle transitions and authorization are enforced; revoked credentials cannot verify as active; event completeness is demonstrated.

- [x] **Phase 10 — Synthetic data, quality, ground truth, and reproducibility.** Implemented deterministic full/starter generators using seed **20261022**. Two clean full-profile PostgreSQL generations produced identical records, counts, checksums, ground-truth labels, and validation results. The verified full dataset contains 20,000 learners, 1,000 courses, 100 rules, 10 issuers, 10,000 credentials, 5,000 verification requests, and valid dependent records; all six anomaly fixtures are covered without weakening production constraints. Separate ground truth, compressed export, source manifest, validation summary, and reproducibility report are available under `data/`. The retained baseline validation passed every check; the reproducibility report records zero differences. Large generated JSONL/CSV/JSON outputs are reproducible and excluded from Git.

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
- **2026-11-11:** Phase 4 Step 4.1 logical database design documents drafted for review under the user's request. They remain proposals; Phase 2 is still **IN REVIEW**, Phase 3 is not implemented, and no Phase 4 schema or code was created.
- **2026-11-11:** User approved using the existing architecture and original requirements as implementation baseline and authorized conservative, documented defaults. Updated database design for stable CredentialAward uniqueness, replacement lineage, immutable evaluation/evidence snapshots, issuer-profile history, and aligned course-scope cardinality. Added 23 SQLAlchemy tables and initial Alembic migration `af6e5dad6637`; PostgreSQL migration and uniqueness checks passed in a disposable database. Phase 4 remains in progress.
- **2026-11-11:** Completed roadmap Phase 10 synthetic seed data. Full-profile generation and all database/data/cryptographic checks passed; a second clean generation produced matching manifests and validation results. The task-level Phase 5 seed-data work is complete; roadmap Phase 5 (eligibility-rule definition) remains pending. Phase 4 remains in progress.
