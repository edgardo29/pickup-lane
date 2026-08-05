# WS02-02 Runtime Lifecycle, Health, and Deployability

Status: implemented for repository source and current tests.

## Scope

WS02-02 establishes source-level FastAPI lifecycle ownership, liveness,
readiness, database shutdown, and non-sensitive release identity behavior.

This pass does not add or change provider deployment configuration. It does not
select worker counts, instance counts, process counts, database pool values,
timeout values, rolling-deployment overlap, provider health-check settings, or
database connection limits.

## Implemented Lifecycle Contract

The FastAPI application now has an explicit lifespan handler.

The application lifecycle is marked active only after the local app object has
been constructed and the server enters lifespan startup. Application import and
app construction do not require PostgreSQL availability and do not initialize
Firebase, Stripe, R2, email, webhooks, or other optional providers.

On shutdown, the lifespan handler marks the lifecycle inactive and calls the
database module's public shutdown helper to dispose the SQLAlchemy runtime
engine. No cleanup behavior is invented for stateless SDK clients or clients
that are constructed per operation.

## Liveness Contract

`GET /live` is the process and lifecycle liveness probe.

It returns a small structured response when the application lifecycle is active.
It does not query PostgreSQL and does not contact Firebase, Stripe, R2, email,
webhooks, or any other external provider. It includes `Cache-Control: no-store`
and exposes only a status and concise non-sensitive release identity.

## Readiness Contract

`GET /ready` is the database-backed readiness probe.

It requires the application lifecycle to be active and verifies the primary
PostgreSQL dependency through the shared minimal database probe. A successful
probe returns ready. An inactive lifecycle or database probe failure returns a
generic not-ready response with HTTP 503.

Database failures are handled without returning exception text, connection
details, hostnames, credentials, stack traces, or provider diagnostics. A failed
probe does not permanently mark the process unready; a later successful probe
can return ready without a restart.

Firebase, Stripe, R2, email, Stripe webhooks, and other optional providers are
not global readiness blockers in this pass.

## Existing Health Behavior

The root endpoint remains a compatibility health surface.

The existing conditional `GET /db-health` diagnostic route remains controlled by
the existing typed setting. It is not the hosting readiness endpoint. When
enabled, it uses the shared database probe, returns `Cache-Control: no-store`,
and hides database exception details behind a generic unavailable response.

## Database Dependency Behavior

The runtime SQLAlchemy engine construction remains compatible with the existing
architecture. WS02-02 does not change pool size, overflow, timeout, recycle,
isolation level, or database URL handling.

The database module now owns engine disposal through a public shutdown helper.
The FastAPI lifespan handler calls that helper during application shutdown.

## Release Identity Behavior

Typed settings now expose a concise runtime release identity. It is stable for
the life of the running deployment and falls back to a safe non-sensitive value
when provider metadata is unavailable.

Health responses expose only this concise release identity, not the full
configuration, provider identifiers, database identifiers, environment-variable
values, credentials, hostnames, or diagnostics.

## Current Tests Added

Current non-legacy runtime tests cover:

- `/live` returns success without executing a database query.
- `/live` uses `Cache-Control: no-store`.
- `/ready` returns success when lifecycle is active and the database probe
  succeeds.
- `/ready` returns HTTP 503 when lifecycle is inactive.
- `/ready` returns HTTP 503 when the database probe fails.
- `/ready` recovers after a previous failed probe.
- readiness and database-health responses hide database exception details.
- release identity is present and limited to the health response shape.
- disabled `/db-health` remains disabled.
- enabled `/db-health` uses `Cache-Control: no-store`.
- application shutdown disposes the SQLAlchemy engine through the public helper.
- FastAPI lifespan does not initialize optional provider clients.

Existing WS02-01 settings and EN-02 observability tests continue to own typed
environment isolation, provider-free import, and release/event metadata safety.

## Post-Merge CI Correction

A post-merge CI false positive was discovered after WS02-03. Alembic startup
loaded minimal database settings and rejected a valid source revision because
the value was passed through generic free-text phone detection.

This was a CI/settings validation defect, not a failed database migration and
not credential exposure.

The correction preserves the global redaction and sensitive-text detector.
Source-revision validation is narrowed structurally: full Git commit SHA values
from source-revision environment variables are accepted as immutable release
identity, while generic release labels and unsafe non-SHA values continue
through the existing safety validation path.

Regression tests cover accepted source revisions, rejected unsafe non-SHA
values, fallback release identity behavior, and the minimal settings path used
by migration startup.

## Repository-Proven Facts

- README documents the intended backend as a Render web service.
- README documents a direct Uvicorn backend start command.
- Uvicorn is present in backend requirements.
- Gunicorn is not present in backend requirements.
- No tracked Render manifest, Procfile, Dockerfile, compose file, Fly config,
  Railway config, or backend runtime manifest exists.
- The app uses FastAPI and SQLAlchemy.
- Alembic uses `NullPool`.
- The runtime app engine uses SQLAlchemy defaults.
- The repository has no worker or scheduler runtime configuration.

## External Evidence Still Required

Repository source does not prove deployed Render or Neon topology.

The following still require external provider evidence or a later approved
technical decision:

- Render service settings and deployed start command.
- Render instance count, process model, autoscaling, and rolling overlap.
- Render health-check path and health-gate behavior.
- Render region, runtime, sandbox, CPU, memory, filesystem, process, and
  platform hardening settings.
- Neon project, plan, connection limit, pooling/proxy mode, reserve, region,
  and operational limits.
- Actual production or staging deployment identity and artifact linkage.
- Runtime startup, shutdown, connection release, and rollback observations.

## Deployment Manifest Decision

No deployment manifest was added because the approved WS02-02 scope is
source-only and repository-proven. A tracked Render manifest, Procfile,
Dockerfile, or equivalent runtime artifact would imply deployment topology,
process, platform, or runtime values that are not yet provider-evidenced.

## Worker, Process, and Pool Values

Worker counts, process counts, instance counts, SQLAlchemy pool sizes, overflow,
wait timeouts, recycle behavior, and platform timeouts were not selected in this
pass. The approved limits method requires evidence before selecting numeric
runtime values.

## Connection-Budget Formula

The deployment-wide database connection budget remains unresolved until Render
and Neon evidence is available.

Sanitized formula:

```text
required_database_connections =
  ((api_instances * api_processes_per_instance)
    * (sqlalchemy_pool_size + sqlalchemy_max_overflow))
  + ((worker_instances * worker_processes_per_instance)
    * (worker_pool_size + worker_max_overflow))
  + migration_connection_allowance
  + monitoring_connection_allowance
  + rolling_deployment_overlap_allowance
  + operational_reserve

required_database_connections <= provider_connection_limit
```

Every variable in that formula still requires provider or owner-approved
evidence before a concrete value can be selected.
