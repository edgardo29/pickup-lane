# WS02-05A HTTP, OpenAPI, Cache, And Compatibility Contracts

Status: implemented as source-owned foundation.

Branch: `pr/WS02-05A`

Baseline: `eb9e709f35fb89c1fbc655d5521912d72630c3e2`

## Scope Split

WS02-05A owns portable HTTP contract foundations:

- JSON media-type behavior for source-owned request-body routes
- framework-owned 405 preservation and documentation
- shared stable API error schemas in OpenAPI
- response-class cache policy
- local/test versus production docs/OpenAPI policy
- tombstone OpenAPI representation
- pagination inventory and contract guardrails
- rolling frontend/backend compatibility policy

WS02-05B remains responsible for compatibility-sensitive payload work:

- request-schema tightening and over-posting cleanup
- response minimization
- public, authenticated, admin, internal, and provider response separation
- frontend caller changes where a request or response contract changes

## JSON Media-Type Decision

Ordinary JSON request-body routes accept `application/json` and compatible JSON
parameters such as charset. Explicitly supplied non-JSON media types are
rejected with a source-owned 415 stable error response before route code runs.

Missing `Content-Type` remains compatible because there is not yet evidence that
all supported callers can tolerate a blanket rejection.

Malformed JSON using an accepted JSON media type keeps the existing stable 422
validation behavior. Request-size enforcement remains independent and may reject
oversized requests with 413 before parsing. Unsupported content encoding keeps
the existing 415 content-encoding contract.

Signed Stripe webhook handling remains raw-body owned. Bodyless tombstones and
other bodyless routes remain outside JSON media parsing.

## 405 Ownership

Unsupported methods remain owned by FastAPI/Starlette routing. The application
exception handler normalizes the response into the stable public error envelope
while preserving the framework `Allow` header.

WS02-05A does not add method aliases for obsolete clients.

## Stable Error OpenAPI Representation

OpenAPI now includes reusable public error schemas for the stable error
envelope and validation-error envelope. The schemas represent the runtime
contract without exposing internal exceptions, SQL, provider diagnostics,
configuration values, submitted sensitive values, or raw request content.

Common error responses are added from route metadata where applicable:

- authenticated and admin routes document auth failures
- JSON body routes document validation, body-limit, and media-type failures
- tombstones document 410
- chat message create routes document 429
- database-backed or readiness routes document 503
- resource routes with path parameters document 404
- mutation routes document possible conflict responses
- documented operations include the framework-owned method-not-allowed contract

## Cache Policy

Source-known authenticated, admin, and private API JSON responses use:

`Cache-Control: private, no-store`

Public API JSON, docs, OpenAPI, health, readiness, and public errors remain
conservatively non-cacheable with:

`Cache-Control: no-store`

Route-specific stricter policies are preserved. Redirect, static, and file
responses remain intentionally outside the generic API cache middleware.

WS02-05A does not introduce public max-age, validators, CDN caching, stale
revalidation, or static asset cache policy.

## Docs And OpenAPI Exposure

FDN-03 remains the controlling policy:

- local and test environments may expose interactive docs and OpenAPI
- production disables docs, Redoc, and raw OpenAPI schema
- preview and staging follow the existing production-like default
- hiding docs is never a substitute for route authorization

WS02-05A does not implement access-restricted production docs.

## Tombstone Representation

Current 410 compatibility tombstones remain visible in OpenAPI while the paths
exist. They are marked deprecated, retain their method and path, document 410,
and do not advertise removed request bodies.

WS02-05A does not invent removal dates and does not remove tombstone routes.

## Pagination Contract

WS02-05A records the current collection-route pagination contract instead of
forcing uniform numeric limits.

Shared principles:

- large collection routes must be bounded before production
- route-level and service-level maximums must not contradict each other
- cursor pagination must use deterministic ordering and a stable tie-breaker
- invalid cursors return stable client errors
- empty-page and next-cursor behavior is deterministic within a route family
- offset pagination remains allowed where intentionally selected
- existing approved numeric values are not reopened for aesthetic consistency

Routes with current source-owned bounds are registered in the pagination
contract inventory. Existing collection routes without an approved explicit
limit are recorded as handoff items rather than receiving invented values.

## Compatibility Model

Pickup Lane remains an internal web-application API. No public versioned API is
required for WS02-05A.

Rolling deployment expectations:

- additive backend changes are preferred
- removals use compatibility tombstones where necessary
- request tightening requires caller audit
- response-field removal requires caller audit
- a new frontend must not depend on new backend behavior until deployment
  sequencing supports it
- adjacent old/new frontend and backend versions should remain compatible

WS02-05A changes are designed to be backend-additive except for explicitly
non-JSON media types on JSON request-body routes, which are now rejected.

## WS02-05B Handoff

The following inspected contract risks remain deliberately outside WS02-05A:

| Area | Concern | Handoff |
|---|---|---|
| `GameCreate` / `GameUpdate` | Server-controlled and workflow-status fields remain request-visible on active admin routes. | Audit active callers and split request contracts safely. |
| Public game responses | Broad game read schemas expose internal/status fields beyond card/detail needs. | Minimize public response shapes after caller review. |
| User responses | Auth/provider/profile fields remain visible in user read schemas. | Separate public, self, and admin user read contracts. |
| Payment/admin-money responses | Provider-linked and financial state fields require audience review. | Confirm admin/self/internal response split. |
| Payment event reads | Raw provider event payload remains visible to admin repair APIs. | Decide whether a redacted/admin-only projection is required. |
| Image/upload responses | Upload action and storage metadata need audience minimization review. | Preserve upload workflow while separating internal metadata. |
| Chat, moderation, and support responses | Review/admin fields need audience-specific response contracts. | Separate public, participant, moderator, and admin views. |
| Policy/legal reads | Evidence and lifecycle fields need final read-contract review. | Preserve legal evidence while minimizing ordinary reads. |
| Unbounded collection routes | Several existing collection routes lack explicit approved pagination limits. | Select numeric bounds or retire/replace routes with bounded views. |

## Temporary-Demo Evidence

Current source tests can verify app-owned Host, CORS, cache, security headers,
error envelopes, body limits, 405, 413, 415, 429, 503, docs exposure, and
OpenAPI representation.

Temporary Render, Vercel, and Neon behavior is not permanent architecture and is
not hardened by this pass.

## Permanent Runtime Deferrals

The following remain external evidence after WS02-05A:

- TLS and HSTS ownership
- proxy/header precedence
- CDN and shared-cache behavior
- direct-origin protection
- edge-generated response behavior
- permanent redirect chain
- permanent staged response captures
- process-server method/header behavior

## Control Status

API-M13 advances for media type, status, 405, and stable error documentation.

API-M16 advances for source-owned private/public API cache behavior.

API-M18 advances for docs/OpenAPI environment policy, shared error schemas, and
tombstone representation.

API-M19 remains partial because permanent HTTP-chain evidence depends on final
hosting and edge choices.

API-M14 is explicitly handed to WS02-05B for request/response separation and
payload minimization.
