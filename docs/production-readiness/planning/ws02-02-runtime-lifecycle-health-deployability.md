# WS02-02 - Runtime Lifecycle, Health, And Deployability

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-02` |
| Track | `WS02` |
| Type | Deployment foundation |
| Primary controls | `API-M03`, `API-M17`, `OPS-001`, `OPS-002`, `OPS-003`, `OPS-004` |
| Authority basis | Current repository, 163-control checklist, finalized remediation plan, `DBP-01`, `FDN-04`, `FDN-06`, `FDN-07`, master blueprint, WS02-01 environment matrix, provider/control-plane records |
| Depends on | `WS02-01`, `DBP-01` policy, preliminary provider topology evidence |
| Trusted test scope | Proposed `backend/tests/platform/runtime/` |

Preliminary provider topology is only partially satisfied: repository intent is
known from tracked source and README guidance, but deployed/provider topology is
not verified.

## 1. Purpose

WS02-02 defines the backend runtime lifecycle and health foundation that later
deployment, database, release, and provider-evidence work depends on.

The pass requires a clear FastAPI application lifecycle owner, side-effect
bounded application import and construction, separate liveness and readiness
semantics, safe database shutdown handling, minimal uncached health responses,
and a non-sensitive release identity that can be tied to later release
evidence.

The repository can prove the source-owned parts of that contract. It cannot, by
itself, prove deployed Render settings, process counts, worker topology, Neon
connection limits, health-gate configuration, rolling overlap, platform
hardening, actual shutdown observations, versioned deployment/runtime
configuration, or release/rollback execution.

## 2. Why This Matters

Runtime readiness is the difference between "the app object imported" and "the
deployed service can safely receive traffic." If liveness contacts PostgreSQL,
a database blip can restart a healthy process. If readiness skips PostgreSQL,
traffic can reach a process that cannot serve database-backed routes. If
shutdown does not dispose runtime database resources, rolling releases can keep
connections open longer than expected. If release identity is absent or unsafe,
operators cannot tie health, errors, logs, or rollback decisions to a specific
source artifact.

WS02-02 reduces those risks without pretending that source code can prove
provider dashboard facts. It creates the repository-owned contract and evidence
needed before later passes gather provider/runtime proof.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-02-R1` | The backend must have one canonical FastAPI application construction and lifecycle owner. | `backend/main.py` owns the app factory, route registration, middleware installation, lifespan hook, and module-level app instance; no alternate reachable app or lifecycle path may contradict it. | A second app or lifecycle owner could bypass health, middleware, startup, or shutdown behavior. |
| `WS02-02-R2` | Application import and app construction must be bounded and provider-free. | Importing or building the app may parse required settings, but must not connect to PostgreSQL, run migrations, initialize Firebase, Stripe, R2, email, webhooks, background workers, schedulers, or provider clients. | Deployment startup and tests must not produce uncontrolled provider or database side effects before the lifecycle begins. |
| `WS02-02-R3` | Lifespan startup and shutdown must expose correct lifecycle state and dispose the runtime SQLAlchemy engine on shutdown. | The app becomes lifecycle-active only inside FastAPI lifespan startup and returns inactive on shutdown; shutdown calls the database module's public engine-disposal helper. | Readiness/liveness need a truthful local lifecycle signal, and rolling releases need source-level resource teardown. |
| `WS02-02-R4` | `GET /live` must be a process/lifecycle liveness probe only. | Liveness succeeds only while the lifecycle is active, returns a minimal uncached response, and does not contact PostgreSQL or external providers. | Liveness should tell the platform whether the process is alive, not restart the process because a dependency is temporarily unavailable. |
| `WS02-02-R5` | `GET /ready` must be the database-backed readiness probe. | Readiness requires an active lifecycle and a successful minimal PostgreSQL probe; inactive lifecycle or probe failure returns HTTP 503 with no diagnostic leakage and later recovery remains possible. | Traffic should be gated until the app can reach the primary database dependency. |
| `WS02-02-R6` | Compatibility and diagnostic health surfaces must not replace readiness. | The root endpoint may remain a compatibility surface. Conditional `/db-health` remains controlled by settings, uses the shared database probe when enabled, returns uncached responses, and hides exception details. | Compatibility endpoints must not become the hosting readiness contract or leak operational diagnostics. |
| `WS02-02-R7` | Health responses must expose only concise, stable, non-sensitive release identity. | Runtime release identity must be bounded, safe, captured when the app is constructed, stable for that app's lifetime, and fall back to a safe value when no provider metadata is available. Source revision inputs must accept only full commit SHA values. | Operators need artifact linkage without leaking configuration, hostnames, credentials, provider IDs, stack traces, free text, or mutable ambient environment state. |
| `WS02-02-R8` | Repository-owned runtime topology and connection-budget boundaries must be mechanically verifiable without claiming provider proof. | Trusted tests may prove no unapproved tracked backend runtime manifest defines production topology, no worker or scheduler runtime configuration exists, no repository-owned numeric process/instance/pool budget is presented as approved, and tracked boundaries still require evidence-based selection. | The repository should catch accidental fake topology values while remaining honest that actual Render, Neon, process, and deployed topology proof is external. |
| `WS02-02-R9` | Release/rollback evidence boundaries must be preserved through a repository-safe template. | The pass must define the minimum safe release/rollback record fields and confidentiality rules, while preserving that the template itself is not evidence that deployment, hardening, rollback, or forward-fix execution occurred. | Later release and recovery work needs a consistent evidence container without leaking provider secrets or falsely closing runtime controls. |
| `WS02-02-R10` | The blueprint-required versioned deployment/runtime configuration and provider-linked runtime proof remain explicitly deferred. | Repository-known runtime intent is documented, but provider/runtime facts needed to create versioned deployment/runtime configuration are unavailable; Gate B must not invent manifests, topology, platform limits, process/instance design, or connection-budget values. | The master blueprint output remains visible without fabricating deployment facts before provider topology, provider limits, and connection-budget inputs exist. |

## 4. Technical Design / Contracts

### 4.1 Canonical FastAPI App And Lifecycle Owner

`backend/main.py` is the canonical backend API construction path. It owns:

- `create_app`;
- the module-level `app`;
- FastAPI lifespan registration;
- health routes;
- middleware installation;
- router inclusion.

No other current repository path may expose a competing FastAPI application,
alternate readiness route, alternate liveness route, or independent startup or
shutdown hook that bypasses this owner.

### 4.2 Import And App Construction Side-Effect Boundary

Application import and construction may validate source-owned settings needed
to build the app. They must not perform runtime dependency work that belongs to
request handling, lifespan, readiness, migrations, or provider operations.

The source-owned boundary is:

- settings parsing is allowed;
- route/middleware registration is allowed;
- static app object construction is allowed;
- PostgreSQL connections are not opened during import or app construction;
- migrations are not run during import or app construction;
- Firebase Admin, Stripe, R2, email, webhook, worker, and scheduler clients are
  not initialized during import or app construction;
- no live server is started merely to prove the import boundary.

Provider clients may still be initialized later by the operation that actually
uses them. WS02-02 does not remove or redesign those operation-owned provider
paths.

Gate B evidence for this requirement must include isolated subprocess import
proof: import `backend.main` in a clean interpreter with synthetic safe
settings, prevent ignored dotenv reliance, trap materially relevant DB
connection, migration, provider-initialization, and uncontrolled-network side
effects, and avoid claiming deployed startup proof.

### 4.3 Lifespan And Shutdown Contract

The FastAPI lifespan hook owns local lifecycle state.

Required behavior:

- the lifecycle flag starts false after app construction;
- the flag becomes true during lifespan startup;
- the flag returns false during shutdown;
- shutdown calls the database module's public engine-disposal helper;
- disposal failure behavior is not broadened by this pass unless current
  source proves a specific defect.

The repository can prove the source-level disposal call. Actual deployed
connection release, signal timing, overlapping processes, and provider
connection counters require runtime/provider evidence.

If later Gate B evidence finds a disposal-failure issue or other source defect,
Gate B must stop and return to Gate A. Gate B may not silently add a production
source correction.

### 4.4 Liveness Contract

`GET /live` is the source-owned process and lifecycle liveness route.

Required behavior:

- inactive lifecycle returns HTTP 503;
- active lifecycle returns HTTP 200;
- the response is minimal and includes only bounded health status and safe
  release identity;
- `Cache-Control: no-store` is present;
- the route does not query PostgreSQL;
- the route does not contact Firebase, Stripe, R2, email, webhooks, or other
  providers.

### 4.5 Readiness Contract

`GET /ready` is the source-owned database-backed readiness route.

Required behavior:

- inactive lifecycle returns HTTP 503;
- active lifecycle plus successful minimal PostgreSQL probe returns HTTP 200;
- active lifecycle plus failed PostgreSQL probe returns HTTP 503;
- failure responses do not expose exception text, SQL, database URLs,
  hostnames, credentials, stack traces, provider identifiers, or diagnostics;
- a failed probe does not permanently poison readiness;
- a later successful probe may return ready without process restart.

Firebase, Stripe, R2, email, webhook, and other optional providers are not
global readiness blockers in this pass. Provider-specific availability and
workflow degradation belong to the provider/workflow passes that own those
operations.

### 4.6 Compatibility And Diagnostic Health Surfaces

The root endpoint may remain a compatibility health surface, but it is not the
canonical liveness or readiness contract.

The conditional `/db-health` route is a diagnostic surface controlled by typed
settings. When disabled, it must not be reachable. When enabled, it must use the
shared minimal database probe, return uncached responses, and hide database
exception details behind generic unavailability.

WS02-02 must not treat `/db-health` as the hosting readiness endpoint.

### 4.7 Release Identity Contract

Runtime release identity is safe operational metadata, not a diagnostics dump.

Required behavior:

- health responses expose only a concise release value;
- missing provider metadata falls back to a safe non-sensitive value;
- whitespace, URL-like values, path-like values, and sensitive-looking values
  are rejected for generic release labels;
- source-revision environment variables accept only full Git commit SHA values
  and normalize them safely;
- the app captures its release identity at construction;
- health responses use the captured app value;
- later ambient environment changes do not mutate the running app's release
  identity;
- health responses do not expose complete configuration, environment-variable
  values, provider IDs, database identifiers, hostnames, credentials, or stack
  traces.

Full release-evidence chains, deployment IDs, SBOM/provenance artifacts,
provider deployment linkage, CI result sets, approval records, and rollback
artifact identities remain `FDN-06`, WS08, WS09, WS10, and provider/runtime
evidence. WS02-02 release-identity tests must not claim full `FDN-06`
release-chain proof.

### 4.8 Runtime Topology And Connection-Budget Boundary

`DBP-01` requires one deployment-wide PostgreSQL connection budget that includes
API instances, process workers, per-process pools, overflow, background
workers, migrations, monitoring, autoscaling, rolling-deployment overlap, and
operational reserve.

Preliminary provider topology is only partially satisfied. The repository shows
runtime intent, such as README guidance for a Render backend and Neon database,
but it does not verify deployed provider topology, provider limits, service
settings, process model, worker/instance design, or connection-budget inputs.

WS02-02 must not select numeric topology or connection-budget values without:

- provider connection limits;
- deployment instance/process/worker topology;
- pool and overflow values;
- migration allowance;
- monitoring allowance;
- rolling-overlap allowance;
- operational reserve;
- boundary tests;
- telemetry and safe-adjustment behavior.

Until those inputs exist, this pass records the formula and evidence boundary
instead of creating fake values.

```text
required_database_connections =
  ((api_instances * api_processes_per_instance)
    * (sqlalchemy_pool_size + sqlalchemy_max_overflow))
  + ((worker_instances * worker_processes_per_instance)
    * (worker_pool_size + worker_max_overflow))
  + migration_connection_allowance
  + monitoring_connection_allowance
  + rolling_deployment_overlap_allowance
  + operational_reserve

required_database_connections <= provider_connection_limit
```

Gate B executable R8 evidence may prove only mechanically reliable
repository-owned facts: no unapproved tracked backend runtime manifest defines
production topology, no worker or scheduler runtime configuration exists, no
repository-owned numeric process/instance/pool budget is presented as approved,
and tracked plan/document boundaries continue to require evidence-based
selection. It must not claim actual Render, Neon, provider, process, or
deployed topology proof.

### 4.9 Release/Rollback Record Template Contract

Gate B must create a repository-safe template at:

`docs/production-readiness/governance/release-rollback-record-template.md`

The template must require, at minimum:

- environment;
- immutable source revision;
- backend deployment or artifact identity;
- related frontend deployment or artifact identity where applicable;
- dependency lockfile identity;
- migration head or schema-compatibility reference;
- CI result-set reference;
- approval record;
- provider deployment linkage;
- prior rollback artifact identity;
- release trigger and intended change;
- health/readiness validation;
- rollback trigger;
- rollback or forward-fix decision;
- rollback/forward-fix procedure reference;
- observed result;
- sanitized evidence reference;
- unresolved or unavailable external fields.

The template itself does not prove a deployment or rollback occurred. Blank
fields are not evidence. Executed records remain later runtime, release, and
provider evidence.

The template must not record credentials, secrets, private URLs, raw provider
payloads, personal data, payment data, or sensitive provider identifiers.

### 4.10 Deployment And External Evidence Boundary

Repository files can prove source contracts, dependency declarations, static
configuration surfaces, safe templates, and explicit deferrals. They cannot
prove live provider state.

The following remain external or later evidence until accepted:

- actual Render service settings and deployed start command;
- versioned deployment/runtime configuration based on verified topology;
- actual health-check path and health-gate behavior;
- actual process, worker, instance, autoscaling, and rolling-overlap behavior;
- platform/container hardening settings;
- runtime startup and shutdown observations;
- actual connection release under provider process signals;
- Neon plan, connection limit, pooling/proxy mode, reserve, region, and
  operational limits;
- immutable deployment or artifact identity;
- rollback and forward-fix execution records.

Completing the repository-owned WS02-02 recheck does not satisfy the deferred
blueprint output for versioned deployment/runtime configuration.

## 5. Implementation Scope

WS02-02 Gate B owns only the approved artifacts listed below. No production
source file is currently authorized. No tracked deployment configuration is
currently authorized.

| Path | Action | Requirement responsibility | Proof type |
|---|---|---|---|
| `backend/tests/support/requirements/ws02_02.json` | Create | Declare `WS02-02-R1` through `WS02-02-R10` with the exact states, scopes, source controls, and reasons in this plan. | Machine-readable traceability metadata. |
| `backend/tests/platform/runtime/TESTING_RECORD.md` | Create | Explain runtime lifecycle, health, release identity, topology-boundary, release/rollback, and deferred-deployment evidence risks for R1-R10. | Human testing/risk record. |
| `backend/tests/platform/runtime/test_runtime_lifecycle_and_health_contract.py` | Create | Prove R1-R6 and the narrow PostgreSQL helper boundary for R5, including isolated subprocess import proof for R2 and controlled app/lifespan/live/ready/db-health behavior. | Trusted executable pytest. |
| `backend/tests/platform/runtime/test_release_and_topology_boundary.py` | Create | Prove R7 release-identity behavior and R8 mechanically reliable repository-owned topology/budget boundary facts without claiming provider or deployed topology proof. | Trusted executable pytest plus static repository checks. |
| `docs/production-readiness/governance/release-rollback-record-template.md` | Create | Preserve R9 release/rollback evidence fields and confidentiality rules; support R10 by keeping unavailable external fields explicit. | Non-executable governance/document evidence. |

Current source assessment: no production source correction is currently proven
necessary for the source-owned lifecycle, liveness, readiness, diagnostic
health, shutdown-disposal call, or release-identity contracts.

If implementation or evidence work finds a contradiction with the frozen plan
or current source assessment, Gate B must stop and return to Gate A. Gate B may
not silently add a production correction, deployment manifest, worker command,
runtime topology value, connection-budget value, or platform-hardening setting.

## 6. Testing And Evidence

WS02-02 evidence must follow the EN-01 testing architecture. Historical tests
under `backend/tests/legacy/` are provenance only and do not count as current
trusted production-readiness evidence.

Proposed trusted evidence:

- requirement declarations in `backend/tests/support/requirements/ws02_02.json`;
- testing record in `backend/tests/platform/runtime/TESTING_RECORD.md`;
- trusted executable tests under `backend/tests/platform/runtime/`;
- source/configuration static checks where they prove repository-owned
  topology boundaries;
- governance/document review for the release/rollback record template and
  non-closure of external evidence;
- checker file/domain/suite validation and generated traceability.

### 6.1 Executable Evidence Responsibilities

Executable evidence should prove:

- R1 canonical app construction and absence of competing FastAPI app owners;
- R2 isolated subprocess import/app-construction side-effect boundary without a
  live server;
- R3 lifespan startup/shutdown lifecycle state and disposal helper call;
- R4 `/live` active/inactive behavior, no DB/provider calls, no-store response,
  and minimal response shape;
- R5 `/ready` active/inactive behavior, controlled database success/failure,
  recovery after a failure, no-store response, diagnostic suppression, and one
  focused real PostgreSQL proof of the shared minimal database helper;
- R6 `/db-health` disabled/enabled behavior, shared probe use, no-store
  response, and diagnostic suppression;
- R7 safe release-identity fallback, full-SHA source revision behavior, unsafe
  release-label rejection, minimal health exposure, no sensitive leakage, and
  stability for the lifetime of a constructed app despite later environment
  changes;
- R8 static repository facts that no tracked backend runtime manifest, worker
  runtime, scheduler runtime, or approved numeric topology/budget values are
  present, and that tracked boundaries require evidence-based selection.

R9 is non-executable governance evidence. R10 is a deferred planning
requirement. Neither should receive fake pytest nodes.

### 6.2 R2 Isolated Import Proof

R2 proof must use an isolated subprocess or equivalent clean-interpreter test
inside `backend/tests/platform/runtime/test_runtime_lifecycle_and_health_contract.py`.
The proof must:

- import `backend.main`;
- supply synthetic safe settings;
- prevent ignored dotenv reliance;
- trap materially relevant DB connection attempts;
- trap migration execution;
- trap Firebase, Stripe, R2, email, webhook, worker, scheduler, and uncontrolled
  network initialization;
- avoid starting Uvicorn or any live server;
- avoid claiming deployed startup proof.

Source/static import-boundary checks may support this evidence, but they do not
replace the isolated import proof.

### 6.3 R7 Release-Identity Stability Proof

R7 proof must include a scenario where the app captures its release identity at
construction, health responses use that captured value, and later ambient
environment changes do not mutate the running app's release identity.

This scenario supplements, but does not replace, coverage for safe fallback,
full commit SHA handling, unsafe label rejection, minimal health exposure, and
no sensitive value leakage.

### 6.4 PostgreSQL Isolation Boundary

PostgreSQL evidence is required only for one focused real test of the shared
minimal `SELECT 1` database helper against the dedicated `pickup_lane_test_db`.

Rules:

- use the existing EN-01 database safety guard;
- never use production, development, preview, or staging databases;
- do not use provider/network access;
- keep ordinary app, lifespan, `/live`, `/ready`, and `/db-health` route
  contract tests independent of live PostgreSQL by substituting the database
  probe where that proves the route rule;
- do not turn the whole runtime suite into a mandatory DB-backed suite.

### 6.5 Specialized Proof Decisions

| Proof type | Decision | Reason |
|---|---|---|
| Real PostgreSQL | YES, narrow | One focused dedicated-test-DB proof of the shared minimal `SELECT 1` helper is the lowest reliable proof for the helper itself. |
| Provider/network access | NO | Provider/runtime facts are external evidence and ordinary trusted tests must not make uncontrolled provider calls. |
| Browser/Playwright | NO | WS02-02 owns backend runtime/health source contracts, not browser behavior. |
| Migration/schema-history testing | NO | Migration runtime and rehearsal proof belongs to WS04/WS08 unless a specific migration change is authorized. |
| Genuine concurrency | NO | The source-owned health/lifecycle contract does not require race proof. |
| Controlled time | NO | No exact time-boundary behavior is owned by this pass. |
| Isolated subprocess import | YES | R2 requires clean-interpreter import proof without starting a live server. |
| Live Uvicorn/server-process proof | NO | Local source proof must not claim deployed startup or provider process behavior. |
| External runtime/provider evidence | YES, later | Full Render, Neon, health-gate, hardening, release, rollback, and topology proof remains external or later-pass evidence. |

### 6.6 Future Requirement Declaration Design

The future JSON declaration must use exactly this metadata design and must not
include product specifications or pytest node IDs.

| ID | owning_pass | source_controls | state | scope | reason where required | Proof owner |
|---|---|---|---|---|---|---|
| `WS02-02-R1` | `WS02-02` | `["API-M03", "API-M17", "OPS-001"]` | `required` | `platform/runtime` | Not required. | Trusted pytest/static app-owner proof. |
| `WS02-02-R2` | `WS02-02` | `["API-M03", "API-M17", "WS02-01"]` | `required` | `platform/runtime` | Not required. | Trusted isolated subprocess import/app-construction proof. |
| `WS02-02-R3` | `WS02-02` | `["API-M03", "API-M17", "OPS-001"]` | `required` | `platform/runtime` | Not required. | Trusted lifespan/shutdown pytest proof. |
| `WS02-02-R4` | `WS02-02` | `["API-M17"]` | `required` | `platform/runtime` | Not required. | Trusted liveness pytest proof. |
| `WS02-02-R5` | `WS02-02` | `["API-M17", "OPS-004"]` | `required` | `platform/runtime` | Not required. | Trusted readiness pytest plus narrow PostgreSQL helper proof. |
| `WS02-02-R6` | `WS02-02` | `["API-M17", "WS02-05"]` | `required` | `platform/runtime` | Not required. | Trusted compatibility/diagnostic health pytest proof. |
| `WS02-02-R7` | `WS02-02` | `["API-M17", "FDN-06", "FDN-07"]` | `required` | `platform/runtime` | Not required. | Trusted release-identity pytest proof. |
| `WS02-02-R8` | `WS02-02` | `["API-M03", "OPS-001", "DBP-01", "FDN-04"]` | `required` | `platform/runtime` | Not required. | Trusted static repository topology/budget-boundary proof plus planning support. |
| `WS02-02-R9` | `WS02-02` | `["OPS-002", "OPS-003", "OPS-004", "FDN-06", "WS02-02"]` | `covered_elsewhere` | `governance` | The canonical plan and release/rollback template preserve the repository-owned evidence boundary; actual deployment, hardening, rollback, and forward-fix execution remain external/later evidence. | Governance/template review. |
| `WS02-02-R10` | `WS02-02` | `["API-M03", "OPS-001", "OPS-002", "OPS-003", "OPS-004", "DBP-01"]` | `deferred` | `planning` | Verified provider topology, platform limits, process/instance design, and connection-budget inputs are not yet available, so Gate B must not fabricate deployment/runtime configuration. | Canonical planning/deferred evidence boundary. |

## 7. Integration / Operational Expectations

- `WS02-01` owns typed settings, environment identity, production-like unsafe
  default rejection, and the environment matrix that WS02-02 consumes.
- `EN-02` owns safe correlation, redaction, event metadata, public error, and
  telemetry primitives. WS02-02 uses safe release identity but does not
  implement broad logging or metrics.
- `EN-03` owns safe provider/control-plane evidence handling, secret lifecycle
  boundaries, and non-closure rules for external proof.
- `WS02-03` owns proxy, host, TLS, CORS, response-class security headers, and
  edge/provider precedence evidence.
- `WS02-04` owns request limits, operation timeouts, cancellation, retry,
  backpressure, rate controls, and stable error behavior beyond health-source
  contracts.
- `WS02-05` owns HTTP media types, OpenAPI, API cache policy, compatibility,
  tombstones, and broader response contracts.
- `WS04-01` owns final database engine/session lifecycle, deployment-wide
  connection budget, provider role/grant planning, and PostgreSQL provider
  evidence.
- `WS05` owns durable worker/job deployment, leases, retries, queue behavior,
  and worker rolling compatibility when durable jobs are introduced.
- `WS07` owns frontend release/build artifact identity, source-map policy, and
  browser-public deployment evidence.
- `WS08` owns broader current test, CI, supply-chain, SBOM/provenance, branch
  protection, and release-evidence gates.
- `WS09` owns full production logging, metrics, dashboards, alerts, release
  context rollout, and operational telemetry.
- `WS10` owns sanitized provider/runtime/control-plane evidence packages,
  secret-store proof, access reviews, backup/recovery evidence, and final
  operational closure.

Operationally, WS02-02 must leave later passes with a truthful runtime contract:
what repository source already proves, what Gate B trusted tests must prove,
what remains deferred, and what still requires provider/runtime evidence.

## 8. Not Part Of This Pass

WS02-02 does not implement or close:

- permanent hosting-provider selection;
- deployed Render service settings;
- actual deployed start command proof;
- blueprint-required versioned deployment/runtime configuration before
  provider topology and connection-budget inputs are available;
- worker, process, instance, autoscaling, keep-alive, recycle, or rolling
  overlap values;
- SQLAlchemy pool-size, overflow, recycle, isolation-level, or final connection
  budget values;
- Neon plan, pooling/proxy mode, region, connection limit, or operational
  reserve proof;
- Dockerfile, container-image, SBOM, artifact registry, signing, or image-scan
  implementation;
- non-root container identity, capability limits, filesystem limits, CPU/memory
  limits, Docker socket restrictions, or platform sandbox proof;
- production runtime observations of startup, shutdown, connection release, or
  health-gated rollout;
- full rollback or forward-fix rehearsal;
- durable worker, scheduler, queue, lease, retry, or background-job topology;
- proxy, host, TLS, CORS, HSTS, direct-origin, or forwarded-header behavior;
- broad request limits, timeouts, rate limits, retry/backpressure policy, or
  stable error work outside the health route contract;
- full logging, metrics, dashboard, tracing, alerting, SLO, or release-gate
  rollout;
- provider-dashboard access, provider account security, secret-store injection,
  rotation, revocation, backup, restore, or DNS/TLS proof.

These are not excuses to ignore the risks. They are explicit boundaries so
later passes can gather the right evidence without WS02-02 claiming it early.

## 9. Related Controls And Remaining Evidence

| Control / Decision | WS02-02 Relationship | Remaining Evidence Boundary |
|---|---|---|
| `API-M03` | WS02-02 advances source and planning for the backend runtime command/process boundary, but does not select unproven worker/process/instance values. R10 defers blueprint-required versioned runtime configuration until topology evidence exists. | Deployed command, process model, keep-alive, recycle, graceful shutdown timing, instance count, and versioned runtime configuration require provider/runtime evidence. |
| `API-M17` | WS02-02 owns source-level liveness, readiness, lifecycle, minimal health response, diagnostic suppression, no-store behavior, and safe release identity. | Deployed health-check binding, health-gate behavior, and runtime observations remain external. |
| `OPS-001` | WS02-02 records API runtime statelessness expectations and absence of tracked worker/scheduler runtime configuration. | Complete frontend/API/worker/scheduler responsibilities, durable shared-service topology, regions, scaling proof, and provider-linked runtime topology remain external/later. |
| `OPS-002` | WS02-02 identifies that no trusted backend runtime image or platform-native runtime artifact is currently repository-proven and requires a safe release/rollback template. | Maintained base image or selected platform runtime strategy, artifact exclusions, scans, rebuild evidence, and executed release records remain later provider/CI/release work. |
| `OPS-003` | WS02-02 preserves platform/container hardening as an explicit deployment evidence need and records that the template must not expose sensitive provider details. | Non-root identity, least capabilities, privileged mode, Docker socket, writable paths, and CPU/memory/process limits require provider/container evidence. |
| `OPS-004` | WS02-02 defines health readiness and requires a release/rollback evidence template. | Health-gated rolling release proof, immutable artifact records, old/new compatibility, rollback/forward-fix execution, and release rehearsal remain external/later. |
| `DBP-01` / `DB-002` | WS02-02 must not invent topology or database connection-budget values and must preserve the formula inputs. R10 stays deferred until those inputs are available. | Provider limits, process topology, pool values, overflow, migration/monitoring reserve, rolling overlap, telemetry, and boundary tests remain WS04/provider evidence. |
| `FDN-04` | WS02-02 follows the evidence-based value selection method. | Numeric runtime, pool, timeout, capacity, and alert values remain unapproved until evidence exists. |
| `FDN-06` | WS02-02 exposes safe source release identity as a building block and defines a release/rollback template. | Full release evidence chain, SBOM/provenance, deployment linkage, CI results, approval record, prior rollback artifact identity, and executed records remain WS08/WS09/WS10 evidence. |
| `FDN-07` | WS02-02 keeps release identity bounded and non-sensitive. | Full structured logging, metrics, tracing, dashboards, alerts, and production correlation rollout remain WS09/WS10 evidence. |

## 10. Completion Criteria

The WS02-02 repository-owned recheck is complete only when all of the following
are true:

- this canonical plan is approved and remains aligned with authority;
- no unresolved owner decision is hidden inside the source-owned scope;
- no production source file or tracked deployment configuration is added unless
  Gate A is reopened and explicitly authorizes it;
- current source still satisfies the lifecycle, liveness, readiness, diagnostic
  health, shutdown, and safe release-identity contracts;
- `backend/tests/support/requirements/ws02_02.json` declares all stable
  WS02-02 requirements with truthful states, scopes, source controls, and
  reasons where required;
- R1-R8 are represented as `required` under `platform/runtime`;
- R9 is represented as `covered_elsewhere` under `governance`;
- R10 is represented as `deferred` under `planning`;
- `backend/tests/platform/runtime/TESTING_RECORD.md` explains the runtime
  evidence risks, scenarios, proof layers, and external gaps;
- fresh trusted runtime/health tests exist under `backend/tests/platform/runtime/`
  and replace the old archived runtime tests as current evidence;
- R2 includes isolated subprocess import proof without starting a live server;
- R7 includes release-identity stability proof for the lifetime of a
  constructed app;
- R8 executable evidence proves only repository-owned topology/budget boundary
  facts and does not claim actual provider/deployed topology proof;
- the narrow PostgreSQL helper proof uses only the dedicated test database and
  does not make the full runtime suite DB-backed;
- `docs/production-readiness/governance/release-rollback-record-template.md`
  exists as a repository-safe artifact without real provider data, secrets,
  deployment IDs, local paths, personal data, payment data, private URLs, raw
  provider payloads, or sensitive provider identifiers;
- checker file/domain/suite scopes pass for the WS02-02 evidence design;
- generated traceability maps executable requirements to current pytest nodes
  and leaves non-executable/external/deferred requirements honestly represented;
- `git diff --check` passes and the diff contains no secrets, credentials,
  provider-private data, real user/payment/provider data, or unsupported
  production-readiness closure claims;
- external Render, Neon, platform-hardening, health-gate, connection-budget,
  deployment-artifact, rollback, and forward-fix gaps remain explicit until
  accepted evidence exists.

Meeting these criteria completes the repository-owned WS02-02 source and
trusted-evidence recheck. It does not satisfy the deferred blueprint-required
versioned deployment/runtime configuration output, and it does not close every
`API-M03`, `OPS-001`, `OPS-002`, `OPS-003`, or `OPS-004` deployment/runtime
obligation because those controls still require accepted provider, runtime,
CI/release, or later-pass evidence.
