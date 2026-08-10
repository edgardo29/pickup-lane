# Backend Testing Guide

This guide describes the target backend testing architecture for Pickup Lane.
The active tree is still being transitioned progressively; existing `pages/`,
`shared/`, `legacy/`, and `_backend_test_contract.py` artifacts are historical
or transitional unless their owning area is rebuilt under this model.

The backend checker validates mechanical architecture and safety rules only. A
checker `PASS` never means a domain is fully or correctly tested.

## Target Ownership Model

Backend tests are domain-first. Place a test with the domain that owns the
behavior being protected, not with the first page or endpoint that exposed it.

Future substantial domain areas should use names such as:

```text
backend/tests/
  auth/
  users/
  games/
  bookings/
  need_a_sub/
  payments/
  admin/
  moderation/
  chat/
  notifications/
  venues/
```

Create a domain directory only when it has reviewed content. Do not add empty
placeholder folders to make the tree look complete.

To choose the owner, ask:

- Which domain defines the rule, state transition, invariant, permission, or
  provider boundary?
- Would the same rule matter if a different page or route exposed it tomorrow?
- Which finalized product or production-readiness source defines the expected
  behavior?
- Which layer can prove the safeguard most directly: unit/policy, service, API,
  PostgreSQL, migration, worker, or provider integration?

Endpoint shape can influence the file name, but endpoint shape does not by
itself own the test.

## Infrastructure And Integrations

`infrastructure/` is reserved for platform-level backend behavior that is not
owned by one product domain, such as test-harness safety, app lifecycle,
request limits, low-level configuration, migration mechanics, and release-time
backend checks. Do not use it as a catch-all for unclear business behavior.

`integrations/` is reserved for real sandbox, emulator, or test-resource
verification against external systems such as Firebase, Stripe, R2, email, or
future provider-backed workers. Standard backend tests mock providers at the
application-owned boundary. Provider integration suites must be separately
approved, separately runnable, and configured only for safe test resources.

`support/` is mechanics-only. It may hold reusable factories, API setup
helpers, assertions, time helpers, environment guards, traceability validators,
and templates. Support code must not import from domain test directories,
`pages/`, `shared/`, or `legacy/`.

## Transitional Directories

The current active tree still contains `pages/` and `shared/` from the old
architecture. They are not the preferred model for future backend work. Keep
them stable until an owning domain is reviewed and reconstructed.

`legacy/` contains historical valid tests that have not been reviewed into the
current production-readiness evidence model. Do not count legacy tests as
current evidence.

Existing `_backend_test_contract.py` files are physically left in place for
their current owners until those areas are reviewed. Future rebuilt domains use
lightweight traceability instead.

## Test File Naming

File names communicate test type and execution needs. They are conventions,
not top-level ownership categories:

```text
test_unit_*.py
test_policy_*.py
test_service_*.py
test_api_*.py
test_db_*.py
test_security_*.py
test_concurrency_*.py
test_migration_*.py
test_webhook_*.py
test_worker_*.py
test_integration_*.py
```

Use the narrowest name that matches the primary behavior. Avoid vague names
such as `test_game.py`, `test_errors.py`, or `test_misc.py`.

## Execution Markers

Markers describe execution characteristics, not ownership.

Registered backend markers:

- `db`: uses the PostgreSQL test database.
- `concurrency`: exercises deterministic concurrent or race-sensitive behavior.
- `migration`: validates Alembic or schema migration behavior.
- `provider_integration`: uses an approved provider sandbox, emulator, or
  test-resource boundary.
- `slow`: intentionally slower than ordinary focused tests.
- `no_db_cleanup`: backend harness/tooling test that must not open or clean the
  application database.

Do not create markers for `auth`, `games`, `payments`, `pages`, `shared`, or
other ownership concepts. Unknown markers fail under strict marker validation.
`no_db_cleanup` is not a product-test shortcut; it must not be combined with
database/concurrency/migration markers or tests that request the shared
`client` fixture, and it must not directly import `backend.database`.

## PostgreSQL Safety

Automated backend pytest uses:

```text
APP_ENV=test
```

Do not branch backend test behavior on `APP_ENV=ci`. CI is an execution
location; `test` is the canonical application environment for automated
backend pytest.

Standard backend tests must use the dedicated PostgreSQL test database name:

```text
pickup_lane_test_db
```

The name match is exact. A database is not safe merely because its name contains
`test`.

The root `conftest.py` owns only global mechanics: synthetic test-safe settings,
settings-cache reset, exact environment and database validation, the shared test
client, dependency override cleanup, database cleanup orchestration, and the
standard-suite network guard.

Database cleanup targets are derived from imported SQLAlchemy model metadata,
then checked against the connected PostgreSQL schema before destructive cleanup.
Only narrow non-application objects such as `alembic_version` may be excluded.
Cleanup truncates the metadata tables with quoted identifiers, `RESTART
IDENTITY`, and `CASCADE` before and after DB-using tests while retaining the
single-worker advisory lock. The harness does not auto-create/drop databases or
support parallel-worker database naming yet.

## Provider Isolation

Standard backend tests must not make live Firebase, Stripe, R2, email, or other
provider calls. Mock at the application-owned boundary while exercising Pickup
Lane's behavior.

Provider integration tests belong under `integrations/` only after approved
sandbox/emulator/test-resource configuration exists. They must never rely on
production credentials, production data, or uncontrolled public network access.

## Fixtures And Helpers

Fixtures belong at the narrowest useful scope.

- Domain-specific fixtures live with that domain.
- Cross-domain mechanics live in `support/`.
- Root `conftest.py` is reserved for application-wide test mechanics such as
  the test client, environment safety, dependency cleanup, and database cleanup.

Factories create valid records or objects. API helpers perform setup through
public/admin API contracts. Assertion helpers should be repeated, named, and
clear enough that the protected behavior remains visible.

## Traceability

For substantial rebuilt domains, use both:

- `TESTING.md`: human-readable test intent, important risks, applicability
  notes, and known gaps.
- `testing_manifest.yaml`: small machine-readable traceability.

The manifest points to authoritative product and production-readiness sources;
it does not duplicate full specifications or state matrices. Keep it small.

The supported manifest convention is documented by:

- `backend/tests/support/TESTING.template.md`
- `backend/tests/support/testing_manifest.template.yaml`

The active checker validates manifest syntax and schema only where a domain
provides a manifest. It does not require manifests for every future domain
during EN-01 foundation work.

Runtime behavior is proven by focused pytest selections. The checker does not
run pytest for a target and does not replace requirement review.

## Targeted Execution

Use the narrowest command that proves the current change:

- one checker/tooling self-test file for checker changes
- one domain directory for a reviewed domain reconstruction
- one marker-selected group when the execution characteristic is the point
- one provider integration suite only when explicitly approved

Do not use the broad current backend product suite as acceptance evidence for
EN-01 foundation/tooling changes.

## Reconstructing A Domain Later

When rebuilding a domain under the new architecture:

1. Read authoritative current requirements.
2. Inspect supported current production behavior.
3. Independently determine the backend scenarios that require testing.
4. Determine domain ownership.
5. Determine the appropriate test layer.
6. Only then inspect existing active tests that may cover those scenarios.
7. Classify each existing test as `KEEP`, `MOVE`, `REWRITE`, `REPLACE`, or
   `DELETE`.
8. Build the approved coverage under the new architecture.

Existing tests are evidence of current behavior. They do not define the product
contract.

## Eventual CI Direction

CI will eventually execute the progressively rebuilt authoritative backend
suite against PostgreSQL, plus separated integration and release-evidence
checks where approved. EN-01 does not wire the entire current backend product
collection into CI.

Retries remain diagnostic only. Failure artifacts must be useful, sanitized,
access-controlled, and free of secrets or sensitive user, message, and payment
data. Coverage remains risk-based, not governed by a universal percentage.
