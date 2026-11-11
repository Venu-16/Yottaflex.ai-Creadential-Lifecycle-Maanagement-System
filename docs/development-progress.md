# Development Progress and 11-Phase Roadmap

The original hackathon problem statement at [original-problem-statement.md](original-problem-statement.md) is the source of truth. This checklist tracks product work, not merely folder creation. Mark a phase complete only when its work and stated checks are implemented and verified. Do not mark a mandatory acceptance criterion out of scope without explicit user approval and a documented trade-off.

## Status summary

- **Verified completed phases:** Phase 1 — Project foundation and initialization; Phase 2 — approved architecture baseline; Phase 10 — synthetic data, quality, ground truth, and reproducibility.
- **Current product phase:** Phase 7 frontend development and backend API integration (MVP UI and routes implemented; full browser journey testing and wider acceptance coverage remain).
- **Completed checklist items:** Phases 1, 2, and 10. Unresolved business choices are handled through documented implementation assumptions, not treated as user approvals.
- **Remaining:** Phases 3–9 and 11. Phase 10 is complete; Phases 3–9 and 11 remain unchecked until their full exit criteria are satisfied.
- **Documentation status:** Project context, AI handover, this roadmap, decisions log, and complete original requirements are established. The architecture baseline is approved; open business/security choices and time-boxed implementation assumptions are distinguished in `docs/DECISIONS.md`.

## Phases

- [x] **Phase 1 — Project foundation and initialization.** Create the repository scaffold; initialize FastAPI and React/Vite; configure environment, PostgreSQL/SQLAlchemy, Alembic, CORS, logging, health check, Pytest, Tailwind, API client, Docker Compose, and initial documentation. **Verified:** one health test passes, frontend production build succeeds, local health/page checks succeed, Alembic offline generation is empty, Compose config validates, and isolated PostgreSQL/backend/frontend Compose services passed their checks. No schema or domain behavior is included.

- [x] **Phase 2 — System architecture and requirements design.** The modular-monolith architecture baseline and original requirements are approved for implementation by the user's 2026-11-11 direction. Unresolved product/security semantics are not approved; conservative defaults are recorded as implementation assumptions in `docs/DECISIONS.md` and must remain distinguishable from user-approved policy.

- [ ] **Phase 3 — Identity, authentication, and authorization (IMPLEMENTATION IN PROGRESS).** Basic local-password authentication, HS256 bearer tokens, active-role lookup, deny-by-default role dependencies, and a separate environment-driven demo-user bootstrap are implemented. Temporary role grants are restrictive assumptions IA-16, not approval of the actor matrix. **Still required:** review/approve identity and actor permissions; add object-level authorization, account lifecycle/role-management workflow, rate limiting, and broader security tests. Phase 3 is not complete.

- [ ] **Phase 4 — Domain model and master data (IN PROGRESS).** The logical catalogue, dictionary, and relationship specification are documented. Initial SQLAlchemy metadata and Alembic revision `af6e5dad6637` define 23 tables. PostgreSQL upgrade/downgrade/re-upgrade, metadata sync, and uniqueness checks passed on disposable databases. Master-data APIs and workflow validation now exercise the schema. Still required: resolve schema assumptions, verify all constraints/concurrency cases, and complete migrations/API integration review. Phase 4 is not complete.

- [ ] **Phase 5 — Credential eligibility rule definition (IMPLEMENTATION IN PROGRESS).** Versioned course-scoped rules are configurable, validated, and evaluable using the documented `latest_graded` assumption. **Still required:** resolve and approve production rule semantics, broaden validation/boundary tests, and review version effective-date behavior. This phase is not complete.

- [ ] **Phase 6 — Course completion and assessment tracking (IMPLEMENTATION IN PROGRESS).** Enrollment, completion, status update, and append-only assessment-attempt APIs are implemented with reference, score, and timestamp validation. PostgreSQL integration tests exercise the normal path. **Still required:** instructor scoping, full invalid/boundary coverage, lifecycle status review, and policy approval. This phase is not complete.

- [ ] **Phase 7 — Eligibility evaluation and business decisions (IMPLEMENTATION IN PROGRESS).** A dedicated service re-reads current source evidence, applies rule-version criteria and attempt policy, persists immutable decisions/reasons/evidence digests, and rejects ineligible issuance. Ground-truth labels are not consumed. **Still required:** broader unit/boundary and generated-ground-truth comparison coverage; review invalid/unavailable evidence behavior and policy approval. This phase is not complete.

- [ ] **Phase 8 — Credential issuance and cryptographic integrity (IMPLEMENTATION IN PROGRESS).** Atomic issuance re-evaluates eligibility, enforces learner/course award-slot uniqueness, allocates stipulated CRD IDs under PostgreSQL advisory locks, supports request idempotency, and signs canonical payloads with Ed25519. Private keys are external to PostgreSQL. **Still required:** production key custody, replacement flow, concurrency/load tests, and policy review. This phase is not complete.

- [ ] **Phase 9 — Verification, revocation, and audit (IMPLEMENTATION IN PROGRESS).** Credential-ID and portable-payload verification, key registry/rotation, fail-closed trust outcomes, revocation, read-only audit, and summary reports are implemented. Integration tests verify VALID→REVOKED and detect stored-payload tampering. **Still required:** unavailable-database, expired/historical key, public disclosure/rate-limit, audit completeness, and deeper anomaly tests. This phase is not complete.

- [x] **Phase 10 — Synthetic data, quality, ground truth, and reproducibility.** Implemented deterministic full/starter generators using seed **20261022**. Two clean full-profile PostgreSQL generations produced identical records, counts, checksums, ground-truth labels, and validation results. The verified full dataset contains 20,000 learners, 1,000 courses, 100 rules, 10 issuers, 10,000 credentials, 5,000 verification requests, and valid dependent records; all six anomaly fixtures are covered without weakening production constraints. Separate ground truth, compressed export, source manifest, validation summary, and reproducibility report are available under `data/`. The retained baseline validation passed every check; the reproducibility report records zero differences. Large generated JSONL/CSV/JSON outputs are reproducible and excluded from Git.

- [ ] **Phase 11 — End-to-end evaluation, hardening, and delivery (IN PROGRESS).** Frontend MVP now includes authentication/session handling, role-aware navigation, dashboard/report views, learner/course/rule administration, enrollment/completion/assessment entry, eligibility evaluation, credential issue/revoke, audit history, and public verification. Production frontend build passed; backend suite passed 27 tests against a separate temporary PostgreSQL database. A browser-driven primary workflow passed against isolated disposable PostgreSQL (learner → course/rule → enrollment → completion/assessment → eligible decision → issuance → VALID verification → confirmed revocation → REVOKED verification); login/logout, role navigation, learner/course updates, audit/report views, public disclosure minimization, and mobile navigation were also checked. Still required: complete the original business-flow and anomaly acceptance criteria; review security, observability, deployment, and all delivery requirements. **Exit checks:** every original definition-of-success criterion is demonstrated; mandatory anomaly fixtures and measurable evaluation outputs pass; deliverables and lawful provenance/reproducibility documentation are complete. No production-ready claim until verified.

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
- **2026-11-11:** Began Phase 6 backend implementation: added authentication/RBAC, demo-user bootstrap, service-layer master and lifecycle operations, versioned rule management, eligibility, idempotent Ed25519 issuance, credential-ID and portable verification, revocation, audit/report APIs, and PostgreSQL integration tests. Phase 6.5 hardening validation passed 27 backend tests on a separate temporary PostgreSQL 17 database, Python compileall, OpenAPI generation (34 paths with bearer auth), Alembic upgrade and metadata check, and Docker Compose configuration validation. Phases 3–9 remain unchecked and pending their full exit criteria and review; no phase is marked complete by this entry.
