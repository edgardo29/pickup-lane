# WS02-01 Typed Settings and Environment Isolation

Status: implemented for repository source and current tests.

## Scope

WS02-01 establishes one authoritative backend settings layer in `backend/settings.py`.
It normalizes `APP_ENV`, validates backend-private configuration before app
startup, and keeps provider SDK calls lazy.

Canonical backend environments are:

- `local`
- `test`
- `ci`
- `preview`
- `staging`
- `production`

Preview, staging, and production are production-like environments. They must
receive settings from deployed environment injection, not ignored local `.env`
files.

When `APP_ENV` is unset outside CI and no deployed-runtime marker is present,
the backend defaults to `local` for development compatibility. CI defaults to
`ci` when `CI` is set, and the repository workflow also sets `APP_ENV=ci`
explicitly.

## Implemented Controls

- `APP_ENV` is typed and case-normalized.
- Blank or unknown `APP_ENV` values fail settings validation.
- Detectable deployed runtimes must explicitly set `preview`, `staging`, or
  `production`.
- `DATABASE_URL` must use a PostgreSQL SQLAlchemy driver and include a host and
  database name.
- Test and CI database URLs must use exactly `pickup_lane_test_db`.
- Production-like database URLs reject localhost and obvious non-production
  database names.
- CORS origins are normalized, deduplicated, and validated as origins only.
- Wildcard CORS origins with credentials are rejected.
- Production-like CORS rejects localhost and requires explicit origins.
- Public API docs default off in production-like environments and cannot be
  enabled in production.
- DB health exposure is environment-aware, but health/readiness semantics remain
  deferred to WS02-02.
- Stripe payments require explicit private Stripe settings only when enabled.
- Stripe currency is constrained to USD.
- Firebase Admin credential forms are validated without provider initialization.
- Cloudflare R2 settings reject partial configuration, invalid endpoints,
  invalid image MIME types, and non-positive limits.
- R2 endpoint derivation remains deterministic from `R2_ACCOUNT_ID`.
- `INBOX_TOKEN_SECRET` no longer falls back to `DATABASE_URL`.
- `INBOX_TOKEN_SECRET` must be independent from the database URL and other known
  private provider credentials.
- `backend/.env.example`, README deployment notes, and backend CI environment
  identity were updated to match the typed settings boundary.
- EN-02 telemetry labels now allow `preview` as an approved environment value.

## Safety Boundaries

Settings parsing does not contact the database or any provider. Existing
database engine creation remains import-time but non-connecting; broader runtime
process, lifecycle, readiness, and pool behavior belong to WS02-02.

Firebase, Stripe, and R2 provider operations remain lazy and are not contacted
during settings validation.

Frontend `VITE_*` browser configuration remains frontend-owned and is not moved
into backend-private settings.

## Deferred Work

- Runtime process, lifecycle, readiness, and deployment health semantics.
- Proxy, host, TLS, response security headers, and edge/origin topology.
- Provider dashboard proof, production secret-store evidence, rotation, and
  revocation exercises.
- CI redesign, branch protection, secret scanning, and release gates.
- Database pool topology, worker/runtime topology, and migration lifecycle
  changes.
- Browser-public Firebase and Stripe configuration validation beyond README
  separation notes.

## Evidence

The pass adds focused current backend tests for settings construction, env
identity, database URL validation, CORS validation, API docs and DB health flags,
Stripe/Firebase/R2 boundaries, inbox token independence, example parity, and app
startup integration.

Validation evidence must be reported in the pull request body with the actual
commands and results from the implementation branch.
