# WS04-02A - Transaction Boundary And External-Side-Effect Safety

This pass makes Pickup Lane's current database transaction boundaries explicit
for workflows that also contact external systems or expose user-visible success.

## 1. What This Work Does

This work addresses the point where database writes meet provider calls,
notification effects, admin actions, and other externally visible outcomes. It
matters because a request can otherwise create a provider object, deliver a
visible result, or imply success while the local database transaction later
rolls back or never recorded enough information to reconcile the outcome.

Pickup Lane already has important foundations: request sessions roll back on
exceptions, PostgreSQL statement and lock timeouts are configured, provider
operations have timeout/retry classifications, and several workflows use
idempotency keys, row locks, and support records. Those pieces are not enough by
themselves to prove that side-effecting workflows have a durable local boundary
before and after external work.

This pass establishes that boundary for the current source:

- every current side-effecting workflow has a named database unit of work and
  external operation classification;
- provider mutations that need local recovery have a committed local checkpoint
  before the provider call;
- external outcomes are recorded after the call without claiming success before
  the database state is durable;
- timeouts and unknown outcomes do not trigger blind automatic replay;
- current notification and user-visible success paths are tied to committed
  local state;
- future durable-worker, payment-lifecycle, reconciliation, provider-sandbox,
  and final deployment proof remain outside this pass.

The result is a current-source transaction contract that later database,
migration, durable-job, payment, observability, and closeout work can rely on.

## 2. What Must Be True

The requirements below define the completed behavior for this pass. They focus
on what must be true at the transaction and side-effect boundary, not on the
later worker and provider lifecycle that other passes own.

### 2.1 Side-Effecting Workflows Are Classified

Every current workflow that combines database mutation with a material external
or externally visible effect must have an explicit classification. The
classification must cover at least:

- the workflow name and owning service function;
- the database rows or state that define the local unit of work;
- the external operation or user-visible effect;
- whether the external operation is a read, an idempotent mutation, a
  reconcile-before-retry mutation, manual repair, provider redelivery, or no
  automatic retry;
- the local checkpoint required before the external operation;
- the local state that must be recorded after success, failure, timeout, or
  unknown outcome;
- the downstream owner when full durable execution belongs to a later pass.

The classification must cover the current Stripe, Firebase, R2 metadata,
checkout, community publish, refund, saved-card, account deletion, unfinished
account cleanup, support/admin, notification, and platform-notice surfaces where
they materially interact with database state.

### 2.2 Provider Mutations Use Durable Local Identity

A provider mutation that can create or change durable provider state must not
depend only on uncommitted local rows for identity, idempotency, or recovery.

Before such a provider call, the application must have either:

- a committed local checkpoint containing the durable identity needed to recover
  or resume the operation; or
- a stable idempotency identity derived entirely from already durable local
  state, with an explicit explanation of why no new checkpoint is required.

The application must not call a provider mutation after flushing new local rows
while those rows remain uncommitted when the provider response, timeout, or
provider-created object would need those rows to exist for recovery.

### 2.3 External Outcomes Are Recorded Safely

After a provider call returns, local state must distinguish:

- provider success;
- provider-declared failure;
- dependency configuration failure;
- timeout or cancellation with unknown provider outcome;
- application/database persistence failure after the provider returned.

Known provider identifiers, status values, failure codes, and recovery metadata
must be recorded in the local model that owns the operation when they are
available. If the outcome is unknown, local state must remain recoverable and
must not imply terminal success.

### 2.4 Unknown Outcomes Are Not Blindly Replayed

Timeouts or unknown provider outcomes must not cause automatic application
replay of a provider mutation unless the current policy class explicitly allows
it and the idempotency identity survives replay.

When automatic replay is unsafe or unapproved, the workflow must return a
bounded failure or pending state that can be retried, reconciled, or repaired by
the proper later owner without duplicating provider work.

### 2.5 User-Visible Success Requires Committed Local State

The application must not tell a user, caller, admin, or downstream workflow that
a side-effecting operation succeeded until the database state needed to justify
that result is committed or otherwise durably available.

This applies to checkout creation/resume, community publish fee handling, refund
retry outcomes, saved-card state, account deletion state, notification read or
delivery state, and platform-notice state where those flows are present today.

### 2.6 Current Boundaries Stay Within This Pass

This pass must not implement the durable worker platform, final production
database topology, final provider evidence, Stripe sandbox lifecycle proof,
full payment state machine redesign, full refund/credit reconciliation program,
production dashboards, alert thresholds, or migration compatibility program.

It may create current-source transaction policies, local checkpoints, service
changes, and tests that are necessary for today's request workflows to avoid
unsafe database/provider split-brain behavior.

### 2.7 Accepted Database Foundations Remain Intact

The accepted database lifecycle and database-access foundations must continue
to hold. This pass must not weaken request rollback/close behavior, pool and
timeout behavior, application-versus-migration credential separation, query
pagination bounds, cursor safety, or database-access contracts accepted by the
previous database foundation work.

### 2.8 Gate B Outputs Remain Traceable

Gate A freezes the traceability and publication outputs for this pass so Gate B
does not invent them after implementation. The completed pass must include:

- a requirement declaration at `backend/tests/support/requirements/ws04_02a.json`;
- focused tests and a testing record under
  `backend/tests/workflows/transaction_boundary_external_side_effect_safety/`;
- a source-owned transaction-boundary policy or equivalent source artifact that
  names the current workflows, checkpoints, provider-operation classes, timeout
  behavior, and downstream owners;
- an execution-register update that records the accepted `WS04-02` Stage 0
  decomposition, marks `WS04-02A` accepted when the pass merges, and leaves
  `WS04-02B` then `WS04-02C` as remaining current children.

The requirement declaration must use these stable requirement IDs. All eight are
`required` for this pass; later-owned work may appear only as a recorded gap or
downstream owner, not as a substitute for these current-source requirements.

| Requirement ID | State | Source controls | Required source truth |
|---|---|---|---|
| `WS04-02A-R1` | `required` | `DB-004`, `DB-005`, `DB-006`, `WS04-02` | Every material current side-effecting workflow is inventoried with its local unit of work, external effect, checkpoint, timeout behavior, and downstream owner. |
| `WS04-02A-R2` | `required` | `DB-004`, `DB-005`, `DB-006`, `PAY-002` | Provider mutations that need local recovery use a committed checkpoint or already durable idempotency identity before the provider call. |
| `WS04-02A-R3` | `required` | `DB-004`, `DB-006`, `DB-008`, `WS02-04C2` | Checkout provider creation, re-entry, and confirmation preserve the accepted checkout/game serialization contract and prevent duplicate create or confirm decisions. |
| `WS04-02A-R4` | `required` | `DB-004`, `DB-006`, `WS02-04C2`, `WS05` | Timeout or unknown provider outcomes do not produce blind automatic replay or ordinary success without durable local state. |
| `WS04-02A-R5` | `required` | `DB-004`, `DB-006`, `PAY-009`, `PAY-010`, `PAY-012`, `ADM-011`, `ADM-016` | Provider success, failure, timeout, and post-provider local persistence failures are recorded or surfaced through honest recoverable states. |
| `WS04-02A-R6` | `required` | `DB-004`, `DB-005`, `EN-02`, `WS03-04` | Current user-visible, admin-visible, notification, platform-notice, and support effects are tied to committed local state. |
| `WS04-02A-R7` | `required` | `DB-005`, `DB-006`, `WS02-04C2`, `WS05` | Existing provider retry classifications and durable-work handoffs remain consistent with the new transaction-boundary policy. |
| `WS04-02A-R8` | `required` | `DB-001`, `DB-002`, `DB-003`, `DB-012`, `DB-013`, `DB-015`, `WS04-01A`, `WS04-01B`, `WS04-01C` | Accepted database lifecycle, timeout, rollback, pool, role, and query-access foundations remain intact. |

## 3. Design

The design makes transaction boundaries explicit before changing workflow
behavior. Current provider and retry classifications remain the starting point,
but the pass adds the missing database checkpoint and outcome-recording
semantics that make those classifications executable.

### 3.1 Add A Transaction Boundary Registry

Introduce a small source-owned registry for transaction boundary policy. The
registry should describe current workflows at the level needed to enforce and
test the pass requirements:

- workflow identifier and service function;
- database unit of work;
- external operation category;
- provider retry policy reference when the effect is a provider operation;
- required pre-effect checkpoint;
- required post-effect recording;
- timeout and unknown-outcome behavior;
- current recovery path;
- downstream owner when a later pass owns full durable processing.

The registry should reuse the existing provider retry policy classes where they
already describe provider operation safety. It should not create a generic
retry decorator, enqueue work, configure provider retry counts, or invent
worker settings.

The registry is allowed to say that a workflow's final durable execution belongs
elsewhere, but only after it records what is safe and unsafe in the current
request path.

### 3.2 Classify The Current Side-Effecting Surfaces

The implementation should classify the current source surfaces that materially
combine database state with external or externally visible effects:

- checkout payment-intent creation, pending checkout resume, credit-covered
  checkout, and stale pending checkout expiry;
- paid waitlist auto-promotion payment-intent creation, confirmation,
  processing, failure recording, and notification-state handling;
- community-game publish fee creation, confirmation, failure, and publish
  outcome recording;
- payment event and Stripe webhook ingestion;
- late successful checkout payment refund creation from webhook or payment
  repair paths;
- admin refund retry and refund/provider reconciliation entry points;
- official-game cancellation and player-removal refund creation;
- saved payment method customer creation, setup intent creation, setup sync,
  default-card update, and detach;
- Firebase self-service account deletion, admin user deletion, and unfinished
  sign-up cleanup paths, including `cleanup_unfinished_account_workflow` /
  `DELETE /auth/unfinished-account`;
- R2 metadata reads and venue-image state paths that rely on provider-object
  existence;
- support flags, admin actions, notifications, platform notices, and inbox state
  where local commits create user-visible operational effects.

Provider reads may be classified separately from provider mutations. Pure local
database updates with no external effect may be out of scope for this child, but
they should remain available as inputs to later invariant and concurrency work.

The inventory must reconcile every current provider-operation key and durable
work handoff in `backend/services/provider_retry_policy.py`. If the source
contains a material provider mutation or user-visible side effect not listed
above, Gate B must classify it rather than silently exclude it.

### 3.3 Commit Recoverable Checkpoints Before Risky Provider Mutations

Where current source creates or mutates provider state using freshly built local
rows, the safe shape is:

1. validate inputs and lock the local rows needed to decide the operation;
2. create or update the local operation rows in a pending or prepared state;
3. commit the local checkpoint;
4. call the provider mutation with a stable idempotency key derived from that
   committed checkpoint;
5. reopen a short database transaction, lock the operation rows, and record the
   provider result;
6. commit the recorded result before returning success.

This shape is required for current workflows where a provider object needs a
local booking, payment, publish attempt, refund, admin action, or comparable
operation row to exist for recovery.

Checkout payment-intent creation and community publish fee creation currently
stage local rows before calling Stripe. They should be refactored so the local
pending rows exist durably before Stripe can create the external object. A
provider timeout then leaves a recoverable pending local operation with a stable
idempotency key instead of rolling back the only local identity for a possible
provider object.

Checkout must also preserve the accepted `WS02-04C2` re-entry contract. After a
Stripe PaymentIntent is created for checkout, the local checkpoint must contain
the booking, pending participants or capacity hold, payment row, payment
idempotency, returned provider PaymentIntent ID, and reserved game-credit state
before confirmation is attempted. Re-entry must reacquire checkout/game
serialization, re-read provider state, and make the confirm-or-fail decision
while that serialization is owned, unless Gate A is revised to approve an
equivalent serialization mechanism. A duplicate request must not decide from a
stale pre-lock view, create a second PaymentIntent, reserve credit twice, or
confirm after local state can no longer support the checkout.

Refund retry should persist the admin action or retry intent before calling
Stripe when that action is the local identity for the external retry. The later
result-recording transaction should update the refund, payment, issue, event,
and admin-action metadata consistently.

If a current provider mutation already uses only durable existing local state
and has a stable idempotency identity, the registry may classify it as not
requiring a new pre-call checkpoint. That classification must be backed by
source evidence and tests.

### 3.4 Keep Transactions Short Around External Work

Provider calls, network reads, and user-visible fanout generally must not happen
while a database transaction is holding locks that are only needed to make the
local decision.

When a workflow needs to lock rows to decide eligibility, capacity, payment
ownership, refundability, or status, the implementation should release that
transaction before the external call unless the call is only a safe local helper
and no network/provider/user-visible effect occurs.

Checkout has a narrower accepted serialization requirement that must not be
weakened by the general short-transaction rule. For the post-checkpoint checkout
resume/confirmation decision, Gate B must keep checkout/game serialization owned
while it re-reads provider state and decides whether confirmation is still valid,
or it must route back to Gate A with an equivalent concurrency design and proof
plan. The safe target is not simply "no provider work while any lock is held";
it is "no unsafe provider work while preserving the serialization that prevents
competing checkout create or confirm decisions."

After the provider call, the workflow should use a short recording transaction.
That transaction should lock only the rows needed to record the outcome and
should tolerate the row already reaching a terminal state through a valid
concurrent path.

### 3.5 Preserve Existing No-Blind-Replay Policy

The existing provider retry policy remains the source for retry-safety classes.
This pass should extend or connect that policy to database checkpoint rules, not
replace it.

Provider mutations with unknown outcomes must remain no-automatic-retry unless
the policy explicitly permits replay with stable idempotency. Existing
DependencyMutationTimeoutUnknownError and PublicTimeoutError behavior should be
preserved where it communicates that the provider outcome is unknown.

### 3.6 Make Local Failure States Honest

A local failure after a provider call returned must not erase the fact that the
provider may have changed state. The affected workflow should retain or create
enough local information to support a later safe retry, reconciliation, support
flag, money issue, or admin repair path.

For non-provider validation and configuration failures, rollback remains
appropriate when no provider mutation occurred and no user-visible success was
returned.

### 3.7 Keep Later Owners Clear

This pass may update current request workflows so their database/provider
boundary is safe, but it must not build the general durable job engine. Durable
job claim/lease semantics, worker execution, crash recovery, retry exhaustion,
dead-letter behavior, and deployed-worker proof remain later work.

This pass may also preserve payment/refund/credit recovery handoffs, but it
must not redesign the full payment state machines or claim Stripe sandbox
lifecycle coverage. The current database boundary should be good enough for
those later passes to consume.

The unfinished-account cleanup path is a current Firebase mutation boundary that
belongs in this pass's inventory. It hard-deletes an incomplete local user row,
calls Firebase user deletion, and then commits; if Firebase succeeds but the
database commit fails, the source records a support-follow-up partial failure.
Gate B must classify and prove that exact current behavior, including Firebase
configuration failure, timeout or unknown outcome, provider success plus local
commit failure, duplicate or retry behavior, and the support/repair state. The
provider retry policy must name this caller under the Firebase user deletion
classification, or the transaction-boundary registry must explicitly justify why
the existing account-deletion classification already covers it.

### 3.8 Gate B Editable Scope And Validation Contract

Gate B may update production source only where needed to satisfy this plan's
current transaction-boundary requirements. The expected editable set is:

- `backend/services/checkout_service.py`;
- `backend/services/community_game_publish_service.py`;
- `backend/services/admin_money_refund_service.py`;
- `backend/services/auth_account_service.py`;
- `backend/services/provider_retry_policy.py`;
- one new or updated source-owned transaction-boundary policy module under
  `backend/services/`;
- focused tests under
  `backend/tests/workflows/transaction_boundary_external_side_effect_safety/`;
- `backend/tests/support/requirements/ws04_02a.json`;
- `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`;
- the pass `TESTING_RECORD.md` under the focused test directory.

If implementation proves another source file is required for the same frozen
requirements, Gate B may include it only with an explicit changed-file
justification tied to one of `WS04-02A-R1` through `WS04-02A-R8`. If the needed
change alters requirements, design, proof strategy, downstream ownership, or
child boundaries, route to Gate A or Stage 0 instead of expanding silently.

Minimum validation must include:

- focused pytest coverage for the new transaction-boundary tests;
- the affected provider timeout/retry and database lifecycle compatibility
  scopes;
- repository requirement/checker validation for the focused scope;
- a `TESTING_RECORD.md` that records selected scenarios, failure
  transformations, side effects, and remaining later-owned gaps without
  claiming final provider, worker, migration, or production-infrastructure
  proof.

When this pass merges, the execution register must record the accepted
`WS04-02` intake, the three-child decomposition, accepted `WS04-02A`, remaining
`WS04-02B` and `WS04-02C`, and the fact that `WS04-02` parent completion waits
for those remaining children.

## 4. Failures And Edge Cases

1. **Provider object may exist but local rows were rolled back**
   - **Condition:** A provider mutation is called using identities from newly
     flushed local rows that are not committed, and the call times out or the
     subsequent database commit fails.
   - **Required behavior:** The workflow must be refactored to commit a
     recoverable local checkpoint before the provider call or prove that the
     mutation does not need that checkpoint.

2. **Provider call happens while locks are held**
   - **Condition:** A workflow holds row locks for eligibility, capacity, refund,
     payment, or status decisions while performing a network/provider mutation.
   - **Required behavior:** Release ordinary decision locks before the provider
     call and record the provider result in a separate short transaction unless
     a reviewed exception is required for safety. The checkout
     post-checkpoint resume/confirmation path must preserve the accepted
     checkout/game serialization contract, including provider re-read and
     confirm-or-fail decision while serialization is owned, or route back to
     Gate A for an equivalent design.

3. **Timeout outcome is unknown**
   - **Condition:** A provider mutation raises a timeout or unknown-outcome
     exception.
   - **Required behavior:** Do not mark the operation succeeded, do not blindly
     replay the provider mutation, and leave a durable pending or repairable
     state when local recovery is required.

4. **Provider success is returned but local recording fails**
   - **Condition:** The provider returns an identifier or terminal status, but
     the database update that records it fails.
   - **Required behavior:** Preserve or surface a recovery path that does not
     deny the possible provider-side effect. Do not return ordinary success
     unless the local record is durable.

5. **Duplicate request reaches the same operation**
   - **Condition:** The same checkout, publish, refund retry, saved-card, or
     notification operation is attempted again after a pending or unknown state.
   - **Required behavior:** Use the stable local identity and idempotency policy
     to resume, reconcile, return the current state, or fail safely without
     creating duplicate provider work.

6. **External failure has no local effect**
   - **Condition:** A provider configuration error, validation error, or safe
     read failure happens before a provider mutation.
   - **Required behavior:** Roll back any unneeded local work and return the
     existing bounded error behavior.

7. **User-visible success outruns persistence**
   - **Condition:** A response, notification, admin action, platform notice, or
     similar visible result claims success before the local state justifying it
     is committed.
   - **Required behavior:** Commit the local state first, or return a pending or
     failure state that does not overclaim success.

8. **Later durable-worker work is pulled forward**
   - **Condition:** A boundary issue appears to require queues, worker leases,
     retry schedules, or deployed-worker evidence.
   - **Required behavior:** Fix only the current request transaction boundary
     needed for safety. Leave full durable-worker behavior to its assigned later
     pass unless the current workflow cannot be made safe without it.

9. **Final infrastructure facts are requested**
   - **Condition:** A transaction-boundary proof asks for final production
     provider capacity, deployed process count, concrete production roles, or
     final topology evidence.
   - **Required behavior:** Treat those as outside this pass. Current local and
     PostgreSQL tests can prove the source contract without final
     infrastructure.

## 5. Testing

Testing must prove that the current source has explicit, enforceable
transaction and side-effect boundaries. It should combine source-policy checks,
focused service tests, and PostgreSQL-backed tests where committed local state
and independent sessions matter.

### 5.1 Policy And Inventory Tests

Tests should verify that every current provider operation and material
side-effecting workflow is present in the transaction boundary registry and has
the required checkpoint, post-effect recording, timeout, retry, and downstream
owner fields.

The tests should also verify that the transaction boundary registry remains
consistent with the provider retry policy: provider operation names, workflow
contexts, retry-safety classes, idempotency-key use, unknown-outcome behavior,
and later durable-work ownership must not drift apart.

### 5.2 Checkout And Community Publish Boundary Tests

Focused tests should prove that checkout payment-intent creation and community
publish fee creation commit their local pending checkpoint before Stripe can
create or confirm a provider object.

Checkout tests must also prove the accepted re-entry behavior: after provider
creation succeeds, confirmation decisions reacquire checkout/game serialization,
re-read provider state, do not use a stale pre-lock view, do not create a second
PaymentIntent, do not reserve credits twice, and do not confirm after local
state can no longer support the checkout.

Timeout tests should prove that a timeout leaves recoverable local state, uses
the stable idempotency identity, does not confirm a payment after a failed
create boundary, and does not return a user-visible success state.

Success tests should prove that provider identifiers and current statuses are
recorded before an ordinary success or resume response is returned.

### 5.3 Waitlist, Refund, And Admin-Money Boundary Tests

Tests should prove that admin refund retry has a durable local retry identity
before calling Stripe and that duplicate retry attempts with the same
idempotency identity do not create duplicate local work.

Timeout and provider-failure tests should prove that the result remains
recoverable or safely bounded and that local refund/payment/admin-action state
does not claim a provider success that was not recorded.

Paid waitlist auto-promotion tests must cover Stripe creation, confirmation,
failure, timeout or unknown-outcome handling, and local notification state.
Late successful checkout payment refund tests must prove that refund creation is
classified, bounded by stable local identity, and routed to the correct later
reconciliation owner when full provider lifecycle proof belongs to `WS05`.

### 5.4 Saved-Card And Account-Deletion Boundary Tests

Tests should preserve the accepted saved-card and account-deletion timeout
behavior while adding database-boundary expectations where needed:

- stable existing user identity for Stripe customer creation;
- no saved-card local state created when provider reads fail;
- default-card and detach operations do not return local success until local
  state matches the intended provider-visible outcome;
- Firebase account deletion keeps the local pending-deletion/support-follow-up
  behavior for unknown outcomes;
- unfinished-account Firebase cleanup classifies `DELETE /auth/unfinished-account`
  and proves config failure, timeout or unknown outcome, provider success plus
  local commit failure, duplicate or retry handling, and support-follow-up state.

### 5.5 Notification, Platform Notice, Support, And Admin Visibility Tests

Tests should verify that local user-visible or admin-visible effects are not
emitted before their owning database state commits. Where the current effect is
purely local database state, tests should prove the committed row is the visible
source of truth.

Future external notification delivery remains later work, but the current
source must not claim that external delivery already happened if only local
notification rows were created.

### 5.6 Compatibility Tests

The pass should rerun the focused compatibility scopes that protect the
database foundation and provider timeout assumptions touched by this work:

- accepted request-session rollback/close and database timeout behavior;
- provider timeout and retry classification;
- side-effect ordering tests updated for the new checkpoint behavior;
- requirement/checker validation for the focused scope and suite policy.

Local tests prove source behavior and deterministic database boundaries. They
do not prove Stripe sandbox behavior, final provider runtime behavior, deployed
worker behavior, or final production infrastructure.

### 5.7 Requirement, Evidence, And Register Checks

Validation must prove that `backend/tests/support/requirements/ws04_02a.json`
contains exactly `WS04-02A-R1` through `WS04-02A-R8`, that each required
requirement has focused pytest evidence or an explicit later-owned disposition,
and that the testing record describes the side effects and gaps truthfully.

Gate B must also verify that the execution-register update matches the accepted
Stage 0 split: `WS04-02A` accepted when this pass merges, `WS04-02B` next, and
`WS04-02C` after `WS04-02B`.

## 6. Done When

- [ ] Current side-effecting workflows have an explicit transaction boundary
      policy and no material current workflow is omitted.
- [ ] Provider mutations that require local recovery use a committed local
      checkpoint or an already durable stable idempotency identity before the
      provider call.
- [ ] Checkout payment-intent creation and community publish fee creation no
      longer rely on uncommitted local rows as the only recovery identity for
      possible Stripe-created objects.
- [ ] Checkout re-entry and confirmation preserve the accepted checkout/game
      serialization contract or route back to Gate A for an approved equivalent
      design.
- [ ] Paid waitlist auto-promotion and late successful checkout payment refund
      paths are inventoried, classified, tested, and routed to the correct
      current or later owner.
- [ ] Unfinished-account Firebase cleanup is inventoried, classified, tested,
      and reconciled with the provider retry policy or an explicit registry
      disposition.
- [ ] Admin refund retry persists the local retry identity needed for safe
      provider-outcome recovery before calling Stripe.
- [ ] Unknown provider outcomes do not create blind automatic replay or ordinary
      success responses.
- [ ] Provider success is recorded durably before the application returns
      ordinary success for the side-effecting operation.
- [ ] User-visible notification, platform-notice, support/admin, and local
      operational effects are tied to committed local state.
- [ ] The current boundary remains compatible with accepted database lifecycle,
      timeout, and retry-policy behavior.
- [ ] Later durable jobs, payment lifecycle redesign, provider sandbox proof,
      final infrastructure verification, migration compatibility, and
      observability/alerting work remain clearly outside this pass.
- [ ] Focused current tests prove the policy inventory, provider-checkpoint
      ordering, timeout/unknown-outcome behavior, duplicate/idempotent behavior,
      and compatibility assumptions.
- [ ] Requirement declaration, testing record, changed-file justification, and
      execution-register update are complete for `WS04-02A` without claiming
      `WS04-02B`, `WS04-02C`, final provider proof, or durable-worker proof.
