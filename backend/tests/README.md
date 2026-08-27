# Backend Test Compliance Checker

## Purpose

The backend test compliance checker validates machine-verifiable testing
foundation rules for trusted backend test scopes. It is a compliance verifier,
not a semantic certification engine and not a pytest runtime runner.

Checker `PASS` means only that the requested scope satisfies applicable
machine-verifiable Pickup Lane test-compliance rules and that required declared
machine-readable evidence is internally consistent. Human adequacy review
remains separate.

## Trusted Architecture

The current backend test tree is:

```text
backend/tests/
  checker/
  compliance/
  platform/
  support/
  legacy/
```

`legacy/` is a historical archive only. It is not trusted production-readiness
evidence, is excluded from trusted discovery, is not part of normal validation,
does not define current expected behavior, and is not required to remain
runnable.

Trusted production-readiness backend tests are organized by ownership:

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
- `checker/` owns checker, compliance, and environment-safety self-tests.

`domains/`, `workflows/`, `migrations/`, and `provider_contract/` are reserved
trusted roots in suite policy. Do not create placeholder directories for them;
create a root only when reviewed, current trusted coverage exists for that
ownership area.

Existing backend application tests are not trusted production-readiness evidence
until future work derives them from authoritative requirements under this
system. Historical/out-of-scope tests are excluded from trusted discovery and
are not inputs to current test design.

## Requirement Declarations And Metadata

Stable requirement IDs are declared once in pass-owned JSON files under:

```text
backend/tests/support/requirements/
```

Each declaration file stores only machine-needed identity: requirement ID,
owning pass, source controls, current machine state, and scope where needed. It
does not store product specifications, scenarios, assertions, or exact pytest
node IDs.

Pytest tests declare the stable requirement IDs they prove with:

```python
@pytest.mark.requirement("EN01-R3")
def test_exact_database_name_is_required():
    ...
```

One test may declare multiple requirements, and one requirement may map to many
tests. Exact current pytest node IDs are generated from pytest collection.

## Human Testing Records

Human testing/risk records are concise and scope-owned. The EN-01 foundation
record lives at:

```text
backend/tests/checker/TESTING_RECORD.md
```

These records explain useful risks, scenarios, boundaries, owning layers, gaps,
and adequacy conclusions. They do not duplicate every Python test, exact node
ID, or product specification. The reusable standard for these records lives at:

```text
docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md
```

## Checker Commands

Run from the repository root.

File scope:

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py \
  --scope file backend/tests/checker/test_checker_foundation.py
```

Domain/subtree scope:

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py \
  --scope domain backend/tests/checker
```

Suite scope:

```bash
backend/.venv/bin/python backend/tests/check_backend_tests.py \
  --scope suite
```

The checker performs pytest collection for node ID generation only. Pytest
remains the runtime authority for executing tests, fixtures, assertions, and
normal pytest/JUnit artifacts.

## Result States

- `PASS` / exit code `0`: applicable machine-verifiable compliance rules pass.
- `FAIL` / exit code `1`: definite machine-verifiable compliance violation.
- `BLOCKED` / exit code `2`: required authority, evidence, or prerequisite is
  missing, unresolved, or explicitly blocked.
- `USAGE_ERROR` / exit code `3`: invocation, arguments, target, or scope is
  invalid.
- `INTERNAL_ERROR` / exit code `4`: checker malfunctioned unexpectedly.

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

## EN-01 Validation

EN-01 is validated by checker, environment-safety, traceability,
suite-separation, browser-quality, retry/flake, artifact, and fixture/support
self-tests. Do not create application-domain pilot tests to prove the
foundation.
