# WS03-03B - App Check, Admin MFA, And Firebase/GCP Governance

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS03-03B` |
| Track | `WS03` |
| Type | Provider/security implementation and evidence boundary |
| Primary controls | `IAM-008`, `IAM-010`, `IAM-011` |
| Authority basis | Current accepted `develop`; locked production-readiness audits; 163-control checklist; final remediation plan; master blueprint `WS03-03`; approved decision `IDB-04`; accepted `WS03-01`, `WS03-02`, `WS03-03A`, `EN-02`, and `EN-03` boundaries |
| Depends on | `WS03-01`; `WS03-02`; `WS03-03A`; `EN-02`; `EN-03`; approved decisions `IDB-01` through `IDB-04` |
| Trusted test scope | `backend/tests/workflows/app_check_provider_security` |

## 1. Purpose

WS03-03B establishes the source-owned Firebase App Check foundation for the
supported Pickup Lane browser client while preserving the provider, runtime,
administrator MFA, and Firebase/GCP credential-governance evidence boundaries.

The pass adds repository-controlled App Check transport, verification,
route-classification, failure, and observability contracts so the application
can safely run in disabled or observe mode and can fail closed in enforced mode
when an owner later approves provider rollout. It also records that local source
evidence does not prove live Firebase App Check registration, production
enforcement, administrator MFA enrollment, or GCP service-account governance.

The historical local branch `pr/WS03-03B1` and commit
`2796a7bc7eb2efcc5d822dafbbf4a1d4c95c7bd8` are provenance only. They provide
useful App Check implementation ideas, but the current pass identity is
`WS03-03B`; no current authoritative source approves a `WS03-03B1` subdivision.

## 2. Why This Matters

The locked audits and approved decisions require stronger protection around
Firebase-sensitive behavior, supported-browser authenticity, and provider
credentials. WS03-03A completed the repository-owned recent-authentication and
frontend step-up work for high-risk actions, but it deliberately left App
Check, administrator MFA, and Firebase/GCP credential governance unclosed.

Firebase App Check is defense in depth. It can help distinguish traffic from
the supported browser app once provider registration and runtime validation are
ready. It must not become a replacement for Firebase Authentication, server-side
authorization, recent authentication, rate limiting, request limits,
idempotency, payment safeguards, or object-level access control.

Administrator MFA and Firebase/GCP credential governance are mostly provider
and operations facts. Local tests can prove that Pickup Lane does not overclaim
or bypass those facts, but they cannot prove Firebase console enrollment,
Identity Platform capability, GCP IAM roles, service-account key inventory,
secret-store injection, rotation, revocation, monitoring, or production runtime
binding.

## 3. Current Authority Reconciliation

### 3.1 Current Pass Identity

Current authority supports one coherent pass:

```text
WS03-03B - App Check, Admin MFA, And Firebase/GCP Governance
```

No current accepted planning document or decision record authorizes a
`WS03-03B1` / `WS03-03B2` split. The old WIP's `WS03-03B1` naming is historical
provenance only and must not define the current branch, requirements, or file
set.

### 3.2 Applicable Controls

| Control / Decision | Current Meaning For WS03-03B |
|---|---|
| `IAM-008` | Recent auth and source-owned step-up are accepted in WS03-03A. Administrator MFA remains provider/governance evidence unless a documented provider limitation and compensating control exists. |
| `IAM-010` / `IDB-04` | Firebase App Check applies to the supported Pickup Lane web client as defense in depth. Adoption requires provider sandbox or staging validation, observation, failure testing, staged enforcement, and documented rollback. |
| `IAM-011` | Firebase/GCP Admin access should use managed identity, ADC, or workload identity where supported. Long-lived service-account keys require least privilege, restricted storage, inventory, rotation, monitoring, and emergency revocation. |
| `EN-02` | App Check diagnostics and errors must use safe public error and bounded event/telemetry primitives without raw tokens, provider payloads, or high-cardinality labels. |
| `EN-03` | Provider-control-plane and credential facts require sanitized evidence. Repository artifacts must not contain secrets, raw provider screenshots, private account data, recovery material, or unsupported closure claims. |
| `WS03-01` | Firebase ID-token verification, project-bound Admin SDK initialization, active local account/admin authority, and external provider closure boundaries remain prerequisites. |
| `WS03-02` | Local account lifecycle, deletion, recovery, same-UID sync, and final-admin protections remain prerequisites. |
| `WS03-03A` | Provider `auth_time`, recent-auth route classification, `require_recent_active_admin`, caller-owned step-up, credential linking, and no-global-replay behavior are accepted and must not be weakened. |
| `WS10` | Broad provider access, secret storage, rotation/revocation, emergency response, and access-review evidence remain later operational closure unless this pass receives accepted sanitized evidence for a narrower Firebase/GCP fact. |

### 3.3 Repository Truth On The Accepted Baseline

Accepted current baseline: `19300926139be30f271107a318892f9ef1b2356f`.

Current repository truth shows:

- backend settings do not yet define `FIREBASE_APP_CHECK_MODE` or
  `FIREBASE_APP_CHECK_APP_ID`;
- backend CORS allowed headers are `Accept`, `Authorization`, `Content-Type`,
  and `X-Request-ID`;
- backend application middleware currently includes request body limits, CORS,
  trusted host, response security headers, and correlation ID middleware;
- no backend App Check middleware, policy, verifier, public error contract, or
  route classification exists;
- `backend/firebase_admin_client.py` initializes Firebase Admin from existing
  backend-private credentials and project id and verifies ID tokens, but does
  not verify App Check tokens;
- accepted WS02-04C1 and WS02-04C2 evidence intentionally centralize Firebase
  Admin production provider/network calls in `backend/firebase_admin_client.py`
  and inventory that file as the Firebase Admin runtime boundary;
- `frontend/src/lib/firebase.js` initializes Firebase app/auth only and already
  uses browser-public `VITE_FIREBASE_APP_ID` as the Firebase web app identity;
- `frontend/src/lib/apiClient.js` does not attach an App Check header;
- current dependencies already include Firebase Admin SDK and Firebase Web SDK
  support, so no dependency-file edit is required for App Check source work;
- direct signed provider uploads use raw `fetch(uploadUrl)` and do not go
  through the shared Pickup Lane API client;
- `frontend/package.json` has `npm run test:unit`;
- accepted WS03-03A evidence has a 25-route recent-auth policy, 107-route admin
  mutation partition, `require_recent_active_admin`, and frontend caller-owned
  step-up;
- accepted WS03-03A requirement IDs `R12`, `R13`, and `R14` remain deferred with
  zero pytest mappings.

## 4. Requirements

| ID | Requirement | What It Means | Why It Matters |
|---|---|---|---|
| `WS03-03B-R1` | App Check mode and configuration are explicit and bounded. | Backend supports only `disabled`, `observe`, and `enforced` modes. Local, test, and CI default to `disabled`; production-like environments must set the mode explicitly. Observe and enforced backend modes require a non-blank `FIREBASE_APP_CHECK_APP_ID` that identifies the supported Pickup Lane Firebase web app. Frontend source uses browser-public `VITE_` App Check configuration, reuses existing `VITE_FIREBASE_APP_ID`, and defaults to disabled when unconfigured. | App Check rollout must be deliberate, environment-specific, bound to the intended supported web app, and unable to silently enforce or silently disable in production-like environments. |
| `WS03-03B-R2` | Frontend App Check token acquisition and transport are centralized. | The browser initializes Firebase App Check lazily from the existing Firebase app and `ReCaptchaEnterpriseProvider` only when enabled and configured. Pickup Lane API requests attach a token through `X-Firebase-AppCheck`; arbitrary absolute URLs and direct signed provider uploads do not. | Prevents scattered token logic, credential exposure, and accidental provider-upload or third-party leakage. |
| `WS03-03B-R3` | Backend App Check verification is provider-owned, supported-app bound, and fail closed in enforced mode. | Backend verification uses Firebase Admin SDK App Check verification through the accepted centralized Firebase provider boundary, then compares the provider-verified App ID claim exactly with configured `FIREBASE_APP_CHECK_APP_ID`. It does not decode JWTs manually, trust client claims, accept query/body tokens or client-supplied App IDs, or expose raw claims. Outcomes are bounded as valid, missing, invalid, or provider unavailable. | App Check must depend on Firebase provider verification and the expected Pickup Lane web app identity, not app-authored assertions or unsafe token parsing, while preserving accepted C1/C2 provider-boundary ownership. |
| `WS03-03B-R4` | App Check middleware applies correct mode semantics and preserves HTTP contracts. | Disabled mode bypasses verification. Observe mode records bounded outcomes and continues. Enforced mode denies missing/invalid tokens with safe `403` responses and provider-unavailable outcomes with safe `503` responses before route side effects. CORS, security headers, and correlation IDs remain present on denials. | Rollout and enforcement must be predictable, safe, and compatible with accepted WS02 HTTP/error contracts. |
| `WS03-03B-R5` | Route and caller policy is classified and fails closed for drift. | Current supported browser API routes are included; infrastructure, health, docs/OpenAPI, static paths, Stripe webhook/provider callbacks, and direct signed provider uploads are excluded. Registered unclassified API routes must fail policy construction or trusted evidence; genuinely unmatched paths may continue to normal 404/405 handling. | App Check should cover supported browser API traffic without breaking provider callbacks or pretending infrastructure probes are browser clients. |
| `WS03-03B-R6` | App Check remains defense in depth and cannot weaken existing safeguards. | App Check must not replace Firebase Authentication, local authorization, recent-auth/step-up, rate limits, request limits, idempotency, payment safeguards, or resource authorization. Authorization and App Check headers stay separate, and low-level frontend transport does not globally replay mutations. | Prevents an abuse-control feature from becoming a weaker identity or authorization source. |
| `WS03-03B-R7` | Evidence and negative-space checks prevent unsafe bypasses and false closure. | Trusted evidence inventories source for query/body token acceptance, client-supplied App ID trust, missing verified-App-ID comparison, fake app-owned App Check state, client-exposed bypass flags, local/test bypass leakage into production-like mode, verifier fail-open behavior, unsafe telemetry, raw token/App ID logging/storage, route-policy drift, recorder failure bypasses, and pytest mappings that falsely close external/provider facts. | A green App Check happy path is insufficient if alternate paths can bypass it or evidence overclaims provider truth. |
| `WS03-03B-R8` | Administrator MFA remains provider/governance evidence. | Local source may preserve recent-auth and admin-access compensating controls, but it must not claim Firebase/Identity Platform MFA support, enrollment, enforcement, factor policy, break-glass, existing-admin migration, recovery, account-access review, or provider limitation proof. | IAM-008 includes administrator MFA, but source-only tests cannot prove live provider MFA posture. |
| `WS03-03B-R9` | Firebase/GCP credential governance remains external unless sanitized evidence is accepted. | Repository artifacts may name expected evidence and preserve safe boundaries, but actual service-account mechanism, least privilege, key inventory, storage, rotation, revocation, monitoring, emergency response, ADC/workload identity, provider IAM, and permanent-host binding remain external/provider facts. | IAM-011 cannot be honestly closed by code inspection or synthetic pytest. |
| `WS03-03B-R10` | Production App Check rollout remains gated by provider/runtime evidence and owner approval. | Source may support observe/enforced modes, but production enforcement requires accepted provider/staging evidence for app registration, valid/missing/invalid/provider-unavailable behavior, false-positive review, rollback, debug-token handling, and owner approval. | IDB-04 requires staged adoption and forbids production enforcement before user-impact and recovery behavior are understood. |

## 5. Requirement Declaration Design

Gate B must create:

```text
backend/tests/support/requirements/ws03_03b.json
```

Planned declaration states:

| Requirement | State | Scope | Source Controls | Reason |
|---|---|---|---|---|
| `WS03-03B-R1` | `required` | `workflows/app_check_provider_security` | `["IAM-010", "IDB-04", "WS02-01", "EN-03", "WS03-03B"]` | App Check mode/configuration and supported-web-app identity binding are source-owned and must be executable in trusted evidence. |
| `WS03-03B-R2` | `required` | `workflows/app_check_provider_security` | `["IAM-010", "IDB-04", "IAM-003", "FE-M09", "WS03-03B"]` | Frontend transport and non-leakage are repository-owned browser-source behavior. |
| `WS03-03B-R3` | `required` | `workflows/app_check_provider_security` | `["IAM-010", "IDB-04", "IAM-001", "WS03-01", "WS03-03B"]` | Backend verifier behavior must use provider verification, verified App ID comparison, and bounded outcomes. |
| `WS03-03B-R4` | `required` | `workflows/app_check_provider_security` | `["IAM-010", "IDB-04", "WS02-03", "WS02-04A", "WS03-03B"]` | Mode enforcement, safe denial, and HTTP contract preservation are repository-owned. |
| `WS03-03B-R5` | `required` | `workflows/app_check_provider_security` | `["IAM-010", "IDB-04", "WS02-03", "WS03-03B"]` | Route/caller classification must fail closed for current source drift. |
| `WS03-03B-R6` | `required` | `workflows/app_check_provider_security` | `["IAM-008", "IAM-010", "IAM-011", "IDB-04", "WS03-03A", "WS03-03B"]` | App Check must preserve existing identity, authz, recent-auth, replay, and business safeguards. |
| `WS03-03B-R7` | `required` | `workflows/app_check_provider_security` | `["IAM-010", "IAM-011", "EN-02", "EN-03", "WS03-03B"]` | Negative-space evidence must block bypasses, unsafe observation behavior, and false provider/governance closure. |
| `WS03-03B-R8` | `deferred` | `governance` | `["IAM-008", "WS03-03B", "WS10"]` | Administrator MFA provider/governance facts cannot be closed by local pytest and must have zero pytest mappings. |
| `WS03-03B-R9` | `deferred` | `governance` | `["IAM-011", "EN-03", "OPS-005", "OPS-006", "OPS-007", "OPS-025", "WS03-03B", "WS10"]` | Firebase/GCP credential-governance facts require sanitized provider/operations evidence and must have zero pytest mappings. |
| `WS03-03B-R10` | `deferred` | `governance` | `["IAM-010", "IDB-04", "WS03-03B", "WS10"]` | Production App Check rollout evidence and approval remain external/runtime and must have zero pytest mappings. |

Requirements `R8`, `R9`, and `R10` are part of WS03-03B's honest evidence
model, but they are not executable pytest requirements in Gate B.

## 6. Technical Design / Contracts

### 6.1 App Check Modes

Backend mode is centralized as `FIREBASE_APP_CHECK_MODE`. Supported web-app
identity is centralized as `FIREBASE_APP_CHECK_APP_ID`.

`FIREBASE_APP_CHECK_APP_ID` is a non-secret Firebase App ID for the supported
Pickup Lane Firebase web app accepted by this backend. It is separate from
`FIREBASE_PROJECT_ID`, may be omitted in disabled mode, and is required to be
configured and non-blank in observe and enforced modes. It must never be logged,
emitted as telemetry, returned in a response, or used as user identity or
authorization authority even though it is not a credential.

| Mode | Backend Behavior | Intended Use |
|---|---|---|
| `disabled` | No App Check verification, no App Check denial, and no App Check observation event required. `FIREBASE_APP_CHECK_APP_ID` may be omitted. | Local development, automated tests, CI, and any production-like environment only when explicitly configured during rollout preparation. |
| `observe` | Applicable routes verify when possible, require configured `FIREBASE_APP_CHECK_APP_ID`, record one bounded outcome event, and continue regardless of App Check result. | Provider sandbox, preview, or staging observation after provider setup exists. |
| `enforced` | Applicable routes require a valid App Check token for the configured `FIREBASE_APP_CHECK_APP_ID`; missing/invalid tokens fail with `403`, provider-unavailable verification fails with `503`, and one bounded enforcement event is recorded. | Only after accepted provider/runtime evidence and owner approval. |

Local, test, and CI default to `disabled` when no mode is supplied.
Production-like environments must set a mode explicitly.

Frontend mode uses `VITE_FIREBASE_APP_CHECK_MODE` with the same values. The
frontend uses existing `VITE_FIREBASE_APP_ID` as the browser Firebase app
identity source and must not add a second frontend App ID variable. Invalid or
missing frontend mode is treated as disabled because browser-public config must
fail closed without breaking local development.

### 6.2 Frontend Token Transport

Gate B must add a focused frontend App Check owner:

```text
frontend/src/lib/appCheck.js
```

Contract:

- use the existing Firebase `app` from `frontend/src/lib/firebase.js` and its
  existing `VITE_FIREBASE_APP_ID` configuration;
- initialize Firebase App Check lazily only when mode is not disabled and
  `VITE_FIREBASE_APP_CHECK_RECAPTCHA_ENTERPRISE_SITE_KEY` is non-blank;
- use Firebase Web SDK `ReCaptchaEnterpriseProvider`;
- call `getToken(appCheck, false)` for normal API requests;
- return `null` when disabled, unconfigured, initialization fails, or token
  acquisition fails;
- never write tokens to URLs, request bodies, localStorage, sessionStorage,
  cookies, analytics, console output, or error messages;
- expose test-only reset/override helpers only for deterministic frontend unit
  tests.

`frontend/src/lib/apiClient.js` must attach `X-Firebase-AppCheck` only to Pickup
Lane API requests. It must not attach the header to arbitrary absolute URLs or
direct signed provider uploads. It must not catch App Check failures and
globally retry mutations.

### 6.3 Backend Verification Boundary

Gate B must add a focused backend verification service:

```text
backend/services/app_check_service.py
```

Contract:

- do not import or call Firebase Admin SDK `app_check.verify_token` directly;
- call a narrow centralized Firebase provider wrapper in
  `backend/firebase_admin_client.py`, such as
  `verify_firebase_app_check_token`;
- define the dedicated header name `X-Firebase-AppCheck`;
- read the App Check token only from `X-Firebase-AppCheck`;
- require configured `FIREBASE_APP_CHECK_APP_ID` before observe/enforced
  verification;
- after centralized Firebase Admin App Check verification succeeds, read only
  the provider-verified App ID claim or narrow verified result needed for the
  equality decision;
- compare the verified App ID exactly with configured
  `FIREBASE_APP_CHECK_APP_ID`;
- discard decoded claims after the narrow App ID decision;
- return bounded outcomes: `valid`, `missing`, `invalid`, and
  `provider_unavailable`;
- treat malformed, expired, wrong-project, wrong-app, wrong configured web-app,
  revoked, or otherwise rejected provider tokens as invalid unless the provider
  boundary is unavailable;
- treat Firebase Admin configuration or provider-unavailable errors as
  provider unavailable;
- do not expose raw token text, claims, verified App ID, configured App ID,
  project id, provider exception text, stack traces, or attestation details.

Source must not manually decode App Check JWTs, use Firebase ID-token decoded
claims as App Check evidence, trust a client-supplied App ID, or accept a
client-supplied "valid app" flag. Reading the provider-verified App ID from the
Firebase Admin verification result solely for this equality check is not manual
JWT decoding and is not application-owned App Check authority; Firebase Admin
remains the token-verification authority through the centralized provider
client.

### 6.3.1 Centralized Firebase Provider Wrapper

Gate B must extend:

```text
backend/firebase_admin_client.py
```

with one narrow App Check provider wrapper, using a current-source name such as
`verify_firebase_app_check_token`.

The wrapper owns:

- obtaining the existing initialized Firebase Admin app through
  `initialize_firebase_admin()`;
- calling Firebase Admin `app_check.verify_token(token, app=firebase_app)`;
- preserving the configured Firebase Admin HTTP timeout ownership;
- translating timeout-like provider/JWKS verification failures into
  `DependencyReadTimeoutError` with `provider_kind="firebase"` and
  `operation="firebase.app_check.verify"`;
- preserving cancellation instead of swallowing or reclassifying it;
- returning only the provider-verified claim result or a narrowly extracted
  verified App ID needed by the App Check service.

The wrapper must not log token text, claims, configured App IDs, verified App
IDs, project IDs, provider payloads, or provider exception text. It must not
manually decode JWTs, create a second Firebase app/client, compare the Pickup
Lane expected App ID unless current layering clearly requires that placement,
or change existing Firebase ID-token/user/delete behavior.

App Check verification is a Firebase provider read for C1/C2 purposes:

- operation identity: `firebase.app_check.verify`;
- provider: `firebase`;
- safety class: `SAFE_READ`;
- read operation: `true`;
- provider mutation: `false`;
- dependency retry owner: dependency-owned;
- application automatic retry: `false`;
- provider idempotency key: `false`;
- unknown mutation outcome: `false`.

WS03-03B request handling maps timeout-like provider read failure to
`provider_unavailable` while the centralized provider boundary still raises
the C1 `DependencyReadTimeoutError` classification. Invalid token rejection
must remain distinct from timeout/provider-unavailable behavior. Ordinary
provider/config/signing-key unavailability must not be mislabeled as an invalid
token, and arbitrary programming/application exceptions must not be treated as
provider proof that a token was invalid.

### 6.4 Middleware And HTTP Contract

Gate B must add:

```text
backend/services/app_check_middleware.py
```

The middleware must be wired through the canonical `create_app` path and receive
the prebuilt route policy and event-recorder boundary during app construction.
It should be added as the innermost application security gate so the existing
outer middleware still applies:

- correlation ID;
- response security/cache headers;
- trusted host;
- CORS;
- request body limits where applicable.

Denial responses must use the existing `public_error_response` helper and must
include the same public error envelope, cache/security headers, CORS behavior,
and response correlation behavior as other app-owned denials.

Middleware runs before FastAPI route execution. At request time it must not
depend on `scope["route"]`, endpoint objects, or route tags already being
populated. It must use only the request method, request path, request headers,
and the precomputed route matcher.

Planned safe public errors:

| Outcome | Status | Code | Message |
|---|---|---|---|
| missing App Check token in enforced mode | `403` | `APP_CHECK.REQUIRED` | `App verification required.` |
| invalid App Check token in enforced mode | `403` | `APP_CHECK.INVALID` | `App verification failed.` |
| provider unavailable in enforced mode | `503` | `APP_CHECK.UNAVAILABLE` | `App verification is unavailable.` |

Observe mode records the same bounded outcome classes and continues to the
route. It must not change route success/failure behavior. Enforced mode records
the bounded outcome before allowing a valid request through or returning the
approved safe denial for missing, invalid, or provider-unavailable outcomes.
Recorder failure must not change the App Check decision for the current
request.

### 6.5 Route Policy

Gate B must add:

```text
backend/services/app_check_policy.py
```

Route policy construction has two stages.

Stage A happens during application construction after all current routes are
registered and OpenAPI/tombstone route metadata is finalized, but before the
middleware stack is finalized. The builder in
`backend/services/app_check_policy.py` must inspect `app.routes` and produce an
immutable runtime matcher. For executing FastAPI routes, the matcher must
retain only bounded structural information needed at request time:

- allowed method or methods;
- route template;
- compiled or structural path matcher;
- App Check disposition;
- bounded resource or route-family classification.

The matcher must not persist handlers, request data, user IDs, object IDs,
dynamic URLs, or provider identifiers.

Stage B happens in `AppCheckMiddleware`. At request time, the middleware uses
only request method, request path, request headers, and the precomputed matcher
to decide whether App Check applies. It must not depend on FastAPI routing
having already executed.

The route policy must classify FastAPI routes from current route objects and
metadata during construction. It must not rely on a stale hand-maintained route
list as the only proof, and it must not use route-name prefixes alone when that
could hide new route families.

Policy categories:

| Category | Disposition |
|---|---|
| Supported Pickup Lane browser API route families | included |
| `/`, `/live`, `/ready`, optional `/db-health` | excluded |
| `/docs`, `/redoc`, `/openapi.json`, docs subpaths | excluded |
| `/static` and `/static/*` | excluded |
| Stripe webhook and future provider callback routes | excluded |
| Direct signed provider upload URLs | not part of backend route policy; frontend transport must keep them outside `apiClient` |
| Non-API mount/infrastructure route | excluded only when explicitly classified as non-API infrastructure |
| Registered but unclassified current FastAPI API route | policy construction or trusted validation failure; do not silently treat as excluded |
| Request path that matches no registered route | continue to normal FastAPI `404` or `405` handling without inventing an App Check-protected business route |

Gate B evidence must compare the complete current route registration against
the classification, prove registered unclassified API routes fail the trusted
inventory, and prove genuinely unmatched requests preserve normal HTTP
semantics.

### 6.6 CORS And Header Policy

`X-Firebase-AppCheck` is a browser request header. Backend CORS must include it
in the exact finite application allowed-header list. This is not a wildcard
expansion. Existing WS02-03 CORS evidence must be updated to reflect the new
finite approved header.

CORS remains outside the App Check gate. Browser `OPTIONS` preflight must remain
handled by the existing CORS middleware and must not be denied merely because it
does not carry `X-Firebase-AppCheck`. Actual applicable API requests still go
through App Check evaluation, and denial responses must still receive current
CORS, security-header, and correlation behavior.

### 6.7 Observability

App Check observations must use existing EN-02 event and telemetry primitives.
Do not add a new telemetry label name unless a later owner explicitly approves
that observability scope. Gate B must implement observation recording inside
`backend/services/app_check_middleware.py`; it must not modify
`backend/observability/events.py` or `backend/observability/telemetry.py`.

`AppCheckMiddleware` must accept an injectable event-recorder or capture
boundary for deterministic tests. The production default emits the validated
event envelope through a bounded application/module logger from
`app_check_middleware.py`. Only the `EventEnvelope.to_json()` safe structured
representation may be emitted.

Recommended source-owned event shape:

- `event_name`: `app_check.request`;
- `provider_kind`: `firebase`;
- `operation`: `app_check.observe` or `app_check.enforce`;
- `resource_kind`: bounded route family;
- `result`: `valid`, `missing`, `invalid`, or `provider_unavailable`;
- `stable_error_code`: one of the App Check public codes where applicable;
- `labels.route_template`: FastAPI route template only.

The event must not include raw tokens, decoded claims, verified App ID,
configured App ID, provider exception text, project identifiers, user
identifiers, object keys, URLs, dynamic paths, or free-form route paths.

Recorder failure is best-effort and privacy-safe. It must not turn an invalid
enforced request into an allowed request, convert a valid request into an
authentication or authorization result, expose exception text, or create a
global retry.

## 7. Implementation Scope

After human Gate A approval, this canonical plan is frozen and is not a Gate B
editable file. Gate B implements the source, configuration, evidence,
requirement metadata, testing-record, and compatibility work in the 30
authorized Gate B files listed in Section 13.

### 7.1 Production Source Corrections

Gate B owns these source/configuration corrections:

- add App Check mode parsing, `BackendSettings.firebase_app_check_mode`, and
  `BackendSettings.firebase_app_check_app_id`;
- add backend App Check service, middleware, and route policy modules;
- extend the centralized Firebase Admin provider client with the narrow App
  Check verification wrapper;
- add the App Check provider read operation to the declarative retry-policy
  registry;
- wire middleware and the precomputed route-policy matcher through `create_app`;
- add `X-Firebase-AppCheck` to the exact backend CORS application header list;
- add backend and frontend env-example names for App Check mode, the backend
  supported-web-app App ID placeholder, and public reCAPTCHA Enterprise site
  key;
- add frontend App Check helper and shared API-client header transport.

### 7.2 Compatibility Corrections

Gate B must update current trusted tests whose finite source expectations are
intentionally affected:

- platform settings tests for the new backend env vars and frontend public
  `VITE_` names;
- synthetic production-like settings helpers for explicit
  `FIREBASE_APP_CHECK_MODE` and observe/enforced
  `FIREBASE_APP_CHECK_APP_ID`;
- WS02-03 CORS tests for the new exact application allowed header;
- WS02-04C1 Firebase timeout evidence for the new centralized
  `firebase.app_check.verify` provider read;
- WS02-04C2 provider-operation inventory evidence for the new safe-read retry
  registry entry;
- WS02-04C3B provider-cost inventory evidence for the new safe-read C2
  registry key, without approving a C3B numeric limiter.

These are compatibility updates, not new product requirements for the older
passes.

### 7.3 Non-Goals

WS03-03B Gate B must not:

- use the old `pr/WS03-03B1` branch as the working branch;
- cherry-pick, rebase, or merge the old WIP commit;
- begin production App Check enforcement;
- commit debug tokens, real site keys, service-account keys, provider IDs, or
  private screenshots;
- mutate Firebase/GCP, Render, Vercel, GitHub, DNS, Stripe, R2, or Neon
  provider settings;
- implement administrator MFA in local source without provider evidence;
- change recent-auth thresholds, protected route matrix, or caller-owned
  step-up behavior from WS03-03A;
- alter Firebase Admin credential loading, ADC, workload identity, or
  service-account roles without a new approved owner decision and evidence
  package;
- create a second production Firebase Admin provider/network boundary outside
  `backend/firebase_admin_client.py`;
- weaken `backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py`
  merely to allow a second Firebase Admin boundary;
- modify dependency manifests, `backend/observability/events.py`, or
  `backend/observability/telemetry.py` unless fresh contradictory evidence
  proves this design cannot be implemented inside the approved 30-file Gate B
  set;
- add Playwright or real provider-network tests by default;
- add database migrations, models, or PostgreSQL-owned behavior.

## 8. Testing And Evidence

### 8.1 Evidence Architecture

| Evidence Artifact | Requirements | Responsibility |
|---|---|---|
| `backend/tests/workflows/app_check_provider_security/test_app_check_settings_contract.py` | `R1`, `R6`, `R7` | App Check mode parsing, accepted modes, invalid mode rejection, production-like explicit mode, observe/enforced App ID requirement, disabled App ID omission, synthetic placeholder handling, local/test/CI disabled default, and no direct provider side effects during settings parsing. |
| `backend/tests/workflows/app_check_provider_security/test_app_check_backend_contract.py` | `R3`, `R4`, `R5`, `R6` | Middleware mode semantics, provider-valid expected-App-ID outcome, provider-valid wrong-App-ID outcome, provider-invalid/missing/provider-unavailable outcomes with injected verifier fakes, denial before endpoint side effects, safe public error envelope, CORS/security/correlation preservation, observe/enforce recorder invocation, and recorder failure safety. |
| `backend/tests/workflows/app_check_provider_security/test_app_check_route_policy_contract.py` | `R4`, `R5`, `R6`, `R7` | Current FastAPI route classification built from registered routes before middleware execution, precomputed structural matching, no dependency on post-routing `scope["route"]`, included browser API families, excluded infrastructure/provider callback paths, no unclassified current API routes, unmatched 404/405 behavior, CORS preflight behavior, and direct signed provider uploads outside backend policy. |
| `backend/tests/workflows/app_check_provider_security/test_app_check_frontend_transport_contract.py` | `R2`, `R5`, `R6`, `R7` | Static/source proof that `apiClient` attaches the dedicated header only to Pickup Lane API requests, direct provider upload helpers avoid `apiClient`, no body/query/header confusion, no global retry/replay. |
| `backend/tests/workflows/app_check_provider_security/test_app_check_negative_space_contract.py` | `R1`, `R2`, `R3`, `R6`, `R7` | Source inventory for bypass flags, query/body token acceptance, client-supplied App ID trust, skipped verified-App-ID comparison, manual JWT decoding, fake app-owned App Check authority, unsafe telemetry/logging/storage, unsafe App ID disclosure, local/test bypass leakage, recorder failure bypasses, new telemetry labels, and zero pytest mappings for deferred provider/governance requirements. |
| `frontend/tests/unit/appCheckApiClient.test.js` | `R2`, `R6` | Node unit proof for frontend helper behavior, token attachment, acquisition failure, no arbitrary absolute URL header, no direct provider-upload header, no token in URL/body/storage, and no generic retry. |
| Existing compatibility tests | `R1`, `R2`, `R4`, `R6` plus older pass IDs | Update finite settings/config/CORS expectations so accepted cross-pass tests remain truthful after App Check source is added. |
| `backend/tests/platform/operation_timeouts/test_firebase_timeout_contract.py` | accepted `WS02-04C1` markers | Extend current Firebase timeout evidence for centralized App Check verification: uses the existing Firebase app, timeout-like verification/JWKS failure maps to `DependencyReadTimeoutError` with operation `firebase.app_check.verify`, invalid token remains non-timeout, provider-unavailable/non-token failure remains distinct, and cancellation is preserved. |
| `backend/tests/platform/retry_reconciliation/test_c2_provider_operation_inventory_contract.py` | accepted `WS02-04C2` markers | Preserve current provider-boundary inventory and require `firebase.app_check.verify` in the retry registry as `SAFE_READ`, read operation, not provider mutation, and no automatic application retry. |
| `backend/tests/platform/provider_cost_rate_limits/test_provider_cost_inventory_contract.py` | accepted `WS02-04C3B` markers | Preserve the exact C3B provider-operation inventory while adding `("firebase.app_check.verify", "app_check_request_verification")` as a current Firebase safe-read surface with no C3B numeric limiter, no provider mutation, no approved retry attempts, and no approved backoff. |
| Requirement JSON and testing record | `R1` through `R10` | Checker traceability plus human adequacy reasoning, including explicit deferred provider/governance evidence. |

### 8.2 Testing Record Design

Gate B must create:

```text
backend/tests/workflows/app_check_provider_security/TESTING_RECORD.md
```

The record must follow `TESTING-RECORD-TEMPLATE.md` and cover:

- scope and non-goals;
- R1-R10 requirement states;
- App Check mode, supported-web-app App ID, route, actor, request-header,
  provider, recorder, failure, and rollout dimensions;
- direct provider upload and provider callback exclusions;
- centralized Firebase App Check verification through
  `backend/firebase_admin_client.py`;
- App Check verification as Firebase provider safe read operation
  `firebase.app_check.verify`;
- C1 timeout/provider-availability preservation and C2 retry/no-replay
  ownership for that operation;
- failure transformations for missing, empty, malformed, invalid,
  wrong-verified-App-ID, provider unavailable, unclassified route, unmatched
  route, recorder failure, unsafe source, and retry/replay;
- selected evidence and why pytest/frontend unit evidence is enough for source
  behavior but not for live provider facts;
- important side effects, including route body execution being prohibited on
  enforced-mode denial and observation sink failure being prohibited from
  changing authorization behavior;
- explicit gaps/deferrals for administrator MFA, Firebase/GCP credentials, and
  production App Check rollout.

### 8.3 Negative-Space Strategy

The negative-space evidence must fail closed for:

- `X-Firebase-AppCheck` accepted from query/body/form/path instead of header;
- an App ID trusted from request body/query/header rather than from the
  provider-verified token result;
- the verified App ID comparison skipped in observe or enforced mode;
- the configured or verified App ID logged, returned, or emitted in telemetry;
- the App ID used as user identity or authorization authority;
- a request body or schema field that lets the client claim App Check validity;
- manual JWT decoding or custom cryptography for App Check;
- direct Firebase Admin App Check SDK use outside
  `backend/firebase_admin_client.py`;
- use of Firebase ID-token claims as App Check proof;
- local/test/CI defaults leaking into production-like mode without explicit
  configuration;
- a client-exposed bypass flag such as `appCheck: false` that current product
  code can set for protected API calls;
- App Check token persistence in localStorage, sessionStorage, cookies, URLs,
  request bodies, analytics, logs, or error messages;
- low-level `apiClient` blind retries or mutation replay;
- App Check substituting for recent-auth, Firebase Auth, admin auth, rate
  limits, request limits, idempotency, payment safeguards, or authorization;
- unclassified current FastAPI routes;
- provider callback routes incorrectly requiring browser App Check;
- health/docs/static infrastructure incorrectly gated;
- unsafe telemetry labels or raw provider exception logging;
- observation recorder failure turning an enforced denial into an allowed
  request or creating a global retry;
- pytest mappings for `WS03-03B-R8`, `WS03-03B-R9`, or `WS03-03B-R10`;
- changed source that weakens accepted WS03-03A recent-auth behavior.

## 9. Repository Versus External Evidence

| Requirement / Fact | Classification | Evidence Owner |
|---|---|---|
| Source App Check settings, modes, supported-web-app App ID binding, env-example names, frontend public names | `PROVEN FROM REPOSITORY` after Gate B implementation/tests | WS03-03B |
| Frontend App Check helper and API header attachment | `PROVEN FROM REPOSITORY` after Gate B implementation/tests plus frontend unit tests | WS03-03B |
| Backend verifier service, centralized Firebase provider wrapper, verified App ID comparison, and middleware mode behavior with injected fakes | `PROVEN FROM REPOSITORY` after Gate B implementation/tests plus WS02-04C1/C2 compatibility evidence | WS03-03B with accepted C1/C2 compatibility evidence |
| Current FastAPI route policy inventory and precomputed matcher behavior | `PROVEN FROM REPOSITORY` after Gate B implementation/tests | WS03-03B |
| Observe/enforce event recording through safe `EventEnvelope.to_json()` logger sink | `PROVEN FROM REPOSITORY` after Gate B implementation/tests | WS03-03B |
| CORS support for the App Check header | `PROVEN FROM REPOSITORY` after Gate B implementation/tests | WS03-03B with WS02-03 compatibility evidence |
| Live Firebase App Check web app registration and proof that the configured App ID is registered for the intended provider web app | `EXTERNAL EVIDENCE STILL REQUIRED` | WS03-03B / WS10 provider evidence |
| reCAPTCHA Enterprise provider/domain configuration | `EXTERNAL EVIDENCE STILL REQUIRED` | WS03-03B / WS10 provider evidence |
| Real App Check token acquisition in deployed browser | `EXTERNAL EVIDENCE STILL REQUIRED` | WS03-03B / WS07 / WS10 provider-runtime evidence |
| Staging observation, false-positive review, rollback, and production enforcement approval | `EXTERNAL EVIDENCE STILL REQUIRED` | WS03-03B / WS10 provider-runtime evidence |
| Administrator MFA capability, enrollment, factor policy, break-glass, recovery, access review | `EXTERNAL EVIDENCE STILL REQUIRED` | WS03-03B / WS10 governance/provider evidence |
| Firebase/GCP service-account IAM, key inventory, storage, rotation, revocation, monitoring, ADC/WIF, permanent-host binding | `EXTERNAL EVIDENCE STILL REQUIRED` | EN-03 / WS03-03B / WS10 |
| Existing recent-auth, admin mutation partition, and caller-owned step-up | `PROVEN FROM REPOSITORY` by accepted WS03-03A evidence | WS03-03A |

## 10. Historical WIP Reconciliation

Historical WIP branch: `pr/WS03-03B1`.

Historical WIP commit: `2796a7bc7eb2efcc5d822dafbbf4a1d4c95c7bd8`.

Likely WIP original base: `d4d1d5fe49e2888ccbb09a68a0500c5d9e71786e`.

The WIP was one local commit, 62 commits behind current develop at inspection
time. It changed 14 files and was never current authority.

| WIP File / Concept | Current Decision |
|---|---|
| `backend/services/app_check_middleware.py` | `PARTIALLY VALID, REQUIRES CURRENT REDESIGN`. Mode semantics and injected verifier/recorder ideas survive; implementation must be rebuilt against current middleware/error/CORS behavior and must not depend on post-routing scope metadata. |
| `backend/services/app_check_policy.py` | `PARTIALLY VALID, REQUIRES CURRENT REDESIGN`. Route classification and unclassified inventory ideas survive, but current policy must be built from `app.routes` into a precomputed runtime matcher. |
| `backend/services/app_check_service.py` | `PARTIALLY VALID, REQUIRES CURRENT REDESIGN`. Bounded outcomes and verified App ID comparison survive, but direct Firebase Admin App Check SDK use must move behind the accepted centralized Firebase provider client in `backend/firebase_admin_client.py`. |
| `backend/settings.py` and `backend/.env.example` ideas | `STILL VALID DESIGN INPUT`. Mode setting survives, and current design adds `FIREBASE_APP_CHECK_APP_ID` with current compatibility tests updated deliberately. |
| `backend/main.py` middleware wiring | `PARTIALLY VALID, REQUIRES CURRENT REDESIGN`. App Check should be innermost so outer CORS/security/correlation still decorate denials. |
| `backend/observability/telemetry.py` adding `mode` label | `CONFLICTS WITH CURRENT AUTHORITY`. Current EN-02 allowed labels do not include `mode`; WS03-03B should use approved event fields instead of widening telemetry labels. |
| `frontend/src/lib/appCheck.js` | `STILL VALID DESIGN INPUT`. Lazy init, provider use, token return/null behavior, and test hooks survive conceptually. |
| `frontend/src/lib/apiClient.js` header attachment | `PARTIALLY VALID, REQUIRES CURRENT REDESIGN`. Header transport survives, but current 03A no-global-replay and current API client shape must be preserved. |
| `frontend/tests/unit/appCheckApiClient.test.js` | `PARTIALLY VALID, REQUIRES CURRENT REDESIGN`. Frontend unit coverage is still needed, but tests must target current source and current unit runner. |
| old backend tests under `backend/tests/shared/...` | `SUPERSEDED BY CURRENT SOURCE`. Current EN-01 trusted tests must live under current trusted roots; old `shared` paths are not the correct architecture. |
| old `WS03-03B1` plan | `HISTORICAL PROVENANCE ONLY`. It does not define current pass identity, requirements, or deferrals. |

## 11. WS03-03A Compatibility

WS03-03B must preserve all accepted WS03-03A behavior:

- the provider `auth_time` authority remains the only recent-auth freshness
  source;
- the five-minute recent-auth window remains unchanged;
- the 25-route protected-action matrix remains unchanged;
- the 107-route admin mutation partition remains unchanged;
- `require_recent_active_admin`, `require_recent_active_user`, and
  `require_recent_app_user` remain the recent-auth owners;
- frontend step-up remains caller-owned;
- the low-level API client must not catch `AUTH.RECENT_AUTH_REQUIRED` or replay
  arbitrary mutations;
- credential-linking remains Firebase-provider owned;
- no application storage value, local timestamp, purpose flag, or token issue
  time may become freshness authority.

App Check is an additional request-source signal. It must not change recent-auth
requirements or provide an alternate route around them.

## 12. Provider, Browser, Database, Migration, And Concurrency Decisions

| Layer | Gate B Decision |
|---|---|
| Backend pytest | Required for source-owned settings, middleware, verifier, route policy, HTTP contracts, and negative-space evidence. |
| Frontend unit | Required through `npm run test:unit` for frontend App Check helper/API-client behavior. |
| Playwright/browser | Not required for Gate B source closure. Real browser/provider runtime proof remains external/later. |
| Firebase provider sandbox/network | Not required for ordinary Gate B pytest. Real provider verification remains external/provider evidence and must not be faked as closure. |
| PostgreSQL | Not required for the focused App Check source tests because this pass is middleware/config/source behavior with no persistence. Relevant full backend regression may still use the standard test database. |
| Migrations | Not applicable. No schema or data migration is owned. |
| Concurrency | Not applicable. App Check source behavior has no database race, idempotency, or concurrent state transition. |
| Controlled time | Not required beyond existing event-envelope timestamp safety; no time-window behavior is owned by App Check source. |
| Provider-contract tests | Not part of Gate B unless a later approved instruction supplies sandbox/provider credentials and evidence rules. |
| Provider timeout/retry/classification compatibility | Required only as source compatibility evidence: App Check verification must remain inside the centralized Firebase Admin provider boundary, classify as C1 dependency-read timeout operation `firebase.app_check.verify`, appear in the C2 declarative retry registry as a safe read without adding runtime retry execution, and appear in C3B's current provider-cost/action inventory without approving a numeric provider-cost/action limiter. |
| Dependency files | Not required. Current `backend/requirements.txt` already includes `firebase-admin`, and current `frontend/package.json` already includes `firebase`. |

## 13. Exact Gate B Editable File Set And Final Pass Status

After human Gate A approval, this canonical plan is frozen and Gate B must not
edit it. Gate B may edit exactly these 30 files:

1. `backend/.env.example`
2. `backend/main.py`
3. `backend/settings.py`
4. `backend/services/app_check_middleware.py`
5. `backend/services/app_check_policy.py`
6. `backend/services/app_check_service.py`
7. `frontend/.env.example`
8. `frontend/src/lib/apiClient.js`
9. `frontend/src/lib/appCheck.js`
10. `frontend/tests/unit/appCheckApiClient.test.js`
11. `backend/tests/support/requirements/ws03_03b.json`
12. `backend/tests/workflows/app_check_provider_security/TESTING_RECORD.md`
13. `backend/tests/workflows/app_check_provider_security/test_app_check_settings_contract.py`
14. `backend/tests/workflows/app_check_provider_security/test_app_check_backend_contract.py`
15. `backend/tests/workflows/app_check_provider_security/test_app_check_route_policy_contract.py`
16. `backend/tests/workflows/app_check_provider_security/test_app_check_frontend_transport_contract.py`
17. `backend/tests/workflows/app_check_provider_security/test_app_check_negative_space_contract.py`
18. `backend/tests/platform/settings/test_backend_settings_contract.py`
19. `backend/tests/platform/settings/test_backend_config_boundaries.py`
20. `backend/tests/platform/http_security/test_cors_contract.py`
21. `backend/tests/platform/http_security/test_host_contract.py`
22. `backend/tests/platform/http_security/test_response_security_headers_contract.py`
23. `backend/tests/platform/http_contracts/test_cache_docs_tombstone_contract.py`
24. `backend/tests/platform/secrets/test_inbox_token_secret_contract.py`
25. `backend/tests/workflows/identity_authority/test_firebase_project_settings_contract.py`
26. `backend/firebase_admin_client.py`
27. `backend/services/provider_retry_policy.py`
28. `backend/tests/platform/operation_timeouts/test_firebase_timeout_contract.py`
29. `backend/tests/platform/retry_reconciliation/test_c2_provider_operation_inventory_contract.py`
30. `backend/tests/platform/provider_cost_rate_limits/test_provider_cost_inventory_contract.py`

The expected final pass changed-file set is exactly 31 files relative to the
accepted baseline:

1. the frozen canonical plan:
   `docs/production-readiness/planning/passes/ws03/ws03-03b-app-check-admin-mfa-firebase-governance.md`;
2. the exact 30 Gate B editable files listed above.

No other file is authorized by this Gate A plan.

Do not add
`backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py`
merely to allow a second Firebase Admin production boundary. Its current
assertions should pass unchanged because App Check verification remains inside
`backend/firebase_admin_client.py`.

Do not add
`backend/tests/platform/retry_reconciliation/test_retry_policy_registry_contract.py`
unless fresh implementation evidence proves a stale finite assertion requires
a compatibility correction. Current plan expectation is that the new
declarative retry-policy entry satisfies that registry test unchanged.

Gate B may update
`backend/tests/platform/provider_cost_rate_limits/test_provider_cost_inventory_contract.py`
only to keep C3B's exact provider-operation inventory truthful for the new
`("firebase.app_check.verify", "app_check_request_verification")` safe-read
entry. The `_policy_keys() == _EXPECTED_POLICY_KEYS` equality must remain
exact, and the test must add focused assertions that the App Check entry is
`provider == "firebase"`, `workflow_context == "app_check_request_verification"`,
`SAFE_READ`, `read_operation`, not `provider_mutation`, no application
automatic retry, no approved retry attempts, and no approved backoff seconds.
The existing exact provider-mutation context set, local manual-operation
context set, retired-route classifications, R2 presign distinction, chat-only
source-owned limiter boundary, and external/provider/runtime deferrals must
remain unchanged.

Do not add or edit
`docs/production-readiness/planning/passes/ws02/ws02-04c3b-provider-cost-rate-limit-deferral.md`,
`backend/tests/platform/provider_cost_rate_limits/TESTING_RECORD.md`,
`backend/tests/platform/provider_cost_rate_limits/test_c3b_boundary_and_handoff_contract.py`,
`backend/tests/platform/provider_cost_rate_limits/test_provider_cost_rate_limit_deferral_contract.py`,
or
`backend/tests/platform/provider_cost_rate_limits/test_non_chat_rate_limit_negative_space_contract.py`
for this compatibility correction. Current C3B authority already assigns App
Check/auth-provider ownership to WS03 and keeps provider/runtime cost, quota,
and abuse evidence external/later.

## 14. Validation Plan

Gate B validation must include:

1. The three originally failing cross-pass provider-boundary nodes:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py::test_current_provider_network_inventory_has_no_unclassified_production_bypass backend/tests/platform/operation_timeouts/test_provider_operation_inventory_contract.py::test_current_provider_boundaries_are_explicitly_accounted_for backend/tests/platform/retry_reconciliation/test_c2_provider_operation_inventory_contract.py::test_current_runtime_provider_network_boundaries_are_classified`
   These must pass because production Firebase Admin access remains centralized
   in `backend/firebase_admin_client.py`, not because provider inventories were
   weakened.
2. Complete WS02-04C1 operation-timeout scope:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/operation_timeouts`
   This must include the extended Firebase App Check timeout evidence for
   `firebase.app_check.verify`.
3. Complete WS02-04C2 retry/reconciliation scope:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/retry_reconciliation`
   This must include the `firebase.app_check.verify` safe-read registry
   classification and no automatic application retry.
4. The C3B node that exposed the finite inventory drift:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/provider_cost_rate_limits/test_provider_cost_inventory_contract.py::test_c2_provider_operation_registry_matches_current_c3b_inventory`
   This must pass because C3B inventories the new App Check safe-read C2
   registry entry without approving a provider-cost/action limiter.
5. Complete WS02-04C3B provider-cost scope:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/provider_cost_rate_limits`
   This must preserve C3B R1/R3 inventory truth, exact mutation context sets,
   chat-only source-owned limiter boundaries, and external/provider/runtime
   deferrals.
6. Focused backend App Check scope:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/workflows/app_check_provider_security`
   This scope must cover expected App ID binding, wrong verified App ID
   rejection, provider-invalid/missing/provider-unavailable outcomes,
   route-policy precomputation, no dependence on post-routing route metadata,
   registered-unclassified failure, unmatched 404/405 preservation, CORS
   preflight preservation, observation recorder invocation, safe event-envelope
   shape, no new telemetry labels, and recorder failure safety.
7. Affected settings/CORS compatibility tests:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/platform/settings backend/tests/platform/http_security/test_cors_contract.py backend/tests/platform/http_security/test_host_contract.py backend/tests/platform/http_security/test_response_security_headers_contract.py backend/tests/platform/http_contracts/test_cache_docs_tombstone_contract.py backend/tests/platform/secrets/test_inbox_token_secret_contract.py backend/tests/workflows/identity_authority/test_firebase_project_settings_contract.py`
8. Accepted WS03 prerequisite regressions:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/workflows/identity_authority backend/tests/workflows/account_lifecycle_concurrency backend/tests/workflows/recent_auth_step_up`
9. Frontend unit tests:
   `npm --prefix frontend run test:unit`
10. Frontend lint/build if Gate B modifies frontend source:
   `npm --prefix frontend run lint`
   and
   `npm --prefix frontend run build`
11. Backend checker domain scope:
   `DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/app_check_provider_security`
12. Backend checker suite scope:
   `DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite`
13. Generated traceability counts for `WS03-03B-R1` through `WS03-03B-R10`,
   with `R8`, `R9`, and `R10` exactly zero.
14. Full trusted backend regression:
   `APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests`
15. `git diff --check`

Because Correction 4 requires only the C3B inventory-test compatibility
update, already-current green C1, frontend, compatibility, and WS03
prerequisite evidence may remain current unless the actual Gate B correction
changes source that can affect those layers. Full backend regression must still
be green before Gate B completion.

Gate B evidence-specific review must confirm:

- C1 provider inventory passes unchanged;
- no direct Firebase Admin import exists in `app_check_service.py`;
- centralized Firebase provider boundary owns App Check verification;
- App Check timeout uses `firebase.app_check.verify`;
- invalid App Check token is not timeout;
- provider/JWKS unavailable is not mislabeled invalid;
- App Check operation appears in the C2 retry registry;
- C2 classifies it `SAFE_READ`;
- no application automatic retry exists;
- C3B exact provider-operation inventory includes the App Check safe-read key
  without adding a numeric provider-cost/action limiter;
- no request or mutation replay is added;
- WS03 App ID comparison remains in the WS03-03B service/policy layer.

If any in-scope evidence mistake appears, fix only inside the 30-file Gate B
editable set. If correct resolution requires production provider access,
another file, another requirement, a different proof layer, a frozen-plan
change, production enforcement, or a new owner decision, stop and return to
Gate A.

Gate B final status validation must separately confirm:

- the frozen canonical-plan SHA-256 is unchanged from human Gate A approval;
- only the 30 Gate B-authorized files were modified during Gate B;
- the exact final pass status contains 31 files: the frozen plan plus the 30
  Gate B files.

## 15. Deferred / Later Evidence

| Deferred Area | Why It Remains Open | Later Owner / Evidence |
|---|---|---|
| Live Firebase App Check app registration and configured-App-ID provider match | Repository source can require and compare `FIREBASE_APP_CHECK_APP_ID`, but cannot prove Firebase console state or production app registration. | Sanitized provider evidence under WS03-03B/WS10. |
| reCAPTCHA Enterprise provider/domain configuration | Requires provider/dashboard evidence. | Sanitized provider evidence under WS03-03B/WS10. |
| Debug/staging handling | Must be decided without committing debug tokens or provider-private values. | Provider/runtime evidence and owner approval. |
| Staging observation and false-positive review | Requires deployed traffic or controlled staging exercise. | WS03-03B/WS10 runtime evidence. |
| Production enforcement approval | Requires provider/runtime behavior, rollback plan, and owner sign-off. | Identity/security owner and platform/deployment owner. |
| Administrator MFA | Requires Firebase/Identity Platform capability, enrollment, factor, recovery, break-glass, existing-admin migration, and access-review evidence. | WS03-03B/WS10 provider-governance evidence. |
| Firebase/GCP credential governance | Requires IAM, service-account, key inventory, managed storage/injection, rotation, revocation, monitoring, emergency response, ADC/WIF, and permanent-host evidence. | EN-03/WS03-03B/WS10 provider-governance evidence. |

## 16. Completion Criteria

WS03-03B Gate B is complete when:

- the frozen canonical plan remains byte-for-byte unchanged during Gate B;
- Gate B modifies only the authorized 30 files from Section 13;
- the final repository pass state contains exactly 31 changed/untracked files
  relative to the accepted baseline: the frozen plan plus the 30 Gate B files;
- no additional file is modified;
- App Check source behavior is implemented without using old WIP branch state;
- App Check Firebase Admin SDK verification is centralized through
  `backend/firebase_admin_client.py` and `app_check_service.py` has no direct
  Firebase Admin SDK provider boundary;
- App Check provider verification timeout uses C1 dependency-read operation
  `firebase.app_check.verify`;
- C2 retry policy includes `firebase.app_check.verify` as `SAFE_READ`, read
  operation, not provider mutation, and no application automatic retry;
- C3B provider-cost inventory includes the `firebase.app_check.verify` safe
  read without adding a provider-cost/action limiter, retry count, or backoff;
- C1 provider inventory passes unchanged because no second Firebase Admin
  production boundary exists;
- App Check verification distinguishes Firebase project validity from supported
  Pickup Lane web-app validity through verified App ID comparison;
- route policy is precomputed from current registered routes before middleware
  execution and fails closed for registered unclassified API routes;
- observe/enforced App Check outcomes are recorded through a source-owned,
  safe, best-effort middleware event sink;
- App Check remains defense in depth and WS03-03A behavior is unchanged;
- `WS03-03B-R1` through `WS03-03B-R7` have meaningful trusted evidence;
- `WS03-03B-R8` through `WS03-03B-R10` remain deferred/governance with zero
  pytest mappings;
- frontend unit evidence proves browser-source token handling;
- checker domain and suite scopes pass;
- generated traceability is current;
- focused, prerequisite, frontend, and full backend validation pass;
- no secrets, raw provider evidence, debug tokens, real project identifiers,
  private account details, or unsupported provider/runtime closure claims enter
  the repository.

## 17. Recommendation

Proceed to Gate B only after human approval of this plan. Gate B should
implement the source-owned App Check foundation on the fresh
`pr/WS03-03B-remediation` branch and preserve administrator MFA,
Firebase/GCP credential governance, and production App Check rollout as explicit
external/provider evidence gaps.
