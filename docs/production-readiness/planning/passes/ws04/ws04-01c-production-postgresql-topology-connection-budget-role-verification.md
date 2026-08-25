# WS04-01C - Production PostgreSQL Verification Framework And Evidence Contract

This pass builds and proves the provider-independent framework that will later be
used to verify Pickup Lane's final production PostgreSQL topology, connection
budget, and least-privilege database roles.

It applies the program-wide final-infrastructure timing and provider-neutrality
rule. It does **not** select the final production infrastructure, bind Pickup
Lane permanently to a temporary hosting/database provider, or treat current
development/demo infrastructure as final production evidence.

The real production-provider/deployment verification is preserved for mandatory
later pass `WS04-01D - Final production PostgreSQL topology, connection budget,
and role verification` after the final infrastructure is selected. Temporary
Neon/Render values, free-tier limits, local settings, README examples, and other
provider-specific development/demo facts are not substitutes for that later
evidence.

## 1. What This Work Does

`WS04-01A` established the application-owned SQLAlchemy contract:
production-like environments require explicit `DB_POOL_SIZE` and
`DB_MAX_OVERFLOW`, per-process application demand is bounded by those values,
pool waiting is bounded, checked-out connections receive statement and lock
timeouts, request sessions are per use, shutdown disposes the application
engine, Alembic uses `MIGRATION_DATABASE_URL`, and online migrations use
`NullPool`.

`WS04-01B` established the current source contract for bounded collection
routes, pagination, cursor context, query/index alignment, authorization and
parent binding in database queries, and page-bounded serialization.

The previous `WS04-01C` plan attempted to combine those accepted contracts with
final provider/runtime evidence. Under the durable program-wide infrastructure
timing rule, that boundary is not executable while final production hosting and
database infrastructure remains intentionally unselected. The executable work
must stay provider-neutral and the final-infrastructure proof must remain a
separate later obligation.

This revised pass completes the useful work that does not depend on provider
selection:

- define a repository-safe sanitized evidence contract for later topology,
  budget, runtime, and role/grant proof;
- define the complete deployment-wide connection-budget model and its required
  inputs without assigning final production numbers;
- make the budget arithmetic deterministic and testable with synthetic fixtures;
- define completeness and evidence rules for every connection consumer;
- define the provider/pooler/runtime compatibility evidence that later
  verification must collect;
- define the least-privilege role/grant/search-path/default-privilege inspection
  contract;
- define the budget telemetry-plan fields, staleness triggers, and safe
  adjustment or rollback evidence required before a production value can be
  trusted;
- produce tests and a testing/evidence record proving the framework rejects
  incomplete, unsafe, inconsistent, or mathematically invalid evidence;
- preserve a precise handoff to `WS04-01D` for the actual final production
  values and runtime/provider verification.

A clean result from this pass means Pickup Lane has a stable, reviewable method
for final production database verification. It does not mean the final provider,
connection budget, or production grants have already been verified.

## 2. What Must Be True

### 2.1 Final Infrastructure Remains Unselected

This pass must apply the final-infrastructure timing and provider-neutrality rule
from the read-first document, Program Context, implementation workflow, and
master blueprint. It must explicitly preserve these facts:

- final production hosting and database infrastructure has not yet been selected;
- current Neon and Render usage is temporary development/demo infrastructure, not
  permanent production architecture;
- temporary provider settings, free-tier limits, local values, README examples,
  and other development/demo facts must not populate final production fields;
- provider-independent configuration *interfaces* may be implemented now when
  they are required by accepted source behavior, but final provider-specific
  values remain deferred;
- no provider, provider plan, capacity, pooler mode, instance count, process
  count, autoscaling ceiling, additional rolling-overlap value, production pool
  value, or concrete production role/grant may be invented or copied from
  examples;
- inability to provide final production values is **not** a blocker for this
  revised C pass because those values belong to `WS04-01D`.

The framework must distinguish an intentionally unpopulated future production
field from a missing field that should have been supplied for a completed D
verification.

### 2.2 Sanitized Evidence Contract Is Explicit

The pass must define one canonical provider-independent evidence shape that
`WS04-01D` can populate later.

The contract must identify, at minimum:

- provider or control plane;
- evidence source type;
- collection or observation date;
- environment class;
- reviewer or accountable role;
- purpose;
- control or pass supported;
- sanitized evidence reference;
- raw evidence location reference when one exists outside Git, or an explicit
  not-applicable reason;
- stable safe alias for provider/service/role where real identifiers are not
  approved for repository exposure;
- evidence state, such as `unverified`, `verified`, `not_applicable`, or
  `deferred_to_ws04_01d`;
- sanitized value when a value is permitted;
- source rationale for zero-valued consumers;
- open gap or blocker when proof is incomplete;
- staleness trigger;
- telemetry signal or explicit later-owner gap where required;
- safe adjustment, rollback, or forward-fix path for mutable capacity inputs.

The contract must prohibit tracked evidence from containing:

- database URLs;
- passwords, tokens, private keys, or other credentials;
- private dashboard URLs;
- account IDs, project IDs, or private provider identifiers when not required;
- raw screenshots or unredacted provider exports;
- raw logs;
- IP addresses or private hostnames;
- personal or payment data.

The framework must make it possible for `WS04-01D` to preserve attributable
proof without committing sensitive source material.

### 2.3 Connection-Budget Model Is Complete And Deterministic

The canonical model is:

```text
per_process_application_connections =
    DB_POOL_SIZE + DB_MAX_OVERFLOW

api_steady_state_connections =
    max_api_instances
    * api_processes_per_instance
    * per_process_application_connections

api_incremental_rolling_overlap_connections =
    additional_rolling_overlap_api_instances
    * api_processes_per_additional_overlap_instance
    * per_process_application_connections

total_budgeted_peak_connections =
    api_steady_state_connections
    + api_incremental_rolling_overlap_connections
    + background_worker_connections
    + scheduler_or_job_runner_connections
    + migration_connections
    + monitoring_connections
    + reporting_or_support_connections
    + routine_human_access_connections
    + operational_reserve_connections

remaining_headroom =
    usable_provider_connection_capacity
    - total_budgeted_peak_connections
```

Final acceptance in `WS04-01D` requires:

```text
total_budgeted_peak_connections <= usable_provider_connection_capacity
remaining_headroom >= 0
```

This pass must prove the **calculation contract**, not production numbers.

`additional_rolling_overlap_api_instances` means the maximum number of
additional API instances or process groups that may coexist with the normal
steady-state maximum during a rolling deployment. It is additive above
`max_api_instances`. Steady-state instances must not be counted again in the
overlap term. If rolling overlap cannot occur, this value may be zero only when
evidence proves that no additional API instance or process group can coexist
with steady state during deployment.
`api_processes_per_additional_overlap_instance` is the process count for those
additional overlap instances or process groups; it is not a second count of the
steady-state processes.

Every numeric term used by the framework must be:

- a non-negative integer;
- traceable to an evidence source when populated for real verification;
- zero only when the evidence state proves the consumer does not exist or cannot
  consume production database connections;
- rejected when required source attribution is absent;
- handled consistently in total and headroom calculations.

Synthetic fixture values may be used in tests only to prove the arithmetic and
validation behavior. They must be unmistakably synthetic and must not be
recorded as production decisions.

### 2.4 Connection Consumers Are Exhaustively Classified

The framework must require explicit disposition for every material connection
consumer class:

- API application pools;
- additional rolling-deployment overlap beyond steady state;
- background workers;
- schedulers or job runners;
- migrations;
- monitoring connections;
- reporting or support connections;
- routine human access;
- operational reserve.

Future connection-producing consumers discovered after this pass must trigger
reassessment. The framework must not permit an unclassified consumer to be
silently omitted from a final budget.

### 2.5 Provider, Pooler, And Runtime Evidence Requirements Are Defined

Without selecting a provider, C must define what D will have to prove.

For direct PostgreSQL connections, D must eventually prove that all application,
migration, monitoring, support, human, and reserve demand fits usable provider
capacity.

For a provider pooler or proxy, D must eventually verify both:

- the client-side connection ceiling that applications and tools may open; and
- the server-side PostgreSQL capacity the pooler/proxy may consume.

The evidence contract must also require the selected mode to be compatible with
accepted application behavior, including:

- checkout-applied statement and lock timeouts;
- transaction semantics;
- migration execution;
- role identity;
- prepared-statement behavior where applicable;
- independent per-process engine creation;
- process-owned pool disposal on shutdown.

The framework must require actual runtime evidence for:

- maximum API instance count;
- process count per instance;
- autoscaling ceiling or evidence that autoscaling is disabled;
- additional rolling-deployment overlap beyond steady state or evidence that
  overlap cannot occur;
- deployed `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, and pool-wait timeout;
- application-versus-migration credential resolution;
- startup/shutdown connection behavior.

C defines these proof requirements. D supplies the facts.

### 2.6 Telemetry And Safe-Adjustment Contract Is Defined

The database-pool budget remains subject to the evidence-based limits method.
The framework must require the final budget evidence to identify, where
applicable:

- protected resource or failure mode;
- all enforcing layers;
- accountable owner;
- provider and platform constraints;
- expected workload and abuse risk;
- failure cost and recovery behavior;
- whether the value is configurable;
- boundary and multi-instance test evidence for the selected final values;
- pool utilization;
- connection errors;
- database outcome classes;
- API correlation;
- job correlation when jobs exist.

Dashboard and alert-threshold implementation remains with `WS09` where already
owned there. C must not claim those dashboards or alerts exist.

For every mutable capacity assumption that D relies on, the framework must
require:

- accountable owner;
- protected resource or failure mode;
- current enforcing layer;
- provider/platform constraint that bounds or motivates the value;
- expected workload, abuse risk, failure cost, and recovery behavior;
- configurability status;
- reassessment trigger;
- boundary and multi-instance evidence required for approval;
- safe adjustment or forward-fix action;
- rollback or abort condition where applicable;
- evidence required after the change before the new value can be trusted.

This applies at least to:

- application pool size and overflow;
- deployment instance/process ceilings;
- autoscaling;
- additional rolling overlap beyond steady state;
- provider plan/capacity assumptions;
- pooler/proxy mode.

### 2.7 Role And Grant Verification Contract Is Complete

C must define the role classes and least-privilege checks that D will apply to
the final production database.

The role model must distinguish each class that actually exists at D time:

- application runtime;
- migration execution;
- background worker or scheduler;
- read-only reporting or support;
- backup or restore database access when exposed as a role;
- routine human access;
- schema or object owner role.

The final verification contract must require inspection of:

- superuser;
- database ownership;
- schema ownership;
- `CREATEDB`;
- `CREATEROLE`;
- replication;
- `BYPASSRLS` where applicable;
- schema usage/create privileges;
- table privileges;
- sequence privileges;
- function privileges where application functions exist;
- default privileges for future tables and sequences;
- search path;
- effective application and migration roles;
- support/reporting/human access when present.

The application runtime role must eventually be proven not to be:

- superuser;
- database owner;
- schema owner;
- migration owner;
- role administrator;
- database creator;
- replication role;
- broad provider administrator;
- routinely DDL-capable.

Migration execution must eventually resolve to a distinct effective production
role from normal request-serving application traffic.

The framework must reject a final evidence record that claims least privilege
without addressing ownership, search path, default privileges, and role
attributes together.

### 2.8 `WS04-01D` Handoff Is Explicit

`WS04-01D - Final production PostgreSQL topology, connection budget, and role
verification` owns all facts that cannot exist until final infrastructure is
selected.

D must later populate and verify:

- actual production PostgreSQL provider/environment;
- provider total and usable connection capacity;
- provider-reserved or unavailable capacity;
- direct/pooler/proxy mode and compatibility;
- actual deployed steady-state instance/process/autoscaling topology and
  additional rolling-overlap topology;
- deployed pool values and wait timeout;
- every current connection consumer and reserve;
- final budgeted peak and remaining headroom;
- runtime observations needed by the budget;
- concrete production role identities through safe aliases;
- real grants, ownership, search path, default privileges, and operational
  database access;
- final telemetry-plan binding and safe-adjustment evidence.

D is mandatory before `CLOSE-01`. If final infrastructure becomes stable earlier,
D may run earlier.

C must not mark any D-owned production fact as proved.

### 2.9 Adjacent Work Remains With Existing Owners

This pass does not claim closure for:

- production query-plan quality or row-count performance;
- transaction invariants or deterministic concurrency;
- migration compatibility, interruption rehearsal, or online-index strategy;
- durable worker/job correctness;
- production dashboards or alert thresholds;
- backup, PITR, restore, or retention;
- provider-account MFA, recovery, rotation, revocation, or offboarding;
- final production sign-off or fresh 163-control reassessment.

The framework may name these as handoffs or inputs only when they materially
affect later database verification.

## 3. Design

### 3.1 Consume Accepted A/B Contracts Without Reopening Them

The implementation begins from accepted `WS04-01A` and `WS04-01B`.

C may inspect current source and accepted evidence to make the verification
framework accurate, but it must not redesign A/B behavior unless a real defect
forces routing back to Gate A or Stage 0 under the durable workflow.

The framework should consume these accepted A facts:

- production-like environments require explicit `DB_POOL_SIZE` and
  `DB_MAX_OVERFLOW`;
- one process can demand at most `DB_POOL_SIZE + DB_MAX_OVERFLOW` application
  connections;
- pool wait, statement timeout, and lock timeout are explicit;
- request sessions are scoped and cleaned up;
- shutdown disposes the application engine;
- Alembic uses `MIGRATION_DATABASE_URL` separately and `NullPool` online.

C consumes the accepted B database-access result without reopening route/query
implementation.

### 3.2 Build A Provider-Neutral Evidence Schema

Implement a deterministic, reviewable schema and validator for future D
evidence.

The Gate B implementation must create the canonical provider-neutral evidence
contract as a tracked JSON template at:

```text
docs/production-readiness/planning/passes/ws04/ws04-01c-production-database-evidence-contract.json
```

It must also create the local test support validator at:

```text
backend/tests/support/production_database_verification.py
```

The JSON template is the durable repository contract that `WS04-01D` will
populate later. The support validator is the deterministic test-facing checker
for required states, budget arithmetic, completeness, safe attribution,
sensitive-value rejection, role/grant coverage, telemetry, safe adjustment, and
the C/D provider-neutrality boundary.

The chosen shape must make these distinctions explicit:

- field required by the framework;
- field intentionally deferred to D;
- field verified with attributable evidence;
- field not applicable with reason;
- field blocked or stale.

The schema must support safe aliases and must make sensitive raw evidence
unnecessary in Git.

### 3.3 Implement Deterministic Budget Validation

Implement the minimum logic needed to prevent arithmetic and completeness drift.

Validation must be able to detect at least:

- missing required consumer categories;
- negative or non-integer terms;
- non-zero values without required source metadata;
- zero values without an accepted absence reason;
- incorrect per-process calculation;
- incorrect peak calculation;
- incorrect headroom calculation;
- over-capacity final fixtures;
- missing reserve;
- missing telemetry-plan fields;
- missing safe-adjustment fields for mutable capacity inputs;
- stale evidence state;
- provider-specific claims populated while the record is still in C/deferred
  state.

Tests should use synthetic fixture records for both passing and failing cases.

### 3.4 Define Runtime And Pooler Verification Checklist

The framework must provide a stable checklist or structured equivalent for D to
verify:

- provider capacity source;
- direct versus pooled/proxied mode;
- client/server connection ceilings where pooling/proxying exists;
- API instance/process ceiling;
- autoscaling;
- additional rolling overlap beyond steady state;
- deployed pool values;
- migration execution and credential separation;
- independent engine creation per process;
- shutdown pool release;
- safe synthetic observation boundaries.

The checklist must make unknown final values legal in C but unacceptable for a
completed D verification.

### 3.5 Define Role/Grant Verification Checklist

The framework must provide a stable role/grant inspection inventory for D.

Where useful, it may define safe read-only SQL query shapes or inspection
instructions that later collect role attributes, ownership, grants, search path,
and default privileges without embedding real role names or credentials in the
repository.

Any future denied-operation probe must remain non-destructive, isolated, or
transaction-rolled-back and must be separately authorized where required.

### 3.6 Preserve A Narrow Implementation Boundary

Normal C implementation should be limited to artifacts that establish and prove
the verification framework, such as:

- the `WS04-01C` stable requirement declaration;
- a provider-neutral topology/budget/role evidence schema or template;
- a small validator/checker when useful;
- focused tests with synthetic evidence fixtures;
- the C `TESTING_RECORD.md`;
- the execution-register update that records C acceptance and preserves the D
  handoff.

Production application source, migrations, database schema, provider settings,
deployment settings, credentials, and real production role/grant state should
not change merely to complete C.

If implementation discovers that the accepted A/B source contract itself must
change, route according to the durable workflow rather than hiding that change
inside the framework pass.

The expected C implementation artifacts are:

- `backend/tests/support/requirements/ws04_01c.json`;
- `backend/tests/support/production_database_verification.py`;
- `backend/tests/platform/production_database_verification/TESTING_RECORD.md`;
- focused tests under
  `backend/tests/platform/production_database_verification/`;
- `docs/production-readiness/planning/passes/ws04/ws04-01c-production-database-evidence-contract.json`;
- the canonical `WS04-01C` plan itself, if Gate A correction changed it;
- the execution register update needed to record C completion and keep
  `WS04-01D` mandatory.

The existing local workflow, Skill, custom-agent, governance, blueprint, intake,
and handoff-upload changes that predate this WS04-01C implementation are
approved carryover baseline for this branch. Gate B must preserve them and may
publish them at the same PR boundary, but must not count them as newly invented
WS04-01C implementation scope or use them to prove C-only requirements unless a
C test explicitly cites their current authority.

## 4. Failures And Edge Cases

1. **Temporary infrastructure is mistaken for production**
   - **Condition:** Neon, Render, Vercel, another temporary provider, a free-tier
     limit, a local setting, or a README/example value is proposed as final
     production evidence merely because it exists today.
   - **Required behavior:** Reject the claim. Keep the production field deferred
     to D or the applicable later infrastructure owner.

2. **Synthetic test values look like production decisions**
   - **Condition:** Fixture numbers are stored or described without an explicit
     synthetic/test-only classification.
   - **Required behavior:** Reject or relabel them so no future reviewer can
     mistake them for approved limits.

3. **A required consumer category is omitted**
   - **Condition:** A final-budget-shaped record lacks API steady-state,
     additional overlap, worker, scheduler/job, migration, monitoring,
     reporting/support, human, or reserve disposition.
   - **Required behavior:** Framework validation fails.

4. **Zero silently means unknown**
   - **Condition:** A consumer is set to zero without evidence that the consumer
     is absent or cannot connect.
   - **Required behavior:** Framework validation fails. Unknown is not zero.

5. **Budget arithmetic is inconsistent**
   - **Condition:** Per-process, peak, capacity, or headroom calculations do not
     recompute deterministically.
   - **Required behavior:** Validation fails.

6. **Production-like final fixture exceeds capacity**
   - **Condition:** A synthetic D-completion fixture has negative headroom or
     peak demand above usable capacity.
   - **Required behavior:** Validation fails and demonstrates the future D stop
     condition.

7. **Evidence has no attribution**
   - **Condition:** A populated final-evidence field lacks source type/date or
     required ownership/reviewer metadata.
   - **Required behavior:** Validation fails.

8. **Sensitive evidence enters the tracked artifact**
   - **Condition:** Credential-bearing URLs, secrets, private provider links,
     private identifiers, raw exports/screenshots/logs, IPs/private hostnames, or
     personal/payment data appear.
   - **Required behavior:** Reject before staging.

9. **Role verification ignores ownership or default privileges**
   - **Condition:** A record claims least privilege from table grants alone.
   - **Required behavior:** Validation/checklist remains incomplete.

10. **Application and migration role separation is not addressed**
    - **Condition:** A final D-shaped record does not distinguish the two
      effective roles.
    - **Required behavior:** Verification remains incomplete.

11. **Pooler mode is asserted without evidence**
    - **Condition:** Direct/pooler/proxy mode is inferred from a hostname,
      connection-string pattern, README, or provider marketing example.
    - **Required behavior:** Keep the field unverified/deferred.

12. **Telemetry requirement is reduced to a future dashboard TODO**
    - **Condition:** The budget contract omits the signals/correlation it will
      need because dashboard implementation belongs to WS09.
    - **Required behavior:** C fails. It must define the telemetry contract even
      though WS09 implements later dashboards/alerts.

13. **Safe adjustment path is missing**
    - **Condition:** A mutable capacity input can change but the final evidence
      shape has no owner, trigger, adjustment path, abort/rollback condition, or
      re-verification requirement.
    - **Required behavior:** Framework validation remains incomplete.

14. **D handoff becomes optional**
    - **Condition:** C wording could be read as closing final DB-002/DB-015
      provider evidence permanently.
    - **Required behavior:** Fail review. D must remain explicit and mandatory
      before final closeout.

15. **A downstream pass needs a D-owned fact early**
    - **Condition:** Later Stage 0/Gate A cannot design safely without actual
      production topology or grants.
    - **Required behavior:** That later pass stops on D or the specific external
      prerequisite. It must not substitute the C framework for real evidence.

## 5. Testing

### 5.1 Framework Schema Validation

Focused automated tests should verify that the evidence contract:

- contains every required topology/budget/role section;
- distinguishes deferred, verified, not-applicable, blocked, and stale states;
- permits D-owned production values to remain intentionally deferred in C;
- rejects a completed/final state when mandatory D evidence is absent;
- requires attribution for populated final evidence;
- requires a reason for not-applicable/zero consumers;
- requires purpose, supported control/pass, sanitized evidence reference, and
  raw-evidence location reference or explicit not-applicable reason;
- rejects prohibited sensitive-value patterns where deterministic checking is
  reasonable;
- preserves stable aliases without requiring real provider or role identifiers.

### 5.2 Budget Formula Validation

Synthetic fixtures must prove:

- `per_process_application_connections = DB_POOL_SIZE + DB_MAX_OVERFLOW`;
- steady-state API demand arithmetic;
- incremental rolling-overlap arithmetic without recounting steady-state
  instances;
- all non-API consumer terms are included;
- peak arithmetic;
- headroom arithmetic;
- zero headroom is allowed when all evidence is otherwise valid;
- negative headroom fails;
- negative/non-integer terms fail;
- missing source metadata fails for populated final values;
- zero-without-absence-evidence fails;
- missing reserve fails;
- unknown values cannot be silently coerced to zero.

The fixtures must be explicitly synthetic and must not be represented as
production recommendations.

### 5.3 Telemetry And Adjustment Validation

Tests or deterministic artifact checks should verify that mutable capacity
inputs require:

- owner;
- protected resource or failure mode;
- enforcing layers;
- provider/platform constraints;
- expected workload and abuse risk;
- failure cost and recovery behavior;
- configurability status;
- reassessment trigger;
- telemetry/evidence boundary;
- boundary and multi-instance test evidence;
- safe adjustment or forward-fix path;
- abort/rollback condition where applicable;
- post-change re-verification requirement.

The evidence contract must include pool utilization, connection errors,
database outcome classes, API correlation, and job correlation where applicable,
while leaving dashboard/alert implementation to WS09.

### 5.4 Role/Grant Contract Validation

Tests or structured checks should verify that a final D-shaped role record cannot
claim completion without disposition for:

- effective application role;
- effective migration role;
- role separation;
- superuser/owner/role-admin/database-create/replication attributes;
- schema ownership;
- schema privileges;
- table privileges;
- sequence privileges;
- function privileges where applicable;
- default privileges;
- search path;
- support/reporting/human/backup roles when present.

The framework should include negative fixtures showing why broad application DDL
or shared application/migration role evidence is unacceptable.

### 5.5 Compatibility Validation

C must rerun the accepted compatibility scopes that materially protect the
framework assumptions, especially:

- `WS04-01A` application database lifecycle/pool-setting evidence;
- accepted database timeout behavior;
- runtime lifecycle/shutdown compatibility;
- backend settings/environment-safety compatibility;
- `WS04-01B` evidence only when C implementation touches shared database-access
  inventories or contracts;
- focused and suite-level requirement/checker validation required by the current
  testing architecture.

Local tests prove the framework and its compatibility only. They do not prove
real provider capacity, real deployment topology, real production grants, or
real runtime behavior.

## 6. Done When

- [ ] The pass explicitly applies the program-wide final-infrastructure timing
      and provider-neutrality rule: final production infrastructure is not
      selected, temporary provider facts are not final production evidence, and
      provider-specific final values remain deferred.
- [ ] A provider-neutral sanitized topology/budget/role evidence contract exists
      and has deterministic validation where appropriate.
- [ ] The evidence contract carries EN-03 metadata: provider/control plane,
      environment, evidence date, reviewer, purpose, supported control/pass,
      source type, sanitized evidence reference, raw-evidence location reference
      when one exists outside Git, and open gaps or follow-up actions.
- [ ] The connection-budget formula and every required consumer category are
      defined without inventing final production values.
- [ ] The future final budget record is required to carry the full applicable
      FDN-04/DBP-01 limit basis: protected resource or failure mode, enforcing
      layers, owner, provider/platform constraints, expected workload and abuse
      risk, failure cost and recovery behavior, configurability, boundary and
      multi-instance tests, telemetry, rollback/safe-adjustment behavior, and
      reassessment triggers.
- [ ] Synthetic tests prove the budget arithmetic, headroom rules, completeness
      rules, and invalid-input behavior.
- [ ] Unknown and deferred values cannot be silently represented as zero.
- [ ] The evidence contract requires attribution, staleness handling, and safe
      evidence hygiene.
- [ ] The pooler/direct/runtime verification requirements needed by later D are
      explicit.
- [ ] The role/grant/search-path/default-privilege verification contract needed
      by later D is explicit.
- [ ] The budget telemetry-plan contract names the required signals and preserves
      WS09 ownership of dashboards/alert thresholds.
- [ ] Mutable capacity inputs require owner, reassessment trigger, safe
      adjustment/forward-fix path, abort/rollback condition where applicable,
      and post-change evidence.
- [ ] Accepted A/B behavior remains intact and required regression validation
      passes.
- [ ] No real provider capacity, deployment topology, production pool value,
      concrete production role/grant, or production-readiness claim is invented.
- [ ] The testing/evidence record states exactly what C proves and what remains
      unverified.
- [ ] `WS04-01D - Final production PostgreSQL topology, connection budget, and
      role verification` is recorded as the mandatory later owner of the final
      provider/runtime evidence.
- [ ] D's trigger is explicit: final production database and hosting/deployment
      topology selected, current launch connection consumers bounded, and safe
      sanitized evidence available.
- [ ] D is required before `CLOSE-01` and final production-readiness reassessment.
- [ ] The execution-register update preserves current program progression without
      treating D-owned facts as proved or the underlying DB-002/DB-015 evidence
      as closed.
