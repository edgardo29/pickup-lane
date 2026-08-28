# WS05-01A - Provider-Independent Durable Job Model, Claim/Lease Lifecycle, And Portable Worker Runtime

This pass adds Pickup Lane's PostgreSQL-backed durable job foundation and a
portable worker command so background work can be claimed, retried, recovered,
and inspected without depending on final worker hosting.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

This section explains the part of the system this pass changes and why that
result matters. Read it as the high-level engineering boundary for the
implementation.

Pickup Lane currently has request-time workflows, provider retry policy
metadata, admin money issue rows, and database transaction safeguards, but it
does not have a general durable job model or worker runtime. Work that outlives
one request is therefore either handled synchronously, left for manual repair,
or explicitly deferred to WS05.

This pass creates the shared durable job substrate:

- a PostgreSQL job table that stores durable work, current state, lease,
  retry, error, result, correlation, and ownership metadata;
- append-only job event history for state transitions and repair visibility;
- worker heartbeat state for portable worker identity and shutdown behavior;
- service APIs for enqueue, claim, heartbeat, completion, retry, exhaustion,
  cancellation, and operator inspection;
- a handler registry that rejects unsupported job types or payload versions
  safely;
- a portable command that can run the worker locally, in CI-style proof, or in a
  later selected platform without embedding final provider topology; and
- deterministic PostgreSQL tests that prove claim, lease, retry, crash, stale
  lease, duplicate worker, unsupported version, shutdown, and backlog behavior.

The job foundation must preserve the accepted database, transaction,
migration, SQL-safety, runtime, and correlation contracts already present in
the repository. It does not implement payment state machines, Stripe
reconciliation, refund/credit workflows, external notice delivery, moderation
delivery, storage reconciliation, final worker hosting, deployed dashboards, or
final production database capacity/role proof.

## 2. What Must Be True

This section defines the required engineering outcomes for the pass. These are
the conditions the implementation and tests must satisfy before the work can be
accepted.

### 2.1 Durable Job State

The application must have a generic durable job model backed by PostgreSQL.
Each job must have:

- stable UUID identity;
- finite job type;
- payload version;
- safe JSON payload;
- priority;
- availability time;
- current status;
- attempt count;
- maximum attempts;
- current lease token;
- lease owner;
- lease expiry;
- heartbeat timestamp;
- correlation identifier;
- optional request or operation reference that is safe to store;
- sanitized error classification;
- safe result metadata; and
- timezone-aware creation, update, completion, cancellation, and exhaustion
  timestamps where applicable.

The database must reject impossible job states. A job cannot be simultaneously
available, leased, succeeded, cancelled, and exhausted. Lease fields must match
lease-owned states. Terminal states must have terminal timestamps. Attempt
counts must be non-negative and cannot exceed the job's maximum attempt count.

### 2.2 Idempotent Enqueue And Transactional Handoff

The enqueue API must be safe to call from an application database transaction.
It must create durable work only from already-known local state and must not
start providers, threads, subprocesses, network clients, or worker execution.

A caller must supply a stable idempotency key for any job whose creation may be
retried or reached from duplicate application work. Reusing the same
idempotency key with the same job type and compatible payload identity must
return the existing job. Reusing the same key with a conflicting type, version,
or protected payload identity must fail without replacing the existing job.

The job foundation must not invent consumer-specific financial, notification,
moderation, storage, or provider state machines. Later passes add concrete job
types and handlers on top of this foundation.

### 2.3 Claim, Lease, And Heartbeat Semantics

Claiming must be atomic across independent PostgreSQL sessions. When multiple
workers attempt to claim the same available work, exactly one worker may obtain
each job. Other workers must skip locked or already leased rows and either
claim different eligible jobs or report no claim.

A worker may claim only job type and payload-version pairs supported by the
immutable registry snapshot used for that claim iteration. An otherwise valid
job must not be leased, have its attempt count incremented, or be moved toward
failure merely because the worker attempting to claim work does not support
that job type or payload version.

Claimed jobs must receive a lease token, lease owner, lease expiry, heartbeat
timestamp, and incremented attempt count inside the same transaction that moves
them out of availability. Attempt count represents lease/execution attempts and
must never exceed `maximum_attempts`.

Heartbeat is lease renewal, not only liveness metadata. While a handler is
executing, the current lease owner must renew the lease before expiry. A valid
heartbeat must atomically require the current lease token and an unexpired
lease, use PostgreSQL/database time, update the heartbeat timestamp, and move
`lease_expires_at` forward by the configured portable lease duration. Heartbeat
must not increment attempt count. The heartbeat interval must be shorter than
the lease duration. Tests may use short explicit values; final deployed tuning
remains outside this pass.

Worker-owned transitions such as heartbeat, completion, retry, release, and
exhaustion must require the current lease token and an unexpired lease. Once
database time reaches the lease expiry, the old token can no longer mutate the
job even if no replacement worker has claimed it yet.

Expired lease recovery must be deterministic and bounded by the attempt limit.
If an expired lease has remaining attempts, recovery may issue a new lease
token and increment the attempt count in the same transaction. If the expired
lease already consumed the maximum allowed attempt, recovery must transition
the job to `exhausted` with a safe lease-expiry error classification instead of
creating an attempt beyond the limit. Reclaiming or exhausting an expired lease
must preserve previous attempt/event history, and every prior lease token must
remain permanently unable to mutate the job.

### 2.4 Handler Execution And Version Compatibility

The worker must execute only registered handlers for supported job types and
payload versions. Claim eligibility and dispatch must use the same immutable
registry snapshot for a worker iteration so a worker does not first claim work
and only afterward discover that its own code version cannot execute it.

Unsupported-by-this-worker job type or payload version is a compatibility
condition, not a job failure. The worker must skip that row without changing
job status, attempt count, lease state, result/error metadata, or lifecycle
history. This permits old and new worker versions to overlap safely: an older
worker can continue processing versions it supports while leaving newer work
available for a compatible worker. If no currently running worker supports a
queued type/version, the work remains durable and visible for operator action;
an incompatible worker must not poison or exhaust it.

Production enqueue still rejects job definitions that the producing
application version does not support. A malformed payload for an otherwise
supported type/version, or an unsafe handler lookup that violates the accepted
registry contract, must fail closed without running a side effect and may move
to exhausted/repairable state with safe diagnostic metadata according to the
framework policy.

Handlers must run under at-least-once semantics. The framework must assume a
handler can be interrupted after it starts and before completion is recorded.
The job lifecycle must therefore make duplicate-safe handler design explicit
and must not mark side effects as completed unless the handler returns a
successful result and the completion transaction commits.

The framework may use synthetic test handlers to prove generic behavior. It
must not add production payment, refund, credit, notice, moderation, storage, or
provider handlers in this pass.

### 2.5 Retry, Exhaustion, Dead-Letter, And Repair

Transient failures must be converted into bounded retry state with the next
availability time recorded durably only when another attempt remains. Permanent
failures must be exhausted without further automatic retry. A transient failure
on the final allowed attempt, or expiry of the final allowed lease, must move
the job to an exhausted/dead-letter state with safe error metadata and operator
visibility. No retry, release, reclaim, or repair path may make the job
automatically claimable in a way that causes `attempt_count` to exceed
`maximum_attempts`; explicit operator requeue remains a separate repair action.

Retry behavior must not use one global invented production retry policy. Each
registered job type must declare its retry classification and numeric policy
before it can be used by production code. Because this pass creates the
framework before consumer jobs exist, framework tests may use explicit
synthetic policies but the production registry must not imply final payment,
provider, notification, storage, or worker limits.

Repair APIs must support explicit operator-directed cancellation or requeue of
exhausted work. Repair must append history and must not silently hide the
previous failure.

### 2.6 Portable Worker Runtime

The worker command must be a repository-native Python entry point that can run
without Celery, RQ, Redis, a managed queue, or final provider hosting. It must
use the normal backend settings/database wiring and must not start when the
FastAPI application is merely imported or constructed.

The command must support a deterministic single-iteration mode for tests and
operator proof. Continuous polling may be supported only as portable behavior;
it must not define final worker instance counts, autoscaling, platform command
syntax, production concurrency, or final provider runtime settings.

Shutdown must be graceful. When shutdown is requested, the worker must stop
claiming new jobs, finish or durably release the current claim according to the
lease rules, update its worker heartbeat state, and exit without claiming
provider-specific signal behavior.

### 2.7 Operator Visibility And Safe Diagnostics

The job system must expose source-level inspection of:

- pending and retry-waiting jobs;
- currently leased jobs;
- expired leases;
- succeeded jobs;
- exhausted/dead-letter jobs;
- oldest pending age;
- aged/fairness-protected backlog;
- queued job type/version combinations unsupported by the inspecting worker
  registry;
- attempt counts;
- last safe error code;
- worker identity, version, and heartbeat age.

Diagnostics must use safe bounded metadata. Job type may be a telemetry label;
job IDs, user IDs, payment IDs, provider IDs, request IDs, correlation IDs,
payload bodies, free text, secrets, and raw exception strings must not become
metric labels or public diagnostic fields.

### 2.8 Compatibility With Accepted Contracts

The implementation must preserve the accepted contracts from `WS02-02`,
`EN-02`, `WS04-01A/B/C`, `WS04-02A/B/C`, and `WS04-03A`.

In particular:

- application import and app construction must not start workers, open
  PostgreSQL connections, run migrations, or initialize providers;
- worker code must use the existing PostgreSQL database safety boundary;
- new migrations must follow the current one-table-one-canonical-migration
  policy;
- job SQL must remain parameterized and avoid unsafe raw SQL construction;
- job JSON payload and result metadata must remain bounded, shaped, and safe;
- worker connection demand must remain visible for final database capacity
  verification; and
- the accepted runtime-topology tests must distinguish this approved portable
  worker command from still-deferred final worker deployment configuration.

## 3. Design

This section describes the implementation approach. The design intentionally
uses PostgreSQL because Pickup Lane already depends on PostgreSQL transactions,
row locks, Alembic, and SQLAlchemy, and because no final managed queue provider
has been selected.

### 3.1 Data Model

The durable job state is stored in ordinary application tables. This makes job
creation transactional with the domain rows that require follow-up and lets
tests prove behavior with independent PostgreSQL sessions.

Use three tables:

| Table | Responsibility |
|---|---|
| `durable_jobs` | Current durable job state and claimable queue. |
| `durable_job_events` | Append-only lifecycle, attempt, error, repair, and operator history. |
| `durable_worker_heartbeats` | Current portable worker identity, version, heartbeat, and shutdown state. |

`durable_jobs` must be claimable by availability, compatibility, priority, and
the starvation-prevention rule defined below. Its identity and idempotency
constraints must prevent duplicate durable work while allowing the same job to
move through retries and leases.

The status set must be finite:

| Status | Meaning |
|---|---|
| `pending` | The job is eligible when `available_at` is due and no active lease exists. |
| `retry_waiting` | The job failed transiently and is waiting until `available_at`. |
| `leased` | A worker owns the current lease and may execute or update the job with the lease token. |
| `succeeded` | The handler result committed successfully. |
| `exhausted` | The job reached a permanent failure or retry limit and needs operator attention. |
| `cancelled` | An operator or owning workflow intentionally stopped the job before success. |

Each new table must have one canonical Alembic migration in the current linear
chain after revision `0059_admin_review_case_events`. Table creation order must
follow foreign-key dependencies: jobs first, job events second, worker
heartbeats independently or after jobs if a foreign key is selected.

### 3.2 Enqueue Contract

The enqueue service should accept:

- job type;
- payload version;
- safe payload;
- idempotency key;
- availability time;
- priority;
- maximum attempts;
- correlation ID or generated safe correlation ID; and
- optional safe origin reference.

The service must validate job type, payload version, payload shape, and numeric
policy through a job definition registry before inserting. If the registry has
no production handler for a type, production enqueue must reject it rather than
creating unprocessable work. Tests may use an isolated registry with synthetic
job definitions.

The insert should rely on a database uniqueness constraint for the idempotency
key. Conflict handling must reload the existing job and compare protected
identity fields. A true duplicate returns the existing job; a conflicting
duplicate raises an explicit domain error.

No enqueue function may commit independently when called with a caller-owned
session. The caller's transaction decides whether both domain state and durable
job creation commit.

### 3.3 Claim, Fairness, Lease, And Heartbeat Algorithm

The claim transaction must use PostgreSQL row-level locking so two workers
cannot claim the same job. Eligibility must include all of the following:

- status is `pending` or `retry_waiting`;
- `available_at` is due according to PostgreSQL/database time;
- `attempt_count < maximum_attempts`; and
- the job type/payload-version pair is supported by the immutable registry
  snapshot for the claiming worker.

The supported-pair filter must be built with parameterized SQL/SQLAlchemy
constructs. It must not use interpolated job type/version strings.

Backlog fairness is part of the repository-owned queue semantics. Eligible jobs
must use an age-based starvation boundary:

1. a job becomes fairness-protected once it has remained eligible for at least
   the configured `fairness_age`;
2. if any fairness-protected compatible jobs exist, the oldest such jobs are
   selected before non-aged jobs, regardless of normal priority;
3. among fairness-protected jobs, order is deterministic by `available_at`,
   `created_at`, then `id`;
4. when no fairness-protected job is waiting, normal order is `priority DESC`,
   then `available_at`, `created_at`, and `id`.

`fairness_age` is a positive bounded portable queue-policy setting, not a
provider/runtime-topology setting. Gate B may place the value in the normal
repository settings/policy surface and tests may override it with short
deterministic values. The semantic rule itself is fixed here: a continuous
stream of newer high-priority work must not allow an older compatible job to
wait indefinitely while workers continue claiming.

The PostgreSQL selection should therefore have the equivalent behavior of:

```sql
SELECT ...
FROM durable_jobs
WHERE status IN ('pending', 'retry_waiting')
  AND available_at <= now()
  AND attempt_count < maximum_attempts
  AND (job_type, payload_version) IN (<supported pairs>)
ORDER BY
  CASE WHEN available_at <= now() - :fairness_age THEN 0 ELSE 1 END ASC,
  CASE
    WHEN available_at <= now() - :fairness_age THEN available_at
  END ASC,
  CASE
    WHEN available_at > now() - :fairness_age THEN priority
  END DESC,
  available_at ASC,
  created_at ASC,
  id ASC
FOR UPDATE SKIP LOCKED
LIMIT ...
```

The selected row is then updated to `leased` with a fresh lease token, worker
identity, lease expiry, heartbeat timestamp, and incremented attempt count
before the transaction commits.

Expired lease handling is part of the same database-authoritative lifecycle.
For a row whose `status = 'leased'` and whose `lease_expires_at <= now()`:

- if `attempt_count < maximum_attempts`, recovery may create a new lease with a
  new token and incremented attempt count;
- if `attempt_count >= maximum_attempts`, recovery must transition the row to
  `exhausted` instead of issuing another lease.

Both paths append a safe event describing lease expiry and recovery/exhaustion.
The prior token becomes permanently stale. The recovery logic must remain
atomic under competing workers.

Heartbeat renewal must execute as a token-guarded update using database time.
A successful heartbeat requires the row to remain `leased`, the supplied token
to equal the current token, and the existing lease to still be unexpired. It
updates `heartbeat_at` and sets `lease_expires_at` to database time plus the
portable lease duration. A heartbeat after expiry fails and cannot resurrect
the lease.

While a handler is running, the worker runtime must maintain heartbeats often
enough to keep the lease valid. Heartbeat persistence must use its own
short-lived database session/transaction or another repository-approved
mechanism that does not share a SQLAlchemy session concurrently with handler
work. This source-level requirement makes the extra worker connection demand
visible to the later final database-capacity pass without choosing final
provider sizing here.

The implementation must not use process-local locks to prove claim, lease,
fairness, or recovery correctness. Process locks may be used only for in-process
cleanup convenience when database state remains authoritative.

### 3.4 Worker Execution

Worker execution separates generic lifecycle from job-specific behavior.

The generic worker owns:

- construction of one immutable supported type/version registry snapshot for
  each claim/dispatch iteration;
- claim;
- lease heartbeat/renewal while handler execution is active;
- handler dispatch;
- result recording;
- retry/exhaustion transition;
- shutdown response; and
- worker heartbeat state.

Registered handlers own only their job-specific work. A handler receives the
current session, job identity, validated payload, attempt information, and safe
correlation context. A handler returns a success result, a transient failure
classification, or a permanent failure classification. Unhandled exceptions
are converted into transient or permanent failure according to the registered
job definition.

The framework must persist completion only after the handler returns and the
completion transaction commits, and completion must still hold the current,
unexpired lease token. If heartbeat renewal fails or the lease is lost, the
worker must treat ownership as lost and must not record success, retry,
release, or exhaustion with that stale token.

If the process stops after a handler side effect but before completion commits,
the lease eventually expires. The job can be retried when an attempt remains,
or becomes exhausted when the expired lease was the final allowed attempt,
under at-least-once semantics. This is why later consumer handlers must be
idempotent; this pass must make that contract unavoidable.

### 3.5 Retry And Repair

The framework supports bounded retry through job definitions. A definition must
state:

- which failure classes are transient;
- which are permanent;
- maximum attempts;
- how to compute the next availability time;
- what safe error code is stored; and
- whether operator repair or replay is allowed.

This pass must not choose final production retry counts, backoff curves, worker
concurrency, or provider-specific retry behavior for future payment and storage
jobs. Framework tests may use explicit synthetic values to prove that the
mechanics work, but production job definitions must provide their own reviewed
policy when introduced.

A transient failure may enter `retry_waiting` only when
`attempt_count < maximum_attempts`. A transient failure on the final allowed
attempt must become `exhausted`. Explicit operator requeue may create a new
repair opportunity only through a reviewed repair transition that records the
previous terminal history and the new attempt policy; it must not silently
decrement or erase prior attempts.

Operator repair must preserve history. Requeueing an exhausted job clears the
terminal state only through an explicit repair transition, increments or
records repair metadata, and creates an event. Cancelling a job must be
terminal and must not delete the job or its event history.

### 3.6 Portable Command

The portable command should be runnable as a Python module. It should support:

- validating that the worker can connect to the configured PostgreSQL database;
- registering the current worker identity and version;
- processing one deterministic iteration for tests and manual checks;
- running a controlled loop when explicitly requested;
- reporting a concise status summary; and
- graceful shutdown.

The command may accept options such as worker identity, once/loop mode, claim
batch size, and poll interval only as portable runtime inputs. It must not
encode final platform process counts, autoscaling, provider command syntax, or
production concurrency values.

Importing `backend.main`, constructing the FastAPI app, importing backend
models, or importing the worker module must not start the worker loop.

### 3.7 Operator Visibility

Source-level inspection should come from service functions and the portable
command, not from provider dashboards. The minimum summaries are backlog by
status/type, oldest pending age, expired lease count, exhausted count, retry
waiting count, active worker heartbeat age, and recent safe event history for a
specific job.

No public route is required in this pass. If Gate B finds that an HTTP admin
route is required to satisfy operator visibility, that is a design change and
must return to Gate A before implementation continues.

### 3.8 Compatibility Updates

The accepted runtime topology boundary currently proves that no worker or
scheduler command exists. That was correct before WS05. This pass must update
that compatibility proof so it now allows the approved portable worker command
while continuing to reject:

- Celery, RQ, Redis, or unmanaged queue adoption;
- tracked final provider deployment manifests;
- final worker instance counts;
- final worker process counts;
- final worker concurrency values;
- autoscaling/resource settings; and
- provider-specific worker start commands.

The implementation must also update the accepted database and migration
compatibility proof where the new job tables become part of the current schema.

## 4. Failures And Edge Cases

This section lists the abnormal situations that matter for durable jobs. The
implementation must handle these cases deterministically because background work
often exists specifically to recover from failures.

1. **Duplicate enqueue**
   - **Condition:** The same idempotency key is submitted twice for the same
     job identity.
   - **Required behavior:** Return the existing durable job without creating a
     duplicate row or duplicate event history that implies new work.

2. **Conflicting enqueue**
   - **Condition:** The same idempotency key is reused with a different job
     type, payload version, or protected payload identity.
   - **Required behavior:** Reject the enqueue and preserve the original job.

3. **Competing claimers**
   - **Condition:** Two independent sessions try to claim the same eligible job.
   - **Required behavior:** Exactly one session receives that job. The other
     session skips it, claims another eligible job, or returns no claim.

4. **Stale lease**
   - **Condition:** A worker claims a job and then stops heartbeating until the
     lease expires.
   - **Required behavior:** A later claim can recover the job with a new lease
     token. The stale token cannot complete, retry, cancel, or exhaust the job.

5. **Lost completion race**
   - **Condition:** An old worker tries to complete a job after a new lease has
     been issued.
   - **Required behavior:** The completion is rejected because the lease token
     is no longer current.

6. **Worker/job version mismatch**
   - **Condition:** A worker's immutable registry snapshot does not support a
     queued job's type or payload version.
   - **Required behavior:** The worker does not claim or mutate that job. Status,
     attempt count, lease fields, result/error metadata, and lifecycle history
     remain unchanged. A compatible worker version may claim it later. The
     incompatible backlog remains visible to operators.

7. **Malformed payload**
   - **Condition:** A job payload is missing required fields, has unexpected
     shape, or contains values rejected by its registered validator.
   - **Required behavior:** The job fails closed without running the handler.
     The stored error classification is safe and bounded.

8. **Transient handler failure**
   - **Condition:** A registered handler returns or raises a retryable failure.
   - **Required behavior:** The job records the failed attempt, clears the
     active lease, stores safe error metadata, and becomes available only at the
     next allowed time unless attempts are exhausted.

9. **Permanent handler failure**
   - **Condition:** A handler returns a permanent failure or the job definition
     classifies the exception as permanent.
   - **Required behavior:** The job moves to exhausted/dead-letter state without
     further automatic retry.

10. **Crash after side effect and before completion**
    - **Condition:** Worker execution is interrupted after a handler begins and
      before the success transition commits.
    - **Required behavior:** The database still shows an active or eventually
      expired lease rather than false success. Re-execution is possible under
      at-least-once semantics, and handler idempotency remains mandatory.

11. **Shutdown while idle**
    - **Condition:** Shutdown is requested while the worker is polling or idle.
    - **Required behavior:** The worker stops claiming work, records safe
      stopped heartbeat state, and exits without marking any job failed.

12. **Shutdown while leased**
    - **Condition:** Shutdown is requested while the worker owns a job.
    - **Required behavior:** The worker finishes the current completion path if
      safe, or durably releases/lets expire the lease without claiming new work.

13. **Unsafe diagnostics**
    - **Condition:** Payloads, provider IDs, user identifiers, request IDs,
      correlation IDs, raw exceptions, or secrets appear in diagnostic metadata.
    - **Required behavior:** The public/operator summary stores only approved
      safe fields and bounded labels; sensitive or high-cardinality values are
      rejected or redacted.

14. **Final-provider substitution**
    - **Condition:** Implementation tries to use Render, Vercel, Neon, CI,
      local settings, framework defaults, or example values as final worker
      hosting proof.
    - **Required behavior:** Reject the claim. Keep final worker hosting and
      runtime proof assigned to the deferred follow-up.

15. **Long-running handler with healthy heartbeat**
    - **Condition:** A handler runs longer than one initial lease duration while
      the worker remains healthy.
    - **Required behavior:** Token-guarded heartbeat renewals extend the lease
      before expiry without incrementing attempts. Another worker cannot claim
      the job while the renewed lease remains valid.

16. **Expired final attempt**
    - **Condition:** A lease expires after `attempt_count` has reached
      `maximum_attempts`.
    - **Required behavior:** Recovery transitions the job to `exhausted` with
      safe lease-expiry metadata. No worker can create attempt
      `maximum_attempts + 1`, and the expired token cannot mutate the job.

17. **Backlog starvation pressure**
    - **Condition:** A lower-priority compatible job remains eligible while a
      continuous stream of newer higher-priority jobs arrives.
    - **Required behavior:** Once the older job crosses `fairness_age`, it is
      fairness-protected and is selected ahead of non-aged work. Sustained
      priority traffic cannot starve it indefinitely while workers continue
      claiming.

## 5. Testing

This section defines what the tests must prove. The proof must exercise the
real PostgreSQL behavior for concurrency and persistence because static
inspection cannot prove lease or claim correctness.

### 5.1 Data Model And Migration Tests

Tests must prove the new tables, constraints, indexes, foreign keys, JSON
defaults, timestamp behavior, and status invariants work in PostgreSQL.
Migration compatibility tests must include the new tables in the current
linear migration chain and must preserve the accepted migration policy.

### 5.2 Enqueue And Idempotency Tests

Tests must prove successful enqueue, duplicate enqueue, conflicting enqueue,
unsupported job type rejection, unsafe payload rejection, transaction rollback,
and no worker/provider side effect during enqueue.

### 5.3 Claim, Lease, Heartbeat, And Concurrency Tests

Tests must use independent PostgreSQL sessions to prove:

- one job cannot be claimed by two workers;
- unaged eligible jobs use deterministic priority/availability order;
- an aged fairness-protected job is selected ahead of newer unaged work even
  under sustained higher-priority arrivals;
- locked rows are skipped rather than blocking unrelated work;
- claim filtering skips type/version pairs unsupported by the worker registry
  without mutating or incrementing attempts on those rows;
- heartbeat requires the current unexpired lease token;
- a valid heartbeat extends lease expiry without incrementing attempt count;
- a heartbeat at or after lease expiry cannot resurrect the lease;
- stale leases with attempts remaining can be recovered;
- expiry at the maximum attempt boundary becomes exhausted rather than creating
  an additional attempt;
- stale lease tokens cannot heartbeat, complete, retry, release, cancel, or
  exhaust a recovered/expired job; and
- process-local locks are not the correctness mechanism.

### 5.4 Worker Execution Tests

Tests must use synthetic handlers to prove success, transient failure, permanent
failure, retry waiting, final-attempt exhaustion, malformed payload, handler
exception classification, event history, safe result metadata, and lease loss
during execution.

Version-overlap tests must use at least two synthetic worker registries. An
older registry that supports only an earlier payload version must leave newer
version work untouched and available, while a compatible newer registry can
claim and execute it. The unsupported worker must not increment attempts or
write failure history merely by encountering that work.

The synthetic handlers prove the framework. They must not become production
payment, refund, credit, notification, moderation, storage, or provider
handlers.

### 5.5 Shutdown And Runtime Boundary Tests

Tests must prove import/app construction does not start the worker, the worker
command supports deterministic single-iteration execution, shutdown stops new
claims, and worker heartbeat state changes predictably. Existing runtime
topology tests must be updated so the approved portable worker command is no
longer treated as an accidental final deployment topology.

### 5.6 Diagnostics And Operator Visibility Tests

Tests must prove backlog summaries, aged/fairness-protected backlog, queued
type/version combinations unsupported by the inspecting worker registry,
expired lease counts, exhausted job visibility, recent event history, worker
heartbeat summaries, and safe diagnostic metadata. Sensitive or
high-cardinality values must not become telemetry labels or public/operator
diagnostics.

### 5.7 Compatibility And Regression Tests

Validation must include the focused durable-job test scope, backend checker
scope for the new requirement declaration and testing record, affected runtime
compatibility tests, accepted migration compatibility tests, accepted database
value/SQL-safety tests for the new SQL surface, and the relevant provider retry
handoff tests that prove WS05 handoff metadata still points to later durable
work rather than obsolete assumptions.

Provider sandbox tests, deployed worker tests, dashboards, alert delivery,
final database connection budget proof, and final worker hosting proof are not
valid evidence for this pass because their required infrastructure is not yet
selected.

## 6. Done When

This section defines the engineering completion bar for this pass.

- [ ] PostgreSQL has durable job, job-event, and worker-heartbeat state with
      constraints that reject impossible lifecycle combinations.
- [ ] Job enqueue is idempotent, transactional with caller-owned database work,
      and side-effect-free.
- [ ] Independent PostgreSQL sessions prove atomic claim, lease token, heartbeat
      renewal, stale lease recovery, maximum-attempt enforcement, and
      duplicate-worker protection.
- [ ] Mixed worker versions can overlap without an incompatible worker claiming,
      consuming an attempt for, or exhausting otherwise valid newer-version
      work.
- [ ] Backlog fairness prevents an older compatible job from starving
      indefinitely behind a continuous stream of newer higher-priority work.
- [ ] Worker execution supports registered handler success, retry, permanent
      failure, exhaustion, malformed payload, lease-loss handling, and
      at-least-once recovery semantics.
- [ ] Retry and repair behavior is bounded by explicit job definitions and does
      not invent final production worker, payment, provider, or storage
      policies.
- [ ] A portable worker command can run deterministically without starting on
      app import or relying on final provider hosting.
- [ ] Operator inspection surfaces backlog, leases, exhausted jobs, attempts,
      worker heartbeat state, and safe recent history without leaking sensitive
      data.
- [ ] Accepted runtime, database, migration, SQL-safety, transaction, retry, and
      correlation compatibility tests remain true after the approved worker
      foundation is introduced.
- [ ] The requirement declaration and testing record describe the durable-job
      scope, evidence, deferrals, and adequacy without claiming final deployed
      worker proof.
- [ ] The accepted-state register records `WS05-01A` as accepted on merge,
      keeps `WS05-01B` mandatory and deferred, and keeps `WS05-01` incomplete
      until that deferred follow-up is accepted or otherwise truthfully
      resolved.
