# WS05-02 Intake - Payment And Booking State Machines With Webhook Authority

## 1. What Needs To Be Decided

This intake decides whether Pickup Lane's payment and booking state-machine
work should execute as one engineering result or be divided before detailed
planning begins. The decision matters because checkout initiation, local
reservation state, Stripe payment state, and webhook-driven finalization all
change the same financial lifecycle and can become inconsistent if separated
at the wrong boundary.

The parent engineering work is `WS05-02 - Payment and booking state machines
with webhook authority`. It covers trusted checkout amounts, coordinated
payment and booking states, capacity reservation and conflict outcomes,
PaymentIntent handling, signed webhook ingestion, and idempotent handling of
duplicate, delayed, or out-of-order provider events. It also covers the
repository-owned saved-payment-method lifecycle that supplies authorized
checkout payment methods.

## 2. What We Know

This section contains the current technical facts and accepted dependencies
that affect the execution shape. Each fact explains whether the parent can
proceed coherently now or requires a separate prerequisite or verification
environment.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Accepted durable-job foundation | `WS05-01A` is accepted and provides PostgreSQL-backed durable jobs, executable handler registration, claim and lease behavior, retries, recovery, repair visibility, and a portable worker command. `WS05-01B` remains deferred for final worker hosting and deployed runtime proof. | Payment and webhook work can use the source-owned job foundation without waiting for final worker infrastructure. Any claim about the selected production worker platform remains outside this parent. |
| Accepted database contracts | `WS04-02A`, `WS04-02B`, `WS04-02C`, and `WS04-03A` are accepted. They define transaction and provider-checkpoint boundaries, database invariants and lock ordering, SQL/value compatibility, and migration policy. | The payment lifecycle can change its schema and workflows against settled transaction, concurrency, and migration rules instead of reopening those earlier passes. |
| Approved financial authority | The approved financial-state decision requires separate but coordinated payment, booking, refund, and compensation states. Stripe owns provider payment outcomes; Pickup Lane owns bookings, participants, capacity, and application compensation. Browser callbacks cannot grant paid entitlement. | The owner decision needed to design the state machines already exists, so there is no unresolved product or authority blocker. |
| Current state representation | The repository already stores bookings, payments, participant holds, payment events, credits, and status history, but the states are not one complete cross-object policy. Payment has no explicit unknown or refunded state, booking contains a disputed value without a complete dispute model, and capacity conflict is handled through failure detail and compensation paths rather than one canonical outcome. | The parent must reconcile the state model and all consumers together. Splitting the schema from checkout and webhook behavior would leave an unsafe period where code and persisted states disagree. |
| Current checkout behavior | Checkout derives amounts from locked server-owned game and credit state, creates durable pending booking and participant holds, persists a PaymentIntent identity checkpoint, and keeps Stripe-backed entitlement pending until server-side finalization. | Existing behavior provides a strong starting point, but the complete state transition and unknown-outcome rules still need one coordinated implementation and review. |
| Current webhook behavior | The signed webhook route records unique Stripe event IDs and handles several PaymentIntent and refund events. Processing is currently synchronous before acknowledgment, and stale or out-of-order protection is event-specific rather than a complete transition policy. | Durable acknowledgment, ordering, idempotency, provider-state checks, and local transitions must be designed as one lifecycle with checkout rather than as an independent webhook-only result. |
| Accepted provider-input and retry boundaries | Earlier accepted work treats provider identifiers as opaque, restricts checkout return URLs, retires generic financial mutation routes, distinguishes reads from unknown-outcome provider mutations, and prohibits blind replay after uncertain Stripe operations. | `WS05-02` must preserve these contracts while implementing the durable state transitions that consume them. It must not reintroduce client authority or unsafe provider retries. |
| Authorization prerequisite | `WS03-04` is complete. Its Stripe webhook lifecycle gap is explicitly assigned to `WS05`, while accepted user, checkout, booking, payment, refund, and admin authorization rules remain prerequisites. | The parent can implement webhook and financial lifecycle semantics without reopening the accepted authorization matrix, while preserving its access boundaries. |
| Current provider boundary | Stripe is the approved product payment provider, so repository-owned Stripe interfaces and deterministic test doubles can be implemented now. Stripe dashboard configuration, test/live account separation evidence, delivery observations, sandbox exercises, and deployed-provider behavior require later provider/runtime verification. | The missing external evidence does not block the source-owned state machines. It is already assigned to `WS05-04` and later provider/operations owners rather than requiring a new child under this parent. |
| Later financial workflows | `WS05-03` owns refunds, credits, notices, moderation delivery, dispute handling, and scheduled or operator-driven reconciliation. | `WS05-02` must define truthful compensation states and durable handoff points, but must not absorb the later workflows that execute and reconcile those outcomes. |
| Later failure and runtime proof | `WS05-04` owns focused replay, race, crash, timeout, Stripe sandbox, and deployed-worker verification after the WS05 domain implementations exist. `WS09` and `WS10` own deployed observability, alerts, provider controls, and operational evidence. | Local PostgreSQL, API, service, and deterministic provider-double proof belongs with `WS05-02`; final provider and deployed-runtime proof remains with the existing later passes. |

## 3. Execution Decision

This section states the chosen execution shape and why it is safe. `WS05-02`
should execute as one pass.

Outcome: execute the parent as one executable pass.

The payment, booking, reservation, capacity-conflict, and compensation states
form one financial lifecycle. Checkout creates the durable operation and
reservation state; Stripe reports provider outcomes; signed webhooks and
server-side reconciliation apply those outcomes to Pickup Lane's booking and
capacity state. None of those pieces is independently complete if the other
pieces still use the old transition rules.

The cohesion assessment supports keeping the parent whole:

| Engineering question | Verdict | Effect on execution shape |
|---|---|---|
| One primary outcome | Yes - one canonical payment and booking lifecycle whose final entitlement is controlled by server and webhook authority. | No split needed. |
| One requirement family | Yes - trusted amount, durable operation identity, coordinated states, provider authority, and event ordering all protect the same financial transition system. | No split needed. |
| One prerequisite state | Yes - the financial-state decision, durable-job foundation, authorization matrix, and database contracts are accepted. | No prerequisite-driven split. |
| One safe merge or forward-fix unit | Yes - schema, checkout producers, webhook consumers, and caller contracts must remain compatible in one merge. | Splitting would create a less safe intermediate state. |
| One evidence model | Yes - current-source proof uses PostgreSQL-backed service/API tests, deterministic event and concurrency scenarios, compatibility checks, and safe static inspection. | Provider sandbox and deployed-runtime evidence remains later-owned rather than creating a second current child. |
| One semantic review model | Yes - the review question is whether every event and request produces a truthful, idempotent transition across payment, booking, reservation, and compensation state. | One review boundary is appropriate. |
| Safe and useful result | Yes - the completed pass leaves one repository-owned financial lifecycle that later refund, reconciliation, and provider-verification work can consume. | The whole parent is independently useful when complete. |

No mandatory deferred child is created for `WS05-02`. Final worker hosting is
already preserved by `WS05-01B`, and Stripe sandbox, provider-dashboard, and
deployed-worker proof is already preserved by `WS05-04`, `WS09`, and `WS10`.
Those later obligations remain open and are not evidence for this pass.

## 4. Where The Parent Work Goes

This section accounts for the complete parent scope and its boundaries. The
table keeps every major responsibility with one owner so the single-pass
decision neither absorbs later work nor loses a payment obligation.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Canonical coordinated payment, booking, reservation, capacity-conflict, and compensation states | `WS05-02` | Actual refund, credit-restoration, dispute, notice, and reconciliation workflows remain with `WS05-03`; this pass defines the states and handoffs they consume. |
| Trusted amount and currency calculation, authenticated checkout ownership, and durable local financial-operation identity | `WS05-02` | Privileged refund, credit, and admin-money operations remain with their accepted authorization rules and `WS05-03` lifecycle work. |
| Stable Stripe mutation identity, local uniqueness, same-key conflict behavior, and unknown PaymentIntent outcomes | `WS05-02` | Full refund and reconciliation mutation handling remains with `WS05-03`; sandbox and deployed-provider proof remains with `WS05-04`. |
| PaymentIntent creation, confirmation, current-state retrieval, browser action-required/processing behavior, and status polling | `WS05-02` | The browser remains a consumer of server state and never becomes final payment or entitlement authority. |
| Checkout reservation expiry, participant holds, capacity revalidation, late provider success, and truthful capacity-conflict compensation handoff | `WS05-02` | Compensation execution involving refunds, credits, user notices, or operator reconciliation remains with `WS05-03`. |
| Signed raw-body webhook ingestion, durable event identity, prompt acknowledgment design, and idempotent payment/booking transitions | `WS05-02` | Stripe endpoint/dashboard configuration, live delivery behavior, and deployed timing evidence remain with `WS05-04` and provider-control owners. |
| Duplicate, delayed, stale, missing, and out-of-order event policy, including current-provider-state retrieval when local ordering is insufficient | `WS05-02` | Scheduled mismatch discovery, disputes, broad provider/local reconciliation, and operator repair execution remain with `WS05-03`. Deterministic sandbox and deployed-provider exercises remain with `WS05-04`. |
| Authorized client-secret delivery and protection from URLs, logs, cross-user responses, and unsafe application artifacts | `WS05-02` | Final deployed log, analytics, bundle, telemetry, and provider-account evidence remains with `WS05-04`, `WS09`, and `WS10`. |
| Repository-owned saved-payment-method lifecycle, including necessary metadata, Stripe Customer and PaymentMethod ownership, consent, attach/detach behavior, stale metadata refresh, and cross-user isolation | `WS05-02` | Accepted provider-input rules remain prerequisites. Stripe dashboard, test/live account, and deployed-provider evidence remains with `WS05-04` and provider-control owners. |
| Compatibility for shared payment consumers such as community publish fees, paid waitlist promotion, credits, and existing financial records | `WS05-02` | Only compatibility required by the canonical payment state model belongs here; product-specific publish, waitlist, credit, and refund workflow expansion remains with its owning pass. |
| Refunds, credits, notices, moderation delivery, disputes, scheduled reconciliation, and operator-driven financial repair | `WS05-03` | Consumes the accepted `WS05-02` state and compensation handoff model. |
| Deterministic provider failure/replay exercises, Stripe sandbox evidence, and deployed-worker verification | `WS05-04` | Runs after the source-owned WS05 domain implementations exist and uses `WS05-01B` when final worker-hosting facts are required. |
| Final worker hosting, scaling, provider deployment configuration, and deployed worker runtime proof | `WS05-01B` | Its existing final-infrastructure trigger remains false; `WS05-02` must not promote temporary hosting into production evidence. |
| Deployed dashboards, alerts, webhook-delivery monitoring, Stripe control-plane evidence, key operations, and incident/recovery procedures | `WS09` and `WS10` | `WS05-02` may provide safe source signals and bounded identifiers needed by later operations, but it does not close deployed operational controls. |

The allocation has no gap or overlap: `WS05-02` owns the repository payment and
booking state machines and their webhook authority, while later passes own the
financial workflows that consume compensation handoffs and the environments
needed for provider/runtime proof.

## 5. What Happens Next

This section identifies the next executable engineering work and whether any
technical fact prevents it from beginning.

`WS05-02 - Payment and booking state machines with webhook authority` is the
next executable work. Its accepted durable-job, database, authorization, and
financial-policy prerequisites are present on the current baseline. The final
worker host and later Stripe sandbox or deployed-provider evidence are not
required to design and implement the repository-owned lifecycle honestly.

There is no current blocker to planning `WS05-02` as one executable pass.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS05-02 - Payment and booking state machines with webhook authority` |
| Intake outcome | Execute parent as one pass |
| Accepted baseline | `fff8d65f11e4137cb2210e22855d5b8ee9ac6faf` |
| Intake path | `docs/production-readiness/planning/passes/ws05/ws05-02-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`; `docs/production-readiness/planning/templates/PASS-INTAKE-TEMPLATE.md`; `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`; `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`; `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md`; `docs/production-readiness/decisions/pickup-lane-decision-packet-3-approved.md`; accepted `WS02-04B2A2B2`, `WS02-04C2`, `WS03-04`, `WS04-02A/B/C`, `WS04-03A`, and `WS05-01A` artifacts; current accepted payment, booking, checkout, webhook, credit, and participant source |
| Execution-register state | `WS05-01A` is accepted; mandatory `WS05-01B` remains deferred for final worker hosting/runtime proof; `WS05-02` is not yet implemented and requires this intake before first-time planning. |
| Approved decisions and prerequisites | DBP-02 / PAY-007 canonical financial authority is approved; accepted durable-job, transaction, invariant, SQL/value, migration, authorization, provider-input, and retry/unknown-outcome contracts are available. |
| Child order | Not applicable - `WS05-02` remains one executable pass |
| Final-infrastructure classification | Repository-owned payment/booking states, Stripe interfaces, durable handoffs, and deterministic current tests are executable now. No final hosting, database-provider, or worker-platform fact is required. Existing later owners retain Stripe sandbox, provider-dashboard, deployed-worker, observability, and operational evidence. |
| Mandatory deferred follow-up created by this intake | None. Existing `WS05-01B`, `WS05-04`, `WS09`, and `WS10` obligations remain open under their accepted triggers and boundaries. |
| Proposed canonical plan path | `docs/production-readiness/planning/passes/ws05/ws05-02-payment-booking-state-machines-webhook-authority.md` |
| Proposed requirement declaration | `backend/tests/support/requirements/ws05_02.json` |
| Proposed trusted test or verification location | `backend/tests/workflows/payment_booking_state_machines_webhook_authority/` |
| Blockers | None |
| Exact next allowed action | Begin Gate A for `WS05-02` from accepted baseline `fff8d65f11e4137cb2210e22855d5b8ee9ac6faf` on branch `pr/WS05-02`; verify this intake SHA-256 before planning. |
