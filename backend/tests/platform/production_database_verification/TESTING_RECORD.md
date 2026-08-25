# WS04-01C Production Database Verification Framework Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS04-01C` |
| Trusted test scope | `backend/tests/platform/production_database_verification/` |
| Requirement declaration | `backend/tests/support/requirements/ws04_01c.json` |
| Authoritative sources | Frozen WS04-01C plan, accepted WS04-01 intake, accepted WS04-01A/B evidence, provider evidence handling standard, provider evidence checklist, limits register, foundation decision register, master blueprint, execution register |
| Evidence layers | pytest static/source inspection, deterministic helper validation, synthetic fixtures, governance/document review, deferred final provider evidence |

## 1. Scope

This record covers WS04-01C's repository-owned provider-independent framework
for final production PostgreSQL topology, connection budget, and role/grant
verification. It proves the sanitized evidence contract, deterministic
connection-budget arithmetic, required consumer classification, EN-03 metadata,
FDN-04/DBP-01 limit-basis fields, runtime/pooler checklist, role/grant
checklist, and mandatory WS04-01D handoff.

This scope intentionally does not prove final hosting, final database provider,
provider plan capacity, deployed API instance or process counts, autoscaling,
rolling-deploy overlap, deployed pool values, final numeric budget/headroom,
concrete production roles/grants, provider dashboards, runtime observations, or
production telemetry.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS04-01C-R1` | C remains provider-independent and D owns final provider/runtime/role proof. | pytest/static and governance |
| `WS04-01C-R2` | Evidence contract carries EN-03 metadata and rejects sensitive raw evidence. | pytest/helper |
| `WS04-01C-R3` | Connection-budget formula and consumer inputs are complete and deterministic. | pytest/helper |
| `WS04-01C-R4` | Future final values must carry FDN-04/DBP-01 limit-basis evidence. | pytest/helper and governance |
| `WS04-01C-R5` | Runtime topology and direct/pooler/proxy proof requirements are explicit. | pytest/static |
| `WS04-01C-R6` | Role/grant/search-path/default-privilege verification contract is complete. | pytest/helper |
| `WS04-01C-R7` | Accepted A/B behavior remains intact and C does not add production source/config/migration changes. | pytest/static |
| `WS04-01C-R8` | WS04-01D remains mandatory before closeout and D-owned facts are not claimed by C. | pytest/static and governance |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R8` | C defines a framework only; D owns final provider/runtime values. | Temporary Neon, Render, Vercel, README, or local values become final evidence. | Production topology and capacity are falsely closed. | Contract and planning boundary tests require deferred D state. | platform/static |
| `R2` | Repository evidence is sanitized, metadata-bearing, and raw evidence stays outside Git. | Raw URLs, credentials, screenshots, provider identifiers, or unsupported evidence enter the contract. | Evidence collection creates a leak path or loses provenance. | Helper metadata validation and sensitive-value detection. | platform/helper |
| `R3`, `R4` | Budget arithmetic uses all required consumer classes and the full limits method. | Unknown consumers become zero, overlap is double-counted, or numeric values lack evidence basis. | Final D budget may pass with unsafe headroom. | Synthetic positive and negative fixtures. | platform/helper |
| `R5` | Runtime and pooler/proxy proof requirements are explicit. | Pooler mode, autoscaling, process count, or shutdown behavior is inferred from examples. | D accepts topology assumptions without provider/runtime proof. | Structured topology checklist and boundary tests. | platform/static |
| `R6` | Least privilege requires roles, attributes, ownership, grants, search path, and defaults together. | Table grants alone are treated as least privilege, or app and migration roles collapse. | Runtime role may retain broad DDL/admin power. | Role contract and negative final-evidence fixtures. | platform/helper |
| `R7` | C avoids production code/config/schema/provider mutation. | Framework work smuggles in source behavior, migrations, credentials, or deployment assumptions. | Scope expands past provider-independent C. | Static source/config/migration negative-space tests. | platform/static |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | database owner, platform/deployment owner, reviewer, later provider-evidence collector | grouped | C defines proof shape and owner metadata; D collects final evidence. |
| States / lifecycle | deferred, verified, not applicable, blocked, stale, final D-shaped evidence | covered | These states decide whether final values can be trusted or must stop. |
| Actions | populate evidence metadata, compute budget, classify consumers, review roles/grants, preserve D handoff | covered | These are the C-owned framework behaviors. |
| Inputs / boundaries | provider capacity, pool values, API topology, rolling overlap, non-API consumers, role privileges | covered/deferred | C validates shape and arithmetic; final facts are D-owned. |
| Dependencies | PostgreSQL provider, hosting provider, pooler/proxy, telemetry, role/grant inspection | deferred | Provider/runtime dependencies are unavailable until final infrastructure selection. |
| Concurrency / multi-instance | API instances, processes, autoscaling, rolling overlap, provider capacity boundary | covered as required evidence | Synthetic arithmetic proves the contract; actual multi-instance proof is D-owned. |
| Authorization / privacy / security | sanitized evidence, safe aliases, raw evidence outside Git, least privilege | covered | Evidence hygiene and role/grant boundaries are high-risk. |
| Persistence / rollback | safe adjustment, rollback/abort, post-change re-verification | covered as required fields | D must preserve these before trusting mutable capacity values. |

## 5. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1`, `R2`, `R5`, `R8` | provider-neutral evidence template, EN-03 metadata, runtime topology checklist, temporary-provider rejection | pytest/static/helper | `test_evidence_contract_schema.py` | Adequate for repository contract shape; not final provider proof. |
| `R3`, `R4`, `R8` | budget formula, consumer completeness, overlap arithmetic, source attribution, zero handling, stale state, negative headroom, FDN-04 basis | pytest/helper | `test_connection_budget_contract.py` | Adequate for deterministic C framework behavior; numeric production values remain D-owned. |
| `R2`, `R6`, `R8` | role classes, required checks, app runtime prohibited privileges, role separation, ownership/search/default privilege completion | pytest/helper | `test_role_grant_contract.py` | Adequate for final evidence contract behavior; no concrete roles/grants are verified. |
| `R1`, `R5`, `R7`, `R8` | current authority consistency, accepted A/B boundary, C/D handoff, no production source/config/migration changes | pytest/static | `test_ws04_01c_boundary_and_handoff_contract.py` | Adequate for source/diff boundary; final runtime/provider facts remain external. |

## 6. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Final PostgreSQL provider/topology | deferred | Final production infrastructure is intentionally not selected. | `WS04-01D` |
| Final deployed connection budget/headroom | deferred | Requires provider capacity, runtime topology, consumer inventory, and sanitized evidence. | `WS04-01D` |
| Concrete production roles/grants | deferred | Requires final provider/database role inspection and safe aliases. | `WS04-01D` |
| Production telemetry dashboards/alerts | deferred | C defines signal needs; dashboard and alert implementation remain later owned. | `WS09` plus `WS04-01D` binding |
| Provider/control-plane access and raw evidence storage | deferred | Raw provider material must remain outside Git and final evidence collection is later. | EN-03 / WS10 / `WS04-01D` |

## 7. Adequacy Conclusion

The selected evidence is adequate for WS04-01C when the focused production
database verification tests, requirement checker for the focused domain,
applicable compatibility scopes, diff checks, and final Gate C
review pass.

Checker `PASS` is structural compliance evidence only. Gate C review must still
confirm that C does not overclaim final provider capacity, production runtime
topology, concrete production role/grant proof, or final DB-002/DB-015 closure.
