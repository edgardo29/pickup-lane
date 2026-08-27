# WS04-03A - Provider-Independent Migration Policy, Compatibility, Graph/Drift Checks, And Controlled Rehearsal

This pass makes Pickup Lane's repository-owned migration safety rules executable without depending on final production database provider or runtime facts.

This document is the engineering blueprint for the pass.

## 1. What This Work Does

This pass establishes the provider-independent part of `WS04-03 - Migration policy, compatibility, interruption, and production-like rehearsal`.

The work covers:

- migration policy and expand/contract rules for repository-owned schema changes;
- old/new application and schema compatibility expectations;
- Alembic graph, dependency, multiple-head, and drift verification;
- empty-database and prior-schema upgrade behavior;
- provider-independent locking, timeout, duration, interruption, resume, rollback, and forward-fix behavior;
- controlled PostgreSQL migration rehearsal using repository-owned or synthetic fixtures;
- trusted migration evidence under `backend/tests/migrations/`;
- accepted-state recording that keeps the mandatory final-provider follow-up open.

The current repository has a 59-file Alembic chain under `backend/alembic/versions/`, from `0001_enable_pg_trgm_extension.py` through `0059_create_admin_review_case_events_table.py`. Current source inspection shows one linear chain with one base and one head. Current upgrade-side migrations are ordinary schema creation plus fixed extension and sequence setup; current inspection did not find upgrade-side destructive drops, renames, alters, backfills, data rewrites, concurrent-index directives, `NOT VALID`, or `VALIDATE` flows.

Gate B must verify current repository truth again before relying on it. If the current migration chain has changed, the implementation must reconcile the plan against the changed truth instead of relying on the Stage 0 snapshot.

Provider-independent runtime migration rehearsal uses a dedicated PostgreSQL migration test database separate from the ordinary backend application test database. This separation allows migration tests to control complete schema-history state without weakening or interfering with the existing backend test-database safety model.

This pass does not select final production infrastructure and does not use Vercel, Render, Neon, local PostgreSQL, CI PostgreSQL, or demo infrastructure as final production evidence.

`WS04-03B - Final provider/runtime migration rehearsal and rollout evidence` remains deferred. It owns final provider/runtime migration ceilings, production-equivalent volume, final migration runner behavior, final rolling-overlap topology, final provider lock/runtime behavior, and final rollout evidence after production infrastructure is selected.

## 2. What Must Be True

The requirements below define the finished behavior for this provider-independent child. They are current-source and controlled-rehearsal requirements, not final production-provider claims.

### 2.1 Migration Policy Is Explicit And Enforceable

The backend must contain a compact, side-effect-free migration safety policy contract at `backend/services/database_migration_safety_policy.py`.

The contract must reconcile the current pre-production clean-rebuild development rule with the production-readiness migration rules that become mandatory once production data must be preserved.

It must cover:

- current pre-production migration editing expectations;
- the point where migrations become immutable production history;
- expand/contract sequencing for future incompatible schema changes;
- compatibility-window expectations for old and new application versions;
- online-index and blocking-DDL rules;
- migration timeout, interruption, resume, rollback, and forward-fix expectations;
- data migration and backfill classification;
- allowed provider-independent proof versus deferred final provider/runtime proof;
- the owner boundary for `WS04-01D`, `WS04-03B`, `WS05`, `WS09`, and `WS10`.

The contract must not open database connections, inspect live provider state, read final-provider settings, or perform runtime migration execution.

### 2.2 Migration Operations Are Classified And Fail Closed

Current and future migrations must be classified so risky operations cannot enter silently.

The classification must account for at least:

- extension setup;
- sequence setup;
- table creation;
- ordinary indexes and unique indexes;
- check constraints, foreign keys, and server defaults;
- raw SQL expressions;
- data updates, inserts, deletes, and backfills;
- table or column drops;
- table or column renames;
- column type changes;
- concurrent index operations;
- `NOT VALID` and `VALIDATE CONSTRAINT` flows;
- special transaction behavior;
- dynamic SQL construction.

For the current 59-migration chain, the implementation must produce a deterministic current inventory and prove that upgrade-side destructive or special-operation patterns are either absent or explicitly classified. The check must fail closed if a future migration introduces an unclassified risky operation.

### 2.3 Alembic Graph And Drift Checks Are Trusted Evidence

The repository must have trusted tests that verify the Alembic graph and model/schema agreement.

The tests must prove:

- there is one expected base and one expected head unless a future reviewed merge-revision design explicitly allows more;
- each revision file has valid `revision`, `down_revision`, `branch_labels`, and `depends_on` metadata;
- there are no duplicate, missing, orphaned, or unexpectedly branched revisions;
- Alembic can resolve heads from the repository configuration;
- model metadata imports correctly for migration comparison;
- drift detection is executed in the trusted test surface, not inferred from CI intent alone.

If graph or drift verification discovers a real current mismatch, Gate B may make the narrow source or migration correction required by current repository truth. If the correct fix changes the accepted WS04-03A/WS04-03B split or requires final production facts, it must return to Stage 0 or stop on the owning dependency.

### 2.4 Empty-Database And Prior-Schema Upgrades Are Proved

Provider-independent upgrade proof must cover both a clean empty database state and a controlled prior-schema state.

Runtime migration rehearsal must use a dedicated PostgreSQL database named `pickup_lane_migration_test_db`.

The existing `pickup_lane_test_db` remains the dedicated database for ordinary backend tests. Migration lifecycle tests must not destructively manipulate that database.

In test and CI environments:

- `DATABASE_URL` must continue to identify exactly `pickup_lane_test_db`;
- `MIGRATION_DATABASE_URL` used by migration lifecycle tests must identify exactly `pickup_lane_migration_test_db`;
- both databases must use the same approved PostgreSQL test host and port so the existing external-network safety boundary remains intact;
- no developer, demo, staging, production, or arbitrary database may be substituted for either purpose.

The migration test database is exclusively owned by migration testing and may be destructively reset only after its exact identity and test environment have been validated.

For migration rehearsal, an empty state means that migration-created schema objects, Alembic version state, and database-level objects relevant to the migration chain have been reset so first-run migration behavior is actually exercised rather than hidden by state from an earlier test.

The empty-database path must prove that the current Alembic chain can upgrade from that clean state to the current head.

The prior-schema path must prove that the dedicated migration test database at a controlled prior revision can upgrade to the current head. The prior state must be built from repository-owned migrations. This is upgrade-path evidence only; it must not claim that downgrade scripts are the primary production recovery strategy.

Migration tests must serialize destructive use of the dedicated migration test database and restore it to a known state after successful, failed, or interrupted rehearsal.

Local and CI test setup must provision the dedicated migration test database explicitly. The migration suite must fail safely if that database is missing or incorrectly configured rather than falling back to the ordinary application test database.

The tests must not depend on external provider state.

### 2.5 Old/New Application Compatibility Rules Are Testable

The migration policy must prevent a migration from breaking the compatibility window between old application code, new application code, old schema, and new schema.

For this pass, provider-independent compatibility means:

- a migration that removes, renames, or changes a currently used table, column, status, default, enum-like value, constraint, or index behavior must be split into reviewed expand/contract steps;
- an expansion step must be compatible with the currently accepted application until all deployed readers/writers are moved;
- a contraction step must not run until the old application behavior is no longer live;
- compatibility declarations must explain how old and new application versions tolerate the schema at each step;
- tests must fail closed when a migration introduces an incompatible one-step change without a declaration and proof.

The pass must not invent final rolling-deployment topology or provider-specific overlap timing. Those facts remain with `WS04-03B` and the later deployment/operations work that supplies final runtime evidence.

### 2.6 Locking, Timeout, Duration, Interruption, Resume, Rollback, And Forward-Fix Behavior Are Covered Provider-Independently

The migration safety contract and tests must cover the behavior that can be proved in controlled PostgreSQL without final infrastructure.

The proof must include:

- migration execution uses bounded database connections and does not depend on the application request pool;
- blocking and long-running migration risks are classified before merge;
- provider-independent timeout behavior is configured or tested with explicit local/test values;
- interrupted migration attempts leave the database in a known recoverable state;
- rerunning the migration path after an interruption either resumes safely or fails with a clear reviewed repair path;
- rollback use is limited to reviewed local/test recovery proof and is not treated as the primary production recovery strategy for destructive or data-affecting migrations;
- forward-fix is the preferred production recovery posture when production data may be affected.

Numeric production migration ceilings, production lock-duration limits, final provider timeout semantics, final migration runner behavior, and production-equivalent volume measurements remain deferred to `WS04-03B`.

### 2.7 Controlled Migration Rehearsal Produces Repository-Owned Evidence

The pass must create a controlled rehearsal surface under `backend/tests/migrations/`.

The rehearsal must use repository-owned migrations and synthetic or repository-owned fixtures against the dedicated migration test database to prove the current provider-independent migration contract. It must cover:

- current-chain upgrade from empty database;
- controlled prior-schema upgrade to head;
- graph and drift verification;
- classification of current migration operations;
- interruption and rerun behavior for representative migration execution;
- compatibility policy behavior for representative safe and unsafe changes;
- sanitized duration and operation observations that are useful for later production planning without claiming final provider/runtime facts.

Because the current repository does not contain a current large data migration, the pass does not need to invent a production-scale data backfill. It must still define the policy and fail-closed tests that future data migrations must satisfy before they can merge.

### 2.8 Accepted Database Contracts And Later-Owned Boundaries Remain Intact

The pass must preserve the accepted contracts from `WS04-01A`, `WS04-01B`, `WS04-01C`, `WS04-02A`, `WS04-02B`, and `WS04-02C`.

The new migration-test database boundary is additive and purpose-specific. It must not weaken the existing rule that ordinary backend tests use only `pickup_lane_test_db`, and it must not broaden backend test network access beyond the approved PostgreSQL test host and port.

It must not:

- weaken request-session rollback/close behavior, pool settings, timeout settings, role/credential boundaries, query/cursor behavior, transaction checkpoints, provider unknown-outcome handling, database invariants, row locks, deterministic concurrency proof, value/default compatibility, or SQL-safety rules;
- allow ordinary backend tests to use `pickup_lane_migration_test_db`;
- allow migration lifecycle tests to fall back to or destructively manipulate `pickup_lane_test_db`;
- broaden test database validation to arbitrary database names;
- broaden the existing external-network safety boundary;
- change current product state machines, payment/provider lifecycle behavior, durable job behavior, deployed logging, dashboards, alerts, backup/PITR behavior, restore exercises, or final production topology;
- claim final PostgreSQL provider behavior, production migration runtime ceilings, final production role/grant behavior, production-equivalent volume, final deployment topology, final migration runner behavior, or final rollout evidence;
- absorb work owned by `WS04-01D`, `WS04-03B`, `WS05`, `WS09`, or `WS10`.

## 3. Design

The design turns migration safety into a declared policy plus trusted tests. Gate B should make narrow source corrections only if current repository truth violates the contract below.

### 3.1 Add A Migration Safety Contract

Introduce `backend/services/database_migration_safety_policy.py` as a declarative contract for migration safety.

The contract should be readable by tests and humans. It should identify each migration-safety family, the requirements it supports, the accepted repository-owned mechanism, and any later owner for final-provider or operational evidence.

At minimum, include these families:

- development versus production migration history rules;
- expand/contract migration sequencing;
- compatibility-window expectations;
- operation classification and risky-operation handling;
- Alembic graph and drift verification;
- empty-database and prior-schema upgrade proof;
- timeout, lock, duration, interruption, resume, rollback, and forward-fix behavior;
- controlled rehearsal evidence;
- deferred final provider/runtime rehearsal.

The contract must be deterministic and side-effect free.

### 3.2 Create Trusted Migration Evidence Under `backend/tests/migrations/`

Create the trusted migration test root reserved by `backend/tests/README.md`.

The focused scope for this pass should be:

`backend/tests/migrations/migration_policy_compatibility_rehearsal/`

Tests in that scope should verify the policy contract and the current migration chain with real PostgreSQL where runtime behavior matters. Static checks are acceptable only for source and migration-inventory properties that do not require database execution.

The tests should avoid `backend/tests/legacy/` and must not use final provider infrastructure.

Runtime migration tests require a dedicated database lifecycle separate from ordinary backend integration tests.

The test-safety architecture must therefore distinguish two explicit database purposes:

- `pickup_lane_test_db` for ordinary backend application tests through `DATABASE_URL`;
- `pickup_lane_migration_test_db` for migration lifecycle tests through `MIGRATION_DATABASE_URL`.

The existing exact-name application-test validation must remain intact. Add a separate migration-test validation path rather than changing the ordinary validator to accept arbitrary additional names.

Migration-test validation must fail before any destructive operation unless all of the following are true:

- the environment is test or CI;
- the migration URL uses PostgreSQL;
- the database name is exactly `pickup_lane_migration_test_db`;
- the ordinary application database remains exactly `pickup_lane_test_db`;
- the migration and application databases resolve to the same approved PostgreSQL host and port;
- neither URL points at a developer, demo, staging, production, or unknown database.

The backend test harness should identify migration lifecycle tests with a dedicated marker or equivalent explicit test classification. Those tests must bypass the ordinary application-table cleanup fixture because they do not own `pickup_lane_test_db`.

The existing `no_db_cleanup` marker must retain its current meaning and must not be repurposed for migration tests that intentionally access PostgreSQL.

Migration lifecycle tests must have their own fixture or support layer that owns `pickup_lane_migration_test_db`.

That support layer must:

- validate the migration database identity before connecting or resetting state;
- acquire a migration-database advisory lock before destructive reset or migration execution so parallel workers or overlapping test runs cannot manipulate the migration database concurrently;
- establish the database state required by the current scenario;
- run Alembic using `MIGRATION_DATABASE_URL` rather than the application request engine;
- preserve Alembic's existing separation from the application request pool;
- clean or reset the dedicated migration database after successful and failed scenarios;
- release the advisory lock only after cleanup has completed or the failure state has been made explicit.

The reset path must be safe specifically because the migration database contains no application-test or development data. It must still fail closed on the database identity before destructive SQL is executed.

The reset implementation must remove migration-created schema state, Alembic version state, and any migration-created database-level objects necessary to reproduce a genuine first-run migration state.

Database-level operations such as extension creation must remain part of migration classification. If future migrations introduce database-level objects that the reset mechanism does not understand, the migration tests must fail closed until reset support and corresponding proof are updated.

The dedicated migration database must be provisioned deterministically in CI before migration tests run. Local backend-test setup must provide an explicit, documented way to provision the same database. The test suite must never silently create or substitute a differently named database when the expected migration database is absent.

### 3.3 Build A Current Migration Inventory

Gate B must derive the current migration inventory from source rather than hard-code the Stage 0 snapshot.

The inventory should include:

- every revision file under `backend/alembic/versions/`;
- revision graph metadata;
- upgrade operation categories;
- downgrade operation categories, clearly separated from upgrade proof;
- raw SQL expressions;
- extension and sequence operations;
- index and constraint patterns;
- data-affecting operations;
- unclassified risky patterns.

The inventory tests should assert the current chain shape and fail closed if new unreviewed risky operations appear.

### 3.4 Prove Graph, Heads, And Drift

Gate B must add tests or helpers that run the repository's Alembic configuration against the dedicated migration test database.

The proof should cover:

- Alembic can resolve the current script directory and head revision;
- the graph has no unexpected multiple heads or missing dependencies;
- the dedicated migration database can be reset to an empty migration state and upgraded to head;
- model metadata and migrations do not show unexpected drift after upgrade;
- drift verification is part of trusted test evidence rather than an informal local command.

If the repository's current Alembic or SQLAlchemy version makes a specific drift-check command unavailable, Gate B may implement an equivalent trusted drift comparison. The fallback must still prove model/schema agreement rather than simply skipping drift evidence.

### 3.5 Prove Empty And Prior-Schema Upgrade Paths

Gate B must use the dedicated migration test database to prove:

- upgrade from a clean empty migration state to current head;
- upgrade from a controlled prior revision to current head;
- rerunning upgrade-to-head against an already-upgraded database is safe;
- failed or interrupted rehearsal state is reset before another migration scenario can use the database.

Each schema-history scenario must run while holding the migration-database serialization lock.

The prior-schema proof must build the prior state from repository-owned migrations. It must not use the ordinary application test database and must not claim production rollback readiness merely because a downgrade command can build or inspect a test fixture.

### 3.6 Prove Compatibility And Interruption With Controlled Fixtures

Gate B must add controlled fixtures or test-only examples that exercise the policy for both safe and unsafe migration shapes.

The tests should prove that the policy accepts compatible expand/contract shapes and rejects unsafe one-step changes such as:

- dropping a currently used column;
- renaming a currently used table or column;
- changing a column type in a way the current application cannot tolerate;
- adding a non-null requirement without an expansion path;
- introducing a data rewrite or backfill without batching, interruption, resume, and verification behavior;
- adding blocking or special transaction behavior without an explicit reviewed classification.

The interruption proof must run against the dedicated migration test database.

It should show that a controlled migration run interrupted at a known point leaves a deterministic inspectable state and that the next run either completes safely or fails with a deterministic repair path.

After the interruption scenario has been observed, the migration test fixture must be able to restore the dedicated migration database to a known state for subsequent tests.

### 3.7 Keep Final-Provider And Later-Program Boundaries Explicit

Gate B must update documentation or testing records only enough to make the boundary testable.

The pass may say that final provider/runtime facts are missing and deferred. It must not invent:

- final production database/provider behavior;
- final production migration runtime ceilings;
- final deployment or rolling-overlap topology;
- final migration runner;
- production-equivalent volume;
- final provider lock/runtime behavior;
- final rollout evidence.

The execution-register update for this pass should record that `WS04-03A` becomes accepted on merge, `WS04-03B` remains a mandatory deferred follow-up, and `WS04-03` remains incomplete until `WS04-03B` is accepted or otherwise resolved by durable authority.

## 4. Failures And Edge Cases

These cases define the boundaries that matter for migration safety.

1. **The Alembic graph has multiple heads, missing links, or invalid metadata**
   - **Condition:** Current source contains unexpected branch heads, missing revision files, duplicate revisions, invalid dependencies, or metadata that Alembic cannot resolve.
   - **Required behavior:** Stop or correct the graph narrowly. Do not proceed with migration proof from an ambiguous graph.

2. **Model/schema drift exists after upgrade**
   - **Condition:** The dedicated migration test database upgraded to head does not match current SQLAlchemy metadata for the repository-owned schema surface.
   - **Required behavior:** Correct the model or migration mismatch in the narrowest current-source way, or return to Gate A if the fix changes the design.

3. **A migration contains an unclassified risky operation**
   - **Condition:** Current or future migrations include drop, rename, type change, backfill, data rewrite, concurrent index, `NOT VALID`, `VALIDATE`, dynamic SQL, or special transaction behavior without an explicit classification.
   - **Required behavior:** Fail closed until the operation is classified and its proof is added, or route to the owning later pass if provider/runtime facts are required.

4. **A migration would break old/new application compatibility**
   - **Condition:** A schema change removes or changes behavior needed by the accepted current application before the compatibility window is complete.
   - **Required behavior:** Split into expand/contract steps or stop for Gate A redesign.

5. **Empty or prior-schema upgrade fails**
   - **Condition:** The dedicated migration test database cannot upgrade from a clean empty state or controlled prior revision to current head.
   - **Required behavior:** Correct the current migration path or stop on a material design problem.

6. **An interrupted rehearsal leaves an unclear state**
   - **Condition:** A controlled interrupted migration run leaves the dedicated migration test database in a state that cannot be safely inspected, resumed, retried, reset, or forward-fixed.
   - **Required behavior:** Correct the migration policy or rehearsal design before Gate C.

7. **Rollback is treated as the production recovery plan**
   - **Condition:** Documentation or tests imply that destructive downgrades are the primary production recovery method.
   - **Required behavior:** Correct the policy to prefer forward-fix for production data and reserve downgrade behavior for reviewed local/test recovery proof.

8. **Provider-specific facts are required**
   - **Condition:** Correct completion requires final provider lock behavior, final runtime ceilings, final migration runner behavior, production-equivalent volume, final rolling-overlap topology, or final rollout evidence.
   - **Required behavior:** Stop and preserve that work for `WS04-03B` instead of expanding WS04-03A.

9. **A required correction crosses into another owner**
   - **Condition:** Completion requires final database topology/roles, durable jobs, payment/provider reconciliation, deployed observability, dashboards, alerts, backup/PITR, restore exercises, or incident operations.
   - **Required behavior:** Route to `WS04-01D`, `WS05`, `WS09`, or `WS10` instead of absorbing the work.

10. **The migration test database target is unsafe or ambiguous**
    - **Condition:** `MIGRATION_DATABASE_URL` is missing for a migration lifecycle test, points to `pickup_lane_test_db`, uses another database name, uses another host or port, or otherwise fails the migration-test safety contract.
    - **Required behavior:** Fail before connecting for destructive migration setup or executing reset SQL. Never fall back to the application test database or another available PostgreSQL database.

11. **Migration test cleanup cannot restore a known state**
    - **Condition:** A migration scenario fails or is interrupted and the dedicated migration test database cannot be safely reset for the next scenario.
    - **Required behavior:** Fail the migration test run and preserve the failure information needed for diagnosis. Do not continue executing later migration lifecycle tests against unknown residual state.

## 5. Testing

Testing must prove migration safety against current repository truth and controlled PostgreSQL behavior. It must not rely on historical audit assumptions, CI intent alone, final provider infrastructure, or legacy tests.

### 5.1 Migration Policy Contract Tests

Create tests that load `backend/services/database_migration_safety_policy.py` and prove:

- every policy family is present;
- every family maps to stable `WS04-03A` requirements;
- accepted mechanisms and deferred owners are explicit;
- final-provider facts are marked deferred rather than claimed;
- the contract is side-effect free.

### 5.2 Migration Inventory And Graph Tests

Create tests that inspect `backend/alembic/versions/` and the Alembic script directory to prove:

- every current revision file is accounted for;
- the current graph is linear unless a future reviewed merge-revision policy changes that expectation;
- exactly one current head is expected;
- no current upgrade-side destructive or special-operation pattern appears without classification;
- raw SQL expressions in migrations are fixed and reviewed for the migration-safety scope;
- operation inventory output is deterministic enough to review when migrations change.

### 5.3 Empty, Prior-Schema, Drift, And Migration-Database Safety Tests

Create PostgreSQL tests under `backend/tests/migrations/migration_policy_compatibility_rehearsal/` that prove:

- ordinary backend tests remain bound to `pickup_lane_test_db`;
- migration lifecycle tests are bound to `pickup_lane_migration_test_db`;
- migration lifecycle tests reject missing, incorrectly named, or unsafe migration database targets before destructive setup;
- the application and migration test databases use the same approved PostgreSQL test host and port;
- migration lifecycle tests do not run the ordinary application-table cleanup fixture;
- concurrent migration lifecycle tests are serialized against the dedicated migration database;
- the migration database can be reset to a genuine empty migration state;
- empty database upgrade to head succeeds;
- controlled prior-schema upgrade to head succeeds;
- upgrade-to-head is safe to rerun on an already-upgraded migration database;
- drift verification runs against the upgraded migration database and current model metadata;
- failed and interrupted scenarios are cleaned up or cause the migration test run to stop before later scenarios execute;
- the ordinary application test database remains untouched by migration lifecycle setup and reset.

These tests may use repository-owned helper fixtures. They must not use developer, demo, provider, staging, or production databases as evidence.

### 5.4 Compatibility, Interruption, And Rehearsal Tests

Create controlled tests that prove:

- compatible expand/contract examples pass the policy;
- unsafe one-step changes fail the policy;
- data-affecting migrations require batching, interruption, resume, and verification design before merge;
- representative interruption behavior leaves a deterministic recoverable test state;
- retry or resume behavior is deterministic;
- migration test cleanup restores a known state after the interruption scenario;
- rehearsal evidence records provider-independent observations without claiming final production runtime facts.

### 5.5 Compatibility With Accepted Database Work

Run the accepted compatibility scopes that could realistically regress from this pass:

- `backend/tests/workflows/application_database_lifecycle_pool_settings_role_credential_boundaries/`;
- `backend/tests/workflows/query_cursor_database_access_behavior/`;
- `backend/tests/platform/production_database_verification/`;
- `backend/tests/workflows/transaction_boundary_external_side_effect_safety/`;
- `backend/tests/workflows/database_invariants_locks_deterministic_concurrency/`;
- `backend/tests/workflows/database_value_default_sql_safety_compatibility/`;
- applicable backend settings and environment-safety tests affected by the dedicated migration-test database validation;
- any focused route, model, or service tests affected by narrow migration-policy corrections.

### 5.6 Requirement Declaration And Testing Record

Gate B must add the stable requirement declaration and human testing record for this scope.

The requirement declaration belongs at `backend/tests/support/requirements/ws04_03a.json`.

Focused tests and the testing record belong under:

`backend/tests/migrations/migration_policy_compatibility_rehearsal/`

The requirement declaration should map sections 2.1 through 2.8 in this plan to stable requirement IDs `WS04-03A-R1` through `WS04-03A-R8`. The testing record should explain the migration risks, selected scenarios, proof layers, dedicated migration-test database isolation, controlled PostgreSQL evidence, gaps, deferrals, and why validation is adequate.

The testing record must not claim final production provider behavior, production runtime ceilings, production-equivalent volume, final rollout evidence, deployed observability, backup/PITR, restore, or incident-response evidence.

## 6. Done When

This checklist defines the engineering completion bar for WS04-03A.

- [ ] The provider-independent migration safety contract exists and covers migration policy, expand/contract, compatibility windows, graph/drift checks, upgrade paths, operation classification, interruption/resume, rollback/forward-fix, rehearsal evidence, and later-owned boundaries.
- [ ] The current Alembic chain is inventoried from source and reconciled against the current 59-migration repository truth or the current migration count if the chain changed before Gate B.
- [ ] Trusted tests prove Alembic graph correctness, one expected head, dependency integrity, and deterministic migration inventory behavior.
- [ ] Ordinary backend tests remain restricted to `pickup_lane_test_db`, while migration lifecycle tests use only the separately validated `pickup_lane_migration_test_db` on the same approved test PostgreSQL host and port.
- [ ] Local and CI test setup provision the dedicated migration test database without allowing fallback to another database.
- [ ] Trusted PostgreSQL tests prove empty-database upgrade, controlled prior-schema upgrade, rerun-to-head behavior, drift verification, serialized migration-test execution, and cleanup after success or failure.
- [ ] Controlled compatibility tests prove safe expand/contract examples and reject unsafe one-step schema changes.
- [ ] Controlled interruption/rehearsal tests prove provider-independent recoverability, retry behavior, cleanup, and sanitized evidence recording.
- [ ] Any current migration, model, Alembic configuration, or test-safety mismatch found by the tests is corrected narrowly within this pass or routed back to Gate A/Stage 0 if it changes the design or executable boundary.
- [ ] Accepted `WS04-01A/B/C` and `WS04-02A/B/C` database contracts remain intact.
- [ ] The stable requirement declaration and testing record for `WS04-03A` are present and match the implemented proof.
- [ ] The execution register records `WS04-03A` as accepted on merge, keeps `WS04-03B` mandatory and deferred, and does not mark the full `WS04-03` parent complete.
- [ ] No final production provider/runtime migration facts, production-equivalent volume, final migration runner behavior, final deployment topology, final provider lock/runtime behavior, backup/restore evidence, deployed observability evidence, or final rollout evidence is claimed by this pass.