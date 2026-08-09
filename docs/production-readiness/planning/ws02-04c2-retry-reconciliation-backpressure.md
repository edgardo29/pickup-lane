# WS02-04C2 Retry Reconciliation And Backpressure

Pass: WS02-04C2

Scope: portable, source-owned retry ownership, provider reconciliation safety,
and current fanout/backpressure policy for backend provider and notification
boundaries.

## Approved Architecture

C2 does not add application-owned retry attempts, retry backoff, retry jitter,
scheduled retries, durable jobs, queues, worker leases, worker heartbeats,
semaphores, provider concurrency caps, rate limits, trusted-IP logic, or
permanent hosting topology.

C2 records current source-owned policy only:

| Class | Meaning |
|---|---|
| `SAFE_READ` | Provider read/query timeout may return retry-later semantics without local mutation. |
| `IDEMPOTENT_MUTATION` | Existing stable workflow identity makes replay safe when the caller deliberately re-enters the workflow. |
| `RECONCILE_BEFORE_RETRY` | Provider mutation outcome may be unknown and must be re-observed or manually repaired before another mutation. |
| `MANUAL_REPAIR` | Existing explicit admin/support workflow owns retry or reconciliation. |
| `PROVIDER_REDELIVERY` | Provider transport owns delivery retry and the application remains idempotent. |
| `NO_AUTOMATIC_RETRY` | Current workflow lacks durable identity or evidence required for application retry. |

The source-owned registry lives in `backend/services/provider_retry_policy.py`.
It is evidence and review scaffolding, not a generic retry framework.

## Dependency Retry Ownership

Current provider retry behavior remains dependency-owned unless explicitly
configured by Pickup Lane source.

| Dependency | Installed version | C2 ownership |
|---|---:|---|
| Stripe Python SDK | 15.1.0 | Dependency-owned retry behavior; Pickup Lane configures read and mutation timeouts only. |
| Firebase Admin SDK | 7.4.0 | Dependency-owned retry behavior; Pickup Lane configures Firebase Admin HTTP timeout only. |
| Botocore | 1.35.99 | Dependency-owned retry behavior; Pickup Lane configures R2 metadata connect/read timeouts only. |
| SQLAlchemy | 2.0.49 | Application rollback/session policy only; no transparent transaction retry count or backoff is approved. |

Provider SDK version changes must trigger WS02-04C2 retry-policy review. Tests
assert the installed dependency versions to make that review visible.

## Stripe Reads

Stripe retrieval operations remain safe reads:

- SetupIntent retrieval
- PaymentMethod retrieval
- PaymentIntent retrieval
- refund/reconciliation retrieval

Read timeouts keep C1 dependency-read semantics. C2 does not add application
retry loops around reads and does not perform local mutation from incomplete
provider state.

## Stripe Mutations

Stripe mutations are classified individually:

| Operation | C2 class | Current ownership |
|---|---|---|
| customer creation | `IDEMPOTENT_MUTATION` | Existing user-scoped idempotency key supports deliberate replay. |
| SetupIntent creation | `NO_AUTOMATIC_RETRY` | Current idempotency key is request-local; durable identity would require later persistence. |
| PaymentIntent creation | `IDEMPOTENT_MUTATION` | Existing payment-row idempotency key supports deliberate replay. |
| PaymentIntent confirmation | `RECONCILE_BEFORE_RETRY` | Confirmation has unknown-outcome risk and must be re-observed before another mutation. |
| refund creation | `IDEMPOTENT_MUTATION` | Existing refund workflow, idempotency key, events, money issues, and admin reconcile remain authoritative. |
| saved-card default | `RECONCILE_BEFORE_RETRY` | Unknown outcome must not be blindly repeated. |
| saved-card detach | `RECONCILE_BEFORE_RETRY` | Unknown outcome must not be blindly repeated. |

C2 preserves C1 mutation-timeout UNKNOWN semantics. It does not make all Stripe
mutations behave identically.

## Idempotency Ownership

PaymentIntent creation and refund creation already have stable source-owned
identities that can make deliberate workflow replay safe.

SetupIntent creation does not have durable request identity today. The current
source creates a request-local provider idempotency key. C2 therefore documents
this as no automatic retry. A durable SetupIntent identity belongs to later
storage-backed work if the product needs app-owned retry.

Arbitrary idempotency keys that cannot survive real client or process retry are
not approved.

## Unknown Outcomes

Outcome-sensitive provider mutations must not be blindly replayed after timeout
or transport uncertainty. Current policy is:

- return unknown-outcome semantics when C1 wrappers cannot prove final provider
  state
- preserve local pending, support, event, or issue records where the current
  workflow already owns them
- re-observe provider/local state before another mutation when safe identifiers
  already exist
- use manual repair where current architecture makes that the authoritative path

C2 does not build durable reconciliation workers.

## Refunds

Refund retry and reconciliation remain explicit admin workflows. They are
state-gated and preserve refund idempotency, row locking, refund events, money
issues, and admin-visible outcomes. C2 does not convert refund repair into
background retry.

## Saved Cards

SetupIntent sync may re-read provider state. Default-card and detach mutations
receive no application retry loop. Unknown outcomes remain reconcile/support
paths, with existing local/provider ownership checks preserved.

## Firebase Account Deletion

Firebase token verification and user lookup are safe reads. Firebase user
deletion is an unknown-outcome mutation on timeout. Existing pending deletion,
checkpoint, support flag, and safe re-entry behavior remain the recovery path.

C2 does not add automatic Firebase deletion retry or a durable account cleanup
worker.

## Stripe Webhooks

Stripe webhook transport retry remains provider redelivery. Pickup Lane keeps
provider event identity dedupe and idempotent processing. C2 does not introduce
scheduled internal webhook retries or generic retry wrapping.

## R2

R2 C2 scope is metadata HEAD retry ownership only. Botocore retry behavior
remains dependency-owned, and Pickup Lane does not configure retry mode or retry
attempt counts. Direct browser uploads and durable object reconciliation remain
outside C2.

## Backpressure And Fanout

Current fanout policy is synchronous and sequential:

- Platform Notice selected-user publish creates database recipient records
- game chat creates database notification rows
- Need-a-Sub chat creates database notification rows
- waitlist promotion follows current locked business workflow
- account deletion cleanup iterates current owned records and provider cleanup

No unbounded provider task fanout is approved. Concurrency must not be
introduced without evidence-backed caps and later owner decisions. Existing
product limits such as a selected-audience maximum are not worker batch sizes,
provider fanout limits, retry batches, or concurrency caps.

## WS05 Durable Work Handoff

C2 records future durable-work needs without designing their tables, leases,
schedulers, or worker topology:

- provider unknown-outcome reconciliation where request-local recovery is not
  enough
- account deletion cleanup recovery
- future external notification delivery
- future Platform Notice external delivery
- durable financial reconciliation if manual repair becomes insufficient

Required durable properties include claimable work identity, stable replay
references, idempotent handlers, bounded retry policy, operator-visible
exhausted states, safe re-entry, and redacted telemetry.

No worker retry attempts, worker concurrency, lease duration, poison threshold,
or scheduler cadence is approved by C2.

## Telemetry

C2 may use existing EN-02 primitives only with bounded labels such as operation
class, retry-safety class, outcome class, reconciliation result class, and
dependency/app ownership class.

C2 does not log provider identifiers, payment IDs, user IDs, URLs, request
bodies, provider responses, raw exceptions, or arbitrary error text.

## API-M10 And API-M11 Status

WS02-04C2 partially closes API-M10 for portable retry/reconciliation ownership
and unknown-outcome safety. API-M10 remains partial until rate/backpressure,
provider/runtime evidence, durable reconciliation, and permanent hosting
alignment are complete.

WS02-04C2 provides source-owned evidence for current sequential fanout policy
but does not close API-M11. C3 owns rate and abuse controls. WS05 owns durable
worker and job execution.

## Evidence

Current non-legacy tests cover:

- retry-safety class inventory
- installed dependency version review triggers
- no Pickup Lane provider retry counts
- Stripe read versus mutation classification
- SetupIntent creation no automatic retry without durable identity
- no blind app retry for unknown provider mutations
- manual refund/reconcile ownership
- Firebase, webhook, and R2 classifications
- mutation timeout wrappers do not call providers twice
- sequential fanout policy and no unbounded async task creation
- durable-work handoff without worker numbers

Provider tests use fakes only and do not call live providers.
