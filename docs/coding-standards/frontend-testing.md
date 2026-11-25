# Frontend Testing

How frontend tests are organized, written, and run in Pickup Lane.

## 1. Purpose

Frontend tests prove what each page shows and does, scenario by scenario
(Section 5 of each page specification under
`docs/production-readiness/feature-pages/pages/`). Backend behavior, such as
which games the API returns, is proved by backend tests; see
`backend-testing.md`.

A test is written from the specification, not from what the code currently
does. If the code and the specification disagree, report it; do not change the
test to match the code.

## 2. Tools

| Tool | Used for |
|---|---|
| Vitest | Runs the tests (the frontend's equivalent of pytest) |
| React Testing Library | Renders a page or component and interacts with it the way a user would |
| jsdom | The fake browser the tests run in; no real browser or backend is needed |
| Playwright | Full workflows in a real browser with the real backend; used sparingly |

## 3. Layout

Frontend tests live in `frontend/tests/`, and Playwright workflows in
`frontend/e2e/`.

```text
frontend/tests/
  setup.js          runs before every test: adds page assertions, clears the page after each test
  backendFields.js  checks a made-up API answer against a page's backend_fields.json
  backend_fields.test.js  proves that check rejects answers that differ from the backend
  pages/<page>/     one folder per page specification, e.g. pages/browse_games/
    backend_fields.json  the fields the backend sends for the endpoints this page
                         uses; saved from the backend, never edited by hand
frontend/e2e/       Playwright workflows, one `<workflow>.spec.js` file each
```

A page folder is named after the page specification's file name, without
the page ID and `-spec.md`, and with underscores instead of dashes:
`F15-browse-games-spec.md` becomes `pages/browse_games/`.
Create a page folder only when its first test is written. Within a page folder,
use one file per topic, named `<topic>.test.jsx`.

The Vitest settings are in `frontend/vitest.config.js`. The Playwright
settings are in `frontend/playwright.config.js`; they start the local backend
and frontend, use the development database, and run in the Google Chrome
installed on the computer.

## 4. Where a test goes

- Every test lives in the folder of a page under `pages/`. The one exception is
  `backend_fields.test.js`, which tests the shared answer check.
- Each page tests its own scenarios in its own folder, even when another page
  already tests the same behavior.
- Use Playwright only for a workflow that crosses pages and needs the real
  backend, such as booking a game end to end.

## 5. Page and scenario in the test name

Every test that proves a page scenario starts its name with the page ID from
`docs/production-readiness/feature-pages/page-inventory.md` and the Section 5
scenario number:

```jsx
it('F15-36: invalid date link is replaced with today', async () => {
  ...
})
```

A test that proves several scenarios lists each: `'F15-18, F15-23: ...'`.

To find every test for a page or scenario, search the source:

```bash
rg "F15-" frontend/tests frontend/e2e
```

## 6. Running tests

Run from the `frontend/` folder.

| Task | Command |
|---|---|
| Run all frontend tests | `npm run test` |
| Run one page's tests | `npm run test -- pages/browse_games` |
| Run one test, e.g. for a failure check | `npm run test -- pages/payment_methods/managing_cards.test.jsx -t "F13-4: after removal, the card is no longer listed"` |
| Re-run tests on every file change | `npm run test:watch` |
| Lint frontend code and tests | `npm run lint` |
| Run Playwright workflows | `npm run test:e2e` |
| Run Playwright workflows in a visible browser | `npm run test:e2e:headed` |
| Open Playwright's interactive UI | `npm run test:e2e:ui` |

Playwright runs only when the user explicitly asks for it.

## 7. How to write a test

- **Name:** start with the page and scenario, then state the result, e.g.
  `'F15-17: a day with no games shows the empty message'`.
- **Use the page the way a user does.** Find elements by role, label, or
  visible text (`screen.getByRole('button', { name: 'Load More' })`), not by CSS
  class or internal structure. Use `@testing-library/user-event` for clicks and
  typing.
- **Fake the API, not the page.** Replace the page's API module with
  `vi.mock(...)` and decide in each test what the backend returns, including
  errors and slow or late responses. Never call the real backend.
- **Made-up answers must match the backend.** After each test, the page's test
  kit checks every answer the faked API gave the page against the page's
  `backend_fields.json`. A missing field, an extra field, or a wrong kind of
  value fails the test. Don't change an answer after the page has received it.
  - When the backend changes what an endpoint sends, the backend test in
    `backend/tests/frontend_fields/` fails. Re-save the files with
    `backend/.venv/bin/python -m backend.tests.frontend_fields.save` (from the
    repository root), then update the made-up answers the check rejects.
  - When a page's tests fake a new endpoint, add it to `PAGE_ENDPOINTS` in
    `backend/tests/frontend_fields/save.py` and re-save.
- **Control time.** Use `vi.useFakeTimers()` for refresh intervals and other
  timing, and advance time on purpose (`vi.advanceTimersByTime(60_000)`).
- **Check the result the user sees,** such as text, badges, disabled controls,
  and the page link. Check the page link when the scenario is about the URL or
  browser history.
- **One behavior per test.** Keep setup visible in the test; move setup into a
  helper only when several tests need it.
- **No dependence on test order.** Each test starts with a blank page.

### Setting up a new page's tests

Do these once, in order, before writing the page's first frontend test:

1. **List the page's endpoints.** In `backend/tests/frontend_fields/save.py`,
   add a line to `PAGE_ENDPOINTS` naming every backend endpoint the page's
   tests fake, e.g. `"game_details": ["GET /games/{game_id}"]`.
2. **Save the page's fields file.** From the repository root, run
   `backend/.venv/bin/python -m backend.tests.frontend_fields.save`. It creates
   `frontend/tests/pages/<page>/backend_fields.json`.
3. **Create the page's test kit,** e.g. `pages/<page>/<page>TestKit.jsx`, with
   the helpers that build the page's made-up answers. Copy the `afterEach`
   check block from `pages/browse_games/browseTestKit.jsx` and point it at the
   page's faked API function, `backend_fields.json`, and endpoint. Without this
   block, the page's made-up answers are never checked.
4. **Write the tests** using the test kit, then run the frontend tests and the
   backend tests.

## 8. Old tests

The previous frontend tests remain in `frontend/tests_archive/` as reference
only. They are not part of the frontend test suite, and lint skips them.

## 9. Rules for AI agents

- Do not run tests unless the user explicitly says to. Do not run Playwright
  unless the user explicitly asks for Playwright or end-to-end tests.
- Reading files, searching, and lint checks are always allowed.
- After running tests, report the exact commands, the results, and anything
  not run.
