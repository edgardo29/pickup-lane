# WS04-03A Migration Policy, Compatibility, Graph/Drift Checks, And Controlled Rehearsal Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS04-03A` |
| Trusted test scope | `backend/tests/migrations/migration_policy_compatibility_rehearsal` |
| Requirement declaration | `backend/tests/support/requirements/ws04_03a.json` |
| Authoritative sources | `docs/production-readiness/planning/passes/ws04/ws04-03a-provider-independent-migration-policy-compatibility-graph-drift-controlled-rehearsal.md`, accepted `WS04-03` intake, accepted WS04-01A/B/C and WS04-02A/B/C artifacts |
| Evidence layers | migration pytest, PostgreSQL, Alembic graph/drift, source-owned policy contract, static migration inventory, compatibility pytest |

## 1. Scope

This record covers provider-independent migration safety for current
repository-owned source. The scope includes migration policy, expand/contract
rules, old/new compatibility expectations, Alembic graph and drift checks,
empty-database and prior-schema upgrade behavior, dedicated migration-test
database safety, interruption/retry/cleanup rehearsal, and current migration
operation classification.

This record does not claim final production provider behavior, production
migration runtime ceilings, production-equivalent volume, final migration
runner behavior, final deployment topology, final provider lock/runtime
behavior, final rollout evidence, backup/PITR, restore exercises, deployed
observability, dashboards, alerts, or incident-response evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS04-03A-R1` | Provider-independent migration policy, compatibility windows, and later-owner boundaries are explicit. | pytest |
| `WS04-03A-R2` | Current and future migration operations are classified and risky patterns fail closed. | pytest |
| `WS04-03A-R3` | Alembic graph, dependency, multiple-head, and drift verification are trusted evidence. | pytest |
| `WS04-03A-R4` | Empty and prior-schema upgrades run only against the dedicated migration test database. | pytest |
| `WS04-03A-R5` | Unsafe one-step schema changes are rejected by compatibility policy. | pytest |
| `WS04-03A-R6` | Provider-independent lock, timeout, interruption, resume, rollback, and forward-fix behavior is covered. | pytest |
| `WS04-03A-R7` | Controlled PostgreSQL migration rehearsal produces repository-owned evidence. | pytest |
| `WS04-03A-R8` | Accepted database contracts remain intact and later-owned final-provider evidence remains deferred. | pytest plus compatibility |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `WS04-03A-R1`, `R8` | One source-owned policy names migration rules and boundaries. | Migration safety stays scattered across docs and future passes silently overclaim proof. | False closure before production migration sign-off. | Declarative policy contract and requirement declaration. | migration |
| `WS04-03A-R2` | Risky migration operations are classified before merge. | Drops, renames, data rewrites, dynamic SQL, or special transactions enter without proof. | Data loss, blocking DDL, or unreviewed schema behavior. | Static inventory and fail-closed risky-pattern checks. | migration |
| `WS04-03A-R3` | The Alembic graph has one expected head and no drift after upgrade. | Multiple heads, missing links, or model/schema drift hide until deploy. | Failed migration or runtime schema mismatch. | Graph tests and PostgreSQL drift comparison. | migration |
| `WS04-03A-R4` | Migration lifecycle tests own only `pickup_lane_migration_test_db`. | Migration reset drops ordinary test data or an unsafe database. | Data loss or misleading evidence. | Exact-purpose URL validation and marker-based cleanup separation. | support/migration |
| `WS04-03A-R5` | Incompatible schema changes require expand/contract. | New code removes a schema shape still needed by old code. | Rolling deploy failure or runtime errors. | Compatibility policy examples and unsafe-change rejection. | migration |
| `WS04-03A-R6`, `R7` | Interrupted controlled runs are inspectable and recoverable. | A failed migration leaves unknown residual state and later tests continue. | Hidden migration failure or unsafe resume assumption. | Advisory lock, reset, interruption marker, and retry proof. | migration/PostgreSQL |
| `WS04-03A-R8` | Final provider/runtime facts remain deferred. | Local or CI rehearsal is treated as production-equivalent evidence. | Premature final-readiness claim. | Policy and testing-record deferrals. | governance/migration |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Migration graph | one base, one head, revision metadata | covered | Current Alembic graph is inspected from source and via Alembic script resolution. |
| Operation types | extension, sequence, table, index, constraints, raw SQL, destructive/data-affecting/special operations | covered | Current operations are inventoried and risky future patterns fail closed. |
| Database states | empty migration state, prior revision, current head, interrupted state | covered | Dedicated migration DB tests exercise each state. |
| Compatibility | safe expansion, unsafe drop/rename/type/default/data-rewrite examples | covered | Policy examples prove old/new schema boundary behavior. |
| Network/provider | local approved PostgreSQL host/port only | covered/deferred | Tests prove exact test DB boundary; final provider behavior remains `WS04-03B`. |
| Recovery | rerun, reset, interruption rollback, forward-fix posture | covered/deferred | Provider-independent recovery is covered; final production recovery evidence remains later-owned. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing `MIGRATION_DATABASE_URL` for migration lifecycle tests | fail-safe validation |
| empty | yes | reset to no migration-created schema state | PostgreSQL rehearsal |
| corrupt | yes | malformed or unsafe migration database URL | environment-safety tests |
| exceed | partial | production runtime ceilings | deferred to `WS04-03B` |
| duplicate | yes | duplicate or branched revision metadata | graph tests |
| delay | partial | migration duration observations | provider-independent sanitized evidence only |
| reorder | yes | old/new compatibility and revision dependency order | policy and graph tests |
| interrupt | yes | controlled interrupted rehearsal | PostgreSQL rehearsal |
| race | yes | parallel migration lifecycle runs | advisory-lock serialization |
| expire / revoke | no | provider credential lifecycle | `WS04-01D` / `WS10` |
| tamper | yes | dynamic SQL or unsafe migration operation pattern | static inventory checks |
| retry | yes | rerun upgrade to head and retry after controlled interruption | PostgreSQL rehearsal |
| recover | yes | reset and forward-fix posture | PostgreSQL plus policy |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `WS04-03A-R1`, `R8` | Policy and boundary contract | pytest/static | `test_migration_safety_policy_contract.py` | Proves one side-effect-free policy covers all requirement families and preserves later owners. |
| `WS04-03A-R2`, `R3`, `R5`, `R6`, `R7` | Current migration inventory and graph | pytest/static/Alembic | `test_migration_inventory_graph_contract.py` | Proves the current 62-revision chain is linear and risky upgrade-side patterns fail closed. |
| `WS04-03A-R4`, `R7`, `R8` | Exact-purpose migration DB safety | pytest/static | `test_migration_database_safety_contract.py` | Proves migration tests require `pickup_lane_migration_test_db` and cannot fall back to `pickup_lane_test_db`. |
| `WS04-03A-R3`, `R4`, `R6`, `R7`, `R8` | Empty/prior upgrade, rerun, drift, reset, interruption | pytest/PostgreSQL/Alembic | `test_migration_lifecycle_rehearsal.py` | Proves provider-independent runtime behavior on the dedicated migration database; not final provider/runtime evidence. |
| `WS04-03A-R8` | Accepted compatibility boundaries | pytest | WS04-01A/B/C and WS04-02A/B/C compatibility scopes | Proves this pass did not weaken accepted database, transaction, invariant, or value/SQL contracts. |

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Migration database reset | `pickup_lane_migration_test_db` returns to a clean migration state. | `pickup_lane_test_db` must not be reset or cleaned by migration lifecycle tests. | Reset runs only after exact identity validation. |
| Empty-to-head upgrade | Dedicated migration DB reaches Alembic head. | No final provider or production database is touched. | Fixture cleans the migration DB afterward. |
| Prior-schema upgrade | Prior revision upgrades to head and rerun to head is safe. | Downgrade is not claimed as production recovery. | Prior state is controlled test setup only. |
| Interruption rehearsal | Interrupted marker rolls back or leaves deterministic inspectable state. | Later tests must not continue against unknown residual state. | Reset restores known state after observation. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Final production PostgreSQL topology, connection budget, concrete roles/grants, and effective migration role | deferred | Final infrastructure remains intentionally unselected. | `WS04-01D` |
| Final provider/runtime migration ceilings, provider lock behavior, final migration runner, production-equivalent volume, final rolling-overlap topology, and final rollout evidence | deferred | These facts require selected final infrastructure and production-equivalent rehearsal inputs. | `WS04-03B` |
| Durable jobs, payment/provider lifecycle, worker execution, and reconciliation | deferred | Not migration-policy ownership. | `WS05` |
| Deployed logs, metrics, dashboards, and alerts | deferred | Local migration evidence is not deployed observability evidence. | `WS09` |
| Backup/PITR, restore exercises, incident response, and recovery operations | deferred | Provider-independent migration rehearsal is not final recovery proof. | `WS10` |
| Transaction, invariant, lock, and SQL/value safety contracts | covered_elsewhere plus compatibility | Accepted A/B/C evidence owns those direct behaviors. | WS04-01A/B/C and WS04-02A/B/C |

## 9. Adequacy Conclusion

The selected evidence is adequate for WS04-03A when the focused migration
pytest scope, backend checker scope, applicable compatibility scopes, and
`git diff --check` pass. The evidence proves provider-independent migration
policy, current graph/inventory behavior, exact-purpose migration DB safety,
controlled empty/prior upgrade behavior, drift verification, interruption/reset
behavior, and later-owner boundaries.

Final provider/runtime migration proof remains explicitly deferred to
`WS04-03B` and is not claimed here. Checker `PASS` remains structural
compliance only, not human adequacy by itself.

## 10. Gate B Validation Results

| Validation | Result |
|---|---|
| Focused WS04-03A migration pytest scope | PASS: `26 passed` against `pickup_lane_migration_test_db` through `MIGRATION_DATABASE_URL`. The scope now includes Alembic-backed interruption/repaired-rerun proof, mixed raw-SQL fail-closed regression coverage, and two-session advisory-lock serialization proof. Warnings were limited to existing Alembic `path_separator` deprecation output and an Alembic expression-index comparison warning for the existing trigram index. |
| Backend test checker for `migrations/migration_policy_compatibility_rehearsal` | PASS: 26 collected pytest nodes; all `WS04-03A-R1` through `WS04-03A-R8` requirements mapped; 36 traceability passes and 324 requirement declarations loaded. |
| Focused settings, environment-safety, and non-lifecycle migration tests | PASS: `154 passed` with the ordinary dedicated `pickup_lane_test_db` boundary. Warnings were limited to existing Alembic `path_separator` deprecation output. |
| Backend checker pytest scope | PASS: `78 passed` with the ordinary dedicated `pickup_lane_test_db` boundary. |
| Accepted WS04-01A/B/C and WS04-02A/B/C compatibility scopes | PASS: `118 passed` across application database lifecycle, query/cursor behavior, production database verification contracts, transaction-boundary contracts, deterministic concurrency/invariant contracts, and value/default/SQL-safety contracts. |
| Python compile validation for new policy/support/test modules | PASS. |
| `git diff --check` | PASS. |
