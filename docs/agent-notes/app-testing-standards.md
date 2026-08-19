# App Testing Standards

This document defines the application-wide standard for discovering risks, edge
cases, failure scenarios, safeguards, and required test coverage across Pickup
Lane.

It is required reading after a page or feature is created, materially changed,
or refactored. The purpose is not merely to confirm that the page renders or
that existing tests pass. The purpose is to examine the complete feature path,
identify realistic ways it can fail or be abused, verify the safeguards that
protect it, and add missing coverage at the correct test layer.

## Use This Together With

This document does not replace layer-specific testing standards. After a
scenario is assigned to an owning layer, follow the relevant repository guide:

- The backend testing standard for pytest, FastAPI, service, PostgreSQL,
  authorization, provider-boundary, and backend security test implementation.
- The frontend testing standard for React, Vite, the current frontend unit-test
  runner, future React component testing, accessibility, and browser-facing
  behavior.
- The Playwright testing standard for mocked browser, full-stack browser, and
  provider-integration test structure.
- Database, architecture, security, infrastructure, and finalized feature or
  domain documents that define the behavior being protected.

When a scenario is assigned to backend ownership, the EN-01 backend testing
architecture governs directory ownership, stable requirement IDs, human testing
records, pytest metadata, checker compliance, and generated traceability.
Expected behavior comes from authority. Current trusted backend tests may
provide evidence of current behavior after expectations are established.
Production-readiness handling of excluded backend tests is governed by
`backend-testing.md`; do not use this application-wide standard to bypass that
rule.

When these sources conflict, do not guess. Report the conflict before encoding
an uncertain expectation into a test.

This document defines required analysis and coverage. It does not grant an agent
permission to run test suites, migrations, containers, provider calls, or other
commands. Command execution remains governed by the relevant layer-specific
execution policy and current task or workflow instruction.

## Normative Language

The words **must**, **must not**, and **required** define hard gates. Work is not
complete when an applicable hard gate is unmet.

The words **should** and **prefer** define strong defaults. Departures require a
clear reason in the completion report.

## Relevance And Scope

Apply this standard to the systems that the page or feature actually touches.
Do not mechanically force Stripe, Firebase, R2, Docker, background jobs,
Playwright, accessibility, or database-concurrency analysis into a page review
when that system is genuinely unrelated to the workflow under review.

At the same time, do not limit the review to files changed by the refactor. If a
page depends on authentication, authorization, persistence, provider state,
background cleanup, shared lifecycle rules, or another domain's data, that
system is relevant even when its files were not edited.

For every major scenario category, classify unrelated systems as
`not_applicable` with a short reason. Classify shared behavior as
`covered_elsewhere`, `partial`, `missing`, or `blocked` instead of pretending
the page owns it.

## Current Application Stack

The current standard assumes the following stack:

- Frontend: React and Vite.
- Frontend unit tests: Node's built-in test runner where applicable.
- React component tests: target standard is Vitest and React Testing Library
  when component testing is adopted.
- Backend: FastAPI.
- Backend tests: pytest.
- Database: PostgreSQL.
- Authentication: Firebase Authentication.
- Payments: Stripe.
- Object and data-lake storage: Cloudflare R2 through its S3-compatible API.
- Browser and full-stack tests: Playwright.
- Local and automated test infrastructure: Docker and Docker Compose.

When the stack changes, update this document and the relevant layer-specific
standard before treating the new dependency as covered.

## Purpose

Application testing must answer all of the following questions:

1. What behavior must the feature provide?
2. What must never happen?
3. How could a normal user, malicious user, external provider, browser, worker,
   database transaction, deployment, or network condition violate those rules?
4. Which safeguards prevent or contain each failure?
5. Which layer owns each safeguard?
6. Which automated or manual test proves the safeguard works?
7. Which important gaps remain?

A feature is not adequately tested merely because:

- The frontend has component tests.
- The backend has endpoint tests.
- Existing tests pass.
- A happy-path Playwright test passes.
- The line or branch coverage percentage increased.

Coverage is adequate only when the important rules, invariants, boundaries,
failure paths, and cross-system interactions have been examined and protected.

## Core Principles

### Test Behavior, Not Implementation Shape

Tests should protect externally meaningful behavior, public contracts, domain
rules, and system invariants. Refactoring internal component structure,
function names, or private implementation details should not break a test when
observable behavior remains correct.

### Safeguard First, Test Second

For every meaningful scenario, distinguish:

1. **Scenario:** What can happen?
2. **Risk:** What damage or incorrect behavior could result?
3. **Expected behavior:** What must the system do?
4. **Safeguard:** What prevents, rejects, contains, rolls back, or recovers from
   the failure?
5. **Proof:** Which test or verification demonstrates that safeguard?

A test is not automatically the safeguard. Safeguards may include:

- Server-side authorization.
- Input validation.
- Database constraints.
- Transactions and row locks.
- Idempotency keys.
- State-transition guards.
- Unique provider-event ledgers.
- Retry limits.
- Timeouts.
- Rate limits.
- File-size and content restrictions.
- Audit records.
- Recovery jobs.
- Health checks.
- Least-privilege credentials.

The test proves the safeguard operates correctly.

### Test at the Lowest Reliable Owning Layer

Every rule must be tested at the lowest layer that can reliably prove it.
Critical user workflows should additionally receive full-stack browser
coverage.

Examples:

- A React loading state belongs in a frontend test.
- A booking uniqueness invariant belongs in backend and PostgreSQL tests.
- An API request and response contract belongs in API integration tests.
- A critical booking journey belongs in Playwright after its lower-level rules
  are already covered.
- Stripe webhook ordering and duplication belong in payment integration tests,
  not only in a browser test.

### Frontend Is Not a Security or Integrity Boundary

Disabled buttons, hidden controls, client validation, and route guards improve
user experience but do not protect the system by themselves.

Any rule involving authorization, ownership, money, capacity, state,
persistence, privacy, or sensitive data must be enforced and tested on the
server and, when applicable, in PostgreSQL.

### Test What Pickup Lane Controls

The standard suite should test Pickup Lane's behavior at external boundaries,
not attempt to retest Stripe, Firebase, Cloudflare, browsers, or PostgreSQL as
products.

Mock or fake the provider network at the application-owned boundary for most
behavior tests. Use a smaller emulator, sandbox, or test-bucket suite to verify
that the adapter and real provider contract still work.

### Determinism and Isolation Are Required

Tests must not depend on:

- Production data or credentials.
- Developer-local data.
- Test execution order.
- Uncontrolled current time.
- Arbitrary sleeps.
- Public network availability in the standard suite.
- State left by another test.
- A previously running container or service.
- Random data without controlled uniqueness or a reproducible seed.

### Passing for the Wrong Reason Is Failure

A test must prove the intended rule and intended safeguard. Examples of weak
coverage include:

- A request returned a non-500 response.
- A button exists but its action was never verified.
- A database insert failed, but the intended constraint was not identified.
- A forbidden request returned 403, but prohibited side effects were not
  checked.
- A Playwright test passed because mocked data bypassed the real integration
  under review.
- A provider failure test mocked the entire service function whose recovery
  logic was supposed to be tested.

## Non-Negotiable Completion Gates

A page or feature testing review must not be marked complete until all
applicable gates below are satisfied:

1. The finalized feature and owning-domain rules were reviewed.
2. The complete feature path and participating systems were identified.
3. Feature-specific invariants were written.
4. Existing frontend, backend, database, browser, provider, and infrastructure
   coverage was inspected where applicable.
5. The scenario matrix and relevant failure transformations were completed for
   every applicable category in this document.
6. Every relevant scenario was classified as `covered`, `partial`, `missing`,
   `covered_elsewhere`, `manual`, `not_applicable`, or `blocked`.
7. `covered_elsewhere`, `manual`, `not_applicable`, and `blocked`
   classifications include a reason.
8. Every high-risk rule identifies its required safeguard.
9. Every required safeguard has a test or an explicitly reported gap.
10. Each test is assigned to the correct owning layer.
11. Frontend behavior is tested through user-visible interactions where the
    frontend owns the behavior.
12. Backend rules are enforced and tested independently of frontend controls
    where the backend owns the safeguard.
13. PostgreSQL-specific integrity is tested against PostgreSQL where
    applicable.
14. Critical cross-system workflows have appropriate full-stack coverage.
15. Provider-backed features have local boundary tests and selected emulator,
    sandbox, or test-resource integration where applicable.
16. Rejected and failed operations verify prohibited side effects where
    meaningful.
17. Retry, duplicate, stale-state, and concurrency behavior was considered for
    every mutation and asynchronous workflow.
18. Security-sensitive pages classify authentication, authorization, data
    exposure, abuse, and resource-limit scenarios.
19. Provider-backed features classify timeout, retry, duplicate, late,
    out-of-order, invalid-response, and partial-success scenarios.
20. Accessibility combines appropriate automation and manual review where
    applicable.
21. Time-sensitive behavior uses a controlled application clock.
22. Test data, time, credentials, and infrastructure are deterministic,
    isolated, and non-production.
23. Remaining gaps, unresolved rules, commands run, and commands not run are
    reported.
24. Review confirms the tests would fail for the correct reason if protected
    behavior regressed.

If a gate cannot be satisfied, report the work as incomplete, blocked, or
partially verified. Do not describe the page as fully tested.

## Phased Completion Labels

Pickup Lane often finishes implementation, backend tests, frontend tests,
Playwright, and release hardening in separate waves. Do not weaken this
standard for phased work. Instead, report the exact phase that is complete and
the phases that remain.

Use these labels when applicable:

- `implementation_review_complete`: implementation has been reviewed against
  finalized behavior, and remaining test or safeguard gaps are documented.
- `backend_test_complete`: backend/API/database coverage required for the
  current phase has been added or verified.
- `frontend_test_complete`: frontend unit or component coverage required for
  the current phase has been added or verified.
- `playwright_complete`: required mocked-browser or full-stack browser coverage
  has been added or verified.
- `provider_integration_complete`: required Firebase, Stripe, R2, or other
  provider-boundary coverage has been added or verified.
- `release_ready`: all relevant implementation, safeguard, automated, manual,
  provider, and unresolved-gap requirements for the feature are satisfied.

Do not use an unqualified `complete` when only one phase is finished.

## Required Workflow After a Page Refactor

After refactoring a page, the agent must review more than the changed React
files.

### Step 1: Read the Sources of Truth

Identify and read:

- The finalized page or feature specification.
- Owning-domain specifications for shared behavior.
- This application testing standard.
- Relevant layer-specific testing standards.
- Relevant security, database, provider, and infrastructure rules.

Expected behavior must not be derived solely from current implementation or
existing tests.

### Step 2: Trace the Complete Feature Path

Inspect every participating part of the workflow, including as applicable:

- Route and page entry.
- React components and hooks.
- Client state, forms, dialogs, tables, filters, and pagination.
- API client functions.
- FastAPI routes and request schemas.
- Authentication dependencies.
- Authorization and ownership policies.
- Service-layer business rules.
- PostgreSQL models, indexes, constraints, triggers, and transactions.
- Background jobs and durable work records.
- Stripe requests, PaymentIntents, refunds, and webhooks.
- Firebase client and Admin SDK behavior.
- R2 object operations and metadata.
- Docker services, environment variables, health checks, and startup order.
- Existing tests across all layers.

Do not assume a page owns every rule it consumes. Shared invariants must remain
with their owning domain.

### Step 3: Write the Feature Invariants

Before listing individual tests, state what must always remain true.

Examples:

- Unauthorized users never receive private resource data.
- A player cannot occupy more capacity than the product permits.
- One logical booking cannot create multiple charges.
- Replayed provider events do not repeat side effects.
- A terminal state cannot transition backward without an explicit restore rule.
- A failed mutation does not leave partial persisted data.
- Database rows, provider objects, counters, and displayed status do not silently
  disagree.
- No production secret or credential is exposed to the frontend or test logs.

Feature-specific invariants are required. Do not rely only on generic examples.

### Step 4: Build the Scenario Matrix

Use the categories and failure transformations in this document. Classify every
relevant item and map items that need coverage to existing or planned tests.

### Step 5: Identify Existing Safeguards and Gaps

For each relevant scenario, identify:

- Existing safeguard.
- Owning layer.
- Existing test coverage.
- Whether coverage proves the intended result and prohibited side effects.
- Missing safeguard.
- Missing test.

Do not add a test that merely records incorrect current behavior. Report
specification and implementation conflicts.

### Step 6: Select the Correct Test Layer

Use the layer-selection rules in this document. Avoid testing every scenario at
every layer.

### Step 7: Implement or Plan Missing Coverage

Add missing tests when behavior is finalized and the task permits changes.
When implementation is blocked, create a concrete gap record rather than a
vague note.

### Step 8: Report Completion Honestly

Provide the required completion report at the end of this document.

## Scenario Discovery Method

No process can enumerate literally every possible failure. This standard
requires a systematic review of realistic, dangerous, rare, and high-impact
conditions.

For each workflow, vary the following dimensions:

- **Actor:** anonymous, valid player, owner, participant, unrelated user, admin,
  inactive user, suspended user, deleted user, revoked user, provider, worker.
- **Resource state:** missing, empty, active, pending, full, expired, cancelled,
  hidden, removed, failed, completed, partially processed, stale.
- **Action:** read, create, update, delete, restore, confirm, cancel, retry,
  upload, download, pay, refund, join, leave, publish.
- **Input:** valid, missing, malformed, boundary, oversized, duplicate, hostile,
  stale, conflicting, unexpected.
- **Timing:** before boundary, at boundary, after boundary, delayed, timed out,
  retried, concurrent, out of order.
- **Dependency condition:** healthy, unavailable, slow, inconsistent, partial
  success, malformed response, duplicate event.
- **Client condition:** first load, refresh, back navigation, two tabs, offline,
  slow network, small screen, keyboard-only use.

Do not generate the full Cartesian product mechanically. Select combinations
that represent distinct rules, distinct risks, or realistic interactions.

## Failure Transformations

Apply the following transformations to every important read, mutation,
background job, and provider workflow:

### Omit

What happens when a required field, header, token, related record, provider
value, configuration value, or expected event is missing?

### Empty

What happens with an empty collection, empty page, empty string, whitespace-only
input, zero results, or zero remaining capacity?

### Corrupt

What happens when data has an invalid type, invalid enum, malformed cursor,
invalid signature, unexpected encoding, invalid object metadata, or impossible
combination?

### Exceed

What happens when length, count, file size, page size, capacity, rate, storage,
timeout, or resource limits are exceeded?

### Duplicate

What happens when the user clicks twice, the client retries, two tabs submit,
two workers process, a webhook is replayed, or the same object key is reused?

### Delay

What happens when a response, webhook, job, upload, authentication result, or
database lock is slow or arrives after the user has moved on?

### Reorder

What happens when provider events, status updates, or asynchronous jobs arrive
in a different order than expected?

### Interrupt

What happens when the browser closes, network disconnects, worker crashes,
container restarts, transaction fails, or provider call succeeds while the
local request fails?

### Race

What happens when two actors or processes compete for the same resource,
capacity, state transition, object key, refund, or final available spot?

### Expire or Revoke

What happens when a token, role, relationship, hold, signed URL, temporary
credential, session, or resource expires or is revoked while the page remains
open?

### Tamper

What happens when a caller changes IDs, hidden fields, ownership fields, role
values, prices, totals, status values, object paths, methods, or request order?

### Retry

What can be retried safely, what must not be repeated, and what persisted ledger
or idempotency record proves the result?

### Recover

After failure, can the user or system determine what happened, retry safely,
reconcile partial state, clean abandoned resources, and avoid silent data loss?

## Required Scenario Categories

Every feature review must classify each relevant item below as `covered`,
`partial`, `missing`, `covered_elsewhere`, `manual`, `not_applicable`, or
`blocked`. Items classified as `partial`, `missing`, or `blocked` must identify
the remaining safeguard, test, rule, or decision gap.

## 1. User Journeys and Normal Behavior

Classify:

- Initial page entry through every supported route.
- Valid data load.
- Every supported successful action.
- Required confirmations and cancellations.
- Navigation to related pages.
- Refresh after a successful mutation.
- Returning to the page after leaving.
- Browser back and forward behavior when relevant.
- Multiple valid records and realistic populated states.
- Correct persisted and displayed result after each mutation.

A happy path is necessary but never sufficient.

## 2. Frontend Rendering and Page States

Classify:

- Initial loading state.
- Background refresh state.
- Empty state.
- Partial-data state.
- Success state.
- Validation-error state.
- Authentication failure.
- Authorization failure.
- Not-found state.
- Conflict or stale-state response.
- Rate-limit response.
- Server failure.
- Network timeout or offline state.
- Retry state.
- Partial-success state.
- Long content and overflow.
- Large collections.
- Small viewport and responsive behavior.
- User action while a request is pending.
- Late response after unmount or navigation.
- Error boundary behavior when applicable.

The UI must not present a failed or uncertain operation as successful.

## 3. Input Validation and Boundary Values

For every user-controlled or provider-controlled input, classify:

- Missing required value.
- Null when null is not allowed.
- Empty string.
- Whitespace-only string.
- Minimum accepted value.
- One value below minimum.
- Maximum accepted value.
- One value above maximum.
- Invalid type.
- Invalid enum.
- Invalid date or timestamp.
- Invalid timezone or offset.
- Invalid identifier.
- Duplicate value.
- Conflicting fields.
- Unexpected extra fields.
- Unicode, emoji, combining characters, and right-to-left text where relevant.
- Newlines and multiline text.
- HTML and script-like text.
- Extremely large numeric values.
- Negative values where prohibited.
- Malformed cursor, token, signature, or object key.
- Frontend validation bypass through a direct API request.

Server-side validation is required even when equivalent frontend validation
exists.

## 4. Authentication and Identity

Classify:

- Anonymous access.
- Valid Firebase-authenticated identity.
- Missing bearer token.
- Malformed token.
- Expired token.
- Revoked token when supported by the verification policy.
- Token for a different Firebase project or audience.
- Valid Firebase identity with no local Pickup Lane user.
- Local user marked inactive, suspended, or deleted.
- Firebase identity linked to the wrong local account.
- User signs out while a protected request is pending.
- User changes account while stale client state remains.
- Authentication emulator accidentally enabled outside tests.
- Test-only unsigned emulator token rejected by production-mode configuration.

Authentication proves identity only. It does not prove authorization.

## 5. Authorization, Ownership, and Visibility

Classify every action and every route shape that can reveal or mutate a
resource:

- Owner access.
- Participant or relationship-based access.
- Unrelated-user denial.
- Admin access.
- Inactive, suspended, deleted, or revoked privileged-user denial.
- Horizontal access by changing a resource ID.
- Vertical access by changing role or calling an admin endpoint.
- Stale, expired, cancelled, removed, or historical relationships.
- Hidden, private, cancelled, removed, or unpublished resources.
- Detail route disclosure.
- List and filter disclosure.
- Search and lookup disclosure.
- Aggregate and count disclosure.
- Mutation route disclosure.
- Unauthorized field updates and mass assignment.
- Excessive response fields.
- Correct 401, 403, or 404 behavior according to policy.
- Required cache and privacy headers for private data.

Frontend route hiding does not count as authorization coverage.

## 6. State Machines and Lifecycle Rules

When a feature has statuses or lifecycle fields, build an authoritative state
matrix.

Classify:

- Every allowed state transition.
- Every prohibited transition.
- Repeated transition attempt.
- Transition from each terminal state.
- Transition after the underlying record changed.
- Transition with stale page data.
- Transition attempted by two actors concurrently.
- Transition whose provider operation succeeded but local persistence failed.
- Restore or rollback behavior when explicitly supported.
- Historical rows that must not grant current privileges.
- Counters, timestamps, audit records, and related rows produced by each
  transition.

Do not assume similarly named statuses behave the same way.

## 7. API Contract and Client-Server Integration

Classify:

- HTTP method and path.
- Authentication requirements.
- Request body, query, path, and header schema.
- Required and optional fields.
- Enum and nullability behavior.
- Exact success status.
- Exact failure statuses.
- Response shape and required fields.
- Absence of internal or sensitive fields.
- Date, time, decimal, currency, and identifier serialization.
- Pagination cursor format.
- Stable sorting and tie-breaking.
- Frontend interpretation of every status and enum.
- Error response mapping to usable UI feedback.
- Backward compatibility when a contract is shared or versioned.
- OpenAPI schema drift.
- Runtime behavior that a schema alone cannot prove.

Generated OpenAPI validation is useful but does not replace behavioral contract
tests.

## 8. PostgreSQL Integrity and Persistence

Classify:

- Required `NOT NULL` rules.
- Unique and composite uniqueness rules.
- Foreign keys.
- Check constraints.
- Exclusion constraints where applicable.
- Referential actions on delete and update.
- Soft-delete interactions with uniqueness.
- Transaction commit and rollback.
- Partial-write prevention.
- Orphan prevention.
- Counter and aggregate consistency.
- Migration upgrade from the supported prior state.
- Migration failure behavior.
- Index-backed uniqueness and query assumptions.
- Constraint failure tied to the intended named constraint or stable error.
- Fresh-session verification of persisted state.
- Rejected transaction cleanup before session reuse.
- Concurrent updates and lock behavior.
- Serialization or deadlock retry behavior where applicable.

Tests that depend on PostgreSQL behavior must run against PostgreSQL, not a
substitute database with different semantics.

## 9. Duplicate Requests, Idempotency, and Concurrency

Every mutation must be reviewed for duplicate and concurrent execution.

Classify:

- Double click.
- Client retry after timeout.
- Same request from two tabs.
- Same logical request with different transport request IDs.
- Two users acting on the same record.
- Two admins resolving the same case.
- Two workers claiming the same job.
- Competing requests for the final capacity unit.
- Concurrent update and delete.
- Concurrent cancel and payment completion.
- Duplicate webhook.
- Duplicate file upload or object key.
- Idempotency-key reuse with the same parameters.
- Idempotency-key reuse with different parameters.
- Transaction serialization failure or deadlock.
- Safe whole-transaction retry.
- Unique database constraint as final duplicate protection.

Frontend button disabling is useful but never sufficient duplicate protection.

## 10. Background Jobs and Asynchronous Work

Classify:

- Job creation and durable persistence.
- Worker claim behavior.
- No available worker.
- Worker crash before work starts.
- Worker crash after partial work.
- Retry after transient failure.
- Permanent failure and terminal status.
- Duplicate worker claim.
- Stale job lease or lock.
- Batch with all success.
- Batch with partial success.
- Batch with all failure.
- Per-item retry.
- Counters and summary status consistency.
- Cancellation while queued.
- Cancellation while processing.
- User or resource becomes ineligible before execution.
- Late completion after the originating page is closed.
- Idempotent reprocessing.
- Audit and operational visibility.
- Cleanup or reconciliation of abandoned work.

Uncontrolled background work must not leak between tests.

## 11. External Provider Boundaries

For every external dependency, classify:

- Successful request and expected response.
- Client-side validation failure before request.
- Provider rejection.
- Authentication or permission failure.
- Timeout.
- Network exception.
- Rate limit.
- Malformed or unexpected provider response.
- Provider returns success but local commit fails.
- Local commit succeeds but response to caller is lost.
- Duplicate provider event.
- Late provider event.
- Out-of-order provider event.
- Provider retry.
- Local retry.
- Provider object already exists.
- Provider object is missing.
- Reconciliation behavior.
- Least-privilege test credentials.
- Separation from production data and credentials.

The application must validate provider data instead of trusting it blindly.

## 12. Stripe Payments

For every payment-affecting feature, classify:

- PaymentIntent creation.
- Required amount, currency, metadata, and ownership.
- Idempotency key generation and reuse.
- Successful payment.
- Declined payment.
- Authentication-required payment.
- Processing or delayed payment.
- Cancelled payment.
- Client closes or refreshes during confirmation.
- API timeout after Stripe accepted the request.
- Webhook as the authoritative completion signal.
- Valid webhook signature.
- Raw request body preserved for signature verification.
- Missing or invalid signature.
- Duplicate webhook event.
- Distinct events representing the same logical object transition.
- Out-of-order event.
- Late event after local cancellation.
- Unsupported event type.
- Refund success, failure, duplicate request, and retry.
- Payment succeeds but booking creation or local persistence fails.
- Booking exists but payment later fails.
- No duplicate charge, booking, credit, refund, or ledger effect.
- Test-mode or sandbox isolation.
- No live payment details in automated tests.

Provider event IDs and local effect ledgers should make repeated processing safe.

## 13. Firebase Authentication

Classify:

- Frontend sign-in and sign-out behavior.
- Auth loading state before identity is known.
- Token acquisition failure.
- Token refresh.
- Expired and revoked credentials.
- Backend token verification.
- Firebase project and audience validation.
- Local user lookup and account-state enforcement.
- Emulator user creation and cleanup.
- Emulator data isolation.
- Email verification, reset, or provider flow when the feature depends on it.
- Admin SDK emulator configuration.
- Production-mode rejection of emulator tokens.
- Fail-closed behavior when Firebase configuration is missing or invalid.

Most local authorization tests should use controlled identities at the
application boundary. Selected integration tests should use the Firebase Auth
Emulator.

## 14. Cloudflare R2 and Object Storage

Classify:

- Upload success.
- Download success.
- Delete success.
- Missing object.
- Duplicate object key.
- Unauthorized key or prefix.
- Path traversal-like object names.
- Invalid file type.
- Oversized object.
- Empty object when prohibited.
- Incorrect content type.
- Incorrect or oversized metadata.
- Checksum mismatch where used.
- Interrupted upload.
- Timeout.
- Authentication and permission failure.
- Presigned URL operation restriction.
- Presigned URL object restriction.
- Presigned URL expiration.
- Reuse after expiration.
- Database row created but upload fails.
- Upload succeeds but database commit fails.
- Delete succeeds but database update fails.
- Safe cleanup of abandoned objects.
- Object exists while metadata row is missing.
- Metadata row exists while object is missing.
- R2-specific behavior that differs from generic S3 assumptions.
- Test-bucket isolation and cleanup.

Because R2 is S3-compatible but not identical to every S3 implementation, local
S3-compatible adapter tests should be supplemented by a smaller R2 test-bucket
suite for the operations Pickup Lane actually uses.

## 15. Network and Distributed Failure Behavior

Classify:

- Offline before action.
- Connection lost during action.
- Slow response.
- Client timeout.
- Server timeout.
- Retry after uncertain outcome.
- Response arrives after navigation.
- Duplicate response handling.
- Stale response overwrites newer state.
- Partial success across systems.
- Dependency unavailable at startup.
- Dependency becomes unavailable during operation.
- Circuit breaker or retry budget when implemented.
- Honest UI status when the outcome is unknown.
- Recovery and reconciliation path.

An uncertain result must not be silently displayed as a confirmed failure or
confirmed success without evidence.

## 16. Security and Abuse

Use the OWASP Web Security Testing Guide, Application Security Verification
Standard, and API Security Top 10 as review baselines.

Classify:

- Authentication bypass.
- Horizontal object-level authorization.
- Vertical function-level authorization.
- Object-property authorization and mass assignment.
- Excessive data exposure.
- Hidden-resource enumeration.
- Parameter and method tampering.
- Invalid HTTP methods.
- Injection attempts relevant to the input and storage path.
- Stored and reflected script-like input.
- File and object path traversal.
- Server-side request forgery when the server fetches caller-provided URLs.
- Unsafe redirect behavior.
- Cross-site request forgery when cookie-based authentication or sensitive
  browser credentials make it applicable.
- CORS configuration.
- Sensitive information in errors, logs, URLs, browser storage, or responses.
- Secrets exposed through Vite client environment variables or built assets.
- Resource exhaustion through page size, search, upload, repeated action, or
  expensive filters.
- Abuse of sensitive business flows.
- Rate-limit behavior where required.
- Unsafe consumption of provider responses.
- Webhook signature validation.
- Security headers and private-cache behavior.
- Audit-log integrity and redaction.
- Test and debug endpoints disabled outside approved environments.

Security testing must prove authorization and validation at the object, action,
and property level.

## 17. Accessibility and Browser Behavior

Automated accessibility checks are useful but do not prove complete WCAG
conformance. Combine automated tests with keyboard and human review for critical
interfaces.

Classify:

- Semantic roles and accessible names.
- Form labels and instructions.
- Validation errors associated with fields.
- Keyboard access to all actions.
- Logical focus order.
- Focus placement after opening and closing dialogs.
- Focus restoration.
- Escape and cancellation behavior.
- Screen-reader announcement of important dynamic changes.
- Loading and error status semantics.
- Color contrast and non-color indicators.
- Text zoom and responsive reflow.
- Touch-target size where relevant.
- Reduced-motion behavior where applicable.
- Disabled versus unavailable action communication.
- Browser back, refresh, and navigation behavior.
- Supported browser projects for critical workflows.

Prefer semantic queries such as role and accessible name in frontend and
Playwright tests.

## 18. Performance and Resource Limits

Performance requirements must be explicit. Do not invent arbitrary thresholds.

Classify:

- Maximum supported page size.
- Large result set.
- Stable pagination under load.
- Expensive search or filter behavior.
- Repeated request rate.
- Upload size and duration.
- Memory-heavy client rendering.
- Slow query or missing-index regression for critical paths.
- Background batch size.
- Provider rate limits.
- Timeout and retry amplification.
- Resource cleanup after failure.
- Denial-of-service exposure through unbounded input or work.

Large load tests and destructive tests should run in separate controlled
workflows, not the normal pull-request suite.

## 19. Configuration, Docker, and Environment Safety

Classify:

- Required environment variable missing.
- Invalid environment variable.
- Test, development, and production configuration separation.
- Production secret accidentally passed to a test service.
- Secret accidentally exposed through a Vite client variable.
- Wrong Firebase project.
- Wrong Stripe mode or key.
- Wrong R2 bucket or endpoint.
- Test database points to development, staging, or production.
- Container starts before PostgreSQL or another dependency is ready.
- Health check reports readiness accurately.
- Migration runs before application startup when required.
- Migration failure prevents unsafe startup.
- Container restart and dependency reconnection.
- Ephemeral test data and volume cleanup.
- Orphaned containers and networks.
- Pinned and reviewed images where reproducibility or security requires it.
- Compose configuration does not request unnecessary host privileges.
- Test-only ports and debug settings are not enabled in production.

Docker Compose dependency order must use readiness checks where startup races
are possible. Container start is not equivalent to service readiness.

## 20. Observability, Audit, Recovery, and Operations

Classify:

- Required audit event created once.
- Actor, target, action, reason, and result recorded correctly.
- Sensitive values redacted.
- Failed attempt recorded only when policy requires it.
- Correlation or provider request ID retained where useful.
- Logs distinguish transient and permanent failure.
- No secrets, tokens, payment data, or private message content leaked.
- Operational status matches persisted truth.
- Metrics or counters remain consistent after retry.
- Reconciliation job can identify mismatched local and provider state.
- Recovery action is idempotent.
- Manual repair does not bypass required audit behavior.
- Alerts are testable when alerting is a finalized requirement.

Do not test logging merely because logging exists. Test it when the log, audit,
metric, or alert is part of a security, support, compliance, or recovery
requirement.

## Test Layer Selection

Use the following ownership rules.

### Static Validation

Use linting, type checking, schema validation, migration inspection, and build
checks for defects that can be proven without runtime behavior.

Examples:

- Invalid imports.
- Missing awaits identified by linting.
- Vite production build failure.
- OpenAPI schema generation failure.
- Invalid Compose configuration.
- Migration syntax or dependency problems detectable statically.

Static validation does not replace behavioral tests.

### Frontend Unit, Component, And Integration Tests

Use the current frontend unit-test runner for pure frontend helpers, formatters,
API utilities, and other non-DOM browser-adjacent logic where appropriate.

When React component testing is adopted, use Vitest and React Testing Library
for behavior owned by the browser-facing React layer:

- Rendering and conditional content.
- Form interaction and client validation.
- Loading, empty, success, and error states.
- Dialog behavior.
- Disabled and pending states.
- Search, filtering, sorting, and local pagination behavior.
- Mapping API responses and errors to UI.
- Keyboard and focus behavior.
- Accessible roles, names, and labels.
- Navigation calls owned by the component.

Prefer user-visible queries and interactions. Avoid asserting component
instances, private state, hook internals, CSS class names, or implementation
structure unless those details are themselves contractual.

Reset or restore mocks between tests. Mock network behavior at the request
boundary rather than mocking the component logic being verified.

### FastAPI, Service, and Backend Tests

Use pytest for:

- Request validation.
- API contracts.
- Authentication and authorization.
- Ownership and visibility.
- Business rules.
- State transitions.
- Idempotency.
- Transactions.
- Persistence effects.
- Background jobs.
- Provider adapters and webhook handling.
- Backend security behavior.

Follow the backend testing standard for organization, fixtures, naming,
assertion depth, time control, side-effect checks, database isolation, and
completion reporting.

### PostgreSQL Integration Tests

Use pytest against an isolated real PostgreSQL database for:

- Constraints.
- Transactions and rollback.
- Locking and concurrency.
- PostgreSQL-specific types and behavior.
- Migration behavior.
- Referential actions.
- Constraint names and database error details.

Do not use SQLite to claim coverage of PostgreSQL-specific behavior.

### API Contract Tests

Use API integration tests and schema checks for:

- Request and response compatibility.
- Status codes.
- Nullability and enums.
- Date and identifier serialization.
- Pagination contracts.
- Absence of private fields.
- Frontend/backend agreement.

OpenAPI schema checks should supplement, not replace, runtime behavior tests.

### Mocked Browser Tests

Use Playwright with controlled API responses for browser behavior that needs a
real browser but not the real backend:

- Routing and navigation.
- Browser-only behavior.
- Complex focus and keyboard interaction.
- Responsive layout behavior.
- Frontend handling of unusual API response timing or failures.
- Critical rendering states that are difficult to prove in a simulated DOM.

These tests must be identifiable as mocked browser tests.

### Full-Stack Browser Tests

Use Playwright against the local React, FastAPI, and PostgreSQL stack for a
small, high-value set of critical workflows:

- Authentication into the application.
- Critical create, update, cancel, booking, participation, or admin flows.
- Persistence visible after refresh.
- Cross-layer authorization.
- Major error and recovery workflows.

Full-stack tests should not repeat every lower-level boundary combination.
Their purpose is to prove that the connected systems work together.

### Provider-Integration Tests

Use separate emulator, sandbox, or test-resource suites for:

- Firebase Auth Emulator integration.
- Stripe sandbox or test-mode requests and webhook fixtures.
- Cloudflare R2 test-bucket operations.
- Other approved external-provider contracts.

These tests must:

- Use isolated non-production credentials and resources.
- Be identifiable and separately runnable.
- Clean up created resources where practical.
- Avoid normal pull-request dependence on unstable public services unless the
  repository explicitly accepts that tradeoff.
- Never use live customer, payment, or production data.

### Infrastructure and Startup Tests

Use Docker Compose validation and smoke tests for:

- Service readiness.
- Health checks.
- Startup order.
- Migration application.
- Missing configuration failure.
- Dependency reconnection.
- Clean startup from an empty environment.

### Manual and Exploratory Verification

Use manual review for behavior that automated tests cannot reliably or
completely prove, including:

- Visual quality across unusual layouts.
- Screen-reader usability.
- Color contrast review when tooling is insufficient.
- Complex browser-specific behavior.
- Provider dashboard configuration.
- Disaster-recovery exercises.
- Large performance and load behavior.

Manual classification requires a concrete checklist and observed result. It
must not be used as a vague replacement for practical automation.

## Avoiding Duplicate Coverage

Do not copy every scenario into frontend, backend, PostgreSQL, and Playwright
suites.

Use this model:

- **Frontend test:** proves what the user sees and can do.
- **Backend test:** proves server policy and business behavior.
- **Database test:** proves the final persistence safeguard.
- **Contract test:** proves connected request and response agreement.
- **Playwright test:** proves the critical workflow across the connected app.
- **Provider test:** proves the application adapter works with the provider's
  testing surface.

Duplicate coverage is justified only when each layer protects a distinct risk.

Example: duplicate booking submission may require:

- Frontend test proving the submit button enters a pending state.
- Backend test proving repeated requests are idempotent.
- PostgreSQL test proving the uniqueness invariant.
- One Playwright test proving a real user action creates one visible booking.

## Mocking and Faking Rules

### Mock the Boundary, Not the Rule

Good:

- Mock Stripe's network client while exercising Pickup Lane payment logic.
- Mock Firebase token verification while exercising local authorization.
- Mock R2 network responses while exercising object cleanup and metadata logic.
- Mock an API response while exercising React error handling.

Bad:

- Mock the exact service function whose business rule is under test.
- Mock PostgreSQL so heavily that constraints and relationships are bypassed.
- Mock the frontend hook and then claim the component's request behavior works.
- Mock a successful payment result in a test intended to prove webhook
  idempotency.

### Restore State

All mocks, dependency overrides, fake timers, environment variables, handlers,
and global state must be restored after each test or fixture scope.

### Provider Contract Balance

Most tests should be fast and local. A smaller suite must verify the real
emulator, sandbox, or test-resource contract to catch adapter drift.

## Test Data Standards

Test data must be:

- Isolated.
- Deterministic.
- Valid by default.
- Explicitly overridden for invalid scenarios.
- Independent of test order.
- Free of real personal, payment, or production data.
- Easy to identify and clean up in external test systems.

Use factories for valid domain records and explicit overrides for the rule under
test. Do not hide critical scenario setup behind overly generic helpers.

For boundary tests, use values that clearly express the boundary:

```text
minimum - 1
minimum
minimum + 1
maximum - 1
maximum
maximum + 1
```

For time boundaries, use one frozen or injected clock baseline:

```text
before boundary
exactly at boundary
after boundary
```

## Time, Dates, and Expiration

Time-sensitive tests must:

- Use timezone-aware UTC internally.
- Derive local dates through the configured application timezone.
- Capture, freeze, or inject one clock baseline per scenario.
- Avoid `sleep()`.
- Test exact equality when equality changes behavior.
- Include daylight-saving behavior when a local-time rule crosses DST.
- Test expired records that cleanup has not processed yet.
- Test credentials, signed URLs, holds, invitations, and state transitions at
  their boundaries.

A cleanup job must not be the only safeguard preventing an already expired row
from acting as valid.

## Risk and Priority Classification

Assign each required scenario a priority:

### Critical

Failure could cause:

- Unauthorized access to private data.
- Account takeover or privilege escalation.
- Duplicate or incorrect charges or refunds.
- Irreversible data corruption.
- Loss of a core booking or payment invariant.
- Production credential or secret exposure.

### High

Failure could cause:

- Incorrect authorization with limited scope.
- Duplicate records or side effects.
- Capacity violations.
- Broken lifecycle state.
- Persistent user-visible inconsistency.
- Unrecoverable provider mismatch.

### Medium

Failure could cause:

- Recoverable workflow failure.
- Incorrect UI state.
- Poor error handling.
- Accessibility failure on an important action.
- Operational confusion without data loss.

### Low

Failure is cosmetic, narrow, recoverable, and does not affect privacy,
integrity, money, access, or core workflow completion.

Priority affects implementation order, not whether a finalized required rule
is valid.

## Page-Specific Scenario Inventory

For every materially changed page, maintain a reviewable scenario inventory in
the task plan, completion report, or a dedicated page testing document.

Use this format:

```md
### Scenario: Duplicate booking submission after client timeout

- Scenario ID: BOOKING-IDEMPOTENCY-01
- Priority: Critical
- Systems involved:
  - React form
  - FastAPI booking route
  - Booking service
  - PostgreSQL
  - Stripe
- Preconditions:
  - The request is valid.
  - The first response is lost after processing begins.
- Action:
  - The client retries the same logical booking.
- Risk:
  - Duplicate booking, participant, payment, or ledger effects.
- Expected behavior:
  - The logical operation completes at most once.
  - The retry returns the existing result or a defined in-progress result.
- Required safeguards:
  - Stable application idempotency key.
  - Transactional local writes.
  - Database uniqueness protection.
  - Stripe idempotency key.
  - Idempotent webhook processing.
- Existing coverage:
  - Frontend: partial
  - Backend: missing
  - PostgreSQL: covered elsewhere
  - Playwright: not required for this boundary
  - Stripe integration: partial
- Required work:
  - Add backend integration test.
  - Add duplicate webhook test.
  - Verify the owning uniqueness constraint.
- Owning documents:
  - Booking feature specification
  - Backend testing standard
  - Payment domain rules
- Status: missing
```

Do not use a loose list of test names without risks, safeguards, ownership, and
expected results.

## Requirement and Scenario Coverage Map

For every reviewed feature, record:

- Requirement or scenario label.
- Source of truth.
- Expected behavior.
- Risk and priority.
- Required safeguard.
- Owning layer.
- Existing test file and test name.
- Coverage status.
- Reason for exclusions or manual classification.
- Remaining implementation gap.

Allowed statuses:

- `covered`
- `partial`
- `missing`
- `covered_elsewhere`
- `manual`
- `not_applicable`
- `blocked`

A passing test without traceability to a requirement, invariant, or risk does
not prove complete coverage.

## CI and Suite Classification

Tests must be clearly classifiable by purpose and execution environment.
Pull-request requirements apply only to currently adopted test layers that are
applicable to the changed behavior. A PR requirement does not require
introducing an unconfigured test framework merely to satisfy a category.

Recommended suite classes:

### Pull-Request Required

- Static validation.
- Current frontend unit tests for frontend helpers, API utilities, and other
  non-DOM behavior they own.
- React component tests only after a React component-test layer is explicitly
  adopted.
- Backend unit and integration tests.
- PostgreSQL tests required by changed behavior.
- API contract tests.
- Current Playwright browser tests according to their actual suite role, and
  selected reliable full-stack browser tests when applicable.
- Migration validation when database behavior changes.

### Separate Provider Integration

- Firebase Auth Emulator.
- Stripe sandbox and webhook integration.
- Cloudflare R2 test bucket.

These may run on pull requests, merge, schedule, or manual dispatch according to
stability and cost, but they must remain visible and must not be confused with
mocked coverage.

### Scheduled or Manual Hardening

- Large load tests.
- Destructive recovery tests.
- Broad security scans.
- Multi-browser compatibility sweeps beyond the required PR set.
- Disaster-recovery and reconciliation exercises.

The normal suite must never silently exclude tests required for merge
protection.

## Docker Test Environment Standards

The Docker test environment must:

- Start from a clean, reproducible configuration.
- Use a dedicated PostgreSQL test database.
- Use test-only Firebase, Stripe, and R2 configuration.
- Apply or validate migrations before application tests.
- Define meaningful service health checks.
- Wait for dependencies to become healthy, not merely started.
- Use separate development, testing, and production environment files or
  equivalent configuration.
- Avoid production credentials in images, Compose files, build arguments, or
  logs.
- Avoid unnecessary privileged mode, host mounts, and added capabilities.
- Use deterministic seed and cleanup behavior.
- Remove test volumes, networks, and orphaned containers when isolation
  requires it.
- Support CI without relying on a developer's existing containers.
- Fail clearly when required configuration or dependencies are unavailable.

Tests should also verify a clean startup path, not only a stack that has already
been running for days.

## Regression Testing

Every confirmed production or pre-production defect must receive a regression
test that would fail if the defect returned, unless an explicit written
exception is accepted.

The regression test must target the root rule or missing safeguard, not only the
surface symptom.

When a defect reveals a recurring scenario category that this document omitted,
update this standard instead of leaving the lesson in one feature folder.

## Refactoring Rules

Refactoring a page must not silently reduce coverage.

The agent must determine:

- Which existing tests protect valid behavior and remain.
- Which tests assert implementation details and should be rewritten.
- Which tests pass for the wrong reason.
- Which tests duplicate the same risk.
- Which tests belong to a shared domain rather than the page.
- Which new states or error paths the refactor introduced.
- Which API or accessibility contracts changed.
- Whether changed batching, caching, pagination, or async behavior creates new
  race or stale-state risks.

Do not delete a failing test merely because the refactor changed implementation.
First determine whether the protected behavior is still required.

## Stop Conditions

Stop and report instead of guessing when:

- The finalized behavior is missing or contradictory.
- The page and backend disagree on a status, enum, or contract.
- Ownership is unclear between page and shared domain.
- A payment or provider outcome has no defined source of truth.
- A concurrency rule has no defined safeguard.
- A security-sensitive route has ambiguous 401, 403, or 404 policy.
- Exact time behavior cannot be tested deterministically with available seams.
- A database constraint is relied upon but cannot be identified.
- A provider test would require production credentials or production data.
- A test would require weakening a valid rule or assertion.

## Anti-Patterns

Do not:

- Ask Codex to “add edge cases” without a scenario matrix.
- Test only the happy path.
- Treat frontend validation as backend protection.
- Treat route hiding as authorization.
- Use only mocked tests for a critical full-stack contract.
- Use only full-stack tests for rules that belong at lower layers.
- Test every scenario at every layer.
- Derive expected behavior solely from current code.
- Preserve a test merely because it already passes.
- Assert only status codes for mutations.
- Ignore prohibited side effects after rejection or failure.
- Accept a generic database error without identifying the intended constraint.
- Use SQLite to claim PostgreSQL behavior.
- Use production Firebase, Stripe, R2, database, or user data.
- Use real card details in Stripe tests.
- Assume provider events arrive once or in order.
- Assume a timed-out request failed.
- Assume container startup means service readiness.
- Use arbitrary sleeps for UI, expiration, jobs, or provider behavior.
- Hide flaky tests with permanent reruns.
- Use coverage percentage as the definition of correctness.
- Add broad snapshots that obscure the behavior being protected.
- Mock the business rule under test.
- Leave external test resources without an ownership or cleanup strategy.
- Claim all possible scenarios were found.
- Claim completion without listing remaining gaps and verification not run.

## Required Agent Completion Report

After the application-wide testing review, report every section below.

### Sources Reviewed

- Feature specification.
- Owning-domain specifications.
- This application testing standard.
- Relevant layer-specific testing standards.
- Frontend, API client, backend, database, provider, worker, and infrastructure
  code inspected.
- Existing related tests inspected.

### Systems and Boundaries

- Systems involved.
- Source of truth for each important status or result.
- External boundaries.
- Transactions and asynchronous boundaries.

### Invariants

- Rules that must always remain true.
- Rules that must never occur.

### Scenario Coverage

- Required scenarios.
- Covered scenarios.
- Partial scenarios.
- Missing scenarios.
- Covered-elsewhere references.
- Manual scenarios and checklist.
- Not-applicable scenarios with reasons.

### Safeguards

- Existing safeguards verified.
- Missing safeguards.
- Safeguards that rely only on frontend behavior and require server protection.

### Test-Layer Decisions

- Frontend tests added or changed.
- Backend tests added or changed.
- PostgreSQL tests added or changed.
- API contract tests added or changed.
- Playwright tests added or changed.
- Provider integration tests added or changed.
- Infrastructure or startup tests added or changed.
- Manual checks required.
- Reason each test belongs at its selected layer.

### Security Review

- Authentication scenarios.
- Authorization and object-level access scenarios.
- Sensitive data and property exposure.
- Input and abuse cases.
- Resource limits.
- Provider trust boundaries.

### Failure and Recovery Review

- Duplicate and retry behavior.
- Concurrency behavior.
- Timeout and uncertain outcomes.
- Partial success.
- Reconciliation and cleanup.
- Audit and operational visibility.

### Verification

- Commands run.
- Commands not run.
- Test suites run.
- Results observed.
- Provider or manual verification still required.

### Remaining Gaps

- Untested behavior.
- Missing safeguards.
- Known limitations.
- Specification conflicts.
- Blocked decisions.

A generic statement such as “tests were added” or “coverage looks good” is not
an acceptable completion report.

## Research Basis

This standard was informed by the following official and primary sources. The
repository's finalized product and architecture rules remain the source of truth
for Pickup Lane behavior.

### Frontend and Browser Testing

- Testing Library, **Guiding Principles**:
  https://testing-library.com/docs/guiding-principles/
- Testing Library, **About Queries**:
  https://testing-library.com/docs/queries/about/
- React, **act** testing helper:
  https://react.dev/reference/react/act
- Node.js, **Test runner**:
  https://nodejs.org/api/test.html
- Vitest, **Mocking**:
  https://vitest.dev/guide/mocking
- Vitest, **Browser Mode**:
  https://vitest.dev/guide/browser/
- Playwright, **Best Practices**:
  https://playwright.dev/docs/best-practices
- Playwright, **Auto-waiting**:
  https://playwright.dev/docs/actionability
- Vite, **Environment Variables and Modes**:
  https://vite.dev/guide/env-and-mode.html

### Backend and Contract Testing

- FastAPI, **Testing**:
  https://fastapi.tiangolo.com/tutorial/testing/
- pytest, **About Fixtures**:
  https://docs.pytest.org/en/latest/explanation/fixtures.html
- pytest, **Parametrization**:
  https://docs.pytest.org/en/stable/how-to/parametrize.html
- OpenAPI Initiative, **OpenAPI Specification**:
  https://spec.openapis.org/oas/

### PostgreSQL

- PostgreSQL, **Constraints**:
  https://www.postgresql.org/docs/current/ddl-constraints.html
- PostgreSQL, **Transaction Isolation**:
  https://www.postgresql.org/docs/current/transaction-iso.html
- PostgreSQL, **SET CONSTRAINTS**:
  https://www.postgresql.org/docs/current/sql-set-constraints.html

### Firebase Authentication

- Firebase, **Local Emulator Suite**:
  https://firebase.google.com/docs/emulator-suite
- Firebase, **Connect to the Authentication Emulator**:
  https://firebase.google.com/docs/emulator-suite/connect_auth

### Stripe

- Stripe, **Test Your Integration**:
  https://docs.stripe.com/testing/overview
- Stripe, **Idempotent Requests**:
  https://docs.stripe.com/api/idempotent_requests
- Stripe, **Webhooks**:
  https://docs.stripe.com/webhooks
- Stripe, **Sandboxes**:
  https://docs.stripe.com/sandboxes

### Cloudflare R2

- Cloudflare, **R2 S3 API Compatibility**:
  https://developers.cloudflare.com/r2/api/s3/api/
- Cloudflare, **Presigned URLs**:
  https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- Cloudflare, **R2 Error Codes**:
  https://developers.cloudflare.com/r2/api/error-codes/

### Docker

- Docker, **Compose Quickstart and Health Checks**:
  https://docs.docker.com/compose/gettingstarted/
- Docker, **Control Startup and Shutdown Order**:
  https://docs.docker.com/compose/how-tos/startup-order/
- Docker, **Compose Trust Model**:
  https://docs.docker.com/compose/trust-model/
- Docker, **Environment Variable Best Practices**:
  https://docs.docker.com/compose/how-tos/environment-variables/best-practices/

### Security and Accessibility

- OWASP, **Web Security Testing Guide**:
  https://owasp.org/www-project-web-security-testing-guide/stable/
- OWASP, **Application Security Verification Standard**:
  https://owasp.org/www-project-application-security-verification-standard/
- OWASP, **API Security Top 10 2023**:
  https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- W3C, **Web Content Accessibility Guidelines 2.2**:
  https://www.w3.org/TR/WCAG22/
- W3C, **Evaluating Web Accessibility**:
  https://www.w3.org/WAI/test-evaluate/
