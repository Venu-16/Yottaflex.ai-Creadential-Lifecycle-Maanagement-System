# Architecture

## Initial application shape

```text
React/Vite browser client
        |
        | HTTP (development CORS configured)
        v
FastAPI application
        |
        | SQLAlchemy / psycopg
        v
PostgreSQL
```

The frontend is split into UI components, pages, routes, hooks, context, utilities, and API services. The backend separates versioned API routing, core configuration, database setup, and future domain packages. Docker Compose provides the local service network.

## Current scope

The API currently exposes only a basic health check. The frontend displays an initialization landing page. There are no domain workflows, authentication handlers, or database tables yet.
