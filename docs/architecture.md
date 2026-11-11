# Architecture

This page is an index. The architecture is described in these documents:

| Document | Content |
|---|---|
| [README.md](../README.md#architecture) | Overview diagram of the running system |
| [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md#architecture) | Request path, repository structure, backend conventions |
| [credential-lifecycle.md](credential-lifecycle.md) | Sequence and state diagrams of the implemented behaviour |
| [system-architecture.md](system-architecture.md) | The approved design baseline, written before implementation |
| [database/database-schema.md](database/database-schema.md) | Tables, keys and constraints |

In short: a React single-page application calls a FastAPI REST API under `/api/v1`, which stores everything in one PostgreSQL database. The Ed25519 signing private key is read from the backend environment and is not stored in the database.
