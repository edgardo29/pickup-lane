# Backend Testing

How backend tests are organized, written, and run in Pickup Lane.

## 1. Purpose

Backend tests prove three things:

- each page does what its page specification says, scenario by scenario
  (Section 5 of each page specification under
  `docs/production-readiness/feature-pages/pages/`);
- shared protections, such as login checks, the admin gate, security headers,
  and request size limits, behave as the production requirements state;
- business rules keep their guarantees, such as concurrency, transactions,
  and every allowed state change.

A test is written from the specification or requirement, not from what the
code currently does. If the code and the specification disagree, report it;
do not change the test to match the code.

## 2. Layout

All backend tests live in `backend/tests/`. Pytest settings are in
`pytest.ini` at the repository root.

```text
pytest.ini          pytest settings and registered markers
backend/tests/
  conftest.py       test setup: synthetic settings, test-database check,
                    schema reuse or rebuild, per-test rollback, and the
                    client, db, committed_db, and clock fixtures
  factories.py      builds test data: make_user, make_game, make_booking, ...
  migrations/       the standard pytest-alembic migration checks
  cloudflare_r2/    live check against a real Cloudflare R2 test bucket
  frontend_fields/  saves each frontend page's backend_fields.json and checks
                    that every saved file still matches the backend
  pages/<page>/     one folder per page specification, e.g. pages/browse_games/
  platform/<area>/  shared protections, e.g. platform/authentication/ (archived, see below)
  domains/<area>/   business-rule guarantees, e.g. domains/bookings/
```

A page folder is named after the page specification's file name, without
the page ID and `-spec.md`, and with underscores instead of dashes:
`F15-browse-games-spec.md` becomes `pages/browse_games/`.
Create any folder only when its first test is written.

## 3. Where a test goes

| Folder | What goes there | Source of expected behavior |
|---|---|---|
| `pages/<page>/` | What a page does: its Section 5 scenarios | The page specification |
| `platform/<area>/` | Shared protections and HTTP behavior: authentication, the admin gate, error responses, headers, size limits, CORS, rate limits | The production requirements and coding standards |
| `domains/<area>/` | A business rule's own guarantees: concurrency, transactions, every allowed and forbidden state change, repeated or out-of-order events | The production requirements |

- Each page tests its own scenarios in its own folder, even when another page
  already tests the same behavior.
- A platform test proves the protection itself and which routes it covers. It
  is not a feature test for every route. Test each distinct path once (normal
  response, error, rejected login, boundary value), not once per page.
- `platform/` is archived while the feature pages are built: `pytest.ini`
  ignores it, so its tests do not run. It comes back in the production launch
  passes, which update the tests that broke and add the missing ones. Do not
  add tests to it until then.
- A domain test checks the rule's guarantees whether or not a page also uses
  the rule. Do not repeat in `domains/` a check a page test already makes.

## 4. The page marker

Every test that proves a page scenario carries the page marker with the page
ID from `docs/production-readiness/feature-pages/page-inventory.md` and the
Section 5 scenario numbers it proves:

```python
@pytest.mark.page("F15", 7)
def test_game_disappears_from_browse_at_registration_cutoff(client): ...
```

A test can carry several page markers when several pages rely on it:

```python
@pytest.mark.page("F15", 9)
@pytest.mark.page("F16", 4)
```

To find every test for a page or scenario, search the source:

```bash
rg 'page\("F15"' backend/tests
```

Platform and domain tests carry no page marker. Each one cites the
requirement it proves in its docstring, so it can be found the same way:

```python
def test_oversized_json_body_is_rejected_before_parsing(client):
    """P06.R14: one byte over the ordinary JSON limit returns 413."""
```

```bash
rg 'P06\.R14' backend/tests
```

The registered markers are `page` and `live` (see Section 7). Pytest rejects
any other marker.

## 5. Running tests

Run every command from the repository root.

| Task | Command |
|---|---|
| Run all backend tests | `backend/.venv/bin/pytest` |
| Run one page's tests | `backend/.venv/bin/pytest backend/tests/pages/browse_games` |
| Run one test, e.g. for a failure check | `backend/.venv/bin/pytest "backend/tests/pages/payment_methods/test_default_and_removal.py::test_an_expired_card_can_be_removed"` |
| Run the migration checks | `backend/.venv/bin/pytest backend/tests/migrations` |
| Also run live checks | `backend/.venv/bin/pytest --live` |
| Force a clean rebuild of the test database | `backend/.venv/bin/pytest --rebuild-test-db` |
| Re-save the frontend pages' backend fields files | `backend/.venv/bin/python -m backend.tests.frontend_fields.save` |

Every run:

1. Uses synthetic settings only. `backend/.env` is not loaded, so real keys
   and the development database never reach a test. The only value read from
   it is `TEST_DATABASE_URL`, and an environment variable of the same name
   (used by CI) takes precedence.
2. Refuses to start unless the database is `pickup_lane_test_db`.
3. Waits for any other run using the test database to finish, so two runs
   never share it at once.
4. Reuses the test database's schema when all of these hold, and otherwise
   rebuilds it from the Alembic migrations:
   - it was built from the current migration files (a fingerprint of
     `backend/alembic/env.py` and every file in `backend/alembic/versions/`
     is recorded at each rebuild, outside the rebuilt schema);
   - its applied migration matches the latest migration;
   - every table is empty, so nothing is left from an earlier run, such as
     one stopped in the middle of a test.

   `--rebuild-test-db` always rebuilds. A rebuild never needs to be run by
   hand otherwise.
5. Runs each test in a transaction that is rolled back afterward.
6. Blocks network access to anything other than this machine
   (pytest-socket).

The migration checks use `pickup_lane_migration_test_db`, on the same server
with the same credentials. Each check empties it before it starts.

Both test databases must exist before the first run. Creating them is in
`database.md`.

## 6. How to write a test

Most tests use three fixtures from the root `conftest.py`:

- `client` calls the API.
- `db` is a database session for building data with `backend.tests.factories`.
  Everything the test and the API write is rolled back when the test ends.
- `clock` freezes the current time at a fixed moment (noon on 2026-06-15 in
  America/Chicago). `clock.now` reads it, and `clock.move_to(...)` or
  `clock.advance(...)` moves it during the test.

```python
@pytest.mark.page("F15", 7)
def test_game_disappears_exactly_at_the_registration_cutoff(clock, db, client):
    make_game(db, starts_at=clock.now - timedelta(minutes=5))

    response = client.get("/games/browse")

    assert response.json()["games"] == []
```

Add a factory to `factories.py` only when a test needs a new kind of row, and
give it defaults that produce a valid, ordinary record.

- **Name:** state the scenario and the result, e.g.
  `test_expired_hold_does_not_reserve_a_spot`.
- **One behavior per test.** Use `pytest.mark.parametrize` only when every case
  has the same setup, action, and expected result.
- **Check exact results:** status code, response fields and values, ordering,
  and totals. Never only "it did not fail".
- **After a successful change,** check the database actually changed.
- **After a rejected request,** check that nothing was created or changed.
- **Cover every allowed value** when behavior depends on a status, role, or
  type. List the values from the model, not from memory.
- **Control time.** Use the `clock` fixture and derive other times from
  `clock.now`. Test exact boundaries (before, at, after) when a rule depends on
  time.
- **No `sleep()`, no dependence on test order, no leftover data.**
- **Keep setup visible** in the test. Move setup into a fixture only when
  several tests need it.

### `db` or `committed_db`

Use `db`. Every database session the app opens during the test, including API
requests and the admin audit log's own session, joins the test's transaction,
and the whole transaction is rolled back at the end.

Use `committed_db` instead only when the test needs data shared across
separate database connections, such as two requests racing for the last spot.
Its writes are really committed, and every table is emptied after the test,
which is slower. A test uses one or the other, never both.

### Database time and `created_at` under `db`

Inside one transaction PostgreSQL's `now()` stays at the moment the
transaction began, and `clock` does not change it. So under `db`:

- Code that reads the time from the database (`select(func.now())`, used by
  checkout, waitlist, payments, Stripe webhooks, and durable jobs) sees one
  fixed real time for the whole test, not `clock.now`. Build that test's data
  relative to the database time.
- Every row created in one test gets the same `server_default` `created_at`.
  When a test depends on creation order, set `created_at` explicitly.

## 7. Outside services

Ordinary tests never call Stripe, Firebase, or Cloudflare R2, and the network
block makes such a call fail. Replace the service with a fake through
`app.dependency_overrides` or `monkeypatch`.

The root `conftest.py` provides two such fakes. The `firebase` fixture answers
sign-in checks. The `stripe` fixture turns payments on and answers the Stripe
calls that checkout, the waitlist, and saved-card management make:

- Set `stripe.confirm_status` to choose how a payment confirmation turns out,
  and call `stripe.report(db, payment, status)` to simulate Stripe's webhook
  reporting a payment's new status.
- Call `stripe.enter_card(setup_intent_id, fingerprint=...)` to simulate the
  player entering a card in Stripe's form. `stripe.setup_intents`,
  `stripe.customer_defaults`, and `stripe.detached` record what Stripe was
  asked to do.
- Add a Stripe call's name to `stripe.failing`, such as
  `"detach_payment_method"`, to make that call fail.

The `stripe` fixture skips the check that asks Stripe whether a saved card is
still valid (`verify_saved_payment_method_with_stripe`); a test of that check
turns it back on with `monkeypatch`. Publish fees call Stripe from their own
module, which the fixture does not cover.

A check against the real service is marked `live` and `enable_socket`. It runs
only with `pytest --live`, on purpose, and uses separate test credentials,
never the app's own. The Cloudflare R2 check reads the `R2_TEST_*` values
listed in `backend/.env.example` and uses a dedicated test bucket.

## 8. Migration checks

`backend/tests/migrations/` runs the four standard pytest-alembic checks:

- the migrations form one line, with no forks;
- every migration applies, from empty to the latest;
- the migrated schema matches the models;
- every migration can be undone.

The schema comparison does not cover `CHECK` constraints. Prove those with a
behavior test that saves an invalid row and expects it to be rejected.

## 9. CI and the pre-commit hook

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and pull request
to `main` and `develop`, and runs the jobs only for the areas that changed:

- **Backend:** `ruff check .` and `ruff format --check .`.
- **Frontend:** lint and the build.
- **Secret scan:** Gitleaks, on every run.

CI does not run the tests. Run the relevant tests while working on a feature,
and the full backend and frontend suites before opening a pull request.

`CI Required` passes only when every job that ran passed.

The pre-commit hook runs Gitleaks, `ruff check`, and `ruff format` on the
staged files before every commit. Set it up once per clone:

```bash
backend/.venv/bin/pre-commit install
```

Ruff settings are in `ruff.toml` at the repository root.

## 10. Old tests

The previous test suite remains in `backend/tests_archive/` as reference only.
It does not run, and Ruff skips it.

When writing tests for a page, search the old tests for the page's endpoints
and backend functions, and check whether they covered a case the new tests
should also cover. Do not copy old tests without checking them against the page
specification.

## 11. Rules for AI agents

- Do not run tests, rebuild databases, run migrations, or start the application
  unless the user explicitly says to. Running pytest can rebuild the test
  database schema.
- Reading files, searching, and compile checks are always allowed.
- After running tests, report the exact commands, the results, and anything
  not run.
