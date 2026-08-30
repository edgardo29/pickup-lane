# WS05-01 Intake - Durable Job Model, Claim/Lease Lifecycle, And Worker Deployment

## 1. What Needs To Be Decided

This intake decides how to execute the durable-job foundation before
implementation begins. The decision matters because the repository can build
and prove portable job semantics now, while final worker-hosting and runtime
proof depend on production infrastructure that has intentionally not been
selected yet.

The parent engineering work is `WS05-01 - Durable job model, claim/lease
lifecycle, and worker deployment`. It covers the shared job state, worker
runtime contract, claim and lease behavior, retry and crash behavior, exhausted
work handling, operator visibility, and worker deployment proof that later
payment, refund, credit, notice, moderation, reconciliation, and storage work
will consume.

The execution shape must keep source-owned durable-job behavior moving without
pretending that temporary demo infrastructure is final production worker
evidence.

## 2. What We Know

This section lists only the facts that affect whether the durable-job parent
can execute now, must be split, or must wait. These facts should be read as
execution-boundary inputs, not as an implementation plan.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Accepted runtime foundation | `WS02-02` is accepted and provides the portable application lifecycle, health, shutdown, and runtime/deployability foundation. Final host/provider topology remains late-bound where provider facts are required. | A portable worker command and graceful-shutdown contract can build on the accepted runtime rules, but final platform deployment proof cannot be invented before provider selection. |
| Accepted database foundation | `WS04-01A`, `WS04-01B`, and `WS04-01C` are accepted. `WS04-01D` remains mandatory and deferred for final PostgreSQL provider, topology, numeric connection budget, and concrete production roles. | Job schema and claim/lease behavior can use the provider-independent PostgreSQL foundation. Final worker connection demand must be fed into `WS04-01D` when actual worker consumers and topology exist. |
| Accepted transaction, invariant, SQL, and migration contracts | `WS04-02A`, `WS04-02B`, `WS04-02C`, and `WS04-03A` are accepted. They define current source transaction boundaries, database invariants, SQL/value safety, migration compatibility, and controlled migration rehearsal. | The job model can now add repository-owned schema and worker behavior without reopening completed database children, while preserving their source/schema contracts. |
| Current durable-job source state | Source inspection found no general durable job table, claimable queue, atomic job claim, lease, heartbeat, worker identity, scheduled worker, dead-letter lifecycle, or worker deployment command. Existing `MoneyIssue` rows are admin money obligation records, not a generic durable worker queue. | The first executable work must create the shared job foundation rather than treating any current source surface as an existing implementation. |
| Current retry and handoff state | Accepted source-owned retry/reconciliation policy records durable handoff needs for checkout, webhook, refund, saved-card, account-deletion, storage, and other provider-adjacent workflows without approving worker retry numbers or topology. | `WS05-01A` should provide the reusable durable job substrate. Consumer-specific payment, provider, refund, credit, and reconciliation state machines stay in later WS05 children. |
| Primary parent controls | The blueprint assigns `JOB-M01` through `JOB-M08` to this parent: durable queue/model, job identity, claim/lease/heartbeat, at-least-once execution, retry/exhaustion, dead-letter/repair, worker shutdown/version behavior, and job observability. | These controls form one cohesive provider-independent engineering result when implemented as a shared job foundation. |
| Final worker infrastructure | Final worker hosting platform, service topology, scaling/resource settings, provider deployment configuration, and runtime proof are intentionally unselected. Current local, Render, Vercel, Neon, or other demo facts are not final production worker evidence. | Final worker-hosting proof is a mandatory deferred follow-up. It cannot block the portable job foundation, and it cannot be closed with temporary infrastructure. |
| Later WS05 payment and reconciliation work | `WS05-02`, `WS05-03`, and `WS05-04` own payment/booking state machines, webhook authority, refunds, credits, notices, moderation delivery, reconciliation, Stripe sandbox proof, deterministic provider failure proof, and deployed-worker verification. | `WS05-01` must provide the shared job machinery those passes need, but it must not absorb their domain-specific workflows. |
| Later operational and provider owners | `WS09` and `WS10` own deployed dashboards, alert routing, log aggregation, incident operations, backup/restore, and recovery exercises. `WS04-01D` owns final database topology and role/budget proof. | The current parent can expose source-owned job state and operator interfaces, but final observability, incident, recovery, and database-provider evidence remain outside this parent. |

## 3. Execution Decision

This section states the chosen execution shape for the parent and the technical
reason that shape is appropriate. The parent should be split because the durable
job model and portable worker runtime are source-owned and executable now,
while final worker deployment proof requires a different environment and
late-bound provider facts.

Outcome: split the parent into ordered child work.

| Order | Work | Depends on |
|---|---|---|
| `1` | `WS05-01A - Provider-independent durable job model, claim/lease lifecycle, and portable worker runtime` | Accepted `WS02-02`, `WS04-01A/B/C`, `WS04-02A/B/C`, `WS04-03A`, and `EN-02` |
| `2` | `WS05-01B - Final worker hosting topology, deployment configuration, and runtime proof` | Accepted `WS05-01A`; final worker platform, service topology, scaling/resource inputs, and provider deployment path selected and evidenced |

`WS05-01A` is one coherent current result: it creates the repository-owned
durable job foundation and portable worker contract that later consumers can
use without knowing the final worker host. It can be accepted from source,
PostgreSQL, and controlled local/CI-style proof.

`WS05-01B` is separate because its result depends on final provider/runtime
facts: the worker host, service topology, process or instance model, resource
and scaling settings, provider configuration, and runtime verification. Keeping
it separate prevents temporary development infrastructure from becoming false
production deployment proof.

## 4. Where The Parent Work Goes

This section accounts for the complete parent scope. It shows where each major
responsibility belongs so the split has no hidden gap and no accidental
overlap.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Durable job schema, identity, type, version, priority, safe payload, availability, attempt, result, and error state | `WS05-01A` | Provider-specific storage or managed-queue configuration is not required for the repository-owned PostgreSQL job model. |
| Transactional handoff or outbox behavior needed so request-time state can create durable work without loss | `WS05-01A` | Domain-specific payment, refund, credit, notice, moderation, or storage handlers remain with their owning later passes unless the minimal handoff contract requires a shared interface. |
| Atomic claim, lease, heartbeat, worker identity, expired-lease recovery, duplicate-worker protection, and backlog fairness | `WS05-01A` | Final runtime sizing, worker count, autoscaling, and provider scheduling behavior remain with `WS05-01B` or later deployed verification. |
| At-least-once execution, handler version compatibility, bounded retry classification, exhausted/dead-letter state, replay authorization, and repair visibility | `WS05-01A` | Consumer-specific provider side effects and financial reconciliation workflows remain with `WS05-02`, `WS05-03`, and `WS05-04`. |
| Portable worker command, graceful shutdown behavior, current source operator interfaces, and runbook draft | `WS05-01A` | Final provider deployment configuration, platform shutdown behavior, rollout overlap, and runtime proof remain with `WS05-01B`. |
| Deterministic provider-independent proof for crash/restart, stale leases, competing claimers, unsupported versions, shutdown, retry exhaustion, and backlog behavior | `WS05-01A` | Stripe sandbox, deployed-worker, provider outage, and final platform proof remain with later WS05 verification work. |
| Final worker hosting platform, service topology, scaling/resource settings, provider deployment configuration, and runtime worker proof | `WS05-01B` | Runs only after final worker infrastructure facts are available. It must not substitute local, CI, Render, Vercel, Neon, or demo evidence for final production proof. |
| Payment and booking state machines with webhook authority | `WS05-02` | Consumes the `WS05-01A` job foundation but owns payment/booking domain semantics and provider authority. |
| Refunds, credits, notices, moderation delivery, and reconciliation workflows | `WS05-03` | Consumes the `WS05-01A` job foundation and any accepted payment state model from `WS05-02`. |
| Deterministic failure, replay, sandbox, and deployed-worker verification for the WS05 workstream | `WS05-04` | Consumes `WS05-01A`, later domain children, and `WS05-01B` when deployed-worker proof depends on final platform facts. |
| Final database connection demand and concrete production database role/grant impact from workers | `WS04-01D` | `WS05-01A` may define how worker demand is counted, but final numeric capacity and concrete production grants remain with the final database verification owner. |
| Deployed job dashboards, alert routing, log aggregation, incident operations, backup/restore, and recovery exercises | `WS09` and `WS10` | `WS05-01A` can expose safe source-owned job signals and records; final operational evidence remains with those later owners. |
| Asynchronous storage processing or storage reconciliation that uses durable jobs | `WS06` | Consumes the job foundation if asynchronous storage work is selected, but storage lifecycle/provider evidence remains outside `WS05-01`. |

## 5. What Happens Next

This section identifies the next executable engineering work and why it is
ready to begin. It separates real blockers from facts that are intentionally
deferred.

`WS05-01A - Provider-independent durable job model, claim/lease lifecycle, and
portable worker runtime` is the next executable work.

It can begin now because the accepted runtime, database, transaction, SQL,
migration, and correlation prerequisites are present in the current accepted
source. The missing final worker host, service topology, scaling/resource
settings, and provider deployment path block only `WS05-01B`, not the
provider-independent durable job foundation.

`WS05-01` remains incomplete until the deferred final worker-hosting/runtime
proof is accepted or otherwise truthfully resolved under durable authority.
After `WS05-01A` is accepted, downstream work that needs only the portable job
foundation may proceed; work that requires final deployed worker facts must wait
for `WS05-01B` or the later deployed-worker verification that consumes it.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS05-01 - Durable job model, claim/lease lifecycle, and worker deployment` |
| Intake outcome | Split current provider-independent durable-job foundation plus mandatory deferred final worker-hosting/runtime follow-up |
| Accepted baseline | `4ac48cd4457e37374e3ccb3c6d981636a6fc1a2e` |
| Intake path | `docs/production-readiness/planning/passes/ws05/ws05-01-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`; `docs/production-readiness/planning/templates/PASS-INTAKE-TEMPLATE.md`; `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`; `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`; `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md`; accepted `WS02-02`, `EN-02`, `WS04-01A/B/C`, `WS04-02A/B/C`, and `WS04-03A` artifacts; current accepted source |
| Execution-register state | `WS05-01` is not yet decomposed or implemented and requires Stage 0 before first-time implementation. `WS04-01D` and `WS04-03B` remain mandatory deferred final-infrastructure follow-ups. |
| Approved decisions and prerequisites | Accepted portable runtime foundation; accepted provider-independent database foundation; accepted source/schema transaction, invariant, SQL, and migration contracts; accepted event/correlation/redaction contract. Final worker hosting and final production database facts remain late-bound. |
| Child order | `WS05-01A -> WS05-01B` |
| Current executable child | `WS05-01A - Provider-independent durable job model, claim/lease lifecycle, and portable worker runtime` |
| Deferred follow-up | `WS05-01B - Final worker hosting topology, deployment configuration, and runtime proof` |
| Deferred trigger | Final worker platform, service topology, process/instance model, scaling/resource settings, provider deployment configuration path, and safe runtime verification environment are selected and evidenced enough to verify deployed worker behavior honestly. |
| Deferred preserved obligations | Final worker hosting/platform proof, provider deployment configuration, scaling/resource settings, service topology, worker runtime identity and shutdown proof in the selected environment, deployed claim/heartbeat/lease evidence, and final worker connection-demand inputs for `WS04-01D`. |
| Deferred dependencies | Accepted `WS05-01A`; final worker infrastructure selection; applicable `WS04-01D` database topology/role/budget evidence when final connection demand is measured; any `WS09` or `WS10` observability/operations evidence required for deployed-worker verification. |
| Latest deferred completion boundary | As soon as the deferred trigger is satisfied and no later than deployed-worker verification in `WS05-04`, WS05 workstream exit evidence, or `CLOSE-01`, whichever first requires final worker runtime facts. |
| Proposed canonical plan path | `docs/production-readiness/planning/passes/ws05/ws05-01a-provider-independent-durable-job-model-claim-lease-lifecycle-portable-worker-runtime.md` |
| Proposed requirement declaration | `backend/tests/support/requirements/ws05_01a.json` |
| Proposed trusted test or verification location | `backend/tests/platform/durable_jobs/` |
| Blockers | None for `WS05-01A`; final worker hosting/runtime facts block only deferred `WS05-01B` |
| Exact next allowed action | Begin Gate A for `WS05-01A` from accepted baseline `4ac48cd4457e37374e3ccb3c6d981636a6fc1a2e` on branch `pr/WS05-01`; verify this intake SHA before planning. |
