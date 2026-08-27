# Backend Testing

This document is the execution standard for backend and API testing in Pickup
Lane. It is required reading before creating, moving, reviewing, or reorganizing
backend tests.

For compliance checker setup and usage, see `backend/tests/README.md`.
Checker `PASS` is structural/machine compliance only, not semantic adequacy.

Use this together with:

- `backend-structure.md` for backend ownership and dependency direction.
- `database.md` for migrations, test database safety, and reset commands.
- The relevant finalized feature document.
- Any owning domain document that defines shared behavior used by the feature.

When these sources conflict, do not guess. Report the conflict and stop before
encoding an uncertain expectation into a test.

## Normative Language

The words **must**, **must not**, and **required** define hard gates. Work is not
complete when a hard gate is unmet.

The words **should** and **prefer** describe strong defaults. Departures require
a clear reason in the completion report.

## Purpose

Backend tests prove finalized behavior. They verify API contracts,
authorization, business rules, database effects, state transitions, expiration,
capacity, payments, failure behavior, security boundaries, and regressions.

The goal is not to maximize test count or coverage percentage. The goal is a
suite that would fail for the correct reason if protected behavior regressed.

## Source Of Truth For Expected Behavior

Tests must be derived from finalized product and domain rules, not from whatever
the current implementation happens to do.

Source priority:

1. Finalized feature specification.
2. Finalized owning-domain specification.
3. Shared platform rules and architecture documents.
4. Current database constraints and public API contracts when they do not
   conflict with a finalized specification.
5. Current trusted tests and implementation only as evidence of current
   behavior, not proof that the behavior is correct.

An agent must not preserve or add an expectation merely because the current code
returns it. When code and specification disagree, report the mismatch. Do not
change the test expectation to match the code without confirming the intended
behavior.

For production-readiness work, `backend/tests/legacy/` is treated as
nonexistent. Do not read, search, list, execute, cite, derive from, use as
provenance, use as requirements, use as scenarios, use as assertions, use as
implementation guidance, or use as evidence for production-readiness work.

## Non-Negotiable Completion Gates

Backend test work must not be marked complete until the applicable items in
`Feature Review Checklist` are satisfied. If a required item cannot be satisfied,
report the work as incomplete or blocked. Do not say the test work is done.

## Required Pre-Work Review

Before writing or reorganizing tests, the agent must identify and read:

- The relevant feature document.
- The owning domain document for each shared rule involved.
- Relevant models, enums, database constraints, service functions, and routes.
- Current trusted tests for the same behavior, if any.
- Current shared fixtures, support utilities, requirement declarations, suite
  policy, and checker behavior relevant to the scope.

The agent must then state or internally establish:

- What behavior is being protected.
- Which source defines that behavior.
- Which layer owns the behavior.
- Which API paths consume it.
- Which state, role, status, and boundary combinations are relevant.
- Which relationship or privilege grants access, and which stale or invalid
  versions must not grant access.
- Which current trusted tests already cover part of the requirement, if any.

Do not begin by copying current tests into a new folder. First determine what the
correct test set should be.

## Requirement-To-Test Traceability

Production-readiness traceability follows this permanent ownership model:

```text
PRODUCTION-READINESS PASS
  -> STABLE REQUIREMENT ID
    -> MEANINGFUL SCENARIOS / EDGE CASES
      -> PYTEST TESTS
```

The canonical pass planning document owns the pass-to-requirement list and the
meaning of each stable requirement. A small machine-readable declaration owns
only the minimum identity needed by tooling.

The concise human testing/risk record for a coherent owned test scope owns
requirement-to-scenario reasoning. It should describe invariants, meaningful
risks, edge cases, owning layer, gaps, blockers, deferrals, and adequacy
conclusions. It must not duplicate every Python test or exact pytest node ID.
Use `docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` when
creating or reconciling a `TESTING_RECORD.md`.

Pytest tests declare the stable requirement IDs they prove with the registered
`requirement` marker. One requirement may map to many tests, and one test may
legitimately prove multiple requirements.

Exact current pytest node IDs are generated from pytest collection and metadata.
They are not manually maintained in permanent planning documents or machine
registries.

Requirement declaration storage, marker mechanics, generated node IDs, and
checker behavior are owned by `backend/tests/README.md`.

`covered_elsewhere`, `not_applicable`, `blocked`, and `deferred` decisions
require a reason. A test expectation without a traceable specification or
established domain policy must be treated as unresolved, not silently invented.

## Enum, Status, Role, And Lifecycle Matrix

When behavior depends on an enum, status field, role, account state, payment
state, participant state, booking state, visibility state, relationship state,
privilege state, or lifecycle state, the agent must build an explicit matrix
before claiming coverage is complete.

The matrix must:

- List every authoritative value currently allowed by the model, enum, or
  database constraint.
- Be checked against the authoritative model, enum, service constant, schema, or
  database constraint. Do not build it from memory or nearby tests.
- State the expected behavior for each relevant value.
- Classify each value as `covered`, `excluded_by_policy`, `not_relevant`, or
  `missing_test`.
- Make classifications a complete, mutually exclusive partition of the
  authoritative values. Every value must belong to exactly one classification
  unless the test is explicitly a combination matrix.
- When a matrix is encoded as classification sets in test code, assert that the
  sets are pairwise disjoint and that their union equals the authoritative
  allowed-value set.
- Identify the source that defines the classification.
- Include combinations when behavior depends on more than one field.
- Include invalid privilege states, such as inactive, suspended, deleted, or
  revoked actors, when an active privileged actor is allowed.
- Include stale relationship states, such as expired, cancelled, removed,
  historical, or no-longer-active rows, when an active relationship is allowed.

Example:

```text
Value                 Expected behavior                Coverage
active                permits the action                covered
pending_review        denies the action                 missing_test
suspended             denies the action                 covered
deleted               denies the action                 covered
```

Do not assume values with similar names behave the same way. Do not omit a value
because current code never produces it in the reviewed path.

Parametrization is encouraged when several values use the same setup, action,
and expected rule. Do not force values with different behavior into one
parametrized test.

## Test Ownership Gate

Before placing a test, identify the layer and owned scope that protect the
behavior.

Ownership rules:

- `domains/` owns stable business and domain invariants.
- `workflows/` owns genuine cross-domain orchestration or user-flow behavior
  whose integration is itself the contract.
- `platform/` owns intentionally global backend, API, framework, and security
  behavior.
- `migrations/` owns Alembic and schema-history testing.
- `provider_contract/` owns explicitly separated real provider, emulator,
  sandbox, or test-resource verification.
- `support/` owns reusable testing infrastructure only.
- `checker/` owns checker, compliance, and environment-safety self-tests.
- A page or route may have integration coverage proving that it consumes a
  domain rule correctly, but page-level coverage must not absorb domain-level
  invariants.
- A database-constraint test belongs with the constrained model or domain, not
  whichever endpoint first exposed the issue.
- File ownership follows the behavior under test, not only the endpoint that
  exposed it.

Before completion, the agent must be able to explain why each new or moved test
belongs in its selected file.

Avoid vague catch-all folders. Add a support helper only when it has a real,
reusable responsibility.

## Test Organization

Backend tests live under `backend/tests/`.

The trusted backend test tree, reserved roots, checker folders, suite policy,
requirement declaration storage, generated-node mechanics, and archive mechanics
are owned by `backend/tests/README.md`.

Organize tests by behavior ownership, not by whichever endpoint first exposed a
bug. Create trusted roots only when reviewed, current coverage exists for that
ownership area. Do not add placeholder domain, workflow, platform, migration,
provider, or checker folders for future work.

Existing backend application tests are not trusted production-readiness evidence
until future work derives them from authoritative requirements under the final
testing system. Historical and out-of-scope tests are not inputs to current test
design.

### Placement Rules

- Domain-specific fixtures belong in that domain or workflow `conftest.py`.
- Fixtures used across many backend areas belong in root `conftest.py`.
- Reusable current infrastructure belongs in `backend/tests/support/` only when
  it has a real cross-scope responsibility.
- New or refactored tests must follow the current trusted-root and support-file
  rules owned by `backend/tests/README.md`.

Do not create empty support modules. Add a support file only when it has a real,
reusable responsibility.

## Test File Design

Each test file must have one clear behavioral responsibility that matches its
name.

Good examples:

```text
test_visibility.py
test_capacity_rules.py
test_domain_constraints.py
test_external_webhooks.py
test_resource_access.py
```

Do not place unrelated policies in the same file merely because they use the
same endpoint or model.

Within a file:

- Group related tests together.
- Keep naming consistent.
- Put shared constants near the top only when they are genuinely stable and not
  pretending to represent current or future time.
- Prefer local setup when it makes the scenario easier to understand.
- Extract setup only after reuse is real and the helper name preserves clarity.
- Avoid creating a large file that becomes a second monolithic test suite.

Keep tests together when they exercise the same endpoint family, policy, and
type of outcome. A long file is acceptable when it is one cohesive behavior
matrix, such as a route authorization matrix or one status-state matrix.

File length alone is not a reason to split. Split a file when tests move to a
different endpoint family, change from read authorization to mutation behavior,
mix unrelated route/resource contracts, require a different persistence or
side-effect assertion shape, or become sections that would naturally be
maintained and reviewed separately.

## Individual Test Scope

A test must prove one primary behavior through one primary action, except for
explicitly allowed cohesive read-access tests and parametrized matrix tests.

Setup actions do not count as the primary action. A focused test may make
multiple read requests only when they jointly prove one atomic policy and do not
change state between scenarios.

Split a test when it mixes:

- Different expected rules.
- Different endpoints with independent contracts.
- Multiple authentication identities that have different policy reasons.
- A normal behavior and a later lifecycle transition.
- A successful mutation and an unrelated rejected mutation.
- Setup or authentication state that can leak between assertions.
- Failures that would not clearly reveal which rule broke.

A state change followed by a second request belongs in the same test only when
the lifecycle transition itself is the behavior under test.

Parametrized matrix tests are allowed when every parameter uses:

- The same setup shape.
- The same primary action.
- The same expected rule.
- The same assertion structure.

Do not use parametrization merely to reduce line count.

## Test Format And Naming

Most tests should follow:

```text
Arrange
Act
Assert
```

Arrange, Act, and Assert comments are optional when the structure is obvious.

Test names must state the scenario and expected result:

```python
test_private_resource_returns_404_for_anonymous_user
test_expired_hold_does_not_reserve_capacity
test_invalid_cursor_returns_400
test_duplicate_webhook_does_not_repeat_side_effect
```

Avoid vague names:

```python
test_game
test_error
test_endpoint_works
test_case_1
```

## Helpers, Fixtures, And Factories

### Root `conftest.py`

Use root `backend/tests/conftest.py` only for fixtures needed across many
features, such as:

- Test client.
- Application-wide dependency cleanup.
- Test database cleanup or rollback.
- Broadly shared database session fixtures, if introduced.

Tests request fixtures through function parameters. Do not import fixtures from
`conftest.py`.

### Feature `conftest.py`

Use a feature-level `conftest.py` only for setup specific to that feature and
reused by multiple tests in the feature folder.

Feature fixtures must earn their indirection. Keep important scenario setup in
the test when hiding it would make the test harder to understand.

Prefer function-scoped fixtures. Broader scopes are allowed only for immutable
objects or state that is safely reset.

Avoid `autouse=True` unless the behavior genuinely applies to every test in the
scope.

### Support Infrastructure

Current support modules must be reusable infrastructure, not a second hidden
test suite. Before adding a support module, confirm:

- more than one current trusted scope needs the helper, or one scope has a
  cohesive local support need that would be harder to read inline
- the helper name states the test responsibility clearly
- the helper does not encode expected product behavior without an authoritative
  source
- the helper does not hide the behavior, assertion, or side effect that makes
  the test meaningful

Current support responsibilities include:

- environment/database/network safety support
- artifact sanitization and browser-quality policy support

Future trusted tests may introduce new support modules, but the module must
match current ownership and be justified by reviewed coverage. Do not recreate
the archived pre-EN-01 helper stack merely because historical tests used it.

### Setup Helpers, Factories, And Shared Assertions

When future domain or workflow coverage needs setup helpers, factories, or
shared assertions, keep these rules:

- Setup helpers may assert setup succeeded only when the test cannot continue
  with invalid setup data.
- A helper must not assert the behavior under test.
- Pure factories must avoid HTTP requests, behavior assertions, unrelated side
  effects, and test-order dependencies.
- Shared assertions should be used only for repeated outcome checks that remain
  clear when named.
- Important one-off behavior should stay visible in the test.
- Security-sensitive response checks may use a shared assertion only when the
  policy applies to several current trusted scenarios.

## Assertion Depth Gate

Assertions must prove the protected behavior, not merely show that execution
completed.

### Read-Only API Tests

Assert the applicable contract details:

- Exact HTTP status code.
- Response body shape.
- Required fields and exact values.
- Enum or status values.
- Pagination metadata.
- Ordering and aggregate totals.
- Required headers.
- Absence of private or internal fields.

When authorization changes whether private data is returned, verify required
cache-control and privacy headers for every relevant authorized response class.

### Successful Mutations

Every successful mutation test must verify the important persisted result after
the request.

Depending on the behavior, verify:

- Row creation, update, deletion, or soft deletion.
- Exact state transition.
- Ownership fields.
- Related rows.
- Timestamps.
- Capacity or inventory changes.
- Audit or history records.
- Notifications or external-action records.

When practical, read persisted state through a fresh database session so the
assertion does not rely on stale in-memory objects.

A success status code alone is insufficient for a mutation.

### Rejected Mutations

Every rejected mutation test must verify relevant prohibited side effects when
the route could otherwise change data.

Before choosing assertions, identify the route's possible side effects:

- Every table the route could create, update, delete, soft-delete, or restore.
- Related capacity or inventory counters.
- Payment intents, refunds, credits, ledger rows, or provider actions.
- Waitlist, booking, participant, roster, invitation, or membership rows.
- Audit, history, notification, email, chat, or background-action records.
- Cache, task, or external-service effects when they are part of the contract.

Depending on the behavior, prove that:

- No booking was created.
- No participant was added.
- No waitlist, invitation, or related membership row was created.
- No payment was confirmed.
- No notification was created or sent.
- No audit entry was created when policy forbids one.
- Existing records and counts remain unchanged.
- Capacity was not consumed.

A rejection status code alone is insufficient when unintended writes are a
meaningful risk. A vague "check the database" is also insufficient; the test or
review notes must name the affected tables and side effects that matter for the
route.

### Idempotency

Idempotency tests must verify both response behavior and persisted effects:

- Repeating a request does not duplicate rows.
- Replaying a webhook does not repeat confirmation.
- Replaying a refund path does not issue another refund.
- Counters and state remain consistent.

### Database Constraint Tests

A database-constraint test must prove that the intended constraint caused the
failure.

Do not accept any generic `IntegrityError` as sufficient. Inspect the available
constraint name, database error code, or stable error detail and assert the
specific cause whenever the database driver exposes it.

Also confirm that the failed transaction did not persist the invalid row.

If the test database or driver cannot expose a stable constraint identifier,
document the limitation and assert the narrowest reliable failure detail plus
post-rollback database state.

## Scenario Review Matrix

Every feature review must classify each relevant scenario item below, not only
each broad category, as `required`, `not_relevant`, or `covered_elsewhere`. An
item marked `required` must map to specific tests. Items marked `not_relevant`
or `covered_elsewhere` require a reason.

### Normal Behavior

- Valid request succeeds.
- Response matches the final API contract.
- Expected database state is produced.

### Validation

- Missing required fields.
- Invalid types.
- Invalid enum values.
- Invalid date or timestamp formats.
- Values below or above allowed limits.
- Conflicting fields.
- Malformed cursor or token.

### Authentication

- Anonymous request where authentication is required.
- Valid authenticated request.
- Invalid or malformed credentials.
- Expired credentials when relevant.

### Authorization And Visibility

- Owner or host access.
- Participant or relationship-based access.
- Stale, expired, cancelled, removed, or no-longer-active relationship denial.
- Unrelated-user denial.
- Admin or privileged-role access.
- Invalid privileged actor denial, including inactive, suspended, deleted, or
  revoked actors when those states exist.
- Horizontal authorization using another user's resource ID.
- Vertical authorization using a lower-privilege user.
- Hidden or private resource behavior.
- Hidden or private resource enumeration through detail, list, lookup, and
  helper routes that accept resource identifiers.
- Correct `401`, `403`, or `404` response according to policy.
- Required privacy and cache headers.

### State And Lifecycle

- Allowed state transitions.
- Prohibited state transitions.
- Repeated transition attempts.
- Terminal-state behavior.
- Historical rows not granting active privileges.

### Dates, Times, And Expiration

- Before the boundary.
- At the exact boundary.
- After the boundary.
- UTC handling.
- Configured timezone behavior.
- Daylight-saving transitions when relevant.
- Expired records that cleanup has not processed yet.

### Capacity And Concurrency

- Empty capacity.
- One remaining spot.
- Exactly full.
- Over-capacity defensive behavior.
- Expired temporary holds.
- Multiple participant rows under one booking.
- Competing requests for the final spot.
- Required transaction and row-lock behavior.

### Pagination, Sorting, And Counts

- First page.
- Middle page.
- Final page.
- Exact-limit page.
- Empty page.
- Stable ordering when primary sort values match.
- Cursor mismatch.
- Invalid cursor.
- No duplicates across pages.
- Aggregate totals, grouped counts, summaries, and available-count fields use
  the same authorization, visibility, lifecycle, cutoff, and status filters as
  the item query.

### External Services And Webhooks

- Successful provider response.
- Provider failure.
- Timeout or exception.
- Duplicate webhook.
- Out-of-order webhook.
- Late webhook.
- Invalid webhook signature.
- Idempotent retry behavior.

### Regression Tests

Every confirmed production or pre-production bug must receive a regression test
that would fail if the bug returned, unless the user explicitly accepts a
written exception.

## Controlled Time Gate

Time-based tests must not depend on uncontrolled wall-clock timing.

Required rules:

- Capture, freeze, or inject one `now_utc` baseline per scenario.
- Derive all relative timestamps from that baseline.
- Do not scatter `datetime.now()` calls through one scenario.
- Do not mix a live current timestamp and an unrelated fixed calendar timestamp
  in one active/expired scenario.
- Do not use a fixed calendar timestamp to represent an active or expired state
  unless the application clock is frozen or injected to the same baseline.
- Fixed historical timestamps are allowed only when their relationship to the
  current clock is irrelevant.
- Test exact equality explicitly when equality has special meaning.
- Use a frozen or injected application clock for exact API boundary tests.
- When an API route cannot safely control the clock, test the exact boundary at
  the owning service layer and use generous offsets for ordinary API tests.
- Use timestamps with enough margin for non-boundary API tests.
- Do not use `sleep()` to wait for expiration.
- Do not create holds so short that normal execution can cross the boundary.
- Store and compare timezone-aware UTC timestamps.
- Derive local dates through the configured application timezone, not the
  developer machine timezone.

When policy says `expires_at > now_utc` is valid, cover:

```text
expires_at > now_utc    valid
expires_at == now_utc   expired
expires_at < now_utc    expired
```

Before completion, the agent must state how time was controlled in every exact
boundary test.

## FastAPI Rules

- Use `TestClient` for synchronous API tests.
- Use `httpx.AsyncClient` only when a test must directly await async application
  or database behavior.
- Override external or expensive FastAPI dependencies through
  `app.dependency_overrides`.
- Always reset dependency overrides after the test or fixture completes.
- Do not call real paid, destructive, or unstable external services in the
  standard suite.
- Test lifespan-dependent behavior with a client setup that triggers startup and
  shutdown.

## Mocking And External Dependencies

Mock the boundary, not the business rule under test.

Good examples:

- Mock Stripe's network response while exercising the application's webhook or
  service logic.
- Mock an external authentication provider while exercising local authorization
  behavior.
- Mock email delivery while verifying that the application requested the correct
  message.

Bad examples:

- Mock the service function whose logic the test is supposed to verify.
- Mock database state so heavily that real constraints and relationships are
  bypassed.
- Return a hard-coded success from the exact function under test.

Use FastAPI dependency overrides or pytest's `monkeypatch` fixture where
appropriate. Ensure patches are restored after the test.

## Database Isolation

Tests must use a dedicated test database or isolated test schema.

Required rules:

- Never point tests at development, staging, or production data.
- Reset database state between tests through rollback, truncation, or another
  deterministic isolation strategy.
- Tests must not depend on rows created by previous tests.
- Migrations used by the application must also be valid for the test
  environment.
- Test important database constraints directly in the owning domain.
- A test that changes data must verify persisted state after the operation.
- A rejected transaction must be rolled back before the session is reused.

## Determinism

Tests must produce the same result regardless of order or repetition.

Do not rely on:

- Existing local data.
- Network availability.
- Real current time for boundary logic.
- Random values without controlled uniqueness or a captured failing example.
- Test execution order.
- Shared mutable global state.
- Uncontrolled background work.
- Arbitrary sleeps.

A flaky test must be fixed at the root cause. Automatic reruns may help diagnosis
but must not hide nondeterminism.

Use `xfail` only for a documented, temporary, known issue. Prefer strict
behavior so an unexpected pass is visible.

## Assertions And Errors

Use direct, specific assertions.

Good:

```python
assert response.status_code == 404, response.text
assert body["availability"]["status"] == "full"
assert booking.booking_status == "expired"
```

Weak:

```python
assert response.status_code < 500
assert response.json()
assert booking is not None
```

Do not wrap ordinary tests in broad `try/except` blocks. Pytest should show the
original exception and traceback.

Use `pytest.raises` only when the expected behavior is an exception. Narrow the
exception assertion to the intended cause.

Test logging only when logging itself is a requirement.

## Reviewing Existing Tests

When reviewing an existing feature test suite, review the suite as a whole. Do
not patch one failing or weak test at a time without checking the complete
policy set.

The review must determine:

- Which tests are correct and stay.
- Which tests duplicate the same behavior without adding protection.
- Which tests must be split.
- Which tests belong in another domain folder.
- Which behavior categories are recurring gaps and should strengthen this
  standard rather than becoming one-off feature notes.
- Which tests need stronger response assertions.
- Which mutation tests need persisted-state assertions.
- Which rejection tests need prohibited-side-effect assertions.
- Which time-sensitive tests need a captured, frozen, or injected clock.
- Which enum, status, role, or lifecycle values are missing.
- Which allowed relationship or privileged-access cases lack stale, revoked, or
  invalid counterparts.
- Which aggregate, grouped-count, or summary assertions fail to prove filter
  parity with the item query.
- Which expectations conflict with the finalized specification.
- Which tests could pass for the wrong reason.

Do not preserve a broad test merely because it already passes. Do not move a
domain test into a page folder merely because the page consumes the result.

## Automated CI Requirements

Pickup Lane currently uses GitHub Actions, but these requirements apply to any
automated workflow provider used for backend validation.

Automation must:

- Run the required backend test suite before merge or release.
- Use an isolated test database.
- Apply or validate migrations when the production path depends on migrations.
- Never use production credentials, production data, or production
  infrastructure.
- Produce readable failure output.
- Fail when required tests fail.
- Avoid stop-after-first-failure behavior in normal CI so the full failure set
  is visible.
- Use least-privilege workflow permissions.

Live external-provider tests, destructive tests, and large performance tests
belong in separate manual or scheduled workflows rather than the normal pull
request gate.

## Local Agent Execution Policy

Automated CI runs the required backend suite.

Agents may inspect code, review tests, edit files, and perform static checks.
Agents must not run backend API tests, migrations, database-reset commands, or
application processes unless the user explicitly instructs them to do so.
An explicitly started production-readiness gate is such an instruction only for
the validation required by its approved workflow, frozen plan, or current gate
instruction; it does not authorize unrelated backend tests, migrations, database
reset commands, or broader suites.

When verification is needed, agents must provide focused commands for the user
to run and clearly state what remains unverified.

Allowed without explicit backend-test approval:

- Reading files.
- Structural searches.
- Static checks that do not mutate application or database state.
- `git diff --check`.

Not allowed without explicit approval:

- `pytest backend/tests...`
- Alembic upgrade or downgrade commands.
- Database create, drop, reset, or truncate commands.
- Starting backend application processes.
- Commands that call paid or external services.

## Required Agent Completion Report

Before saying backend test work is complete, the agent must provide a concise
report that communicates:

- Sources reviewed, including feature/domain specifications and material source
  areas inspected.
- Requirement coverage, including fully covered, partially covered, missing,
  covered-elsewhere, blocked, or deferred behavior.
- Matrix and ownership decisions, including authoritative enum/status/role/
  relationship classifications and why each test belongs in its selected file.
- Evidence quality, including response assertions, persisted effects for
  successful mutations, prohibited side effects for rejected mutations,
  constraint proof, security-sensitive data exposure, and time control.
- Remaining gaps, unresolved specification conflicts, commands run, commands not
  run, observed results, and any verification still required from the user or
  CI.

This report is not a substitute for satisfying the `Feature Review Checklist`.

An agent must not replace this report with a generic statement such as “tests
were added” or “coverage was improved.”

## Stop Conditions

Stop and report instead of guessing when:

- The finalized specification is missing or contradictory.
- A required status or role has no defined behavior.
- Code and specification conflict.
- Test ownership is unclear between page and domain layers.
- Exact time behavior cannot be tested deterministically with available seams.
- The intended database constraint cannot be identified reliably.
- A requested test would require weakening product behavior or existing valid
  assertions.

## Security Tests

Important APIs must include authorization and data-exposure tests.

At minimum, classify:

- Unauthenticated access.
- Horizontal access using another user's resource ID.
- Vertical privilege escalation.
- Hidden or private resource enumeration.
- Unauthorized field updates.
- Excessive response data.
- Invalid methods.
- Invalid or unexpected input.
- Error responses that expose internal details.
- Resource-limit validation such as maximum page size.
- Webhook signature validation.
- Required privacy and cache headers.

Security tests must prove authorization at the object and action level.
Authentication alone is not sufficient.

When hidden or private resources exist, test every route shape that can reveal
the resource by identifier, including detail routes, list routes with filters,
lookup helpers, mutation routes, and aggregate routes. If policy requires
non-enumeration, unauthorized responses must not reveal whether the hidden
resource exists through status codes, body shape, counts, cache headers, or
timing-sensitive side effects.

## Anti-Patterns

Do not:

- Derive expected behavior solely from current code.
- Change production code only for tests.
- Weaken an assertion to make a failure disappear.
- Assert only that the API did not return `500`.
- Assert only a mutation status code.
- Accept any `IntegrityError` without tying it to the intended constraint.
- Catch and suppress unexpected exceptions.
- Reuse production databases or credentials.
- Depend on test order.
- Put every fixture in one giant root `conftest.py`.
- Put every helper in one dumping-ground module.
- Put domain constraints in a page test folder.
- Duplicate the same business-rule setup across many files without reviewing
  whether a fixture or factory is justified.
- Use scattered `datetime.now()` calls in one scenario.
- Use fixed dates as fake future or active timestamps without a controlled
  application clock.
- Use real time for exact boundary tests.
- Use real external services in the standard suite.
- Treat coverage percentage as the definition of correctness.
- Add permanent reruns to hide flaky tests.
- Leave undocumented skips or non-strict `xfail` markers indefinitely.
- Test only the success path.
- Claim completion without listing remaining gaps and commands not run.

## CI Hardening Targets

These are good targets, but not mandatory until repository and automation
configuration enforce them:

- Branch coverage reports.
- Coverage thresholds or coverage-diff enforcement.
- JUnit XML test reports.
- Test sharding.
- Dedicated slow or manual external-provider workflows.
- Scheduled large performance tests.

Do not describe hardening targets as required until they are actually enforced.

## Markers

Use a small registered marker set only when it supports real workflow needs.

Current registered markers:

```text
migration_lifecycle
no_db_cleanup
requirement
suite_type
```

Rules:

- Register every custom marker in pytest configuration.
- Keep strict marker validation enabled.
- Do not use markers as a replacement for clear folder and file organization.
- Tests required for merge protection must not be silently excluded by marker
  defaults.

## Feature Review Checklist

This is the canonical backend-testing completion checklist. Before a feature is
considered fully tested, confirm the applicable items below:

### Source And Ownership

- [ ] The finalized feature specification was reviewed.
- [ ] Relevant owning-domain specifications were reviewed.
- [ ] Every test expectation is traceable to a specification or established
      domain policy.
- [ ] Each test is placed with the correct page, feature, or owning domain.
- [ ] Page tests do not absorb unrelated domain invariants or constraints.

### Coverage Matrix

- [ ] Every relevant finalized requirement maps to at least one test.
- [ ] Relevant enum, status, role, privilege, relationship, and lifecycle values
      were listed from authoritative sources.
- [ ] Every listed value is covered, excluded by policy, or marked not relevant.
- [ ] Positive privileged-access cases have invalid-privilege counterparts, or
      an exact `covered_elsewhere` reference.
- [ ] Positive relationship-based access cases have stale, expired, cancelled,
      removed, or no-longer-active counterparts when those states exist.
- [ ] Missing and unresolved combinations are reported.

### Test Design

- [ ] Each test has one primary behavior and primary action.
- [ ] Parametrized cases apply the same rule and assertion shape.
- [ ] Broad mixed tests were split where failures would be ambiguous.
- [ ] Duplicate tests add distinct protection or were removed.

### Assertions

- [ ] Response contracts are asserted directly.
- [ ] Successful mutations verify persisted database state.
- [ ] Rejected mutations identify affected tables and side effects, then verify
      every relevant prohibited side effect.
- [ ] Idempotency tests verify persisted effects.
- [ ] Constraint tests prove the intended constraint failed.
- [ ] Security-sensitive headers and data exposure are covered.
- [ ] Aggregates, grouped counts, summaries, and availability/count fields prove
      filter parity with the item query.

### Time And Determinism

- [ ] One captured, frozen, or injected clock baseline is used per scenario.
- [ ] Exact before, equal, and after boundaries are covered when required.
- [ ] No fixed date pretends to be active or future without a matching frozen
      clock.
- [ ] Tests do not depend on execution order, network access, or sleeps.

### Verification

- [ ] Regression tests exist for confirmed bugs.
- [ ] No test-specific production logic was added.
- [ ] Feature tests are included in the normal automated backend suite.
- [ ] Remaining gaps are listed.
- [ ] Commands run and commands not run are stated.
