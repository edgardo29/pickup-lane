# Pickup Lane Coding Standards

The documents in this directory are tracked repository guidance. Read the ones
applicable to the work before changing or reviewing code.

- `backend-structure.md`: backend ownership, dependency
  direction, imports, validation, queries, file placement, and API design.
- `backend-standards.md`: general Python, FastAPI, Pydantic,
  SQLAlchemy, PostgreSQL, Alembic, reliability, security, and testability
  practices.
- `backend-testing.md`: backend and API test organization,
  fixtures, isolation, proof quality, and execution.
- `css-standards.md`: general CSS ownership, cascade,
  accessibility, responsive behavior, and maintenance rules.
- `database.md`: PostgreSQL, Alembic, migration,
  database-safety, and database-verification rules.
- `frontend-standards.md`: general React, JavaScript, and Vite
  engineering practices, including state, effects, API behavior, security,
  accessibility, and performance.
- `frontend-structure.md`: Pickup Lane frontend ownership, file
  placement, imports, styles, assets, routes, and test locations.

Read `backend-standards.md` and `backend-structure.md` before relevant backend
changes. Read the backend testing and database guides when their specialized
requirements apply.

Read both frontend documents before relevant frontend changes. Neither replaces
the other. Also read `css-standards.md` before stylesheet changes.

## Document Responsibilities

- General engineering standards (`backend-standards.md`,
  `frontend-standards.md`, and `css-standards.md`) define transferable coding
  practices.
- Repository-specific standards (`backend-structure.md`,
  `frontend-structure.md`, `backend-testing.md`, and `database.md`) define
  Pickup Lane's concrete engineering conventions and ownership boundaries.
- `docs/production-readiness/system-architecture.md` records the selected
  technical architecture and infrastructure decisions.
- `docs/production-readiness/production-launch/production-launch-requirements.md`
  defines required production-readiness outcomes and verification
  obligations.

Applicable engineering standards constrain the technical approach. They do not
by themselves authorize additional product behavior, infrastructure, or
production-readiness scope. For production-readiness work, a standard governs
how a master requirement is implemented only as Section 3.4 of the production
launch requirements provides: the master or pass plan must identify its exact
file and section.

When two documents prescribe incompatible behavior, report the conflict and
resolve it according to each document's responsibility instead of silently
following either one. A coding standard cannot weaken a production
requirement.

## Local Feature Notes

The documents in `docs/feature-notes/` contain local product, page, UI, QA, admin,
and notification working notes. This directory is intentionally ignored by Git.
Read the relevant local note when it exists, but verify its claims against
current repository source and applicable tracked authority.
