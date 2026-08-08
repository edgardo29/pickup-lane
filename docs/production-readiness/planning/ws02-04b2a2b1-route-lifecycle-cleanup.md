# WS02-04B2A2B1 Route Lifecycle Cleanup

## Scope

WS02-04B2A2B1 removes obsolete body-bearing mutation surfaces before adding
broader request-size policy. The pass keeps active product workflows intact and
reduces the future WS02-04 A2C ordinary JSON blocker set by eliminating routes
that should not accept public request bodies at all.

This is the B1 portion of the WS02-04B2A2B split:

- B1: route lifecycle cleanup and internalization.
- B2: provider, payment, and raw metadata evidence.
- B3: policy, legal, and acceptance ownership.

The pass does not activate the ordinary JSON body limit, does not redesign
provider/payment metadata, and does not change policy/legal behavior.

## Bodyless Tombstones

The notification admin-write scaffolds now remain as stable HTTP 410 tombstones
without request-body parameters:

- `POST /notifications`
- `PATCH /notifications/{notification_id}`

The routes keep authentication and stable error handling while avoiding JSON
body parsing and route-owned notification mutation work.

## Generic CRUD Retirement And Internalization

The following public/admin scaffolds now return stable HTTP 410 responses and no
longer parse request bodies:

- `POST /bookings`
- `PATCH /bookings/{booking_id}`
- `POST /game-participants`
- `PATCH /game-participants/{participant_id}`
- `POST /waitlist-entries`
- `PATCH /waitlist-entries/{waitlist_entry_id}`
- `POST /host-publish-fees`
- `PATCH /host-publish-fees/{host_publish_fee_id}`
- `POST /venues`
- `PATCH /venues/{venue_id}`
- `POST /game-images`
- `PATCH /game-images/{game_image_id}`
- `POST /venue-approval-requests`
- `PATCH /venue-approval-requests/{venue_approval_request_id}`
- `POST /user-settings`
- `PATCH /user-settings/{user_id}`
- `POST /user-stats`
- `PATCH /user-stats/{user_id}`
- `POST /game-chats`
- `PATCH /game-chats/{game_chat_id}`
- `POST /admin/actions`
- `POST /admin/actions/{admin_action_id}/notes`
- `POST /game-status-history`
- `PATCH /game-status-history/{history_id}`
- `POST /booking-status-history`
- `PATCH /booking-status-history/{history_id}`
- `POST /participant-status-history`
- `PATCH /participant-status-history/{history_id}`
- `POST /booking-policy-acceptances`
- `PATCH /booking-policy-acceptances/{booking_policy_acceptance_id}`

The underlying models and service primitives remain available for supported
domain workflows and controlled test setup. Current tests that used these
routes as fixtures were migrated to service-owned or database-owned setup.

## Preserved Read And Active Workflow Behavior

The pass preserves current read and workflow endpoints, including:

- booking, roster, waitlist, host-fee, venue, image, approval, stats, chat,
  audit, status-history, and policy-acceptance reads
- `/user-settings/me`
- `/user-stats/me`
- scoped game chat and Need-a-Sub chat workflows
- official-game create/update, roster, cancellation, preview, and execute
  actions
- active admin venue-image upload, authorization, stored-object verification,
  moderation, and selected-image capacity behavior

No database models or migrations were changed.

## Audit, History, And Service Ownership

Audit, status-history, booking-policy acceptance, and notification mutation
state is now server-derived through product-owned services rather than public
generic write APIs. This preserves append-only audit principles and prevents a
client from fabricating lifecycle history directly.

## Need-A-Sub Removal

The canonical admin Need-a-Sub removal route remains:

- `POST /admin/need-a-sub/{post_id}/remove`

The legacy duplicate route now returns a stable HTTP 410 tombstone and does not
mutate:

- `PATCH /need-a-sub/posts/{sub_post_id}/remove`

The canonical workflow remains responsible for admin authorization, moderation,
review-case linkage, audit behavior, notification behavior, and its response
contract.

## Official-Game Player Removal

The active frontend caller now uses the existing POST preview/execute flow:

- `POST /admin/official-games/{game_id}/participants/{participant_id}/remove-preview`
- `POST /admin/official-games/{game_id}/participants/{participant_id}/remove`

The legacy DELETE-with-body route now returns a stable HTTP 410 tombstone:

- `DELETE /admin/official-games/{game_id}/participants/{participant_id}`

Payment, credit, audit, roster, waitlist, and notification behavior remains
owned by the existing official-game player-removal service.

## Official-Game Host Removal

Host removal now has a POST action endpoint:

- `POST /admin/official-games/{game_id}/host/remove`

The endpoint requires an internal reason and delegates to the existing
host-removal service. It preserves active-admin authorization, dynamic host
eligibility validation, audit recording, notification behavior, game state
effects, and the existing `AdminOfficialGameRead` response shape.

The legacy DELETE-with-body route now returns a stable HTTP 410 tombstone:

- `DELETE /admin/official-games/{game_id}/host`

The frontend host-removal caller now posts to the action endpoint and captures a
required internal reason before submission.

## A2C Blocker Reduction

This pass removes public request-body parsing from the 35 B1 body-bearing
surfaces. Remaining WS02-04 request-body work is outside B1 and includes the
ordinary JSON body limit activation, provider/payment metadata evidence, and
policy/legal ownership decisions.

## API-M09 Status

API-M09 remains partial. B1 reduces the body-bearing public surface but does not
complete the broader ordinary JSON, provider metadata, payment, policy/legal, or
infrastructure request-body control set.
