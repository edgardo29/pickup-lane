# Playwright Test Structure and Standards

## 1. Purpose

This document defines the general standards for creating, organizing, reviewing, and maintaining Playwright tests.

These rules apply whenever Playwright test code, fixtures, helpers, page objects, configuration, test data, or continuous integration settings are created or modified.

The goals are to keep the test suite:

- Reliable
- Deterministic
- Independent
- Readable
- Maintainable
- Fast enough to run regularly
- Capable of scaling to parallel execution when the environment supports it
- Useful when failures occur

This is a general testing standard. Product-specific workflows, business rules, user roles, and test scenarios belong in separate project documentation.

---

## 2. Rule Language

The following terms are intentional:

- **MUST**: Required. Code that violates the rule should not be accepted without a documented exception.
- **MUST NOT**: Prohibited.
- **SHOULD**: The preferred approach. A different approach requires a clear reason.
- **SHOULD NOT**: Usually incorrect or risky. Use only when justified.
- **MAY**: Optional and dependent on the test's needs.

When generated code conflicts with this document, this document takes precedence unless a more specific repository-level instruction explicitly overrides it.

---

## 3. Testing Philosophy

### 3.1 Test observable behavior

Tests MUST verify behavior that a user or external consumer can observe.

Good targets include:

- Visible text
- Enabled or disabled controls
- Navigation results
- Form validation
- Created, updated, or removed records
- Accessible state
- API responses
- Persisted server state
- User-visible error and success states

Tests MUST NOT depend on internal implementation details that users cannot observe, including:

- React component names
- Internal state variables
- Private functions
- CSS framework classes
- Exact DOM nesting
- Internal array structures
- Temporary implementation-specific attributes

```js
// Good: verifies an observable result.
await page.getByRole('button', { name: 'Submit' }).click();
await expect(page.getByRole('status')).toHaveText('Saved successfully');

// Bad: depends on implementation details.
await expect(page.locator('.form-container > div:nth-child(3)')).toHaveClass(/success/);
```

### 3.2 Test outcomes, not activity

A test is not complete because it clicked buttons or filled fields. Every test MUST contain meaningful assertions that prove the expected outcome occurred.

```js
// Incomplete: performs actions without proving the result.
await page.getByLabel('Name').fill('Example Name');
await page.getByRole('button', { name: 'Save' }).click();

// Complete: proves the result.
await page.getByLabel('Name').fill('Example Name');
await page.getByRole('button', { name: 'Save' }).click();
await expect(page.getByRole('status')).toHaveText('Saved successfully');
await expect(page.getByLabel('Name')).toHaveValue('Example Name');
```

### 3.3 Use the correct test layer

Playwright SHOULD be used for behavior that benefits from a real browser, such as:

- Critical end-to-end workflows
- Browser navigation
- Authentication flows
- Cross-page behavior
- Form interactions
- Browser storage behavior
- Multi-user browser interaction
- Accessibility-driven interaction
- Responsive UI behavior
- Integration between the frontend and backend

Playwright SHOULD NOT replace lower-level tests for every business-rule permutation.

Pure functions, domain rules, service methods, database constraints, webhook handling, token validation, concurrency rules, and large edge-case matrices SHOULD normally be tested at unit, service, integration, or API level. Browser tests should cover representative and high-value workflows.

### 3.4 Name the test category accurately

Every Playwright test MUST be classifiable by test category. Repositories SHOULD make the category identifiable through naming, tags, directories, projects, or configuration. A repository does not need to use every mechanism, but developers and automated agents must be able to determine what infrastructure the test uses and what the test can legitimately claim to prove.

#### Mocked browser tests

A mocked browser test runs browser interactions while one or more application or external-service responses are replaced with controlled fixtures.

It proves that the frontend behaves correctly against the mocked contract. For example, it may prove that the UI disables an action when a mocked API response reports that the action is unavailable.

It does **not** prove that:

- The real backend calculates that state correctly
- The database enforces the corresponding rule
- Concurrent requests are handled safely
- Authentication or authorization is enforced server-side
- A payment, email, identity, or other provider behaves correctly
- A queue, worker, webhook, or scheduled job processes the event correctly

Those claims require appropriate backend, API, integration, full-stack, or provider-integration tests.

```js
// This proves frontend behavior against the mocked response only.
await page.route('**/api/resources/123', async route => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    json: { id: '123', available: false },
  });
});

await page.goto('/resources/123');
await expect(page.getByRole('button', { name: 'Continue' })).toBeDisabled();
```

#### Full-stack browser tests

A full-stack browser test exercises the real application frontend and approved test instances of the application backend and supporting infrastructure.

It may prove browser-visible integration across application-controlled components, but only for the components and environment actually exercised. It MUST NOT be described as proving production behavior when production services, production configuration, or production-scale concurrency were not tested.

#### Provider-integration tests

Provider-integration tests exercise an approved sandbox, emulator, or test environment for an external provider. They may use Playwright when browser interaction is part of the behavior, but provider integration does not inherently require a browser.

Webhook validation, payment idempotency, email delivery processing, token verification, provider callbacks, and similar server-side concerns SHOULD normally be tested through backend, API, or integration tests unless browser behavior is genuinely part of the scenario.

Test names, tags, project configuration, and documentation MUST NOT imply broader coverage than the selected category actually provides.

---

## 4. Test Independence and Isolation

### 4.1 Every test must run independently

Each test MUST be able to run:

- By itself
- In any order
- Before or after any other test
- After another test fails
- Repeatedly against a clean test environment

Tests MUST be order-independent even when the current environment requires `workers: 1`. Parallel execution is a separate environment capability and MUST be enabled only after shared resources are properly isolated.

A test MUST NOT depend on another test creating, updating, or deleting data first.

```js
// Forbidden: the second test depends on the first test.
test('creates a record', async ({ page }) => {
  // Creates a shared record.
});

test('edits the created record', async ({ page }) => {
  // Assumes the previous test already ran.
});
```

Create the required state independently for each test or group the actions into a single workflow test when the sequence itself is what is being tested.

### 4.2 Browser isolation is not database isolation

Playwright creates a new browser context for each test by default. This isolates browser cookies, storage, and pages, but it does not automatically isolate backend data.

Tests MUST also control and isolate:

- Database records
- User accounts
- Uploaded files
- Background jobs
- Queues
- Cached data
- External-provider state
- Shared test resources

### 4.3 Use unique test data

Mutable records MUST have unique identifiers when tests can run concurrently.

Use stable uniqueness sources such as:

- `testInfo.testId`
- `testInfo.workerIndex`
- A UUID
- A fixture-generated unique suffix
- A database-generated identifier returned during setup

```js
import { randomUUID } from 'node:crypto';

const uniqueName = `e2e-record-${randomUUID()}`;
```

Do not rely only on timestamps when tests may create data within the same millisecond or when deterministic cleanup is required.

### 4.4 Do not solve isolation with serial execution

`test.describe.serial()` and other forced ordering MUST NOT be used as a shortcut for shared-state problems.

Serial execution MAY be used only when the ordered sequence is the actual behavior under test and cannot reasonably be represented as one test. The reason MUST be documented in the test file.

### 4.5 Cleanup must be reliable

Tests SHOULD create only the data they need.

Cleanup SHOULD occur through controlled fixtures or API helpers. Cleanup logic MUST be safe when setup partially fails.

Use `try/finally`, fixture teardown, or idempotent cleanup APIs when appropriate.

```js
test('updates a record', async ({ request, page }) => {
  const record = await createRecord(request);

  try {
    await page.goto(`/records/${record.id}`);
    // Test behavior.
  } finally {
    await deleteRecord(request, record.id);
  }
});
```

When the test environment is reset completely between runs, per-test cleanup MAY be reduced, but tests must still remain independent and order-free within the same run. They must also avoid shared-state conflicts before parallel execution is enabled.

---

## 5. Directory and File Organization

The repository's existing Playwright location, naming, module system, and language convention MUST be inspected before adding files.

This guide MUST NOT be used as justification to create a new root-level `tests/` directory, reorganize an established suite, or migrate files between JavaScript and TypeScript.

The following is an example only:

```text
<existing-playwright-root>/
  e2e/
    authentication/
      sign-in.spec.js
      sign-out.spec.js
    account/
      profile.spec.js
    records/
      create-record.spec.js
      edit-record.spec.js
  fixtures/
    test.js
    auth.fixture.js
    data.fixture.js
  pages/
    sign-in.page.js
    records.page.js
  components/
    navigation.component.js
    dialog.component.js
  helpers/
    api.js
    data-builders.js
    assertions.js
  setup/
    auth.setup.js
  data/
    static-example.json
<existing-playwright-config>
<ignored-auth-state-directory>/
```

Repositories MAY use different folders, file names, and co-location strategies. Responsibilities SHOULD remain understandable, but existing repository conventions take precedence over this example.

### 5.1 Test files

Test files MUST:

- Follow the repository's existing test-file convention, such as `.spec.js`, `.spec.ts`, `.test.js`, or `.test.ts`
- Follow the repository's existing JavaScript or TypeScript convention
- Contain executable test scenarios
- Avoid becoming general-purpose utility modules
- Be grouped by user-facing capability or workflow

Adding Playwright coverage MUST NOT trigger an unrequested JavaScript-to-TypeScript or TypeScript-to-JavaScript migration.

### 5.2 Fixtures

Fixtures SHOULD own reusable lifecycle behavior, including:

- Creating and cleaning test data
- Providing authenticated pages
- Providing role-specific contexts
- Supplying API clients
- Managing temporary files
- Establishing reusable environment state

### 5.3 Page and component objects

Page objects and component objects SHOULD represent stable user-facing areas, not individual test cases.

### 5.4 Helpers

Helpers SHOULD contain small, focused, reusable functions. Helpers MUST NOT hide the main behavior being tested so completely that the test becomes unreadable.

---

## 6. Test Naming and Organization

### 6.1 Describe behavior clearly

Test titles MUST describe the expected behavior or outcome.

Preferred format:

```text
[action or condition] [expected result]
```

Examples:

```js
test('submits the form when all required fields are valid', async ({ page }) => {});

test('shows a validation error when the email is missing', async ({ page }) => {});

test('redirects an unauthenticated user to sign in', async ({ page }) => {});
```

Avoid vague names:

```js
test('works', async ({ page }) => {});
test('test form', async ({ page }) => {});
test('scenario 2', async ({ page }) => {});
```

### 6.2 Organize by behavior

Use `test.describe()` to group related behavior when it improves clarity.

```js
test.describe('profile editing', () => {
  test('saves valid profile changes', async ({ page }) => {});
  test('rejects an invalid phone number', async ({ page }) => {});
});
```

Do not create deeply nested `describe` blocks. More than two levels SHOULD be avoided.

### 6.3 Keep tests focused

A test SHOULD verify one coherent behavior or workflow.

This does not mean one assertion per test. Multiple assertions are appropriate when they collectively prove one result.

Split a test when:

- Failures would have unrelated causes
- Setup differs significantly
- The scenarios can run independently
- The title requires the word "and" to join unrelated outcomes

Keep a workflow together when splitting it would create artificial dependencies or repeat the same expensive setup without improving diagnosis.

### 6.4 Use tags consistently

Tags MAY classify tests by purpose or execution group.

```js
test('completes the critical workflow', { tag: '@smoke' }, async ({ page }) => {});
```

Common categories MAY include:

- `@smoke`
- `@regression`
- `@critical`
- `@visual`
- `@accessibility`
- `@external`

Tags MUST have an agreed meaning. Do not create near-duplicate or one-off tags without updating the project documentation.

---

## 7. Arrange, Act, Assert

Tests SHOULD be easy to read as three logical phases:

1. Arrange the required state.
2. Act through the behavior under test.
3. Assert the expected result.

```js
test('updates an existing record', async ({ request, page }) => {
  // Arrange
  const record = await createRecord(request, { name: 'Before' });
  await page.goto(`/records/${record.id}`);

  // Act
  await page.getByLabel('Name').fill('After');
  await page.getByRole('button', { name: 'Save' }).click();

  // Assert
  await expect(page.getByRole('status')).toHaveText('Saved successfully');
  await expect(page.getByLabel('Name')).toHaveValue('After');
});
```

Comments are optional when the phases are already obvious. Do not add comments that merely repeat the code.

---

## 8. Locators

### 8.1 Locator priority

Use locators in this general priority order:

1. `getByRole()` with an accessible name
2. `getByLabel()`
3. `getByPlaceholder()` when the placeholder is a stable user-facing contract
4. `getByText()` for stable visible content
5. `getByAltText()` or `getByTitle()` when semantically appropriate
6. `getByTestId()` for an explicit testing contract
7. A short, stable CSS locator only when no better option exists

```js
const saveButton = page.getByRole('button', { name: 'Save' });
const emailInput = page.getByLabel('Email address');
const successStatus = page.getByRole('status');
```

### 8.2 Prefer accessible, user-facing locators

Locators SHOULD reflect how a user identifies an element. This improves both test resilience and accessibility quality.

```js
// Preferred
page.getByRole('button', { name: 'Delete record' });

// Avoid
page.locator('.red-button.delete-action');
```

### 8.3 Locators must be unique

A locator used for an action or singular assertion MUST uniquely identify its intended element.

Do not silence strict-mode errors by casually adding `.first()`, `.last()`, or `.nth()`.

```js
// Weak: hides an ambiguous locator.
await page.getByRole('button', { name: 'Edit' }).first().click();

// Better: scope to the correct record.
const row = page.getByRole('row').filter({ hasText: recordName });
await row.getByRole('button', { name: 'Edit' }).click();
```

Positional locators MAY be used only when position itself is part of the behavior being tested.

### 8.4 Scope locators instead of building DOM paths

Use locator chaining and filtering.

```js
const card = page.getByRole('article').filter({ hasText: recordName });
await card.getByRole('button', { name: 'Open' }).click();
```

Avoid long CSS and XPath chains:

```js
// Forbidden unless no stable alternative exists.
page.locator('#root > main > div:nth-child(2) > div > button');
page.locator('//div[3]/section/div[2]/button');
```

### 8.5 Test IDs are explicit contracts

Use `getByTestId()` when an element cannot be reliably identified through accessible semantics or stable visible content.

Test IDs MUST:

- Describe purpose, not appearance
- Remain stable across styling changes
- Be unique within the relevant scope
- Avoid database values or sensitive information unless required

```jsx
<button data-testid="record-menu-trigger">Open menu</button>
```

```js
await page.getByTestId('record-menu-trigger').click();
```

Do not add test IDs to every element by default.

### 8.6 Do not store element handles

Use `Locator` objects instead of `ElementHandle` objects. Locators re-resolve elements and participate in Playwright's waiting behavior.

---

## 9. Waiting and Synchronization

### 9.1 Rely on Playwright auto-waiting

Playwright automatically waits for actionability conditions before actions such as clicks and fills. Tests SHOULD rely on locators and web-first assertions instead of adding manual delays.

### 9.2 Fixed sleeps are forbidden

`page.waitForTimeout()` and equivalent sleep helpers MUST NOT appear in committed tests.

```js
// Forbidden
await page.waitForTimeout(2000);
```

A fixed delay MAY be used temporarily during local debugging, but it MUST be removed before the code is committed.

### 9.3 Wait for an observable condition

Wait for the state that actually matters:

```js
await expect(page.getByRole('status')).toHaveText('Complete');
await expect(page).toHaveURL(/\/records\/\w+$/);
await expect(page.getByRole('button', { name: 'Continue' })).toBeEnabled();
```

When a specific network request is the meaningful synchronization point, start waiting before triggering the request:

```js
const responsePromise = page.waitForResponse(
  response =>
    response.url().endsWith('/api/records') &&
    response.request().method() === 'POST' &&
    response.status() === 201,
);

await page.getByRole('button', { name: 'Create' }).click();
const response = await responsePromise;
```

### 9.4 Do not use `networkidle` as a general readiness signal

`networkidle` SHOULD NOT be used to decide that a page is ready. Modern applications may keep background requests, analytics, polling, or open connections active.

Wait for a specific visible state, URL, request, response, or application signal instead.

### 9.5 Use polling only for eventual external state

Use `expect.poll()` when the expected result is not directly represented by a locator and may become true asynchronously.

```js
await expect
  .poll(async () => {
    const response = await request.get(`/api/jobs/${jobId}`);
    const body = await response.json();
    return body.status;
  })
  .toBe('completed');
```

Polling MUST have a meaningful assertion target. Do not create unbounded custom loops.

---

## 10. Assertions

### 10.1 Prefer web-first assertions

Use Playwright's async locator and page assertions whenever possible.

```js
// Preferred
await expect(page.getByRole('alert')).toContainText('Invalid email');

// Avoid
expect(await page.getByRole('alert').textContent()).toContain('Invalid email');
```

Web-first assertions re-check the condition until it passes or reaches the assertion timeout.

### 10.2 Assert the final meaningful state

Assertions SHOULD prove the expected user or system outcome, not merely an intermediate animation or transient implementation detail.

Good assertions include:

- The expected confirmation is visible
- The URL changed correctly
- The updated value is displayed
- The record appears or disappears
- The relevant control changed state
- The API or database contains the expected result

### 10.3 Avoid weak assertions

The following are usually too weak by themselves:

```js
expect(response.ok()).toBeTruthy();
await expect(page.locator('body')).toBeVisible();
expect(items.length).toBeGreaterThan(0);
```

Use precise assertions tied to the scenario.

### 10.4 Use exactness intentionally

Use exact text when the exact content is part of the contract. Use regular expressions or partial matching only when variable content makes exact matching inappropriate.

```js
await expect(page.getByRole('heading')).toHaveText('Account settings');
await expect(page.getByRole('status')).toContainText('Saved');
```

Do not loosen an assertion merely to make a failing test pass.

### 10.5 Use soft assertions sparingly

`expect.soft()` MAY be used when collecting multiple independent diagnostics is valuable.

It SHOULD NOT be used for required preconditions. A test should stop when continuing would produce misleading failures or unsafe actions.

### 10.6 Server-side verification

A browser assertion SHOULD normally verify the visible result. An API or database assertion MAY additionally verify persistence when the workflow's purpose includes server-side state.

Avoid asserting the same fact repeatedly through multiple layers unless the additional assertion catches a distinct failure mode.

---

## 11. Test Data and State Setup

### 11.1 Use API or fixture setup for unrelated prerequisites

The browser SHOULD perform the behavior being tested. Unrelated prerequisite state SHOULD be created through fixtures, APIs, factories, or controlled database utilities.

For example, a test of record editing may create the original record through an API, then edit it through the UI.

This keeps tests focused, faster, and easier to diagnose.

### 11.2 Keep dedicated UI tests for setup workflows

Using API setup does not mean setup workflows should never be tested through the UI. Each important creation or onboarding flow SHOULD have its own dedicated browser test.

Other tests SHOULD reuse lower-level setup when creation is only a prerequisite.

### 11.3 Use builders or factories

Complex test objects SHOULD be created through builders or factories with clear inputs and sensible defaults.

```js
import { randomUUID } from 'node:crypto';

function buildRecord(overrides = {}) {
  return {
    name: `record-${randomUUID()}`,
    status: 'active',
    ...overrides,
  };
}
```

Factories MUST allow the test to override fields relevant to the scenario.

### 11.4 Avoid unexplained fixture data

Do not use large shared JSON fixtures when only a few fields matter. The test should make important inputs visible.

Static files are appropriate for:

- Upload testing
- Contract examples
- Large structured payloads
- Stable visual assets

### 11.5 Never use production data

Playwright tests MUST NOT create, update, delete, or depend on production data.

Automated tests MUST run only against approved test environments and accounts.

---

## 12. Fixtures and Hooks

### 12.1 Prefer fixtures for reusable lifecycle behavior

Fixtures are preferred over repeated hooks when setup has a reusable value and teardown responsibility.

```js
import { test as base } from '@playwright/test';

export const test = base.extend({
  createdRecord: async ({ request }, use) => {
    const record = await createRecord(request);

    try {
      await use(record);
    } finally {
      await deleteRecord(request, record.id);
    }
  },
});
```

### 12.2 Keep fixtures composable

A fixture SHOULD have one clear responsibility. Avoid a single fixture that creates an entire application universe for every test.

Fixtures SHOULD be lazy. A fixture should perform work only when a test requests it.

### 12.3 Hooks must remain small and predictable

`beforeEach` MAY handle simple navigation or state that every test in the block genuinely needs.

Avoid large `beforeEach` hooks that hide most of the test setup. Hidden setup makes tests difficult to understand and can create unnecessary runtime.

### 12.4 Use `beforeAll` carefully

`beforeAll` MUST NOT create mutable state that individual tests modify unless the tests are intentionally isolated from one another through separate copies.

A worker restart after a failure can cause `beforeAll` to run again. Setup MUST be safe and repeatable.

### 12.5 Teardown must tolerate partial setup

Teardown code MUST handle cases where setup failed before all resources were created.

---

## 13. Authentication and User Roles

### 13.1 Reuse authenticated state when appropriate

Authentication state MAY be created in a setup project and reused through `storageState` when tests do not need to exercise the sign-in flow itself.

```js
use: {
  storageState: 'playwright/.auth/user.json',
}
```

A separate test MUST cover the actual sign-in workflow when sign-in is an important application behavior.

### 13.2 Protect authentication state files and credentials

Authentication-state files MUST be stored in an ignored location and excluded from version control.

Authentication state may contain sensitive cookies, tokens, local storage, headers, or IndexedDB data. It MUST be treated as a secret.

Tests MUST NOT:

- Use production credentials
- Use a developer's or employee's personal account
- Generate reusable auth state from a production environment
- Commit passwords, tokens, cookies, headers, or saved browser state
- Copy authenticated browser profiles into the test suite

Use dedicated test accounts, mocked authentication, local emulators, or approved test environments according to the test category.

```gitignore
playwright/.auth/
```

### 13.3 Generate and refresh authentication state deterministically

Saved authentication state MUST be generated only from approved test environments and dedicated test accounts. It SHOULD be created through a deterministic setup project, fixture, bootstrap script, or documented repository command rather than copied manually from a developer browser.

Authentication-state files SHOULD be treated as disposable generated artifacts. The test setup MUST be able to regenerate them when tokens expire, credentials rotate, accounts are recreated, roles or permissions change, or the authentication implementation changes.

Tests MUST NOT silently rely on stale authentication state when the scenario requires a specific role, permission, account condition, or token scope. Regeneration SHOULD happen before dependent tests run, not through ad hoc manual repair after failures.

### 13.4 Use separate states for separate roles

Each role SHOULD have its own storage-state file, fixture, or account strategy.

Tests MUST NOT change roles by mutating frontend storage directly unless that mutation is the behavior under test.

### 13.5 Shared accounts must not share mutable server state

A single shared account MAY be reused only when tests do not modify server-side state associated with that account.

When tests modify account-specific state and run in parallel, use one account per worker or create isolated accounts per test.

### 13.6 Multi-user scenarios

Use separate browser contexts when multiple users or roles must interact in one scenario.

```js
const firstContext = await browser.newContext({ storageState: firstAuthFile });
const secondContext = await browser.newContext({ storageState: secondAuthFile });

try {
  const firstPage = await firstContext.newPage();
  const secondPage = await secondContext.newPage();

  // Interact as two independent users.
} finally {
  await firstContext.close();
  await secondContext.close();
}
```

---

## 14. Page Objects and Reusable Components

### 14.1 Use page objects for stable concepts

Page objects MAY encapsulate:

- Stable locators
- Repeated navigation
- Repeated interaction sequences
- Domain-readable actions

```js
export class RecordsPage {
  constructor(page) {
    this.page = page;
    this.createButton = page.getByRole('button', { name: 'Create record' });
    this.nameInput = page.getByLabel('Name');
  }

  async goto() {
    await this.page.goto('/records');
  }

  async create(name) {
    await this.createButton.click();
    await this.nameInput.fill(name);
    await this.page.getByRole('button', { name: 'Save' }).click();
  }
}
```

### 14.2 Do not create page objects mechanically

A page object is not required for every page or every test. Create one when it removes meaningful duplication or provides a stable, readable abstraction.

### 14.3 Keep assertions visible

Assertions SHOULD generally remain in the test so expected behavior is easy to see.

Page objects MAY expose domain-specific assertion methods when they are broadly reused and remain explicit, but they MUST NOT hide all test expectations behind vague methods such as `verifyEverything()`.

### 14.4 Prefer component objects for shared UI

Reusable UI that appears on multiple pages SHOULD use a component object rather than duplicating locators across page objects.

Examples include:

- Navigation bars
- Date pickers
- Data tables
- Dialogs
- Toast notifications
- Pagination controls

### 14.5 Avoid giant page objects

A page object SHOULD represent one page, section, or stable capability. Split it when it becomes a general dumping ground for unrelated helpers.

---

## 15. Network Requests and External Services

### 15.1 Test only what the team controls

The primary test suite MUST NOT depend on uncontrolled live third-party services.

Third-party responses SHOULD be mocked, intercepted, or replaced with approved test adapters when testing application behavior.

```js
await page.route('**/external-api/**', async route => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    json: { status: 'approved' },
  });
});
```

### 15.2 Register mocks before navigation or action

Network mocks MUST be installed before the request can occur.

```js
await page.route('**/api/config', route => route.fulfill({ json: testConfig }));
await page.goto('/');
```

### 15.3 Keep test categories explicit and separate

Mocked browser, full-stack browser, and provider-integration coverage SHOULD be identifiable through project configuration, tags, directory organization, naming, or another consistent repository convention.

Provider-integration tests MAY exercise approved sandboxes, emulators, or test environments. They do not inherently require Playwright and SHOULD use backend, API, or integration tooling when browser interaction is not part of the behavior.

Provider-integration tests SHOULD:

- Be separated from the deterministic mocked browser suite
- Use provider test accounts or approved emulator identities only
- Be safe to repeat
- Avoid real financial, email, identity, or production effects
- Have clear environment requirements
- State exactly which provider boundary they exercise

A mocked browser test MUST NOT be presented as proof that the real backend or provider integration works.

### 15.4 Do not over-mock the system under test

Mock third-party boundaries and hard-to-control dependencies. Do not mock the application's own behavior so extensively that the test no longer validates the real integration being claimed.

### 15.5 Assert request details only when relevant

Network assertions MAY verify method, URL, status, or payload when those details are part of the contract. Avoid coupling every UI test to exact internal request payloads.

---

## 16. Asynchronous Jobs and Eventual Consistency

Applications may use queues, workers, scheduled jobs, webhooks, or delayed processing.

Tests MUST synchronize with a deterministic signal rather than sleep for an estimated duration.

Preferred approaches include:

- A controlled test endpoint that runs queued work
- Polling a status endpoint with `expect.poll()`
- Waiting for a specific browser-visible state
- Delivering a deterministic test webhook
- Inspecting a controlled API response

Background processing MUST have an explicit timeout and a useful failure message.

Do not leave tests waiting indefinitely for a worker or external callback.

---

## 17. Time-Dependent Behavior

### 17.1 Control browser time when needed

Use Playwright's clock support for browser-side time behavior such as:

- Timers
- Countdown displays
- Client-side expiration
- Scheduled UI changes
- Date-based rendering

```js
await page.clock.setFixedTime(new Date('2030-01-15T12:00:00Z'));
```

Clock configuration MUST occur before the application reads the relevant time when required by the scenario.

### 17.2 Browser time does not control server time

Changing the browser clock does not automatically change backend, database, queue, or provider time.

Server-side time-dependent behavior SHOULD use a separate test clock, explicit injected timestamp, or controlled test environment mechanism.

### 17.3 Use controlled reference time and dates

Tests SHOULD derive time-sensitive fixture data from a controlled reference time rather than from the machine's uncontrolled current time.

Use one of the following according to the scenario:

- Dates supplied by controlled mocked API fixtures
- A fixture or builder that derives valid dates from an explicit test reference time
- A backend test clock, injected timestamp, or approved environment mechanism
- Playwright's browser clock when the browser's perception of time affects the UI

```js
const referenceTime = new Date('2030-01-15T12:00:00Z');
const scheduledTime = new Date(referenceTime);
scheduledTime.setUTCDate(scheduledTime.getUTCDate() + 7);
```

Avoid hardcoded calendar dates that silently become invalid because of rolling application windows, expiration rules, or the real passage of time.

Avoid vague uses of `new Date()` or "today plus one day" when the test cannot control what "today" means.

Literal calendar dates MAY be used when that exact date is part of the behavior under test or when all relevant application clocks are intentionally controlled.

Dates MUST include a known timezone when timezone behavior matters.

---

## 18. Timeouts

### 18.1 Configure defaults centrally

Test, assertion, action, and navigation timeouts SHOULD be configured centrally in `playwright.config.js`.

```js
export default defineConfig({
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
});
```

Project-specific values may differ.

### 18.2 Do not increase global timeouts to hide problems

Timeouts MUST NOT be increased merely because tests are flaky.

First investigate:

- Incorrect synchronization
- Ambiguous locators
- Shared data
- Slow setup
- Resource constraints
- Environment instability
- A real application performance issue

### 18.3 Use local timeout overrides intentionally

A longer local timeout MAY be used for a legitimately long operation.

```js
await expect(page.getByRole('status')).toHaveText('Import complete', {
  timeout: 30_000,
});
```

The reason SHOULD be clear from the operation or documented in a short comment.

### 18.4 Do not disable timeouts casually

Unlimited timeouts SHOULD NOT be used in committed tests.

---

## 19. Retries and Flaky Tests

### 19.1 Retries are diagnostic, not a fix

A test that passes only on retry is still flaky.

Retries MAY be enabled in CI to collect traces and reduce interruption while a failure is investigated, but retries MUST NOT be used to conceal an unreliable test.

```js
retries: process.env.CI ? 1 : 0,
```

The exact retry count is a project decision. It SHOULD remain low.

### 19.2 Fix the cause of flakiness

Common causes include:

- Shared mutable data
- Fixed sleeps
- Weak readiness checks
- Ambiguous locators
- Animation timing
- Live third-party dependencies
- Reused accounts
- Uncontrolled background jobs
- Incorrect cleanup
- Environment resource limits

### 19.3 Do not commit repeated local retries

Loops that rerun an action until it succeeds are prohibited unless retry behavior itself is the feature under test.

### 19.4 Quarantine only with ownership

A known flaky test MAY be quarantined temporarily only when:

- The issue is tracked
- An owner is identified
- The test remains visible in reporting
- The quarantine has a removal condition

Do not silently skip flaky tests.

---

## 20. Parallelism and Workers

### 20.1 Require independence before parallelism

Tests MUST be independent and order-free regardless of the configured worker count.

Independent tests do not automatically mean that the current environment is safe for multi-worker execution. Full-stack environments may temporarily require `workers: 1` while test users, database records, queues, ports, provider resources, or other shared state remain unisolated.

Serial execution MUST NOT be used as permission for one test to depend on another.

### 20.2 Start conservatively and enable parallelism intentionally

CI SHOULD begin with a conservative worker count when the suite or environment is new, resource-constrained, or not yet isolated.

```js
workers: process.env.CI ? 1 : undefined,
```

Increase parallelism only after proving that tests, accounts, data, ports, queues, files, clocks, and external resources are isolated. Document any suite that intentionally remains single-worker and the shared resource that requires it.

### 20.3 Prefer sharding for scale

For large suites, sharding across CI jobs is preferred over forcing too many workers onto one machine, provided the backing environment can safely support the shards.

### 20.4 Worker-scoped resources must be unique

When parallel execution is enabled, worker-scoped accounts, schemas, databases, ports, directories, queues, and provider resources MUST include the worker index or another unique identifier.

---

## 21. Browser Projects and Coverage

### 21.1 Define browser coverage intentionally

Do not run every test against every browser without considering cost and value.

A common strategy is:

- Run the full suite against the primary browser
- Run a smaller critical suite against additional browsers
- Run responsive projects for important viewport classes

### 21.2 Use projects for meaningful differences

Playwright projects MAY represent:

- Browser engines
- Desktop and mobile viewports
- Authenticated roles
- Environment configurations
- Locale or timezone coverage
- Smoke and regression groups

Projects MUST have clear names and avoid duplicating coverage without a purpose.

### 21.3 Do not branch test logic excessively by browser

Avoid large `if (browserName === ...)` blocks. Browser-specific behavior SHOULD be rare, documented, and tied to a real compatibility difference.

---

## 22. Visual and Snapshot Testing

### 22.1 Use visual tests selectively

Visual comparisons SHOULD target stable, high-value presentation contracts.

Good candidates include:

- Critical components
- Important empty states
- Stable responsive layouts
- High-risk visual regressions

Avoid broad screenshot coverage for pages dominated by dynamic content.

### 22.2 Stabilize dynamic content

Before taking a screenshot:

- Use controlled data
- Disable or finish animations
- Fix browser time when needed
- Hide or mask unavoidable dynamic regions
- Use a stable viewport
- Wait for relevant fonts and assets

### 22.3 Generate and run baselines consistently

Visual baselines MUST be generated and compared in a consistent browser, operating system, configuration, and rendering environment.

CI containers are preferred for stable visual output.

### 22.4 Review baseline updates

Snapshot baselines MUST NOT be updated automatically just to make CI pass.

Every update requires review of the actual visual difference.

### 22.5 Prefer scoped screenshots

Element or component screenshots are usually more stable and easier to review than full-page screenshots.

---

## 23. Accessibility-Oriented Testing

Semantic locators SHOULD be used because they reflect how users and assistive technologies identify controls.

Tests SHOULD verify critical accessibility behavior where appropriate, including:

- Keyboard access
- Focus movement
- Dialog focus trapping
- Accessible names
- Error association
- Required-field communication
- Disabled state
- Live-region announcements

An automated accessibility scanner MAY supplement these checks, but it does not replace workflow-based accessibility testing or manual review.

---

## 24. File Uploads, Downloads, Popups, and New Pages

### 24.1 Register event waits before triggering events

```js
const downloadPromise = page.waitForEvent('download');
await page.getByRole('button', { name: 'Download' }).click();
const download = await downloadPromise;
```

The same pattern applies to popups, new pages, dialogs, and other browser events.

### 24.2 Use temporary test files

Generated upload and download files SHOULD use the test output directory or another isolated temporary location.

Do not write test artifacts into source directories.

### 24.3 Validate meaningful file behavior

Assertions MAY verify:

- Suggested filename
- Download completion
- File existence
- File type
- Parsed contents

Do not assert machine-specific absolute paths.

---

## 25. Error, Negative, and Boundary Scenarios

Each critical workflow SHOULD include representative coverage for:

- Successful behavior
- Validation failure
- Authorization failure
- Server failure
- Empty state
- Relevant boundary values

Do not create an exhaustive browser test for every possible invalid input. Large input matrices belong in lower-level tests unless browser behavior changes meaningfully for each case.

Failure scenarios SHOULD mock or control the exact failure condition rather than relying on an unstable service failure.

---

## 26. Debugging and Failure Artifacts

### 26.1 Configure useful artifacts

A recommended baseline is:

```js
use: {
  trace: 'on-first-retry',
  screenshot: 'only-on-failure',
  video: 'retain-on-failure',
}
```

When retries are disabled, `trace: 'retain-on-failure'` MAY be more appropriate.

### 26.2 Do not record everything without need

Recording traces and video for every successful test increases runtime and storage. Use failure-focused settings unless a temporary investigation requires more.

### 26.3 Attach useful diagnostics

Tests and fixtures MAY attach:

- API responses
- Generated identifiers
- Relevant JSON state
- Console logs
- Application logs
- Small text summaries

Sensitive values MUST be redacted.

### 26.4 Failure messages must be actionable

Custom assertions and polling should provide enough context to identify:

- What was expected
- What was observed
- Which resource was involved
- Which operation failed

---

## 27. Logging and Secrets

Tests MUST NOT print or attach:

- Passwords
- Access tokens
- Session cookies
- Authorization headers
- Private API keys
- Full authentication-state files
- Sensitive user data

Logs SHOULD include generated test identifiers when they help correlate frontend, backend, and worker activity.

Secrets MUST come from approved environment variables or secret management. They MUST NOT be hardcoded in test files, fixtures, screenshots, or committed configuration.

---

## 28. Language and Code Quality

### 28.1 Follow the repository language convention

Playwright tests MUST follow the repository's existing JavaScript or TypeScript convention unless a language migration is explicitly requested and separately justified.

TypeScript MAY be preferred when the project already uses it or intentionally adopts it. This general standard MUST NOT require TypeScript or trigger an unrelated JavaScript-to-TypeScript migration.

JavaScript tests SHOULD use the repository's available type checking, JSDoc, linting, editor tooling, or runtime validation where they materially improve safety.

### 28.2 Await Playwright operations

All asynchronous Playwright operations MUST be awaited or intentionally returned.

Use the repository's linting or static-analysis rules to detect missing `await` statements. TypeScript repositories may use rules such as `@typescript-eslint/no-floating-promises`; JavaScript repositories should use the closest supported equivalent.

```js
// Forbidden
page.getByRole('button', { name: 'Save' }).click();

// Correct
await page.getByRole('button', { name: 'Save' }).click();
```

### 28.3 Run repository-appropriate static checks

The test code SHOULD pass the checks configured by the repository, which may include:

- Type checking
- Linting
- Formatting
- Playwright test discovery

Typical checks may include:

```bash
npx eslint <playwright-test-path> <playwright-config>
npx playwright test --list
```

TypeScript repositories SHOULD also run their configured type-checking command. Commands and file paths MUST follow the repository rather than being invented from this guide.

### 28.4 Keep abstractions explicit

TypeScript fixtures, builders, API helpers, and page objects SHOULD have useful types and avoid unjustified `any`.

JavaScript abstractions SHOULD keep inputs, outputs, defaults, and error behavior clear through naming, focused APIs, JSDoc where useful, and repository-supported static analysis.

---

## 29. Continuous Integration Standards

CI MUST:

- Install dependencies deterministically
- Install only the required Playwright browsers and system dependencies
- Run against an approved isolated environment
- Preserve useful reports and failure artifacts
- Fail when required tests fail
- Avoid production credentials and data

Recommended CI behavior includes:

- `npm ci` or the package manager's locked equivalent
- A pinned Playwright package and compatible browser environment
- One worker initially when stability is uncertain
- Sharding when the suite becomes large
- HTML or machine-readable reports retained as artifacts
- Traces, screenshots, and videos retained for failures

Visual tests MUST run in the same rendering environment used to generate their baselines.

---

## 30. Forbidden Patterns

The following patterns MUST NOT appear in Playwright tests unless a documented exception applies:

1. `page.waitForTimeout()` or another fixed sleep.
2. Tests that depend on another test running first.
3. Shared mutable test data without isolation.
4. Production users, production data, or production side effects.
5. Long CSS selectors or XPath tied to DOM structure when a semantic locator is available.
6. `.first()`, `.last()`, or `.nth()` used only to suppress locator ambiguity.
7. `force: true` used to bypass an actual interactability problem.
8. `networkidle` used as a general page-readiness check.
9. Retries increased instead of fixing a flaky test.
10. Assertions removed or weakened merely to make a test pass.
11. Tests that perform actions without asserting a meaningful outcome.
12. Hardcoded passwords, tokens, cookies, API keys, or other secrets.
13. Authentication-state files committed to version control.
14. Live third-party dependencies in the deterministic main suite.
15. Giant fixtures or hooks that create unnecessary state for every test.
16. Helpers that hide the scenario so completely that the test no longer communicates its behavior.
17. Automatic screenshot-baseline updates without human review.
18. Unlimited polling loops or disabled timeouts.
19. Silent skipping or quarantining without a tracked reason.
20. Direct database manipulation from UI test code when an approved fixture, factory, or test API is available.
21. A mocked browser test described as proving real backend, database, provider, worker, webhook, authorization, or concurrency behavior.
22. Hardcoded dates that become stale under rolling application windows when controlled reference time or fixture builders are available.
23. An unrequested JavaScript-to-TypeScript or TypeScript-to-JavaScript migration introduced only to add Playwright coverage.

### 30.1 About `force: true`

`force: true` MAY be used only when the application intentionally requires interaction that Playwright's normal actionability rules cannot represent. The test MUST include a comment explaining why forcing the action is correct.

It MUST NOT be used to bypass overlays, disabled controls, unfinished animations, incorrect layering, or other application defects.

---

## 31. Exception Standard

A rule may be overridden only when all of the following are true:

- The normal approach cannot correctly represent the required test.
- The exception is narrow.
- The reason is documented beside the code or in project testing documentation.
- The exception does not expose secrets or production data.
- The resulting test remains deterministic and maintainable.

Do not create broad exceptions to avoid fixing test design problems.

---

## 32. Review Checklist

Before accepting a new or modified Playwright test, verify the following.

### Scenario

- [ ] The test verifies user-visible or externally observable behavior.
- [ ] Playwright is the appropriate test layer.
- [ ] The title clearly describes the expected behavior.
- [ ] The test covers one coherent scenario.
- [ ] The final meaningful outcome is asserted.

### Isolation and data

- [ ] The test can run independently and in any order.
- [ ] Test data is controlled and unique where required.
- [ ] The test has no execution-order dependency, and any shared-resource constraints match the configured worker strategy.
- [ ] Cleanup is reliable and tolerates partial failure.
- [ ] No production data or services are used.

### Locators and waiting

- [ ] Locators use accessible or user-facing contracts where possible.
- [ ] Singular locators uniquely identify their target.
- [ ] No fragile DOM paths are used.
- [ ] No fixed sleeps are present.
- [ ] The test waits for specific observable conditions.
- [ ] `networkidle` is not used as a generic readiness signal.

### Assertions

- [ ] Web-first assertions are used where appropriate.
- [ ] Assertions are precise enough to detect the intended failure.
- [ ] Assertions were not weakened to accommodate flaky behavior.
- [ ] Server-side assertions are included only when they add meaningful coverage.

### Structure

- [ ] Reusable lifecycle behavior is in fixtures.
- [ ] Page objects or helpers reduce meaningful duplication without hiding the scenario.
- [ ] Hooks are small and predictable.
- [ ] Playwright operations are awaited.
- [ ] Abstractions follow the repository language convention and make inputs, outputs, and errors clear.

### Reliability and security

- [ ] External dependencies are controlled or explicitly separated.
- [ ] Time and asynchronous behavior are deterministic.
- [ ] No secrets or sensitive data are logged, attached, or committed.
- [ ] Retries are not being used as a substitute for a fix.
- [ ] Failure artifacts will provide useful diagnostics.

### Validation

- [ ] The agent provided the narrowest relevant Playwright command for manual execution.
- [ ] The agent provided any related linting, formatting, type-checking, or discovery commands.
- [ ] The agent did not run Playwright, browser, or e2e tests unless the project owner explicitly authorized that run for the current task.
- [ ] The agent did not claim tests passed unless they were actually executed successfully by an authorized agent run or reported by the project owner.
- [ ] Any unrun validation is clearly listed with exact commands for the project owner to run.

---

## 33. Instructions for Automated Coding Agents

When creating or modifying Playwright tests, an automated coding agent MUST:

1. Read this document before making changes.
2. Inspect existing test structure, fixtures, naming, and configuration before adding new patterns.
3. Reuse existing approved fixtures, builders, helpers, and page objects when appropriate.
4. Avoid creating duplicate abstractions.
5. Select the correct test layer instead of automatically writing an end-to-end test.
6. Preserve test independence and order-free execution. Do not enable or assume multi-worker execution until shared resources are isolated.
7. Identify the correct test category and state only what that category can prove.
8. Use semantic locators and web-first assertions.
9. Avoid fixed waits and retry-based workarounds.
10. Add or update cleanup for any new mutable test data.
11. Follow the repository's existing language, file naming, folder, and module conventions.
12. Keep product-specific behavior in the relevant test or project documentation, not in this general standards document.
13. Do not run Playwright, browser, or e2e tests unless the project owner explicitly authorizes that run for the current task.
14. Provide the narrowest relevant Playwright command for the project owner to run manually.
15. Provide any related linting, formatting, type-checking, or discovery commands separately.
16. If validation was not run by the agent, clearly state that it was not run and list the exact commands the project owner should run.
17. Report any test that remains flaky, skipped, incomplete, single-worker by necessity, or dependent on unavailable infrastructure.
18. Never claim a test passed unless it was actually executed successfully by an authorized agent run or reported by the project owner.

When a requested test would violate these standards, the agent SHOULD implement the closest compliant design and clearly explain the conflict.

---

## 34. Server Startup and Base URL

### 34.1 Configure a stable `baseURL`

Repositories SHOULD configure `use.baseURL` so tests can navigate with relative application URLs such as:

```js
await page.goto('/sign-in');
```

The base URL MUST identify the intended test environment. It MUST NOT silently point to production or depend on a developer's current shell directory, browser session, or manually remembered port.

A repository MAY read the URL from an environment variable and provide a safe local default:

```js
use: {
  baseURL:
    process.env.PLAYWRIGHT_BASE_URL ??
    'http://127.0.0.1:3000',
}
```

### 34.2 Use `webServer` when Playwright owns local server startup

Use Playwright's `webServer` configuration when the Playwright command is responsible for starting and stopping a local application server. The command MUST be a canonical repository command available to other developers and CI, such as a package script or checked-in task command.

Playwright configuration, CI, and required testing instructions MUST NOT depend on personal shell aliases. Personal aliases MAY exist as optional local conveniences, but they cannot be required to start, discover, debug, or run the suite.

```js
webServer: {
  command: 'npm run dev:test',
  url: 'http://127.0.0.1:3000',
  timeout: 120_000,
  reuseExistingServer: !process.env.CI,
}
```

The exact command, URL, timeout, and environment variables are repository-specific.

### 34.3 Reuse an existing server deliberately

`reuseExistingServer: !process.env.CI` MAY be used when local development intentionally supports reusing a compatible server while CI requires a fresh or separately managed environment.

An existing server MUST NOT be reused when doing so could silently connect tests to the wrong configuration, database, mock profile, build, credentials, or environment variables. Reuse is acceptable only when the repository workflow makes the server's identity and configuration predictable.

### 34.4 Use a meaningful readiness check

The configured `webServer.url` or readiness endpoint SHOULD indicate that the application is ready to serve tests, not merely that a process has opened a port. When the application requires dependent services, migrations, seeded data, or generated assets, the startup command or readiness check MUST account for them.

Tests SHOULD NOT add fixed sleeps to compensate for incomplete server readiness. Fix the startup command, readiness endpoint, or test-environment orchestration instead.

### 34.5 Support externally managed environments

When tests run against an already deployed or externally managed test environment, configure `baseURL` without requiring Playwright to start a local `webServer`. The environment MUST still be approved for automated testing, isolated from production, and documented well enough for the suite to run reproducibly.

---

## 35. Recommended Configuration Baseline

The following is a general starting point, not a mandatory project configuration:

```js
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [['html', { open: 'never' }], ['list']]
    : [['html', { open: 'never' }], ['line']],
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL:
      process.env.PLAYWRIGHT_BASE_URL ??
      'http://127.0.0.1:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: 'npm run dev:test',
        url: 'http://127.0.0.1:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
```

Before adopting this baseline, adjust it for the repository's existing test location, JavaScript or TypeScript convention, module system, environment, browser coverage, runtime, authentication, test categories, shared-resource isolation, and CI resources.

`fullyParallel: false` is a conservative starting point, not a requirement. Enable broader parallel execution only after the suite and its backing resources are proven safe.

---

## 36. Official References

This standard is based on Playwright's official documentation and should be reviewed when Playwright is upgraded significantly.

- Best practices: https://playwright.dev/docs/best-practices
- Writing tests: https://playwright.dev/docs/writing-tests
- Locators: https://playwright.dev/docs/locators
- Assertions: https://playwright.dev/docs/test-assertions
- Fixtures: https://playwright.dev/docs/test-fixtures
- Authentication: https://playwright.dev/docs/auth
- API testing: https://playwright.dev/docs/api-testing
- Mock APIs: https://playwright.dev/docs/mock
- Network handling: https://playwright.dev/docs/network
- Page object models: https://playwright.dev/docs/pom
- Timeouts: https://playwright.dev/docs/test-timeouts
- Retries: https://playwright.dev/docs/test-retries
- Parallelism: https://playwright.dev/docs/test-parallel
- Projects: https://playwright.dev/docs/test-projects
- Continuous integration: https://playwright.dev/docs/ci
- Trace viewer: https://playwright.dev/docs/trace-viewer
- Configuration options: https://playwright.dev/docs/test-use-options
- Web server and base URL: https://playwright.dev/docs/test-webserver
- Clock: https://playwright.dev/docs/clock
- Visual comparisons: https://playwright.dev/docs/test-snapshots

---

## 37. Maintenance

Review this document when:

- Playwright receives a major upgrade
- The test suite adopts a new architecture
- Authentication or test-data strategy changes
- CI execution changes significantly
- Repeated review issues reveal a missing standard
- A new exception becomes common enough to require an explicit rule

Changes to this document should improve reliability and clarity without introducing product-specific requirements.
