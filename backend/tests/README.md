# Backend Tests

This directory contains the current backend test suite. Tests are organized by
the behavior they protect, and backend pytest execution must go through the
repository-owned guarded runner.

## Run Tests Safely

Run commands from the repository root. The runner reads `TEST_DATABASE_URL` and
`MIGRATION_DATABASE_URL` from the environment or the ignored `backend/.env`.

```bash
backend/.venv/bin/python -m backend.test_runner --help

backend/.venv/bin/python -m backend.test_runner rebuild ordinary
backend/.venv/bin/python -m backend.test_runner rebuild migration
backend/.venv/bin/python -m backend.test_runner rebuild all

backend/.venv/bin/python -m backend.test_runner test ordinary \
  backend/tests/platform/settings -q

backend/.venv/bin/python -m backend.test_runner test migration \
  backend/tests/migrations/migration_policy_compatibility_rehearsal -q

backend/.venv/bin/python -m backend.test_runner test ordinary \
  backend/tests --collect-only -q
```

The first argument after `ordinary` or `migration` must be an existing path
under `backend/tests`. Additional test selections must stay under that tree.
Pytest options follow the first selection. The runner rejects options,
configuration, plugins, and environment overrides that could bypass the root
safety fixtures.

## Behavior Ownership

Directory placement describes the behavior a test owns. It does not certify a
test or give it a different level of authority.

- `domains/` owns stable business and domain invariants.
- `workflows/` owns cross-domain behavior whose integration is the contract.
- `platform/` owns global backend, API, framework, security, and test-runner
  behavior.
- `migrations/` owns Alembic, schema-history, graph, drift, and lifecycle
  behavior.
- `support/` owns reusable test infrastructure only.
- Provider-contract coverage, when applicable, must be explicitly separated
  and designed around safe emulator, sandbox, test-mode, or dedicated test
  resources.

Create or move tests according to the behavior under test, not merely the route
or page that first exposed a defect. Do not create placeholder directories.

`legacy/` is excluded from default collection. Its tests require individual
assessment before reuse or reactivation; their location alone does not establish
whether they are correct, obsolete, or useful.

## Database Safety And Isolation

Ordinary tests and migration tests use separate exact-purpose PostgreSQL
databases:

- ordinary tests: `pickup_lane_test_db`;
- migration lifecycle tests: `pickup_lane_migration_test_db`.

The runner verifies configured database names, loopback endpoints, and the
database actually reached before destructive operations. It rejects development,
production, remote, backup-like, cross-endpoint, or otherwise unsafe targets.
It also locks destructive operations and requires the ordinary database schema
to match the current migration source before pytest starts.

Root fixtures in `backend/tests/conftest.py` validate the ordinary database,
check cleanup-table inventory completeness, clean application tables before and
after database-using tests, clear dependency overrides, and install the
network/provider guard.

Tests that genuinely must not open or clean the ordinary application database
use `pytest.mark.no_db_cleanup`. Migration-owned lifecycle tests use
`pytest.mark.migration_lifecycle` where appropriate. Filenames do not bypass
database cleanup.

## Fixtures And Support

- Put broadly shared fixtures in `backend/tests/conftest.py` only when they
  genuinely apply across the suite.
- Put feature-specific shared setup in the owning feature directory.
- Put reusable cross-scope infrastructure in `backend/tests/support/`.
- Keep important scenario setup and assertions visible in the test when a
  helper would obscure the behavior being proved.

Current support responsibilities include environment and database validation,
migration inspection and lifecycle support, production-database target
rejection, artifact sanitization, and genuinely reusable behavioral fixtures.

## Network And Provider Isolation

Ordinary tests block uncontrolled external network access. The configured local
PostgreSQL test endpoint is allowed; provider and arbitrary external endpoints
are not. Mock or fake provider boundaries for ordinary tests.

Tests that intentionally contact a real provider require an explicitly safe
execution design and non-production resources such as a sandbox, emulator,
test-mode account, or dedicated disposable resource. They must never rely on
production credentials, data, or infrastructure.

## Migration Tests

Migration tests use the migration runner mode and the dedicated migration
database. The surviving migration suite directly covers database targeting,
migration graph and source inspection, unsafe change detection, lifecycle
rehearsal, locking, interruption and recovery, drift, and schema compatibility.

Use:

```bash
backend/.venv/bin/python -m backend.test_runner test migration \
  backend/tests/migrations/migration_policy_compatibility_rehearsal -q
```

## Artifact And Output Safety

Runner output and captured artifacts must not expose database credentials,
provider secrets, tokens, or other sensitive values. Artifact sanitization is
owned by `backend/tests/support/artifacts.py` and direct tests under
`backend/tests/platform/backend_test_runner/`.

Keep live progress visible during long runs. Sanitization must redact output as
it streams rather than hiding the complete run until exit.

## Strict Markers

Pytest uses strict marker validation. The complete custom marker set is:

```python
pytest.mark.no_db_cleanup
pytest.mark.migration_lifecycle
pytest.mark.pass_provenance(*pass_ids)
```

`pass_provenance` records production-readiness passes that introduced or
materially changed a test as evidence for those passes.

- Use one or more pass IDs when that provenance is real.
- Preserve genuine multi-pass provenance.
- Place the marker at the narrowest accurate module, class, or function scope.
- Do not add a pass merely because it reran an existing test.
- Ordinary product-development tests with no production-readiness provenance do
  not need the marker.

Provenance is source-local. To find tests associated with a pass, search the
test source directly:

```bash
rg 'WS06-01' backend/tests
```

There is no separate provenance manifest or rule requiring every test to carry
provenance.

## Focused Safety Tests

`backend/tests/platform/backend_test_runner/` directly tests runner selection,
database and endpoint validation, network blocking, cleanup inventory,
artifact sanitization, strict marker configuration, silent retry settings,
sleep-based synchronization, and production-looking credentials.

These focused tests protect concrete execution safeguards. Normal test design
still follows the risk-based guidance in
`docs/agent-notes/coding-standards/backend-testing.md`.
