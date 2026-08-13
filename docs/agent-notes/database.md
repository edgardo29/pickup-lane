# Database And Migrations

This document defines the authoritative rules for PostgreSQL schema ownership,
Alembic migration structure, local database use, and database verification in
Pickup Lane.

Read it before creating, editing, reordering, renaming, or deleting migrations,
models, constraints, indexes, database scripts, or persistent data structures.

Also read:

* `backend-structure.md` for model, service, and schema ownership
* the relevant feature documentation before changing database behavior
* `global-rules.md` before running tests or broad repository commands

This document does not define feature behavior or maintain a catalog of current
feature tables. Feature-specific schema contracts belong in their owning
feature documents.

When existing migrations conflict with these rules, do not copy or expand the
conflict. Identify it and keep the requested change focused unless the task
explicitly includes migration cleanup.

## Current Database Setup

Pickup Lane uses PostgreSQL and Alembic.

Run Alembic from the repository root because `alembic.ini` is located there.

```bash
source backend/.venv/bin/activate
alembic upgrade head
```

The application reads `DATABASE_URL` from `backend/.env` unless a command
explicitly overrides it.

The current local databases are:

* `pickup_lane_db_dev`: local development, browser testing, manual QA, and
  development rebuilds
* `pickup_lane_test_db`: backend and API tests that should behave like CI

Do not use the test database for manual QA. Do not run destructive test setup
against the development database.

## Pre-Production Migration Policy

Pickup Lane is currently pre-production and uses a clean-rebuild migration
strategy.

Applied development migrations are not treated as immutable production history.
When the schema changes, update the canonical migration that owns the affected
database object and rebuild local databases from base to head.

Do not create patch migrations merely to preserve an outdated local database. A
local database that has already applied an edited migration must be dropped and
rebuilt because Alembic will not rerun an applied revision after its file
changes.

This policy changes once deployed databases contain data that must be
preserved. At that point, applied migrations become immutable and schema
changes require new forward migrations.

The transition to immutable production migration history requires an explicit
project-level decision.

## One Table, One Canonical Migration

Each application table must have one canonical Alembic revision that owns the
table's complete current schema.

The canonical migration owns:

* table creation
* all columns
* primary keys
* foreign keys originating from the table
* unique constraints
* check constraints
* indexes
* partial and expression indexes
* server defaults
* table-specific PostgreSQL expressions
* table-specific triggers or functions when they are not shared

A migration that creates an application table must not create or alter another
application table.

Do not combine multiple table definitions in one migration because the tables
belong to the same feature or were designed at the same time.

Join tables, ledger tables, history tables, association tables, and audit tables
are still tables. Each receives its own canonical migration.

The preferred filename pattern is:

```text
<sequence>_create_<table_name>_table.py
```

The filename, revision metadata, and responsibility should make the owning
table obvious.

## Changing An Existing Table

While the project follows the pre-production clean-rebuild policy, any change
to an existing table must be made in that table's canonical migration.

This includes:

* adding, removing, or renaming columns
* changing types or nullability
* changing defaults
* adding or removing indexes
* changing unique or check constraints
* adding or removing foreign keys
* changing partial-index predicates
* adding table-specific PostgreSQL behavior

Do not create later migrations such as:

* `add_column_to_<table>.py`
* `alter_<table>_constraints.py`
* `add_<table>_index.py`
* `update_<table>_status_values.py`

For example, a new column, index, foreign key, target requirement, or action
type for `admin_actions` belongs in the canonical `admin_actions` table
migration.

After editing a canonical migration, rebuild any local database that previously
applied the old version.

## Creating A New Table

A genuinely new table receives a new canonical migration at the end of the
current migration chain, subject to dependency ordering.

Before creating the migration, identify:

1. the table name
2. its one-sentence responsibility
3. the SQLAlchemy model that owns it
4. the parent tables it references
5. the indexes and constraints required by its final schema
6. where it belongs in the revision dependency order

The new migration should create the table in its intended complete development
shape.

Do not place placeholder columns, future feature fields, or unrelated audit
targets into the migration.

## Foreign Keys And Dependency Order

A foreign key belongs to the table containing the foreign-key column.

The child table's canonical migration owns:

* the foreign-key column
* the foreign-key constraint
* related indexes on the child table
* child-side nullability and delete behavior

The referenced parent table must exist before the child migration runs.

Alembic dependency order must follow schema dependencies. Filename numbering
and `down_revision` links should remain understandable and aligned.

When an existing table gains a foreign key to a table whose migration currently
runs later, do not create a patch migration solely to avoid correcting the
order. Reorder the clean-development revision chain deliberately so the parent
exists first, then rebuild from base.

Do not introduce circular foreign-key dependencies casually. Redesign the
relationship when practical.

An unavoidable circular dependency requires an explicit documented exception
and project-level approval before introducing a relationship-only migration or
other nonstandard ordering.

## Non-Table Database Objects

The one-table-one-migration rule applies to application tables. Database objects
that are not owned by one table require a focused migration with one clear
responsibility.

Examples include:

* PostgreSQL extensions
* shared enum types
* shared database functions
* views and materialized views
* shared triggers
* database-wide policies
* merge-only Alembic revisions

A non-table migration must not become a dumping ground for unrelated objects.

A database object used only by one table should remain in that table's
canonical migration when ordering and lifecycle permit it.

A shared object used by multiple tables should have one dedicated owner and
must not be duplicated across table migrations.

Merge revisions may resolve Alembic branches but must not contain unrelated
schema changes.

## Migration Implementation Rules

Keep migrations deterministic, readable, and rebuildable from base to head.

Alembic revision IDs must be 32 characters or fewer because Alembic stores them
in `alembic_version.version_num`. Migration filenames can be longer and more
descriptive.

Use normal Alembic operations for tables, columns, indexes, constraints, and
foreign keys whenever practical.

Use raw SQL only when Alembic does not express the required PostgreSQL behavior
cleanly or when a deliberate data cleanup is required before narrowing a
constraint.

Do not rely blindly on Alembic autogenerate. It may be used as a drafting aid,
but generated output must be reviewed and reshaped to follow this document.
Autogenerate must not produce a final migration that owns multiple tables.

Do not add defensive existence checks to clean development migrations without a
specific documented reason. Avoid patterns such as:

* `if_exists=True`
* `DROP TABLE IF EXISTS`
* `DROP INDEX IF EXISTS`
* `ADD COLUMN IF NOT EXISTS`
* `CREATE INDEX IF NOT EXISTS`
* inspector-based existence checks
* conditional `pg_constraint` checks

Dirty or outdated local databases should be rebuilt rather than making clean
migrations tolerate every historical local shape.

An exception is acceptable for database infrastructure that is intentionally
idempotent, such as an approved `CREATE EXTENSION IF NOT EXISTS` statement.

Do not add manual commits or rollbacks inside migrations unless the operation
requires special transaction handling and the reason is documented.

## Constraints And Indexes

Database-enforced invariants belong in the canonical migration and SQLAlchemy
model when the ORM can represent them.

Use stable, descriptive names for:

* foreign keys
* unique constraints
* check constraints
* indexes

Partial, functional, expression, and unique indexes must be represented in both
the SQLAlchemy model and the canonical migration when they are part of the
intended schema.

Check-constraint definitions should match between the model and migration as
closely as practical so `alembic check` does not report avoidable drift.

Do not duplicate indexes that provide the same effective access path without a
measured or documented reason.

Indexes should support real query, ordering, uniqueness, or enforcement needs.
Do not add speculative indexes for possible future use.

## Models, Schemas, And Services

Persistent data changes must remain aligned across:

* SQLAlchemy models
* canonical Alembic migrations
* Pydantic schemas
* services and queries
* tests
* feature documentation

The model and canonical migration must describe the same intended final table
shape.

A model-only schema change is incomplete.

A migration-only behavior change is incomplete when application code still
assumes the old contract.

Database constraints are the final enforcement layer for invariants that must
remain true regardless of the caller. Service validation should still provide
clear domain errors before a database constraint fails where practical.

## Upgrade And Downgrade Behavior

Each canonical table migration should have a clear upgrade and downgrade.

The upgrade creates only the owning table and its owned database objects.

The downgrade removes those objects in a safe dependency order, usually:

1. table-specific triggers or dependent objects
2. indexes not removed automatically with the table
3. foreign keys when explicit removal is required
4. the table
5. table-specific types or functions that are no longer used

A downgrade must not delete or alter unrelated tables.

When narrowing a constraint in a production-safe migration is eventually
required, data must be normalized or removed before the constraint is applied.
That production workflow is outside the current editable-history policy unless
explicitly requested.

## Retiring A Pre-Production Table

When a pre-production table is retired, clean rebuilds must not recreate it.

Preserve the Alembic revision chain when necessary by converting the retired
canonical revision into a clearly documented no-op placeholder or another
approved clean-history form.

Do not reuse the retired revision for an unrelated table or feature.

Do not leave obsolete tables in the clean rebuild merely because an older local
database once contained them.

## Data And Seed Changes

Schema migrations should define schema, not serve as general seed scripts.

Use `backend/scripts/` for development seed data and operational data setup.

Immutable reference rows that are required for the database contract may be
inserted by a focused migration when explicitly approved.

Do not place large demo datasets, Firebase test-user creation, or manual QA
data inside Alembic migrations.

When a schema change affects seed scripts, update the scripts in the same task.

Local scripts that create Firebase Auth test users are sensitive and dev-only
unless explicitly approved for commit.

## Local Database Rebuilds

The commands below are reference commands. Run destructive database commands
only when the user explicitly asks and `global-rules.md` permits it.

### Development Database

`pickup_lane_db_dev`

Use this for local browser testing, manual QA, and development rebuilds. When
the user says to wipe or rebuild the app database for manual testing, this is
usually the database they mean.

The app does not hardcode a development database name. Backend code loads
`DATABASE_URL` from `backend/.env`; the current local dev setting uses
`pickup_lane_db_dev`.

Clean rebuild and seed development auth users:

```bash
dropdb -h localhost -U postgres pickup_lane_db_dev
createdb -h localhost -U postgres -O pickup-lane-user pickup_lane_db_dev
DATABASE_URL='[LOCAL_DEV_DATABASE_URL]' backend/.venv/bin/alembic upgrade head
DATABASE_URL='[LOCAL_DEV_DATABASE_URL]' backend/.venv/bin/python -m backend.scripts.seed_dev_auth_users --count 12
```

Important:

* Run `seed_dev_auth_users` with `-m backend.scripts.seed_dev_auth_users`, not
  as a file path, so Python can import the `backend` package.
* This seed script creates Firebase Auth test users and matching database rows.
* The seeded users are `sub1@test.com` through `sub<count>@test.com` by
  default.
* Use only the approved local seed password for generated test users; do not
  publish real user credentials in this document.
* Use `--start-index` to create a later range such as `sub13@test.com` through
  `sub24@test.com`.

### Test Database

`pickup_lane_test_db`

Use this for backend and API tests that should behave like CI. Do not use this
database for browser or manual QA.

Clean rebuild:

Use `DATABASE_URL=[REDACTED]` for Alembic commands against the local test database.

Do not point destructive test commands at `pickup_lane_db_dev`.

If backend tests skip unexpectedly, verify `DATABASE_URL` points at
`pickup_lane_test_db`.

Exact pytest selections belong in `global-rules.md` or focused testing
documentation, not in this file.

## Verification

Use the narrowest verification appropriate to the change.

Before considering a database change complete, confirm as applicable:

* migration modules import successfully
* the revision chain has one head unless an approved branch is in progress
* every application table has one canonical migration owner
* no migration creates or alters multiple application tables
* a clean database runs `alembic upgrade head`
* downgrade and re-upgrade work when the affected revisions support downgrade
* `alembic check` reports no unexpected model drift
* required indexes and constraints exist in both the model and migration
* relevant seed scripts still run
* focused backend checks pass when tests are requested

Do not treat success against an already-migrated local database as proof that
an edited historical migration works. Verify with a clean rebuild.

## Before Database Changes

Before editing persistent data structures:

1. Read this document.
2. Read `backend-structure.md`.
3. Read the relevant feature documentation.
4. Identify every table and non-table object affected.
5. Identify the canonical migration that owns each existing table.
6. Confirm that a new revision is needed only for a genuinely new table or a
   focused non-table database object.
7. Confirm foreign-key dependency order.
8. State whether local databases must be rebuilt.
9. List the models, schemas, services, tests, and seed scripts that must remain
   aligned.
10. Keep unrelated migration cleanup outside the task.

Before creating a migration that alters an existing table, stop and re-check
the canonical table migration rule. Under the current pre-production policy,
the existing table's canonical migration should normally be edited instead.
