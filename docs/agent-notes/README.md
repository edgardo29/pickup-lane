# Pickup Lane Agent Notes

This directory separates shared coding standards from local feature working
notes.

## Coding Standards

The documents in `coding-standards/` are tracked repository guidance. Read the
ones applicable to the work before changing or reviewing code.

- `coding-standards/app-testing-standards.md`: application-wide risk analysis,
  safeguards, scenario coverage, and completion reporting.
- `coding-standards/backend-structure.md`: backend ownership, dependency
  direction, imports, validation, queries, and file placement.
- `coding-standards/backend-testing.md`: backend and API test organization,
  fixtures, isolation, proof quality, and execution.
- `coding-standards/css-standards.md`: general CSS ownership, cascade,
  accessibility, responsive behavior, and maintenance rules.
- `coding-standards/database.md`: PostgreSQL, SQLAlchemy, Alembic, migration,
  database-safety, and database-verification rules.
- `coding-standards/frontend-structure.md`: frontend ownership, file placement,
  imports, styles, assets, routes, and tests.

## Local Feature Notes

The documents in `feature-notes/` contain local product, page, UI, QA, admin,
and notification working notes. This directory is intentionally ignored by Git.
Read the relevant local note when it exists, but verify its claims against
current repository source and applicable tracked authority.

Production-readiness work must also start from
`docs/production-readiness/00-READ-ME-FIRST.md` and
`docs/production-readiness/01-PROGRAM-CONTEXT.md` and follow their routing.
