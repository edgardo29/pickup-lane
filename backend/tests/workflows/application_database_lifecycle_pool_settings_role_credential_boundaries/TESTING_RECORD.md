# Testing Record: WS04-01A - Application Database Lifecycle, Pool Settings, And Role-Credential Boundaries

## Scope

This record covers trusted local evidence for `WS04-01A`, the first child of
`WS04-01`. The evidence proves the backend application contract for database
URL validation, per-process SQLAlchemy pool settings, request-session
lifecycle, health/shutdown behavior, migration URL separation, side-effect-free
model metadata loading, and backend-only database configuration ownership.

This pass does not prove actual production provider capacity, deployed process
counts, final deployment-wide connection-budget math, concrete production
database roles, or real provider grants. Those remain with later `WS04-01`
children.

## Requirement Mapping

| Requirement | Evidence |
| --- | --- |
| `WS04-01A-R1` | Settings tests prove safe application database URL parsing remains intact, `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` are parsed as a required pair in preview/staging/production, local/test/CI can omit both, invalid values are rejected, and errors name settings without echoing URL values. |
| `WS04-01A-R2` | Engine tests prove configured pool size, maximum overflow, pool wait, and zero checked-out connections reach SQLAlchemy, while local/test/CI still work without optional pool values. |
| `WS04-01A-R3` | Request-session tests prove success closes without rollback, ordinary exceptions roll back and close, and cancellation closes while propagating as cancellation. |
| `WS04-01A-R4` | Engine/session and health/shutdown tests prove import/engine construction does not open a connection, health failures stay generic, shutdown disposes the engine, and existing timeout behavior remains compatible. |
| `WS04-01A-R5` | Migration tests prove application settings do not require `MIGRATION_DATABASE_URL`, production-like migrations require it, local/test/CI may fall back to `DATABASE_URL`, invalid migration URLs fail safely, and Alembic uses `NullPool`. |
| `WS04-01A-R6` | Metadata tests prove Alembic no longer imports the application database module, the shared base lives on the side-effect-free metadata path, and the current exported model set remains registered. |
| `WS04-01A-R7` | Backend-only tests prove database-related env names are registered in backend settings, documented with sanitized placeholders, absent from frontend text files, and not added as literal credential-bearing URLs. |

## Evidence Quality Notes

- Tests use only synthetic, non-credential database URLs and do not contact
  production infrastructure.
- The focused workflow suite tests application-owned source behavior; it does
  not claim production provider capacity or production role/grant evidence.
- Existing operation-timeout tests remain the compatibility evidence for the
  real checked-out PostgreSQL statement and lock timeout behavior.
- The runtime topology compatibility test treats application pool settings as
  per-process application configuration, not as final deployment-wide provider
  budget proof.
- Checker `PASS` results are structural and traceability checks; semantic
  adequacy comes from the focused behavior assertions and this record.

## Validation Results

- Focused WS04-01A evidence: `29` tests passed.
- Operation-timeout compatibility: `95` tests passed.
- Runtime compatibility: `31` tests passed.
- Settings compatibility: `75` tests passed.
- WS04-01A requirement mapping/domain checker: `PASS`.
- Repository suite checker: `PASS`.

## Boundaries

- No production provider facts, provider connection limits, deployed instance
  counts, worker-process counts, rolling-overlap math, monitoring reserve, or
  production role/grant assignments are proven by this pass.
- Final deployment-wide connection budget and concrete production database
  permission verification remain with later `WS04-01` children.

## Final Self-Review

- This record contains no literal credentials, credential-bearing URLs, private
  keys, tokens, personal/payment data, provider-private values, raw sensitive
  logs, local machine paths, usernames, session state, or internal chat
  material.
- Requirement IDs preserve the meanings frozen in the approved WS04-01A plan.
- Remaining boundaries are concrete and do not overclaim local pytest evidence.
