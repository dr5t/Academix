# Phase 1 foundation

The repository is split into an `apps` layer for the API and dashboard and a `packages` layer for reusable Python code. The engine owns configuration, logging, models, provider metadata, and SQLite initialization. API routes and CLI commands import that package directly.

The dashboard intentionally contains only functional empty states and configuration surfaces. It does not display fabricated documents, metrics, provider availability, or processing results.
