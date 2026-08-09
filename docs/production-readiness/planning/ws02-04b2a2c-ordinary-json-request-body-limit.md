# WS02-04B2A2C Ordinary JSON Request Body Limit

Pass: WS02-04B2A2C

Scope: source-owned activation of the general ordinary JSON request-body limit
after A2A, B1, B2, and B3 removed or bounded the prior blocker set.

## Prerequisites

- WS02-04B2A2A bounded active ordinary and admin workflow request schemas.
- WS02-04B2A2B1 retired obsolete lifecycle, duplicate, and scaffolded
  mutation routes as bodyless tombstones.
- WS02-04B2A2B2 removed generic payment/refund/event writes, raw provider
  metadata writes, and unowned provider/payment inputs from retained request
  bodies.
- WS02-04B2A2B3 retired generic policy/legal authoring and acceptance writes as
  bodyless tombstones.
- WS02-04B2A1 already introduced the portable ASGI request-body limiter and the
  two source-owned special classes.

## Retained Body-Bearing Inventory

The A2C baseline contains 83 retained body-bearing routes:

- 81 ordinary JSON request-body routes derived from FastAPI route metadata.
- 1 Platform Notice create special route.
- 1 signed Stripe webhook special route.

Bodyless routes, health/readiness, documentation/OpenAPI routes, WebSocket and
lifespan scopes, and bodyless 410 tombstones are excluded from ordinary JSON
limiting.

## Approved Request Classes

| Class | Limit | Selection |
|---|---:|---|
| Ordinary JSON | 65,536 bytes | FastAPI routes with retained request-body parameters, excluding approved special classes |
| Platform Notice create | 163,840 bytes | `POST /admin/platform-notices` |
| Signed Stripe webhook | 65,536 bytes | signed `POST /stripe/webhook` requests |

Precedence is signed Stripe webhook, Platform Notice create, ordinary JSON, then
no-body or excluded route.

## Evidence Basis

The largest deterministic ordinary route family measured during readiness was
Need-a-Sub at 29,042 compact JSON bytes using escaped non-BMP worst-case text.
That is 36,494 bytes below the approved 65,536-byte ordinary JSON limit.

Some retained legacy-shaped game and admin create/update schemas still contain
scalar or text fields without product-specific maxima. Those are not arbitrary
JSON, provider payload, or raw metadata fields. A2C intentionally treats the
ordinary 65,536-byte transport boundary as the source-owned API request-body
limit for those routes rather than inventing unrelated product field policy.

Future product work that intentionally needs larger ordinary JSON bodies must
revisit this register and add explicit evidence before changing the approved
limit.

## Enforcement Semantics

- Valid `Content-Length` above the applicable class limit may reject before
  downstream route work.
- `Content-Length` is advisory only.
- Actual received ASGI request bytes are authoritative.
- Missing, malformed, duplicate, and underdeclared lengths cannot bypass byte
  counting.
- Chunked and multi-message ASGI request bodies are counted cumulatively.
- Accepted request bytes are passed downstream unchanged and are not consumed
  twice.
- Oversized requests reject before request parsing completes, authentication
  lookups, database work, provider calls, notification creation, background
  work, or mutation.

## Content Encoding And Content Type

Limited request classes accept no `Content-Encoding` header or identity
encoding. Non-identity request encoding is rejected because the application does
not support request decompression.

A2C does not introduce a new global media-type policy. FastAPI and Starlette
keep their existing request parser behavior for supported, missing, malformed,
or unsupported content types below the body limit. Oversized bodies are rejected
by the byte boundary before parser work once the limit is exceeded.

## Stable App-Owned Errors

Oversized ordinary JSON requests reuse the existing stable app-owned 413
contract:

- HTTP 413.
- Stable machine-readable request-body-too-large code.
- Safe public message and top-level detail.
- Correlation ID in body and header.
- CORS and response-security headers where applicable.
- No submitted body, field value, provider data, token, identifier, or internal
  diagnostic leakage.

Unsupported non-identity request encoding uses the existing app-owned 415
unsupported-content-encoding contract for limited classes.

## Typed Configuration

The ordinary JSON limit is provider-independent typed backend configuration with
a default of 65,536 bytes. It is a positive integer, is not frontend exposed, is
not reused as a product field maximum, and remains adjustable later without
redesigning the middleware.

The three request classes keep separate settings so Platform Notice, signed
Stripe webhook, and ordinary JSON limits cannot drift into one shared value by
accident.

## Future-Route Safety

Ordinary request-body routes are derived from FastAPI route metadata. A future
retained JSON route with request-body parameters inherits the ordinary 64 KiB
class unless it is explicitly reviewed and configured as a special class.

Special classes remain explicit. Bodyless routes and tombstones do not receive
ordinary JSON limiting merely because a caller submits an unexpected body.

## Impact

- No frontend change.
- No database model or migration change.
- No provider configuration change.
- No CI workflow change.
- R2 object bytes still bypass FastAPI through direct upload URLs.

## API-M09 Status

A2C closes the source-owned ordinary JSON request-body gap for FastAPI request
bodies and preserves the previously approved Platform Notice and signed Stripe
webhook body classes.

API-M09 remains partial overall. B2B/B2C still own external ingress limits,
header and request-line behavior, URL limits, process-server behavior, provider
and edge precedence, final staging captures, configuration drift evidence, and
R2 direct-upload provider-side enforcement.
