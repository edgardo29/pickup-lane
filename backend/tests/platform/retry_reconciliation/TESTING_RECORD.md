# WS02-04C2 Retry Reconciliation And Backpressure Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-04C2` |
| Trusted test scope | `backend/tests/platform/retry_reconciliation/` |
| Requirement declaration | `backend/tests/support/requirements/ws02_04c2.json` |
| Authoritative sources | Canonical WS02-04C2 plan, current backend provider/payment source, accepted C1 timeout contract, accepted B2A2B2 payment-input ownership, accepted WS03-02 account-deletion ownership, EN-02 safe metadata boundaries, WS05 durable-work ownership |
| Evidence layers | pytest, PostgreSQL for persisted payment/refund/webhook state, provider fakes at app-owned seams, static source inventory, deferred governance |

## 1. Scope

This record covers Pickup Lane's current source-owned retry,
reconciliation, provider-redelivery, and fanout/backpressure evidence for C2.
It verifies that the retry-policy registry is declarative and workflow-aware,
that provider mutation replay is classified by durable identity, that checkout
PaymentIntent confirmation is preceded by a durable local checkpoint and
serialized provider re-read, and that current
provider/webhook/manual-repair/fanout boundaries stay explicit.

This scope intentionally does not close live provider retry behavior, provider
dashboard settings, production endpoint reachability, rate or abuse limits,
generic retry framework design, durable worker implementation, worker leases,
worker retry counts, queue topology, global request/response deadlines,
database connection budgeting, browser behavior, migration evidence, telemetry
dashboards, alerts, or runtime load evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-04C2-R1` | Retry policy stays source-owned, truthful, and non-executing. | pytest |
| `WS02-04C2-R2` | Dependency retry ownership and version reassessment triggers stay explicit. | pytest |
| `WS02-04C2-R3` | Current runtime provider/outbound operations are inventoried and classified. | pytest |
| `WS02-04C2-R4` | Safe reads and mutation unknown outcomes keep distinct replay semantics. | pytest |
| `WS02-04C2-R5` | Idempotency is classified by durable replay identity, not key presence alone. | pytest and PostgreSQL |
| `WS02-04C2-R6` | Unknown-outcome recovery requires reconciliation or state-gated manual repair before another mutation. | pytest and PostgreSQL |
| `WS02-04C2-R7` | Stripe webhook delivery remains provider redelivery plus local idempotency. | pytest and PostgreSQL |
| `WS02-04C2-R8` | Current fanout/backpressure policy is synchronous, sequential, and inventory-backed. | pytest/static |
| `WS02-04C2-R9` | Durable-work handoffs remain explicit and WS05-owned. | pytest/static |
| `WS02-04C2-R10` | Runtime telemetry labels and static registry prose remain separate and safe. | pytest/static |
| `WS02-04C2-R11` | Later/runtime/provider/rate/durable-worker evidence remains deferred. | deferred with zero pytest mappings |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R5`, `R6` | One provider operation may have multiple workflow-specific retry meanings. | Registry silently treats all Stripe `payment_intent.create` calls as replay-safe. | Duplicate money movement or false recovery confidence. | Workflow context, durable-identity fields, and ambiguous lookup failure. | platform |
| `R2` | Dependency versions are visible reassessment triggers only. | Local source claims exact SDK retry counts or adds unreviewed retry mode/backoff. | GOV-006 numeric authority is bypassed. | Version comparison and negative static retry-policy checks. | platform |
| `R3`, `R4` | Runtime provider reads and mutations are classified without hidden outbound bypasses. | A new provider/network path avoids C1/C2 ownership. | Unbounded or unsafe provider retry behavior. | Static production-source inventory and registry coverage. | platform |
| `R5`, `R6` | Checkout stores provider PaymentIntent identity before confirmation and reacquires game serialization before post-checkpoint confirmation. | Confirmation timeout rolls back the provider ID, credit reservation context, or lock release allows two stale confirmation decisions. | Re-entry can create a second provider identity, duplicate credit reservation, or duplicate confirmation decision. | PostgreSQL checkout checkpoint and deterministic serialization tests with Stripe fakes. | platform |
| `R6` | Unknown provider outcomes stay pending/processing/support-owned until reconciled. | Timeout is marked definite success/failure or replayed blindly. | Duplicate charges/refunds/card detach/account cleanup or misleading support state. | C1 timeout exceptions, state-gated repair tests, and registry classifications. | platform |
| `R7` | Webhook redelivery is provider-owned transport plus local idempotency. | Duplicate provider events reprocess side effects or local tests claim live Stripe behavior. | Duplicate payment/refund state or false provider-dashboard closure. | Provider event ID requirement, unique-event handling, and explicit non-closure. | platform |
| `R8` | Current fanouts remain synchronous/sequential with no approved parallel provider fanout. | Source introduces background tasks, thread/process pools, or async fanout. | Request-local work becomes unbounded or externally expensive. | Registry inventory and static source checks for unapproved concurrency constructs. | platform |
| `R9`, `R11` | Durable recovery needs are named but not implemented by C2. | Local tests are mistaken for worker topology, leases, retries, or poison policy. | False production-readiness closure. | WS05 handoff registry and deferred R11 declaration. | governance/platform |
| `R10` | Static policy prose is not runtime telemetry, and future labels must be bounded. | Registry prose leaks private data or runtime telemetry is inferred where none exists. | Privacy leak or EN-02 regression. | Sensitive-marker scan and no direct C2 telemetry emission proof. | platform |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | backend service, provider, admin/support, provider webhook, account-deletion cleanup | grouped | C2 owns retry/reconciliation boundaries, not broad authorization. |
| States / lifecycle | safe read, create-timeout unknown, confirmation-unknown, pending checkout, stale checkout, processing refund, duplicate webhook event, deferred worker | covered/deferred | These are the material C2 replay and recovery states. |
| Actions | provider read, provider mutation, checkout create/confirm/retrieve, refund retry/reconcile, webhook ingest, fanout loop | covered | Current runtime operations are inventoried and tested at app-owned seams. |
| Inputs / boundaries | provider IDs, idempotency keys, operation contexts, static prose, telemetry labels | covered | Durable identity and sensitive metadata are core C2 risks. |
| Time | active checkout hold and deterministic stale expiry | covered/grouped | Tests use explicit expired timestamps and no arbitrary sleeps. |
| Dependencies | Stripe, Firebase Admin, R2, SQLAlchemy/PostgreSQL | covered/grouped | Providers are faked; PostgreSQL is used where persisted state matters. |
| Concurrency / idempotency | checkout active-hold serialization, duplicate webhook IDs, replay identity, no blind second provider call | covered/deferred by owner | C2 includes one deterministic PostgreSQL checkout serialization proof; deterministic webhook concurrency remains deferred. |
| Authorization / privacy / security | admin repair ownership, account deletion support state, safe static prose | covered/grouped | Broader role permissions belong to owning workflow passes. |
| Persistence / rollback | durable checkpoint, credit reservation, stale release, refund/event state gates | covered | Mutations verify meaningful persisted effects and prohibited side effects. |
| Recovery | active-hold re-entry, manual repair, provider redelivery, WS05 handoff | covered/deferred | C2 proves current source handoffs; durable worker execution remains later. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing workflow context in ambiguous lookup | pytest |
| empty | yes | missing provider event ID | pytest |
| corrupt | yes | unsafe retry prose or invented provider/network path | static pytest |
| exceed | no | C2 approves no retry/backpressure numeric limit | deferred |
| duplicate | yes | webhook event ID, active-hold re-entry, credit reservation | PostgreSQL pytest |
| delay | yes | mutation timeout unknown and stale checkout expiry | pytest with fakes/explicit time |
| reorder | no | no ordered event stream claim beyond local idempotency | not applicable |
| interrupt | yes | provider mutation timeout before or after checkpoint | pytest with fakes |
| race | yes, narrowly | checkout active-hold confirmation serialization | PostgreSQL pytest with independent sessions and barriers/events |
| expire / revoke | yes | stale checkout expiration | PostgreSQL pytest |
| tamper | yes | caller cannot fabricate retry identity from request-only state | pytest/static |
| retry | yes | safe read versus mutation replay classification | pytest |
| recover | yes | re-read, manual repair, provider redelivery, WS05 handoff | pytest/deferred |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1` | retry classes, non-executing registry, workflow lookup integrity, no numeric retry policy | pytest/static | `test_retry_policy_registry_contract.py` | Adequate for source-owned registry truth; not a runtime retry framework. |
| `R2` | dependency version triggers and no source-configured retry/backoff/jitter | pytest/static | `test_dependency_retry_ownership_contract.py` | Adequate for repository dependency authority; does not claim SDK internals. |
| `R3`, `R4` | production provider/outbound inventory and safe read/mutation split | pytest/static | `test_c2_provider_operation_inventory_contract.py`, registry tests | Adequate for current runtime source; manual tooling and browser/direct provider behavior remain outside C2. |
| `R5`, `R6` | checkout idempotency identity, post-create checkpoint, serialized confirmation resume, confirmation-unknown, active-hold re-entry, stale expiration | PostgreSQL with Stripe fakes | `test_idempotency_replay_contract.py`, `test_unknown_outcome_no_blind_replay_contract.py` | Proves persisted state, locked provider re-read before confirmation, and no duplicate external mutation at app-owned seams; does not claim durable post-expiry reconciliation. |
| `R6` | manual repair, saved-card/account-deletion recovery, refund/money issue ownership | pytest/PostgreSQL/static | `test_manual_repair_reconciliation_contract.py` | Representative current state-gated recovery is covered; no background worker is invented. |
| `R7` | signed webhook seam, provider event ID requirement, duplicate and IntegrityError paths, local idempotency | PostgreSQL and fakes | `test_webhook_redelivery_idempotency_contract.py` | Adequate for repository-owned webhook idempotency; does not prove live Stripe redelivery or races. |
| `R8` | fanout inventory and no hidden parallel/background fanout | pytest/static | `test_fanout_backpressure_contract.py` | Adequate for current source inventory; no provider concurrency or worker limit is approved. |
| `R9`, `R10` | WS05 durable handoffs, no retry telemetry emission, safe static prose | pytest/static | `test_durable_handoff_and_metadata_contract.py` | Adequate for source-owned metadata/handoffs; telemetry dashboards and worker design remain later. |
| `R11` | external/later closure boundaries | declaration and record | `ws02_04c2.json`, this record | Correctly remains deferred and zero-mapped. |

### Evidence Quality Checks

- Time-boundary evidence uses explicit stale timestamps instead of sleeps.
- Successful checkout mutation evidence proves persisted Booking, Payment,
  pending participant/capacity, provider PaymentIntent ID, idempotency key,
  reserved `GameCreditUsage`, and decremented `GameCredit.available_cents`.
- Rejected/timeout paths prove prohibited effects such as confirmation after
  create-timeout, duplicate PaymentIntent creation, duplicate credit
  reservation, definite success/failure after confirmation-unknown, and erased
  provider identity did not occur.
- Idempotency tests prove persisted and external effects are not duplicated for
  active-hold checkout re-entry, serialized checkout confirmation, and webhook
  duplicates.
- PostgreSQL is used for persisted checkout, refund, credit, and webhook state
  where static source proof would be insufficient.
- The checkout serialization proof uses independent sessions/application
  requests and barriers/events, not arbitrary sleeps, to prove a competing
  request cannot reach create or confirm while another request owns the locked
  confirmation decision.
- Stripe/Firebase/R2 behavior is faked or inspected at application-owned
  wrapper boundaries; no live provider is called.
- Database-constraint proof is used for provider-event uniqueness where the
  database exposes reliable identifying evidence.
- Registry tests resolve every declared material caller to a current source
  symbol so provider-backed retry policy metadata cannot drift to stale dotted
  paths.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Checkout PaymentIntent create succeeds | Pending Booking/participants, Payment idempotency key, provider PaymentIntent ID, capacity hold, reserved credits, and decremented available credit are committed before confirmation. | Confirmation must not begin before the checkpoint exists or from an unlocked stale checkout view. | Initial request and active-hold re-entry both reacquire game serialization, reload persisted state, and re-read provider state before confirmation. |
| Checkout PaymentIntent create times out | Pending Booking/participants, Payment idempotency key, reserved credit checkpoint, `unknown` local payment state, and reconcile job remain committed. | No confirmation, no ordinary success response, and no claimed provider ID. | Durable local identity survives for status/reconciliation; app-owned blind replay remains prohibited. |
| Checkout confirmation times out | Durable checkpoint survives with `unknown` local payment state, active hold, provider ID, reserved credits, and reconcile job. | No definite success/failure, no second confirm in same request, no erased provider identity. | Re-entry retrieves provider state first. |
| Active-hold re-entry | Same Booking/Payment/provider PI is found; provider read occurs before confirm decision while game serialization is owned. | No second PaymentIntent create, no second credit reservation, and no stale duplicate confirmation decision. | Idempotency is the persisted local checkout identity. |
| Stale checkout expiration | Local booking/participant state expires, capacity releases, reserved credits release, and unresolved payment truth is preserved. | Payment row and provider PaymentIntent ID are not erased; no provider cancellation or failed payment outcome is claimed. | WS05 owns durable post-expiry provider reconciliation. |
| Admin refund repair | State-gated retry/reconcile records enforce uncertain-provider checks. | No blind refund retry when provider outcome is uncertain. | Admin action/idempotency and refund events own repair evidence. |
| Stripe webhook duplicate | Existing event or provider-event unique conflict returns idempotent result. | No reprocessing or scheduled internal webhook retry. | Provider redelivery plus local uniqueness/idempotency. |
| Fanout inventory | Current work remains synchronous/sequential. | No unapproved background tasks, thread/process pools, or parallel provider fanout. | Product audience bounds are not worker policy. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-04C2-R11` | deferred | Rate controls, abuse controls, provider dashboards, live retry behavior, permanent runtime topology, durable workers, global deadlines, DB connection budgets, load evidence, telemetry dashboards, alerts, and provider concurrency limits cannot be proven by local C2 source tests. | WS02-04C3A/B, WS04, WS05, WS06, WS09, WS10, provider/runtime evidence |
| Checkout post-expiry provider reconciliation | deferred | C2 preserves provider identity and local release semantics but does not implement a durable worker or delayed provider comparison. | WS05 |
| Live Stripe webhook delivery/redelivery schedule | deferred | Local tests prove signed ingestion and duplicate handling only. | Provider evidence / operations |
| Deterministic concurrent webhook duplicate race | deferred | C2 proves DB uniqueness and duplicate-insert handling, not a real concurrent race. | Later database/payment owner if required |
| External notifications and provider delivery | deferred | Current source creates in-app rows only. | WS05 / notification delivery owner |
| Telemetry dashboards and alerts | deferred | C2 proves no direct retry telemetry emission and safe prose boundaries only. | WS09 |

## 9. Adequacy Conclusion

The selected evidence is adequate for the frozen WS02-04C2 Gate B scope when
focused C2, C1 regression, adjacent payment/API/observability regression, full
trusted backend, checker/domain/suite, traceability, compile, and diff checks
pass.

`WS02-04C2-R1` through `WS02-04C2-R10` must have executable trusted evidence
under `backend/tests/platform/retry_reconciliation/`. `WS02-04C2-R11` is
intentionally deferred and must remain zero-mapped. Checker `PASS` is
structural compliance evidence only; human Gate C review must still confirm
semantic adequacy and ensure C2 does not overclaim provider, runtime, durable
worker, dashboard, or live telemetry closure.
