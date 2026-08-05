# WS02-03 Proxy, Host, TLS, CORS, and Response-Class Security Headers

Status: implemented for repository source and current tests.

## Scope

WS02-03 implements only FastAPI-owned source controls for host validation,
current CORS runtime behavior, and response-class security headers.

This pass does not change provider dashboards, DNS, CDN, frontend hosting
headers, deployment manifests, workers, processes, database pools, request
timeouts, authentication, payments, storage, migrations, or data models.

## Repository-Proven Request Path Facts

- The backend application is built by `backend/main.py`.
- Backend configuration is centralized in `backend/settings.py`.
- FastAPI owns API JSON, health, diagnostic, API error, API documentation, and
  OpenAPI schema responses emitted by the backend application.
- Frontend HTML and static-asset headers are not owned by the backend API
  source.
- TLS termination, HTTP-to-HTTPS redirects, HSTS, direct-origin reachability,
  canonical-host redirects, forwarded-header trust, and provider-added response
  headers are not proven by repository source.

## External Facts Still Required

The repository does not prove deployed public topology. The following remain
external provider or owner evidence:

- frontend public and custom domains
- API public and custom domains
- provider-generated origin domains
- DNS ownership and record authority
- CDN or proxy participation
- TLS termination and certificate status
- HTTP redirect behavior
- HSTS ownership
- direct-origin reachability
- forwarded-header behavior
- trusted proxy boundary
- health-check path configured by the backend host
- provider-added, removed, or overwritten headers
- duplicate-header and precedence behavior
- deployed response captures by response class

## FDN-02 Ownership Matrix

| Control | Application-owned source behavior | Edge/provider-owned behavior | WS02-03 status |
|---|---|---|---|
| Host validation | FastAPI accepts only configured Host values from typed settings. Invalid hosts are rejected before route handling and without allowlist disclosure. | Public host inventory, direct-origin exposure, canonical host policy, provider-generated hosts, and edge-level host filtering. | Advanced in source; requires deployed topology evidence. |
| CORS | FastAPI keeps exact-origin allowlist behavior with credentials, safe preflight handling, null-origin denial, and no wildcard credentialed production-like configuration. | Browser-facing production origin list and any provider-level CORS or header behavior. | Advanced in source; requires deployed response captures. |
| API JSON headers | FastAPI-owned JSON, error, health, diagnostic, webhook, and no-content responses receive source-owned cache, content-sniffing, and referrer protections unless a route declares a deliberate cache policy. | Edge may add, preserve, or override headers and must be verified for conflicts. | Advanced in source; requires deployed precedence evidence. |
| Interactive API documentation | FastAPI applies a documentation-specific policy when docs are enabled in allowed environments. | Hosting access policy, public exposure decision, and deployed availability must be verified externally. | Advanced in source; production-like docs exposure remains restricted by settings. |
| OpenAPI schema JSON | FastAPI applies API JSON protections without treating schema JSON as HTML. | Public exposure and edge-header interaction require deployed evidence. | Advanced in source; requires deployed captures. |
| Frontend HTML and static assets | Not owned by backend API source. | Frontend hosting edge owns HTML, static-asset, browser CSP, framing, permissions, referrer, cache, and preload behavior. | Not implemented in this pass. |
| TLS, HTTPS redirect, and HSTS | Not implemented in backend source. | Public edge or hosting provider owns TLS, redirects, certificate renewal, and HSTS. | Not implemented in this pass. |
| Forwarded headers and client IP | Backend does not expand trust or rely on forwarded host as trusted host identity. | Trusted proxy chain, direct-origin restrictions, and forwarded-header normalization require provider topology evidence. | Not implemented in this pass. |

## Host-Validation Contract

`ALLOWED_HOSTS` is the typed application Host allowlist setting.

Local and test environments keep known development and test-client defaults.
Preview, staging, and production require an explicit non-empty host allowlist.
Production-like environments reject global wildcard hosts and local-only hosts.

Host entries are normalized for case and harmless trailing-dot differences.
Entries containing schemes, paths, queries, fragments, credentials, control
characters, blank values, malformed labels, or ports are rejected. Host values
are not derived from CORS origins, frontend URLs, provider-generated domains, or
deployment provider names.

FastAPI uses framework-supported Host validation. The boundary applies to
health, diagnostics, docs, OpenAPI, errors, webhook paths, and normal API routes.
Invalid Host responses do not expose configured allowlist values.

## CORS Contract

CORS remains owned by the existing typed origin setting and FastAPI middleware.

Runtime behavior proves:

- explicitly allowed origins receive exact allow-origin responses
- credentialed requests receive credentialed CORS behavior
- allowed preflight requests succeed
- disallowed preflight requests fail safely
- disallowed simple requests do not receive allow-origin
- null origin is not implicitly allowed
- wildcard credentialed production-like configuration remains rejected
- suffix, prefix, path, case-confusion, and lookalike origins are not accepted
- controlled application errors preserve CORS headers when the request origin is
  allowed
- responses that vary by origin include the correct vary behavior

No separate OPTIONS route was added.

## FastAPI-Owned Response Classes

The FastAPI response-header policy is centralized in `backend/main.py`.

The application-owned API policy applies:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Cache-Control: no-store` when the route has not deliberately set its own
  cache policy

Covered source-owned response classes:

- normal API JSON responses
- authentication and authorization failures
- validation and application errors
- not-found responses
- webhook responses
- no-content responses
- `/live`
- `/ready`
- enabled `/db-health`
- OpenAPI schema JSON

The policy preserves status codes, content type, explicit route cache headers,
and CORS headers.

## Documentation Response Behavior

Interactive documentation HTML receives the API policy plus documentation-only
anti-framing and browser-capability protections:

- `Content-Security-Policy: frame-ancestors 'none'`
- `X-Frame-Options: DENY`
- a restrictive `Permissions-Policy` that disables browser capabilities that are
  unnecessary for generated API documentation

The documentation CSP is limited to frame ownership so it does not break the
generated documentation resources.

OpenAPI schema JSON receives API JSON protections without HTML-only controls.
Production cannot silently enable docs through source defaults.

## Intentionally Excluded Response Classes

The policy intentionally avoids blanket handling for:

- redirects
- mounted static files
- image responses
- file/download responses
- responses with deliberate route-specific cache policies
- frontend HTML and frontend static assets

These classes require their own owner and deployed behavior evidence.

## Conflict and Precedence Policy

FastAPI source sets only the application-owned headers for the response classes
above. It does not overwrite an explicit route cache policy.

If an edge or hosting provider adds, removes, duplicates, or overwrites a header,
the provider behavior takes operational precedence for browser-observed traffic.
Those conflicts must be captured from deployed environments and recorded before
the related controls can close.

## Tests Added

Current non-legacy tests were added under
`backend/tests/shared/http_security/`.

They cover host configuration, Host validation, CORS exactness and credentialed
behavior, response-class security headers, documentation protections, health
contract preservation, explicit cache preservation, redirect/file/no-content
behavior, and provider-network-free app construction.

## Provider-Evidence Checklist

Collect only sanitized evidence. Do not record account identifiers, secrets,
private URLs, credentials, tokens, screenshots containing sensitive values, or
raw environment values.

Required evidence:

- frontend public and custom domain inventory
- API public and custom domain inventory
- provider-generated origin-domain inventory
- DNS owner and authority proof
- CDN or proxy participation proof
- TLS termination and certificate proof
- HTTP redirect observations
- HSTS ownership and deployed header observations
- direct-origin reachability observations
- forwarded-header behavior captures
- trusted proxy boundary record
- hosting health-check path and behavior
- provider-added or removed header inventory
- duplicate-header and precedence observations
- deployed captures for API JSON, API errors, health, diagnostics,
  documentation HTML, OpenAPI schema JSON, redirects, and static/file responses

## Controls Advanced But Not Closed

API-M04, API-M05, API-M06, API-M07, and API-M08 are advanced by repository
source and current tests. They are not closed by this pass because deployed
edge, provider, DNS, TLS, proxy, direct-origin, frontend-header, and precedence
evidence remains external.

## Why Provider Configuration Was Not Changed

No Vercel, Render, DNS, CDN, or provider configuration was changed because the
approved WS02-03 scope is source-only and repository-proven. Adding deployment
configuration would require guessing public topology, hostnames, edge behavior,
trusted proxies, TLS ownership, or direct-origin policy.
