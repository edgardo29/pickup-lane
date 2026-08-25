# WS04-01 - Database engine/session lifecycle, connection budget, and least-privilege roles intake

## 1. What Needs To Be Decided

This intake records the structural correction for the remaining `WS04-01`
database-foundation work after `WS04-01A` and `WS04-01B` were accepted.

The original split correctly separated application-owned database behavior,
query/database-access behavior, and production provider verification, but it did
not operationalize the program's infrastructure-timing rule correctly for the
remaining child. Current durable authority now makes that rule explicit:

- final production hosting and database infrastructure is intentionally
  late-bound until the permanent infrastructure is selected;
- current Vercel, Render, and Neon usage is temporary development/demo
  infrastructure, not permanent production architecture;
- temporary provider facts, free-tier limits, README examples, local/CI values,
  and demo deployment settings must not be promoted into final production
  assumptions or evidence;
- coherent provider-independent work should be completed now where possible;
- final provider-specific configuration, numeric values, topology, roles/grants,
  and runtime/provider proof must be preserved as mandatory deferred work with a
  named owner, trigger, dependencies, and latest completion boundary;
- final infrastructure must not be selected prematurely only to satisfy this
  pass.

This is therefore a correction to the executable structure, not a new exception
for `WS04-01`. The same durable timing rule applies program-wide.

The structural question is therefore whether the remaining work should stay as
one `WS04-01C` pass or be separated into work that can be completed now and
work that can only be completed after final infrastructure exists.

The revised structure must preserve every original `WS04-01` obligation without
reopening or weakening the accepted `WS04-01A` and `WS04-01B` results.

## 2. What We Know

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Accepted source foundation | `WS04-01A` is accepted. It established application database lifecycle, explicit pool size/overflow inputs, bounded pool wait and PostgreSQL timeouts, session cleanup, shutdown disposal, and application-versus-migration credential boundaries. | This work is complete and must not be reopened merely because final provider facts remain unknown. |
| Accepted database-access foundation | `WS04-01B` is accepted. It established current query, pagination, cursor-context, query/index-alignment, parent-binding, and page-bounded serialization behavior. | This work is complete and does not depend on final hosting or database-provider selection. |
| Approved budget direction | `DBP-01 / DB-002` requires one deployment-wide PostgreSQL connection budget with reserve. | The method is settled, but final numeric values still require actual provider capacity and deployment topology. |
| Durable infrastructure-timing rule | `00-READ-ME-FIRST.md`, `01-PROGRAM-CONTEXT.md`, the implementation workflow, and the master blueprint require final-infrastructure-dependent facts to remain late-bound and require Stage 0 to split/defer them when coherent provider-independent work can proceed. | This is the governing program rule for the remaining `WS04-01` structure, not a pass-specific workaround. |
| Final infrastructure status | Final production hosting and PostgreSQL provider/topology are intentionally undecided. Vercel, Render, and Neon are temporary development/demo infrastructure. | No pass may use current temporary provider facts as final production evidence or force an early infrastructure decision. |
| Superseded frozen `WS04-01C` boundary | The previous frozen `WS04-01C` plan combined provider-independent verification machinery with final provider/runtime evidence and therefore stopped when final provider facts were unavailable. | Its executable boundary conflicts with the durable infrastructure-timing rule and must be replaced before Gate B. |
| Provider-independent work | The remaining design already defines a reusable budget formula, evidence-safety rules, required connection-consumer categories, role/grant verification areas, telemetry-plan requirements, and safe-adjustment requirements. | These can be made into a coherent, testable verification framework now without inventing provider values. |
| Provider-dependent work | Actual provider capacity, pooler/proxy mode, deployed process counts, autoscaling/rolling overlap, deployed pool values, concrete production roles/grants, and runtime observations require the final deployment. | These must remain a later evidence-backed verification result. |
| Downstream database work | `WS04-02` and `WS04-03` need the accepted source/database foundation, while later provider/operations work needs final production evidence. `WS05` may add future database consumers that the final budget must account for. | The program must be able to continue source/domain work without pretending final production topology is already verified. |
| Closeout | `CLOSE-01` requires current provider/runtime evidence and all required workstream evidence to be reconciled. | Final production database verification cannot remain outstanding at closeout. |

## 3. Revised Execution Decision

Outcome: structurally revise the remaining `WS04-01` work.

Accepted `WS04-01A` and `WS04-01B` remain unchanged. The old `WS04-01C`
production-verification boundary is split into:

1. a provider-independent verification framework that can be completed now; and
2. a mandatory later final-production verification pass that becomes executable
   only after final infrastructure is selected.

### Current executable children

| Order | Work | Depends on |
|---|---|---|
| accepted | `WS04-01A - Application database lifecycle, pool settings, and role-credential boundaries` | Accepted WS02 runtime and timeout foundation |
| accepted | `WS04-01B - Query, cursor, and database-access behavior` | Current source and applicable accepted database-access decisions |
| next | `WS04-01C - Production PostgreSQL verification framework and evidence contract` | Accepted `WS04-01A` and accepted `WS04-01B` |

Current dependency graph:

```text
WS04-01A + WS04-01B -> WS04-01C
```

### Mandatory deferred follow-up

`WS04-01D - Final production PostgreSQL topology, connection budget, and role
verification` is the mandatory deferred verification unit for the remaining
final-infrastructure-dependent `WS04-01` obligations. It remains visible under
`WS04-01`, but it is not part of immediate executable child progression while
its final-infrastructure trigger is false. Deferred status is not proof and does
not close the affected `DB-002` or `DB-015` obligations.

`WS04-01D` becomes executable when all of the following are true:

- the final production database provider/topology is selected;
- the final hosting/deployment topology is selected sufficiently to bound API
  instances, processes, autoscaling, and rolling overlap;
- the current launch database consumers can be enumerated, including migrations,
  workers/jobs if present, monitoring/reporting/support access, and routine human
  access if any;
- sanitized provider/runtime/role evidence can be collected safely.

`WS04-01D` must run as soon as its trigger is satisfied and no later than the
earliest downstream pass that genuinely requires a D-owned fact or `CLOSE-01`,
whichever comes first. If a later pass requires one of its still-unverified
production facts earlier, that pass must stop on that specific prerequisite
rather than inventing or substituting temporary infrastructure values.

## 4. Where The Parent Work Goes

| Parent work | Primary owner | Remaining boundary / disposition |
|---|---|---|
| SQLAlchemy engine lifecycle, request session scope, rollback/close behavior, shutdown disposal, and database health-query boundaries | `WS04-01A` | Accepted. Do not reopen in C except compatibility verification. |
| Source-owned database settings for connection waiting, pool sizing/overflow, and safe environment use | `WS04-01A` | Accepted. Final deployed numeric values remain for `WS04-01D`. |
| Application and migration credential boundaries | `WS04-01A` | Accepted source boundary. Concrete production role identities and grants remain for `WS04-01D`. |
| Current query, pagination, cursor, and database-access behavior assigned to `DB-012` and `DB-013` | `WS04-01B` | Accepted. Production performance/observability remains later-owned. |
| Canonical deployment-wide connection-budget formula and required consumer categories | `WS04-01C` | Define and test the calculation contract now. Populate with final production values only in `WS04-01D`. |
| Sanitized evidence schema and evidence-safety validation for topology/budget/role proof | `WS04-01C` | Define and test the artifact contract now. Collect real provider/runtime evidence in `WS04-01D`. |
| Pooler/direct-connection compatibility evidence requirements | `WS04-01C` | Define the required evidence and acceptance rules now. Verify the selected production mode in `WS04-01D`. |
| Runtime topology evidence requirements for instances, processes, autoscaling, rolling overlap, startup/shutdown, and migration execution | `WS04-01C` | Define the verification contract now. Observe and verify the final deployment in `WS04-01D`. |
| Role/grant/search-path/default-privilege verification inventory | `WS04-01C` | Define the least-privilege checks and safe inspection contract now. Verify concrete production roles/grants in `WS04-01D`. |
| Budget telemetry-plan fields, reassessment triggers, and safe-adjustment/rollback contract | `WS04-01C` | Define required signals and adjustment evidence now. Bind them to the real deployment in `WS04-01D`; dashboards/alert thresholds remain with `WS09`. |
| Actual production PostgreSQL provider identity, usable connection capacity, pooler/proxy/direct mode, and provider-reserved capacity | `WS04-01D` | Deferred until final infrastructure is selected. Temporary Neon/Render facts are not acceptable substitutes. |
| Actual deployed API/process/autoscaling/rolling-overlap topology and deployed pool values | `WS04-01D` | Deferred until final deployment topology exists. |
| Final numeric connection budget, reserve, peak, and headroom | `WS04-01D` | Must use real provider/deployment evidence and the framework accepted in `WS04-01C`. |
| Concrete production application/migration/support/reporting/human roles, grants, ownership, search path, and default privileges | `WS04-01D` | Deferred until final provider role model exists. Broader provider-account MFA/rotation/revocation/offboarding remains `WS10`. |
| Transaction invariants, explicit locking, deterministic concurrency, and external-side-effect transaction boundaries | `WS04-02` | Not owned by `WS04-01C` or `WS04-01D`. |
| Migration compatibility policy, interruption/rehearsal behavior, and online-index strategy | `WS04-03` | Not owned by `WS04-01C` or `WS04-01D`; final migration connection facts may be consumed by D. |
| Durable worker/job design | `WS05` | Worker design remains WS05. Any worker connection demand that exists at final verification time must be included by `WS04-01D`. |
| Production dashboards, alerts, capacity trends, and long-term observability | `WS09` | C defines only the database-budget telemetry contract. D verifies the real database budget against the selected deployment. |
| Provider account lifecycle, backup/PITR/restore, recovery, rotation, revocation, and offboarding | `WS10` | Remains outside WS04-01 except for database role/grant facts directly required by D. |

No `WS04-01` obligation is dropped. Provider-specific proof is explicitly
preserved for `WS04-01D` rather than being guessed, silently closed, or replaced
with temporary infrastructure evidence.

## 5. Progression And Completion Meaning

`WS04-01C` is the next executable work.

It must leave a useful provider-independent result that downstream source/domain
work can consume without knowing the final provider. It must not claim a final
production connection budget or final production least-privilege verification.

After `WS04-01C` is accepted:

- the current provider-independent `WS04-01` database foundation is complete for
  purposes of continuing downstream engineering whose prerequisites are only
  source/database contracts;
- final `DB-002` connection-budget evidence and final `DB-015` production
  role/grant evidence remain explicitly deferred to `WS04-01D`;
- the broader controls and the parent are not represented as fully production
  verified merely because C is accepted;
- the mandatory deferred D unit remains visible in the execution register while
  its trigger is false;
- downstream Stage 0/Gate A work may proceed only when its own prerequisites do
  not require a D-owned production fact;
- if downstream work does require such a fact, it stops on that specific
  prerequisite;
- `WS04-01D` runs when its trigger is satisfied and remains mandatory no later
  than the first true consumer of its facts or `CLOSE-01`.

This distinction allows the program to continue without either forcing an early
infrastructure choice or falsely claiming production verification.

## 6. Current Next Action

The previous frozen `WS04-01C` plan no longer matches the revised executable
boundary and must not resume Gate B.

The next action is a fresh Gate A for:

`WS04-01C - Production PostgreSQL verification framework and evidence contract`

That Gate A plan must preserve accepted A/B behavior, define only work that can
be completed without final provider facts, and make the `WS04-01D` handoff
explicit.

## 7. Internal Record

| Detail | Value |
|---|---|
| Parent pass | `WS04-01 - Database engine/session lifecycle, connection budget, and least-privilege roles` |
| Intake outcome | Structural revision of remaining scope after accepted `WS04-01A` and `WS04-01B` |
| Current accepted develop basis for revision | `4200850354a5fd7db0dc0bdd2a7cfb8394cfa54f` |
| Intake path | `docs/production-readiness/planning/passes/ws04/ws04-01-intake.md` |
| Authority sources | `00-READ-ME-FIRST.md` final-infrastructure timing/provider-neutrality rule; `01-PROGRAM-CONTEXT.md` late-bound production-evidence rule; current implementation workflow Stage 0 infrastructure-timing classification; execution register; master blueprint Sections 3.1 and 8.1 plus `WS04-01`; final remediation plan; `DBP-01 / DB-002`; `FDN-04 / GOV-006`; accepted `WS04-01A`; accepted `WS04-01B`; current source |
| Preserved accepted children | `WS04-01A`; `WS04-01B` |
| Current dependency shape | `WS04-01A + WS04-01B -> WS04-01C` |
| Current selected child | `WS04-01C - Production PostgreSQL verification framework and evidence contract` |
| Deferred follow-up | `WS04-01D - Final production PostgreSQL topology, connection budget, and role verification` |
| `WS04-01D` trigger | Final production provider and deployment topology selected; launch database consumers bounded; sanitized evidence collectable |
| Temporary infrastructure rule | Vercel/Render/Neon development/demo facts, free-tier limits, examples, and local/CI values must not be used as final production architecture, configuration values, or evidence |
| Previous C plan state | Superseded for execution by this structural correction; do not resume its Gate B |
| Exact next action | Fresh Gate A for revised `WS04-01C`; do not rerun accepted A/B |
