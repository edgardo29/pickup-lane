# WS02-01 - Typed Settings And Environment Isolation

## At A Glance

| Field | Value |
|---|---|
| Pass ID | WS02-01 |
| Pass Name | Typed Settings And Environment Isolation |
| Primary Domain | Backend configuration, environment identity, and environment-isolation evidence |
| Primary Controls | GOV-002, API-M01, API-M02 |
| Current Source Assessment | Existing backend typed settings and environment-isolation foundation is materially correct; no broad production source correction is currently proven necessary. |
| Required Pass-Owned Artifact | `docs/production-readiness/governance/environment-matrix.md` |
| Trusted Test Scope | Required under the EN-01 architecture; exact executable test design belongs to the test/evidence phase, not this plan. |
| External Evidence Boundary | Provider dashboards, deployed runtime bindings, secret-store configuration, rotation, revocation, and runtime environment proof require later redacted external evidence. |

## 1. Purpose

WS02-01 establishes the repository-owned foundation for typed backend settings and explicit environment isolation. The pass makes the backend's configuration boundary intentional, validates unsafe production-like configuration before readiness, and defines the durable environment matrix needed to prevent accidental cross-environment reuse of databases, provider projects, credentials, domains, webhooks, and public configuration.

The pass is not a broad deployment, provider-dashboard, runtime-monitoring, or frontend-build pass. Its job is to make configuration parsing, environment identity, source-owned config behavior, and repository evidence precise enough that later runtime and provider passes can verify the deployed system without guessing.

## 2. Why This Matters

Configuration mistakes are production-readiness defects even when application logic is correct. A backend that silently accepts local defaults in production-like environments can connect to the wrong database, expose development docs, accept unintended origins, reuse provider credentials, or produce evidence that cannot be tied to a real deployment environment.

WS02-01 reduces that risk by requiring:

- one authoritative typed backend settings boundary;
- explicit local, test, CI, preview, staging, and production environment identity;
- production-like unsafe-default rejection before readiness;
- backend-private provider configuration validation without provider SDK/network side effects during parsing;
- clear public/private configuration boundaries;
- a complete GOV-002 environment matrix that records what the repository can prove and what must be proven externally.

This keeps the repository honest: source-level invariants are tested and documented in the repo, while provider/runtime facts are preserved as open evidence until they are verified through the appropriate later passes.

## 3. Requirements

These stable IDs define the WS02-01 requirement surface for future requirement declarations, testing records, checker traceability, and completion review. They intentionally describe what must be true, not exact pytest node IDs or implementation file names.

| Requirement ID | Requirement |
|---|---|
| WS02-01-R1 | The backend must have one authoritative typed settings boundary for source-owned configuration parsing and validation. |
| WS02-01-R2 | The backend must use explicit environment identity for `local`, `test`, `ci`, `preview`, `staging`, and `production` behavior. |
| WS02-01-R3 | Production-like environments must reject missing, malformed, unsafe, or local-only configuration before readiness instead of silently falling back to development defaults. |
| WS02-01-R4 | Database configuration must be environment-isolated so automated tests, CI, local development, preview, staging, and production cannot accidentally reuse unsafe database bindings. |
| WS02-01-R5 | Backend-private provider configuration must be validated as backend-private configuration and must not be confused with frontend-public configuration. |
| WS02-01-R6 | Public and private configuration boundaries must remain explicit for backend secrets, frontend-public values, provider identifiers, domains, origins, webhooks, and deployment bindings. |
| WS02-01-R7 | Settings parsing and safe initialization must be provider-free and must not require provider network calls, provider SDK initialization, database migrations, or unrelated runtime side effects merely to validate configuration. |
| WS02-01-R8 | Pass-owned secrets and secret-like configuration must remain independent where repository source can prove independence, and reused/cross-boundary values must be rejected where WS02-01 owns the validation boundary. |
| WS02-01-R9 | Repo-owned environment documentation and example configuration must stay consistent with the authoritative typed settings contract. |
| WS02-01-R10 | The repository must maintain a complete GOV-002 environment matrix covering all required environments, system/config classes, public/private boundaries, repository-provable isolation, and external evidence needs. |
| WS02-01-R11 | WS02-01 evidence must clearly separate repository-provable configuration behavior from external provider, deployment, secret-store, rotation, revocation, DNS/TLS, webhook, and runtime evidence. |

## 4. Technical Design / Contracts

### 4.1 Authoritative Backend Settings Boundary

Backend configuration must flow through a typed settings boundary owned by the backend. The boundary must define the accepted environment names, parse supported configuration values, normalize source-owned representations, and reject invalid values in the environment class where they become unsafe.

The authoritative settings boundary is responsible for source-owned configuration semantics. Other backend modules may consume validated settings, but they must not become competing configuration authorities with independent production-default behavior.

### 4.2 Environment Identity And Production-Like Rules

The canonical backend environment identities for this pass are:

- `local`;
- `test`;
- `ci`;
- `preview`;
- `staging`;
- `production`.

Preview, staging, and production are production-like environments. Production-like environments must not load ignored local `.env` files as authoritative deployment configuration, must not silently accept local-only defaults, and must fail before readiness when required production-like configuration is missing, malformed, or unsafe.

Local, test, and CI may use controlled development or automated-test defaults only where those defaults are explicitly bounded to that environment and cannot be mistaken for production-like readiness.

### 4.3 Database Configuration And Environment Isolation

Database configuration must be validated according to environment identity. The pass-owned contract requires:

- automated tests and CI use dedicated non-production database bindings;
- production-like environments reject local database bindings and unsafe database names;
- database URL parsing does not silently repair malformed production-like values;
- environment documentation and examples do not imply that production-like database configuration may be copied from local or test configuration.

WS02-01 does not own final database process counts, connection pool sizing, runtime connection release proof, or provider deployment topology. Those remain downstream runtime/provider evidence.

### 4.4 Backend-Private Provider Configuration

Backend-private provider configuration includes secret-bearing or server-only configuration for systems such as Firebase Admin, Stripe server-side configuration, R2/storage credentials, webhook secrets, inbox token secrets, and other backend-only provider bindings.

WS02-01 owns typed source-level validation and environment-boundary rules for backend-private provider configuration where the repository can validate the value class without contacting the provider. The pass must preserve the existing safe pattern that provider configuration parsing does not require provider network access or provider SDK initialization.

WS02-01 must not claim provider-dashboard state, provider access controls, credential rotation, revocation, deployed secret injection, webhook installation, or bucket/project separation as fully proven by repository tests alone.

### 4.5 Public / Private Configuration Separation

Frontend-public configuration and backend-private configuration must remain separate concepts.

Repository documentation and typed settings rules must not blur:

- public provider identifiers used by browser code;
- backend-only provider credentials;
- backend-only webhook secrets;
- server-side database credentials;
- frontend API base URLs and public deployment bindings;
- backend CORS origins and host allowlists.

WS02-01 may define invariants that prevent unsafe source-owned mixing, but deployed frontend public configuration and production artifact validation belong to WS07. Provider dashboard evidence and secret-store proof belong to WS10 and related provider/control-plane work.

### 4.6 Provider-Free Settings Parsing And Safe Initialization Boundary

Settings parsing and validation must be safe to execute as a source-level readiness check. It must not require:

- provider network calls;
- provider SDK initialization;
- database migrations;
- background worker startup;
- deployment-specific process topology;
- unrelated application side effects.

This supports API-M01 by keeping import/startup boundaries controlled, but WS02-01 does not close the full runtime lifecycle control. Startup/shutdown lifecycle ownership, deployed runtime health proof, resource teardown, and process/connection topology are owned by WS02-02 and later runtime evidence.

### 4.7 Pass-Owned Environment Matrix Contract

WS02-01 owns the GOV-002 environment matrix artifact at:

`docs/production-readiness/governance/environment-matrix.md`

The matrix is a governance and evidence-boundary artifact. It must not contain secrets, credential values, private keys, real tokens, full database URLs, webhook secret values, provider access tokens, or copied provider dashboard secrets.

The matrix must cover, at minimum, these environments:

- local development;
- backend automated test;
- CI;
- browser/test environment when distinct from backend automated test;
- preview;
- staging;
- production.

The matrix must cover, at minimum, these system/config classes:

- PostgreSQL databases;
- Firebase frontend/public project configuration;
- Firebase Admin/backend-private configuration;
- Stripe public and backend-private configuration;
- R2/storage configuration;
- frontend domains and origins;
- backend/API domains and origins;
- webhooks;
- backend-private secrets;
- frontend-public configuration;
- logs/telemetry environment identity;
- CI credentials and configuration;
- other provider or environment bindings introduced by the repository.

For each relevant environment and system/config class, the matrix must record:

- expected environment identity;
- configuration owner;
- public or private status;
- repository-known configuration rule;
- repository-provable isolation;
- external proof needed;
- prohibited cross-environment reuse;
- unknown or open evidence.

The matrix may use redacted provider identifiers or descriptive placeholders when exact values are secret or unavailable, but it must clearly distinguish known, unknown, not applicable, repository-proven, and externally required evidence.

### 4.8 Repository And External Evidence Boundary

WS02-01 evidence must make the boundary explicit:

- Repository evidence can prove source-owned parsing, typed validation, unsafe-default rejection, documentation consistency, and requirement traceability.
- Repository evidence can prove that certain values are rejected or classified without contacting providers.
- Repository evidence cannot prove provider dashboards, deployed secret-store injection, provider project separation, live DNS/TLS state, webhook installation, rotation/revocation, production runtime health, production logs, or production access controls.

Any plan, testing record, or completion claim must preserve that distinction.

## 5. Implementation Scope

WS02-01 owns these changes and artifacts:

- canonical planning for typed settings and environment isolation;
- source-level correction only if a concrete contradiction is found between current backend behavior and the requirements above;
- repository-owned environment documentation/example consistency for backend settings;
- the GOV-002 environment matrix artifact at `docs/production-readiness/governance/environment-matrix.md`;
- WS02-01 requirement declarations under the EN-01 testing architecture;
- a WS02-01 testing/risk record that distinguishes executable repository evidence from external evidence;
- compatibility notes for downstream passes when settings behavior affects runtime, provider, frontend, or deployment work.

The current accepted source assessment is that the backend typed settings and environment-isolation foundation is materially correct and no broad production source correction is currently proven necessary. Future implementation work should therefore be targeted: preserve the existing foundation unless a source-level gap is demonstrated against this plan.

## 6. Testing And Evidence

WS02-01 testing and evidence must follow the EN-01 testing architecture. Historical pre-EN-01 tests may be useful for context but must not be treated as trusted production-readiness evidence.

The trusted evidence package for this pass must include, at a high level:

- stable WS02-01 requirement declarations using the requirement IDs in this plan;
- a human testing/risk record explaining source-owned coverage, risk decisions, and remaining evidence boundaries;
- trusted current tests or static checks for typed settings behavior, environment identity, unsafe-default rejection, database isolation, backend-private provider config validation, public/private config separation, provider-free parsing, and documentation/config consistency where those are repository-provable;
- checker/traceability evidence showing the WS02-01 requirement declarations remain complete under the EN-01 architecture;
- the GOV-002 environment matrix review as documentation/governance evidence;
- explicit external-evidence entries for provider dashboards, deployed runtime configuration, secret-store injection, rotation, revocation, DNS/TLS, webhooks, production logs, and provider access controls.

This section intentionally does not prescribe exact pytest node IDs, fixture names, checker internals, or individual test cases. Those belong to the test/evidence design phase and should be generated or collected from the current trusted test suite rather than hand-maintained in this planning document.

## 7. Integration / Operational Expectations

WS02-01 integrates with surrounding passes as follows:

- EN-01 provides the trusted backend testing/checker architecture used for WS02-01 requirement traceability.
- EN-02 provides safe correlation, event, redaction, public-error, and telemetry label primitives, including accepted environment labels such as preview.
- EN-03 provides secrets/control-plane/provider-evidence boundaries and records where repository evidence stops.
- WS02-02 owns runtime lifecycle, app startup/shutdown resource ownership, deployed readiness behavior, and runtime process/resource proof.
- WS02-03 owns proxy/host/TLS/security-header/runtime CORS evidence and deployed edge behavior.
- WS02-04 owns request limits, timeouts, rate limiting, and stable error behavior outside the settings foundation.
- WS02-05 owns HTTP/OpenAPI/cache/compatibility contracts and API documentation exposure decisions beyond the settings boundary.
- WS07 owns production frontend build, frontend-public environment binding, public artifact validation, and source-map policy.
- WS10 and provider/control-plane work own provider dashboard state, access controls, secret-store bindings, rotation, revocation, and sanitized provider evidence packages.

Operationally, WS02-01 must leave later passes with a clear map of which environment/config facts are source-owned, which are documented but externally unproven, and which require provider or deployment evidence before final production readiness.

## 8. Not Part Of This Pass

WS02-01 does not implement or close:

- complete provider-dashboard verification;
- provider access controls, MFA, account ownership, or role review;
- managed secret-store injection proof;
- credential rotation or revocation proof;
- live DNS, TLS, proxy, CDN, or deployment routing proof;
- production runtime startup/shutdown/health proof;
- process counts, worker topology, or database connection budgets;
- frontend production artifact validation or browser-public environment proof;
- full logging rollout, metrics exporters, dashboards, tracing, alerting, or release gates;
- API request limits, timeout policy, cache policy, or compatibility guarantees beyond settings-owned configuration;
- broad production application behavior unrelated to typed settings and environment isolation.

These boundaries are not deferrals of known WS02-01 source defects. They are ownership boundaries for later production-readiness evidence.

## 9. Related Controls And Remaining Evidence

| Control / Decision | WS02-01 Relationship | Remaining Evidence Boundary |
|---|---|---|
| GOV-002 | WS02-01 owns the complete environment matrix and source-level environment-isolation contract. | Provider dashboard, deployed binding, secret-store, webhook, log, and CI credential evidence remain external until verified. |
| API-M01 | WS02-01 supports controlled initialization by keeping settings parsing provider-free and side-effect bounded. | Runtime lifecycle, graceful teardown, startup/shutdown health, process topology, and connection-release proof remain WS02-02/runtime evidence. |
| API-M02 | WS02-01 owns typed production configuration validation and unsafe-default rejection before readiness. | Deployment-specific proof that managed environments supply correct values remains runtime/provider evidence. |
| FDN-03 | WS02-01 supports environment-aware API docs/config exposure rules. | Final public docs/schema exposure policy and deployed behavior are confirmed in HTTP/deployment passes. |
| FDN-04 | WS02-01 must not invent provider limits, timeout numbers, pool counts, or deployment budgets without evidence. | Evidence-based sizing and runtime limits remain later pass work. |
| FDN-07 | WS02-01 provides environment identity that observability/release metadata can use safely. | Full observability rollout remains later-scope work beyond EN-02 primitives. |
| WS10 Provider / Secrets Work | WS02-01 identifies provider and secret evidence needs through the environment matrix. | Provider control-plane screenshots/exports, secret-store configuration, rotation, revocation, and access evidence remain WS10/provider-owned. |

## 10. Completion Criteria

WS02-01 is complete only when all of the following are true:

- the canonical plan is reconciled with the authoritative production-readiness requirements and current repository source;
- any source-level settings defects proven against this plan are corrected without broad unrelated application changes;
- the GOV-002 environment matrix exists at `docs/production-readiness/governance/environment-matrix.md` and covers the required environments, system/config classes, public/private boundaries, repository-provable rules, and external evidence needs;
- WS02-01 requirement declarations exist under the EN-01 architecture and use stable requirement IDs from this plan;
- a WS02-01 testing/risk record explains trusted repository evidence, risk decisions, and remaining external evidence;
- trusted current tests/static checks provide repository-provable evidence for the settings and environment-isolation requirements;
- checker/traceability validation passes for the WS02-01 requirement set under the EN-01 architecture;
- documentation and example configuration do not contradict the authoritative settings contract;
- no secret values, credential-bearing commands, provider tokens, private keys, database URLs, real user data, or copied provider secrets are introduced into source or artifacts;
- completion claims do not falsely close provider-dashboard, deployed runtime, secret-store, rotation, revocation, DNS/TLS, webhook, frontend artifact, or runtime observability evidence.

When these criteria are satisfied, WS02-01 may be accepted as the repository-owned typed settings and environment-isolation foundation while preserving downstream external evidence obligations.
