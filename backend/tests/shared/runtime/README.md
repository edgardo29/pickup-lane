# Runtime Shared Tests

Owner: Runtime process, lifecycle, health, and deployability contracts

Affected areas:

- FastAPI application lifespan.
- Liveness and readiness probes.
- Database dependency health.
- Runtime release identity exposure.
- SQLAlchemy engine shutdown.

Rules covered here:

- Liveness proves the API process and application lifecycle are running without
  querying PostgreSQL or optional providers.
- Readiness proves the lifecycle is active and the primary PostgreSQL
  dependency is reachable through a minimal probe.
- Health responses are small, uncached, and free of internal diagnostics.
- Failed readiness probes do not permanently mark the process unready.
- Application shutdown disposes runtime database connections through the
  database module's public shutdown helper.

This folder does not prove Render, Neon, edge, worker, rolling-deployment,
container, or provider dashboard settings. Those require external runtime
evidence.
