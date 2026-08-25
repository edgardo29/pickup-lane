# WS04-02 - Transactions, invariants, locks, and deterministic concurrency intake

## 1. What Needs To Be Decided

This intake decides how to execute the remaining database transaction and
concurrency work for `WS04-02`.

The parent is not a single narrow feature. It covers transaction boundaries,
external side-effect safety, database-enforced invariants, lock and retry
behavior, deterministic concurrency proof, database value/default behavior, and
SQL/logging safety across several current backend domains. The execution shape
matters because those responsibilities have different implementation surfaces
and proof needs. Combining them into one pass would make it easy to hide gaps
between financial/provider workflows, game roster invariants, database
constraints, and query-safety checks.

## 2. What We Know

This section lists only the facts that affect whether `WS04-02` should execute
as one pass, be split, or wait on another decision. These facts matter because
they define which work can be completed from current repository authority and
which work belongs to later durable-job, payment, storage, observability, or
final-infrastructure passes.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Accepted database foundation | `WS04-01A`, `WS04-01B`, and `WS04-01C` are accepted on `develop`. The final-production facts owned by `WS04-01D` remain intentionally deferred because final hosting and database infrastructure are not selected. | `WS04-02` can use the provider-independent database foundation, but it must not require final production provider capacity, role/grant, pooler, or deployment evidence. |
| Parent authority | The master blueprint assigns `WS04-02` to database/domain/concurrency work for `DB-004`, `DB-005`, `DB-006`, `DB-007`, `DB-008`, `DB-009`, `DB-010`, and `DB-014`. It requires narrow models, constraints or deliberate serialization, deterministic independent-session tests, and an invariant catalog. | The parent is large enough that the split must preserve every control without creating artificial planning-only children. |
| Transaction and provider boundaries | Current backend source contains many database writes and explicit commits. Stripe, notification, refund, community publish, checkout, venue image, and support/admin paths include provider or user-visible side effects near database mutation paths. | External side-effect safety has a distinct implementation boundary from pure database invariants because it governs when a workflow may tell a user or provider that durable state exists. |
| Current durable-job state | The blueprint assigns durable job state, claim/lease lifecycle, worker execution, retry policy, crash recovery, and deployed-worker proof to `WS05`. Current authority does not approve generic worker concurrency numbers or a final worker runtime. | `WS04-02` should provide database transaction and invariant contracts that later jobs consume, but it must not invent a durable worker system or treat absent job claims as complete `WS05` work. |
| Game and roster invariants | Current game, booking, participant, waitlist, capacity, and host/guest flows use a mix of service checks, row locks, status transitions, and schema constraints. Current evidence does not include deterministic concurrent winner/loser proof for those invariants. | Game/roster concurrency is a coherent database result: it can add or verify database protection and prove simultaneous-session behavior without final infrastructure facts. |
| Financial invariants | Payments, refunds, host publish fees, game credits, credit usage, money issues, and admin money workflows already have some provider IDs, idempotency keys, checks, and row locks, but the remediation record still flags over-refund, over-credit, duplicate, retry, and unknown-outcome risks. | Financial database invariants must be reconciled with transaction boundaries and later `WS05` payment/reconciliation ownership; they cannot be safely treated as only a schema-cleanup task. |
| Database value/default behavior | Current models and migrations use database defaults for many timestamps, text defaults, currency fields, numeric cent amounts, status fields, and JSON defaults while services also assign some update timestamps manually. | Type/default/time/money behavior is a separate proof area from transaction locking, and it should run after the transaction/invariant changes it must verify. |
| SQL and logging safety | Source uses SQLAlchemy ORM broadly, plus explicit SQL text for database health, timeout/lock helpers, advisory-lock test support, partial indexes, and migration expressions. Prior evidence did not prove runtime SQL/log redaction or all current SQL construction boundaries. | SQL/default safety should be verified after earlier children settle their database changes so the final pass can cover the whole current database surface. |
| Later-pass consumers | `WS04-03` depends on accepted `WS04-02` source/schema contracts. `WS05-01`, `WS05-02`, `WS05-03`, `WS09-02`, and later closeout consume parts of the transaction, invariant, concurrency, and SQL-safety results. | `WS04-02` must produce enough accepted database contracts for downstream work, while explicitly leaving later payment/job/provider/runtime proof with the passes that own it. |
| Current blocker state | No final infrastructure, provider account, worker runtime, or owner threshold decision is required to begin the provider-independent `WS04-02` work. | The parent is ready to execute now, but it should be split along real engineering boundaries. |

## 3. Execution Decision

This section states the execution shape chosen for `WS04-02` and why it is the
right engineering shape. The parent should be split because the work has three
coherent results with different implementation and verification boundaries:
current transaction/side-effect safety, current domain concurrency invariants,
and final database value/SQL-safety compatibility for the settled surface.

Outcome: split the parent.

| Order | Work | Depends on |
|---|---|---|
| `1` | `WS04-02A - Transaction boundary and external-side-effect safety` | Accepted provider-independent `WS04-01` foundation |
| `2` | `WS04-02B - Database-enforced invariants, locks, and deterministic concurrency` | `WS04-02A` |
| `3` | `WS04-02C - Database value, default, and SQL-safety compatibility` | `WS04-02A`; `WS04-02B` |

`WS04-02A` is first because workflows that contact external systems or expose a
success outcome must have explicit transaction and handoff boundaries before
concurrency tests can claim durable final-state behavior. `WS04-02B` is second
because the main business invariants need the settled transaction boundary and
can then prove simultaneous database behavior directly. `WS04-02C` is last
because SQL/default/type compatibility and SQL-safety evidence should cover the
database surface after the transaction and invariant changes are in place.

Each child leaves behind an independently useful result. The first makes
current side-effecting workflows durable enough to reason about, the second
protects current concurrent domain invariants, and the third verifies the
current database surface for value/default/SQL safety after the earlier database
changes are complete.

## 4. Where The Parent Work Goes

This section accounts for the complete parent scope. Its purpose is to show
that every major `WS04-02` responsibility has exactly one destination and that
the split does not drop, duplicate, or prematurely close work that belongs to a
later owner.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Current request transaction boundaries and database unit-of-work rules | `WS04-02A` | Covers current source-owned service and route workflows; final deployed runtime observations remain later evidence. |
| External side-effect ordering around Stripe, notification, support/admin, storage-adjacent, and user-visible success paths | `WS04-02A` | Covers current repository-owned transaction and handoff safety. Full durable worker execution, Stripe sandbox lifecycle proof, and provider reconciliation remain with `WS05` where assigned. |
| Transaction and invariant catalog for current database workflows | `WS04-02A` | Serves as the source/schema contract for downstream `WS04-02B`, `WS04-03`, and `WS05`; it is not a substitute for implementing the later children. |
| Current game, booking, participant, waitlist, host/guest, capacity, and roster invariants | `WS04-02B` | Covers database-enforced or deliberately serialized behavior and deterministic concurrent proof for current source. Product rule changes remain outside this pass. |
| Current financial database invariants for payments, refunds, host publish fees, game credits, credit usage, money issues, and admin money state | `WS04-02B` | Covers database invariants and concurrent final-state protection. Payment state machines, provider truth, reconciliation, and worker-backed financial recovery remain with `WS05`. |
| Explicit locks, isolation, retry, timeout, deadlock, duplicate, and unknown-outcome behavior for current database invariants | `WS04-02B` | Covers current PostgreSQL/source behavior that can be proven locally. Final infrastructure runtime behavior and observability thresholds remain later-owned. |
| Deterministic independent-session concurrency tests for current invariants | `WS04-02B` | Covers current source/database invariants. Durable job claim tests run when `WS05` creates job state to claim. |
| Database time, currency, amount, status, JSON, and update-default compatibility | `WS04-02C` | Covers current repository-owned models, migrations, and tests after A/B changes. Production provider/runtime-specific observations remain late-bound where durable authority assigns them. |
| SQL construction, parameterization, raw SQL inventory, migration SQL expressions, and SQL/logging safety | `WS04-02C` | Covers repository source and current test evidence. Provider/database log access and broader observability controls remain with `WS09` and `WS10` where assigned. |
| Schema and migration compatibility policy, expand/contract migration rules, graph/drift, interruption, and production-like rehearsal | `WS04-03` | Not owned by `WS04-02` except for source/schema contracts that `WS04-03` consumes. |
| Durable job model, claim/lease lifecycle, worker deployment, crash recovery, retries, and worker runtime proof | `WS05-01` and later `WS05` passes | `WS04-02` must not invent a worker system. When jobs exist, their database transaction and claim behavior must satisfy the accepted WS04 source/schema contracts. |
| Full payment, booking, refund, credit, webhook, provider reconciliation, and Stripe sandbox lifecycle proof | `WS05-02` through `WS05-04` | `WS04-02` protects current database invariants and handoff boundaries only; it does not close the broader payment/provider controls. |
| Final production database topology, numeric connection budget, concrete production roles/grants, and provider/runtime verification | `WS04-01D` | Still deferred until final infrastructure exists and not required for current `WS04-02` execution. |
| Production dashboards, alert thresholds, SQL log access, incident/recovery exercises, backups, PITR, and provider-account operations | `WS09` and `WS10` | `WS04-02` may define source signals or safe metadata needed by its own proof, but it does not close later operational evidence. |

No parent responsibility is lost. The split preserves current database
transaction and concurrency work in `WS04-02` while keeping durable workers,
full payment/provider reconciliation, final infrastructure, and operational
evidence with their assigned later owners.

## 5. What Happens Next

This section identifies the next executable engineering work and why it is
ready to begin. The accepted database foundation is present, the current source
contains repository-owned transaction and external-side-effect workflows, and no
final production infrastructure fact is required to make those boundaries
explicit.

`WS04-02A - Transaction boundary and external-side-effect safety` is the next
executable work.

It can begin now because its required source, decisions, and technical
prerequisites are available on the accepted `develop` baseline. It must not
implement the later durable job system, select final infrastructure, or claim
full payment/provider reconciliation. It should leave accepted current-source
transaction and handoff contracts that `WS04-02B`, `WS04-03`, and `WS05` can
consume.

There is no current blocker to starting `WS04-02A`.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS04-02 - Transactions, invariants, locks, and deterministic concurrency` |
| Intake outcome | Split parent |
| Accepted baseline | `ec7332c5b4090f67963a7be7754d585626bb600e` |
| Intake path | `docs/production-readiness/planning/passes/ws04/ws04-02-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`; `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`; `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md`; accepted `WS04-01` artifacts; current source |
| Execution-register state | `WS04-02` is not yet decomposed or implemented and requires Stage 0 before first-time implementation |
| Approved decisions and prerequisites | Accepted provider-independent `WS04-01` foundation; final `WS04-01D` facts remain deferred and are not required for `WS04-02A` |
| Child order | `WS04-02A -> WS04-02B -> WS04-02C` |
| Proposed canonical plan path | `docs/production-readiness/planning/passes/ws04/ws04-02a-transaction-boundary-external-side-effect-safety.md` |
| Proposed requirement declaration | `backend/tests/support/requirements/ws04_02a.json` |
| Proposed trusted test or verification location | `backend/tests/workflows/transaction_boundary_external_side_effect_safety` |
| Blockers | None |
| Exact next allowed action | Fresh Gate A for `WS04-02A` |
