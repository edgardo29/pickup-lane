# WS05-02 - Payment And Booking State Machines With Webhook Authority

This work gives Pickup Lane one explicit, durable payment and booking lifecycle in which Stripe decides provider payment outcomes and the application decides reservations, roster entitlement, capacity conflicts, and compensation needs.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

Pickup Lane already calculates official-game checkout amounts on the server,
creates a pending booking and roster hold before calling Stripe, records Stripe
event IDs, and waits for a signed webhook before granting paid entitlement. The
current implementation does not yet have one complete transition policy across
checkout, PaymentIntent state, booking state, hold expiry, delayed events, and
capacity-conflict compensation. Webhook processing also occurs inside the HTTP
request instead of using the accepted durable-job foundation.

This work establishes one canonical lifecycle for official in-app checkout and
the shared Stripe payment records used by community publish fees. It makes
payment, booking, reservation, refund, and compensation state distinct; moves
verified webhook events into durable processing; makes stale and out-of-order
event handling deterministic; and preserves the existing game-first database
serialization and provider-checkpoint rules.

The same work completes the application-owned saved-card lifecycle. Stripe
Customer, SetupIntent, and PaymentMethod ownership remains provider-verified,
while Pickup Lane stores only the identifiers and card-display metadata needed
to select, refresh, default, and detach a saved method safely. Saving a card is a
separate user action from authorizing an off-session paid-waitlist charge. The
existing paid-waitlist auto-charge consent remains its own explicit authorization
and is not implied by merely saving or defaulting a card.

This pass does not implement the general refund, credit-restoration, dispute,
notice, scheduled reconciliation, or operator financial-repair workflows. It
creates truthful compensation and reconciliation states that those workflows
can consume. It also does not claim Stripe dashboard, sandbox, deployed-worker,
deployed logging, alerting, or final hosting evidence.

## 2. What Must Be True

These requirements define the finished financial lifecycle. They separate
provider truth from application truth so a successful charge, a reserved game
spot, and a confirmed booking can never be mistaken for the same fact.

### 2.1 Trusted Checkout Identity And Amount

Every checkout must belong to the authenticated user and to one durable local
booking/payment operation. The server must derive game price, party size,
currency, platform fee, available game-credit balance, credit application, and
remaining Stripe amount from locked current database state. Client-supplied
amounts, currency, user IDs, Stripe Customer IDs, and provider payment status
must not influence the calculation.

PaymentIntent creation and PaymentIntent confirmation have distinct protected
identities.

The PaymentIntent creation operation must have:

- one durable local payment identity;
- one immutable creation-request fingerprint;
- one stable Stripe creation idempotency key.

The creation fingerprint contains only fields that are immutable for the life of
that PaymentIntent creation operation. It must not bind a replaceable checkout
PaymentMethod when the same PaymentIntent is allowed to accept a different
verified method after `requires_payment_method`.

Each server-side confirmation attempt must instead have its own durable
confirmation-attempt identity, immutable confirmation fingerprint, and stable
Stripe confirmation idempotency key. The confirmation fingerprint binds the
payment, authenticated owner, Stripe Customer, selected PaymentMethod, amount,
currency, booking, and other protected confirmation inputs.

Repeating the same creation or confirmation attempt with the same protected
inputs must reuse its existing local identity and Stripe idempotency key.
Reusing either identity with changed protected inputs must fail before another
provider mutation occurs.

A user who receives `requires_payment_method` while the reservation is still
live may choose another verified saved method. That choice creates a new
confirmation-attempt identity under the existing PaymentIntent. It must not
change the immutable PaymentIntent creation fingerprint or reuse the prior
confirmation attempt's identity for different PaymentMethod inputs.

The pending booking, reservation, participant rows, credit reservation, payment
row, creation fingerprint, creation idempotency identity, and any current
confirmation-attempt identity must commit before the corresponding Stripe
mutation. No database lock may be held during a Stripe network call. After a
provider call, the workflow must reacquire the game row first and then re-read
and lock dependent state according to the accepted lock-order contract before
making any reservation, capacity, credit, booking, or entitlement decision.

### 2.2 Separate Financial And Booking State

Stripe PaymentIntent state must be stored separately from Pickup Lane booking
and reservation state. A browser callback, return URL, client-side Stripe
result, or successful HTTP response must never mark a booking paid, confirm a
participant, or consume a game spot.

Each payment record must store both the exact last observed Stripe
PaymentIntent status and a normalized application payment-operation state. The
provider status preserves Stripe truth without forcing application code to
interpret provider strings differently in each workflow. The normalized state
controls Pickup Lane behavior but may change only from a signed event or a
server-side provider observation.

The application must support and validate these normalized payment-operation
states:

| Payment-operation state   | Meaning                                                                                                                                                                                                                                          |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `requires_payment_method` | Stripe requires a usable payment method before another confirmation attempt can proceed.                                                                                                                                                         |
| `requires_confirmation`   | Stripe reports that the PaymentIntent is ready for server-controlled confirmation. No paid entitlement exists.                                                                                                                                   |
| `requires_action`         | Stripe requires customer action. No paid entitlement exists.                                                                                                                                                                                     |
| `processing`              | Stripe is processing the attempt and the final provider outcome is not known.                                                                                                                                                                    |
| `requires_capture`        | Stripe reports a manual-capture state that is not part of Pickup Lane's automatic-capture checkout contract. No entitlement may be granted from this state.                                                                                      |
| `succeeded`               | Stripe reports that the PaymentIntent succeeded. This state remains true even if a separate refund later succeeds.                                                                                                                               |
| `failed`                  | The local payment operation is closed without provider success after a definitive failed attempt or after the reservation has been released and no continuing provider-success possibility is being represented as a nonterminal provider state. |
| `canceled`                | Stripe reports that the PaymentIntent was canceled.                                                                                                                                                                                              |
| `unknown`                 | A provider mutation or observation ended without a trustworthy outcome. No entitlement may be granted from this state.                                                                                                                           |

The application must support and validate these booking states:

| Booking state         | Meaning                                                                                                              |
| --------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `pending_payment`     | The booking has a live payment reservation and is not confirmed.                                                     |
| `confirmed`           | The complete party has confirmed roster entitlement.                                                                 |
| `waitlisted`          | The complete party is waiting for capacity and has no active reservation or confirmed roster entitlement.            |
| `partially_cancelled` | Part of a previously confirmed party remains entitled.                                                               |
| `cancelled`           | The booking was explicitly cancelled and has no active reservation.                                                  |
| `expired`             | A previously held checkout or promotion reservation ended before confirmation.                                       |
| `failed`              | A definitive payment or application failure released the reservation before entitlement.                             |
| `capacity_conflict`   | Stripe succeeded, but Pickup Lane could not grant the requested roster entitlement after current-state revalidation. |

The reservation lifecycle must be explicit as `not_required`, `held`,
`confirmed`, `released`, or `capacity_conflict`.

The legal booking/reservation combinations are:

| Booking state         | Allowed reservation state    | Expiry requirement                                                                                                                                                                                             |
| --------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pending_payment`     | `held`                       | Non-null future expiry while the hold is live.                                                                                                                                                                 |
| `confirmed`           | `confirmed`                  | No active expiry.                                                                                                                                                                                              |
| `partially_cancelled` | `confirmed`                  | No active expiry for the remaining entitlement.                                                                                                                                                                |
| `waitlisted`          | `not_required`               | No reservation expiry.                                                                                                                                                                                         |
| `expired`             | `released`                   | The former hold expiry is retained as historical booking data when useful, but no active reservation expiry exists.                                                                                            |
| `failed`              | `released`                   | No active reservation expiry.                                                                                                                                                                                  |
| `capacity_conflict`   | `capacity_conflict`          | No active reservation expiry.                                                                                                                                                                                  |
| `cancelled`           | `released` or `not_required` | `released` when a reservation previously existed; `not_required` when the booking was cancelled from a state that never owned a reservation, such as an ordinary waitlist state. No active reservation expiry. |

`not_required` is therefore used only where the booking does not currently own
capacity and has not just released a prior hold. A held reservation must have an
expiry time, must count the complete party against available capacity, and must
be represented by the matching pending participant rows.

Confirmation, release, expiry, and capacity conflict must update the booking,
reservation, participants, credit usage, and capacity projection in one database
transaction under the game lock.

The current two-minute checkout hold remains the reservation duration. A hold
is live only while database time is strictly before its expiry.

When database time reaches or passes the expiry boundary, entitlement must be
released even if Stripe is still in a nonterminal or unresolved state. The
booking becomes `expired`, the reservation becomes `released`, pending
participants lose the pending entitlement, reserved credit is released, and
capacity is recomputed under the game lock.

Expiry must not falsify provider truth. If the PaymentIntent remains
`unknown`, `processing`, `requires_action`, `requires_confirmation`,
`requires_capture`, or `requires_payment_method`, that payment state remains
truthful after the reservation is released. The expired booking cannot regain
entitlement merely because the provider operation remains unresolved.

If an authoritative `succeeded` observation arrives after expiry, the payment
remains `succeeded`, no participant is confirmed, and exactly one active
compensation requirement is created for the payment and booking.

Refund state remains separate from PaymentIntent state. A succeeded refund may
change the booking's financial summary to `partially_refunded` or `refunded`,
but it must not rewrite a succeeded PaymentIntent as failed or canceled.

### 2.3 Explicit Compensation

When Stripe succeeds but the reservation cannot become a confirmed booking,
Pickup Lane must record the actual application outcome and one durable
compensation requirement. The payment remains `succeeded`; the booking becomes
`expired` when the hold elapsed or `capacity_conflict` when current capacity or
reservation integrity prevents confirmation; and no participant is confirmed.

A compensation record must identify the booking, payment, reason, amount,
currency, requested action, current status, and safe timestamps. The supported
current requested action is `refund`. Its lifecycle is `required`,
`processing`, `succeeded`, `failed`, or `cancelled`.

For capacity/expiry compensation, `required` and `processing` are the active
states. There may be at most one active compensation for the same payment and
booking regardless of whether the triggering reason was hold expiry,
capacity conflict, or another equivalent no-entitlement result covered by this
pass.

The first active compensation record is the durable refund obligation. Repeated
or concurrent equivalent triggers must reuse or no-op against that obligation
rather than create a second active refund requirement. A later duplicate trigger
with a different capacity/expiry reason must not create a parallel active
compensation merely because the reason string differs.

This pass must create the compensation requirement transactionally with the
failed entitlement decision. It must not perform a new ad hoc Stripe refund
inside webhook state application. Existing refund records and refund webhook
compatibility remain intact, while the general mechanism that executes and
reconciles compensation belongs outside this pass.

### 2.4 Durable Webhook Authority

The Stripe webhook route must verify the signature against the unmodified
request body using the configured webhook secret. An invalid signature,
malformed event identity, unsupported environment configuration, or failed
database commit must not be acknowledged as successfully accepted.

For a valid event, the route must persist a unique provider event record and,
for a supported event, enqueue exactly one executable durable job in the same
database transaction. The route may acknowledge only after that transaction
commits. Duplicate delivery of an already committed provider event must return
a successful duplicate acknowledgment without creating another event or job.

The durable payload must contain only the internal payment-event identifier.
It must not contain a client secret, card data, raw request body, Stripe secret,
full provider payload, email address, or user-entered text. The persisted event
envelope must retain only the allowlisted provider and application fields needed
to process and audit the event: event ID and type, provider creation time,
object ID and status, amount, currency, latest charge or refund identity when
applicable, and the bounded metadata references needed to resolve the local
payment, booking, game, or refund.

The production worker registry must include the webhook-event handler. The
handler must be idempotent under duplicate execution and lease recovery. It
must distinguish transient provider/database failures from permanent invalid
events, preserve a safe processing error code, and leave exhausted work visible
through the durable-job inspection surface. Unsupported event types must be
recorded as ignored without becoming executable work.

### 2.5 Duplicate, Delayed, Missing, And Out-Of-Order Outcomes

All PaymentIntent event types consumed by Pickup Lane must pass through one
transition function. Before a provider event can regress local state or when
its event payload cannot establish the current outcome safely, the handler must
retrieve the current PaymentIntent and apply that authoritative status instead
of trusting arrival order.

A local `succeeded` PaymentIntent must never regress because a delayed
`processing`, `requires_action`, `requires_confirmation`, `requires_capture`,
`requires_payment_method`, failed-attempt event, or `canceled` event arrives. A
definitive provider state may resolve local `unknown`, `processing`,
`requires_action`, `requires_confirmation`, or `requires_payment_method` state.
A late authoritative success may supersede an earlier failure observation, but
it must still pass current booking, reservation, and capacity rules before
entitlement is granted.

An unknown PaymentIntent creation outcome must preserve the committed local
operation, immutable creation fingerprint, and original Stripe creation
idempotency key. Durable recovery may repeat the exact creation request with
that same identity to recover the provider object; it must never issue a new key
or changed creation payload.

An unknown confirmation outcome must preserve the confirmation-attempt identity
and retrieve the known PaymentIntent before deciding whether another provider
mutation is safe. A new PaymentMethod choice after a definitive
`requires_payment_method` result creates a new confirmation-attempt identity
rather than mutating or reusing the prior confirmation identity.

Checkout status reads must remain local and bounded rather than turning browser
polling into unbounded provider traffic.

The same transition function must be used by webhook handling and targeted
server reconciliation so the source of the observation does not change the
state rules. Broad scheduled mismatch discovery, disputes, and operator-driven
financial repair are not part of this work.

### 2.6 Saved Payment Methods

Only an active authenticated user may create a SetupIntent, synchronize a
completed SetupIntent, list saved methods, choose a checkout method, change the
default method, or detach a method. Every operation must verify that the Stripe
Customer and PaymentMethod belong to that same user. Cross-user identifiers
must not reveal or mutate another user's method.

The existing add-card flow is the user's consent to save a PaymentMethod. The
user explicitly starts the saved-card action, the backend creates an
owner-bound SetupIntent for future application use, and synchronization occurs
only after that SetupIntent succeeds for the same Stripe Customer. The
`set_as_default` choice is a separate explicit choice within that save action.

Saving or defaulting a card does not authorize an off-session waitlist charge.
Paid-waitlist auto-charge remains governed by its separate accepted consent
fields and consent version. Checkout or saved-card code must not treat ordinary
saved-card consent as equivalent to off-session charge consent.

Saved records may contain only the internal owner, Stripe Customer and
PaymentMethod identifiers, card fingerprint, brand, last four digits,
expiration month/year, default flag, lifecycle status, and safe timestamps.
Raw card numbers, CVC, billing details, client secrets, SetupIntent secrets,
and complete provider objects must never be persisted or returned by saved-card
read APIs.

Provider-mutating saved-card actions must have a durable local operation
identity, immutable protected-input fingerprint, and explicit state before the
provider call. Setup, default, detach, and default-clear operations must use
stable Stripe idempotency keys where Stripe accepts mutation idempotency. An
unknown outcome must be represented as requiring reconciliation, not reported
as local success or replayed under a different identity.

The payment-method-operation lifecycle is `pending`, `provider_unknown`,
`succeeded`, or `failed`. No separate `cancelled` operation state is introduced
by this pass because the current saved-card workflow has no independently
authorized cancellation transition for an in-flight provider mutation.

Synchronizing or using a saved method must retrieve current provider ownership
and card metadata. It must refresh changed brand, last-four, and expiration
metadata, mark an expired method unusable, and reject detached, missing,
fingerprint-mismatched, or differently owned methods. Detach must be
idempotent. Default changes must leave at most one active default per user and
must not claim local/provider agreement when the provider result is unknown.

The browser may receive a SetupIntent or PaymentIntent client secret only in
the authenticated response for the operation's owner. Client secrets must not
appear in URLs, logs, analytics, errors, durable jobs, database records,
support/admin payloads, or responses to other users.

### 2.7 Compatibility And Security

The implementation must preserve the accepted transaction checkpoint,
game-first lock order, credit-ledger, database-value, SQL-safety, migration,
authorization, provider-input, timeout, and durable-job contracts.

Community publish-fee payments must continue to use Stripe-authoritative
PaymentIntent state and signed webhook finalization. Paid waitlist promotion
must continue to reserve capacity before provider work and reacquire the game
lock before confirmation. Full-credit official checkout must continue to
confirm without a PaymentIntent while maintaining the same booking,
reservation, participant, history, and credit invariants.

Generic booking, payment, and payment-event mutation routes must remain
retired. Public and user-facing reads must expose only the financial state
needed by the authorized caller. Provider IDs, safe operator details, and
repair controls must retain their accepted authorization boundaries.

## 3. Design

The design uses PostgreSQL as the durable application-state authority and
Stripe as the PaymentIntent authority. Provider calls occur between committed
database checkpoints, while every entitlement decision occurs afterward in a
short, game-serialized database transaction.

### 3.1 Persisted State And Constraints

The existing payment state constraint must add `unknown`,
`requires_confirmation`, and `requires_capture` where they are not already
allowed, and the payment row must add a constrained `provider_status` for the
exact last observed Stripe status. `succeeded` continues to require `paid_at`;
non-success states must not synthesize a paid timestamp.

The existing provider PaymentIntent uniqueness and local creation-idempotency
uniqueness remain database-enforced.

The payment operation stores:

- a canonical immutable PaymentIntent creation fingerprint;
- the stable PaymentIntent creation idempotency key;
- the exact last provider status;
- the normalized application payment state.

Server-side confirmation attempts are represented separately from the immutable
creation fingerprint. Each confirmation attempt records:

- the owning payment and booking;
- authenticated user and Stripe Customer identity;
- selected Stripe PaymentMethod identity;
- immutable confirmation fingerprint;
- stable confirmation idempotency key;
- attempt outcome or unresolved state;
- safe timestamps and bounded diagnostic code.

A new verified card chosen after `requires_payment_method` therefore creates a
new confirmation attempt while preserving the same PaymentIntent creation
identity.

The booking state constraint must add `capacity_conflict`, and the booking must
store `reservation_status`. Row-local database constraints must enforce the
complete booking/reservation matrix:

- `pending_payment` requires reservation `held` and a non-null live expiry;
- `confirmed` and `partially_cancelled` require reservation `confirmed`;
- `waitlisted` requires reservation `not_required`;
- `expired` and `failed` require reservation `released`;
- `capacity_conflict` requires reservation `capacity_conflict`;
- `cancelled` permits reservation `released` when a hold previously existed or
  `not_required` when no reservation was ever owned;
- only `held` may have an active reservation expiry;
- `not_required`, `confirmed`, `released`, and `capacity_conflict` must not
  represent an active reservation expiry;
- a held reservation cannot report a refunded or restored financial summary;
- a capacity-conflict booking with a Stripe charge must keep its booking
  financial summary truthful as paid until refund state says otherwise.

The cross-table rule that a confirmed paid booking corresponds to a succeeded
Stripe payment or a fully redeemed credit-only checkout is enforced by the
canonical transition service under row locks and proved against PostgreSQL. It
must not be implemented as an unmaintainable cross-table check constraint.

Booking status history must include reservation-state changes with the same
transition entry rather than leaving reservation movement unaudited.

A payment-compensation table owns compensation state. It references one booking
and payment, stores the requested action and reason as constrained values,
stores integer-cent amount and explicit currency, and records state timestamps
and safe error code fields.

For capacity/expiry compensation, PostgreSQL must enforce at most one active
compensation per payment and booking, where active means `required` or
`processing`. The active uniqueness rule must not include the reason as part of
the uniqueness key because that would permit parallel refund obligations for the
same successful payment. Completed, failed, or cancelled historical
compensations remain retainable according to the state model.

A payment-method-operation table owns SetupIntent creation, saved-method sync,
default selection, detach, and default-clear mutation identity. Operation kinds
are `setup_create`, `sync`, `set_default`, `detach`, and `clear_default`;
operation states are `pending`, `provider_unknown`, `succeeded`, and `failed`.
The table stores only internal/user/method references, operation kind and state,
request fingerprint, Stripe idempotency key, safe provider object reference
when available, safe error code, and timestamps. It must not store a client
secret or full provider response.

The payment-event record must retain provider creation time and the normalized
event envelope described above. Its processing states are `pending`,
`processing`, `processed`, `failed`, and `ignored`. `processed` and `ignored`
are terminal successful handling outcomes; `failed` is a terminal semantic or
exhausted-processing outcome. A transient attempt returns the event to
`pending` with a safe error code while the durable job is retryable.

Schema changes must follow the current clean-rebuild Alembic policy. Existing
table changes belong in each table's canonical migration. Each genuinely new
table receives its own canonical migration at the current head, with dependency
order, model metadata, constraints, indexes, upgrade/downgrade behavior,
empty-database upgrade, prior-schema upgrade, and model/head drift kept
consistent.

### 3.2 Checkout Checkpoint And Provider Calls

Checkout begins under the owning game-row lock. It expires stale holds, rejects
duplicate active participation or waitlist state, recomputes current capacity,
calculates the complete-party amount and available credit, verifies the chosen
saved method when a Stripe balance remains, and builds the pending booking,
held reservation, participants, credit reservation, and payment operation.

The protected PaymentIntent creation request is normalized from:

- payment and booking IDs;
- authenticated payer and Stripe Customer IDs;
- amount and currency;
- game ID and complete-party count;
- bounded metadata references and credit/total snapshots.

The selected Stripe PaymentMethod is not part of the immutable PaymentIntent
creation fingerprint for a checkout that permits another verified card after
`requires_payment_method`.

The normalized creation representation produces the stored creation
fingerprint. The PaymentIntent create key is stable for the payment operation.

When server confirmation is required, the application creates a distinct
confirmation-attempt identity. Its protected representation contains:

- payment and booking IDs;
- authenticated payer and Stripe Customer IDs;
- selected Stripe PaymentMethod ID;
- amount and currency;
- game and complete-party identity;
- the provider PaymentIntent ID;
- bounded confirmation metadata.

That representation produces a confirmation fingerprint and stable
confirmation idempotency key. A retry of the same confirmation attempt must
reuse both. Choosing another verified method creates another confirmation
attempt rather than changing the existing fingerprint.

After the local checkpoint commits, checkout calls Stripe without database
locks. It then reacquires the game row and locks/revalidates dependent state
using the ordering in section 3.3 before recording the provider identity and
state.

If the response is lost or ambiguous, the application records `unknown` for
the appropriate operation, preserves the corresponding immutable identity, and
schedules exact-identity recovery. It never creates a second local booking,
reserves credits twice, changes an existing operation's idempotency identity,
or reports confirmed entitlement.

Full-credit checkout follows the same locked local preparation but confirms
the reservation, participant rows, booking, and credit redemption in one local
transaction without creating a Stripe payment operation.

### 3.3 Canonical Transition Service

One internal transition service owns all PaymentIntent-to-application state
changes. It accepts a normalized authoritative provider observation, locks the
game first for booking payments, re-reads all dependent rows, validates
provider IDs, amount, currency, Customer, payment, booking, game, and bounded
metadata references, then applies one transition or a no-op.

For every capacity-sensitive booking transition, the accepted cross-family lock
order is:

1. owning `Game` row;
2. affected `Booking` rows;
3. affected `WaitlistEntry` rows;
4. affected `GameParticipant` rows;
5. financial/support rows required by that transition.

Multiple rows inside one family are locked in stable primary-key order unless an
accepted prerequisite already defines a stricter stable order.

Entering the financial/support family must never be followed by acquiring an
earlier `Game`, `Booking`, `WaitlistEntry`, or `GameParticipant` lock. Existing
financial services, including game-credit operations, retain their accepted
internal row ordering. WS05-02 must not introduce a new reverse financial lock
order merely for payment processing.

For WS05-02 transitions, financial/support rows may include `Payment`,
`UserPaymentMethod`, game-credit/usage rows, `Refund`,
`PaymentCompensation`, and `PaymentEvent` when genuinely required. A path must
lock only the rows it needs and preserve the existing service-owned order among
financial rows. Any path that cannot satisfy both that accepted internal order
and the cross-family order above must be redesigned before implementation rather
than creating a reverse acquisition.

The Stripe-to-application mapping is:

| Stripe observation                    | Stored provider status    | Normalized application state and behavior                                                                                                                                                                                           |
| ------------------------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `requires_payment_method`             | `requires_payment_method` | Set normalized state to `requires_payment_method`. Record safe latest-attempt failure when present. Keep the operation reusable only while the reservation is live. A new verified method uses a new confirmation-attempt identity. |
| `requires_confirmation`               | `requires_confirmation`   | Set normalized state to `requires_confirmation`. Keep entitlement pending and allow only the reviewed server confirmation path to advance the operation.                                                                            |
| `requires_action`                     | `requires_action`         | Set normalized state to `requires_action`. Keep entitlement pending and return action-required state only to the authorized checkout owner.                                                                                         |
| `processing`                          | `processing`              | Set normalized state to `processing`. Keep entitlement pending while the hold remains live.                                                                                                                                         |
| `requires_capture`                    | `requires_capture`        | Set normalized state to `requires_capture`. Automatic-capture checkout grants no entitlement from this state and leaves it visible for bounded operator/reconciliation handling.                                                    |
| `succeeded`                           | `succeeded`               | Set normalized state to `succeeded` and apply success through current reservation and capacity rules.                                                                                                                               |
| `canceled`                            | `canceled`                | Set normalized state to `canceled` and release any live reservation.                                                                                                                                                                |
| Provider mutation outcome unavailable | Last known status or null | Set normalized payment state to `unknown`, preserve the exact creation or confirmation identity involved, and run targeted recovery.                                                                                                |

`payment_intent.payment_failed` is evidence that the latest confirmation
attempt failed; its embedded current PaymentIntent status is still stored
exactly. While the hold remains live, `requires_payment_method` may permit the
same owner to choose another verified saved method under the same PaymentIntent
but with a new confirmation-attempt identity. Once the hold is released, no new
confirmation attempt may consume that reservation.

The supported webhook event mapping is:

| Event type                       | Required handling                                                                                                                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `payment_intent.succeeded`       | Resolve the current PaymentIntent and apply succeeded payment plus the current reservation/capacity outcome.                                                                                 |
| `payment_intent.processing`      | Resolve the current PaymentIntent and apply normalized `processing` unless provider truth has already advanced.                                                                              |
| `payment_intent.requires_action` | Resolve the current PaymentIntent and apply normalized `requires_action`; expose action-required state only to the checkout owner.                                                           |
| `payment_intent.payment_failed`  | Record the safe latest-attempt failure, preserve the exact embedded/current provider status, and either keep a live retryable hold or leave an already released booking without entitlement. |
| `payment_intent.canceled`        | Resolve the current PaymentIntent and apply cancellation only when provider truth has not already advanced.                                                                                  |
| Existing supported refund events | Enter the separate refund transition service and update booking financial summary or compensation only from validated refund state.                                                          |
| Any other event                  | Persist the bounded event identity as ignored and enqueue no executable work.                                                                                                                |

For a valid live hold:

- `requires_payment_method` keeps the reservation held only while another safe
  confirmation attempt remains possible before expiry;
- `requires_confirmation`, `requires_action`, `processing`,
  `requires_capture`, and `unknown` preserve no entitlement and retain the hold
  only until expiry;
- `canceled` or a definitive closed local failure releases the reservation and
  credit, cancels pending participants, records history, and moves the booking
  to `failed`;
- `succeeded` revalidates complete-party capacity and hold integrity, redeems
  reserved credit, confirms all participants and the reservation, marks the
  booking confirmed/paid, records history, and updates game capacity.

At the exact expiry boundary, database time is authoritative. If the booking
still owns a `held` reservation and no authoritative success has been applied,
the canonical transition service must release the reservation regardless of
whether the payment is `requires_payment_method`, `requires_confirmation`,
`requires_action`, `processing`, `requires_capture`, or `unknown`.

That expiry transaction:

- reacquires the game lock;
- moves the booking to `expired`;
- moves reservation state to `released`;
- removes pending roster entitlement;
- releases reserved credit;
- records status history;
- recomputes game capacity;
- preserves the truthful PaymentIntent provider status and normalized payment
  state instead of converting an unresolved provider state into a false payment
  failure.

After expiry, the payment may continue to be unresolved, but it cannot continue
to reserve capacity.

If an authoritative success is later observed for that expired booking, the
payment becomes/remains `succeeded`, entitlement stays released, and the
transition creates or reuses the one active compensation requirement for the
payment and booking.

Paid waitlist auto-promotion is non-interactive and has no browser available to
complete Stripe action. For that source, `requires_action` and
`requires_payment_method` are definitive promotion failures: release the
promotion reservation and reserved credit, remove the party from the active
waitlist under the game lock, preserve the unsuccessful payment attempt, and
emit the existing safe payment-failed notification. It must not retain capacity
while waiting for browser action.

`requires_confirmation` is handled only through the reviewed server
confirmation path. `requires_capture` is not a valid successful automatic
waitlist outcome and must grant no entitlement.

A succeeded auto-charge still revalidates capacity under the game lock; if the
complete party cannot be confirmed, it uses the same truthful
capacity-conflict and compensation path as checkout.

For an expired or otherwise invalid reservation, `succeeded` records payment
success but does not confirm participants. It releases any remaining local
hold, records the truthful booking outcome, creates or reuses the one active
compensation requirement, and updates capacity. Failure or cancellation after a
released reservation is an idempotent terminal update and cannot recreate the
hold.

Every transition must be monotonic with respect to the latest authoritative
provider state and idempotent when repeated. State helpers must reject an
unsupported transition rather than assigning arbitrary strings. Notification
creation may occur only from a committed domain transition and must retain its
existing aggregation/idempotency behavior.

Community publish-fee events use the same provider-state normalization and
anti-regression rules but retain their accepted publish-attempt and entitlement
state machine. Refund events retain their existing separate refund transition
service and are made durable through the same event-ingestion mechanism without
expanding refund policy.

### 3.4 Webhook Ingestion And Durable Processing

The HTTP route reads the body once, verifies Stripe's signature, normalizes the
allowlisted event envelope, and opens one database transaction. It inserts the
unique event row and enqueues a `stripe_webhook_event` version 1 job whose
payload is only the internal event UUID. The durable-job idempotency key is
derived from the provider event ID, and the protected identity binds the job to
that internal event.

The production registry is built in one application module and supplied to the
portable worker command and all enqueue callers. It must not be reconstructed
with different definitions in the route and worker.

Each Stripe job definition owns its own numeric retry policy. Sharing values is
allowed only when the individual job's failure model justifies the same values.

`stripe_webhook_event` version 1 uses five total execution attempts with retry
delays of 1, 5, 30, and 120 seconds.

The basis for this webhook policy is:

- webhook ingestion has already committed the durable event and acknowledged
  only after that durable handoff exists;
- transient database or provider-read failures therefore need local recovery
  without depending on another HTTP request;
- execution is idempotent, so repeating the same durable event does not create a
  second financial transition;
- the schedule provides immediate retry for short failures, then increasingly
  spaced attempts over a bounded 156-second local recovery window;
- the attempt count remains small enough to avoid unbounded provider/database
  pressure;
- Stripe transport redelivery remains a separate provider mechanism and does
  not reset durable-job attempts;
- exhaustion intentionally makes the event and job operator-visible rather than
  retrying indefinitely.

This is an initial source-owned recovery policy, not a claim that 1/5/30/120 is
a universal Stripe or production-provider optimum. Its boundary tests must prove
the exact attempt count, delay progression, final exhaustion, idempotent
re-execution, and operator requeue behavior. Runtime evidence may later require
a separately reviewed policy change.

The webhook definition is executable, validates the exact payload shape, and
classifies known transient provider/database errors separately from permanent
semantic failures.

The handler first reads the event envelope without taking domain row locks. It
retrieves current Stripe state when ordering or completeness requires it, then
invokes the canonical transition service.

For booking payments, row acquisition follows section 3.3. The game row is
always the first capacity-domain lock. Booking, waitlist, and participant rows
follow in the accepted family order. Financial/support rows are acquired only
after those domain rows and must preserve their existing accepted internal
ordering.

The handler and transition use the same SQLAlchemy session as the durable-job
completion update so committed domain effects and the durable job's `succeeded`
transition are one database commit. If the process stops before that commit,
neither the domain transition nor job completion is considered committed and
lease recovery re-enters the idempotent handler.

Transient failures preserve retryable work and a safe event error code.
Permanent validation failures mark the event failed without changing payment,
booking, reservation, participant, credit, refund, or compensation state. On
the last transient attempt, the event becomes failed with an exhausted safe code
and the durable job becomes exhausted. Operator requeue uses the accepted
durable-job repair path and re-enters the same idempotent handler.

The retained payment-event admin repair surface may link an unmatched event to
the correct payment and request durable reprocessing under recent-admin
authorization. It must not let an operator assign arbitrary provider state,
mark a booking paid, or bypass the canonical transition service. Event payload
identity and normalized provider facts remain immutable.

### 3.5 Targeted PaymentIntent Recovery

A second registered job, `stripe_payment_intent_reconcile` version 1, handles a
known checkout operation whose create or confirm outcome is unknown or whose
expected webhook has not yet resolved the local state. Its payload contains
only the internal payment UUID. Its protected identity and idempotency key bind
it to that payment and reconciliation reason.

When no provider PaymentIntent ID was recorded after an unknown creation call,
the handler rebuilds the protected creation request from committed columns,
verifies its creation fingerprint, and repeats creation with the original
Stripe creation idempotency key.

When the provider ID is known, the handler retrieves the PaymentIntent. It does
not blindly repeat an unresolved confirmation. The resulting observation enters
the same canonical transition service used by webhooks.

`stripe_payment_intent_reconcile` version 1 uses five total execution attempts
with retry delays of 1, 5, 30, and 120 seconds.

This job has a distinct numeric-policy basis: its local recovery window must
cross the two-minute reservation boundary so an unknown or missing provider
outcome cannot leave capacity held indefinitely. The initial execution plus
1, 5, 30, and 120-second delays reaches a final scheduled observation after the
two-minute hold boundary. That final observation must invoke the canonical
expiry logic when the reservation is still held and no authoritative success
has been applied.

The retry schedule does not extend the reservation. Database time and the
original expiry remain authoritative.

Exhaustion leaves an unresolved payment truthful, commonly `unknown`, while the
booking/reservation has already been released by normal expiry when its
boundary was reached. The job remains visible for repair. Exhaustion does not
grant entitlement, invent a provider outcome, or reset the attempt count.

Tests must prove the schedule using controlled availability time rather than
sleeping, including the exact expiry crossing, reservation release, attempt
limit, and post-expiry late-success compensation behavior.

This is targeted recovery for a known checkout operation, not broad scheduled
reconciliation.

### 3.6 Saved-Method Operations

Saved-method mutation endpoints require an `Idempotency-Key` header containing
an application UUID for each user action. The frontend creates one UUID when
the user starts an action and reuses it only when retrying that same action. The
backend binds it to the authenticated user, operation kind, target method,
desired default state, and protected request fingerprint.

The user's deliberate start of the add-card flow is consent to save the
resulting PaymentMethod for future Pickup Lane use. The SetupIntent operation
records the authenticated owner and the `set_as_default` choice before the
provider call. Sync may persist the card only when the completed SetupIntent and
PaymentMethod both belong to that owner's Stripe Customer.

That saved-card consent does not authorize paid-waitlist auto-charge. Existing
waitlist auto-charge consent timestamp/version and authorized-method fields
remain the separate authority for off-session charging.

SetupIntent creation records and commits the local operation before calling
Stripe, uses a stable Stripe idempotency key, records the returned SetupIntent
ID, and returns the client secret only to the owner.

The sync endpoint retrieves the completed SetupIntent and PaymentMethod,
requires the same Stripe Customer, checks ownership and status, applies the
five-card and one-default constraints, and stores only safe card metadata.
Repeated sync of the same operation is idempotent.

Default and detach operations commit their pending identity before provider
mutation. On a known success, local saved-method state is updated to match the
provider result. On timeout or ambiguous failure, the operation becomes
`provider_unknown`; the API does not claim success.

A targeted durable handler retrieves provider state and either:

- completes the same operation from current provider truth;
- safely repeats the exact mutation when the provider operation supports
  idempotent replay under the original identity; or
- leaves the operation visible for repair when another mutation cannot be shown
  safe.

It must never issue a changed mutation under the same identity.

The production registry also includes
`stripe_payment_method_operation_reconcile` version 1. Its payload contains
only the internal operation UUID.

This job uses five total execution attempts with retry delays of 1, 5, 30, and
120 seconds, but for a different reason from checkout reconciliation.

The basis for the saved-method recovery policy is:

- the operation has already committed a durable identity and protected
  fingerprint before provider mutation;
- recovery is limited to provider reads or exact idempotent replay under that
  identity;
- the user-facing operation must not remain silently `provider_unknown`
  indefinitely after short transient provider/database failures;
- a bounded 156-second recovery window provides immediate and spaced retry
  opportunities without creating an unbounded provider loop;
- unlike checkout reconciliation, this schedule does not control reservation
  expiry and must not be described as doing so;
- exhaustion leaves the operation `provider_unknown` and operator-visible
  rather than guessing provider success or failure.

This is an initial source-owned recovery policy, not a universal provider
default. Tests must prove the exact attempt count, delays, no changed-payload
replay, no duplicate provider mutation, exhaustion behavior, and operator
visibility. Later provider/runtime evidence may justify a separately reviewed
change.

A permanent ownership, fingerprint, or operation conflict fails without
mutating the saved method; an exhausted transient result remains
`provider_unknown` and operator-visible.

Checkout verification retrieves the selected PaymentMethod, confirms Customer
ownership and fingerprint, refreshes safe display/expiry fields, and locks the
local method before binding it to a confirmation attempt. A provider-detached,
missing, expired, or mismatched method is marked unusable and cannot be charged.

### 3.7 API And Frontend Contract

Checkout initiation returns the internal booking/payment identity, server
amount breakdown, local booking/reservation/payment state, and a client secret
only when the authenticated owner needs Stripe action. Checkout status returns
local state only, including reservation and compensation status, and never
returns a client secret or unrestricted provider object.

The frontend treats all Stripe.js results as progress signals. After required
customer action, it polls the authenticated local checkout status. It navigates
to the game only when booking and reservation are confirmed and the relevant
payment is succeeded or the checkout was fully credit-covered.

`requires_payment_method`, `requires_confirmation`, `requires_action`,
`processing`, `requires_capture`, and `unknown` are non-entitlement states.
The UI must distinguish the user-actionable states from states that merely
require server/provider resolution.

A live `requires_payment_method` checkout may allow the owner to select another
verified saved card. That new card creates a new server confirmation attempt
without creating a new booking, PaymentIntent, reservation, or credit hold.

Definitive failure/cancellation permits a safe new checkout after the prior
hold is released. An expired or capacity-conflict booking with successful
payment shows that no spot was granted and that refund follow-up is required; it
must not display ordinary payment-failed copy or ask the user to pay again.

An expired booking whose provider outcome remains unresolved must show that the
spot is no longer reserved while payment resolution is still pending. It must
not imply either payment success or payment failure until provider truth is
known.

Saved-method screens preserve the existing add, select, default, and remove
flows while handling pending/unknown provider operations without optimistic
success. Public UI and API responses continue to expose only brand, last four,
expiry, default, and usable status.

## 4. Failures And Edge Cases

These cases define how the lifecycle behaves when requests, provider results,
or database state do not arrive in the ideal order. Correct handling prevents
duplicate charges, false roster entitlement, lost compensation, and disclosure
of payment secrets.

1. **Duplicate checkout request**
   - **Condition:** The same user repeats checkout for the same live operation.
   - **Required behavior:** Reuse the matching booking, payment, reservation, credit hold, PaymentIntent creation fingerprint, and creation idempotency identity; do not create duplicate local or Stripe work.

2. **Conflicting creation-operation reuse**
   - **Condition:** An existing PaymentIntent creation operation or idempotency identity is presented with different immutable protected creation inputs.
   - **Required behavior:** Reject before calling Stripe and leave all existing state unchanged.

3. **Changed card after `requires_payment_method`**
   - **Condition:** A live checkout receives `requires_payment_method` and the owner chooses another verified saved card.
   - **Required behavior:** Preserve the existing booking, reservation, PaymentIntent creation identity, and credit hold. Create a new confirmation-attempt identity/fingerprint for the new PaymentMethod. Never mutate or reuse the previous confirmation identity with changed PaymentMethod inputs.

4. **Unknown PaymentIntent creation**
   - **Condition:** Stripe may have created a PaymentIntent, but the create response is lost or times out.
   - **Required behavior:** Mark the payment unknown, retain the committed creation operation, recover only with the original creation fingerprint and creation idempotency key, and grant no entitlement.

5. **Unknown confirmation**
   - **Condition:** Server-side confirmation returns an ambiguous outcome.
   - **Required behavior:** Preserve the confirmation-attempt identity and retrieve the known PaymentIntent through targeted recovery before any further provider mutation or local finalization.

6. **Browser abandonment**
   - **Condition:** The browser closes or stops polling after the local hold or provider operation exists.
   - **Required behavior:** Server/webhook processing continues independently; the hold expires by database time even if provider state remains unresolved; a later authoritative success creates truthful compensation rather than silent entitlement.

7. **Nonterminal provider state at hold expiry**
   - **Condition:** Database time reaches the reservation expiry while the payment remains `requires_payment_method`, `requires_confirmation`, `requires_action`, `processing`, `requires_capture`, or `unknown`.
   - **Required behavior:** Release reservation, pending participant entitlement, and reserved credit under the game lock; mark the booking expired; preserve the truthful payment/provider state; do not extend the hold or mark payment failed merely to release capacity.

8. **Duplicate webhook delivery**
   - **Condition:** Stripe delivers the same event ID more than once or two requests race to insert it.
   - **Required behavior:** One event and one durable job exist; every delivery is acknowledged after durable identity is known; domain effects occur at most once.

9. **Out-of-order provider events**
   - **Condition:** An older failure, cancellation, action-required, requires-confirmation, requires-capture, or processing event arrives after a newer outcome.
   - **Required behavior:** Retrieve provider truth when needed and apply a monotonic no-op or transition; never regress succeeded payment or confirmed entitlement.

10. **Webhook worker interruption**
    - **Condition:** The worker stops after claim or during event handling.
    - **Required behavior:** Lease recovery re-runs the idempotent handler; a committed domain transition and job completion are not duplicated, and an uncommitted transaction leaves no partial domain effects.

11. **Invalid event references**
    - **Condition:** Amount, currency, Customer, provider object, metadata, payment, booking, or game references do not match committed state.
    - **Required behavior:** Mark the event permanently failed with a safe code, make no financial or entitlement mutation, and retain operator-visible durable history.

12. **Payment success after hold expiry**
    - **Condition:** Stripe succeeds after the two-minute reservation has expired.
    - **Required behavior:** Keep payment succeeded, keep the booking unconfirmed and expired, keep the reservation released, create or reuse exactly one active compensation requirement, and never label the payment failed.

13. **Payment success with insufficient current capacity**
    - **Condition:** Under the game lock, the complete party cannot be confirmed despite provider success.
    - **Required behavior:** Record booking and reservation capacity conflict, confirm no participants, preserve succeeded payment, and create or reuse exactly one active compensation requirement.

14. **Concurrent expiry and capacity-conflict compensation triggers**
    - **Condition:** Duplicate or concurrent handling reaches equivalent no-entitlement outcomes with different capacity/expiry reasons for the same payment and booking.
    - **Required behavior:** PostgreSQL and transition logic permit only one active compensation obligation. The second trigger reuses or no-ops against the existing active compensation instead of creating another refund obligation.

15. **Partial participant or credit state**
    - **Condition:** Pending participant count, reservation, or credit rows do not match the committed booking snapshot.
    - **Required behavior:** Do not grant partial entitlement; record a safe failed event and leave repairable state without overfilling or double-consuming credit.

16. **Saved method belongs to another Customer or user**
    - **Condition:** A SetupIntent, PaymentMethod, local method ID, fingerprint, or Stripe Customer does not belong to the authenticated user.
    - **Required behavior:** Reject without revealing another user's saved method and without provider or local mutation.

17. **Saved-card consent confusion**
    - **Condition:** Code attempts to treat an ordinary saved-card add/default action as authorization for a later off-session paid-waitlist charge.
    - **Required behavior:** Reject that assumption. Saving/defaulting a method and paid-waitlist auto-charge consent remain distinct contracts; the existing waitlist consent fields remain required for auto-charge.

18. **Saved-method provider outcome is unknown**
    - **Condition:** Setup, default, detach, or default-clear mutation times out or loses its response.
    - **Required behavior:** Preserve the operation as provider-unknown, report no success, reconcile using the same operation identity, and prevent conflicting local actions until resolved or repaired.

19. **Stale or expired saved-card metadata**
    - **Condition:** Current provider data differs from the local display/expiry snapshot, or the method is detached or expired.
    - **Required behavior:** Refresh safe metadata when ownership still matches; otherwise mark the method unusable and reject checkout.

20. **Client-secret exposure attempt**
    - **Condition:** A different user, admin list, URL, log, analytics path, error, durable payload, or support response could receive a client secret.
    - **Required behavior:** Return no secret and persist/log none; only the authenticated owner-specific initiation response may contain it.

21. **Refund or compensation event after payment success**
    - **Condition:** A refund progresses after the PaymentIntent succeeded.
    - **Required behavior:** Update separate refund, compensation, and booking financial-summary state without rewriting the PaymentIntent outcome.

22. **Paid waitlist auto-charge requires browser action**
    - **Condition:** An off-session paid waitlist promotion returns `requires_action` or `requires_payment_method`.
    - **Required behavior:** Release the promotion hold and credit, remove the party from the active waitlist, record the unsuccessful attempt and safe notification, and never hold capacity for unavailable browser interaction.

23. **Manual-capture state appears**
    - **Condition:** An automatic-capture checkout or auto-promotion PaymentIntent reports `requires_capture`.
    - **Required behavior:** Store exact provider status and normalized `requires_capture`, grant no entitlement, do not invent capture behavior, and keep the condition visible for bounded reconciliation/operator handling.

## 5. Testing

Testing must prove the complete lifecycle rather than isolated status
assignments. PostgreSQL tests establish persistence, uniqueness, lock ordering,
transaction boundaries, and idempotency; provider doubles establish application
behavior at the Stripe boundary; API and frontend unit tests establish caller
authority and user-visible state without claiming deployed Stripe evidence.

### 5.1 State And Database Proof

Build complete finite matrices for payment, booking, reservation, event,
compensation, refund, and saved-method operation states.

Payment-state proof must include every normalized state:

- `requires_payment_method`;
- `requires_confirmation`;
- `requires_action`;
- `processing`;
- `requires_capture`;
- `succeeded`;
- `failed`;
- `canceled`;
- `unknown`.

Tests must prove every allowed transition, every material rejected transition,
terminal anti-regression, timestamp requirements, and the exact partition of
all database-allowed values.

Booking/reservation tests must prove the complete legal matrix, including:

- `pending_payment` + `held`;
- `confirmed` + `confirmed`;
- `partially_cancelled` + `confirmed`;
- `waitlisted` + `not_required`;
- `expired` + `released`;
- `failed` + `released`;
- `capacity_conflict` + `capacity_conflict`;
- both legitimate `cancelled` cases, `released` and `not_required`.

Tests must prove that only `held` may retain an active reservation expiry.

PostgreSQL constraint tests must prove invalid combinations fail at the
database layer and identify the intended constraint.

Compensation tests must prove the active partial uniqueness rule on payment +
booking across both `required` and `processing`, including concurrent attempts
using different capacity/expiry reasons.

Saved-method operation tests must prove the finite operation state set does not
contain an unsupported `cancelled` transition.

Migration validation must prove empty-to-head and accepted prior-schema-to-head
behavior, one Alembic head, model/head agreement, and successful
downgrade/rebuild under the current migration policy.

### 5.2 Checkout And Concurrency Proof

Focused service/API tests must prove server-derived amount and currency,
authenticated ownership, credit-only/partial-credit/full-Stripe calculations,
complete-party capacity, stable creation fingerprints, stable confirmation
fingerprints, same-operation reuse, same-key conflict, and no duplicate
PaymentIntent or credit reservation.

Tests must specifically prove:

- PaymentIntent creation identity excludes replaceable confirmation-only
  PaymentMethod state;
- repeating the same confirmation attempt reuses the same confirmation identity;
- selecting a different verified card after `requires_payment_method` creates a
  new confirmation attempt without creating a new booking or PaymentIntent;
- a changed card cannot be replayed under the old confirmation identity.

Independent PostgreSQL sessions must prove game-first serialization for two
checkouts competing for remaining capacity and for webhook confirmation racing
with expiry, cancellation, waitlist promotion, or another capacity mutation.

Tests must prove the accepted lock-family order:

1. Game;
2. Booking;
3. WaitlistEntry;
4. GameParticipant;
5. financial/support rows.

They must prove no WS05-02 path acquires one of the first four families after a
financial/support lock and no current financial service introduces a reverse
game/domain lock order.

Persisted final state must be read from a fresh session and must show no
over-capacity roster, partial party, duplicate credit use, or reverse lock
order.

Provider-checkpoint tests must prove local state commits before Stripe, no lock
is held across the provider call, state is reacquired after the call, and an
unknown result leaves recoverable local identity without false success.

### 5.3 Webhook And Recovery Proof

Route tests must use the exact raw body and signature boundary. They must prove
invalid signatures and failed event/job commits are not acknowledged, while a
valid event is acknowledged only after the event and job commit. Concurrent
duplicate deliveries must produce one event, one job, and one set of domain
effects.

Durable webhook worker tests must cover:

- success;
- transient retry;
- permanent invalid event;
- exact 1/5/30/120 retry progression;
- five-attempt maximum;
- final-attempt exhaustion;
- lease interruption/recovery;
- stale lease-token rejection;
- same-transaction domain transition plus durable-job completion;
- operator requeue.

The test provider boundary must cover delayed, duplicate, missing, and
out-of-order observations for `requires_payment_method`,
`requires_confirmation`, `requires_action`, `processing`, `requires_capture`,
`succeeded`, `canceled`, and `unknown` states.

Targeted PaymentIntent reconciliation tests must prove:

- exact-idempotency recovery of unknown creation;
- retrieve-before-decision for unknown confirmation;
- no changed-payload replay;
- no provider traffic from ordinary browser status polling;
- identical state application from webhook and reconciliation observations;
- the exact 1/5/30/120 schedule;
- the final scheduled observation crosses the two-minute hold boundary;
- that crossing invokes expiry rather than extending the reservation;
- exhaustion never leaves capacity reserved beyond expiry.

### 5.4 Reservation And Compensation Proof

Tests must cover success before expiry, failure before expiry, exact expiry
boundary, browser abandonment, unresolved state at expiry, success after expiry,
success with a corrupted or unavailable reservation, and success when current
complete-party capacity cannot be granted.

Unresolved-expiry cases must include at least:

- `requires_payment_method`;
- `requires_confirmation`;
- `requires_action`;
- `processing`;
- `requires_capture`;
- `unknown`.

Each case must assert payment, provider status, booking, reservation,
participants, credits, history, compensation, and game capacity together.

Late success and capacity conflict must create exactly one active compensation
record under duplicate and concurrent processing, including when competing
triggers use different expiry/capacity reasons.

Tests must prove no synchronous ad hoc refund mutation occurs in the webhook
transition and that existing refund events remain compatible with separate
payment state.

Paid waitlist tests must prove off-session success, definitive failure,
action-required failure, requires-payment-method failure,
requires-confirmation handling, manual-capture rejection, missing prerequisites,
duplicate events, and a post-provider capacity conflict. They must assert
complete-party behavior, game-first lock ordering, reservation release or
confirmation, waitlist state, credit state, notification idempotency, and
compensation when payment succeeds without entitlement.

### 5.5 Saved-Method And Secret-Safety Proof

Tests must cover:

- SetupIntent ownership and completion;
- the explicit user add-card action as saved-card consent;
- separation between saved-card consent and paid-waitlist auto-charge consent;
- default choice;
- duplicate fingerprint;
- five-card limit;
- metadata refresh;
- expiry;
- detach;
- default replacement;
- idempotent repeat;
- provider-unknown recovery;
- exact saved-method recovery attempt/delay policy;
- final exhaustion remaining `provider_unknown`;
- cross-user attempts.

PostgreSQL assertions must prove one active default and immutable operation
identity under concurrent requests.

Tests must prove payment-method operations use only `pending`,
`provider_unknown`, `succeeded`, and `failed`, with no unexplained cancellation
transition.

API and static checks must prove client secrets appear only in owner-specific
initiation responses and never in status/list/admin schemas, URLs, logs,
exceptions, event envelopes, durable payloads, testing records, or tracked
artifacts. Provider keys and webhook secrets must remain separated by existing
configuration contracts.

### 5.6 Caller And Regression Proof

Compatibility validation must cover official game checkout, full/partial game
credits, paid waitlist promotion, community publish fees, booking/payment/admin
reads, cancellation/refund summaries, saved-card settings, transaction and
timeout policies, database invariants, SQL/value compatibility, migration
rehearsal, authorization matrices, provider-input ownership, retry policy, and
the durable-job platform.

Frontend unit tests must prove progress and error presentation for:

- payment-method-required;
- confirmation-ready;
- action-required;
- processing;
- manual-capture/unresolved;
- unknown;
- succeeded/confirmed;
- definitive failure;
- expired with unresolved payment;
- expired-paid;
- capacity-conflict-paid.

Browser end-to-end or Stripe sandbox tests are not required for this pass and
must not be represented as completed by local tests.

## 6. Done When

This checklist is the engineering completion bar for WS05-02.

- [ ] Checkout amount, currency, credit, ownership, PaymentIntent creation identity, and provider request fingerprint come only from trusted committed server state.
- [ ] PaymentIntent creation identity is immutable while each server confirmation attempt has its own PaymentMethod-bound fingerprint and idempotency identity.
- [ ] A user may change to another verified card after `requires_payment_method` without creating a new booking or PaymentIntent and without reusing a conflicting confirmation identity.
- [ ] Exact provider PaymentIntent status and normalized application payment state are separate, and every supported provider state has an explicit normalized mapping.
- [ ] Payment, booking, reservation, refund, and compensation states are separate, constrained, and changed only through validated transitions.
- [ ] The booking/reservation matrix accounts for `waitlisted`, `not_required`, cancellation with and without a prior hold, and all active-expiry rules.
- [ ] The two-minute reservation lifecycle is complete for confirmation, failure, cancellation, unresolved expiry, late success, and capacity conflict.
- [ ] No unresolved PaymentIntent state can keep capacity or reserved credit after the database-time hold expiry.
- [ ] A successful Stripe payment is never mislabeled as failed when Pickup Lane cannot grant capacity, and at most one active compensation requirement exists for the payment and booking across equivalent expiry/capacity triggers.
- [ ] Signed webhook events are persisted and enqueued atomically, acknowledged promptly after commit, and processed idempotently by the portable durable worker.
- [ ] Domain transition effects and durable-job success are committed together through the accepted worker session model.
- [ ] Booking/capacity transitions preserve the accepted Game → Booking → WaitlistEntry → GameParticipant → financial/support lock-family order and do not create reverse acquisition.
- [ ] Duplicate, delayed, missing, and out-of-order provider outcomes cannot regress terminal state or create duplicate financial, credit, reservation, participant, notification, or compensation effects.
- [ ] Unknown PaymentIntent creation recovers only through the original creation fingerprint/idempotency identity; unknown confirmation is retrieved before another mutation decision.
- [ ] Webhook, PaymentIntent-reconciliation, and saved-method-reconciliation jobs each have an explicit numeric retry basis and deterministic boundary proof rather than inheriting an unexplained global retry policy.
- [ ] Saved-card setup, sync, selection, default, detach, stale refresh, unknown outcome, and cross-user behavior preserve Stripe Customer ownership and minimum stored metadata.
- [ ] Saved-card consent is explicitly defined by the add-card flow and remains distinct from paid-waitlist off-session charge consent.
- [ ] Saved-method operations use only states that have defined transitions.
- [ ] Client secrets and provider secrets remain confined to their authorized boundaries and absent from persistent state, logs, URLs, jobs, and unrelated responses.
- [ ] Existing checkout, credit, waitlist, community publish, refund-summary, authorization, transaction, concurrency, migration, timeout, SQL-safety, and durable-job contracts remain valid.
- [ ] Deterministic PostgreSQL, provider-boundary, API, static, and frontend unit tests prove the complete current lifecycle without claiming sandbox, deployed-runtime, or final-infrastructure evidence.
