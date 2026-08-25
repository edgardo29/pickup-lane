# WS04-02B - Database-Enforced Invariants, Locks, And Deterministic Concurrency

This pass makes Pickup Lane's current roster, capacity, waitlist, and financial
database invariants deterministic under concurrent PostgreSQL sessions.

## 1. What This Work Does

This section defines the engineering result of the pass. It matters because
game capacity, waitlist promotion, payment, refund, credit, and money-issue
rules are only production-ready when simultaneous requests cannot make the
database accept two incompatible truths.

The completed pass protects the current application database surface with the
lowest reliable mechanism for each invariant:

- PostgreSQL constraints and unique indexes for single-row, duplicate, and
  idempotency invariants;
- row-level locks and ordered state transitions for aggregate invariants such
  as roster capacity, waitlist position, booking state, refund state, and credit
  balances;
- explicit service policy for lock ownership, loser outcomes, contention
  behavior, and later owners;
- deterministic tests that use independent database sessions and assert final
  persisted state after concurrent attempts complete.

This pass builds on the accepted WS04-02A transaction-boundary work.

WS04-02A remains authoritative for:

- external-provider operation classification;
- pre-provider durable checkpoints;
- provider retry classification;
- provider timeout and unknown-outcome behavior;
- post-provider recovery behavior;
- downstream ownership of full provider reconciliation.

WS04-02B owns:

- database invariants;
- database constraints and uniqueness;
- database serialization points;
- row-lock ownership and ordering;
- concurrent winner/loser database behavior;
- deterministic database concurrency proof.

WS04-02B must reference the accepted WS04-02A transaction-boundary contract
where the two surfaces meet. It must not create a second competing definition
of provider retry, checkpoint, or recovery behavior.

This pass does not select production infrastructure, assume Neon/Render/Vercel
are final production providers, create a durable worker system, redesign Stripe
reconciliation, or complete the value/default/SQL-safety work assigned to
WS04-02C.

## 2. Required System Behavior

This section states what must be true when the pass is complete. The
requirements are scoped to current database invariants and current source
workflows. Later provider, worker, migration-rehearsal, and operational proof
remain with their assigned passes.

### 2.1 Current Invariants Are Cataloged

The backend must contain a compact database-invariant policy that names the
current invariants this pass protects.

The policy must cover:

- game, booking, participant, waitlist, host guest, player guest, roster count,
  capacity status, and waitlist-promotion invariants;
- payment, refund, host publish fee, game credit, credit usage, money issue,
  provider-identity, and idempotency invariants;
- the table, row family, or workflow that owns each invariant;
- one authoritative enforcement disposition for each invariant;
- every mechanism that forms that disposition when the invariant deliberately
  relies on more than one mechanism;
- the expected concurrent loser behavior;
- any downstream owner when broader lifecycle work belongs to another pass.

An enforcement disposition may use:

- PostgreSQL constraint;
- unique index;
- row lock;
- ordered service transition;
- idempotency key;
- or an intentional combination of these.

For example, a capacity invariant may correctly require both a game-row lock
for the aggregate decision and a database unique index for duplicate
participant protection. The policy must record that combined disposition rather
than pretending only one mechanism exists.

The policy must be deterministic and free of database, provider, network, and
framework side effects. It is a current-source contract and test target, not a
new runtime policy engine.

### 2.2 Capacity And Roster Decisions Serialize On Database Rows

Every current workflow that decides, consumes, frees, reserves, or refills game
capacity must hold a PostgreSQL serialization point before reading roster
counts, waitlist positions, or active relationship rows and before making the
corresponding database decision.

For the current source, the shared serialization point is the `Game` row lock
unless an already accepted workflow has an equivalent stricter serialization
mechanism.

This applies to:

- community player join;
- player guest add;
- host guest add;
- player leave;
- guest removal;
- account-deletion roster cancellation;
- waitlist promotion;
- capacity status updates coupled to those operations.

The community workflows must acquire the game serialization point before
deciding from:

- current occupied capacity;
- pending-payment capacity holds;
- active waitlist membership;
- next waitlist position;
- next roster order;
- whether a party fits;
- whether a newly freed spot may be promoted.

Official checkout, official roster administration, official player removal,
and official cancellation already use row locking in current source. This pass
must preserve and prove those accepted serialization contracts rather than
adding a second competing mechanism.

### 2.3 Paid Waitlist Promotion Uses A Durable Capacity Hold Across Provider Work

Paid waitlist auto-promotion crosses the WS04-02B database-concurrency boundary
and the WS04-02A provider boundary.

The required design is:

1. Acquire the game-row serialization point.
2. Re-read current capacity and the candidate waitlist state while serialized.
3. Confirm that the full waitlist party fits.
4. Transition the booking, participants, waitlist entry, and payment into the
   current pending/payment-processing state that owns that capacity.
5. Persist and commit that local checkpoint before the provider mutation as
   required by WS04-02A.
6. The committed pending-payment participant/booking state must count as a
   capacity hold so another transaction cannot consume the same spots while
   provider work is in progress.
7. Release the database transaction before the external provider call. Do not
   hold a PostgreSQL row lock across Stripe network work.
8. Record provider identity/result according to WS04-02A.
9. Before making another capacity decision, finalizing a capacity-sensitive
   local transition, evaluating the next waitlist candidate, or updating final
   capacity status, reacquire the game-row serialization point.
10. Re-read the current persisted roster/capacity state after reacquiring the
    lock. Do not continue from an `available_spots` value calculated before a
    commit/provider boundary.
11. Only then make the next promotion/capacity decision.

`promote_waitlist_entries` remains the owner of waitlist promotion mechanics
and must defensively preserve this contract.

It must not rely only on a caller having acquired a lock that an internal commit
can release.

For free/non-provider promotion paths, the promotion decision and corresponding
capacity updates may stay in one serialized transaction.

For paid promotion paths, every commit boundary that releases the game lock
requires the game serialization point to be reacquired and capacity to be
recomputed before another capacity-sensitive decision.

### 2.4 Waitlist Promotion Preserves Party And Position Rules

Waitlist promotion must:

- use current active waitlist candidate status rules;
- preserve waitlist position order;
- never split a party across confirmed and waitlisted states;
- promote only when the complete party fits current available capacity;
- preserve committed pending-payment holds while paid promotion is processing;
- update booking, participant, waitlist, payment, notification, and capacity
  status rows consistently with the current path;
- recompute current capacity after any transaction boundary that could allow
  another transaction to change capacity;
- leave paid waitlist provider lifecycle, retry, timeout, and recovery behavior
  under the accepted WS04-02A contract and later WS05 ownership.

### 2.5 Database Lock Ordering Is Deterministic

WS04-02B must establish a deterministic lock order for the database rows that
participate in roster/capacity mutations.

The normal capacity-mutation order is:

1. owning `Game` row;
2. affected `Booking` rows;
3. affected `WaitlistEntry` rows;
4. affected `GameParticipant` rows;
5. financial/support rows only when the current workflow genuinely requires
   them.

Within a row family, acquire multiple rows in deterministic stable order,
preferably primary-key ascending unless current source already has a stricter
accepted order.

A workflow must not acquire dependent booking/participant/waitlist locks and
then later acquire the owning game lock when another current path acquires
those rows in the reverse order.

#### Account deletion

Account deletion can affect more than one future game and therefore needs an
explicit multi-game rule.

The account-deletion roster cleanup path must:

1. preserve its existing user/admin-account protection;
2. identify the candidate affected game IDs without first creating a conflicting
   dependent-row lock order;
3. acquire all affected `Game` rows in deterministic `Game.id` order;
4. after those game locks are owned, re-read the relevant active
   booking/participant/waitlist state;
5. acquire and mutate dependent rows under the same game-first ordering;
6. process affected games in deterministic game-ID order;
7. perform waitlist promotion/capacity reconciliation under the corresponding
   game serialization point.

If source inspection proves a different existing lock order is already required
for a specific accepted invariant, Gate B may preserve it only if the resulting
combined ordering is shown to be deadlock-safe.

Gate B must not introduce `Game -> dependent row` in one path and
`dependent row -> Game` in another.

### 2.6 Duplicate And Active-Relationship Rules Stay Database-Enforced

PostgreSQL must remain the final enforcement layer for duplicate active
relationships and provider/idempotency identities that can be represented as
single-table constraints or unique indexes.

Current enforcement must include:

- no duplicate active registered participant for the same user and game across
  active roster or waitlist participant statuses;
- no duplicate active waitlist entry for the same user and game;
- no duplicate active waitlist position for a game;
- payment idempotency key uniqueness;
- payment provider PaymentIntent and charge identity uniqueness when present;
- refund provider refund identity uniqueness when present;
- refund-event provider event and idempotency uniqueness when present;
- game-credit and game-credit-usage idempotency uniqueness;
- money-issue operation-key uniqueness;
- existing admin/support/platform-notice idempotency constraints that interact
  with the financial or operational database state protected by this pass.

Service code may provide clearer errors, but it must not be the sole mechanism
preventing these duplicate states.

### 2.7 Financial Database Invariant Dispositions Are Frozen

The financial portion of WS04-02B is not an open-ended Gate B discovery task.

Gate A freezes the following disposition by financial family.

| Financial family | Current enforcement disposition | Gate B action |
|---|---|---|
| Game-credit grants and available balance | Ordered `FOR UPDATE` locking of available credit grants plus persisted credit/usage state | Prove concurrent reservation cannot overdraw a grant. Preserve current ordering. Add only a narrow correction if deterministic proof exposes an actual gap. |
| Game-credit redemption/release/restoration/reversal | Locked credit/usage rows, usage status transitions, idempotency identities, and persisted ledger state | Prove no double restore, reverse, redeem, or lost ledger update. Narrow correction only if proof fails. |
| Payment identities | PostgreSQL uniqueness for payment idempotency/provider identities plus workflow-specific state serialization already present in accepted payment/checkout paths | Prove duplicate identities remain database-enforced. Do not redesign payment lifecycle. |
| Refund and refund-event identities | PostgreSQL uniqueness/idempotency plus current state-gated refund/admin workflows | Prove duplicate refund/provider/event identities and concurrent state mutation are bounded. Do not implement broader reconciliation. |
| Host publish fee | Existing persisted fee/outcome identity and ordered current publish/payment transitions | Prove current database invariant and duplicate behavior. No broader publish/payment redesign. |
| Money issues and admin financial repair | Operation-key/idempotency protection plus current row/state gating in admin money workflows | Prove concurrent duplicate repair/reconciliation requests cannot create incompatible persisted outcomes. |
| Admin/support records tied to financial operations | Existing idempotency/operation identity and current state transitions | Prove only the portions participating in financial invariant correctness. Do not broaden into general admin-system redesign. |

The planned Gate B financial work is therefore primarily:

- catalog current enforcement;
- prove it with deterministic current-database tests;
- preserve existing working locks/constraints/idempotency;
- make only narrow corrections where a required WS04-02B invariant demonstrably
  fails.

If implementation discovers that a financial invariant requires a substantial
new state machine, provider-reconciliation design, durable job model, or
material redesign not represented by this frozen plan, route back to Gate A or
the later owner instead of inventing that design in Gate B.

Stripe provider lifecycle, webhook authority, durable execution, deployed
worker behavior, and full financial reconciliation remain with WS05.

### 2.8 Lock, Timeout, Deadlock, And Unknown-Outcome Behavior Is Explicit

The current database invariant paths must have explicit behavior for contention
and database failure classes.

The default shape is:

- use PostgreSQL row locks for aggregate decisions;
- use database uniqueness for duplicate states that can be expressed as
  constraints/indexes;
- follow the deterministic lock order defined by this pass;
- keep database transactions short;
- do not hold database locks across external provider network work;
- preserve WS04-02A durable checkpoint behavior around provider calls;
- after a provider/checkpoint commit boundary, reacquire required database
  serialization before another database aggregate decision;
- respect accepted statement and lock timeout configuration;
- do not use process-local locks as production correctness mechanisms;
- do not add automatic whole-transaction retries unless the operation is
  explicitly idempotent and safe;
- map ordinary concurrent losers to existing HTTP/domain conflicts or bounded
  validation results where appropriate;
- surface deadlock, lock timeout, serialization, or unknown-commit outcomes as
  bounded failures unless an existing accepted idempotent recovery path applies.

WS04-02B must not redefine provider unknown-outcome behavior already owned by
WS04-02A.

### 2.9 Independent-Session Tests Prove Final Database State

Concurrency evidence must use separate SQLAlchemy sessions or database
connections.

It must not simulate concurrency by:

- making sequential calls through one session;
- using only mocks;
- using a process-local mutex as the correctness mechanism.

The tests must coordinate contending operations with barriers or an equivalent
deterministic harness and then assert final persisted state from a fresh
database session.

The evidence must cover representative winner/loser cases for:

- two users competing for the final roster spot;
- competing player or host guest additions when only part of the requested
  capacity remains;
- capacity-freeing operations that trigger waitlist promotion;
- paid waitlist promotion across its committed pending-payment/provider boundary;
- recomputation of capacity after a paid-promotion transaction boundary;
- account-deletion roster cancellation followed by waitlist promotion;
- deterministic multi-game account-deletion lock ordering;
- duplicate active participant or waitlist relationships;
- duplicate payment, refund, credit, usage, money-issue, and provider identities
  where current database constraints own the invariant;
- concurrent game-credit reservation;
- concurrent game-credit release/restoration/reversal;
- bounded database lock/conflict behavior where current source exposes reliable
  handling.

Tests must assert both:

1. immediate winner/loser behavior; and
2. final persisted database state after all concurrent transactions finish.

Tests must not read from or rely on `backend/tests/legacy/`.

### 2.10 Accepted Foundations And Later Boundaries Remain Intact

The pass must preserve accepted WS04-01 database foundations and the accepted
WS04-02A transaction-boundary contract.

It must not weaken:

- request rollback;
- session close;
- pool and timeout behavior;
- application-versus-migration credential separation;
- query pagination bounds;
- cursor safety;
- side-effect checkpoint behavior;
- provider timeout/unknown-outcome behavior accepted in WS04-02A;
- accepted checkout serialization.

The pass must not claim:

- final production database topology;
- numeric production connection budget;
- concrete final-production roles/grants;
- final provider runtime proof;
- durable worker behavior;
- full Stripe reconciliation;
- schema migration compatibility/rehearsal;
- production dashboarding;
- alert thresholds;
- operational recovery evidence.

## 3. Implementation Design

This section describes the intended code shape.

Gate B may modify any file genuinely required to implement and prove this
frozen design, but every changed file must be justified by a current invariant
or its evidence.

### 3.1 Add A Database-Invariant Policy

Add a focused source-owned service policy module for current database
invariants.

The module should use the lightweight style of the accepted transaction-boundary
policy:

- plain data structures;
- finite entries;
- no route imports;
- no database session use;
- no provider calls;
- no runtime orchestration.

Each entry should name:

- invariant ID/name;
- current owner table/row family/workflow;
- authoritative enforcement disposition;
- every mechanism in that disposition;
- serialization owner when applicable;
- expected contention/loser result;
- related WS04-02A transaction-boundary entry when provider work is involved;
- later owner when a broader lifecycle belongs to another pass.

Every invariant must have exactly one authoritative **disposition entry** in the
B policy.

That disposition may deliberately name multiple enforcement mechanisms.

The B policy must not duplicate WS04-02A provider:

- operation classes;
- checkpoint rules;
- retry classifications;
- timeout/unknown-outcome semantics;
- recovery-path definitions.

Where those facts matter, the B policy references the corresponding accepted
A contract.

### 3.2 Add One Shared Game Serialization Helper

Add a focused game-domain database helper that loads a non-deleted `Game` row
with `SELECT ... FOR UPDATE` and preserves the existing not-found behavior.

Use that helper wherever a current community roster workflow makes a capacity,
waitlist, or promotion decision:

- `join_game_roster_workflow`;
- `leave_game_roster_workflow`;
- `add_booking_game_guests_workflow`;
- `add_host_game_guests_workflow`;
- `remove_game_guests_workflow`;
- account-deletion roster cleanup;
- waitlist promotion.

The helper belongs with existing game database/service helpers.

It must not:

- create a repository abstraction layer;
- hide product authorization;
- replace existing validation;
- perform provider work;
- introduce process-local locking.

### 3.3 Make Waitlist Promotion Self-Consistent Across Commit Boundaries

`promote_waitlist_entries` remains the owner of promotion mechanics.

It must ensure the game serialization point is held before each
capacity-sensitive decision.

For free/non-provider promotion:

- lock game;
- calculate capacity;
- choose candidate;
- transition booking/participant/waitlist state;
- update capacity state;
- commit through the owning request transaction.

For paid promotion:

- lock game;
- calculate capacity;
- choose candidate;
- create the pending/payment-processing capacity hold;
- commit the checkpoint required by WS04-02A;
- call Stripe outside the game lock;
- record provider result according to WS04-02A;
- reacquire the game lock before another capacity-sensitive local decision;
- reload/recompute occupied and available capacity;
- continue only from the fresh persisted state.

A paid promotion must never return to the outer waitlist loop and continue from
an `available_spots` value captured before the checkpoint/provider transaction
boundary.

The durable pending-payment hold must remain visible to other transactions while
provider work is pending.

### 3.4 Refactor Account-Deletion Capacity Work To The Shared Lock Order

The account-deletion path currently touches multiple future games and performs
roster cancellation plus waitlist promotion.

Gate B must align it with the canonical game-first capacity lock order.

The implementation should:

1. preserve account/user/admin deletion protections;
2. discover candidate affected game IDs;
3. sort those IDs deterministically;
4. lock the affected game rows in that order;
5. re-read active roster/booking/waitlist rows after the game locks are held;
6. lock/mutate dependent rows under the same ordering;
7. reconcile booking state;
8. promote waitlist entries under the corresponding game lock;
9. update capacity state.

Do not iterate an unordered set when lock acquisition order matters.

Do not leave the current path acquiring dependent roster rows first and game
rows later if community roster paths use the reverse order.

### 3.5 Preserve Existing Official And Checkout Serialization

Official checkout, official roster administration, official cancellation, and
official player removal already contain current row-locking contracts.

Gate B must:

- preserve those locks;
- verify them against the B invariant policy;
- add focused evidence showing the current source continues to satisfy the
  accepted serialization contract.

Changing official product behavior is not part of this pass unless the proof
reveals an actual current invariant defect.

### 3.6 Prove The Frozen Financial Dispositions

Gate B must implement the financial table in section 2.7 as written.

It should not begin with an open-ended redesign/inventory exercise.

For each financial family:

1. map the frozen invariant to the exact current model/service mechanism;
2. prove the current mechanism through policy, constraint, and/or
   independent-session tests as appropriate;
3. preserve the mechanism when it succeeds;
4. add only the smallest in-scope correction if the required invariant fails;
5. route broader lifecycle redesign to the appropriate later pass.

Game-credit concurrency receives direct independent-session proof because the
current service already uses ordered grant/usage locking and its correctness
depends on concurrent database state.

Database uniqueness families may use direct PostgreSQL conflict tests where
that is the most reliable proof.

Provider lifecycle behavior itself is not re-tested as a provider integration
in this child.

### 3.7 Add Deterministic Concurrency Evidence

Add trusted backend tests under one coherent workflow scope for database
invariants, locks, and deterministic concurrency.

The tests must:

- use the dedicated PostgreSQL test database through independent sessions;
- coordinate contending operations with barriers or an equivalent deterministic
  harness;
- avoid sleep-based race assumptions where deterministic synchronization is
  possible;
- assert immediate winner/loser behavior;
- assert final persisted state from a fresh session;
- verify lock-order and reacquisition behavior where relevant;
- include policy/static tests for finite invariant coverage where direct
  concurrency would be brittle or would duplicate provider-owned behavior;
- mark tests with the WS04-02B requirement IDs they prove;
- pass the backend compliance checker for the new trusted scope.

## 4. Failure Cases And Edge Conditions

Gate B must cover or explicitly classify:

- two users competing for the last roster spot;
- one party that fits and another that no longer fits after serialization;
- player guest and host guest additions racing for the same remaining capacity;
- player leave or guest removal freeing capacity while another join competes;
- account deletion freeing capacity while another capacity mutation competes;
- multi-game account deletion and deterministic game-lock ordering;
- waitlist promotion after a capacity-freeing operation;
- waitlist parties larger than available capacity;
- paid waitlist promotion committing a durable capacity hold before Stripe;
- another transaction acting while paid waitlist provider work is in progress;
- waitlist promotion recomputing capacity after the provider/checkpoint boundary;
- active participant duplicates;
- active waitlist duplicates;
- duplicate waitlist positions;
- duplicate/replayed payment identities;
- duplicate/replayed refund identities;
- duplicate/replayed credit and credit-usage identities;
- duplicate/replayed money-issue/admin/support operation identities;
- simultaneous credit reservations that would overdraw one grant;
- simultaneous credit restoration attempts;
- simultaneous credit reversal attempts;
- lock timeout;
- deadlock;
- serialization conflict where applicable;
- integrity conflict;
- unknown commit outcome where current database code exposes it;
- cancelled games;
- full games;
- roster-locked games;
- unpublished games;
- hidden/deleted games;
- stale or already-started games.

The pass must not invent cases requiring:

- final production topology;
- deployed process/pool counts;
- provider-specific final database roles;
- final worker runtime;
- Stripe sandbox lifecycle;
- production logs.

Those remain outside WS04-02B unless later durable authority supplies the
missing external dependency.

## 5. Requirement And Evidence Plan

All requirements are required for this pass.

| Requirement ID | Source controls | Required behavior |
|---|---|---|
| `WS04-02B-R1` | `DB-007`, `DB-008`, `WS04-02` | Current roster, capacity, waitlist, and financial database invariants are cataloged with exactly one authoritative enforcement disposition per invariant. A disposition may intentionally combine constraints, unique indexes, row locks, ordered transitions, and idempotency mechanisms. |
| `WS04-02B-R2` | `DB-007`, `DB-008`, `DB-009`, `WS04-02A` | Community capacity decisions serialize on the owning PostgreSQL game row before reading or deciding from roster counts, waitlist state, active relationships, or capacity status. |
| `WS04-02B-R3` | `DB-007`, `DB-008`, `WS04-02`, `WS04-02A` | Waitlist promotion preserves full-party capacity, position order, durable pending-payment holds, and fresh capacity recomputation after any commit/provider boundary. Paid provider lifecycle remains governed by WS04-02A. |
| `WS04-02B-R4` | `DB-007`, `DB-008`, `DB-010`, `WS04-02` | Capacity-mutating workflows follow a deterministic game-first lock order, including deterministic multi-game ordering for account deletion, and do not introduce reverse-order deadlock hazards. |
| `WS04-02B-R5` | `DB-007`, `DB-009`, `WS04-02` | Active participant, active waitlist, provider identity, and idempotency duplicates remain enforced by PostgreSQL constraints or unique indexes with bounded service conflict handling. |
| `WS04-02B-R6` | `DB-005`, `DB-007`, `DB-008`, `DB-009`, `WS04-02` | Current payment, refund, host publish fee, game-credit, credit-usage, money-issue, and admin-money invariants retain their frozen database enforcement dispositions and receive only narrow corrections where deterministic proof exposes a current failure. |
| `WS04-02B-R7` | `DB-007`, `DB-008`, `DB-009`, `WS04-02` | Concurrent credit reservation, release, restoration, redemption, and reversal cannot overdraw, double-restore, double-reverse, or silently lose persisted ledger state. |
| `WS04-02B-R8` | `DB-004`, `DB-008`, `DB-010`, `WS04-02A` | Contention, integrity conflicts, lock timeouts, deadlocks, serialization conflicts, and unknown database outcomes are bounded without unsafe process locks or blind whole-transaction replay, while provider retry/unknown-outcome semantics remain owned by WS04-02A. |
| `WS04-02B-R9` | `DB-001`, `DB-002`, `DB-003`, `DB-006`, `DB-012`, `DB-013`, `DB-014`, `DB-015`, `WS04-01A`, `WS04-01B`, `WS04-01C`, `WS04-02A` | Accepted database foundations and transaction-boundary contracts remain intact, and this pass does not claim final infrastructure, provider runtime, migration rehearsal, durable jobs, or full payment/provider reconciliation. |

Gate B must add a machine-readable declaration at:

`backend/tests/support/requirements/ws04_02b.json`

and a testing record under the new trusted database-invariants workflow test
scope.

## 6. Validation Plan

Gate B must run:

- focused pytest for the new WS04-02B database-invariant/concurrency scope;
- current trusted tests directly affected by changed roster, waitlist,
  account-deletion, or financial code;
- accepted WS04-02A transaction-boundary tests that protect the checkpoint and
  provider-boundary contract;
- deterministic PostgreSQL independent-session concurrency tests;
- backend compliance checker for the new trusted test scope and requirement
  declaration;
- `git diff --check`.

The focused validation must prove at least:

- final-roster-spot winner/loser behavior;
- guest-capacity winner/loser behavior;
- waitlist promotion after capacity release;
- durable paid-waitlist capacity hold;
- post-provider-boundary capacity recomputation;
- account-deletion/game-lock ordering;
- representative PostgreSQL duplicate enforcement;
- game-credit concurrent reservation;
- game-credit restore/reversal concurrency;
- final persisted state from a fresh database session.

If a schema constraint or canonical migration changes, Gate B must also run the
database/migration validation required by the database standards and update the
canonical migration that owns the changed table.

A schema change is not the default design for this pass. Existing constraints
and deliberate database serialization should be preserved where they already
correctly enforce the invariant.

If implementing a required invariant would need a destructive/backfill-heavy
schema change not represented by this plan, route to the appropriate migration
design rather than improvising it in Gate B.

## 7. Completion Criteria

The pass is complete when:

- the current database-invariant policy names every required roster/capacity,
  waitlist, and financial invariant;
- every invariant has one authoritative enforcement disposition, including all
  mechanisms when the disposition is intentionally combined;
- the B invariant policy does not duplicate WS04-02A's provider checkpoint,
  retry, unknown-outcome, or recovery ownership;
- every current community capacity-consuming or capacity-freeing workflow
  serializes its capacity decision on the owning game row;
- paid waitlist promotion commits a durable pending-payment capacity hold before
  provider work and reacquires the game serialization point before any later
  capacity-sensitive decision;
- waitlist promotion preserves complete-party promotion, waitlist order,
  post-boundary capacity recomputation, booking/participant/waitlist/payment
  consistency, and current WS04-02A provider-boundary ownership;
- account-deletion roster cleanup follows deterministic game-first lock order,
  including multi-game ordering and waitlist/capacity reconciliation under the
  corresponding game lock;
- PostgreSQL constraints or unique indexes remain the final enforcement layer
  for active participant, active waitlist, provider-identity, and idempotency
  duplicate facts that can be represented in the database;
- the frozen financial invariant dispositions are cataloged and proved without
  broad payment, refund, provider, durable-worker, or reconciliation redesign;
- independent-session PostgreSQL tests and static policy checks prove the
  required winner/loser, duplicate, lock-order, credit, and persisted-state
  scenarios for the WS04-02B requirements;
- the WS04-02B requirement declaration and testing record are present, accurate,
  and aligned with the implemented evidence;
- the workflow-required execution-register update records the accepted state
  that will become true when WS04-02B merges, leaves WS04-02C as the remaining
  current WS04-02 child, and does not mark the WS04-02 parent complete;
- affected compatibility validation passes, including WS04-02A transaction
  boundary and accepted WS04-01 database-foundation scopes;
- `git diff --check` passes;
- no final production infrastructure, provider runtime proof, migration
  rehearsal, durable jobs, observability dashboards, alert thresholds,
  operational recovery evidence, or full Stripe reconciliation is claimed by
  this pass.
