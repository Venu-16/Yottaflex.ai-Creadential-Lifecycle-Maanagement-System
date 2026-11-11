# Database Design Status

The logical design deliverables for Phase 4 Step 4.1 have been corrected from the quality review and aligned to the MVP implementation assumptions:

- [Entity catalogue](database/entity-catalogue.md)
- [Data dictionary](database/data-dictionary.md)
- [Relationship specification and ER diagram](database/relationship-specification.md)

The architecture baseline is approved. Business defaults in [DECISIONS.md](DECISIONS.md) are explicitly labeled implementation assumptions, not user approvals. The original requirements remain the source of truth.

The initial SQLAlchemy schema defines 23 PostgreSQL-oriented tables, including all mandatory entities and the MVP support entities. Alembic revision `af6e5dad6637` creates the schema. It was upgraded, downgraded, and re-upgraded on a disposable PostgreSQL 17 database. No application services, APIs, or production data have been added. Phase 4 remains in progress.
