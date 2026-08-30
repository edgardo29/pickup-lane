# WS05-01A Durable Job Foundation Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS05-01A` |
| Trusted test scope | `backend/tests/platform/durable_jobs/` |
| Requirement declaration | `backend/tests/support/requirements/ws05_01a.json` |
| Authoritative sources | Frozen WS05-01A plan, accepted WS05-01 intake, master blueprint `JOB-M01` through `JOB-M08`, accepted WS02/WS04/EN-02 contracts, current backend source |
| Evidence layers | PostgreSQL integration tests, independent SQLAlchemy sessions, static command/import inspection, requirement checker |

## 1. Scope

This record covers the provider-independent durable job substrate: PostgreSQL
job state, lifecycle constraints, transactional/idempotent enqueue, atomic
claim, lease token, heartbeat renewal, expired-lease recovery, retry/exhaustion,
handler dispatch through synthetic handlers, active handler lease renewal,
token-guarded worker release, shutdown behavior, worker heartbeat state, source
operator summaries, recent safe event history, exception classification,
explicit operator repair operations, handlerless-definition rejection, and the
portable worker command.

It intentionally does not close payment, refund, credit, notice, moderation,
storage, Stripe sandbox, deployed worker hosting, final worker process counts,
final database connection budget, dashboards, alerts, incident operations, or
final provider/runtime proof.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS05-01A-R1` | PostgreSQL durable job, event, and worker heartbeat schema defaults and lifecycle invariants are physically enforced. | pytest/PostgreSQL |
| `WS05-01A-R2` | Enqueue is idempotent, transaction-owned by the caller, and side-effect-free. | pytest/PostgreSQL |
| `WS05-01A-R3` | Claim, lease, heartbeat, stale-token, and expired-lease behavior are database-authoritative. | pytest/PostgreSQL |
| `WS05-01A-R4` | Worker version compatibility, handlerless definitions, malformed payloads, and handler exceptions fail closed without unsafe side effects. | pytest/PostgreSQL |
| `WS05-01A-R5` | Retry, final-attempt exhaustion, explicit repair operations, and backlog fairness are bounded by executable job definitions. | pytest/PostgreSQL |
| `WS05-01A-R6` | Portable worker command runs only when invoked and does not define final deployment topology. | pytest/static |
| `WS05-01A-R7` | Operator summaries expose safe queue and worker state without sensitive diagnostics. | pytest |
| `WS05-01A-R8` | Accepted runtime/database/migration/transaction/SQL/correlation contracts remain compatible. | pytest/checker/regression |
| `WS05-01A-R9` | Final worker hosting, domain consumers, deployed proof, and operations remain later-owned. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R3`, `R5` | Job lifecycle state is finite and token guarded. | A job is both leased and terminal, or an old token mutates recovered work. | Duplicate or lost background work. | Database constraints and stale-token tests. | platform/PostgreSQL |
| `R2` | Enqueue does not commit or start work. | A request rolls back while the job survives, or enqueue starts providers. | Lost handoff or premature side effect. | Transaction rollback/idempotency tests. | platform/PostgreSQL |
| `R3` | Row locks, not process locks, decide claims. | Two workers claim the same row. | Duplicate execution. | Independent-session SKIP LOCKED proof. | platform/PostgreSQL |
| `R4` | Only executable definitions with handlers are claimable. | An incompatible or handlerless worker consumes attempts or exhausts valid work. | Deployment overlap can poison the queue. | Executable-registry claim filtering and handlerless negative tests. | platform/PostgreSQL |
| `R5` | Retries cannot exceed maximum attempts and aged work cannot starve indefinitely. | Infinite retries or priority starvation hides work. | Backlog growth and unresolved obligations. | Final-attempt exhaustion and fairness tests. | platform/PostgreSQL |
| `R6`, `R9` | Portable worker command is not final runtime proof. | Local command is mistaken for deployed worker hosting evidence. | False production-readiness closure. | Static command/topology boundary tests. | platform/static |
| `R7` | Diagnostics remain safe and bounded. | Payloads, secrets, personal data, or IDs leak through summaries. | Privacy/security incident. | Safe metadata rejection and summary tests. | platform |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | request enqueuer, worker, incompatible worker, operator | covered/grouped | These are the framework actors before consumer jobs exist. |
| States | pending, retry_waiting, leased, succeeded, exhausted, cancelled | covered | Finite lifecycle is central to the pass. |
| Actions | enqueue, claim, heartbeat, complete, retry, exhaust, cancel, requeue, inspect | covered/grouped | Tests cover core automatic paths and source repair boundaries. |
| Time | available_at, fairness age, lease expiry, heartbeat renewal | covered | PostgreSQL time and deterministic offsets prove behavior. |
| Concurrency | competing claimers, stale token, expired lease recovery | covered | Independent sessions prove database locking semantics. |
| Compatibility | executable worker type/version support and handler presence | covered | Registry filtering proves overlap behavior without handlerless attempt consumption. |
| Privacy/security | safe metadata and summaries | covered | Diagnostics reject sensitive/high-cardinality data. |
| Final infrastructure | worker platform, topology, connection budget | deferred | Requires final provider/runtime facts and WS05-01B/WS04-01D. |

## 5. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1`, `R2` | schema defaults, physical constraints, enqueue, duplicate/conflict, rollback | PostgreSQL | `test_enqueue_claim_lease_contract.py` | Proves current model/migration behavior, database-enforced lifecycle rejection, JSON defaults, and caller-owned transaction semantics. |
| `R3`, `R4`, `R5` | claim, SKIP LOCKED, version skip, handlerless rejection, fairness, heartbeat, stale lease, worker release, max attempts, operator cancel, operator requeue | PostgreSQL independent sessions | `test_enqueue_claim_lease_contract.py` | Exercises real row locking, token transitions, executable-registry filtering, worker-owned release, and repair history rather than mocks. |
| `R4`, `R6` | synthetic handler success/retry/exhaustion, transient/permanent exceptions, malformed payload, active lease renewal, active lease loss, shutdown, worker heartbeat | pytest/PostgreSQL | `test_worker_runtime_and_diagnostics_contract.py` | Proves generic framework behavior without adding consumer handlers. |
| `R6`, `R9` | portable command and no final topology claim | static/import/command | `test_worker_runtime_and_diagnostics_contract.py`, runtime compatibility tests | Confirms command is source-owned and provider-independent only. |
| `R7` | backlog summaries, worker heartbeat summaries, attempt/error visibility, recent safe history, safe metadata | pytest/PostgreSQL | `test_worker_runtime_and_diagnostics_contract.py` | Proves source summaries expose counts/classes/history, not sensitive payloads or high-cardinality internals. |
| `R8` | accepted compatibility scopes | pytest/checker/regression | focused WS05 tests plus accepted runtime, migration, SQL-safety, retry-handoff, and checker commands | Needed because WS05 adds schema and a command near accepted WS02/WS04 boundaries. |
| `R9` | later-owned evidence | declaration/record | `ws05_01a.json`, this record | Remains deferred because local source cannot prove final worker hosting or domain consumers. |

## 6. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Enqueue | A durable job and enqueue event exist only if the caller transaction commits. | No provider call, thread, subprocess, worker execution, or independent commit. | Duplicate key returns existing compatible job; conflicting key fails. |
| Claim | One compatible executable job is leased with token, owner, expiry, heartbeat, and incremented attempt. | Incompatible or handlerless worker cannot mutate, claim, exhaust, or consume attempts. | Uncommitted claim locks are skipped by another session. |
| Heartbeat | Current unexpired token extends the lease without incrementing attempts. | Expired or stale token cannot resurrect/mutate the job. | Lease ownership remains database-authoritative. |
| Handler success | Job becomes succeeded only after handler return and completion commit. Active handlers renew their lease through a separate database session before expiry. | Lease-lost worker cannot record success, retry, release, or exhaustion. | At-least-once contract remains explicit. |
| Handler exception | Transient and permanent handler exceptions are classified into safe error codes. | Raw exception details cannot become diagnostics or event metadata. | Worker exception handling uses definition-owned safe codes. |
| Worker release | Current unexpired lease token releases work back to pending when attempts remain; final-attempt release exhausts. | Stale or superseded lease tokens cannot release or mutate recovered work. | Release is worker-owned and token guarded. |
| Operator repair | Explicit operator cancellation and requeue preserve terminal/history state. | Operator repair is not confused with stale worker lease ownership. | Operator cancel/requeue repair is explicit and history-preserving. |
| Shutdown | Idle shutdown does not claim work; leased shutdown finishes or leaves the current claim under lease rules and does not claim additional jobs. | Shutdown does not mark idle jobs failed or consume attempts for unprocessed work. | Worker heartbeat records stopped state. |
| Diagnostics | Counts, safe statuses, attempt counts, worker heartbeat age, safe error codes, recent safe event history, and safe labels are available. | No payload, personal data, provider IDs, secrets, raw exceptions, lease tokens, or high-cardinality IDs in public/operator metadata. | Inspection is read-only. |

## 7. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Final worker hosting and deployment topology | deferred | Final worker platform and runtime are intentionally unselected. | `WS05-01B` |
| Payment/booking/refund/credit/notice/moderation/storage handlers | deferred | This pass creates the generic substrate only. | `WS05-02`, `WS05-03`, `WS06` as applicable |
| Stripe sandbox, deployed-worker failure/replay proof | deferred | Requires later domain state machines and deployed/sandbox evidence. | `WS05-04` |
| Final worker DB connection budget and production roles | deferred | Requires final topology and concrete worker consumers. | `WS04-01D` |
| Deployed dashboards, alerts, log aggregation, incident operations, recovery exercises | deferred | Source summaries are not deployed operations evidence. | `WS09`, `WS10` |

## 8. Adequacy Conclusion

The selected evidence is adequate for the frozen WS05-01A Gate B scope when the
durable-job focused tests, affected runtime/migration/SQL-safety/retry-handoff
compatibility tests, backend checker, and diff checks pass.

The evidence proves the provider-independent source and PostgreSQL framework.
It does not claim final worker hosting, payment/provider consumers, deployed
worker runtime proof, dashboards, alerts, or final database capacity evidence.
