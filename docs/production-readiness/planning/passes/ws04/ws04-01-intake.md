# WS04-01 - Database engine/session lifecycle, connection budget, and least-privilege roles intake

## 1. What Needs To Be Decided

This intake decides how to execute the database-foundation work in `WS04-01`.
That decision matters because the parent combines application source behavior
that can be inspected and improved now with production database facts that are
not present in the repository.

`WS04-01` covers the way Pickup Lane opens and closes PostgreSQL connections,
manages SQLAlchemy sessions, bounds connection waiting and pool growth, accounts
for the deployment-wide connection budget, and verifies least-privilege database
roles. It also includes the database-access review work assigned to the parent
for query and cursor behavior.

The execution shape must separate work that can be completed from current
source from work that requires sanitized production-provider and deployment
evidence. It must also avoid creating dependencies between source-owned work
areas that do not technically depend on each other.

## 2. What We Know

This section contains only the current facts, decisions, dependencies, and
unknowns that affect how `WS04-01` should be executed. Each item explains why it
changes the execution decision.

| Topic | Current fact or constraint | Why it affects execution |
|---|---|---|
| Approved budget direction | `DBP-01 / DB-002` approves one deployment-wide PostgreSQL connection budget with reserve. Exact values still depend on provider limits and deployment topology. | The budget method is decided, but the final numeric budget cannot be honestly selected from repository source alone. |
| Current application database source | `backend/database.py` has one imported SQLAlchemy engine, per-request `SessionLocal`, rollback on request failure, session close in all cases, a database health probe, checkout-applied statement and lock timeouts, and shutdown disposal through `backend/main.py`. | Application lifecycle and session behavior are source-owned and can be reviewed without production provider facts. |
| Current database settings | `backend/settings.py` validates `DATABASE_URL`, enforces the dedicated test database name in test and CI, rejects unsafe production-like database URLs, and exposes database wait, statement, and lock timeout settings. Current source does not contain approved pool-size or overflow values. | Source configuration can define and test application-owned database boundaries without selecting unverified production capacity values. |
| Alembic connection behavior | `backend/alembic/env.py` uses the configured database URL and `NullPool` for online migrations. Repository source does not prove which production credential or role will run migrations. | Application and migration credential boundaries can be handled in source, while concrete production roles and grants require external evidence. |
| Accepted prerequisite evidence | Accepted WS02 runtime and timeout work already covers application startup/shutdown shape, health behavior, environment validation, database pool wait timeout, statement timeout, and lock timeout at the source level. | `WS04-01A` can build on that accepted behavior instead of reopening it. |
| Production PostgreSQL and deployment facts | Governance records identify Neon/PostgreSQL as the intended durable database provider, but provider connection limits, pooler/proxy mode, deployed instance count, process count, rolling overlap, monitoring consumption, role grants, and human access are not yet evidenced. | Final connection-budget and least-privilege production verification requires a separate evidence-backed result. |
| Query and cursor obligations | The parent owns database-access work for current query, pagination, and cursor behavior, including the `DB-012` and `DB-013` concerns. | This work has its own source surface and can be reviewed independently of application engine/session changes and production provider verification. |
| Neighboring work | `WS04-02` owns transaction invariants, locks, and deterministic concurrency. `WS04-03` owns migration policy and production-like migration rehearsal. `WS05` owns durable worker/job behavior. `WS09` owns durable telemetry and alerting. `WS10` owns broad provider-access, rotation, revocation, and offboarding evidence. | `WS04-01` must preserve these boundaries instead of absorbing adjacent database, worker, observability, or provider-access work. |

## 3. Execution Decision

This section defines the executable shape of `WS04-01` and explains why the
parent should be divided this way.

The chosen execution shape is a split parent.

The parent contains three coherent results:

1. application database lifecycle and configuration behavior;
2. query, cursor, and database-access behavior;
3. production database topology, connection-budget, and role verification.

The first two are independent source-owned work areas. Neither requires the
other to be completed first. The production verification work depends on both
source-owned areas being settled and on sanitized production-provider and
deployment evidence.

| Order | Work | Depends on |
|---|---|---|
| `1` | `WS04-01A - Application database lifecycle, pool settings, and role-credential boundaries` | Accepted WS02 runtime and timeout foundation |
| `1` | `WS04-01B - Query, cursor, and database-access behavior` | Current source and applicable accepted database-access decisions |
| `2` | `WS04-01C - Production PostgreSQL topology, connection budget, and role verification` | Accepted `WS04-01A`, accepted `WS04-01B`, and sanitized production-provider and deployment evidence |

`WS04-01A` leaves a coherent application-side result: the repository defines
the application database lifecycle, bounded pool configuration, session
behavior, and application-versus-migration credential boundaries without
claiming production facts the source cannot establish.

`WS04-01B` leaves a coherent database-access result: current query, pagination,
cursor, and related database-access behavior is reviewed and corrected against
its own source and requirements.

Neither result requires the other in order to be correct and independently
accepted.

`WS04-01C` combines the accepted source behavior with real production facts to
establish the deployment-wide connection budget and verify the concrete
production role and privilege model.

Keeping all three in one executable pass would mix source implementation and
review with external production verification that has different prerequisites.
Splitting them preserves those boundaries without creating an artificial
dependency between the two source-owned children.

## 4. Where The Parent Work Goes

This section accounts for the complete `WS04-01` scope. It shows where each
major responsibility belongs so the split does not lose work or assign the same
engineering responsibility to multiple children.

| Parent work | Goes to | Remaining boundary |
|---|---|---|
| SQLAlchemy engine lifecycle, request session scope, rollback/close behavior, shutdown disposal, and database health-query boundaries | `WS04-01A` | Production process topology and provider-side connection limits are outside this source-owned work. |
| Source-owned database settings for connection waiting, pool sizing/overflow, and safe environment use | `WS04-01A` | Concrete production values are outside this source-owned work. Accepted WS02 timeout behavior remains a prerequisite. |
| Application and migration credential boundaries | `WS04-01A` | Concrete production roles, grants, schema ownership, and operational access are outside this source-owned work; broader provider-account access lifecycle remains with `WS10`. |
| Current query, pagination, cursor, and database-access behavior assigned to `DB-012` and `DB-013` | `WS04-01B` | Production telemetry and long-term observability remain with `WS09` where they are not required by this parent. |
| Deployment-wide PostgreSQL connection budget and reserve calculation | `WS04-01C` | The calculation must use actual provider and deployment facts rather than local defaults or examples. |
| PostgreSQL/Neon provider limits, pooler/proxy mode, deployed instance and process counts, rolling overlap, migration allowance, monitoring allowance, and operational reserve | `WS04-01C` | These are production facts and require sanitized provider or runtime evidence. |
| Production application, migration, support, reporting, and human-access database roles and grants | `WS04-01C` | Provider-user MFA, recovery, rotation, revocation, offboarding, and broader account-access lifecycle remain with `WS10`. |
| Transaction invariants, explicit locking, deterministic concurrency, and external-side-effect transaction boundaries | `WS04-02` | Session lifecycle owned by `WS04-01A` does not absorb business invariants or concurrency design. |
| Migration compatibility policy, interruption/rehearsal behavior, online-index strategy, and production-like migration execution | `WS04-03` | `WS04-01A` owns only the database connection and credential boundary relevant to application-versus-migration access. |
| Durable worker/job design | `WS05` | Any worker database consumption that exists in the actual production deployment is included when `WS04-01C` calculates the real connection budget. |

## 5. What Happens Next

This section identifies which engineering work is ready to begin and whether any
technical prerequisite prevents it.

`WS04-01A` and `WS04-01B` are both technically ready for their engineering-plan
stage.

`WS04-01A` has the current application database source, accepted WS02 runtime
and timeout behavior, and approved connection-budget direction required to
design its application-owned database work.

`WS04-01B` has the current query, pagination, cursor, and database-access source
plus the applicable accepted requirements required to design its work. It does
not depend on `WS04-01A` being completed first.

`WS04-01C` is not yet executable because it requires accepted results from both
source-owned children and sanitized production-provider and deployment evidence.

For the current execution sequence, `WS04-01A` is the next selected child.
Nothing in the known technical state blocks its engineering-plan work.

## 6. Internal Record

This section preserves the production-readiness routing and bookkeeping needed
to freeze the intake decision. It records the exact process state without
mixing that information into the engineering explanation above.

| Detail | Value |
|---|---|
| Parent pass | `WS04-01 - Database engine/session lifecycle, connection budget, and least-privilege roles` |
| Intake outcome | Split parent into three executable children |
| Accepted baseline | `08ce291e8322461ca8a32c4ce3cdc07ba97b4172` |
| Intake path | `docs/production-readiness/planning/passes/ws04/ws04-01-intake.md` |
| Authority sources | `00-READ-ME-FIRST.md`; `01-PROGRAM-CONTEXT.md`; `PASS-IMPLEMENTATION-WORKFLOW.md`; `PASS-INTAKE-TEMPLATE.md`; `PASS-EXECUTION-REGISTER.md`; master blueprint; final remediation plan; `DBP-01 / DB-002`; `FDN-04 / GOV-006`; provider, ownership, evidence, and limits governance records; current `backend/database.py`, `backend/settings.py`, `backend/main.py`, and `backend/alembic/env.py` |
| Execution-register state | `WS04-01` is not yet selected in the accepted register and requires intake before implementation |
| Approved decisions and prerequisites | `DBP-01 / DB-002` budget direction approved; `FDN-04 / GOV-006` evidence-based limits method approved; accepted WS02 runtime and timeout foundation available |
| Child dependency shape | `WS04-01A + WS04-01B -> WS04-01C` |
| Current selected child | `WS04-01A` |
| Proposed canonical plan path | `docs/production-readiness/planning/passes/ws04/ws04-01a-application-database-lifecycle-pool-settings-role-credential-boundaries.md` |
| Proposed requirement declaration | `backend/tests/support/requirements/ws04_01a.json` |
| Proposed trusted test or verification location | `backend/tests/workflows/application_database_lifecycle_pool_settings_role_credential_boundaries` |
| Blockers | None for `WS04-01A` or `WS04-01B`; `WS04-01C` requires accepted `WS04-01A`, accepted `WS04-01B`, and sanitized production-provider and deployment evidence |
| Exact next allowed action | Human review and approval of this intake path and SHA, then Gate A for `WS04-01A` only |