# WS02-04C1 Operation Timeouts And Cancellation

Pass: WS02-04C1

Scope: portable, source-owned operation-specific timeout and cancellation
semantics for current backend provider and database operations.

## Approved Architecture

C1 does not add a global request deadline, response deadline, route-family
deadline, retry policy, rate limit, concurrency control, durable worker, or
hosting-provider-specific setting.

C1 adds operation-specific timeout ownership only:

| Operation class | Approved initial value | Ownership |
|---|---:|---|
| Stripe read/query operation | 6 seconds | backend typed setting |
| Stripe mutation operation | 15 seconds | backend typed setting |
| Firebase Admin HTTP operation | 8 seconds | backend typed setting |
| R2 metadata/HEAD connect | 2 seconds | backend typed setting |
| R2 metadata/HEAD read | 6 seconds | backend typed setting |
| SQLAlchemy pool wait | 2 seconds | backend typed setting |
| PostgreSQL statement timeout | 12000 milliseconds | backend typed setting applied to checked-out sessions |
| PostgreSQL lock timeout | 2000 milliseconds | backend typed setting applied to checked-out sessions |

These values are initial application policy values. They are configurable and
must be reassessed after real telemetry, permanent hosting/runtime selection,
provider evidence, and load/failure evidence exist.

## Timeout Taxonomy

Public timeout categories:

- `API.DEPENDENCY_READ_TIMEOUT`: a required dependency read/query did not
  complete in time. The response is HTTP 503 and safe retry-later semantics.
- `API.DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN`: an external mutation did not
  confirm its final provider outcome. The response is HTTP 503 and must not
  state that the operation definitely failed.
- `API.DATABASE_TIMEOUT`: an application-owned database operation reached the
  configured bound. The response is HTTP 503 and safe retry-later semantics.

`CANCELLATION` remains an internal classification only. C1 does not invent a
client response when the client is already disconnected.

## Provider Semantics

Stripe uses distinct timeout-owned clients for read and mutation operations.
Read timeouts return dependency-read timeout semantics and do not drive local
mutation based on incomplete provider state. Mutation timeouts return
unknown-outcome semantics, preserve idempotency-key usage, do not retry, and do
not record a definite provider failure solely from timeout.

Firebase Admin uses one shared HTTP timeout for existing app/client ownership.
Verification and lookup timeouts map to dependency-read timeout semantics.
Deletion timeout is treated as unknown outcome and routed through existing
support/recovery state instead of restoring or finalizing account state as if
the provider result were known.

R2 C1 scope is metadata/HEAD verification only. Connect and read timeout values
apply to the backend R2 client used for metadata verification. Presigned upload
and read URL generation remains local signing work and is not treated as a
network timeout path. Browser direct-upload behavior and R2 retry policy are not
changed.

## Database Semantics

SQLAlchemy pool acquisition wait is bounded by the source-owned pool wait
setting. C1 does not change pool size, maximum overflow, recycle, pre-ping, or
database connection-budget planning.

Checked-out PostgreSQL sessions receive `statement_timeout` and `lock_timeout`
settings from typed backend configuration. Lock timeout remains lower than
statement timeout. Timeout failures roll back where the current request/session
dependency owns rollback, and checked-out connections are reset on reuse.

DB connect timeout, transaction timeout, idle-session timeout, migrations,
schema changes, and provider-specific database topology remain outside C1.

## Cancellation And Sync Work

Cancellation is distinct from timeout and failure. New timeout helpers do not
catch `BaseException`, and ordinary `Exception` handling does not swallow
`asyncio.CancelledError` in the current runtime.

A local timeout signal does not prove already-running synchronous provider work
has stopped. C1 response semantics therefore do not claim cancellation. For
outcome-sensitive provider mutations, timeout may mean unknown provider outcome.
C2 owns retry, recovery, and reconciliation improvements.

## Telemetry

C1 uses existing safe telemetry-label primitives for timeout classification.
Allowed labels are bounded values such as operation class, provider kind,
resource kind, outcome class, result class, and stable error code. C1 does not
add labels containing user IDs, provider IDs, payment IDs, object keys, URLs,
emails, tokens, request content, exception strings, or arbitrary text.

No dashboards, alerts, SLOs, or retention values are introduced by C1.

## Evidence And Confidence

Confidence: source-owned and test-backed for typed settings, provider wrapper
selection, public error taxonomy, cancellation classification, R2 metadata
scope, and local PostgreSQL timeout behavior.

External evidence not proven by C1: Render worker/process topology, Neon
connection limits, provider dashboard timeout/retry settings, production logs,
staging captures, alert behavior, and permanent hosting/runtime alignment.

## Deferred Work

C2 owns retries, recovery, reconciliation, backpressure, durable job behavior,
and provider outcome repair. C3 owns rate, abuse, and concurrency controls.
Permanent hosting/runtime alignment remains outside C1.

## API-M10 Status

WS02-04C1 partially closes API-M10 for portable source-owned operation timeout
semantics. API-M10 remains partial overall until later passes provide retry,
reconciliation, rate/backpressure, provider/runtime evidence, and permanent
hosting alignment.
