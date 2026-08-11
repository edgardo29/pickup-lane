# Backend Test Compliance Checker

## Purpose

The backend-test compliance checker enforces the backend testing standards defined in `docs/agent-notes/backend-testing.md`.

It checks exactly one target at a time:

- one specific backend `test_*.py` file
- one leaf page/domain test directory

It does not scan the entire backend test suite.

## Production-Readiness Evidence Rules

The production-readiness taxonomy builds around this checker. It does not
replace it.

Current backend evidence uses these categories:

- Checker-certified leaf-domain tests: organized page or shared-domain tests
  with a `_backend_test_contract.py` that pass this checker for the selected
  target.
- Organized but not yet checker-certified tests: current page or shared-domain
  tests that live in the organized tree but do not yet have a contract for their
  leaf target.
- Shared backend tests: tests for rules used by more than one page or feature.
- Checker and compliance self-tests: tests for the backend test harness itself,
  not application-domain evidence.
- Legacy historical tests: old valid coverage under `backend/tests/legacy/`.

My Games is currently the contract-certified pilot:

- `backend/tests/pages/my_games/_backend_test_contract.py`
- `backend/tests/pages/my_games/`

Organized tests without a contract are not yet checker-certified for their
domain. Empty categories must not be presented as existing coverage.

`backend/tests/legacy/` is historical. It can contain useful scenarios for
future migration, but it does not count as current production-readiness evidence
and ordinary current-test discovery excludes it. Do not delete, move, rewrite,
or count legacy tests as part of EN-01.

Standard backend tests must use synthetic data and must not use development,
staging, or production resources. Backend test URLs must use a PostgreSQL
SQLAlchemy driver, such as `postgresql://` or `postgresql+psycopg://`. The
dedicated PostgreSQL test database name is exactly `pickup_lane_test_db`; a
database is not accepted merely because its name contains `test`.

Standard backend tests must not make live provider calls. Firebase, Stripe, R2,
email, and other provider behavior must be mocked at the application-owned
boundary unless a later provider-integration suite has explicit approved
sandbox or emulator configuration. Ordinary backend tests may open network
sockets only to the configured PostgreSQL test host and exact port from the
approved `DATABASE_URL`; EN-01 does not perform protocol inspection after that
host-and-port decision. Every other network endpoint is prohibited.

Retries are diagnostic only. A retry success does not erase the original
failure or become clean evidence by itself. Flaky tests require an owner, a
reason, and a repair or removal plan.

## Required Contract

Each checked leaf page/domain directory requires `_backend_test_contract.py`.

The contract is the machine-readable review record for the directory. It represents finalized requirements, authoritative state matrices, scenario applicability, ownership decisions, structured effects, exact time boundaries, gaps, conflicts, and review decisions that cannot be reliably derived from the test AST alone.

Example only: `pages/my_games/_backend_test_contract.py`.

## Static And Contract Usage

Run from the repository root:

```bash
backend/.venv/bin/python \
  backend/tests/check_backend_tests.py \
  pages/my_games
```

One-file example:

```bash
backend/.venv/bin/python \
  backend/tests/check_backend_tests.py \
  pages/my_games/test_api_contract.py
```

Single-file checks load the containing directory contract and report file-level compliance only. They do not certify the full feature or domain.

## Runtime Usage

Runtime mode requires:

- a dedicated test database
- `APP_ENV=test`
- `DATABASE_URL` pointing to that test database
- synthetic local-only backend secrets for settings that tests exercise
- the required tables/schema already existing

Example:

```bash
APP_ENV=test \
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/pickup_lane_test_db' \
INBOX_TOKEN_SECRET='synthetic-inbox-test-token' \
backend/.venv/bin/python \
  backend/tests/check_backend_tests.py \
  pages/my_games \
  --runtime
```

Never use development, staging, or production databases.

The checker does not automatically create, migrate, reset, drop, or truncate databases. Database-changing commands still require explicit user approval.

## Mutation Hardening

Mutation testing is optional targeted hardening. It is not required for normal directory `PASS`.

Example:

```bash
APP_ENV=test \
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@localhost:5432/pickup_lane_test_db' \
INBOX_TOKEN_SECRET='synthetic-inbox-test-token' \
backend/.venv/bin/python \
  backend/tests/check_backend_tests.py \
  pages/my_games \
  --runtime \
  --mutations
```

Mutation status is reported separately:

- `NOT_REQUESTED`: mutation hardening was not requested.
- `PASSED`: requested mutation hardening completed with no surviving protected mutants.
- `FAILED`: protected mutants survived.
- `DEFERRED`: mutation hardening was not completed, for example due to runtime caps.
- `UNSUPPORTED`: mutation hardening cannot run with the declared target, tooling, or safety configuration.

## Accepted Targets

- one `test_*.py` file
- one leaf page/domain directory

## Rejected Targets

- `.`
- `backend/tests`
- `pages`
- `shared`
- `support`
- broad `legacy`
- multiple target paths
- `conftest.py` or support/helper files as the direct target

## Result Meanings

- `PASS` / exit code `0`: no failures or blockers remain for the requested scope.
- `FAIL` / exit code `1`: definite violations were found.
- `BLOCKED` / exit code `2`: required evidence or review is missing.
- `USAGE_ERROR` / exit code `3`: the CLI target or options are invalid.
- `INTERNAL_ERROR` / exit code `4`: the checker itself crashed.

## Starting A New Page Or Domain

The checker validates backend testing work, but it does not discover every feature requirement by itself. The finalized page/domain specification, `docs/agent-notes/app-testing-standards.md`, and the page Markdown checklist define the required testing surface.

For every new page or backend domain, read:

- the page or domain specification, such as `docs/agent-notes/browse-games.md`
- `docs/agent-notes/app-testing-standards.md`
- `docs/agent-notes/backend-testing.md`
- `backend/tests/README.md`
- relevant routes, services, schemas, models, migrations, provider adapters, workers, infrastructure, and existing tests

For this project, the backend testing wave includes every applicable non-UI area identified by `docs/agent-notes/app-testing-standards.md`, including:

- API contracts
- authentication and authorization
- security and private-data exposure
- service and domain behavior
- PostgreSQL behavior and persisted effects
- pagination, sorting, cursors, filtering, caching, and time boundaries
- transactions, rollback, idempotency, retries, and concurrency when applicable
- provider boundaries, webhooks, workers, and infrastructure when applicable

Required sequence:

1. Review and correct the page specification.
2. Expand the page Markdown backend checklist with all applicable scenarios, edge cases, exclusions, safeguards, and not-applicable decisions.
3. Review existing tests against that checklist.
4. Create or update the leaf `_backend_test_contract.py`.
5. Run checker static/contract mode.
6. Correct genuine specification, production-code, contract, or test gaps.
7. Run checker runtime mode using the dedicated PostgreSQL test database.
8. Update the page Markdown checklist with completed scenarios, verification counts, remaining gaps, and the backend completion statement.
9. Do not claim completion unless the checker passes and no required backend checklist items remain incomplete.

## Recommended Workflow

1. Read the finalized page/domain specification, `docs/agent-notes/app-testing-standards.md`, `docs/agent-notes/backend-testing.md`, this README, and the page-specific Markdown checklist.
2. Create or update the leaf directory `_backend_test_contract.py` from the corrected specification and checklist.
3. Run static/contract mode.
4. Correct genuine findings in the right source: specification, contract, tests, production behavior, or checker.
5. Run runtime mode with the safe dedicated test database.
6. Update the page-specific Markdown checklist with completed scenarios, verification counts, remaining gaps, and the backend completion statement.
7. Use mutation testing only when useful as optional hardening.
8. Do not claim completion while required failures, blockers, or backend checklist gaps remain.

## Maintenance Rule

Do not modify the checker merely to make a target pass.

Modify checker code only when a confirmed checker defect or false positive has been demonstrated. Production behavior, tests, contracts, or specifications must be corrected based on the actual source of the problem.
