# Frontend Test Taxonomy

This folder contains frontend and browser tests. Frontend and Playwright
execution guidance is separate from the guarded backend pytest suites and their
behavior-owned test roots.

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

Install the repository-selected browser and its system dependencies with:

```bash
npx playwright install --with-deps chromium
```

The existing landing Playwright test is a signed-out browser smoke test. It must
not be described as mocked browser, full-stack browser, external-service
integration, authenticated-user, or production verification.

The signed-out smoke setup uses Playwright's version-pinned Chromium browser.
CI installs that browser explicitly after `npm ci`; it does not depend on an
ambient system Chrome installation.

## Future Suites

### Mocked Browser Tests

Mocked browser tests use Playwright with controlled application responses. They
verify frontend behavior against mocked API responses only. They do not verify
backend business rules, PostgreSQL behavior, external-service behavior, or
production behavior.

No current tests are classified as mocked browser coverage.

### Full-Stack Browser Tests

Full-stack browser tests use Playwright against configured non-production
instances of the frontend, backend, PostgreSQL, and supporting local/test
infrastructure. They must use synthetic data and must clean up browser-created
backend state.

No current tests are classified as full-stack browser coverage.

### External-Service Integration Tests

External-service integration tests use non-production Firebase, Stripe, R2,
email, or other sandbox, emulator, or test resources. They must be separately
named and separately runnable from mocked and full-stack browser tests.

No current tests are classified as external-service integration coverage.

## Data And Auth State

Frontend and browser tests must use synthetic non-production data.

Tests must not use production users, production payments, production messages,
production files, live customer data, or real external-service objects.

Browser tests must be order-independent. Each test must be able to run by
itself, in any order, and after another test fails.

Playwright creates isolated browser contexts by default, but that is not
database, external-service, or file-storage isolation. Tests that create backend
data, external-service objects, files, messages, or payments must own reliable
setup and cleanup.

Authenticated browser tests must generate auth state reproducibly. Do not
commit real credentials, tokens, cookies, local storage, Firebase user data, or
external-service secrets. Stored auth state, when introduced, must be generated
from dedicated synthetic test users and kept out of source control.

## Artifact Sensitivity

Screenshots, videos, traces, Playwright reports, logs, and error-context files
can capture visible page text, request state, identifiers, URLs, local storage,
messages, payment references, and other sensitive context.

Artifacts must not contain secrets, tokens, real user data, real messages,
payment data, external-service credentials, or production files. Any artifact
used as production-readiness evidence must be sanitized and access-controlled.

Artifact retention duration remains unresolved until an owner decision defines
the required value.

## Retries And Flakes

CI and local Playwright runs use zero retries so an initial failure cannot be
hidden by a later passing attempt. Traces are retained on failure for diagnosis.

A flaky test requires an owner, reason, and repair or removal plan. No
quarantined frontend or Playwright flakes are currently permitted.
