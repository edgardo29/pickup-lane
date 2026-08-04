# Frontend Test Taxonomy

This folder contains frontend and browser tests. Frontend and Playwright
governance is separate from the backend `_backend_test_contract.py` model.

## Current Suites

### Frontend Unit Tests

Location:

```text
frontend/tests/unit/*.test.js
```

Command:

```bash
npm run test:unit
```

These tests use Node's built-in test runner for frontend helpers and other
non-DOM logic where a browser is not required.

### Signed-Out Browser Smoke Tests

Location:

```text
frontend/tests/e2e/landing.spec.js
```

Command:

```bash
npm run test:e2e:smoke
```

The existing landing Playwright test is a signed-out browser smoke test. It must
not be described as mocked browser, full-stack browser, provider-integration,
authenticated-user, or production evidence.

The current EN-01 signed-out smoke setup runs Playwright with `channel:
"chrome"`, so local and CI environments need system Google Chrome installed. A
later CI or browser-installation pass may replace this with an explicit
Playwright browser installation strategy. This requirement applies only to the
current signed-out smoke setup and does not imply broader browser portability.

## Future Suites

### Mocked Browser Tests

Mocked browser tests use Playwright with controlled application responses. They
prove frontend behavior against mocked contracts only. They do not prove backend
business rules, PostgreSQL behavior, provider behavior, or production behavior.

No current tests are classified as mocked browser coverage.

### Full-Stack Browser Tests

Full-stack browser tests use Playwright against approved test instances of the
frontend, backend, PostgreSQL, and supporting local/test infrastructure. They
must use synthetic data and must clean up browser-created backend state.

No current tests are classified as full-stack browser coverage.

### Provider-Integration Tests

Provider-integration tests use approved Firebase, Stripe, R2, email, or other
provider sandbox, emulator, or test resources. They must be separately named and
separately runnable from mocked and full-stack browser tests.

No current tests are classified as provider-integration coverage.

## Data And Auth State

Frontend and browser tests must use synthetic non-production data.

Tests must not use production users, production payments, production messages,
production files, live customer data, or real provider objects.

Browser tests must be order-independent. Each test must be able to run by
itself, in any order, and after another test fails.

Playwright creates isolated browser contexts by default, but that is not
database, provider, or file-storage isolation. Tests that create backend data,
provider objects, files, messages, or payments must own reliable setup and
cleanup.

Authenticated browser tests must generate auth state reproducibly. Do not
commit real credentials, tokens, cookies, local storage, Firebase user data, or
provider secrets. Stored auth state, when introduced, must be generated from
approved synthetic test users and kept out of source control.

## Artifact Sensitivity

Screenshots, videos, traces, Playwright reports, logs, and error-context files
can capture visible page text, request state, identifiers, URLs, local storage,
messages, payment references, and other sensitive context.

Artifacts must not contain secrets, tokens, real user data, real messages,
payment data, provider credentials, or production files. Any artifact used as
production-readiness evidence must be sanitized and access-controlled.

Artifact retention duration is not approved by EN-01. It remains deferred until
evidence-based values are approved through the production-readiness limit
process.

## Retries And Flakes

Retries are diagnostic only. A retry success does not erase the original failure
or become clean evidence by itself.

A flaky test requires an owner, reason, and repair or removal plan. No
quarantined frontend or Playwright flakes are approved by EN-01.
