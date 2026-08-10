# EN-01 Backend Testing Architecture Redesign

Status: Phase 2 backend test infrastructure cleanup.

Branch: `pr/EN-01-backend-test-redesign`

Baseline: `d4d1d5fe49e2888ccbb09a68a0500c5d9e71786e`

Controls: TST-001, TST-003, TST-004, TST-010, TST-011

## Audit Result

The original EN-01 pass established useful safety boundaries: exact dedicated
PostgreSQL test database naming, synthetic data expectations, standard-suite
provider isolation, legacy exclusion from current evidence, diagnostic-only
retry policy, and artifact sensitivity.

Those safety requirements remain durable. EN-01 did not close broad current
coverage, provider sandbox, browser, migration, deterministic concurrency,
security, release, or CI evidence.

## Why Reconsider The Architecture

The first backend test architecture treated `pages/` and `shared/` leaf
directories plus `_backend_test_contract.py` as the future certification model.
That made the checker responsible for business completeness judgments and
large Python contracts.

The redesign narrows the checker to mechanical validation and moves future
business traceability into lightweight source-linked domain records.

## Preserved Safety Requirements

- Standard backend pytest uses `APP_ENV=test`.
- Standard backend tests use the exact `pickup_lane_test_db` PostgreSQL test
  database.
- Standard backend tests mock providers at the application-owned boundary.
- Provider sandbox/emulator/resource verification stays separate.
- Legacy tests are not current production-readiness evidence.
- Retries are diagnostic only and cannot hide recurring failures.
- Failure artifacts must be sanitized and access-controlled.
- Coverage is risk-based, not governed by one universal percentage.

## Superseded Optional Choices

- `pages/` is no longer the preferred future backend ownership model.
- `shared/` is no longer the preferred cross-domain bucket.
- Leaf-directory checker certification is not the future completion gate.
- `_backend_test_contract.py` is not required for future rebuilt domains.
- Mutation execution and runtime pytest execution are not part of checker
  `PASS`.
- The checker does not certify business completeness.

Existing active contract files remain physically untouched until their owning
areas are reviewed.

## Approved Domain-First Model

Future backend behavior tests are organized by owning domain, such as `auth`,
`users`, `games`, `bookings`, `need_a_sub`, `payments`, `admin`,
`moderation`, `chat`, `notifications`, and `venues`.

Platform-level tests may live in `infrastructure/`. Real sandbox, emulator, or
test-resource checks may live in `integrations/`. Reusable test mechanics live
in `support/`.

Directories are created only when they have reviewed content.

## Lightweight Traceability Decision

Substantial rebuilt domains use:

- `TESTING.md` for human-readable intent, risks, applicability notes, and gaps.
- `testing_manifest.yaml` for small machine-readable source-linked
  traceability.

The manifest points to authoritative product and production-readiness
documents. It does not reproduce full specifications, large state matrices, or
scenario inventories.

## Checker Simplification Decision

The active checker validates narrow mechanics only:

- pytest strict marker configuration
- approved execution marker usage
- skip/xfail documentation policy
- lightweight traceability manifest syntax/schema where provided
- support dependency direction

A checker `PASS` means only that these checked mechanical rules passed.

## Phase 1 Scope

Phase 1 updates backend testing documentation, marker configuration, checker
tooling, traceability template/schema convention, checker self-tests, and this
redesign record.

No product tests are moved or rewritten. No application routes, services,
schemas, models, migrations, frontend tests, Playwright tests, provider suites,
CI gates, DB cleanup rewrite, root fixture overhaul, or network-guard rewrite
are included.

## Phase 2 Scope

Phase 2 keeps the approved domain-first architecture and updates only backend
test infrastructure mechanics.

The root `conftest.py` is narrowed to global orchestration: synthetic test-safe
settings, settings-cache reset, exact `APP_ENV=test` validation, exact
`pickup_lane_test_db` PostgreSQL validation, the shared test client, dependency
override cleanup, network guard installation, and DB cleanup orchestration.

The manual `TEST_TABLES` inventory is replaced by SQLAlchemy metadata-derived
cleanup targets. Before truncation, the connected PostgreSQL schema is checked
against those targets and only narrow non-application exclusions such as
`alembic_version` are allowed. Cleanup uses quoted metadata table identifiers
with `TRUNCATE ... RESTART IDENTITY CASCADE` before and after DB-using tests
under the existing single-worker advisory lock.

The standard-suite network guard remains local pytest infrastructure. It allows
only the configured dedicated PostgreSQL test database host and port and blocks
provider or arbitrary external sockets during ordinary backend tests.

No product tests are moved or rewritten. No product coverage is added. No
application routes, services, schemas, models, migrations, frontend tests,
Playwright tests, provider integration suites, broad CI gates, parallel
database naming, or DB auto-create/drop behavior are included.

## Remaining Deferrals After Phase 2

- Provider fake architecture.
- Current-test inventory and domain reconstruction.
- CI suite selection and release evidence gates.
- Provider integration suites.
- Deterministic migration, concurrency, worker, webhook, privacy, and recovery
  suites.

## Progressive Domain Reconstruction Rule

Later domain work must first read authoritative current requirements and
supported production behavior, independently identify required backend
scenarios, choose domain ownership and test layer, then inspect existing active
tests only as possible evidence.

Existing tests never define the product contract by themselves. Each existing
test is classified as `KEEP`, `MOVE`, `REWRITE`, `REPLACE`, or `DELETE` during
the owning domain review.
