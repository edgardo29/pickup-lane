# WS02-04B2A1 Request Body Limits Decision

Status: APPROVED AND LOCKED

Approval date: August 13, 2026.

Approved by: Project owner.

Applies to: `WS02-04B2A1`

Related controls: `API-M09`, `GOV-006`, `FDN-04`

## Decision

1. `POST /admin/platform-notices` has an approved source-owned FastAPI
   request-body limit of `163,840` bytes.
2. Signed `POST /stripe/webhook` requests have an approved source-owned FastAPI
   request-body limit of `65,536` bytes.
3. These values govern application-source enforcement only.
4. They do not establish provider, edge, ingress, process-server,
   permanent-host, staging, Stripe-provider, or R2 object limits.
5. Ordinary JSON request-body limits remain separately owned by
   `WS02-04B2A2C`.

## Rationale

Protected resource / failure mode: oversized request bodies must not reach JSON
parsing, Stripe webhook construction, database mutation, or business mutation
for the approved source-owned classes before the application applies a bounded
failure.

Enforcing layers: FastAPI ASGI request-body middleware enforces these two
source-owned classes. Browser/client constraints, ingress, edge,
process-server, provider, permanent-host, staging, and R2 object-byte controls
remain outside this decision.

Accountable owner: API owner for portable FastAPI source enforcement, with
platform/deployment, payments, storage, reliability, privacy, and quality owner
participation where their later evidence is affected. All roles are held by the
Project owner on an interim basis until reassigned.

Provider/platform constraints: current repository evidence can prove FastAPI
behavior only. This decision does not claim Stripe provider payload limits,
Stripe dashboard configuration, hosting-provider behavior, process-server
limits, provider precedence, or deployed staging/runtime behavior.

Expected workload and abuse risk: Platform Notice create accepts bounded admin
text plus selected-user IDs; current valid selected-user request shape is well
below `163,840` bytes. Signed Stripe webhook handling must preserve raw bytes
for signature verification while rejecting oversized provider input before
application mutation.

Failure cost / recovery behavior: rejected requests receive stable app-owned
errors and can be retried with a smaller valid body. Provider/runtime rejection
behavior before FastAPI remains later evidence and may not share the application
error envelope.

Configurability: the values are backend typed settings exposed through
`PLATFORM_NOTICE_REQUEST_BODY_LIMIT_BYTES` and
`STRIPE_WEBHOOK_REQUEST_BODY_LIMIT_BYTES`; any numeric change requires a
superseding approved decision record.

Boundary-test expectations: trusted source tests must cover accepted and
rejected sizes, exact-limit and limit-plus-one bodies, actual bytes versus
`Content-Length`, missing/malformed/duplicate `Content-Length`, multi-message
ASGI delivery, content-encoding rejection for the approved classes, route-class
selection, signed Stripe raw-byte preservation, missing-signature separation,
and stable public errors.

Multi-instance relevance: the limits are stateless per-request source
enforcement and do not by themselves prove multi-instance ingress, provider, or
runtime precedence.

Telemetry / alert handoff: request-size rejection telemetry, route template,
outcome class, stable error code, provider errors, dashboards, and alerts remain
WS09/provider/runtime evidence.

Rollback / safe adjustment: source configuration can be adjusted only after a
superseding approved decision. A failed boundary test or workload finding must
return to owner review rather than silently rewriting the threshold.

Reassessment triggers: source route/schema changes, provider or platform
constraint changes, permanent-host selection, workload or abuse signals,
incident findings, boundary-test failures, telemetry findings, or any
superseding owner decision.

## Evidence Basis

Current Platform Notice source bounds `idempotency_key` to 160 characters,
`title` to 150 characters, `message` to 4,000 characters, and selected users to
500 IDs. A compact synthetic request at those current valid selected-user
bounds is 23,911 bytes; an impossible combined all-eligible-plus-selected shape
is 23,915 bytes. The approved 163,840-byte value remains comfortably above the
largest current valid source-owned Platform Notice create shape.

Current signed Stripe webhook source consumes a raw provider payload, verifies
it using the Stripe signature, and then processes supported payment-intent and
refund event classes. A representative safe synthetic supported payment-intent
event containing the current fields consumed by source is about 1 KiB. The
approved 65,536-byte value is a source-owned application boundary and is not a
claim about Stripe's maximum possible provider payload size.

## Change Rule

A later numeric change requires a superseding approved decision record. Do not
silently rewrite this decision.
