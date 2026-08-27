# WS04-03 Intake - Migration Policy, Compatibility, Interruption, And Production-Like Rehearsal

## 1. What Needs To Be Decided

This intake decides how to execute the migration-safety parent work before
implementation begins. The decision matters because part of migration safety can
be proved from the repository and controlled PostgreSQL rehearsal now, while
part of it depends on final production database and deployment facts that are
intentionally not selected yet.

The parent engineering work is `WS04-03 - Migration policy, compatibility,
interruption, and production-like rehearsal`. It covers the rules and proof
needed to make Alembic schema changes safe across old and new application
versions, migration graph changes, interrupted migration runs, and production
rollout conditions.

The execution shape must separate provider-independent migration safety from
final provider/runtime evidence. Otherwise the current work would either block
on unknown final infrastructure or falsely treat temporary demo infrastructure
as production proof.

## 2. What We Know

This section lists only the facts that affect whether the migration work can be
executed now, must be split, or must wait. These facts should be read as
execution-boundary inputs, not as an implementation plan.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Accepted database foundation | `WS04-01A`, `WS04-01B`, and `WS04-01C` are accepted. `WS04-01C` provides a provider-independent production database verification framework while final topology, connection budget, and concrete production roles remain deferred to `WS04-01D`. | `WS04-03` can rely on application database lifecycle, query behavior, and provider-neutral verification contracts, but it must not require final production provider capacity, role, pooler, or deployment evidence. |
| Accepted transaction and schema contracts | `WS04-02A`, `WS04-02B`, and `WS04-02C` are accepted. They establish transaction boundaries, database invariants, locks, value/default behavior, SQL construction safety, and later-owner boundaries. | Migration compatibility work can now consume stable current source/schema contracts. It must preserve those accepted contracts and leave payment, job, observability, operations, and final-infrastructure proof with their owning later work. |
| Current migration shape | The repository has 59 Alembic revision files under `backend/alembic/versions/`, from `0001_enable_pg_trgm_extension.py` through `0059_create_admin_review_case_events_table.py`. The revision metadata forms one linear chain with one base and one head in current source inspection. | Graph and drift checks can be implemented and proved against current repository truth without final production infrastructure. |
| Current migration operations | Current upgrade-side migrations are predominantly table and ordinary index creation, plus fixed extension and sequence setup. Static inspection found no current upgrade-side destructive drop, rename, alter, backfill, data rewrite, concurrent-index directive, `NOT VALID`, or `VALIDATE` flow. | The current repository does not require an immediate destructive-data migration split. It does require a policy and fail-closed proof so future risky migration patterns cannot enter silently. |
| Current migration execution wiring | Alembic uses `backend/alembic/env.py`, resolves the migration database URL through settings, imports models to populate metadata, and uses `NullPool` for online migration execution. CI currently contains `alembic upgrade head` intent. | Empty-database upgrade, graph, and drift behavior can be checked provider-independently. Runtime deployment sequencing and final provider behavior remain separate. |
| Current trusted migration tests | `backend/tests/README.md` reserves `backend/tests/migrations/` for Alembic and schema-history testing, but that trusted root does not exist yet. Existing CI intent is not trusted evidence for prior-schema upgrade, drift, interruption, resume, old/new overlap, downgrade, rollback, or forward-fix behavior. | The current executable work should create the migration evidence surface rather than treating CI configuration as proof. |
| Current development migration policy | Repository agent standards still describe a pre-production clean-rebuild migration strategy and one-table-one-canonical-migration rule. Production-readiness authority requires expand/contract, compatibility-window, online-index, timeout, rollback/forward-fix, and rehearsal rules before production migration sign-off. | The current executable work must reconcile the pre-production development policy with the future immutable production migration policy without rewriting final provider facts. |
| Final infrastructure timing | Current Vercel, Render, and Neon usage is temporary demo/prototype infrastructure. Final database provider, deployment topology, migration runner, provider lock behavior, production volume, and migration runtime limits remain late-bound. | Provider-specific migration ceilings and final production-like topology evidence cannot be completed honestly now and must be deferred rather than guessed. |
| Later owners | Durable jobs, payment lifecycle, deployed logging, dashboards, alerts, backup/PITR, restore exercises, and final provider-role verification are assigned outside this parent. | `WS04-03` must define migration safety contracts these later passes can consume, but it must not absorb `WS05`, `WS09`, `WS10`, or `WS04-01D` work. |

## 3. Execution Decision

This section states the selected execution shape and why it is technically
appropriate. The parent is split because repository-owned migration policy and
controlled rehearsal can proceed now, while final provider/runtime migration
evidence depends on late-bound production infrastructure.

Outcome: split the parent into ordered child work.

| Order | Work | Depends on |
|---|---|---|
| `1` | `WS04-03A - Provider-independent migration policy, compatibility, graph/drift checks, and controlled rehearsal` | Accepted `WS04-01A/B/C` and `WS04-02A/B/C` |
| `2` | `WS04-03B - Final provider/runtime migration rehearsal and rollout evidence` | Accepted `WS04-03A`; final production database provider, deployment topology, migration runner, and production-equivalent rehearsal inputs selected and evidenced |

`WS04-03A` is one coherent current result: it establishes the repository-owned
migration policy, compatibility rules, graph and drift checks, and controlled
PostgreSQL rehearsal surface that future schema work must obey. It can be
accepted without final production infrastructure because it uses current source,
current migrations, controlled test databases, and sanitized synthetic or
repository-owned fixtures.

`WS04-03B` is separate because its proof depends on facts that are not available
yet: the final provider, runtime/deployment topology, migration execution path,
production-like volume or representative dataset, provider lock behavior, and
final operational rollout conditions. Keeping it separate prevents temporary
demo infrastructure from becoming accidental production evidence.

## 4. Where The Parent Work Goes

This section accounts for the complete parent scope. It shows where each major
responsibility belongs so the split has no hidden gap and no accidental overlap.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| Migration policy and expand/contract rules | `WS04-03A` | Final provider-specific thresholds or rollout settings are not invented by the policy. |
| Old/new application compatibility rules for schema changes | `WS04-03A` | Final rolling-deployment topology proof remains with `WS04-03B` after infrastructure selection. |
| Migration graph, multiple-head, dependency, and drift verification | `WS04-03A` | Provider dashboard or production schema observations remain external evidence. |
| Empty-database upgrade and prior-schema upgrade behavior | `WS04-03A` | Uses controlled local/test PostgreSQL evidence, not final production database access. |
| Locking, duration, timeout, interruption, resume, rollback, and forward-fix behavior for current repository migrations | `WS04-03A` | Provider/runtime-specific ceilings and production-volume timing are deferred to `WS04-03B`. |
| Controlled migration rehearsal design and provider-independent rehearsal results | `WS04-03A` | Final provider/runtime rehearsal facts are not claimed until `WS04-03B`. |
| Final production database provider lock behavior, migration runtime ceilings, topology-specific rolling overlap, and production-equivalent rehearsal evidence | `WS04-03B` | Runs only after final provider/runtime facts are available. It does not replace `WS04-01D` role, connection-budget, or grant verification. |
| Migration interaction with future durable workers and payment/provider flows | Later `WS05` passes consume `WS04-03A` contracts | `WS04-03` does not design durable jobs, payment state machines, webhook recovery, provider reconciliation, or worker deployment. |
| Deployed migration observability, dashboards, alerts, log aggregation, incident runbooks, backup/PITR, restore, and recovery exercises | `WS09` and `WS10` | `WS04-03A` may define migration signals or records needed by its own repository proof, but operational evidence remains with those owners. |
| Final production PostgreSQL topology, numeric connection budget, concrete roles/grants, and effective migration-role evidence | `WS04-01D` | `WS04-03B` consumes these facts when available; it does not own their selection or final role/grant proof. |

## 5. What Happens Next

This section identifies the next executable engineering work and why it is ready
to begin. It separates real blockers from facts that are intentionally deferred.

`WS04-03A` is the next executable work because the accepted database foundation,
transaction/invariant/value contracts, current Alembic chain, current models,
database settings, CI configuration, and trusted test architecture are now
available in accepted `develop`.

No technical prerequisite blocks `WS04-03A`. The missing final production
provider, topology, runtime, and provider-specific rehearsal facts block only
`WS04-03B`, not the provider-independent policy, compatibility, graph/drift, and
controlled rehearsal work.

## 6. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS04-03 - Migration policy, compatibility, interruption, and production-like rehearsal` |
| Intake outcome | Split current provider-independent work plus mandatory deferred follow-up |
| Accepted baseline | `7e3308591a7f3789adad04623978da3304b481d1` |
| Intake path | `docs/production-readiness/planning/passes/ws04/ws04-03-intake.md` |
| Authority sources | `docs/production-readiness/00-READ-ME-FIRST.md`; `docs/production-readiness/01-PROGRAM-CONTEXT.md`; `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`; `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`; `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`; `docs/production-readiness/planning/program/pickup-lane-production-readiness-remediation-plan-final.md`; locked audit controls `DB-016`, `DB-017`, `DB-018`, and `TST-009`; relevant governance records for final infrastructure timing and database ownership; current accepted source and migration/test infrastructure |
| Execution-register state | `WS04-03` is not yet decomposed or implemented. `WS04-01A/B/C` and `WS04-02A/B/C` are accepted. `WS04-01D` remains deferred until final production infrastructure is selected. |
| Approved decisions and prerequisites | Accepted provider-independent `WS04-01` foundation; accepted `WS04-02` child set; PostgreSQL remains the selected database technology; final provider/runtime facts remain late-bound |
| Child order | `WS04-03A -> WS04-03B` |
| Current executable child | `WS04-03A - Provider-independent migration policy, compatibility, graph/drift checks, and controlled rehearsal` |
| Deferred follow-up | `WS04-03B - Final provider/runtime migration rehearsal and rollout evidence` |
| Deferred trigger | Final production database provider, deployment topology, migration runner, and production-equivalent rehearsal inputs are selected and evidenced enough to measure provider/runtime migration behavior safely. |
| Deferred preserved obligations | Provider/runtime-specific migration ceilings, production-equivalent lock and duration evidence, topology-specific rolling overlap behavior, final migration execution path, provider-specific extension/sequence behavior where applicable, and final rollout/rehearsal evidence. |
| Deferred dependencies | Accepted `WS04-03A`; final-infrastructure selection; applicable `WS04-01D` database topology/role/budget evidence; any required `WS09` or `WS10` operational/recovery evidence needed for safe final rehearsal. |
| Latest deferred completion boundary | As soon as the deferred trigger is satisfied and no later than the first production migration sign-off that requires final provider/runtime migration facts or `CLOSE-01`, whichever comes first. |
| Proposed canonical plan path | `docs/production-readiness/planning/passes/ws04/ws04-03a-provider-independent-migration-policy-compatibility-graph-drift-controlled-rehearsal.md` |
| Proposed requirement declaration | `backend/tests/support/requirements/ws04_03a.json` |
| Proposed trusted test or verification location | `backend/tests/migrations/migration_policy_compatibility_rehearsal/` |
| Blockers | None for `WS04-03A`; final provider/runtime facts block only deferred `WS04-03B` |
| Exact next allowed action | Begin Gate A for `WS04-03A` from accepted baseline `7e3308591a7f3789adad04623978da3304b481d1` on branch `pr/WS04-03`; verify this intake SHA before planning. |
