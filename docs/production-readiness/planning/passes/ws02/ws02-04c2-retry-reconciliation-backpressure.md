# WS02-04C2 - Retry Reconciliation And Backpressure

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-04C2` |
| Track | `WS02-04` source-owned API boundary recheck |
| Type | Backend provider retry/reconciliation policy, fanout/backpressure inventory, and trusted evidence reconstruction |
| Primary controls | `API-M10`, `JOB-M05`, `PAY-002`, `GOV-006` |
| Supporting controls | `API-M11`, `FDN-04`, `API-M12`, `API-M19`, `DB-002`, `WS02-04C1`, `WS02-04C3A`, `WS02-04C3B`, `WS05` |
| Authority basis | Current accepted repository tree; `API-M10`; `API-M11`; `JOB-M05`; `PAY-002`; `GOV-006` / `FDN-04`; `docs/production-readiness/governance/limits-and-thresholds-register.md`; `docs/production-readiness/planning/passes/ws02/ws02-04-source-owned-closeout.md`; accepted `WS02-04C1`; accepted payment/provider request-ownership passes; accepted account-deletion ownership; WS05 durable-work ownership |
| Depends on | `EN-01`; `EN-02`; `WS02-01`; `WS02-04A`; `WS02-04B1`; `WS02-04B2A2B2`; `WS02-04C1`; `WS03-02` |
| Trusted test scope | `backend/tests/platform/retry_reconciliation/` |

## 1. Purpose

WS02-04C2 defines Pickup Lane's source-owned retry, reconciliation, and
fanout/backpressure policy for current backend provider and notification
boundaries.

In plain terms, this pass decides when the backend may safely try something
again, when it must first check provider or local state, when a human repair
workflow owns recovery, and when durable background work must remain a later
WS05 obligation.

C2 does not add a generic retry framework. It does not approve application
retry counts, backoff, jitter, worker leases, worker retry counts, worker
concurrency, queue topology, provider concurrency caps, provider dashboard
settings, live provider retry behavior, or rate limits. It records the current
truth, corrects stale retry-policy declarations, and adds trusted evidence so
future changes cannot silently claim unsafe replay behavior.

The source-owned registry is `backend/services/provider_retry_policy.py`. It is
a production policy artifact and review registry. It is not called by runtime
business workflows, and it must not be mistaken for executable retry behavior.

## 2. Why This Matters

Retries are dangerous when a provider operation may already have happened.
For example, if Pickup Lane sends a Stripe payment or refund mutation and the
request times out, the provider might still create the object. Retrying blindly
can duplicate money movement, detach a payment method twice, erase useful
recovery state, or mislead support staff about what actually happened.

Reads and mutations therefore have different safety. A provider read that times
out can usually be tried later because it did not ask the provider to change
state. A provider mutation timeout is an unknown outcome: Pickup Lane knows
that it sent or attempted the mutation, but it does not know whether the
provider accepted, rejected, completed, or will later complete it.

An idempotency key helps only when the identity behind that key is durable
enough for the real retry path. A key generated from a committed user or refund
identity can support deliberate replay. A key generated inside one request from
rows that are rolled back after timeout does not prove safe replay from a later
client request.

Fanout also matters. A single request that loops over recipients, waitlist
entries, saved cards, payments, or refunds can produce a lot of work. C2 records
the current source policy: current fanout is synchronous and sequential, and no
new parallel fanout or provider task fanout is approved without a later
evidence-backed owner decision.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-04C2-R1` | Retry policy is source-owned, truthful, and non-executing. | `backend/services/provider_retry_policy.py` remains a production policy/review registry, not a retry framework. Every class and entry must describe current source truth, and registry drift is a test failure. | Prevents stale declarations from creating false confidence about retry safety. |
| `WS02-04C2-R2` | Dependency retry ownership is explicit and version-triggered. | Stripe, Firebase Admin, Botocore, and SQLAlchemy versions in the registry must match repository dependency authority. Pickup Lane must not claim exact dependency retry schedules unless source-owned configuration proves them. | Keeps SDK-owned retry behavior visible without inventing retry counts or backoff. |
| `WS02-04C2-R3` | Runtime provider and outbound operation inventory is complete for C2 scope. | Current production application/runtime Stripe, Firebase Admin, R2, webhook, and other outbound/provider operations must be represented, classified, or explicitly assigned to another owner. Manual bootstrap, seed, and maintenance scripts are operational tooling, not runtime API retry policy. | Prevents hidden runtime provider paths from escaping retry/reconciliation ownership. |
| `WS02-04C2-R4` | Reads and provider mutations keep separate replay semantics. | Safe provider reads may return retry-later semantics. Provider mutation timeouts remain unknown outcomes under the accepted C1 contract. C2 must not reinterpret unknown mutation timeouts as definite failure. | Prevents local timeout handling from causing duplicate or misleading provider state. |
| `WS02-04C2-R5` | Idempotency keys are classified by durable identity, not mere presence. | Provider idempotency key usage must record where the key comes from, whether it survives the real deliberate replay path, and which hold/reconciliation boundary owns it. Request-local or rolled-back identities cannot be called stable client replay. | Prevents a Stripe idempotency option from being mistaken for safe application retry. |
| `WS02-04C2-R6` | Unknown-outcome recovery uses reconciliation or manual repair before another mutation. | Saved-card mutations, payment confirmation, refund repair, Firebase deletion, late payment refunds, and other unknown-outcome paths must preserve state-gated recovery and avoid blind replay. Checkout confirmation-unknown safety is guaranteed during the active checkout hold; durable post-expiry reconciliation remains WS05-owned. | Protects money movement, account cleanup, capacity, reserved credits, and saved-card state after uncertain provider results. |
| `WS02-04C2-R7` | Stripe webhook delivery is provider-redelivery plus app idempotency, not app retry. | The repository-owned proof is signed webhook ingestion, event ID dedupe, unique-provider-event handling, and idempotent local processing. Provider dashboard delivery and live redelivery schedules remain external. | Prevents C2 from claiming provider-runtime facts the repository cannot prove. |
| `WS02-04C2-R8` | Current fanout/backpressure policy is synchronous, sequential, and inventory-backed. | Platform notices, game chat, Need-a-Sub chat, game update notices, waitlist promotion, account deletion cleanup, and refund/payment loops must be inventoried with current bounds and provider-call behavior. New parallel fanout is not approved. | Prevents a request from silently becoming unbounded parallel work or provider fanout. |
| `WS02-04C2-R9` | Durable-work handoffs are explicit and owned by WS05. | Provider unknown-outcome reconciliation, account cleanup recovery, external notification delivery, platform notice external delivery, and durable financial reconciliation record required durable properties without designing worker internals. | Keeps current C2 honest while preserving the later durable job owner. |
| `WS02-04C2-R10` | Runtime telemetry labels and static policy prose have separate safety rules. | C2 currently emits no retry-policy telemetry directly. Any future emitted telemetry or event labels must use bounded EN-02-safe class values. Static registry descriptions may contain concise non-sensitive policy prose, but must not contain secrets, private identifiers, raw provider payloads, raw exceptions, credentials, or sensitive request content. | Preserves EN-02 privacy guarantees without pretending human-readable registry descriptions are runtime telemetry. |
| `WS02-04C2-R11` | Later and external retry/backpressure evidence remains explicit. | Rate controls, abuse controls, provider dashboards, live provider retry behavior, permanent runtime topology, durable workers, global request deadlines, DB connection budgets, load evidence, telemetry dashboards, alerts, and provider concurrency limits remain later or external. | Prevents local source tests from falsely closing runtime, provider, rate, or durable-job obligations. |

### Requirement Declaration Design

Gate B must create `backend/tests/support/requirements/ws02_04c2.json` with
this exact machine declaration design:

| Requirement ID | State | Scope | `source_controls` | Reason |
|---|---|---|---|---|
| `WS02-04C2-R1` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "GOV-006", "FDN-04", "WS02-04C2", "WS02-01"]` | Not required. |
| `WS02-04C2-R2` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "GOV-006", "FDN-04", "WS02-04C2", "WS02-04C1"]` | Not required. |
| `WS02-04C2-R3` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "PAY-002", "GOV-006", "WS02-04C1", "WS02-04C2", "WS02-04B2A2B2", "WS03-02"]` | Not required. |
| `WS02-04C2-R4` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "PAY-002", "GOV-006", "WS02-04C1", "WS02-04C2"]` | Not required. |
| `WS02-04C2-R5` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "PAY-002", "GOV-006", "WS02-04C2", "WS02-04B2A2B2", "WS05"]` | Not required. |
| `WS02-04C2-R6` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "PAY-002", "GOV-006", "WS02-04C2", "WS02-04C1", "WS02-04B2A2B2", "WS03-02", "WS05"]` | Not required. |
| `WS02-04C2-R7` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "PAY-002", "GOV-006", "WS02-04C2", "WS02-04B2A2B2", "WS05"]` | Not required. |
| `WS02-04C2-R8` | `required` | `platform/retry_reconciliation` | `["API-M11", "API-M10", "JOB-M05", "GOV-006", "WS02-04C2", "WS02-04B1", "WS02-04C3A", "WS02-04C3B", "WS05"]` | Not required. |
| `WS02-04C2-R9` | `required` | `platform/retry_reconciliation` | `["API-M10", "JOB-M05", "PAY-002", "GOV-006", "WS02-04C2", "WS03-02", "WS05"]` | Not required. |
| `WS02-04C2-R10` | `required` | `platform/retry_reconciliation` | `["API-M10", "API-M12", "API-M15", "EN-02", "OPS-010", "WS02-04C2"]` | Not required. |
| `WS02-04C2-R11` | `deferred` | `governance` | `["API-M10", "API-M11", "API-M19", "DB-002", "GOV-006", "FDN-04", "JOB-M05", "PAY-002", "WS02-04C2", "WS02-04C3A", "WS02-04C3B", "WS04", "WS05", "WS06", "WS09", "WS10"]` | `Rate controls, abuse controls, provider dashboard delivery/retry settings, live provider retry behavior, permanent runtime topology, durable worker implementation, queue tables, leases, scheduler cadence, worker retry counts, worker concurrency, poison policy, global request/response deadlines, database connection budgets, load evidence, telemetry dashboards, alerts, and provider concurrency limits remain later or external responsibilities and cannot be closed by local C2 source tests.` |

`WS02-04C2-R11` must have zero pytest mappings.

## 4. Technical Design / Contracts

### 4.1 Retry Classes

**What this is**

C2 uses retry-safety classes to describe what Pickup Lane may do after a
provider operation fails, times out, or may have completed with an unknown
outcome.

**Contract / required behavior**

| Class | Meaning |
|---|---|
| `SAFE_READ` | A provider read/query did not ask the provider to mutate state. Timeout may use retry-later semantics. |
| `IDEMPOTENT_MUTATION` | The mutation uses an idempotency identity that is stable for the real replay path and another deliberate attempt can reuse that same identity. |
| `RECONCILE_BEFORE_RETRY` | The provider mutation may have happened. Pickup Lane must re-read provider/local state or use a state-gated recovery path before another mutation. |
| `MANUAL_REPAIR` | A current explicit admin/support workflow owns the retry or reconciliation. It is not an automatic background retry. |
| `PROVIDER_REDELIVERY` | Provider transport owns delivery retry. Pickup Lane owns idempotent ingestion and duplicate handling. |
| `NO_AUTOMATIC_RETRY` | Current source lacks durable identity or evidence needed for app-owned retry. |

The registry may add fields needed to keep classifications truthful. In Gate B
it must stop representing all `stripe.payment_intent.create` calls as one
stable replay-safe class because current workflow identity differs by caller.

**Why**

The same provider API operation can have different application safety depending
on caller state. The registry must describe the workflow identity, not only the
Stripe method name.

### 4.2 Dependency Retry Ownership

**What this is**

Dependency retry ownership records where retry behavior comes from when Pickup
Lane has not configured retry counts or retry mode.

**Contract / required behavior**

The registry must match current repository dependency authority:

| Dependency | Current pinned version | C2 policy |
|---|---:|---|
| Stripe Python SDK | 15.1.0 | Dependency-owned behavior when Pickup Lane does not configure retry attempts. Pickup Lane configures operation timeouts through C1 clients. |
| Firebase Admin SDK | 7.4.0 | Dependency-owned behavior. Pickup Lane configures `httpTimeout` only. |
| Botocore | 1.35.99 | Dependency-owned behavior. Pickup Lane configures R2 metadata connect/read timeouts only, not retry mode or attempts. |
| SQLAlchemy | 2.0.49 | Application rollback/session policy only. No transparent transaction retry count or backoff is approved. |

Hard-coded dependency versions are allowed in the production policy registry
only as visible reassessment triggers. Gate B tests must compare them to
`backend/requirements.txt` so dependency upgrades force C2 review.

The registry must not claim exact SDK retry counts, backoff, jitter, or
provider schedules unless Pickup Lane source configures them or a later
accepted authority records them.

**Why**

`GOV-006` requires evidence-backed limits. Dependency defaults can change under
library upgrades, so C2 records ownership and reassessment triggers instead of
inventing numeric retry policy.

### 4.3 Current Provider And Outbound Inventory

**What this is**

C2 must know every current production application/runtime provider or outbound
operation that can matter to retry or reconciliation.

**Contract / required behavior**

Current production application/runtime source contains these C2-relevant
provider/outbound families:

| Family | Current operations | C2 classification responsibility |
|---|---|---|
| Stripe reads | SetupIntent retrieve, PaymentMethod retrieve, PaymentIntent retrieve, Refund retrieve | `SAFE_READ`; C1 read-timeout semantics are inherited. |
| Stripe mutations | Customer create, SetupIntent create, PaymentIntent create, PaymentIntent confirm, Refund create, PaymentMethod detach, customer default payment method set, customer default payment method clear | Workflow-specific mutation classification, idempotency identity, and unknown-outcome recovery. |
| Firebase Admin reads | token verification, user lookup, email lookup | `SAFE_READ`; C1 read-timeout semantics are inherited. |
| Firebase Admin mutation | user deletion | `RECONCILE_BEFORE_RETRY`; timeout outcome remains unknown and account-deletion recovery owns follow-up. |
| R2 metadata | `head_object` metadata check | `SAFE_READ`; C1 metadata timeout semantics are inherited. |
| R2 presigned URLs | upload/read presigned URL generation | local signing/configuration work, not provider network retry evidence. |
| Direct browser R2 upload | browser-to-provider upload via presigned URL | outside C2 local backend provider retry proof; later storage/runtime owner. |
| Stripe webhook | signed event construction plus application event processing | `PROVIDER_REDELIVERY` for transport, repository-owned idempotent processing only. |

Current source search found no production `requests`, `httpx`, `aiohttp`,
`urllib.request`, raw socket, SMTP, or other third-party provider network SDK
path outside the listed Stripe, Firebase Admin, and R2 families.

Manual bootstrap, seed, and maintenance scripts that call provider SDKs are
operational tooling. They are not runtime API retry/reconciliation policy, are
not required as runtime registry entries, and must be given explicit ownership
if they are later promoted into scheduled or production automation.

**Why**

Provider retry policy is only useful if it is complete. A hidden provider call
would undermine C1 timeout and C2 replay safety.

### 4.4 Stripe Reads

**What this is**

Stripe read/query operations ask the provider for current state without
mutating provider state.

**Contract / required behavior**

These operations remain safe reads:

- `stripe.setup_intent.retrieve`
- `stripe.payment_method.retrieve`
- `stripe.payment_intent.retrieve`
- `stripe.refund.retrieve`

They do not use provider idempotency keys. Timeout inherits C1
dependency-read semantics. C2 does not add an application retry loop around
them. A later caller may deliberately re-read state because no provider
mutation was requested by the read itself.

**Why**

Reads can usually be repeated later. They must still be bounded by C1 timeouts,
but they do not carry the duplicate-mutation risk of writes.

### 4.5 Stripe Mutations And Idempotency Identity

**What this is**

Stripe mutation safety depends on the application identity behind the provider
request, not just whether a Stripe idempotency option is present.

**Contract / required behavior**

| Operation/context | Provider idempotency key | Current identity source | C2 class |
|---|---|---|---|
| Customer create for saved-card setup | yes | deterministic user-scoped key, `user:{user.id}:stripe_customer` | `IDEMPOTENT_MUTATION` |
| SetupIntent create | yes | request-local generated key | `NO_AUTOMATIC_RETRY` |
| Checkout initial PaymentIntent create before provider result | yes | payment-row key created before provider call; if create itself times out before a provider ID is returned, no durable provider checkpoint exists | `NO_AUTOMATIC_RETRY` for app-owned automatic retry |
| Checkout initial PaymentIntent confirm after successful create | no | Gate B must persist a durable local checkout checkpoint containing Booking, pending participants/capacity hold, Payment row, Payment idempotency identity, returned provider PaymentIntent ID, and any reserved game-credit state, then reacquire checkout/game serialization and re-read provider state before confirmation | `RECONCILE_BEFORE_RETRY` |
| Checkout existing pending PaymentIntent confirm | no | persisted provider PaymentIntent ID from existing local payment row after checkout/game serialization and provider re-read | `RECONCILE_BEFORE_RETRY` |
| Community publish fee initial PaymentIntent create | yes | attempt/payment IDs created before provider call but rolled back on timeout before commit | `NO_AUTOMATIC_RETRY` for app-owned automatic retry; unknown outcome requires later reconciliation/repair if needed |
| Community publish fee confirm | no | persisted provider PaymentIntent ID after create commit | `RECONCILE_BEFORE_RETRY` |
| Waitlist auto-promotion PaymentIntent create | yes | persisted payment-row key inside locked promotion workflow once surrounding transaction commits | `RECONCILE_BEFORE_RETRY` with processing/local recovery; no blind loop |
| Waitlist auto-promotion PaymentIntent confirm | no | provider PaymentIntent ID from the promotion payment | `RECONCILE_BEFORE_RETRY` |
| Refund create - admin retry | yes | admin-provided idempotency key scoped by refund/admin action | `MANUAL_REPAIR` |
| Refund create - official game cancellation | yes | deterministic game/payment refund key | `RECONCILE_BEFORE_RETRY` plus refund/money-issue records |
| Refund create - official player removal | yes | deterministic game/booking/payment refund key | `RECONCILE_BEFORE_RETRY` plus refund/money-issue records |
| Refund create - late checkout payment | yes | deterministic booking/payment refund key | `RECONCILE_BEFORE_RETRY` plus refund record |
| Refund create - community publish financial outcome | yes | admin action key plus refund suffix | `MANUAL_REPAIR` / `RECONCILE_BEFORE_RETRY` depending state gate |
| PaymentMethod detach - user-visible saved card | no | provider payment method ID plus persisted local saved-card row | `RECONCILE_BEFORE_RETRY` |
| PaymentMethod detach - account deletion cleanup | no | provider payment method ID plus pending account-deletion cleanup/support state | `RECONCILE_BEFORE_RETRY` |
| PaymentMethod detach - unpersisted best-effort cleanup | no | provider PaymentMethod intentionally not persisted after duplicate-card or saved-card-cap rejection | `NO_AUTOMATIC_RETRY` with best-effort cleanup semantics |
| Customer default payment method set/clear | no | customer/default-card state only | `RECONCILE_BEFORE_RETRY` |

Gate B must correct `backend/services/provider_retry_policy.py` so its entries
are workflow-aware enough to make these distinctions. The registry must not say
that `stripe.payment_intent.create` is generally stable for checkout replay.

Gate B must also correct `backend/services/checkout_service.py` so a new
checkout persists a durable local checkpoint after Stripe PaymentIntent create
succeeds and before PaymentIntent confirmation starts. The checkpoint must
atomically retain:

- pending Booking;
- pending participants and capacity hold;
- Payment row;
- Payment idempotency identity;
- returned provider PaymentIntent ID;
- all `GameCreditUsage` rows reserved for that booking/payment when credits are
  applied;
- the corresponding decremented `GameCredit.available_cents` state.

The correction must not add a game-credit model or field, change credit
calculation, change credit amounts, change reservation idempotency scope, or
edit `backend/services/game_credit_service.py`. The existing
reservation/redeem/release model remains authoritative.

After the checkpoint commit, the initial request must not call
`confirm_payment_intent(...)` directly from the pre-commit create result. The
initial request and any later active-hold re-entry must share the same
serialized persisted-checkout resume shape:

1. acquire the existing game checkout serialization lock;
2. resolve the persisted pending checkout;
3. load the persisted Payment/provider PaymentIntent identity;
4. retrieve provider PaymentIntent state;
5. decide whether another confirmation is appropriate;
6. if appropriate, perform at most one confirmation from that locked checkout
   decision;
7. persist the resulting local state before releasing the lock.

No post-checkpoint PaymentIntent confirmation may be initiated from an
unlocked or stale checkout view. The provider must be re-read after the
checkpoint commit and after serialization is reacquired. Any confirmation call
must occur while the checkout/game serialization lock remains owned by the
current transaction so another request for the same game cannot make a
competing confirmation decision from pre-lock state.

If payment later succeeds through the existing authoritative success path, the
existing credit redemption behavior remains authoritative. If the checkout
expires through the existing stale-checkout path, the existing credit-release
behavior remains authoritative.

If confirmation then raises the existing C1 mutation-unknown timeout, the
checkpoint, pending participants/capacity hold, Payment row, provider
PaymentIntent ID, and reserved game-credit state must survive without marking
payment or booking as definitely succeeded or failed. During the active
checkout hold, re-entry must use the existing reusable pending checkout path,
retrieve the persisted provider PaymentIntent first, and observe provider
state before deciding whether confirmation is still appropriate. It must not
create a new PaymentIntent or a second credit reservation merely because the
earlier confirmation timed out.

When the existing checkout hold expires, current checkout-expiration behavior
may expire the Booking locally, release capacity, release reserved credits
through the existing credit-release contract, and transition local stale
checkout state. C2 does not change the hold duration. Expiration must not erase
the persisted Payment row or provider PaymentIntent identity merely because the
local hold expired, and local expiration is not proof of the provider's final
outcome. Durable provider reconciliation after the request-local checkout hold,
including delayed or missing provider events, remains WS05-owned.

Community publish remains a contrast case: current source commits the created
PaymentIntent ID before confirmation. Paid waitlist promotion also differs:
unknown mutation timeout is preserved as processing state instead of blindly
replaying a new provider identity. SetupIntent create and community publish
initial PaymentIntent-create timeout still use request-local or rolled-back
identity and must not be described as stable client replay.

**Why**

A provider idempotency key generated from a rolled-back row cannot be reused by
a later request unless the local identity survived. C2 must prevent that from
being called safe application retry.

### 4.6 Unknown Outcomes, Retry, Reconciliation, And Manual Repair

**What this is**

Unknown outcome means Pickup Lane does not know whether a provider mutation
completed. Retry means sending another provider mutation. Reconciliation means
checking provider and local state before deciding what to do. Manual repair is
a state-gated admin/support workflow that performs recovery intentionally.

**Contract / required behavior**

- C1 mutation timeouts remain `DependencyMutationTimeoutUnknownError` /
  `API.DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN`; C2 must not reinterpret them as
  definite failure.
- If checkout `create_payment_intent(...)` itself times out before returning a
  provider PaymentIntent ID, no post-create checkpoint exists, confirmation
  must not run, and the current local transaction rollback behavior remains.
- Automatic application retry is prohibited unless the operation has a durable
  replay identity and a current source-owned owner.
- Payment confirmation, saved-card detach/default changes, Firebase deletion,
  and most refund cases must be reconciled or manually repaired before another
  mutation.
- Checkout confirmation-unknown must preserve the durable checkpoint during the
  active checkout hold. The initial post-checkpoint request and any later
  active-hold re-entry must reacquire checkout/game serialization, re-resolve
  persisted local state, retrieve provider state, and decide from that locked
  view before any later confirmation attempt.
- A competing active-hold checkout request must not reach PaymentIntent create
  or confirmation while another request owns the locked post-checkpoint
  confirmation decision for that checkout.
- Checkout expiration after the existing hold may release capacity and reserved
  credits locally, but it must not be described as provider reconciliation or
  provider cancellation.
- Admin refund retry and reconciliation must remain explicit state-gated
  workflows with admin idempotency/action records, refund events, money issues,
  and provider re-read where applicable.
- Admin credit retry is local ledger repair. It must not be described as a
  provider retry.
- Account deletion cleanup must preserve pending deletion/support follow-up for
  Firebase deletion and saved-card detach uncertainty.
- Saved-card sync may re-read provider state. User-visible detach/default
  mutations do not receive a blind retry loop.
- `detach_unpersisted_payment_method(...)` is distinct best-effort cleanup of a
  provider PaymentMethod that Pickup Lane intentionally did not persist after a
  local duplicate-card or saved-card-cap rejection. Cleanup failure is not a
  user-visible successful detach, not reconciliation proof, and not a retry
  loop.

**Why**

Unknown outcomes are where duplicate side effects happen. The safe response is
to make the recovery path explicit, state-gated, and auditable.

### 4.7 Stripe Webhook Redelivery And Idempotency

**What this is**

Stripe webhook retry is provider transport redelivery. Pickup Lane owns local
idempotency once a signed event reaches the application.

**Contract / required behavior**

Repository-owned C2 proof may establish:

- signed webhook route accepts a provider event only after signature/body
  construction succeeds;
- event payload must contain provider event `id` and `type`;
- existing `PaymentEvent.provider_event_id` returns duplicate success without
  reprocessing;
- database-level duplicate-insert handling is guarded by provider-event
  uniqueness;
- processing is idempotent by event identity and local payment/refund state;
- there is no internal scheduled webhook retry loop.

C2 does not claim deterministic concurrent webhook race proof. Later
database/payment/test owners may add genuine concurrency evidence if they need
to prove concurrent duplicate delivery behavior beyond the database uniqueness
and duplicate-insert guard.

Repository-owned C2 proof must not claim:

- Stripe dashboard endpoint configuration;
- Stripe retry/redelivery schedule;
- production endpoint reachability;
- live provider behavior;
- durable webhook replay worker behavior.

**Why**

Provider redelivery is different from app retry. C2 can prove that duplicate
events are safe locally, but it cannot prove the provider dashboard or live
transport behavior from local tests.

### 4.8 Fanout And Backpressure

**What this is**

Fanout is work created from one request over many recipients, payments, cards,
waitlist entries, or related rows. Backpressure is the evidence-backed control
that keeps that work from becoming unbounded or parallel without review.

**Contract / required behavior**

Current source-owned fanout inventory:

| Workflow | Current execution model | Current bound | Provider calls per item | C2 policy |
|---|---|---|---|---|
| `platform_notice.selected_user_publish` | synchronous sequential database recipient creation | selected-user product maximum of 500 recipients | none | no new concurrency; future external delivery belongs to WS05 |
| `game_chat.notification_rows` | synchronous sequential database notification updates | current game chat members excluding sender | none | no new concurrency; future external delivery belongs to WS05 |
| `need_a_sub_chat.notification_rows` | synchronous sequential database notification updates | current Need-a-Sub chat members excluding sender | none | no new concurrency; future external delivery belongs to WS05 |
| `game_updated.notification_rows` | synchronous sequential database notification updates | current game update recipients | none | no new concurrency; future external delivery belongs to WS05 |
| `waitlist.promotion` | synchronous sequential locked workflow | available roster spots and ordered waitlist candidates | possible Stripe create/confirm per paid promoted entry | no parallel provider fanout; durable payment reconciliation belongs to WS05 |
| `account_deletion.cleanup` | synchronous sequential cleanup | current user-owned records and saved cards | possible Firebase delete and Stripe detach | no parallel provider fanout; durable cleanup recovery belongs to WS05 |
| `official_game_cancellation.refunds` | synchronous sequential refund loop | current refundable successful payments for the canceled game | possible Stripe refund per refundable payment | no parallel provider fanout; refund/money issue state gates recovery |
| `official_game_player_removal.refunds` | synchronous sequential refund loop | current succeeded payments for the removed booking/player context | possible Stripe refund per refundable payment | no parallel provider fanout; refund/money issue state gates recovery |
| `community_publish_fee.financial_outcome_refund` | single explicit admin financial-outcome workflow | one publish-fee payment/refund context | one possible Stripe refund | manual/admin state gate |
| `late_checkout_payment.refund` | webhook/payment repair helper | one late payment context | one possible Stripe refund | deterministic refund key and refund record |

Gate B tests must prove current source does not use `asyncio.gather`,
`asyncio.create_task`, thread pools, process pools, FastAPI `BackgroundTasks`,
or similar hidden parallel work for these C2 fanouts.

Existing product limits are not C2-approved retry, provider, worker, or
concurrency values. The selected-user maximum is a product audience limit, not
a worker batch size.

**Why**

Sequential source structure is the current portable guarantee. Real durable
backpressure, queue limits, worker leases, and provider concurrency policy need
later evidence.

### 4.9 Durable Work Handoffs

**What this is**

C2 records where request-local or manual repair behavior is not the final
production-grade answer, while leaving worker design to WS05.

**Contract / required behavior**

| Handoff | Current safe interim behavior | Why durable work may be needed | Required durable properties |
|---|---|---|---|
| provider unknown-outcome reconciliation | reconcile before retry, manual repair, or local pending/processing/support state | request-local handling cannot guarantee later provider/local repair | claimable work identity, stable replay reference, idempotent handler, bounded retry policy, operator-visible exhausted state |
| checkout post-expiry provider reconciliation | active-hold re-entry reuses the durable pending checkout and provider PaymentIntent re-read; local expiration may release local capacity and credit holds while preserving provider identity | delayed or missing provider/webhook outcomes after the request-local checkout hold need durable follow-up | persisted provider identity, provider/local comparison, idempotent repair decision, credit/capacity compensation rules, operator-visible exhausted state |
| account deletion cleanup recovery | pending deletion and support flags | provider cleanup may outlive one request | checkpointed cleanup stage, safe re-entry, provider outcome reconciliation, support-visible failure state |
| future external notification delivery | in-app notification rows only | external delivery will need durable handoff | delivery job identity, idempotent recipient handling, retry and poison state, redacted telemetry |
| future platform notice external delivery | synchronous database recipient record creation | external bulk delivery cannot run unbounded | audience snapshot, claimable delivery work, bounded worker concurrency, partial-delivery state |
| durable financial reconciliation | admin refund retry/reconcile and money issues | manual repair may become insufficient at scale | financial workflow identity, provider/local comparison, idempotent repair action, auditable operator outcome |

C2 approves none of the following: worker retry attempts, worker concurrency,
lease duration, scheduler cadence, poison thresholds, queue schema, heartbeat
policy, or durable job topology.

**Why**

The pass can identify durable repair needs without pretending local source
tests have implemented a production worker system.

### 4.10 Numeric Authority

**What this is**

C2 has no approved numeric retry or worker policy.

**Contract / required behavior**

C2 approves no application-owned numeric:

- retry attempts;
- retry backoff;
- retry jitter;
- provider concurrency cap;
- worker retry count;
- worker concurrency;
- worker lease duration;
- scheduler cadence;
- poison threshold;
- generic batch size.

The limits register records that C2 approves classifications and ownership,
not those numbers. If a future source change adds a retry/backpressure number,
it must identify its actual owner and basis instead of treating C2 as blanket
authority.

**Why**

`GOV-006` and `FDN-04` require evidence-backed numeric limits. C2 does not have
runtime/load/provider evidence to approve them.

### 4.11 Runtime Telemetry And Static Policy Prose

**What this is**

C2 may describe retry outcomes or policy classes in two different places:
runtime telemetry/event labels and static human-readable registry prose.

**Contract / required behavior**

Current C2 source emits no retry-policy telemetry directly. Gate B must prove
that negative space rather than pretending telemetry exists.

If C2 later emits runtime telemetry or event labels, those emitted values must
use bounded EN-02-safe class labels such as:

- provider family;
- operation class;
- retry-safety class;
- ownership class;
- outcome class;
- reconciliation result class;
- durable-handoff class.

Static registry fields such as `current_behavior`, `current_recovery`,
`durable_follow_up`, and `reassessment_trigger` are documentary policy prose,
not emitted telemetry labels. They may contain concise non-sensitive policy
descriptions.

Runtime labels and static registry prose must not contain:

- provider IDs;
- payment IDs;
- refund IDs;
- user IDs;
- booking IDs;
- URLs;
- request bodies;
- provider response bodies;
- raw exception strings;
- credentials;
- secrets;
- URLs containing private data;
- sensitive request content.

C2 does not create telemetry dashboards, alerts, retention settings, or
production monitoring closure.

**Why**

Retry and reconciliation failures are often sensitive. EN-02 safety boundaries
remain prerequisites for any observability added later, while the static
registry still needs readable non-sensitive policy explanations.

## 5. Implementation Scope

### Gate A Artifact

Gate A updates only this canonical planning document.

### Frozen Gate B Editable Set

Gate B may edit exactly these files:

1. `backend/services/provider_retry_policy.py`
2. `backend/services/checkout_service.py`
3. `backend/tests/support/requirements/ws02_04c2.json`
4. `backend/tests/platform/retry_reconciliation/TESTING_RECORD.md`
5. `backend/tests/platform/retry_reconciliation/test_retry_policy_registry_contract.py`
6. `backend/tests/platform/retry_reconciliation/test_c2_provider_operation_inventory_contract.py`
7. `backend/tests/platform/retry_reconciliation/test_dependency_retry_ownership_contract.py`
8. `backend/tests/platform/retry_reconciliation/test_idempotency_replay_contract.py`
9. `backend/tests/platform/retry_reconciliation/test_unknown_outcome_no_blind_replay_contract.py`
10. `backend/tests/platform/retry_reconciliation/test_manual_repair_reconciliation_contract.py`
11. `backend/tests/platform/retry_reconciliation/test_webhook_redelivery_idempotency_contract.py`
12. `backend/tests/platform/retry_reconciliation/test_fanout_backpressure_contract.py`
13. `backend/tests/platform/retry_reconciliation/test_durable_handoff_and_metadata_contract.py`

The complete expected pass change set is this Gate A planning document plus
the 13 Gate B files above.

### Production Correction Set

Gate B must correct exactly these production files:

1. `backend/services/provider_retry_policy.py`
2. `backend/services/checkout_service.py`

No other production/runtime source correction is currently approved.

Required registry corrections:

- keep the module as a production policy/review artifact, not a runtime retry
  framework;
- add or change fields as needed so operation entries can identify workflow
  context, material callers, idempotency identity source, and whether the
  identity survives deliberate replay;
- split or otherwise correct `stripe.payment_intent.create` so checkout and
  community publish initial creation are not claimed as stable client replay;
- distinguish checkout create-timeout identity, checkout post-create active-hold
  durable checkpoint behavior, checkout credit-reservation state, and
  post-expiry WS05 reconciliation ownership;
- distinguish admin refund retry, cancellation refunds, player-removal refunds,
  late-payment refunds, community publish financial-outcome refunds, and
  waitlist auto-promotion behavior;
- distinguish user-visible saved-card detach, account-deletion saved-card
  cleanup, and unpersisted best-effort PaymentMethod cleanup;
- include current webhook, Firebase, R2, saved-card, account deletion, game
  update notification, and refund fanout surfaces;
- keep hard-coded dependency versions only as tested reassessment triggers;
- keep every retry/backoff/concurrency numeric field `None` unless later
  authority approves a value;
- keep static registry prose concise and non-sensitive while not treating it as
  emitted telemetry.

### Provider/Service Correction Set

Checkout must persist a durable local checkpoint after new PaymentIntent create
succeeds and before confirmation starts. The checkpoint must atomically
preserve the pending Booking, pending participants/capacity hold, Payment row,
Payment idempotency identity, returned provider PaymentIntent ID, all reserved
`GameCreditUsage` rows for that booking/payment when credits are applied, and
the corresponding decremented `GameCredit.available_cents` state.
Confirmation-unknown timeout must leave that checkpoint reusable during the
active checkout hold without recording definite success or definite failure.
After the checkpoint commit, the initial request must enter the same serialized
persisted-checkout resume path used by later active-hold re-entry. That path
must reacquire the existing game checkout serialization lock, reload the
persisted pending Booking/Payment state, retrieve the persisted provider
PaymentIntent, and only then decide whether confirmation is appropriate. Any
post-checkpoint confirmation must occur while the serialization lock remains
owned by the current transaction, and the resulting local state must be
committed or rolled back before another checkout request for the game can make
its own confirmation decision. Active re-entry must not create a second
PaymentIntent or second game-credit reservation.

When the existing checkout hold expires, the current expiration behavior may
expire the Booking locally, release capacity, release reserved credits through
the existing credit-release contract, and transition local stale-checkout
state. The persisted Payment row and provider PaymentIntent identity must not
be erased merely because the local checkout hold expired. Local expiration is
not provider outcome proof and not provider cancellation. Durable recovery
after the request-local checkout hold remains WS05-owned.

Provider wrapper correction: none.

Settings/config correction: none.

Database model/migration correction: none.

Frontend correction: none.

Governance-register correction: none.

If Gate B requires another production file, provider wrapper, setting,
database model, migration, frontend file, governance document, test module,
requirement, proof layer, or owner decision, the pass must stop and return to
Gate A.

### Governance/Document Correction Set

No governance document correction is frozen for Gate B. The current
limits-and-thresholds register already records that C2 approves retry and
reconciliation classifications without approving retry/backoff/worker numeric
values.

## 6. Testing And Evidence

### Trusted Evidence Scope

Gate B must create one EN-01 trusted platform scope:

`backend/tests/platform/retry_reconciliation/`

The testing record must be:

`backend/tests/platform/retry_reconciliation/TESTING_RECORD.md`

Historical/pre-EN-01 tests are provenance only and are not current trusted C2
evidence.

### Planned Test Modules

| Module | Required proof |
|---|---|
| `test_retry_policy_registry_contract.py` | Registry classes, schema, current entries, non-executing retry-framework boundary, no numeric retry/backoff/concurrency approvals, no stale generic PaymentIntent-create overclaim. |
| `test_c2_provider_operation_inventory_contract.py` | Current Stripe/Firebase/R2/webhook/other outbound inventory matches production source; every current operation is represented or explicitly out of scope. |
| `test_dependency_retry_ownership_contract.py` | Registry dependency versions match `backend/requirements.txt`; Pickup Lane source does not configure Stripe retry attempts, Botocore retry mode/attempts, generic retry decorators, backoff, jitter, or urllib3 retry policy. |
| `test_idempotency_replay_contract.py` | Provider idempotency key identity is traced by workflow; corrected checkout post-create durable checkpoint and active-hold re-entry behavior are proven with PostgreSQL, fake Stripe, and at least one non-zero game-credit application; stable user/refund identities are distinguished from request-local or rolled-back payment identities. |
| `test_unknown_outcome_no_blind_replay_contract.py` | C1 mutation-timeout unknown semantics are consumed correctly; corrected checkout confirmation-unknown preserves reusable pending state, capacity hold, and reserved game-credit state without definite success/failure; active-hold re-entry does not create a second PaymentIntent or credit reservation; one deterministic PostgreSQL concurrency proof covers checkout active-hold confirmation serialization; stale-checkout expiration releases local holds without claiming provider reconciliation. |
| `test_manual_repair_reconciliation_contract.py` | Admin refund retry/reconcile, admin credit retry, saved-card support/re-read paths, Firebase account-deletion follow-up, and refund/money-issue recovery are state-gated and do not claim automatic background retry. |
| `test_webhook_redelivery_idempotency_contract.py` | Signed Stripe webhook local processing uses provider event identity, existing-event duplicate handling, real provider-event uniqueness, duplicate-insert IntegrityError handling, and no internal scheduled retry loop while leaving provider dashboard/redelivery and deterministic concurrent-race facts external. |
| `test_fanout_backpressure_contract.py` | Current fanout inventory is synchronous/sequential; no hidden `gather`, `create_task`, thread/process pools, `BackgroundTasks`, or unapproved parallel provider fanout exists. |
| `test_durable_handoff_and_metadata_contract.py` | WS05 handoffs are explicit, contain required durable properties, contain no worker numeric values, prove C2 emits no retry-policy telemetry directly, and distinguish bounded runtime labels from concise non-sensitive static registry prose. |

### Proof-Layer Decisions

| Requirement | Static/unit proof | Service/workflow proof | PostgreSQL | Provider/network | Browser | Migration | Genuine concurrency | Controlled time |
|---|---|---|---|---|---|---|---|---|
| `WS02-04C2-R1` | yes | service inspection for non-executing registry boundary | no | prohibited | no | no | no | no |
| `WS02-04C2-R2` | yes | no | no | prohibited | no | no | no | no |
| `WS02-04C2-R3` | yes | limited source/service inspection | no | prohibited | no | no | no | no |
| `WS02-04C2-R4` | yes | representative C1 integration references | no | prohibited | no | no | no | no |
| `WS02-04C2-R5` | yes | yes for representative payment/refund identity flows | required | prohibited | no | no | required narrowly for checkout active-hold confirmation serialization | no |
| `WS02-04C2-R6` | yes | yes for state-gated manual/reconciliation paths | required | prohibited | no | no | required narrowly for checkout active-hold confirmation serialization | no |
| `WS02-04C2-R7` | yes | yes | required | prohibited | no | no | no | no |
| `WS02-04C2-R8` | yes | limited service/source inspection | no | prohibited | no | no | no | no |
| `WS02-04C2-R9` | yes | no | no | prohibited | no | no | no | no |
| `WS02-04C2-R10` | yes | no | no | prohibited | no | no | no | no |
| `WS02-04C2-R11` | declaration/governance only | no | no | prohibited | no | no | no | no |

Gate B must use fakes/mocks at the application-owned provider boundary. It must
not call live Stripe, Firebase, R2, SMTP, or other external network providers.
Browser/Playwright, migration/schema-history proof, and controlled-time proof
are not required for C2. Genuine concurrency/race execution is required only
for the narrow R5/R6 checkout active-hold confirmation serialization proof; it
remains not required for webhook duplicate delivery, fanout/backpressure,
Firebase, R2, and other C2 requirements.

R5 PostgreSQL proof must use the dedicated local PostgreSQL test database with
fake Stripe boundaries to prove:

- at least one corrected initial checkout uses non-zero game-credit
  application;
- PaymentIntent create succeeds exactly once;
- before confirmation, the checkpoint is committed;
- the checkpoint contains the persisted Booking, pending participants, Payment
  row, provider PaymentIntent ID, and Payment idempotency identity;
- the associated `GameCreditUsage` reservation is persisted;
- the corresponding `GameCredit.available_cents` balance reflects that
  reservation;
- confirmation-unknown leaves that checkpoint durable and reusable during the
  active checkout hold;
- active-hold checkout re-entry finds the persisted checkout and re-observes
  the provider PaymentIntent instead of generating a new PaymentIntent
  identity;
- active-hold checkout re-entry does not call PaymentIntent create again;
- active-hold checkout re-entry does not create a second credit reservation;
- provider state is retrieved before another confirmation decision;
- the initial post-checkpoint request and a competing active-hold request use
  the same serialized persisted-checkout resume shape;
- while one request owns the checkout/game serialization lock at the
  confirmation decision seam, a competing active-hold request cannot reach
  PaymentIntent create or confirmation;
- after the first locked confirmation decision releases, the competing request
  must re-resolve persisted state and retrieve provider state before any later
  confirmation decision;
- total PaymentIntent create count remains one and no duplicate game-credit
  reservation is created;
- community-publish initial PaymentIntent-create timeout continues to roll back
  its uncommitted request-local attempt/payment identity and is not described
  as stable client replay;
- stable user-scoped/customer and durable refund identities remain
  distinguishable from request-local or rolled-back identities.

R6 PostgreSQL proof must use the dedicated local PostgreSQL test database with
provider fakes to prove:

- corrected checkout confirmation-unknown leaves reusable pending state and
  does not create definite local success or definite local failure;
- corrected checkout confirmation-unknown preserves the active capacity hold;
- corrected checkout confirmation-unknown preserves the game-credit reservation
  as reserved;
- confirmation-unknown does not permit a second confirmation inside the same
  request, and a later request must reacquire checkout/game serialization and
  retrieve provider state before deciding whether another confirmation is
  appropriate;
- the deterministic concurrency proof must use two independent database
  sessions/application requests, fake Stripe, and barriers/events rather than
  sleeps to prove no duplicate confirmation decision proceeds from the same
  pre-reconciliation checkout state;
- deterministic stale-checkout expiration uses an explicitly supplied later
  `now` or already-expired fixture state, not sleeping or clock racing;
- stale-checkout expiration releases reserved game credits through the existing
  release contract;
- stale-checkout expiration releases the local capacity hold;
- stale-checkout expiration does not erase the persisted Payment row or
  provider PaymentIntent identity;
- stale-checkout expiration is not claimed as provider reconciliation or
  provider cancellation;
- a representative admin refund retry/reconciliation path enforces persisted
  state gate, idempotency, and reconciliation boundaries;
- C1 mutation-unknown semantics are not converted into blind mutation replay.

R7 PostgreSQL proof must prove:

- real provider-event-ID uniqueness exists;
- existing-event duplicate handling is idempotent;
- the database duplicate-insert conflict path is guarded by the actual
  provider-event unique constraint and IntegrityError handling.

R7 does not prove a deterministic concurrent webhook race.

### Evidence Quality Checks

Gate B evidence must apply the testing-record evidence-quality rules where
relevant:

- successful mutations prove meaningful persisted effects, not only responses;
- rejected mutation paths prove prohibited side effects did not occur where
  applicable;
- idempotency tests prove persisted and external effects are not duplicated
  where the pass claims idempotency;
- PostgreSQL-backed duplicate event or state-gate behavior uses the local test
  database when static proof is insufficient;
- provider SDK behavior is faked at the wrapper/application boundary, not by
  mocking away the rule being tested.

### Required Validation Commands

Gate B must run:

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/retry_reconciliation
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/operation_timeouts
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/workflows/provider_payment_input_ownership backend/tests/workflows/source_owned_boundaries backend/tests/platform/api_errors backend/tests/platform/observability
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/checker backend/tests/workflows backend/tests/platform
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/checker
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/retry_reconciliation
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/platform/operation_timeouts
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/provider_payment_input_ownership
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

```bash
backend/.venv/bin/python -m py_compile backend/services/provider_retry_policy.py backend/services/checkout_service.py backend/tests/platform/retry_reconciliation/test_retry_policy_registry_contract.py backend/tests/platform/retry_reconciliation/test_c2_provider_operation_inventory_contract.py backend/tests/platform/retry_reconciliation/test_dependency_retry_ownership_contract.py backend/tests/platform/retry_reconciliation/test_idempotency_replay_contract.py backend/tests/platform/retry_reconciliation/test_unknown_outcome_no_blind_replay_contract.py backend/tests/platform/retry_reconciliation/test_manual_repair_reconciliation_contract.py backend/tests/platform/retry_reconciliation/test_webhook_redelivery_idempotency_contract.py backend/tests/platform/retry_reconciliation/test_fanout_backpressure_contract.py backend/tests/platform/retry_reconciliation/test_durable_handoff_and_metadata_contract.py
```

```bash
git diff --check
```

### Traceability Expectations

`WS02-04C2-R1` through `WS02-04C2-R10` must each have at least one generated
pytest mapping. `WS02-04C2-R11` must remain deferred with zero pytest mappings.

The checker-generated traceability report, not the planning document, is the
authority for exact pytest node IDs.

## 7. Integration And Cross-Pass Ownership

C2 depends on C1 for timeout wrappers and public unknown-outcome semantics. C2
must not duplicate C1 timeout value proof or change C1 timeout behavior.

C2 consumes EN-02 safe telemetry/error primitives and must not weaken them.

C2 consumes B2A2B2 provider/payment input ownership. B2A2B2 prevents callers
from fabricating payment/provider evidence. C2 decides whether current
provider operations are safe to retry or must be reconciled.

C2 consumes WS03-02 account-deletion ownership. Firebase deletion timeout and
saved-card cleanup uncertainty remain account-deletion support/recovery paths
until WS05 durable cleanup exists.

C3A owns authenticated chat rate limits. C3B owns later provider-cost/action
rate and abuse controls. C2 does not approve rate limits or abuse thresholds.

WS05 owns durable jobs, durable provider reconciliation, queue/worker topology,
worker retry numbers, leases, heartbeats, scheduler cadence, poison handling,
and permanent replay/recovery infrastructure.

## 8. Explicit Non-Goals

C2 does not close:

- global request or response deadlines;
- C1 timeout values or timeout implementation;
- C3A/C3B rate/abuse values;
- application retry counts, backoff, or jitter;
- provider dashboard retry settings;
- live provider behavior or sandbox behavior;
- provider concurrency limits;
- durable worker implementation;
- queue tables, leases, heartbeats, scheduler, poison policy, or worker
  topology;
- database connection budget, pool sizing, or deployment instance math;
- external notification delivery;
- R2 direct browser upload/provider-object reconciliation;
- production telemetry dashboards, alerts, retention, or on-call process;
- permanent runtime/hosting topology;
- frontend behavior.

## 9. Controls And Remaining Evidence

| Control / owner | C2 status |
|---|---|
| `API-M10` | Partially closed for source-owned retry/reconciliation classification and no-blind-replay policy. Remains open for runtime, global deadline, provider, durable-worker, database-capacity, and telemetry evidence. |
| `API-M11` | Source-owned fanout/backpressure inventory provided. Rate/abuse controls remain with C3A/C3B and later runtime owners. |
| `JOB-M05` | Source-owned retry/permanent/reconcile classification and WS05 handoffs provided. Durable job implementation remains open. |
| `PAY-002` | Payment/refund idempotency and no-blind-replay policy clarified for current provider workflows. Full durable payment reconciliation remains later. |
| `GOV-006` / `FDN-04` | No numeric retry/backpressure values are approved without evidence. Dependency versions and registry entries become tested review triggers. |
| `WS05` | Receives durable provider reconciliation, durable cleanup, durable external delivery, durable financial reconciliation, and worker topology. |

## 10. Completion Criteria

Gate B is complete only when:

- `backend/services/provider_retry_policy.py` truthfully represents current
  source-owned retry/reconciliation/fanout policy;
- `backend/services/checkout_service.py` persists the durable local checkout
  checkpoint after new PaymentIntent create succeeds and before confirmation
  starts;
- the checkpoint includes any reserved game-credit `GameCreditUsage` rows and
  corresponding decremented `GameCredit.available_cents` state when credits are
  applied;
- the initial post-checkpoint confirmation path reacquires checkout/game
  serialization, reloads persisted checkout state, retrieves provider
  PaymentIntent state, and makes any confirmation decision from that locked
  view instead of from the pre-commit create result;
- the registry no longer overclaims blanket stable replay for
  `stripe.payment_intent.create`;
- checkout confirmation-unknown active-hold re-entry uses the existing reusable
  pending checkout path and provider PaymentIntent re-read instead of creating
  a new PaymentIntent identity or a second credit reservation;
- deterministic PostgreSQL evidence proves a competing active-hold request
  cannot reach PaymentIntent create or confirmation while another request owns
  the locked post-checkpoint confirmation decision, and that later continuation
  re-resolves persisted state before any confirmation decision;
- stale-checkout expiration preserves persisted Payment/provider PaymentIntent
  identity, releases local capacity/credit holds through existing contracts,
  and is not claimed as provider reconciliation;
- PaymentIntent create-timeout before a provider PaymentIntent ID returns still
  creates no post-create checkpoint, does not run confirmation, and keeps the
  current local rollback behavior;
- dependency version reassessment triggers are tested against current pinned
  dependency authority;
- current provider/outbound inventory has trusted evidence;
- idempotency identity and unknown-outcome behavior have trusted evidence;
- manual repair/reconciliation and webhook idempotency have trusted evidence;
- fanout/backpressure inventory has trusted source evidence;
- durable WS05 handoffs and deferred external facts remain explicit;
- `backend/tests/support/requirements/ws02_04c2.json` exists with the exact
  declaration design above;
- `backend/tests/platform/retry_reconciliation/TESTING_RECORD.md` accurately
  records evidence, risks, boundaries, and non-closure;
- all required validation commands pass;
- generated traceability maps `R1` through `R10` and leaves `R11` at zero
  mappings;
- no live provider, browser, migration, untrusted legacy, or external runtime
  evidence is used as C2 authority;
- no file outside the complete expected pass set changes.
