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
  backend/tests/migrations -q

backend/.venv/bin/python -m backend.test_runner test ordinary \
  backend/tests/domains backend/tests/workflows backend/tests/platform \
  backend/tests/migrations --collect-only -q

backend/.venv/bin/python -m backend.test_runner test ordinary \
  backend/tests/domains backend/tests/workflows backend/tests/platform -q
```

The first argument after `ordinary` or `migration` must be an existing path
under `backend/tests`. Additional test selections must stay under that tree.
Pytest options follow the first selection. The runner rejects options,
configuration, plugins, and environment overrides that could bypass the root
safety fixtures. `--basetemp`, `--debug`, and `--pastebin` are prohibited.
JUnit XML and pytest log output must use a file below the ignored
`backend/.test-artifacts/` directory.

## Behavior Ownership

Directory placement describes the behavior a test owns. It does not establish
that a test is correct or useful.

- `domains/` owns stable business and domain invariants.
- `workflows/` owns cross-domain behavior whose integration is the behavior
  under test.
- `platform/` owns global backend, API, framework, security, and test-runner
  behavior.
- `migrations/` owns Alembic, schema-history, graph, drift, and lifecycle
  behavior.
- `support/` owns reusable test infrastructure only.
- `provider_contract/` owns separately runnable external-service/provider-contract
  compatibility verification designed around safe emulator, sandbox, test-mode,
  or dedicated test resources.

Create or move tests according to the behavior under test, not merely the route
or page that first exposed a defect. Do not create placeholder directories.

All maintained backend tests belong in one of the active roots above. The former
`legacy/` archive was assessed file by file: useful missing coverage was migrated
to its behavior owner, redundant coverage was confirmed against active tests,
and obsolete infrastructure was retired. Do not recreate a second excluded test
tree; evaluate and place every new regression in the active structure.

The canonical active-suite selection is explicit: ordinary execution owns
`domains`, `workflows`, and `platform`; migration execution owns `migrations`.
Complete collection selects all four roots through the guarded ordinary runner.
The isolated R2 compatibility check remains separately runnable and is never folded into
ordinary or migration execution.

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
after database-using tests, clear dependency overrides, and install the network
and external-service guard.

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

The runner and test-owned subprocesses use a minimal allowlisted environment
with synthetic application settings. Ambient external-service credentials, pytest
options, and unrelated secrets are not inherited. A test that starts a child
process must build its environment with
`isolated_test_subprocess_environment`; an inline Python child must also install
`install_test_network_guard` before importing application code.

## Network And External-Service Isolation

Ordinary tests block uncontrolled external network access. The configured local
PostgreSQL test endpoint is allowed; external-service and arbitrary external
endpoints are not. Mock or fake external-service boundaries for ordinary tests.

Tests that intentionally contact a real external service require an explicitly safe
execution design and non-production resources such as a sandbox, emulator,
test-mode account, or dedicated disposable resource. They must never rely on
production credentials, data, or infrastructure.

The Cloudflare R2 object-semantics check is the sole current
external-network mode. It
is database-free, accepts only `backend/tests/provider_contract/r2`, and permits
network access only to the exact validated HTTPS endpoint for
`R2_TEST_ACCOUNT_ID`. It requires all five `R2_TEST_*` values documented in
`backend/.env.example`, and its bucket must differ from `R2_BUCKET_NAME` when
that application bucket is configured. Run it separately:

```bash
backend/.venv/bin/python -m backend.test_runner test provider_contract \
  backend/tests/provider_contract/r2 -q
```

Missing isolated configuration is a failed prerequisite, not a skipped or
passing R2 verification. Ordinary and migration modes continue to block R2.

Each R2 compatibility run owns only three exact keys below its unique
`provider-contract/r2-object-semantics/{run_id}/` prefix. It attempts all three
idempotent deletions without listing the bucket. A cleanup-only failure fails
the R2 verification; when the verification has already failed, cleanup failure
is attached to that original failure rather than replacing it. The team
responsible for Storage and Cloudflare R2 owns lifecycle expiry and manual
removal of objects abandoned by process termination or an unavailable R2
service. Application venue-image reconciliation does not own this isolated test
bucket, and the R2 test token does not need listing or lifecycle-administration
permission.

## Migration Tests

Migration tests use the migration runner mode and the dedicated migration
database. The surviving migration suite directly covers database targeting,
migration graph and source inspection, unsafe change detection, lifecycle
rehearsal, locking, interruption and recovery, drift, and schema compatibility.

Use:

```bash
backend/.venv/bin/python -m backend.test_runner test migration \
  backend/tests/migrations -q
```

## Artifact And Output Safety

Runner output and captured artifacts must not expose database credentials,
external-service secrets, tokens, or other sensitive values. Artifact sanitization is
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
