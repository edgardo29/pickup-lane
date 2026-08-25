# Testing Record: WS04-02B - Database-Enforced Invariants, Locks, And Deterministic Concurrency

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS04-02B` |
| Trusted test scope | `backend/tests/workflows/database_invariants_locks_deterministic_concurrency/` |
| Requirement declaration | `backend/tests/support/requirements/ws04_02b.json` |
| Authoritative sources | Frozen WS04-02 intake, frozen WS04-02B canonical plan, accepted WS04-01A/B/C database foundation, accepted WS04-02A transaction-boundary evidence, current backend source |
| Evidence layers | pytest, barrier-synchronized independent PostgreSQL sessions, static source-policy checks |

## 1. Scope

This record covers current database-owned roster, capacity, waitlist,
provider-adjacent, credit, refund, and financial invariants assigned to
WS04-02B. It proves game-first serialization for current capacity mutations
with deterministic independent-session contention, paid-waitlist capacity holds
across the provider checkpoint, runtime account-deletion multi-game cleanup and
waitlist promotion, database-enforced duplicate/idempotency boundaries, and
frozen financial invariant dispositions.

This scope does not prove final production hosting/database infrastructure,
live provider reconciliation, durable worker execution, complete payment
lifecycle redesign, migration rehearsal, observability dashboards, or deployed
runtime evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS04-02B-R1` | Material current database invariants are cataloged with one authoritative disposition. | pytest/static |
| `WS04-02B-R2` | Community capacity decisions serialize on the owning game row before capacity reads/decisions. | pytest/PostgreSQL |
| `WS04-02B-R3` | Waitlist promotion preserves party size, ordering, paid holds, and post-provider-boundary recomputation. | pytest/PostgreSQL/static |
| `WS04-02B-R4` | Capacity mutations use deterministic game-first lock order, including account deletion. | pytest/static |
| `WS04-02B-R5` | Active participant, waitlist, provider, and idempotency duplicates are database-enforced. | pytest/static/PostgreSQL |
| `WS04-02B-R6` | Frozen financial invariant dispositions remain source-owned and narrow. | pytest/static |
| `WS04-02B-R7` | Game-credit reserve/release/restore/reverse cannot overdraw or duplicate ledger state. | pytest/PostgreSQL/static |
| `WS04-02B-R8` | Database contention and unknown outcomes are bounded without process-local locks or blind replay. | pytest/static |
| `WS04-02B-R9` | Accepted database foundations and WS04-02A transaction boundaries remain intact without final-infrastructure claims. | pytest/static |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Safeguard | Owning Test Layer |
|---|---|---|---|---|
| `R1`, `R5`, `R6` | Every current invariant has one declared disposition and matching database/service owner. | A financial or roster invariant is omitted, duplicated, or assigned to the wrong owner. | Declarative policy registry and model constraint checks. | workflows |
| `R2`, `R8` | Capacity decisions are serialized through the game row, not process-local memory. | Concurrent joins or guest adds both observe stale capacity and overfill the game. | Barrier-synchronized independent-session service races against PostgreSQL row locks. | workflows |
| `R3` | Paid waitlist promotion reserves full-party capacity across provider checkpoints. | A second join consumes the same spot while Stripe work is pending. | Committed pending-payment hold plus post-boundary lock reacquisition/recompute. | workflows |
| `R4` | Account deletion locks affected future games before dependent roster rows. | Multi-game cleanup can deadlock with normal roster mutations or skip affected rows. | Runtime multi-game cleanup proof plus static lock-order proof for game discovery, deterministic game locks, reread bookings/participants, then promotion. | workflows |
| `R7` | Credit usage rows and grant balances serialize on credit/usage rows. | Concurrent reservations overdraw, release/redeem twice, restore twice, or reverse with reserved usage. | Barrier-synchronized independent-session credit reservation, release, redeem, restore, and reversal races plus source checks for locks and unique restore identity. | workflows |
| `R9` | This pass does not change WS04-02A provider boundaries or final-infrastructure deferrals. | Database-invariant work silently redesigns payment/provider lifecycle or claims production facts. | Negative-space checks against source and policy text. | workflows |

## 4. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence |
|---|---|---|---|
| `R1`, `R5`, `R6`, `R8`, `R9` | invariant disposition registry, model/database constraint inventory, provider/final-infrastructure negative space | pytest/static | `test_database_invariant_policy_contract.py` |
| `R2`, `R5`, `R8` | concurrent community joins against one remaining spot | pytest/PostgreSQL barrier-synchronized independent sessions | `test_roster_capacity_concurrency_contract.py` |
| `R2`, `R5`, `R8` | concurrent player guest and host guest adds against one remaining spot | pytest/PostgreSQL barrier-synchronized independent sessions | `test_roster_capacity_concurrency_contract.py` |
| `R3` | waitlist promotion after a roster departure | pytest/PostgreSQL service workflow | `test_roster_capacity_concurrency_contract.py` |
| `R3`, `R4`, `R8` | account-deletion multi-game roster cleanup, deterministic game order, and waitlist promotion | pytest/PostgreSQL runtime workflow | `test_roster_capacity_concurrency_contract.py` |
| `R3`, `R8`, `R9` | paid waitlist provider checkpoint and committed capacity hold | pytest/PostgreSQL with provider fake | `test_roster_capacity_concurrency_contract.py` |
| `R7`, `R8` | concurrent game-credit reservation, release, redeem, restore, and reversal convergence | pytest/PostgreSQL barrier-synchronized independent sessions | `test_credit_concurrency_contract.py` |

## 5. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Final production PostgreSQL provider, deployed connection budget, production roles/grants | deferred | Final infrastructure remains intentionally unselected. | `WS04-01D` |
| Provider retry reconciliation, live Stripe truth, and durable payment workers | covered elsewhere/deferred | WS04-02B preserves but does not redesign provider lifecycle. | `WS04-02A`, `WS05` |
| Migration rehearsal and production-like upgrade/downgrade proof | deferred | Not assigned to this executable child. | `WS04-03` |
| Database value/default/logging safety | deferred | Assigned to the next WS04-02 child. | `WS04-02C` |
| Observability dashboards, deployed alerts, and incident/audit operations | deferred | Not produced by local database invariant proof. | `WS09`, `WS10` |

## 6. Validation Results

- Focused WS04-02B workflow evidence: `17 passed`.
- Focused WS04-02B checker: `PASS`.
- Accepted WS04-02A transaction-boundary compatibility scope: `20 passed`.
- Affected account-deletion compatibility slice: `15 passed`.
- Affected roster and credit-source compatibility slice: `20 passed`.
- Accepted WS04-01A/B/C database foundation, query, and production-database
  verification compatibility scopes: `69 passed`.
- `git diff --check`: `PASS`.

## 7. Adequacy Conclusion

The selected evidence is adequate for Gate B when the focused WS04-02B tests,
affected WS04-02A compatibility tests, accepted database-foundation checks,
focused checker, `git diff --check`, and final scope/security review pass. No
WS04-02B requirement is marked covered elsewhere or deferred in the declaration.
Later production-infrastructure, provider, migration, runtime, observability,
and full payment-lifecycle evidence remains explicit.
