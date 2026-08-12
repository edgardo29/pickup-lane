# WS02-02 Runtime Platform Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS02-02` |
| Trusted test scope | `backend/tests/platform/runtime/` |
| Requirement declaration | `backend/tests/support/requirements/ws02_02.json` |
| Authoritative sources | Frozen WS02-02 plan, frozen pass recheck workflow, EN-01 testing architecture, WS02-01 settings evidence, current backend runtime source |
| Evidence layers | Trusted platform pytest, isolated subprocess import proof, one narrow PostgreSQL helper proof, static repository checks, governance template review, deferred external evidence |

## 1. Scope

This record covers the repository-owned runtime lifecycle, health, release
identity, topology-boundary, and release/rollback evidence foundation for
WS02-02. It covers the canonical FastAPI app owner, import/app-construction
side-effect boundaries, lifespan state, shutdown disposal calls, liveness,
readiness, optional diagnostic health, safe release identity, and static
non-invention of deployment topology or connection-budget values.

This scope does not prove deployed hosting health-check configuration, Render
or Neon dashboard settings, deployed process or worker topology, deployed
connection release, platform hardening, versioned deployment/runtime
configuration, release execution, rollback execution, browser behavior,
migration rehearsal, observability dashboards, alerts, provider access, or
external evidence packages.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-02-R1` | One canonical FastAPI app construction and lifecycle owner exists. | pytest/static |
| `WS02-02-R2` | Importing and constructing the app is provider-free and side-effect bounded. | isolated subprocess pytest |
| `WS02-02-R3` | Lifespan state transitions are truthful and shutdown calls the database disposal helper. | pytest |
| `WS02-02-R4` | `/live` is lifecycle/process liveness, not database or provider readiness. | pytest |
| `WS02-02-R5` | `/ready` is database-backed readiness with generic failure behavior and recovery. | pytest plus one PostgreSQL helper proof |
| `WS02-02-R6` | Root compatibility and `/db-health` do not replace canonical readiness. | pytest |
| `WS02-02-R7` | Health responses expose only stable, concise, non-sensitive release identity. | pytest |
| `WS02-02-R8` | Repository topology and connection-budget boundaries remain mechanically verifiable without provider-proof overclaim. | pytest/static |
| `WS02-02-R9` | Release/rollback evidence is preserved through a safe non-executable template. | covered elsewhere |
| `WS02-02-R10` | Versioned deployment/runtime configuration and provider-linked runtime proof remain deferred. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `WS02-02-R1` | `backend/main.py` owns app construction, lifecycle, and health routes. | Another reachable app factory, route receiver, router-owned health path, lifecycle binding, startup/shutdown handler, or module app bypasses lifecycle behavior. | Deployments or tests validate the wrong app. | Alias-aware FastAPI construction detection, semantic factory/module-app ownership detection, receiver-independent route detection, lifecycle binding detection, adversarial detector tests, and runtime app construction proof. | platform/static |
| `WS02-02-R2` | Import/app construction does not connect to DB, run migrations, start workers, or initialize providers. | Module import opens PostgreSQL, starts Uvicorn, reads local dotenv secrets, or initializes Firebase/Stripe/R2. | Startup and tests create uncontrolled side effects. | Clean-interpreter subprocess with fail-fast sentinels and synthetic settings. | platform subprocess |
| `WS02-02-R3` | Lifecycle state is false before startup, true during lifespan, false after shutdown, and shutdown uses the public disposal helper. | Readiness is true outside lifecycle or shutdown leaks source-level engine disposal. | Health probes lie and rolling releases keep source-owned resources open. | Direct lifespan exercise plus helper-to-engine delegation proof. | platform pytest |
| `WS02-02-R4` | `/live` depends only on process/lifecycle state and returns minimal no-store output. | Database or provider failure restarts an otherwise live process or health leaks diagnostics. | Availability loss or operational information exposure. | Fail-fast DB/provider sentinels and active/inactive route assertions. | platform API pytest |
| `WS02-02-R5` | `/ready` gates traffic on active lifecycle plus a minimal DB probe, suppresses diagnostics, and can recover. | Readiness skips DB, leaks exception details, blocks on optional providers, or stays poisoned after one failure. | Traffic reaches broken processes or operational secrets leak. | Controlled probe substitution plus one real dedicated-DB helper proof. | platform API pytest/PostgreSQL |
| `WS02-02-R6` | Root compatibility and optional `/db-health` remain separate from canonical readiness. | Root or `/db-health` becomes the hosting readiness contract or leaks DB diagnostics. | Provider health-gate claims become false or diagnostics leak. | Disabled/enabled `/db-health` route tests and root-vs-ready separation. | platform API pytest |
| `WS02-02-R7` | Release identity is safe, bounded, captured at app construction, and stable for the app lifetime. | URLs, paths, secrets, short revisions, mutable env values, or config dumps leak through health. | Operators lose artifact linkage or expose sensitive data. | Settings rejection tests and health-response stability tests. | platform pytest |
| `WS02-02-R8` | Repository artifacts do not invent approved runtime topology or connection-budget values. | A tracked deploy/runtime artifact, worker config, scheduler config, process/instance/replica value, pool-size/overflow value, or provider claim is treated as approved without evidence. | Deployment design appears closed while provider facts remain unknown. | Cached tracked-file inventory, constrained runtime/deploy classifier, worker/scheduler detection, process/instance/replica detection, pool-size/overflow detection, adversarial classifier tests, and deferred R10 metadata verification. | platform/static |
| `WS02-02-R9` | The release/rollback template is a safe container, not execution evidence. | Blank fields or unsafe provider details become published evidence. | False release closure or confidential data exposure. | Template rules plus human governance review. | governance |
| `WS02-02-R10` | Deployment/runtime configuration remains deferred until provider topology and budget inputs exist. | Gate B fabricates manifests or numeric topology values. | Future deployment work starts from false assumptions. | Deferred declaration and plan/template boundary review. | planning |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | Backend process, platform health checker, release reviewer, provider/runtime owner | grouped | The pass owns platform runtime behavior, not user authorization. |
| States / lifecycle | app constructed, inactive lifecycle, active lifespan, shutdown complete, failed DB probe, recovered DB probe | covered | These are the material lifecycle and readiness states. |
| Actions | import app, construct app, start lifespan, shut down, call `/live`, call `/ready`, call root, call `/db-health`, parse release metadata, inspect tracked topology artifacts | covered | These are the repository-owned runtime actions. |
| Inputs / boundaries | missing release metadata, safe label, full 40/64 character source revision, short revision, blank, whitespace, URL-like, path-like, sensitive-looking, DB exception detail | covered/grouped | Distinct release and diagnostic leakage risks are represented without a blind Cartesian matrix. |
| Time | App construction before later environment mutation | covered | R7 requires app-lifetime stability; no exact time-boundary clock behavior is owned. |
| Dependencies | PostgreSQL helper, substituted DB probe, Firebase, Stripe, R2, email/webhook boundary, socket/network, migrations, worker/scheduler startup | covered/grouped | Dependencies are either fail-fast sentinels, controlled substitutions, or one narrow real DB helper proof. |
| Concurrency / idempotency | Not applicable | not applicable | WS02-02 does not own race, retry, or mutation idempotency behavior. |
| Authorization / privacy / security | release identity exposure, diagnostic suppression, secret/provider data exclusion | covered | Health and evidence surfaces must stay non-sensitive. |
| Persistence / rollback | Release/rollback template only; no mutation | governance | The template is not an executed release record. |
| Recovery | readiness failure followed by success | covered | Recovery after a failed probe is material to readiness correctness. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | Missing release metadata, disabled `/db-health`, unavailable provider topology fields | pytest/governance/deferred |
| empty | yes | Blank release metadata ignored according to settings contract | pytest |
| corrupt | yes | Unsafe release values and DB probe exceptions | pytest |
| exceed | yes | Overlong release identity through settings contract | pytest grouping through concise release parser coverage |
| duplicate | yes | Duplicate app/health ownership search | static pytest |
| delay | no | No timing threshold is owned by WS02-02. | not applicable |
| reorder | no | No ordered external workflow is owned. | not applicable |
| interrupt | yes | Shutdown path calls disposal helper; deployed signal behavior external | pytest plus external gap |
| race | no | No genuine concurrency contract is owned. | not applicable |
| expire / revoke | no | Release/revision revocation is later release evidence. | later evidence |
| tamper | yes | Ambient environment changes after app construction | pytest |
| retry | no | No retry policy is owned. | not applicable |
| recover | yes | Readiness recovers after a failed DB probe | pytest |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `WS02-02-R1` | Canonical app owner and duplicate route/lifecycle detection | pytest/static | `test_runtime_lifecycle_and_health_contract.py` | Adequate for repository-owned app-owner drift because the detector covers aliased/module-qualified FastAPI construction, semantic factory and module-app ownership, route registration independent of receiver name, lifecycle binding, startup/shutdown handlers, and positive/negative detector cases; not deployed entrypoint proof. |
| `WS02-02-R2` | Clean-interpreter import with side-effect sentinels | subprocess pytest | `test_runtime_lifecycle_and_health_contract.py` | Adequate for import/app construction side effects; not live server or provider startup proof. |
| `WS02-02-R3` | Lifespan state and disposal delegation | pytest | `test_runtime_lifecycle_and_health_contract.py` | Adequate for source-level lifecycle and helper delegation; deployed signal timing remains external. |
| `WS02-02-R4` | Liveness active/inactive behavior and provider/DB non-contact | API pytest | `test_runtime_lifecycle_and_health_contract.py` | Adequate for source-owned liveness; not hosting health-gate configuration. |
| `WS02-02-R5` | Readiness success/failure/recovery plus real helper connectivity | API pytest and PostgreSQL | `test_runtime_lifecycle_and_health_contract.py` | Adequate for route semantics and helper; provider DB limits and deployed health gate remain external. |
| `WS02-02-R6` | Root compatibility and optional `/db-health` behavior | API pytest | `test_runtime_lifecycle_and_health_contract.py` | Adequate for repository route separation; not provider health-check binding. |
| `WS02-02-R7` | Safe release parsing and app-lifetime capture | pytest | `test_release_and_topology_boundary.py` | Adequate for source health metadata; not full release evidence chain. |
| `WS02-02-R8` | Topology/config non-invention and deferred metadata | static pytest | `test_release_and_topology_boundary.py` | Adequate for repository non-invention because the detector uses `git ls-files --cached`, a constrained backend runtime/deploy artifact classifier, worker/scheduler command and source detection, process/instance/replica value detection, pool-size/overflow detection, positive/negative classifier cases, and structural R10 deferred metadata verification; not actual Render/Neon/provider/deployed topology. |
| `WS02-02-R9` | Release/rollback safe template | governance | `release-rollback-record-template.md` plus human review | Adequate for repository container only; executed records remain later evidence. |
| `WS02-02-R10` | Explicit deferral of deployment/runtime config | declaration/planning | `ws02_02.json`, frozen plan, template unresolved fields | Adequate for non-fabrication; provider topology and budget inputs remain required later. |

### Evidence Quality Checks

- Route rejection tests keep otherwise-valid synthetic prerequisites so failed
  assertions exercise the intended health rule.
- Readiness failure proves prohibited diagnostic leakage and proves recovery
  after a later successful probe.
- The real PostgreSQL test uses the existing dedicated test database guard and
  only the shared minimal `SELECT 1` helper.
- External provider boundaries are fail-fast sentinels at app-owned provider
  functions rather than mocks of the health business rule.
- Static topology checks use tracked-file inventory, finite manifest patterns,
  constrained runtime/deploy classification, AST/config parsing, positive and
  negative drift examples, and structured declaration inspection rather than
  arbitrary Markdown grep or exact planning prose.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| App import/construction | Canonical app object exists with synthetic settings. | No PostgreSQL connection, migration, provider initialization, network connection, worker/scheduler start, live server, or dotenv reliance. | No mutation. |
| Lifespan shutdown | Public disposal helper is called. | No broadened disposal-failure behavior or deployed signal claim. | No mutation. |
| Liveness/readiness/db-health | Return minimal no-store responses according to lifecycle and DB probe state. | No optional provider calls, diagnostic leaks, or root-as-readiness claim. | Readiness can recover after one failed probe. |
| Real database helper proof | Execute only the shared minimal `SELECT 1` helper. | No migrations, app-data mutation, provider access, or non-test database. | Read-only; no cleanup required. |
| Release/rollback template | Preserve safe fields and explicit unknowns. | No secrets, provider-private data, or execution-evidence claim from blanks. | Non-executable governance record. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-02-R9` | covered_elsewhere | The canonical plan and release/rollback template preserve the repository-owned evidence boundary. Actual deployment, hardening, rollback, and forward-fix execution remain external or later evidence. | Governance review; WS08/WS09/WS10/provider evidence. |
| `WS02-02-R10` | deferred | Verified provider topology, platform limits, process and instance design, and deployment-wide connection-budget inputs are unavailable. Gate B must not fabricate values. | WS04, WS08, WS09, WS10, and provider/runtime evidence. |
| Deployed health-gate binding | external/later | Source tests cannot inspect provider dashboard health-check paths. | Provider/runtime evidence. |
| Render/Neon topology and limits | external/later | Repository files do not prove deployed provider state. | Provider/runtime evidence and DBP-01 follow-up. |
| Platform hardening and release execution | external/later | A template cannot prove an executed release, rollback, or platform setting. | Release/provider evidence. |

## 9. Adequacy Conclusion

This WS02-02 runtime evidence is adequate for Gate C review when the runtime
pytest scope passes with the dedicated test database, WS02-01 settings
regression passes, checker file/domain/suite scopes pass, generated
traceability maps R1-R8 to truthful executable tests, R9 and R10 have no fake
pytest mappings, final review confirms only the approved five Gate B files were
created, and the security review finds no real secrets or provider-private
data.

Checker `PASS` is structural compliance only. Human review remains responsible
for judging whether the selected scenarios and oracles are adequate for the
frozen WS02-02 risk model.
