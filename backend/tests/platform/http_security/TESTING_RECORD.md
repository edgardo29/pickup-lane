# WS02-03 HTTP Security Testing Record

## Scope

This record covers the WS02-03 trusted platform HTTP-security evidence under
`backend/tests/platform/http_security/`. The scope proves repository-owned
FastAPI Host enforcement, exact CORS configuration and runtime behavior,
response-class security-header ownership, and source/static bypass resistance.

The scope does not prove DNS, TLS, HSTS, canonical-host behavior, direct-origin
restriction, trusted proxy topology, deployed provider headers, browser
captures, provider dashboards, deployment settings, database behavior, or
frontend HTML/static security headers.

## Authoritative Basis

- Canonical WS02-03 planning document.
- FDN-02 application/edge response-header ownership matrix.
- WS02-01 typed settings and environment boundary.
- WS02-02 canonical app construction and runtime boundary.
- EN-01 trusted testing architecture and checker requirements.

## Requirements And Evidence

| Requirement | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS02-03-R1` | Response-class ownership matrix is a planning/governance artifact. | Covered elsewhere by the canonical WS02-03 plan; no pytest mapping. |
| `WS02-03-R2` | `ALLOWED_HOSTS` is a typed safe Host allowlist. | Pytest settings evidence in `test_host_contract.py`. |
| `WS02-03-R3` | Host enforcement applies through the canonical app path without allowlist disclosure. | Pytest runtime evidence in `test_host_contract.py`. |
| `WS02-03-R4` | CORS uses exact configured origins/methods/application headers and non-wildcard Starlette safelisted behavior. | Pytest source/runtime evidence in `test_cors_contract.py`. |
| `WS02-03-R5` | FastAPI-owned API response classes receive app-owned headers and cache protections. | Pytest direct/TestClient evidence in `test_response_security_headers_contract.py`. |
| `WS02-03-R6` | Docs HTML and OpenAPI JSON keep distinct response-header ownership. | Pytest TestClient evidence in `test_response_security_headers_contract.py`. |
| `WS02-03-R7` | Source does not invent proxy, TLS, HSTS, canonical-host, or forwarded-header trust. | Pytest static source evidence in `test_edge_boundary_static_contract.py`. |
| `WS02-03-R8` | Provider/edge evidence remains deferred until sanitized external evidence exists. | Deferred governance evidence; no pytest mapping. |
| `WS02-03-R9` | Host, CORS, response headers, static/redirect exclusions, and app construction preserve single ownership. | Pytest source/runtime evidence in `test_edge_boundary_static_contract.py`. |

## Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `WS02-03-R2`, `WS02-03-R3` | Host trust is explicit, typed, and enforced before route/static exposure. | Wildcards, local production hosts, URL-like values, malformed hosts, or bypass surfaces are accepted. | Backend behavior is reachable through unintended hostnames or configured hostnames leak. | Settings validation plus `TrustedHostMiddleware` with `www_redirect=False`. | platform |
| `WS02-03-R4` | CORS is exact and non-wildcard. | Wildcard methods/headers remain, arbitrary headers are accepted, disallowed origins receive credentials, or a manual bypass is introduced. | Browser origins or request headers outside the reviewed contract gain API access. | Exact `CORSMiddleware` configuration plus Starlette non-wildcard runtime behavior. | platform |
| `WS02-03-R5`, `WS02-03-R6` | FastAPI-owned API response classes get the right API/docs headers while preserving explicit cache decisions. | API JSON, errors, health, docs, OpenAPI, webhooks, or 204 responses miss protections or docs/OpenAPI ownership is mixed. | Sensitive API data can be cached or exposed through incorrect browser behavior. | Central response-header middleware with response-class checks. | platform |
| `WS02-03-R7`, `WS02-03-R9` | The app does not claim external edge behavior and does not create alternate owners. | Source trusts forwarded metadata, adds TLS/HSTS/canonical redirects, duplicates middleware, or applies API header policy to static/redirect responses. | Local tests falsely close provider risks or app paths bypass the reviewed owner model. | Static source checks plus TestClient proof for real static and framework redirect surfaces. | platform |
| `WS02-03-R1`, `WS02-03-R8` | Planning and governance preserve ownership and deferred provider evidence. | Pytest pretends to prove ownership matrices or real deployment topology. | False closure of provider/edge controls. | Canonical plan, provider-evidence checklist, and later sanitized provider/staging evidence. | planning/governance |

## Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | Browser clients, provider webhook caller, framework middleware, app source. | Grouped. | HTTP security behavior is actor-agnostic at this layer; auth/domain actors are not under test. |
| States / lifecycle | Local/test defaults, production-like settings, docs enabled/disabled, DB health enabled/disabled. | Covered. | Settings and TestClient cases cover the material source-owned environment states without contacting the database. |
| Actions | GET, POST, PUT, PATCH, DELETE, preflight OPTIONS, framework slash redirect, mounted static read. | Covered. | These are the reviewed browser/API CORS methods and response-class surfaces. |
| Inputs / boundaries | Host values, Origin values, CORS methods, request headers, static path, redirect slash form. | Covered. | Tests include valid, malformed, wildcard, local-only, disallowed, safelisted, and arbitrary-header classes. |
| Time | Not applicable. | Not applicable. | WS02-03 has no time-boundary behavior. |
| Dependencies | FastAPI/Starlette middleware, settings parser, static filesystem asset. | Covered. | All proof is local and deterministic; no provider or database dependency is required. |
| Concurrency / idempotency | Not applicable. | Not applicable. | WS02-03 does not mutate state or coordinate retries. |
| Authorization / privacy / security | Host, CORS, cache/privacy headers, forwarded-header non-trust. | Covered. | These are the core HTTP-security boundaries for this pass. |
| Persistence / rollback | Not applicable. | Not applicable. | The tests perform no persistence or mutations. |
| Recovery | Provider/deployment evidence remains later. | Deferred. | Repository pytest cannot honestly prove deployed edge behavior. |

## Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `WS02-03-R2`, `WS02-03-R3` | Host configuration and runtime enforcement across API, health, docs, OpenAPI, errors, webhook, and static. | Settings pytest and TestClient. | `test_host_contract.py`. | Adequate for repository-owned Host validation/enforcement; public host inventory remains external. |
| `WS02-03-R4` | Exact CORS method/header configuration, Starlette safelisted runtime behavior, origin confusion, preflight/simple requests, and bypass absence. | TestClient and static source checks. | `test_cors_contract.py`. | Adequate for source-owned CORS policy; deployed browser captures remain external. |
| `WS02-03-R5`, `WS02-03-R6` | API JSON, errors, health, webhook, OpenAPI JSON, docs HTML, 204, and explicit cache policy preservation. | TestClient and direct middleware/helper checks. | `test_response_security_headers_contract.py`. | Adequate for FastAPI-owned response classes; provider/header precedence remains external. |
| `WS02-03-R7`, `WS02-03-R9` | No forwarded-header trust, no app TLS/HSTS/canonical redirect, no duplicate middleware, static exclusion, and framework redirect exclusion. | Static source checks and TestClient. | `test_edge_boundary_static_contract.py`. | Adequate for repository non-ownership and bypass resistance; provider topology remains external. |
| `WS02-03-R1` | Response-class ownership matrix. | Planning/governance review. | Canonical WS02-03 plan. | Adequate for planning artifact; no pytest mapping is appropriate. |
| `WS02-03-R8` | Provider/edge evidence profile and deferred gaps. | Governance/later evidence. | Canonical WS02-03 plan and provider-evidence checklist. | Not complete until sanitized external evidence exists. |

## Important Side Effects

This scope is pure policy, configuration, middleware, and static/source
evidence. It performs no database writes, provider calls, deployed
configuration changes, DNS/TLS changes, frontend changes, or external evidence
publication.

## Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS02-03-R1` | covered_elsewhere | The ownership matrix is the canonical planning artifact and must not be reduced to a fake pytest assertion. | Canonical WS02-03 plan and human review. |
| `WS02-03-R8` | deferred | Actual edge/origin topology, TLS/HSTS, canonical-host, direct-origin, trusted-proxy, deployed CORS, provider header precedence, redirect traces, proxy-spoof observations, and staging response captures require sanitized external evidence. | Provider/evidence workflow using the canonical provider-evidence checklist and WS02-03 evidence profile. |
| Deployed response captures | deferred | Local TestClient cannot prove public edge/provider behavior. | Later staging/provider evidence. |
| Frontend HTML/static headers | outside scope | WS02-03 owns backend API/source behavior only. | WS07 and frontend/provider evidence. |

## Adequacy Conclusion

WS02-03 trusted local evidence is adequate for Gate C review when the four
platform HTTP-security pytest modules pass, the checker domain and suite scopes
pass, generated traceability maps `WS02-03-R2` through `WS02-03-R7` and
`WS02-03-R9` to trusted pytest nodes, and human review confirms that `R1` and
`R8` remain correctly non-executable.

Checker `PASS` is structural compliance only. It does not close provider,
runtime, browser, DNS/TLS, staging, or API-M19 end-to-end HTTP-chain evidence.
