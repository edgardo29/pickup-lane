# Backend Engineering Standards

## Purpose and relationship to project rules

This document defines transferable engineering practices for Python backends
using HTTP frameworks, validation models, relational databases, migrations,
and external services. It does not prescribe a directory tree, deployment
model, provider, API error format, or test command.

Apply it alongside the adopting project's architecture, database, testing,
security, and API-contract rules. Those documents define actual ownership,
paths, supported versions, migration policy, and execution restrictions. A
project rule that conflicts with a **MUST** or **MUST NOT** here requires an
explicit, documented exception with a reason and scope. Do not infer that a
general production migration pattern replaces a project's current policy.

**MUST** and **MUST NOT** are requirements. **SHOULD** and **SHOULD NOT** are
strong defaults that allow a justified exception. **MAY** is optional.

## 1. Python code and boundaries

Prefer the smallest abstraction with a clear responsibility. Use a function
for a stateless operation; introduce a class when state, lifecycle, coherent
invariants, or useful polymorphism warrants one. Do not add wrapper layers or
shared modules merely to remove a few repeated lines. Promote shared behavior
when its responsibility and consumers are established.

Annotate public interfaces and non-obvious values where types clarify a
contract. `Protocol`, `TypedDict`, dataclasses, and enums MAY express their
respective behavioral, dictionary, data-record, and finite-value contracts.
Type annotations **MUST NOT** be treated as runtime validation. Validate
untrusted values at the boundary where they enter the application.

Mutable defaults **MUST NOT** unintentionally share state between calls or
instances. Use a fresh value or a factory when each instance needs its own
collection. Avoid hidden mutable globals whose state can leak across requests,
jobs, or tests.

Files, sessions, locks, and temporary resources **MUST** have an owner that
releases them on both success and failure. Use context managers or equivalent
`try/finally` cleanup. Catch an exception only where code can add useful
context, translate it, recover safely, or clean up. **SHOULD NOT** suppress a
broad exception merely to keep a workflow running.

Keep dependency resolution reproducible through the adopting project's chosen
lock, constraints, image, or equivalent mechanism. Do not assume an unconstrained
latest-compatible dependency graph is reproducible.

## 2. HTTP handling and application lifecycle

HTTP handlers SHOULD adapt transport input to application operations and return
declared contracts. Keep reusable business decisions and database-dependent
authorization in the owning application layer. Request-scoped resources
**MUST** be released deterministically; framework dependency teardown is one
way to provide that lifecycle. Process-lifetime resources SHOULD have an
explicit startup and shutdown owner.

Choose synchronous or asynchronous handlers from the execution path, not from
a blanket preference for async. An `async def` path **MUST NOT** run blocking
database, network, file, or substantial CPU work directly on the event loop.
Use a synchronous handler, an asynchronous implementation, or explicit offload
as appropriate. Directly called utility functions are not automatically
offloaded merely because a framework offloads synchronous route functions.

Public endpoints SHOULD declare response contracts that match runtime
serialization and field exposure. Generated API descriptions SHOULD reflect
actual parameter, response, status, and error behavior. Keep HTTP error
selection separate from centralized error serialization when the application
uses a shared error format. Exact paths, status mappings, error fields, and
compatibility rules belong to the adopting project's API contract.

## 3. Validation and serialization

Use Pydantic v2 models where validation or serialization crosses a meaningful
boundary, such as an HTTP request, configuration, an external response, or a
structured message. Do not force every already-validated internal value through
another model. A service MAY accept a request model when its semantics fit the
operation; introduce a transport-independent input type only when real callers
or differing semantics justify it.

Pydantic may coerce values. Choose strictness or conversion deliberately for
each contract, including differences between JSON and Python inputs. Validators
SHOULD remain deterministic and focused on boundary or cross-field rules; they
**MUST NOT** hide database writes or external calls.

When omission and explicit null have different meanings, partial-update logic
**MUST** preserve that distinction, for example through `model_fields_set` or
`model_dump(exclude_unset=True)`. Use Pydantic v2 configuration and
serialization APIs in new code; do not present v1-only `orm_mode` patterns as
current v2 practice. Avoid unnecessary conversion chains that can change
aliases, omitted fields, or field exposure.

## 4. SQLAlchemy sessions and transactions

A Session **MUST** have a bounded, explicit lifecycle and deterministic cleanup.
Do not share one mutable `Session` across concurrent threads or one
`AsyncSession` across concurrent tasks. A session's identity map and pending
state affect what its queries and objects observe; do not treat it as a
stateless connection wrapper.

One logical atomic state-changing workflow **MUST** have a clear transaction
owner. Operations participating in that transaction **MUST NOT** independently
commit or roll it back. They MAY flush when database-generated values or
constraints must be observed before the owner commits. A separate commit is
appropriate only for an intentional durable stage with defined recovery and
retry behavior.

`flush()`, `refresh()`, and `commit()` serve different purposes. **MUST NOT**
commit merely as a generic way to synchronize pending ORM state when a flush
or a suitable database return value suffices. After a failed flush or commit,
roll back before reusing the Session, or close and discard it. Keep
transactions and row locks no longer than the operation requires.

Use constraints or atomic database operations for invariants they can express.
Use targeted row locks when a known contested resource needs them. Stronger
isolation MAY be appropriate when its anomaly protection is needed, but its
retry behavior and cost must be understood. Do not make one locking or
isolation strategy universal.

## 5. Queries and PostgreSQL integrity

Use SQLAlchemy's supported statement and parameter-binding APIs. Data values
**MUST** be bound as parameters; **MUST NOT** interpolate untrusted values into
SQL text. Dynamic identifiers and sort keys require a controlled allowlist,
not value binding alone.

Choose relationship-loading strategy for the access pattern. Review bulk
serialization and collection loops for accidental N+1 queries. Lazy loading,
`selectinload()`, `joinedload()`, and `raiseload()` each have appropriate uses;
none is a universal default. Prefer set-oriented SQL or SQLAlchemy Core when
it makes a bulk operation clearer or more efficient than per-row ORM work.

When `joinedload()` eagerly loads a collection, apply `Result.unique()` before
consuming the ORM result, as required by SQLAlchemy 2.x.

Persistent invariants that PostgreSQL can express **MUST** have database
enforcement. Application validation may give clearer errors but cannot replace
constraints against concurrent or alternative writers. A PostgreSQL `CHECK`
passes when its condition evaluates to true or null; use `NOT NULL` as well
when null is forbidden. Select timestamp types according to whether a value
represents an instant or an intentionally timezone-free wall-clock value.

Indexes SHOULD follow real predicates, ordering, selectivity, and workload.
Consider write and storage costs as well as read speed. Use representative
query plans and measurements when optimizing a meaningful bottleneck; a plan
from tiny development data may not represent production. `EXPLAIN ANALYZE`
executes its statement, so run potentially mutating statements only in an
appropriate controlled environment. Bounded pagination and deterministic
ordering are important for growing collections; choose offset or keyset/cursor
behavior according to access needs rather than requiring one everywhere.

## 6. Migration engineering

Alembic autogeneration produces a candidate migration, not an authoritative
schema change. Every generated revision **MUST** be reviewed for rename
inference, dropped data, constraints, defaults, lock or rewrite cost, and
deployment compatibility. Use deterministic names for constraints and indexes
when the adopting project's database policy calls for them.

When applied database history must be preserved, plan compatible forward
changes for old and new application versions, including backfills and staged
constraint enforcement where necessary. An adopting project may instead have
an explicitly approved clean-rebuild policy for disposable environments;
follow that policy until its owner approves a transition. **MUST NOT** claim a
destructive downgrade restores data that was not preserved. A drift check such
as `alembic check` MAY supplement review but cannot prove schema semantics or
migration correctness.

The adopting project's database guide owns exact migration structure,
commands, allowed targets, rebuilds, and verification gates.

## 7. External effects, webhooks, and workers

An external call and a database commit are not one atomic transaction. When
committed database state **must** reliably cause later external work, persist
a durable work record in the same transaction or use a mechanism with
equivalent failure guarantees. Dispatch must tolerate retries and duplicate
delivery. Best-effort effects do not automatically require an outbox or queue.
For a provider-authoritative operation, use the provider's supported
idempotency mechanism where available and reconcile local state with the
provider rather than pretending a database transaction includes the call.

External network calls **MUST** have an explicit, bounded timeout policy.
Retries **MUST** be limited to failures for which the complete operation is
safe to repeat or protected against duplicate effects. Do not hold a database
transaction or lock across slow or retry-prone external I/O unless correctness
requires it and the failure strategy is documented.

Authenticate incoming webhooks using each provider's documented mechanism,
such as signature verification or HTTP Basic Authentication. **MUST NOT**
require a signature from a provider that does not support one. Verify the
provider's required credentials or evidence before trusting the event. Handle
repeated, delayed, and out-of-order delivery without duplicating material
effects; use a stable event identity when the provider supplies one. Material
local state SHOULD be reconcilable with an authoritative provider or stored
source of truth. Provider-specific protocol mechanics belong to the owning
client or integration boundary.

Each concurrent worker or scheduled execution that uses the database **MUST**
own its session lifecycle and explicit, bounded transaction stages. One job
MAY use separate short transactions to claim work and record its outcome,
with external I/O between them. Jobs that may be retried or interrupted
**MUST** be safe to resume or repeat. Long-running workers SHOULD stop
claiming new work and finish or release claims safely during graceful
shutdown. A scheduler's single-active-run guarantee does not make a business
operation idempotent.

## 8. Security and operational visibility

Derive actor identity from verified authentication and enforce authorization
for the target object, action, and fields at the backend boundary that owns
the decision. Client visibility or a route guard cannot grant authorization.
Token verification and token revocation checking are distinct; the adopting
project must define when additional revocation checks are required. Do not
invent that policy from the presence of an authentication SDK.

Secrets, tokens, credentials, connection strings containing credentials, and
sensitive request contents **MUST NOT** be written to ordinary logs. Log safe
operation names, correlation context, duration, and sanitized failure details
needed for diagnosis. Do not log complete bodies or headers by default.
Required production credentials SHOULD fail closed when absent; configuration
and secret distribution must follow the adopting project's deployment policy.

Request-correlation identifiers and distributed trace context serve different
purposes. If distributed tracing is introduced, use a documented trace
propagation mechanism and correlate it with logs without redefining an
existing request-ID contract.

## 9. Performance and testability

Measure meaningful database, network, memory, or worker costs before adding
optimization complexity. Size connection pools against database capacity and
process concurrency. Cache only when benefit and invalidation behavior are
clear. Stream or batch work when result size makes full materialization costly;
do not complicate small operations solely to use a streaming pattern.

Keep effect boundaries visible so tests can control database access, time,
randomness, network calls, and storage without production-only branches or
mocking every private helper. Verify PostgreSQL-specific constraints, locking,
and migration behavior against an appropriate real database environment when
those properties matter. Pure deterministic rules can use focused unit tests.
The adopting project's testing standard owns suite placement, fixtures,
execution permission, commands, and completion reporting.

## 10. Decision rule

When several implementations are valid, prefer clear ownership, preserved
invariants, bounded resource lifetimes, explicit failure behavior, and the
least complexity justified by current requirements. Project-specific API,
database, architecture, and testing rules remain authoritative for their
respective contracts.
