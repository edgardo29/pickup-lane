# WS02-04B2A1 Portable Request Boundaries

Status: implemented for repository source and current tests.

## Why WS02-04B2 Was Split

WS02-04B2 covers request body, header, URL, ingress, process-server, provider,
and staging precedence behavior. The available evidence supports a portable
source-only subset now, but it does not prove the permanent public edge or
provider topology.

The approved split is:

- WS02-04B2A1: portable application request-body enforcement for classes with
  approved evidence.
- WS02-04B2A2: ordinary JSON schema bounds and general ordinary-JSON body-limit
  approval.
- WS02-04B2B: permanent hosting, ingress, process-server, and provider
  alignment.
- WS02-04B2C: permanent staging and precedence verification.

Render, Vercel, and Neon are treated as temporary demo infrastructure for this
pass. Permanent hosting-provider selection is not required for B2A1 because the
implementation is owned by FastAPI source and does not depend on provider edge
behavior. Permanent-host selection triggers B2B and B2C verification.

The permanent application stack remains React/Vite, FastAPI, PostgreSQL,
SQLAlchemy, and Alembic.

## Portable ASGI Design

The application owns a pure ASGI request-body limiter inside the FastAPI
middleware stack. It selects only the approved route classes by request method
and normalized path before reading the request body.

The limiter:

- counts actual bytes received from ASGI `http.request` messages
- treats `Content-Length` as advisory only
- supports requests without `Content-Length`
- supports chunked bodies that reach the ASGI application
- stops passing body data downstream once the approved limit is exceeded
- does not read, parse, reconstruct, or alter accepted request bytes
- does not parse JSON
- does not touch database or provider clients
- does not affect WebSocket or lifespan scopes
- does not add timeout, retry, rate, cancellation, response-streaming, or
  process-server behavior

## Approved Limits

| Request class | Approved application limit | Evidence basis | Status |
|---|---:|---|---|
| Platform Notice create route class | 160 KiB / 163,840 bytes | Maximum valid selected-create synthetic request measured at 69,555 bytes. Conservative impossible combined shape measured at 81,580 bytes. The approved value provides at least 2x margin over the conservative shape. | Approved for B2A1 source enforcement only. |
| Signed Stripe webhook requests | 64 KiB / 65,536 bytes | Largest relevant sanitized synthetic fixture measured at 31,052 bytes. The approved value provides approximately 2.1x margin. | Approved for B2A1 source enforcement only and configurable through typed settings. |

The Stripe value is not a Stripe provider hard-limit claim.

## Content-Length And Actual Bytes

For the approved request classes only, one valid non-negative `Content-Length`
value above the applicable limit can be rejected before the body is read. A
declared value within the limit is not trusted for acceptance; actual bytes are
still counted.

Missing length metadata is allowed and enforced by actual-byte counting. Chunked
bodies that reach ASGI are enforced by actual-byte counting. Malformed,
duplicate, or conflicting length metadata is not used for early approval.
Transport or edge rejections that happen before FastAPI are outside this source
contract and may not use the application error envelope.

## Platform Notice Behavior

B2A1 applies the 160 KiB application body limit to the Platform Notice create
route class. This protects selected-audience creation while avoiding JSON
parsing inside middleware.

The limit does not apply to recipient pagination, campaign-history pagination,
notification lookup, delivery worker batching, direct R2 object uploads, or
unrelated admin routes.

The existing 500-user selected-audience behavior remains a source-owned service
limit from WS02-04B1.

## Stripe Webhook Behavior

Signed Stripe webhook requests enforce the 64 KiB application body limit before
Stripe verification and before database or business mutation.

Accepted webhook bodies preserve exact raw bytes and body-read-once route
behavior. Duplicate-event, idempotency, and ignored-event route behavior remain
compatible below the limit.

A webhook request missing the required Stripe signature header still reaches the
route and is rejected there before the body is read. The limiter does not
trigger declared-length rejection or buffer the request body for missing-signature
webhook requests.

## Compressed Requests

No request decompression support exists.

For the approved Platform Notice and signed Stripe webhook classes, non-identity
`Content-Encoding` is rejected by the application before body processing. The
application does not decompress the request and does not count decoded bytes.

This pass does not create a global `Content-Type` or global 415 policy for
unrelated routes.

## Stable App-Owned Errors

Application-owned oversized body rejection uses HTTP 413 with a stable public
error code, safe message, top-level `detail`, correlation ID in the body and
header, CORS behavior where applicable, response-security headers, and no
submitted-body, signature, header, provider, or internal diagnostic leakage.

Unsupported content encoding for approved classes uses a stable app-owned
unsupported-content-encoding error. Edge or process-server rejection may not
use this envelope.

## Exclusions And Remaining Work

Ordinary JSON body limits remain deferred to WS02-04B2A2 because many older,
admin, internal, payment, policy, metadata, and provider-related schemas still
contain unbounded fields. B2A2 must approve schema bounds before any ordinary
JSON body limit can be claimed.

Form, multipart, and FastAPI file-upload limits are not implemented because the
current repository has no form, multipart, or file-upload request consumers.

R2 object bytes bypass FastAPI through direct signed upload URLs. B2A1 does not
enforce object-byte limits at the API request-body layer.

Headers, URLs, ingress, process-server limits, permanent hosting, provider
alignment, and staging precedence remain WS02-04B2B and WS02-04B2C work.

## API-M09 Status

WS02-04B2A1 advances API-M09 for two source-owned request-body classes only:
Platform Notice create-route requests and signed Stripe webhook requests.

API-M09 remains partial. Remaining gaps include ordinary JSON body limits,
headers, URLs, ingress and process-server behavior, provider/edge precedence,
permanent staging verification, form/multipart consumers if introduced, R2
object-byte behavior, rate, timeout, retry, cancellation, and runtime evidence.
