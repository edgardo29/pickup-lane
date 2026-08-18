# WS02-03 - Proxy, Host, TLS, CORS, and Response-Class Security Headers

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-03` |
| Track | `WS02` |
| Type | Configuration and provider verification |
| Primary controls | `API-M04`, `API-M05`, `API-M06`, `API-M07`, `API-M08` |
| Authority basis | WS02-03 blueprint contract, FDN-02 app/edge response-header ownership, API-M04 through API-M08, and accepted WS02-01 / WS02-02 environment and app-construction contracts. |
| Depends on | `WS02-01`, `WS02-02`, `FDN-02`, and actual edge/origin topology. Repository intent and app behavior are known; deployed topology remains external evidence. |
| Trusted test scope | `backend/tests/platform/http_security/` |

## 1. Purpose

WS02-03 establishes the proxy, Host, TLS, CORS, and response-class
security-header foundation for the backend HTTP chain.

The pass has two jobs:

- make the repository-owned FastAPI behavior explicit and mechanically
  provable; and
- preserve the external edge/provider evidence still required before the
  related controls can close.

The pass type is configuration and provider verification. Repository source can
prove typed Host and CORS settings, FastAPI Host enforcement, app-owned
response headers, documentation/OpenAPI behavior, source non-trust of forwarded
headers, and local bypass resistance. Repository source cannot prove DNS, TLS,
HSTS, public/custom domains, canonical-host redirects, direct-origin exposure,
trusted proxy topology, provider-added headers, or browser-observed staging
captures.

The actual edge/origin topology prerequisite is partially satisfied only:
repository intent and app behavior are known, but deployed public/edge topology
is not verified. Repository-owned implementation work may proceed for source and
trusted local evidence, but full provider-verification acceptance cannot occur until
the WS02-03 external evidence profile in this plan is satisfied.

## 2. Why This Matters

HTTP security controls fail when ownership is blurry. A backend can validate
Host headers correctly while the public edge still exposes a direct origin. CORS
can be exact in source while the wrong frontend origin is deployed. API JSON can
receive safe app headers while browser HTML, static assets, TLS redirects, and
HSTS remain edge-owned. A proxy chain can be safe only when the trusted immediate
proxy and direct-origin behavior are actually known.

WS02-03 keeps those surfaces separated. It requires source-owned safeguards
where the repository is authoritative, fresh trusted evidence under the EN-01
testing architecture, and explicit provider/staging evidence for the parts the
repository cannot honestly prove.

## 3. Requirements

Stable requirement IDs define the WS02-03 requirement surface for requirement
declarations, testing records, checker traceability, implementation review, and
future closure. They describe required invariants, not exact pytest node IDs.

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-03-R1` | Maintain the response-class ownership matrix. | The plan must separate FastAPI-owned API controls from frontend, edge, provider, static, redirect, and other non-API response ownership. | Blurry ownership causes false closure, duplicated controls, or gaps where no system actually owns the security behavior. |
| `WS02-03-R2` | Keep `ALLOWED_HOSTS` as a typed safe Host allowlist. | Production-like configuration must reject missing, wildcard, local-only, malformed, URL-like, port-bearing, or placeholder hosts. | Unsafe Host configuration can expose the API through unintended hostnames or let attacker-controlled Host values influence request handling. |
| `WS02-03-R3` | Enforce Host through the canonical FastAPI app path. | Host enforcement must cover normal API routes, health/diagnostics, docs, OpenAPI, errors, webhooks, mounted static assets, and middleware-owned failures without disclosing the configured allowlist. | A bypass on any request surface can expose backend behavior through untrusted hostnames or leak deployment details. |
| `WS02-03-R4` | Use exact reviewed CORS policy. | Browser CORS must use exact origins, credentials, exact methods, exact application-configured request headers, Starlette's non-wildcard safelisted-header behavior, safe preflight/simple-request behavior, and no route-level or duplicate middleware bypass. | Overbroad CORS can let unintended browser origins call authenticated API surfaces or mask unsafe origin assumptions. |
| `WS02-03-R5` | Apply app-owned API response security and cache headers by response class. | FastAPI-owned API JSON, API errors, health/diagnostics, webhook responses, OpenAPI JSON, and no-content responses must receive the intended content-sniffing, referrer, and cache protections while preserving deliberate route cache policy. | Missing or overbroad headers can leak sensitive API data, break route-owned cache decisions, or assign browser/edge behavior to the wrong owner. |
| `WS02-03-R6` | Apply documentation-specific browser controls only to docs HTML. | Interactive docs HTML receives anti-framing and capability restrictions when enabled; OpenAPI JSON remains JSON-owned and is not treated as HTML. | Docs and schema responses have different browser risk profiles; mixing them can either under-protect docs or break schema consumers. |
| `WS02-03-R7` | Do not invent edge, TLS, proxy, or forwarded-header trust. | Repository source must not trust forwarded Host, scheme, or client-address metadata, add trusted-proxy behavior, implement canonical-host redirects, or claim TLS/HSTS ownership without provider topology evidence. | Local source cannot honestly prove public edge behavior; pretending it can would leave spoofing and deployment risks unverified. |
| `WS02-03-R8` | Preserve deferred provider/edge evidence. | Actual public topology, TLS, HSTS, canonical-host behavior, direct-origin restriction, trusted proxy chain, deployed CORS, header captures, redirect traces, and duplicate-header precedence remain external evidence until sanitized proof exists. | Provider facts must not be fabricated by local tests; these gaps need explicit tracking until real deployment evidence is reviewed. |
| `WS02-03-R9` | Preserve single ownership and bypass resistance. | Host, CORS, API response headers, cache policy, static/redirect exclusions, exception paths, and canonical app construction must not create alternate owners or bypass paths. | Security middleware is only reliable when all app paths preserve the same owner boundaries and no hidden route or middleware bypass exists. |

## 4. Technical Design / Contracts

### 4.1 App And Edge Ownership

FDN-02 is the controlling decision for security-header ownership. The final
ownership model is:

| Surface | Owner | Repository proof | External evidence still required |
|---|---|---|---|
| API JSON responses | FastAPI app, with edge verification where applicable | Source and trusted platform tests | Deployed response captures and provider precedence |
| API errors | FastAPI app and response-header middleware; invalid Host remains middleware-owned | Source and trusted platform tests | Deployed response captures |
| Health and diagnostics | FastAPI app | Source and trusted platform tests | Hosting health-check path and deployed observations |
| Interactive API docs HTML | FastAPI app plus hosting access policy | Source and trusted platform tests for app behavior | Deployed exposure/access evidence |
| OpenAPI JSON | FastAPI app | Source and trusted platform tests | Deployed exposure/header captures |
| Frontend HTML and frontend static assets | Frontend hosting edge/frontend configuration | Repository can only prove backend non-ownership here | Vercel/frontend deployment headers and browser captures |
| Backend mounted static files | Present mounted static asset responses, explicitly excluded from generic API header policy | Source and trusted platform tests | Any deployed static/file behavior if exposed |
| Redirects | Explicit app-owned edge redirects are absent; framework routing redirects are route/framework-owned, not generic API header middleware-owned | Source static proof for explicit redirect absence plus TestClient proof for framework routing redirect ownership | Provider redirect traces and loop checks |
| File/download/image responses | Route/storage/frontend/provider owner, not generic WS02-03 API policy | Source static proof of current absence | Provider/storage/frontend evidence where applicable |
| Host validation | Typed settings plus FastAPI `TrustedHostMiddleware` | Source and trusted platform tests | Public host inventory, direct-origin behavior, provider-generated domains |
| Canonical-host redirect | Edge/provider unless a later approved source decision says otherwise | Repository proves no invented app redirect | Provider redirect traces |
| CORS | FastAPI app for API CORS policy; provider evidence for deployed behavior | Source and trusted platform tests | Browser-observed deployed CORS captures |
| TLS termination, HTTP-to-HTTPS redirect, HSTS | Public edge/hosting provider | Repository proves no app ownership claim | TLS/certificate/HSTS/redirect evidence |
| Forwarded-header trust and direct-origin restriction | Provider/topology owner; app source must not trust unverified forwarded values | Source static proof of non-trust | Trusted proxy chain, direct-origin restriction, proxy-spoof staging proof |
| Provider-added headers and duplicate-header precedence | Platform/deployment owner | Repository can list app-owned headers only | Deployed header inventory and conflict resolution |

`WS02-03-R1` is proven by this canonical planning artifact and the FDN-02
matrix above. It must not receive a pytest mapping. Executable source
conformance and bypass resistance are proven separately by `WS02-03-R5`,
`WS02-03-R6`, `WS02-03-R7`, and `WS02-03-R9`.

### 4.2 Host Contract

`ALLOWED_HOSTS` is the only source-owned backend Host allowlist setting.

Required configured-host behavior:

- local and test environments may use bounded local/test defaults;
- preview, staging, and production require explicit configured hosts;
- production-like environments reject local-only hosts;
- global wildcard hosts are rejected;
- documented placeholders are rejected;
- configured hosts are lowercased and harmless trailing dots are removed;
- blank entries, control characters, malformed DNS labels, schemes, paths,
  queries, fragments, credentials, backslashes, and ports are rejected;
- Host allowlist values are not derived from CORS origins, frontend base URLs,
  provider-generated domains, README provider names, or forwarded headers.

Required runtime behavior:

- the canonical FastAPI app installs one `TrustedHostMiddleware`;
- `www_redirect` stays disabled unless a later canonical-host decision approves
  redirect behavior;
- Host enforcement applies to normal API routes, health, diagnostics, docs,
  OpenAPI, application errors, webhook paths, mounted static assets, and
  middleware-owned failures;
- invalid Host responses must not disclose the configured allowlist;
- Host validation is not replaced by route-level checks or CORS-derived trust.

### 4.3 CORS Contract

CORS is browser policy, not authentication or authorization.

Required configured-origin behavior:

- `CORS_ALLOWED_ORIGINS` is required in production-like environments;
- wildcard credentialed origins are rejected;
- origins must be HTTP or HTTPS origins only;
- paths, queries, fragments, blanks, and localhost production-like origins are
  rejected;
- origin values are not used as Host allowlist values.

Required runtime behavior:

- allowed origins are reflected exactly when Starlette considers the request
  origin allowed;
- disallowed, null, missing, prefix, suffix, lookalike, scheme-confused,
  port-confused, path-confused, and query-confused origins are not implicitly
  allowed;
- credentialed behavior remains deliberate and tied to exact origins;
- simple requests and preflights are both covered;
- allowed-origin error responses preserve CORS behavior;
- disallowed-origin errors do not gain allow-origin headers;
- responses that vary by origin include the framework-owned `Vary: Origin`
  behavior where applicable;
- no manual OPTIONS route, route-level CORS header, duplicate CORS middleware,
  or alternate app path may bypass the policy.

API-M07 requires exact reviewed methods, exact application-configured request
headers, and non-wildcard framework runtime behavior. Current accepted source
still uses wildcard CORS methods and headers. The pass-owned implementation
must replace the wildcards with the exact method allowlist and exact
application-configured request-header allowlist below.

The reviewed backend API CORS method allowlist is exactly:

```text
GET, POST, PUT, PATCH, DELETE
```

Derivation:

- current FastAPI APIRoute inventory exposes target operations for `GET`,
  `POST`, `PUT`, `PATCH`, and `DELETE`;
- current frontend browser API callsites use `GET` through default `apiRequest`
  behavior and explicit `POST`, `PUT`, `PATCH`, and `DELETE` operations;
- `HEAD` is excluded because no current browser/API contract requires
  cross-origin HEAD requests;
- `OPTIONS` is excluded because current use is CORS preflight handled by
  `CORSMiddleware`, not an application target operation represented by
  `Access-Control-Request-Method`.

Future additions to the backend browser CORS method policy must return for
planning review or follow a later approved policy-change process. This pass
must not add methods beyond the frozen allowlist.

The reviewed backend API CORS application-configured request-header allowlist is
exactly:

```text
Accept, Authorization, Content-Type, X-Request-ID
```

Derivation:

- `Accept` is sent by the central frontend `apiRequest` wrapper;
- `Authorization` is sent by authenticated Firebase bearer-token browser API
  calls;
- `Content-Type` is sent by current JSON browser request bodies;
- `X-Request-ID` is the accepted EN-02 request-correlation header; the current
  frontend does not normally send it, but the backend API contract permits a
  caller-supplied validated correlation ID;
- direct upload headers used with provider upload URLs are not backend API CORS
  headers;
- `Stripe-Signature` is a provider webhook header, not a browser API request
  header;
- idempotency keys are current JSON body fields, not request headers.

Starlette 1.0.0 combines a non-wildcard configured `allow_headers` value with
its framework CORS-safelisted request headers:

```text
Accept, Accept-Language, Content-Language, Content-Type
```

Therefore the effective non-wildcard Starlette runtime request-header set is:

```text
Accept, Accept-Language, Authorization, Content-Language, Content-Type, X-Request-ID
```

`Accept-Language` and `Content-Language` are framework-safelisted behavior, not
Pickup Lane application-specific CORS permissions. Their presence does not
authorize arbitrary request headers, and header-name comparison is
case-insensitive at runtime where Starlette specifies that behavior.

Future additions to the backend browser CORS application-specific
request-header policy must return for planning review or follow a later
approved policy-change process. This pass must not add application-configured
headers beyond the frozen allowlist.

The pass-owned `backend/main.py` correction is:

- introduce or use the exact reviewed CORS method constant/list:
  `GET`, `POST`, `PUT`, `PATCH`, `DELETE`;
- introduce or use the exact reviewed application-configured CORS
  request-header constant/list:
  `Accept`, `Authorization`, `Content-Type`, `X-Request-ID`;
- replace `allow_methods=["*"]` with that exact method allowlist;
- replace `allow_headers=["*"]` with that exact application-configured
  request-header allowlist;
- make no other middleware, Host, response-header, cache, proxy, TLS,
  redirect, or application behavior change.

If implementation reveals a source defect outside this frozen scope, the pass
must return for planning review rather than silently broaden scope.

### 4.4 Response-Class Header Contract

The FastAPI response-header policy is centralized in `backend/main.py`.

App-owned API response classes must receive:

- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: no-referrer`;
- `Cache-Control: no-store` for public API JSON, public errors, health,
  diagnostics, OpenAPI, docs, and public/middleware-owned API responses unless
  a route has deliberately supplied a stricter or more specific policy;
- `Cache-Control: private, no-store` for source-known private/authenticated or
  admin API JSON responses where private-route metadata identifies the route.

The response-header middleware must preserve:

- status codes;
- content types;
- CORS headers;
- explicit route cache policy;
- framework-owned `Allow` and authentication headers;
- route-specific behavior for redirects, mounted static files, and future
  non-API response classes that are intentionally outside this policy.

Frozen current response-class inventory:

| Current response class / surface | Current source state | Trusted evidence owner |
|---|---|---|
| Ordinary public API JSON | Present through FastAPI routes/default JSON serialization. | Executable TestClient or direct middleware/helper evidence under `test_response_security_headers_contract.py`. |
| Private/authenticated/admin API JSON | Present through authenticated/admin routes and private-route metadata. | Executable or direct middleware/helper evidence under `test_response_security_headers_contract.py`; static route metadata evidence where direct route execution would require unrelated DB/provider setup. |
| Auth/authz failure, validation error, application error, and 404 | Present through WS02-04A stable error handlers and framework errors. | Executable TestClient evidence under `test_response_security_headers_contract.py`. |
| Webhook response | Present as `POST /stripe/webhook`; provider signature behavior is not WS02-03-owned. | Executable or direct middleware/helper evidence for response headers only; no Stripe/provider call. |
| Health/diagnostic responses | Present as `/live`, `/ready`, and conditional `/db-health`. | Executable TestClient evidence where dependency state can be controlled without PostgreSQL. |
| OpenAPI JSON | Present when docs/OpenAPI are enabled in allowed environments. | Executable TestClient evidence under `test_response_security_headers_contract.py`. |
| Docs HTML | Present when docs are enabled in allowed environments. | Executable TestClient evidence under `test_response_security_headers_contract.py`. |
| Backend mounted static responses | Present: `/static` is mounted with `StaticFiles`, and tracked assets exist under `backend/static`, including `backend/static/seed/venues/harrison-park/gallery-1.webp` served at `/static/seed/venues/harrison-park/gallery-1.webp`. Mounted static responses are intentionally outside the generic FastAPI API response-security-header policy while remaining subject to applicable canonical app middleware, including Host enforcement. | TestClient evidence under `test_host_contract.py` that allowed Host can reach the concrete asset and disallowed Host is rejected before exposure; TestClient/static evidence under `test_edge_boundary_static_contract.py` that the real mounted static response stays outside the generic API header policy without creating an alternate owner. |
| File/download/image binary response classes | No current app-owned `FileResponse`, `StreamingResponse`, or binary/image route response class was found in backend source. Mounted static assets are tracked separately as the static response class above. | Static absence/non-ownership evidence only; no executable response test is required for a nonexistent app-owned binary route surface. |
| Explicit application redirects | No current source-owned canonical-host redirect, HTTP-to-HTTPS redirect, TLS redirect, or equivalent edge redirect is approved in backend source. | Static absence/non-ownership evidence that WS02-03 does not invent app-owned edge redirects. |
| Framework routing redirects | Present: current FastAPI/Starlette routing has `redirect_slashes=True`; `GET /live/` with redirect following disabled produces `307` to `/live`. | TestClient evidence under `test_edge_boundary_static_contract.py` that the alternate slash form redirects to the canonical route form and that the generic API response-security-header policy does not take ownership of the routing redirect response. |
| 204/no-content responses | Present at `DELETE /auth/unfinished-account`. | Executable or direct middleware/helper evidence that 204 responses receive the intended app-owned API headers without body assumptions. |
| Explicit route cache-policy responses | Present in current game, community-game-detail, my-games, and health/diagnostic source paths. | Direct middleware/helper evidence that explicit `Cache-Control` is preserved, plus static inventory of current explicit route cache owners. |

### 4.5 Documentation And OpenAPI Contract

Interactive documentation HTML receives the API policy plus documentation-only
browser controls:

- `Content-Security-Policy: frame-ancestors 'none'`;
- `X-Frame-Options: DENY`;
- restrictive `Permissions-Policy` for capabilities not needed by generated API
  documentation.

The docs CSP is limited to frame ownership so generated documentation resources
are not broken by an invented broad CSP. OpenAPI schema JSON receives JSON/API
headers only. Production cannot silently enable docs through source defaults;
preview and staging follow production-like defaults unless later approved
evidence says otherwise.

### 4.6 Proxy, TLS, HSTS, Canonical Host, And Direct-Origin Boundary

WS02-03 must not fabricate provider topology.

Repository source must continue to prove only these local facts:

- no source path trusts `X-Forwarded-Host`, `Forwarded`, forwarded scheme, or
  forwarded client-address metadata as production authority;
- no unapproved `ProxyHeadersMiddleware` or equivalent trusted-proxy behavior is
  installed;
- no app-owned HTTPS redirect, HSTS policy, canonical-host redirect, or
  direct-origin restriction is invented without provider evidence;
- README/provider names do not become trusted hostnames by implication.

Actual public topology remains external evidence until sanitized provider and
staging evidence is accepted.

### 4.7 Provider-Evidence Checklist And WS02-03 Evidence Profile

The canonical reusable provider-evidence checklist is:

```text
docs/production-readiness/governance/provider-evidence-checklist.md
```

WS02-03 must use that existing governance artifact as the provider-evidence
checklist framework. This pass must not create or modify a generic provider
checklist.

The WS02-03 evidence profile that future sanitized provider/staging evidence
must cover is:

- frontend public/custom domains;
- API public/custom domains;
- provider-generated origin domains;
- DNS owner and authority;
- TLS termination/certificate status;
- HTTPS redirect behavior;
- HSTS ownership and observed value;
- canonical-host behavior;
- direct-origin reachability/restriction;
- trusted immediate proxy;
- forwarded Host behavior;
- forwarded scheme behavior;
- forwarded client-address behavior;
- multi-hop normalization where applicable;
- proxy-spoof observations;
- provider-added response headers;
- provider-removed or provider-overwritten response headers;
- duplicate-header precedence;
- staging API JSON capture;
- staging API-error capture;
- staging health/diagnostic capture;
- staging docs HTML capture;
- staging OpenAPI JSON capture;
- staging redirect capture;
- staging static/file response capture where applicable;
- release/deployment identity associated with the observations.

The existing checklist remains unchanged until actual evidence is collected by
the appropriate provider/evidence workflow.

## 5. Implementation Scope

The pass-owned implementation and evidence scope is limited to the artifacts
needed to satisfy this plan:

- one targeted production source correction in `backend/main.py` to replace
  wildcard CORS methods and headers with the exact reviewed method allowlist
  and exact application-configured request-header allowlist in Section 4.3;
- WS02-03 requirement declarations under `backend/tests/support/requirements/`;
- a WS02-03 human testing/risk record under the trusted platform HTTP-security
  scope;
- fresh trusted platform tests under `backend/tests/platform/http_security/`;
- source/static evidence checks needed for single-owner, bypass, non-trust,
  response-class, Host, CORS, and provider-boundary proof.

The pass must not change provider dashboards, DNS, Vercel, Render, frontend
hosting headers, TLS settings, deployment manifests, `.github` workflows, broad
application behavior, authentication, payments, storage, database models,
migrations, timeout/rate-limit policy, logging rollout, frontend source, or
tests outside the authorized WS02-03 file set.

If implementation reveals a source defect beyond the explicit CORS wildcard
correction, the pass must return for planning review rather than silently
broadening scope.

## 6. Testing And Evidence

WS02-03 evidence must follow the EN-01 testing architecture. The trusted local
scope for this pass is:

```text
backend/tests/platform/http_security/
```

The pass-owned evidence file set is:

- `backend/tests/platform/http_security/TESTING_RECORD.md`;
- `backend/tests/platform/http_security/test_host_contract.py`;
- `backend/tests/platform/http_security/test_cors_contract.py`;
- `backend/tests/platform/http_security/test_response_security_headers_contract.py`;
- `backend/tests/platform/http_security/test_edge_boundary_static_contract.py`;
- `backend/tests/support/requirements/ws02_03.json`.

Executable local evidence may use:

- pure settings validation for configured Host and CORS classes;
- FastAPI `TestClient` for app-owned request/response behavior;
- raw ASGI or middleware-level proof where `TestClient` hides a material
  middleware detail;
- static source/config checks for canonical app ownership, duplicate middleware,
  manual CORS/OPTIONS bypass, forwarded-header non-trust, no app HSTS/HTTPS
  redirect, and no invented provider topology.

Executable local evidence must not use PostgreSQL, provider/network access,
browser/Playwright, migration/schema-history execution, concurrency, controlled
time, or a live subprocess/server because current planning analysis finds no such
need.

The testing record must explain scenario selection and evidence quality,
including:

- Host classes: allowed exact host, case normalization, harmless trailing dot,
  disallowed Host, wildcard, localhost in production-like env, missing
  production-like allowlist, blank entry, malformed DNS label, scheme, path,
  query, fragment, credentials, port, control characters, no allowlist
  disclosure, normal API route, health, diagnostics, docs, OpenAPI, error path,
  webhook, allowed Host access to the concrete mounted static asset,
  disallowed Host rejection before the asset is exposed, and mounted/static
  behavior where ownership matters;
- CORS classes: allowed/disallowed simple request, allowed/disallowed preflight,
  credentials, null Origin, missing Origin, wildcard prohibition, prefix/suffix
  confusion, lookalike domain, scheme confusion, port confusion,
  path/query confusion, current web-origin case behavior, `Vary: Origin`,
  allowed-origin errors, disallowed-origin errors, no manual OPTIONS bypass,
  exact reflection only when allowed, exact method allowlist, exact
  application-configured request-header allowlist, effective Starlette
  safelisted-header behavior, case-insensitive header-name matching, and
  rejection of arbitrary non-approved headers such as `X-Custom-Header`,
  `X-Admin`, and `X-Forwarded-Host`;
- response classes: ordinary public API JSON, private API JSON, auth/authz
  failure, validation error, application error, 404, webhook, `/live`, `/ready`,
  `/db-health`, OpenAPI JSON, docs HTML, backend mounted static responses,
  absent app-owned file/download/image binary response classes, absent explicit
  application redirects, present framework routing redirects, 204/no-content,
  and current explicit route cache policies;
- edge boundary: source non-trust of forwarded values, no source-owned TLS/HSTS
  or canonical redirect, no duplicate provider/header ownership claim, and
  explicit external/staging evidence required.

Checker `PASS` remains structural compliance. Human review remains responsible
for confirming that the selected scenario groups are adequate for the risks.

### 6.1 Requirement Declaration Design

| ID | owning_pass | source_controls | state | scope | reason |
|---|---|---|---|---|---|
| `WS02-03-R1` | `WS02-03` | `API-M04`, `API-M05`, `API-M06`, `API-M07`, `API-M08`, `FDN-02` | `covered_elsewhere` | `planning` | The canonical WS02-03 plan contains the FDN-02 response-class ownership matrix. Executable source conformance and bypass resistance are proven separately by R5, R6, R7, and R9. |
| `WS02-03-R2` | `WS02-03` | `API-M05`, `WS02-01` | `required` | `platform/http_security` |  |
| `WS02-03-R3` | `WS02-03` | `API-M05`, `API-M08`, `WS02-02` | `required` | `platform/http_security` |  |
| `WS02-03-R4` | `WS02-03` | `API-M07`, `API-M05`, `WS02-01` | `required` | `platform/http_security` |  |
| `WS02-03-R5` | `WS02-03` | `API-M08`, `FDN-02`, `API-M16`, `WS02-05` | `required` | `platform/http_security` |  |
| `WS02-03-R6` | `WS02-03` | `API-M08`, `FDN-02`, `FDN-03`, `WS02-05` | `required` | `platform/http_security` |  |
| `WS02-03-R7` | `WS02-03` | `API-M04`, `API-M05`, `API-M06`, `FDN-02` | `required` | `platform/http_security` |  |
| `WS02-03-R8` | `WS02-03` | `API-M04`, `API-M05`, `API-M06`, `API-M07`, `API-M08`, `OPS-025`, `WS10-02` | `deferred` | `governance` | Actual edge/origin topology, TLS/HSTS behavior, canonical-host and direct-origin behavior, trusted-proxy behavior, deployed CORS, provider header precedence, redirect traces, proxy-spoof observations, and staging response captures remain unverified external evidence. The canonical provider-evidence checklist and the WS02-03 evidence profile preserve these gaps without fabricating provider facts. |
| `WS02-03-R9` | `WS02-03` | `API-M04`, `API-M05`, `API-M07`, `API-M08`, `WS02-02` | `required` | `platform/http_security` |  |

`WS02-03-R1` and `WS02-03-R8` must receive no pytest mapping. The future
testing record must still explain both requirements and why their proof is
non-executable. Executable mapping applies only to `WS02-03-R2` through
`WS02-03-R7` and `WS02-03-R9`.

### 6.2 Evidence Design

| Requirement | Risks | Scenario groups | Proof layer | Executable mapping |
|---|---|---|---|---|
| `WS02-03-R1` | Wrong owner or false closure. | FDN-02 ownership matrix and response-class ownership split. | Canonical plan/governance review. | No pytest mapping. |
| `WS02-03-R2` | Unsafe Host configuration accepted. | Missing, wildcard, local-only, malformed, URL-like, port-bearing, and normalized configured hosts. | Settings pytest. | `test_host_contract.py` |
| `WS02-03-R3` | Host middleware bypass or allowlist disclosure. | Allowed/disallowed Host across API, health, docs, OpenAPI, errors, webhooks, concrete mounted static asset access, and static/mount boundary. | TestClient/raw ASGI where needed. | `test_host_contract.py` |
| `WS02-03-R4` | Overbroad browser API access. | Exact origin, exact method allowlist, exact application-configured request-header allowlist, wildcard `allow_headers` removal, preflight acceptance for `Authorization` and `X-Request-ID`, Starlette safelisted-header acceptance for `Accept`, `Accept-Language`, `Content-Language`, and `Content-Type`, arbitrary header rejection, case-insensitive header-name matching, allowed/disallowed errors, and no manual OPTIONS bypass. | Source correction plus TestClient/static proof that interprets `Access-Control-Allow-Headers` according to Starlette's effective non-wildcard header set. | `test_cors_contract.py` |
| `WS02-03-R5` | Missing, overbroad, or overwritten API headers/cache. | Public/private JSON, errors, health, webhook, OpenAPI JSON, 204, explicit route cache preservation. | TestClient/direct middleware/helper/static proof. | `test_response_security_headers_contract.py` |
| `WS02-03-R6` | Docs HTML and OpenAPI JSON receive wrong ownership. | Docs HTML controls, OpenAPI JSON controls, production-like docs boundary. | TestClient/settings proof. | `test_response_security_headers_contract.py` |
| `WS02-03-R7` | Spoofed forwarded metadata or invented edge ownership. | Forwarded Host/scheme/client-address non-trust, no proxy middleware, no app TLS/HSTS/canonical redirect. | Static source/config proof. | `test_edge_boundary_static_contract.py` |
| `WS02-03-R8` | Provider gaps hidden by local tests. | WS02-03 provider-evidence profile and deferred external evidence. | Governance/evidence process. | No pytest mapping. |
| `WS02-03-R9` | Alternate owner or bypass path. | Canonical app construction, duplicate middleware absence, manual CORS/OPTIONS absence, response-header/cache bypass resistance, real mounted static exclusion from generic API header ownership, and framework routing redirect exclusion from generic API header ownership. | Static/TestClient proof. | `test_edge_boundary_static_contract.py` |

### 6.3 Evidence And File Responsibilities

| Path | Action | Responsibility | Requirement mapping |
|---|---|---|---|
| `backend/main.py` | Modify | Replace wildcard CORS methods and wildcard CORS request headers with the exact reviewed method allowlist and exact application-configured request-header allowlist only. | `WS02-03-R4` |
| `backend/tests/support/requirements/ws02_03.json` | Create | Declare `WS02-03-R1` through `WS02-03-R9` using the design above. | All WS02-03 declarations |
| `backend/tests/platform/http_security/TESTING_RECORD.md` | Create | Human risk/evidence record; explain R1/R8 non-executable ownership and deferred evidence. | All WS02-03 requirements |
| `backend/tests/platform/http_security/test_host_contract.py` | Create | Host settings and Host runtime enforcement evidence, including concrete mounted static asset access/rejection. | `WS02-03-R2`, `WS02-03-R3` |
| `backend/tests/platform/http_security/test_cors_contract.py` | Create | Exact-origin, exact-method, exact application-configured headers, Starlette safelisted-header, arbitrary-header rejection, preflight/simple, and CORS bypass evidence. | `WS02-03-R4` |
| `backend/tests/platform/http_security/test_response_security_headers_contract.py` | Create | Response-class security headers, docs/OpenAPI, cache preservation, current response-class inventory evidence. | `WS02-03-R5`, `WS02-03-R6` |
| `backend/tests/platform/http_security/test_edge_boundary_static_contract.py` | Create | Forwarded-header non-trust, no invented edge ownership, canonical app/middleware/bypass static evidence, mounted static ownership exclusion, and framework routing redirect ownership exclusion. | `WS02-03-R7`, `WS02-03-R9` |

The existing provider checklist at
`docs/production-readiness/governance/provider-evidence-checklist.md` is a
read-only evidence framework for this pass, not a pass-owned changed file.

## 7. Integration / Operational Expectations

WS02-03 inherits from WS02-01:

- typed backend environment identity;
- `ALLOWED_HOSTS`;
- `CORS_ALLOWED_ORIGINS`;
- production-like unsafe-default rejection;
- repository-versus-external environment boundary.

WS02-03 inherits from WS02-02:

- one canonical FastAPI app construction path;
- lifecycle-owned `/live` and `/ready`;
- conditional `/db-health`;
- app construction and middleware boundary;
- deferred deployment/runtime topology.

WS02-03 integrates with downstream and adjacent controls:

- WS02-04A stable errors must continue to receive CORS and response-security
  headers where the current middleware stack owns them, while invalid Host
  remains middleware-owned;
- WS02-05A cache/OpenAPI/docs behavior strengthens the response-class cache and
  docs/OpenAPI contracts and must not be weakened;
- WS07 owns frontend HTML/static browser security headers and frontend
  production artifact proof;
- WS10/provider work owns provider dashboards, access, DNS/TLS, secret-store,
  deployment, and sanitized provider evidence packages;
- API-M19 and release/deployment evidence require later staging HTTP-chain proof
  tied to an accepted release artifact.

Operationally, accepting WS02-03 means the repository-owned HTTP security
foundation is ready for human review. It does not mean public edge, DNS, TLS,
HSTS, direct-origin, provider-header, or staging evidence is closed.

## 8. Not Part Of This Pass

WS02-03 does not implement or close:

- broad deployment topology;
- provider dashboard changes;
- DNS, CDN, registrar, certificate, or custom-domain configuration;
- actual TLS termination, certificate renewal, HTTPS redirect, or HSTS proof;
- direct-origin blocking or provider-generated domain suppression;
- trusted proxy chain configuration or multi-hop forwarded-header
  normalization;
- canonical-host redirects;
- frontend HTML/static security-header implementation;
- provider-added header precedence;
- browser-observed production/staging captures;
- full API-M19 end-to-end HTTP-chain acceptance;
- authentication or authorization redesign;
- request limits, timeouts, rate limits, retries, or load policy;
- database behavior, migrations, models, or PostgreSQL tests;
- provider-contract tests or uncontrolled network calls;
- broad logging, metrics, dashboards, tracing, alerting, or release gates.

These are not ignored. They remain explicit external, downstream, or later-pass
evidence requirements.

## 9. Related Controls And Remaining Evidence

| Control / Decision | WS02-03 Relationship | Remaining Evidence Boundary |
|---|---|---|
| `API-M04` | Source must not trust unverified forwarded Host/scheme/client-address metadata and must preserve proxy/direct-origin evidence gaps. | Trusted proxy chain, multi-hop normalization, direct-origin restriction, and proxy-spoof staging proof require external provider and staging evidence. |
| `API-M05` | Source owns typed Host allowlist validation and FastAPI Host enforcement. | Public/custom domains, provider-generated origin domains, canonical-host behavior, and direct-origin host policy require provider/DNS evidence. |
| `API-M06` | Source must not claim TLS redirect/HSTS ownership without approved edge evidence. | TLS certificate status, HTTPS redirect behavior, HSTS, redirect-loop checks, and public edge captures remain external. |
| `API-M07` | Source owns exact-origin credentialed CORS, exact reviewed methods, exact application-configured request headers, and non-wildcard Starlette safelisted-header runtime behavior. | Deployed browser-observed CORS captures and provider/header interactions remain external. |
| `API-M08` / `FDN-02` | Source owns API JSON and docs/OpenAPI app headers by response class; R1 records the ownership matrix as planning/governance evidence. | Frontend headers, provider-added headers, duplicate-header precedence, and staging response captures remain external. |
| `API-M16` | WS02-05A strengthened private/public API cache behavior that WS02-03 response-class evidence must preserve. | Shared/CDN cache behavior and deployed cache observations remain external/later. |
| `API-M19` | WS02-03 provides source-owned HTTP-chain pieces but does not close full chain proof. | Authorized staging HTTP-chain report tied to release/deployment evidence remains later. |
| `OPS-025` / `WS10-02` | Provider evidence must be sanitized and handled under the existing provider evidence checklist and the WS02-03 evidence profile. | Provider account, access, MFA, settings, deployment, DNS/TLS, and logs remain provider/control-plane evidence. |

## 10. Completion Criteria

WS02-03 is complete only when all of the following are true:

- [ ] The canonical plan is reconciled with current authority and current
  source.
- [ ] Stable WS02-03 requirement declarations exist and parse under the EN-01
  checker.
- [ ] `WS02-03-R1` is declared as `covered_elsewhere` with `scope: planning`
  and receives no pytest mapping.
- [ ] `WS02-03-R8` is declared as `deferred` with `scope: governance` and
  receives no pytest mapping.
- [ ] `backend/main.py` no longer uses wildcard CORS methods or wildcard CORS
  request headers.
- [ ] `backend/main.py` uses exactly the reviewed CORS methods `GET`, `POST`,
  `PUT`, `PATCH`, and `DELETE`.
- [ ] `backend/main.py` uses exactly the reviewed application-configured
  CORSMiddleware request headers `Accept`, `Authorization`, `Content-Type`, and
  `X-Request-ID`, while trusted evidence interprets Starlette's effective
  runtime header set as the configured list plus framework CORS-safelisted
  headers.
- [ ] The human testing/risk record clearly separates source-owned proof from
  external provider/staging proof.
- [ ] Fresh trusted tests under `backend/tests/platform/http_security/` prove
  only executable `WS02-03-R2` through `WS02-03-R7` and `WS02-03-R9`
  requirements.
- [ ] Trusted evidence proves backend-mounted static responses are present,
  Host-enforced, and intentionally outside the generic API response-header
  policy.
- [ ] Trusted evidence proves explicit application redirects remain absent and
  framework routing redirects remain outside generic API response-header
  ownership.
- [ ] Checker domain scope for `backend/tests/platform/http_security` passes.
- [ ] Checker suite scope passes.
- [ ] `git diff --check` passes.
- [ ] No provider dashboard, DNS, TLS, frontend hosting, deployment, CI,
  database, migration, or unrelated production behavior is changed.
- [ ] No new provider checklist is created.
- [ ] No secret values, credential-bearing commands, provider tokens, private
  keys, database URLs, real user/payment/provider data, private URLs, or copied
  provider evidence are introduced.
- [ ] Completion claims do not close actual public topology, TLS/HSTS,
  canonical host, direct-origin restriction, trusted proxy chain, provider-added
  header precedence, staging captures, or API-M19 end-to-end HTTP-chain proof.

When these criteria are satisfied, WS02-03 may be accepted as the
repository-owned HTTP security foundation while preserving downstream external
evidence obligations.
