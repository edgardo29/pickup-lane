# EN-01 Test Taxonomy And Isolation Baseline

Pass: EN-01  
Branch: pr/EN-01  
Status: implemented as an early taxonomy and isolation baseline only

## Scope

EN-01 creates the production-readiness test taxonomy and isolation baseline
around the existing backend compliance system. It does not replace the backend
checker, create a competing contract model, migrate legacy tests, add provider
sandbox suites, add broad domain coverage, change application code, or close
production-readiness controls by assertion.

The backend checker remains the authoritative leaf-domain backend validator.
Frontend and Playwright governance remain separate because browser tests have
different fixtures, data, artifact, and environment boundaries.

## Backend Taxonomy

### Checker-Certified Leaf-Domain Backend Tests

These are backend page or shared-domain leaf directories that have a
machine-readable `_backend_test_contract.py` and pass the existing backend
compliance checker for the selected target.

Current evidence:

- `backend/tests/pages/my_games/`

My Games is currently the only checker-contract pilot. Its contract is
`backend/tests/pages/my_games/_backend_test_contract.py`.

### Organized But Not Yet Checker-Certified Domain Tests

These tests live in the organized current structure but do not yet have a
machine-readable contract for the leaf target. They are useful current source
evidence, but they are not domain-certified by the backend checker.

Current examples:

- `backend/tests/pages/browse_games/`

Empty or contractless categories must not be presented as checker-certified
coverage.

### Shared Backend Tests

Shared tests protect rules used by more than one page or feature. Shared areas
must identify their owning rule area and affected pages/features. A shared area
is checker-certified only after it has a contract and the checker passes for
the leaf target.

Current examples:

- `backend/tests/shared/authentication/`
- `backend/tests/shared/bookings/`

### Checker And Compliance Self-Tests

The checker self-tests validate the backend test harness itself. They are not
application domain evidence.

Current examples:

- `backend/tests/test_check_backend_tests.py`
- `backend/tests/compliance/**`
- `backend/tests/test_environment_safety.py`

### Legacy Historical Tests

`backend/tests/legacy/` contains valid historical tests that have not yet been
reorganized into current page or shared-domain ownership. Legacy tests may be
reviewed for useful scenarios, but they do not count as current
production-readiness evidence and must not be collected by ordinary current-test
discovery.

EN-01 does not delete, move, rewrite, or count legacy tests.

### Future Provider-Integration Backend Tests

Provider-integration tests are not added by EN-01. Future provider suites must
use explicit approved sandbox, emulator, or test-resource configuration for
Firebase, Stripe, R2, email, and other external providers. They must be
separately named, separately runnable, and separate from mocked backend tests.

### Future Migration, Concurrency, Failure, Worker, Webhook, And Infrastructure Tests

These categories are recognized for production-readiness taxonomy purposes but
are not implemented as broad coverage in EN-01. They belong to later passes
after the relevant domain interfaces and provider or runtime environments are
stable.

## Frontend And Browser Taxonomy

### Frontend Unit Tests

Frontend unit tests live under `frontend/tests/unit/` and currently use Node's
built-in test runner. They cover frontend helpers and non-DOM logic where that
is the correct layer.

### Signed-Out Browser Smoke Tests

The existing Playwright landing test is classified only as a signed-out browser
smoke test. It verifies a public page in a browser and must not be described as
mocked, full-stack, provider-integration, authentication, or production evidence.

Current evidence:

- `frontend/tests/e2e/landing.spec.js`

### Mocked Browser Tests

Mocked browser tests will run Playwright with controlled application responses.
They prove browser behavior against a mocked contract only. No current tests are
classified as mocked browser coverage.

### Full-Stack Browser Tests

Full-stack browser tests will run the browser against approved local or test
instances of the frontend, backend, and supporting infrastructure. No current
tests are classified as full-stack browser coverage.

### Provider-Integration Browser Tests

Provider-integration tests will use approved Firebase, Stripe, R2, or other
provider sandbox/emulator resources. No current tests are classified as
provider-integration browser coverage.

## Isolation Baseline

### Database Safety

Standard backend tests may only use the repository's dedicated PostgreSQL test
database name:

```text
pickup_lane_test_db
```

The database rule is exact and anchored. A database is not safe merely because
its name contains `test`; names such as `pickup_lane_test_db_backup`,
`pickup_lane_prod_test_db`, development, staging, and production names are
rejected before cleanup and test execution.

EN-01 does not create, migrate, reset, drop, rename, or connect to any database
as part of the safety rule itself.

### Cleanup Completeness

Backend test session initialization compares SQLAlchemy's registered tables
with the `TEST_TABLES` cleanup inventory. A registered table missing from the
cleanup list fails clearly unless it has an explicit documented exclusion.

There are no cleanup exclusions at EN-01.

### Network And Provider Isolation

Standard backend tests block ordinary external network sockets. Only the
configured dedicated PostgreSQL test database socket is allowed. This prevents
normal tests from contacting live Firebase, Stripe, R2, email, or other external
providers. Mocked provider behavior remains allowed because mocks do not require
provider network access.

EN-01 does not add a provider sandbox suite.

### Synthetic Data

Current standard backend and frontend tests must use synthetic non-production
data. Tests must not use production users, payments, messages, files, objects,
or provider resources.

### Browser Artifacts

Screenshots, videos, traces, reports, logs, and error-context artifacts can
capture page text, request state, identifiers, and other sensitive context.
Artifacts must be sanitized and access-controlled before they become
production-readiness evidence.

Artifact retention duration remains deferred until evidence-based values are
approved through the foundation limits method.

### Flaky Tests And Retries

Retries are diagnostic only. A retry success does not erase the original failure
or become clean evidence by itself. A flaky test requires an owner, reason,
containment, and repair or removal plan. No quarantined flakes are approved by
EN-01.

## Control Mapping

### TST-001

EN-01 partially satisfies TST-001 by documenting the current suite taxonomy,
separating current, checker-certified, organized-but-not-certified, legacy,
frontend unit, smoke browser, and future suite categories.

Not closed: broad current coverage, service/domain coverage, provider sandbox,
migration, deterministic concurrency, security, production smoke, and enforced
CI evidence remain later work.

### TST-003

EN-01 partially supports TST-003 by classifying the existing landing Playwright
test as signed-out smoke only and documenting browser artifact and retry rules.

Not closed: broad Playwright quality evidence, auth-state generation,
deterministic browser data cleanup, screenshots/videos policy in CI, device
matrix, and CI execution remain later work.

### TST-004

EN-01 partially supports TST-004 by separating taxonomy language for mocked
browser, full-stack browser, and provider-integration tests and by preventing
standard backend tests from making live provider calls.

Not closed: actual provider sandbox/emulator suites, full-stack browser
environment, provider reports, and CI separation remain later work.

### TST-010

EN-01 partially satisfies TST-010 by strengthening the backend test database
guard, adding cleanup-table completeness detection, documenting synthetic-data
rules, excluding legacy from ordinary current discovery, and blocking ordinary
external network sockets during standard backend tests.

Not closed: browser-created data cleanup, provider-object cleanup, background
worker isolation, time-control expansion, and full parallel resource isolation
remain later work.

### TST-011

GOV-01 supplied the foundation decision for diagnostic retries, flake handling,
artifact sensitivity, and risk-based coverage. EN-01 applies that decision to
the test taxonomy baseline.

Not closed: implemented CI artifact retention values, recurring flake workflow
evidence, artifact storage controls, and CI retry-report evidence remain later
work.

## Deferred Work

- Contract-certify additional backend leaf domains when those domains are
  actively polished.
- Add provider sandbox/emulator suites only after approved provider resources
  and secret boundaries exist.
- Add deterministic migration, concurrency, failure, worker, webhook, and
  infrastructure suites in their later passes.
- Add full-stack and mocked browser suites when stable backend/frontend
  contracts are ready.
- Add CI gates and artifact retention after stable commands, job names, and
  evidence policies are approved.
