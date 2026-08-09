# WS02-05B1 Request Ownership And Mass-Assignment Cleanup

Status: implemented as source-owned request-contract cleanup.

Branch: `pr/WS02-05B1`

Baseline: `f2a313aab194bd982aca55344ea5b7e578be2e82`

## Scope Split

WS02-05B was split because request ownership and response minimization carry
different compatibility risk.

WS02-05B1 owns:

- request ownership
- mass-assignment and over-posting cleanup
- authority-specific request schemas
- backend-only compatibility unless a real caller requires adjustment

WS02-05B2 owns:

- response minimization
- public, authenticated, host, admin, internal, and provider response
  separation
- frontend response compatibility
- payment-event raw-payload removal from HTTP responses

## Request Authority Findings

The active frontend does not use generic `POST /games` for community game
publishing and does not use generic `PATCH /games/{game_id}` for host editing.
Active callers use:

- `POST /community-games/publish`
- `PATCH /games/{game_id}/host-edit`
- `PUT /community-game-details/games/{game_id}/host-edit`
- `POST /admin/official-games`
- `PATCH /admin/official-games/{game_id}`
- explicit admin official-game host, roster, cancellation, and image workflows
- explicit admin community-game enforcement workflows

The generic game create and update routes are admin-only. Their prior
`GameCreate` and `GameUpdate` schemas were table-shaped enough to advertise and
accept fields that belong to workflow, identity, lifecycle, location snapshot,
payment/provider mode, and server-derived state.

## Implemented Boundaries

`GameCreate` now accepts only caller-owned generic admin create fields:

- game type
- title and description
- venue reference
- community host reference when creating a community game
- schedule and timezone
- format, group, skill, environment, capacity, and price
- guest and waitlist switches
- chat switch
- host-visible notes and parking notes
- custom rules text

The service now derives or validates the rest:

- creator identity from the authenticated admin
- venue snapshots from the stored venue row
- publish, game, visibility, and joining state
- payment collection mode
- policy mode
- currency and sport
- local start date
- official and community invariant fields
- lifecycle timestamps and cancellation/completion fields
- host guest maximum

`GameUpdate` now accepts only generic admin-editable game attributes:

- title and description
- schedule and timezone
- format, group, skill, environment, capacity, and price
- guest and waitlist switches
- chat switch
- custom rules text
- game notes and parking notes

`GameUpdate` no longer accepts identity, lifecycle/status, location snapshot,
payment/provider, policy, currency, sport, host guest maximum, or audit-style
fields. Existing dedicated admin official-game and admin community-game routes
remain the authority for their specialized actions.

## Mass-Assignment Result

Generic game creation now passes a service-built dictionary into the ORM
constructor instead of expanding a request-shaped dictionary.

Generic game update still applies an update dictionary, but that dictionary is
now produced from a narrowed request schema and augmented only with
service-derived lifecycle/local-date/official-invariant fields. Removed
server-owned request fields are rejected by request validation before service
or database mutation work.

## Compatibility

No active frontend caller sends the removed generic game fields.

Non-legacy test helpers that used generic `POST /games` for fixture setup now
send only the narrowed create contract through HTTP. When tests need seeded
historical, hidden, cancelled, or otherwise non-current fixture state, helpers
apply those setup details directly to the test database after creation. This
keeps test setup flexible without treating unsafe HTTP over-posting as a
current API contract.

No frontend files were changed.

## Fields Removed From Generic Game Requests

Server-derived or workflow-owned fields removed from generic game request
schemas include:

- `payment_collection_type`
- `publish_status`
- `game_status`
- `public_visibility_status`
- `join_enforcement_status`
- `starts_on_local`
- `sport_type`
- `currency`
- `minimum_age`
- `policy_mode`
- `host_guest_max`

Identity and audit-style fields removed include:

- `created_by_user_id`
- `cancelled_by_user_id`
- `completed_by_user_id`

Snapshot fields removed include:

- `venue_name_snapshot`
- `address_snapshot`
- `city_snapshot`
- `state_snapshot`
- `neighborhood_snapshot`

Lifecycle fields removed include:

- `published_at`
- `cancelled_at`
- `cancellation_source`
- `cancel_reason`
- `completed_at`

The dormant custom cancellation text field was also removed from the generic
game request contracts. Existing stored data and responses are unchanged.

## Other Request Surfaces

`UserUpdate` remains narrow and rejects ordinary-user over-posting of role,
provider identity, verification state, deletion state, administrative flags,
and system timestamps.

Generic payment, refund, and payment-event mutation routes remain retired
where applicable. The retained payment-event admin repair request remains
limited to processing linkage/result fields and does not accept raw provider
payload updates.

Checkout, saved-card, admin-money, admin official-game, admin community-game,
policy/legal, chat, and request-body/media contracts remain governed by the
source-owned WS02-04 and WS02-05A work already completed. No additional request
schema changes were needed in WS02-05B1.

## OpenAPI

OpenAPI now reflects the narrowed `GameCreate` and `GameUpdate` request
schemas. Removed privileged fields no longer appear as ordinary caller-writable
input for `POST /games` or `PATCH /games/{game_id}`.

Response schemas are intentionally unchanged.

## WS02-05B2 Handoff

WS02-05B2 retains the response findings and owner decisions:

- public game detail response
- authenticated, host, and admin game response separation
- participant and public user identity responses
- self-user response
- admin-user response
- ordinary payment and refund summaries
- admin financial response
- `PaymentEventRead.raw_payload` removal from HTTP API
- public versus admin image responses
- participant versus moderation chat responses
- admin review and support evidence
- policy and legal read minimization
- frontend migration requirements
- present-null versus absent-field compatibility concerns

## Impact

- No database model change.
- No migration.
- No provider configuration change.
- No deployment or CI change.
- No permanent-host change.
- No response minimization.

## API-M14 Status

API-M14 advances for request ownership and mass-assignment safety on the
generic game create/update surface. API-M14 remains partial until WS02-05B2
completes response minimization and audience-specific read contracts.
