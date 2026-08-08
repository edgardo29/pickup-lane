# WS02-04B2A2B2 Opaque Provider And Payment Inputs

Pass: WS02-04B2A2B2

Scope: retained opaque/provider/payment request ownership, generic payment
mutation retirement, and source-derived game-credit issue boundaries.

## Split

- B1 retired obsolete body-bearing lifecycle and generic CRUD scaffolds.
- B2 owns opaque provider identifiers, inbox seen tokens, checkout return URLs,
  generic payment/refund/event mutation ownership, raw provider metadata
  ownership, and game-credit source-derived issue/reverse boundaries.
- B3 remains responsible for policy, legal, and acceptance ownership decisions.
- A2C remains responsible for any future ordinary JSON body-size limit.

## SetupIntent Ownership

`POST /user-payment-methods/sync` still accepts `setup_intent_id` because the
identifier comes from a completed frontend Stripe setup flow. The request treats
it as an opaque provider-validated identifier:

- trim surrounding whitespace
- require non-empty input
- cap at 255 characters
- do not infer object type from provider prefixes
- validate the SetupIntent, customer ownership, status, and PaymentMethod
  legitimacy through the existing provider-backed service workflow

Invalid static input is rejected before provider retrieval.

## Inbox Seen Token Ownership

`PUT /inbox/app-updates/global-seen` treats `seen_token` as an opaque
server-issued token:

- trim surrounding whitespace
- require non-empty input
- cap at 512 characters
- do not validate internal token structure in the request schema
- preserve signed payload, kind, version, user, and sequence verification in the
  inbox service

The 512-character cap provides version-aware headroom over the current signed
global-seen token shape while rejecting oversized input before token
verification or database mutation.

## Checkout Return URL Ownership

`POST /checkout/games/{game_id}/payment-intent` retains optional `return_url`
support for the current frontend checkout flow, but the value must resolve to
the configured Pickup Lane application origin and the current game checkout
return path:

- origin must match configured application/CORS origins
- path must be `/games/{game_id}/checkout`
- credentials, fragments, and query strings are rejected
- arbitrary external origins are rejected
- no Render, Vercel, or temporary hostnames are hard-coded

The URL is validated before game lookup, database mutation, or provider work.

## Generic Payment And Refund Mutations

Generic payment and refund create/update routes are now retired bodyless
tombstones:

- `POST /payments`
- `PATCH /payments/{payment_id}`
- `POST /refunds`
- `PATCH /refunds/{refund_id}`

Read routes remain available. Supported writes stay owned by checkout, signed
webhook processing, refund/retry/reconcile workflows, official-game workflows,
admin-money services, and reconciliation services.

## Payment Event Ownership

Signed Stripe webhook processing remains authoritative for payment-event
creation. Generic payment-event creation is retired:

- `POST /payment-events`

The retained repair route only accepts proven repair/linking fields:

- `payment_id`
- `processing_status`
- `processing_error` capped at 1,000 characters

Provider identity, event type, raw payload, and provider-owned event data are
not request-writable through the retained repair surface.

## Raw Provider Metadata Ownership

Raw provider payloads and provider metadata remain owned by provider webhook/API
inputs and server-derived projections. Ordinary or generic client request
bodies cannot supply arbitrary raw provider payloads, provider event identity,
provider statuses, provider failure objects, provider timestamps, or receipt
metadata through the retired generic surfaces.

## Game Credit Ownership

The B2 owner decision removes arbitrary source-less monetary credit issuance
from the generic admin game-credit issue route.

`POST /admin/game-credits/issue` now requires an authoritative eligible source
with server-derived value:

- source-linked issuance remains supported
- a source booking and/or source payment is required
- `source_game_id` alone can prove official in-app eligibility but does not
  provide a monetary ceiling
- the issued amount must not exceed the remaining source-derived eligible amount
- existing non-reversed credits for the same credited user and source reduce the
  remaining eligible amount
- no universal monetary ceiling is invented
- source-less discretionary reasons such as generic support/admin adjustments
  are intentionally unsupported through this route in B2

No current frontend caller depended on source-less issuance at inspection time.
A future discretionary support-credit capability, if needed, requires a separate
product decision with explicit limits, audit semantics, and authorization.

Game-credit reversal remains bounded by the existing credit row and reverses
only the current unused/eligible available amount. It does not accept a
client-supplied reversal amount.

## Error And Ordering

Static request-shape checks run before provider lookup, source eligibility,
database mutation, audit writes, notification/background work, or provider work
where applicable. Service-owned provider, ownership, source, and dynamic
eligibility checks preserve stable public error behavior without echoing tokens,
URLs, provider identifiers, raw provider payloads, or internal details.

## A2C Compatibility

The retained B2 body-bearing requests are now deterministic and bounded enough
for future A2C ordinary JSON policy review:

- payment-method sync
- inbox global-seen
- checkout payment-intent request
- retained payment-event repair
- game-credit issue/reverse

This pass does not activate the ordinary JSON body limit.

## Migration Impact

No database models or migrations are changed. Storage can remain wider than the
active B2 request policy.

## Remaining Work

API-M09 remains partial. Later WS02 work still owns the broader ordinary JSON
body limit, policy/legal ownership, provider infrastructure, timeout/retry/rate
behavior, and any separately approved discretionary support-credit capability.
