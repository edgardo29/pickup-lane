# WS04-01A - Application Database Lifecycle, Pool Settings, And Role-Credential Boundaries

This pass defines how the backend creates and uses PostgreSQL connections,
bounds each application's connection pool, manages request sessions, and keeps
migration database access separate from request-serving access.

## 1. What This Work Does

This section explains the database behavior covered by this pass and the result
the implementation must produce.

Pickup Lane currently uses PostgreSQL through SQLAlchemy. Backend settings
validate the application database URL and database timeout values. The database
module creates one SQLAlchemy engine, builds request sessions from that engine,
checks database readiness with a simple query, and disposes the engine during
application shutdown. Alembic runs migrations with `NullPool`, but currently
loads model metadata through the same module that creates the application
engine.

This pass keeps the existing application architecture while making its database
behavior explicit and bounded:

- the application database URL remains backend-only configuration;
- preview, staging, and production require explicit pool size and maximum
  overflow settings;
- the application engine uses those pool settings with the existing pool-wait,
  statement-timeout, and lock-timeout behavior;
- request sessions remain scoped to individual requests and are always closed;
- Alembic uses separate migration database configuration and does not import the
  application engine merely to access model metadata;
- application and migration database access can use separate configuration.

Production provider capacity, deployment-wide connection budgeting, query and
index review, transaction and locking rules, and concrete production database
roles and grants are outside this pass.

## 2. What Must Be True

This section defines the required engineering outcomes. Implementation is
correct only when these behaviors are true.

### 2.1 Database Configuration Is Explicit And Safe

The backend must continue to require a valid PostgreSQL SQLAlchemy database URL
for application traffic.

The existing environment protections remain in force. Test and CI must use the
dedicated test database. Preview, staging, and production must reject local
hosts, development or test database identities, prohibited placeholders, and
other unsafe values.

Configuration errors must identify the invalid setting without echoing
credential-bearing values.

The backend must recognize:

- `DB_POOL_SIZE`;
- `DB_MAX_OVERFLOW`.

Preview, staging, and production require both settings before the application
engine is created.

Local, test, and CI may omit both settings so existing development and test
behavior remains usable. If either setting is provided, both must be provided.

`DB_POOL_SIZE` must be a positive integer.

`DB_MAX_OVERFLOW` must be a non-negative integer, so `0` is valid when overflow
is intentionally disabled.

The existing pool-wait, statement-timeout, and lock-timeout behavior remains
unchanged, including the rule that lock timeout is lower than statement timeout.

### 2.2 Per-Process Connection Growth Is Bounded

When pool size and maximum overflow are configured, the application engine must
pass both values explicitly to SQLAlchemy.

For one application process, the maximum configured number of simultaneous
application-pool connections is:

```text
per_process_application_connections =
    DB_POOL_SIZE + DB_MAX_OVERFLOW
```

Connection waiting remains bounded by the configured pool-wait timeout.

Checked-out PostgreSQL connections must continue receiving the configured
statement and lock timeouts.

### 2.3 Request Sessions Stay Per Request

Each FastAPI request or explicit database operation must receive its own
SQLAlchemy session.

A session must not be stored globally, shared across concurrent requests, or
reused after its request or operation finishes.

On normal completion, the session closes without rollback.

On an ordinary exception, the session rolls back and closes.

On cancellation, the session closes and cancellation propagates without being
reclassified as a database timeout.

Existing callers of the request-session helper must continue working.

### 2.4 Startup, Health, And Shutdown Remain Predictable

Importing or configuring the backend application must not itself open a
PostgreSQL connection.

Database readiness and health checks may open a connection for the duration of
the check.

When a database health check fails, public behavior must remain generic and must
not expose database URLs, hosts, role information, grants, connection counts,
or raw database errors.

Application shutdown must dispose the SQLAlchemy engine so pooled connections
owned by the process are released.

### 2.5 Migration Configuration Is Separate From Application Runtime

Alembic must obtain migration database access through
`MIGRATION_DATABASE_URL`.

Preview, staging, and production migration execution requires
`MIGRATION_DATABASE_URL` and must not silently fall back to the application's
`DATABASE_URL`.

Local, test, and CI migration execution may fall back to `DATABASE_URL` when
`MIGRATION_DATABASE_URL` is not configured.

Migration URL validation must apply the same relevant PostgreSQL URL,
environment, placeholder, and safe-error rules as application database URL
validation.

Normal application startup, request handling, and health checks must not require
or evaluate `MIGRATION_DATABASE_URL`.

Alembic online migrations must continue using `NullPool`.

### 2.6 Model Metadata Loads Without Creating The Application Engine

Alembic must be able to load the complete SQLAlchemy model metadata without
importing the module that creates the application engine.

The shared declarative base must therefore have an import path that has no
dependency on settings, engine construction, or the application session
factory.

All existing models must continue registering against the same shared metadata.

Moving metadata ownership must not change any table, column, relationship,
constraint, index, migration, API route, service behavior, or product behavior.

### 2.7 Database Configuration Remains Backend-Only

Application and migration database URL settings, pool settings, and database
timeout settings must remain backend-only configuration.

Tracked source, examples, tests, and documentation may contain configuration
names and sanitized placeholders but must not contain literal database
credential values or credential-bearing URLs.

These settings must not be exposed through frontend environment configuration,
browser code, or public API responses.

## 3. Design

This section explains how the backend will satisfy the requirements above while
keeping the existing synchronous SQLAlchemy architecture recognizable.

### 3.1 Settings Own Database Inputs

The backend settings layer remains the single parser and validator for
database-related environment configuration.

It exposes the application database configuration needed by the runtime:

- application database URL;
- pool-wait timeout;
- statement timeout;
- lock timeout;
- pool size when configured;
- maximum overflow when configured.

Pool size and maximum overflow are treated as a pair.

For preview, staging, and production, both are required.

For local, test, and CI, both may be absent. If one is supplied without the
other, configuration fails.

The settings layer also provides migration database URL resolution.

For preview, staging, and production:

```text
migration_database_url = MIGRATION_DATABASE_URL
```

For local, test, and CI:

```text
migration_database_url =
    MIGRATION_DATABASE_URL when configured
    otherwise DATABASE_URL
```

Normal application settings construction does not require the migration URL.

### 3.2 The Application Engine Keeps One Pool Per Process

`backend.database` remains responsible for the SQLAlchemy engine used by normal
application traffic.

The engine is created from validated settings.

When pool settings are configured, engine construction includes:

```text
pool_size = DB_POOL_SIZE
max_overflow = DB_MAX_OVERFLOW
pool_timeout = configured pool-wait timeout
```

When pool size and maximum overflow are omitted in local, test, or CI, the
engine preserves the current non-production behavior by omitting those two
arguments.

The existing PostgreSQL checkout hook remains attached to the application
engine and continues applying statement and lock timeouts to checked-out
connections.

Creating the engine must remain lazy with respect to the actual database
connection. Importing the application or constructing the engine must not itself
open a PostgreSQL connection.

### 3.3 Sessions Keep Their Current Request Semantics

The existing request database dependency continues creating a fresh session
from the application session factory for each use.

Its lifecycle remains:

1. create the session;
2. yield it to request or operation code;
3. allow successful work to complete without rollback;
4. roll back ordinary exceptions;
5. close the session in all cases.

Cancellation must propagate normally after session cleanup.

The exception handling must not be broadened in a way that converts
cancellation or process-level interruption into ordinary database failure.

The existing synchronous session configuration remains unchanged unless the
current implementation requires otherwise for the behavior above.

This pass does not redesign transaction ownership inside routes or services.

### 3.4 Model Metadata Is Split From Runtime Connections

Current model modules obtain their declarative base through the database module,
which also creates the application engine. That coupling causes migration
metadata loading to depend on application-engine initialization.

The declarative base moves to a small metadata module that does not depend on
settings, engine creation, or the application session factory.

Application model modules import the declarative base from that metadata module.

The application database module may re-export the same base when necessary to
preserve existing callers, but model registration and Alembic must use the
side-effect-free metadata path directly.

The existing models package continues registering the complete model set against
that shared metadata.

This change affects metadata ownership only. It does not change database schema
or application behavior.

### 3.5 Alembic Uses Migration Configuration And NullPool

Alembic stops obtaining its database URL or model metadata through the
application database module.

Instead, Alembic:

1. loads the shared declarative metadata;
2. loads the application's model registrations;
3. resolves the migration database URL through the settings layer;
4. applies that URL to the Alembic configuration.

Offline migration generation uses the resolved URL without opening a live
database connection.

Online migration execution continues using `NullPool`.

Neither path imports or reuses the request-serving application engine or
application session factory.

### 3.6 Existing Compatibility Remains Intact

This pass does not change API routes, service behavior, database schemas,
migration contents, or business transaction semantics.

Existing route, service, test, and script imports that intentionally use the
application database helpers must continue working.

Existing pool-wait, statement-timeout, lock-timeout, health, shutdown, and
session behavior must remain compatible with the changes above.

Application pool configuration represents the connection limit for one
application process. It must not be treated as the deployment-wide production
database capacity.

## 4. Failures And Edge Cases

This section defines the abnormal and boundary conditions that must be handled
predictably. Correct behavior prevents unsafe database configuration,
unbounded connection growth, session leaks, credential exposure, and accidental
coupling between migration and application database access.

1. **Missing application database URL**
   - **Condition:** A runtime starts without the required application database
     URL.
   - **Required behavior:** Configuration fails before database use without
     exposing credential values.

2. **Unsafe application database URL**
   - **Condition:** The URL is malformed, non-PostgreSQL, missing required URL
     components, a prohibited placeholder, points to the wrong test/CI database,
     or uses a local or lower-environment database in preview, staging, or
     production.
   - **Required behavior:** Configuration rejects the URL without echoing its
     value.

3. **Partial pool configuration**
   - **Condition:** Only pool size or only maximum overflow is supplied.
   - **Required behavior:** Configuration fails and identifies the missing
     paired setting.

4. **Invalid pool size**
   - **Condition:** Pool size is blank, non-integer, zero, or negative.
   - **Required behavior:** Configuration fails and identifies the pool-size
     setting.

5. **Invalid maximum overflow**
   - **Condition:** Maximum overflow is blank, non-integer, or negative.
   - **Required behavior:** Configuration fails and identifies the maximum
     overflow setting. Zero remains valid.

6. **Missing pool configuration in preview, staging, or production**
   - **Condition:** Either required pool setting is absent.
   - **Required behavior:** Configuration fails before application-engine
     creation.

7. **Pool exhaustion**
   - **Condition:** All configured pool and overflow connections are in use.
   - **Required behavior:** SQLAlchemy waits no longer than the configured
     pool-wait timeout before reporting pool exhaustion.

8. **Request database failure**
   - **Condition:** Request database work raises an ordinary exception.
   - **Required behavior:** The session rolls back, closes, and the original
     exception continues upward.

9. **Request cancellation**
   - **Condition:** Request processing is cancelled while a database session is
     active.
   - **Required behavior:** The session closes and cancellation propagates
     without being converted into a database timeout.

10. **Database health failure**
    - **Condition:** The database health check cannot connect or execute its
      connectivity query.
    - **Required behavior:** Health/readiness behavior reports the failure
      without exposing private database details.

11. **Missing migration URL in preview, staging, or production**
    - **Condition:** Alembic runs without `MIGRATION_DATABASE_URL`.
    - **Required behavior:** Migration configuration fails before opening a
      database connection instead of using the application URL.

12. **Unsafe migration database URL**
    - **Condition:** `MIGRATION_DATABASE_URL` violates the applicable database
      URL or environment-safety rules.
    - **Required behavior:** Migration configuration fails without exposing the
      URL value.

13. **Alembic metadata loading creates the application engine**
    - **Condition:** Loading model metadata for Alembic imports the application
      database module in a way that creates the engine or reaches the
      application session factory.
    - **Required behavior:** The implementation is invalid until metadata can
      load through the independent metadata path.

14. **Model metadata registration changes**
    - **Condition:** Moving the declarative base causes an existing model table
      to disappear from the shared metadata.
    - **Required behavior:** The implementation fails validation until the
      complete existing model set is registered.

## 5. Testing

This section defines what tests must prove before the implementation is
considered correct.

### 5.1 Settings And Configuration

Tests must cover:

- application database URL validation;
- test and CI database restrictions;
- preview, staging, and production environment restrictions;
- pool-size parsing and validation;
- maximum-overflow parsing and validation;
- paired pool-setting behavior;
- required pool configuration in preview, staging, and production;
- optional pool configuration in local, test, and CI;
- migration URL requirements and allowed fallback behavior;
- safe errors that do not expose database credential values;
- backend-only ownership of database-related configuration.

### 5.2 Application Engine And Session Lifecycle

Tests must verify:

- configured pool size reaches SQLAlchemy;
- configured maximum overflow reaches SQLAlchemy;
- pool-wait timeout remains configured;
- local, test, and CI behavior remains valid when the optional pool settings
  are omitted;
- statement and lock timeouts continue applying to checked-out PostgreSQL
  connections;
- creating the engine does not eagerly open a database connection;
- sessions close after successful work;
- ordinary exceptions roll back and close;
- cancellation closes the session without timeout reclassification;
- shutdown disposes the application engine;
- database health failures remain generic.

### 5.3 Migration And Metadata Behavior

Tests must verify:

- migration URL resolution follows the environment rules defined above;
- preview, staging, and production migrations require
  `MIGRATION_DATABASE_URL`;
- local, test, and CI migrations use the allowed fallback;
- Alembic online migrations continue using `NullPool`;
- Alembic metadata loading does not create or reuse the application engine;
- the complete current model set remains registered against the shared
  declarative metadata.

### 5.4 Compatibility Tests

Existing affected behavior must continue working after the database and metadata
changes.

Tests must verify:

- existing route and service use of the request-session dependency remains
  compatible;
- existing scripts and tests that intentionally use database helpers remain
  compatible;
- pool-wait, statement-timeout, and lock-timeout behavior remains unchanged;
- existing health and shutdown behavior remains unchanged;
- application pool configuration is treated as per-process application
  configuration rather than deployment-wide capacity.

Repository tests establish the application behavior described by this pass.
They do not establish actual production database capacity or production role
assignments.

## 6. Done When

This section defines the engineering completion bar. The pass is complete when
all of the following are true.

- [ ] Application database URL validation and environment protections remain
      correct.
- [ ] Pool size and maximum overflow are validated together and are required in
      preview, staging, and production.
- [ ] Local, test, and CI remain usable when the optional pool settings are
      omitted.
- [ ] The application engine uses the configured pool size, maximum overflow,
      and pool-wait timeout.
- [ ] The per-process application connection limit is explicitly defined as
      pool size plus maximum overflow.
- [ ] Existing statement-timeout and lock-timeout behavior remains correct.
- [ ] Request sessions remain isolated per use and close correctly after
      success, ordinary failure, and cancellation.
- [ ] Ordinary request database failures roll back before session close.
- [ ] Application shutdown disposes the database engine.
- [ ] Database health failures remain generic and do not expose private
      database information.
- [ ] Application runtime does not require the migration database URL.
- [ ] Migration URL resolution follows the required environment rules.
- [ ] Alembic online migrations continue using `NullPool`.
- [ ] Alembic can load the complete model metadata without creating or reusing
      the application engine.
- [ ] Moving metadata ownership does not change existing database schema or
      model registration.
- [ ] Database-related configuration remains backend-only and no literal
      credential values or credential-bearing URLs are introduced.
- [ ] Required tests pass and existing affected database behavior remains
      compatible.