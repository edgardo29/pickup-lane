# Environment Matrix

## Purpose

This matrix is the durable GOV-002 environment-isolation artifact for WS02-01.
It records the repository-owned configuration boundaries, public/private
classification, prohibited cross-environment reuse rules, repository-proven
safeguards, and remaining external evidence needed before broader
production-readiness closure.

The matrix is not an environment file, deployment manifest, provider-dashboard
snapshot, or secret inventory containing values. It records names, classes,
rules, and evidence status only.

## Metadata

| Field | Value |
|---|---|
| Related control | `GOV-002` |
| Owning pass | `WS02-01` |
| Primary purpose | Prevent accidental cross-environment provider, credential, database, domain, webhook, log, and CI configuration mixing. |
| Related records | `provider-control-plane-register.md`, `secret-lifecycle-register.md`, `provider-evidence-handling-standard.md`, `provider-evidence-checklist.md` |
| Repository fact sources | Current tracked backend settings, tracked env examples, CI workflow configuration, EN-01/EN-02/EN-03 planning records, WS02 planning records, and current governance registers. |

## Safe Use Rules

- Do not add secret values, token values, private keys, credential-bearing
  database URLs, webhook secret values, Firebase service-account JSON, signed
  URLs, recovery codes, raw provider exports, personal data, or payment data.
- Do not copy values from ignored local `.env` files or provider dashboards into
  this document.
- Environment-variable names and safe configuration categories are allowed.
- A repository-known setting name is not proof that the deployed value,
  provider resource, dashboard setting, or secret-store binding is correct.
- Unknown provider/runtime facts remain unknown until sanitized evidence is
  accepted under the provider-evidence process.

## Evidence State Legend

| State | Meaning |
|---|---|
| `REPOSITORY-PROVEN` | Current tracked source, configuration, or governance records prove this rule or boundary without provider/runtime access. |
| `ACCEPTED EXTERNAL EVIDENCE` | Sanitized external/provider/runtime evidence has been accepted and can be referenced safely. |
| `EXTERNAL EVIDENCE REQUIRED` | The repository defines the expected rule, but provider/runtime/deployment evidence is still required. |
| `LATER-PASS RESPONSIBILITY` | The issue is intentionally owned by a later pass or evidence phase. |
| `UNKNOWN` | The fact is not knowable from current repository evidence and has no accepted external evidence here. |
| `NOT APPLICABLE` | The environment/system relationship does not apply. |

No row in this matrix currently relies on `ACCEPTED EXTERNAL EVIDENCE`.

## Classification Legend

| Classification | Meaning |
|---|---|
| `PRIVATE CREDENTIAL` | Server-side or provider-side credential material. Never browser-public and never committed as a value. |
| `PUBLIC CONFIGURATION` | Browser-visible configuration. Public does not mean provider binding or environment correctness is proven. |
| `SENSITIVE CONFIGURATION` | Non-secret configuration that can expose topology, routing, environment binding, or provider surfaces. |
| `LOCAL OR TEST CONFIGURATION` | Development or automated-test configuration that must not be reused as production-like configuration. |
| `MIXED` | The class includes multiple classifications that must stay separated. |

## Environment Contexts

| Environment / context | Backend `APP_ENV` identity | Configuration boundary | Prohibited reuse or mixing | Repository-proven safeguard | Evidence state | Remaining evidence / owner |
|---|---|---|---|---|---|---|
| Local development | `local` | Developer local environment and ignored local env files for local-only work. | Local databases, provider credentials, origins, and secrets must not be treated as preview, staging, or production evidence. | Typed settings recognize `local`; local defaults are bounded to non-production-like environments. | `REPOSITORY-PROVEN` for source rules; `UNKNOWN` for ignored local values. | Local secret contents are intentionally not inspected. |
| Backend automated test | `test` | Current backend test execution environment. | Automated tests must not use development, preview, staging, or production PostgreSQL databases or provider resources. | Typed settings require the dedicated backend test database identity for `test`; EN-01 requires ordinary tests to avoid uncontrolled provider calls. | `REPOSITORY-PROVEN` for source rules. | Fresh WS02-01 trusted evidence remains a later test/evidence phase. |
| CI | `ci` | GitHub Actions workflow and CI service configuration. | CI must not silently borrow local developer state or production credentials. CI database configuration must remain CI/test scoped. | Backend workflow sets `APP_ENV=ci` and uses a local PostgreSQL service for backend validation. Typed settings require the dedicated backend test database identity for `ci`. | `REPOSITORY-PROVEN` for tracked workflow rules; `UNKNOWN` for GitHub repository settings and secrets. | GitHub branch protection, secret inventory, OIDC, roles, and required-check evidence remain WS10/provider and release-governance evidence. |
| Browser/test context | Not a distinct backend `APP_ENV` by itself. | Browser or frontend test runner configuration when materially distinct from backend automated tests. | Browser tests must not imply a new backend environment identity or reuse production provider/browser configuration unless explicitly authorized. | EN-01 separates ordinary tests from provider/full-stack suites; frontend public config names are tracked. | `LATER-PASS RESPONSIBILITY` and `UNKNOWN` for actual browser runtime bindings. | WS07 and later WS08 test passes own production-build/browser evidence. |
| Provider sandbox / emulator context | Not a distinct backend `APP_ENV` by itself unless a test/runtime explicitly binds one of the canonical values. | Explicit provider-contract or sandbox/emulator evidence boundary. | Provider sandbox resources must not be confused with production provider resources or ordinary deterministic tests. | EN-01 requires provider-contract tests to be explicitly separated; EN-03 records provider evidence boundaries. | `LATER-PASS RESPONSIBILITY`; `EXTERNAL EVIDENCE REQUIRED` for actual provider resources. | Provider-specific sandbox evidence belongs to WS03, WS05, WS06, WS10, or later approved provider passes. |
| Preview | `preview` | Deployed production-like backend environment. | Preview must not load ignored local `.env` configuration or reuse local/test databases, local origins, or placeholder/provider credentials as proof of readiness. | Typed settings classify `preview` as production-like, require deployed environment injection, and reject local-only defaults where WS02-01 owns validation. | `REPOSITORY-PROVEN` for source rules; `EXTERNAL EVIDENCE REQUIRED` for actual deployed bindings. | Deployment/runtime evidence remains WS02-02/WS02-03/WS10 and related provider evidence. |
| Staging | `staging` | Deployed production-like backend environment. | Staging must not reuse local/test configuration and must remain distinct from production unless an approved evidence record says otherwise. | Typed settings classify `staging` as production-like and apply production-like unsafe-default rejection. | `REPOSITORY-PROVEN` for source rules; `EXTERNAL EVIDENCE REQUIRED` for actual provider/runtime resources. | Staging deployment, provider, DNS/TLS, secret-store, and runtime proof remain later evidence. |
| Production | `production` | Deployed production backend environment. | Production must not use local/test/staging/preview databases, local origins, placeholder values, browser-private secrets, or ignored local env files. | Typed settings classify `production` as production-like, reject unsafe/local defaults, and prohibit production API docs enablement through settings. | `REPOSITORY-PROVEN` for source rules; `EXTERNAL EVIDENCE REQUIRED` for actual production provider/runtime resources. | Production provider, secret-store, deployment, DNS/TLS, logs, rotation, revocation, and access evidence remain external/later. |

## System / Configuration Matrix

| System or configuration class | Applicable environments / contexts | Classification | Repository-owned rule and prohibited reuse | Repository-proven safeguard | Evidence state | Remaining external or later evidence |
|---|---|---|---|---|---|---|
| Backend environment identity | Local, backend automated test, CI, preview, staging, production | `SENSITIVE CONFIGURATION` | Backend behavior must use only the canonical identities `local`, `test`, `ci`, `preview`, `staging`, and `production`. Preview, staging, and production are production-like. | Typed backend settings parse and normalize `APP_ENV`, reject blank/unknown values, default CI only when CI is detected, and require deployed runtime markers to use production-like identity. | `REPOSITORY-PROVEN` | Actual deployed `APP_ENV` bindings remain `EXTERNAL EVIDENCE REQUIRED`. |
| PostgreSQL database binding | Local, backend automated test, CI, preview, staging, production | `PRIVATE CREDENTIAL` | Test and CI database bindings must be dedicated to tests. Production-like environments must not use local/test database bindings or unsafe database names. | Typed settings require PostgreSQL SQLAlchemy URLs with host and database name, require the dedicated test database identity for `test` and `ci`, and reject local/unsafe production-like database bindings. | `REPOSITORY-PROVEN` for parser and CI workflow; `EXTERNAL EVIDENCE REQUIRED` for deployed databases. | PostgreSQL/Neon roles, grants, production resources, backups, PITR, connection limits, and app/migration credential separation remain WS04 and WS10 evidence. |
| Firebase Admin backend configuration | Local, preview, staging, production, provider sandbox where explicitly used | `PRIVATE CREDENTIAL` plus `SENSITIVE CONFIGURATION` | Firebase Admin credentials must stay backend-private and environment-specific. Backend Admin credentials must not enter frontend bundles. | Typed settings recognize backend Firebase Admin credential names, validate configured credential forms without provider initialization, require production-like credential/project configuration, and reject placeholders where WS02-01 owns the source rule. | `REPOSITORY-PROVEN` for source validation; `EXTERNAL EVIDENCE REQUIRED` for actual Firebase/GCP projects and IAM. | Firebase project separation, IAM, service-account scope, key inventory, MFA, App Check decision, rotation, revocation, and runtime binding remain WS03 and WS10 evidence. |
| Firebase frontend public configuration | Local frontend, browser/test context, preview, staging, production | `PUBLIC CONFIGURATION` | Browser-public Firebase values are separate from backend Admin credentials and must bind to the intended frontend environment. | Tracked frontend env example and frontend source define only browser-public Firebase configuration names; EN-03 records the public/private boundary. | `REPOSITORY-PROVEN` for names and boundary only; `EXTERNAL EVIDENCE REQUIRED` for deployed binding. | Frontend provider env binding, Firebase project/domain restriction evidence, production artifact inspection, and browser runtime proof remain WS07/WS03/WS10 evidence. |
| Stripe backend payment configuration | Local, preview, staging, production, provider sandbox where explicitly used | `MIXED`: private backend keys, public publishable key, sensitive flags | Stripe secret keys and webhook secrets must stay backend-private. Publishable configuration may be public but must match the intended environment. Test/live mode separation must not be assumed from source names alone. | Typed settings require explicit Stripe values when payments are enabled, validate currency, and reject documented placeholders in production-like environments. | `REPOSITORY-PROVEN` for source validation; `EXTERNAL EVIDENCE REQUIRED` for Stripe account/mode/webhook state. | Stripe dashboard roles, key scope, test/live separation, webhook endpoint/event registration, event delivery, rotation, and revocation remain WS05 and WS10 evidence. |
| Stripe frontend public configuration | Local frontend, browser/test context, preview, staging, production | `PUBLIC CONFIGURATION` plus `SENSITIVE CONFIGURATION` | Frontend publishable key and payment-enable flag must not be confused with backend secret or webhook credentials. | Tracked frontend env example exposes only frontend `VITE_*` Stripe configuration names. | `REPOSITORY-PROVEN` for config surface only; `EXTERNAL EVIDENCE REQUIRED` for deployed values. | Production frontend build/public env scan and frontend/provider binding proof remain WS07 and WS10 evidence. |
| Cloudflare R2 / storage binding | Local, preview, staging, production, provider sandbox where explicitly used | `MIXED`: private credentials and sensitive bucket/account configuration | R2 credentials must stay backend-private. Bucket/account/endpoint bindings must be environment-specific and must not be treated as proof of provider bucket separation. | Typed settings require complete R2 configuration when R2 is configured or production-like, require HTTPS endpoints, reject placeholders in production-like environments, and keep provider calls outside settings parsing. | `REPOSITORY-PROVEN` for source validation; `EXTERNAL EVIDENCE REQUIRED` for actual buckets/accounts/tokens. | Bucket identity, privacy, CORS, token scope, lifecycle, logging, object recovery, rotation, and revocation remain WS06 and WS10 evidence. |
| Backend/API hosts and CORS origins | Local, backend automated test, CI, preview, staging, production, browser/test context | `SENSITIVE CONFIGURATION` | Production-like backend hosts and CORS origins must be explicit and must not reuse local origins unless intentionally approved by later evidence. CORS is not authentication. | Typed settings validate host/origin shape, reject global wildcard hosts, reject wildcard credentialed CORS, and reject localhost host/origin values in production-like environments. | `REPOSITORY-PROVEN` for source validation and current FastAPI-owned behavior; `EXTERNAL EVIDENCE REQUIRED` for deployed edge behavior. | Public host inventory, DNS/TLS, proxy, direct-origin behavior, deployed CORS captures, and provider-added header behavior remain WS02-03 and WS10 evidence. |
| Frontend domains, origins, and API base URL | Local frontend, browser/test context, preview, staging, production | `PUBLIC CONFIGURATION` plus `SENSITIVE CONFIGURATION` | Frontend builds must target the matching API environment and must not silently point production browser traffic at local/test/staging APIs. | Tracked frontend env example and frontend source define the frontend API base URL configuration boundary. | `REPOSITORY-PROVEN` for config surface only; `EXTERNAL EVIDENCE REQUIRED` for deployed frontend/API URL binding. | Production frontend artifact scan, Vercel/env-scope evidence, domain inventory, and browser runtime proof remain WS07, WS02-03, and WS10 evidence. |
| Webhooks | Local webhook development, provider sandbox, preview, staging, production | `PRIVATE CREDENTIAL` plus provider/runtime evidence | Webhook signing secrets must be scoped to the endpoint and environment. Test/live webhook secrets must not be reused. | Backend settings recognize the Stripe webhook signing-secret configuration name and keep it backend-private. | `REPOSITORY-PROVEN` for source surface only; `EXTERNAL EVIDENCE REQUIRED` for provider endpoint state. | Webhook endpoint registration, event list, mode separation, delivery behavior, secret rotation, and replay/reconciliation evidence remain WS05 and WS10 evidence. |
| Backend-private secrets | Local, backend automated test, CI, preview, staging, production | `PRIVATE CREDENTIAL` | Backend-private secrets must not be committed, logged, copied into frontend bundles, or reused across unrelated credential classes. | Typed settings stores secret-bearing values as secret fields where applicable and rejects `INBOX_TOKEN_SECRET` reuse with database, Firebase, Stripe, and R2 credential values where WS02-01 owns the source rule. | `REPOSITORY-PROVEN` for source validation; `EXTERNAL EVIDENCE REQUIRED` for actual secret storage/injection. | Secret-store location, provider-side injection, access controls, rotation, revocation, emergency response, and offboarding remain EN-03/WS10 evidence. |
| Frontend-public configuration | Local frontend, browser/test context, preview, staging, production | `PUBLIC CONFIGURATION` plus `SENSITIVE CONFIGURATION` | Browser-public values must remain separate from backend-private credentials. Public config still requires environment review and deployed binding proof. | Tracked frontend env example uses `VITE_*` names for browser-public configuration; EN-03 records public/private classification. | `REPOSITORY-PROVEN` for names and boundary only; `EXTERNAL EVIDENCE REQUIRED` for deployed artifact values. | Production build scanning, public env allowlist, source-map policy, and browser runtime proof remain WS07 evidence. |
| Logs / telemetry environment identity | Local, backend automated test, CI, preview, staging, production | `SENSITIVE CONFIGURATION` for environment/release labels | Logs and telemetry must carry bounded environment identity without secrets, credentials, free text, raw provider payloads, or private IDs. Environment labels must not obscure which environment produced evidence. | EN-02 defines bounded safe environment label values including `local`, `test`, `ci`, `preview`, `staging`, and `production`; typed settings exposes environment identity and safe release identity. | `REPOSITORY-PROVEN` for primitives; `LATER-PASS RESPONSIBILITY` for full logging/telemetry rollout. | Log sink selection, dashboard/alert setup, production log samples, retention, access, and runtime correlation remain WS09 and WS10 evidence. |
| CI credentials and configuration | CI | `SENSITIVE CONFIGURATION` and possible `PRIVATE CREDENTIAL` if secrets are later added | CI must be CI-scoped and must not borrow local developer env state or production credentials for ordinary validation. | Tracked GitHub Actions backend job sets `APP_ENV=ci`, uses a local PostgreSQL service for backend validation, and does not prove provider/dashboard secrets. | `REPOSITORY-PROVEN` for workflow YAML; `UNKNOWN` for GitHub repository settings and secrets. | GitHub secret inventory, branch protection, required checks, OIDC/federation, protected environments, and admin/access review remain WS08/WS10/release-governance evidence. |
| API docs and DB health exposure flags | Local, backend automated test, CI, preview, staging, production | `SENSITIVE CONFIGURATION` | Production docs/schema and diagnostic exposure must not silently inherit local/test defaults. Health/readiness proof is not the same as settings proof. | Typed settings controls API docs and DB health flags by environment and prevents production docs enablement through settings. | `REPOSITORY-PROVEN` for source flags; `EXTERNAL EVIDENCE REQUIRED` for deployed exposure. | Runtime health/deployability remains WS02-02; docs/OpenAPI/cache/compatibility remains WS02-05; provider/runtime exposure proof remains WS10 where applicable. |
| Browser-test configuration | Browser/test context, provider sandbox where explicitly approved | `PUBLIC CONFIGURATION`, `LOCAL OR TEST CONFIGURATION`, or provider sandbox credential boundary depending on suite | Browser tests must use synthetic/local or explicitly approved sandbox configuration and must not count as provider or production proof unless the suite is authorized for that evidence. | EN-01 separates ordinary deterministic tests, full-stack/browser tests, and provider-contract suites. | `LATER-PASS RESPONSIBILITY` | Exact browser-test environment binding, artifact proof, and provider sandbox proof remain later WS07/WS08/provider evidence. |

## Cross-Environment Isolation Rules

- Backend environment identity must remain one of `local`, `test`, `ci`,
  `preview`, `staging`, or `production`; browser/provider testing does not
  create a new backend `APP_ENV` value by itself.
- Preview, staging, and production are production-like and must receive deployed
  environment injection rather than ignored local `.env` values.
- Automated tests and CI must use the dedicated backend test database identity
  and must not use development, preview, staging, or production databases.
- Production-like backend database bindings must not use local hosts,
  development/local/test database names, or placeholder values.
- Backend-private credentials must not become frontend-public configuration.
- Browser-public Firebase and Stripe values must remain distinct from Firebase
  Admin credentials, Stripe secret keys, Stripe webhook secrets, database
  credentials, R2 credentials, and inbox token secrets.
- `INBOX_TOKEN_SECRET` must be independent from the database URL and known
  backend-private provider credentials where repository source can compare the
  configured values.
- Provider resource names, project IDs, bucket names, dashboard settings, and
  mode separation are not proven merely because an environment-variable name is
  present in tracked source.
- Logs, telemetry, and release metadata must retain bounded environment identity
  and must not contain secrets, raw provider payloads, personal data, payment
  data, or unbounded private identifiers.
- CI configuration must remain CI-scoped and must not silently inherit local
  developer state or production credentials.

## Known External Gaps And Later Owners

| Gap | Current matrix state | Later owner / evidence path |
|---|---|---|
| Deployed backend runtime environment values | `EXTERNAL EVIDENCE REQUIRED` | WS02-02 and WS10/provider evidence |
| Public host, DNS, TLS, proxy, direct-origin, and deployed CORS behavior | `EXTERNAL EVIDENCE REQUIRED` | WS02-03 and WS10/provider evidence |
| Request limits, timeouts, rate/error runtime behavior beyond settings-owned config | `LATER-PASS RESPONSIBILITY` | WS02-04 |
| HTTP/OpenAPI/cache/compatibility deployed behavior | `LATER-PASS RESPONSIBILITY` | WS02-05 |
| Frontend production build, public env binding, source maps, and artifact inspection | `LATER-PASS RESPONSIBILITY` | WS07 |
| Provider accounts, access, MFA, service identities, secret stores, rotation, revocation, and offboarding | `EXTERNAL EVIDENCE REQUIRED` | EN-03/WS10 provider-control-plane and secret-lifecycle evidence |
| Firebase project separation and Auth/Admin provider settings | `EXTERNAL EVIDENCE REQUIRED` | WS03 and WS10 |
| Stripe account/mode separation, webhook endpoint state, and payment provider evidence | `EXTERNAL EVIDENCE REQUIRED` | WS05 and WS10 |
| R2 bucket/account/token separation and storage provider evidence | `EXTERNAL EVIDENCE REQUIRED` | WS06 and WS10 |
| PostgreSQL/Neon roles, grants, production resources, backups, PITR, and connection limits | `EXTERNAL EVIDENCE REQUIRED` | WS04 and WS10 |
| Logs/metrics provider selection, sink separation, dashboards, alerts, retention, and access | `LATER-PASS RESPONSIBILITY` | WS09 and WS10 |
| GitHub repository settings, branch protection, required checks, secrets, and OIDC/federation | `EXTERNAL EVIDENCE REQUIRED` | WS08/WS10/release-governance evidence |

## Maintenance Rules

- Update this matrix when a pass adds, removes, or changes a material
  environment/configuration class.
- Do not change an evidence state from `UNKNOWN` or `EXTERNAL EVIDENCE REQUIRED`
  to a stronger state without sanitized accepted evidence.
- Do not add exact provider values unless an approved evidence-handling decision
  says the value is safe and necessary for repository exposure.
- Keep secret lifecycle details in `secret-lifecycle-register.md`; keep
  provider account/control-plane details in `provider-control-plane-register.md`.
  This matrix should reference those boundaries rather than duplicating them.
