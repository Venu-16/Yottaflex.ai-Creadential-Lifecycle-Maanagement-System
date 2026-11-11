# Database Design

This page is an index.

| Document | Content |
|---|---|
| [database/database-schema.md](database/database-schema.md) | **The schema as implemented:** 23 tables, columns, keys, constraints and indexes, read from PostgreSQL after `alembic upgrade head` |
| [database/entity-catalogue.md](database/entity-catalogue.md) | Logical design: entities and their purpose |
| [database/data-dictionary.md](database/data-dictionary.md) | Logical design: fields |
| [database/relationship-specification.md](database/relationship-specification.md) | Logical design: relationships and cardinality |
| [database/seed-data-guide.md](database/seed-data-guide.md) | Synthetic seed data |

The three logical design documents were written before the schema was implemented. Where they differ from `database-schema.md`, `database-schema.md` is correct.

The schema is created by a single Alembic revision, `af6e5dad6637`. The SQLAlchemy models are in `backend/app/models/domain.py`.
