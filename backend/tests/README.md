# Backend Tests

## Purpose

This guide documents backend test organization, execution boundaries, and test
environment safety. Backend evidence is selected by the behavior and material
risk being proved, not by compliance metadata or directory status. Pytest is the
runtime authority for tests, fixtures, assertions, and normal test artifacts.

## Test Organization

The current backend test tree is:

```text
backend/tests/
  checker/
  compliance/
  platform/
  workflows/
  migrations/
  support/
  legacy/
```

`legacy/` contains older tests. Its location neither validates nor invalidates a
test: retain and run useful regressions, and correct or remove a test only when
it is individually shown to be obsolete, invalid, or redundant.

Backend tests are organized by ownership:

```text
backend/tests/
  domains/
  workflows/
  platform/
  migrations/
  provider_contract/
  support/
  checker/
```

- `domains/` owns stable business and domain invariants.
- `workflows/` owns cross-domain orchestration whose integration is itself the
  contract.
- `platform/` owns global backend, API, framework, and security behavior.
- `migrations/` owns Alembic and schema-history testing.
- `provider_contract/` owns explicit provider, emulator, sandbox, or
  test-resource verification.
- `support/` owns reusable test infrastructure only.
- `checker/` and `compliance/` contain existing historical test-framework code
  pending separate cleanup. Their presence does not make checker execution,
  requirement declarations, requirement markers, or testing records mandatory.

Create or retain a directory only when current tests have a real ownership need.
Do not create placeholder test roots for future work.

## Safety Foundation

Standard backend tests must use synthetic non-production data and resources.
The exact dedicated PostgreSQL test database name is:

```text
pickup_lane_test_db
```

Migration lifecycle tests have their own exact-purpose PostgreSQL database:

```text
pickup_lane_migration_test_db
```

Those tests use `MIGRATION_DATABASE_URL` and may reset only that migration test
database after validating that the ordinary `DATABASE_URL` still points at
`pickup_lane_test_db` on the same approved PostgreSQL test host and port.

Local setup must provision the migration database explicitly:

```bash
createdb -h localhost -U postgres -O pickup-lane-user pickup_lane_migration_test_db
```

Use a sanitized URL with the same host and port as the ordinary test database:

```bash
MIGRATION_DATABASE_URL='postgresql+psycopg://pickup-lane-user:[PASSWORD]@localhost:5432/pickup_lane_migration_test_db'
```

Unsafe database configuration fails before cleanup. Ordinary backend tests block
uncontrolled external network access and may use only explicitly allowed local
or test infrastructure for their suite. Provider-contract tests are separate
and must use test-mode, emulator, sandbox, or equivalent resources when later
implemented.

Retries are diagnostic only and must not silently turn an initial failure into
clean evidence. Failure artifacts must be sanitized before becoming
production-readiness evidence.
