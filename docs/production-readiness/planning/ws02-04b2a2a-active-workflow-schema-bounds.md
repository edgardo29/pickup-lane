# WS02-04B2A2A Active Workflow Schema Bounds

Pass: WS02-04B2A2A

Scope: active ordinary and admin workflow request-schema bounds, plus the narrow
service-owned checks needed when the approved maximum depends on a current
server-side target.

## Split

- A2A covers active request schemas for account deletion, profile/contact
  updates, active settings, community game publish/edit, game join/checkout,
  booking guest changes, active chat, Need-a-Sub pricing, admin official-game
  actions, admin review closure, admin money actions, support-flag resolution,
  and venue image metadata.
- A2B remains responsible for legacy, internal, scaffolded, raw provider/audit,
  legal/policy, generic CRUD, uncertain duplicate routes, opaque provider IDs,
  return URLs, inbox tokens, and broader request-shape decisions.
- A2C remains responsible for activating the general ordinary JSON request-body
  limit.

## Included Active Families

- Account deletion, profile/contact updates, and active user settings.
- Community game publish/edit, game create/edit, game join/leave/cancel,
  checkout, booking guest add/remove, and active game chat.
- Need-a-Sub lifecycle requests and Need-a-Sub chat.
- Payment-method setup/sync request surfaces only where A2A has an approved
  source-owned request shape; provider-owned identifiers remain outside A2A.
- Platform Notice cancellation.
- Admin official-game workflows, active moderation, review cases, admin users,
  admin money actions, support-flag resolution, and venue-image request metadata.

## A2B Exclusion Registry

The accepted A2A inspection kept 49 body-bearing routes, covering 48 request
schema shapes, outside this pass. A2B owns these categories:

- Legacy, internal, generic CRUD, and scaffolded route families.
- Removed notification writes.
- Policy/legal scaffolding and historical status records.
- Provider/audit raw-record routes.
- Generic payment, refund, venue, waitlist, user-stat, and settings scaffolds.
- Unrestricted raw metadata and uncertain or duplicate Need-a-Sub routes.
- Checkout return-URL policy, provider-owned payment identifiers, and inbox
  seen-token policy.

## Approved Static Request Limits

| Area | Approved request rule | Enforcement |
|---|---|---|
| Profile update | email 255, phone 30, first/last name 100, home city/state 120 | `UserUpdate` |
| Profile update | `profile_photo_url` and `email_verified_at` are not client-writable | `UserUpdate` with forbidden extras |
| Account deletion | confirmation must be `DELETE`, trimmed and case-insensitive | `AuthDeleteAccountRequest` |
| Game capacity | `total_spots` 6 through 99 | active game create/update schemas |
| Player guests | join/checkout `guest_count` 0 through 2 | player join and checkout schemas |
| Booking guest add | `guest_count` 1 through 2 | booking guest-add schema |
| Guest removal | `remove_count` at least 1 | guest-remove schema |
| Player guest policy | `max_guests_per_booking` 0 through 2 | active game create/update schemas |
| Host guest policy | exposed `host_guest_max` at least 0 only | active game create/update schemas |
| Pricing | player and Need-a-Sub supplied cents 0 through 99,900 | active game and sub-post schemas |
| Community payment methods | at most 2 typed items, no extra keys, values trimmed and 255 chars | community payment schemas |
| Community payment instructions | absent or `None` only | community payment schemas |
| Admin operational text | 1,000 chars unless a stricter current rule already exists | active admin action schemas |
| Chat messages | 300 chars | active game and Need-a-Sub chat schemas |
| Venue image metadata | existing roles/statuses; `sort_order` 0 through 2 | venue image request schemas |

## Dynamic Service-Owned Checks

- Admin money amounts must be non-negative in the request schema and must not
  exceed the eligible server-calculated target amount.
- Admin money actions with no eligible target may not introduce a positive
  client-supplied amount.
- Venue image selected-photo capacity is capped at three selected images,
  counting active and pending-upload images.
- Format-specific game minimums, capacity availability, host guest behavior,
  booking ownership, participant eligibility, payment totals, R2 MIME/type/byte
  configuration, and provider behavior remain service-owned.

## Explicit Deferrals

- No URL policy or maximum is invented for checkout `return_url`.
- No provider-ID pattern or maximum is invented for payment-method
  `setup_intent_id`.
- No token-shape policy is invented for inbox `seen_token`.
- No general ordinary JSON body limit is activated.
- No database migration is introduced. Storage capacity can remain wider than
  active product request policy.
- No file-size, MIME, pixel, decompression, processing, or provider upload
  policy is invented beyond existing R2 service configuration.

## Compatibility

Invalid A2A request values now fail during request parsing where the rule is
static, or during the existing service workflow where the approved maximum
requires server-side target state. Database columns, response fields, historical
records, and provider-owned values are preserved.

API-M09 is only partially addressed by this pass. Remaining body-size, URL,
header, provider identifier, raw metadata, and deferred route-family bounds stay
with A2B, A2C, B2B, B2C, or later WS02 work.
