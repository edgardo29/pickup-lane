# WS02-04B1 Source-Owned Request, Pagination, Collection, and Upload Boundaries

Status: implemented for repository source and current tests.

## Why WS02-04B Was Split

WS02-04B covers request, pagination, collection, and upload boundaries. The
inspection found two different kinds of evidence:

- source-owned limits that can be implemented and tested in the repository
- provider, edge, transport, body/header, URL, timeout, rate, proxy, and staging
  behavior that requires runtime or external-provider evidence

WS02-04B1 is limited to the source-owned values approved by the owner. It does
not change global transport/body/header limits, infrastructure worker behavior,
provider limits, timeout budgets, rate controls, proxy identity, migrations, or
models.

## Platform Notice Decision

The controlling selected-user audience limit is 500 unique selected users.

This supersedes the older 200-user Platform Notice planning value. The old value
was a conservative product safety rail, but WS02-04B1 records the approved
source-owned value as 500.

The implementation keeps these concepts separate:

- selected-audience maximum: 500 unique selected users for one selected
  Platform Notice publish
- recipient-list pagination: default 50 recipients per page, maximum 100
  recipients per page
- campaign history pagination: maximum 30 notices per page
- worker, delivery, fanout, or provider batch size: not used by Platform
  Notices and not changed by this pass

Selected-user publish still normalizes duplicate IDs before applying the unique
limit. More than 500 unique selected users is rejected before delivery rows,
notifications, provider work, or irreversible mutation. Missing or ineligible
selected users still reject the request without persisting the notice.

Platform Notices remain sparse:

- global notices create no recipient rows
- selected notices create one membership row per unique selected user
- neither path creates ordinary notification rows

## Public Pagination

The approved public card pagination values are:

| Surface | Default | Maximum | Cursor maximum |
|---|---:|---:|---:|
| Browse Games | 40 | 100 | 2000 characters |
| My Games | 40 | 100 | 2000 characters |
| My Need a Sub | 40 | 100 | 2000 characters |
| Need a Sub cards | 40 | 100 | 2000 characters |

Values above the maximum remain clamped where existing service behavior clamps.
Values below the minimum remain rejected by route validation. Cursor parsing and
query-context checks remain deterministic and database queries remain bounded to
one page plus one extra row for `has_more` detection.

## Need A Sub Limits

Approved source-owned Need a Sub values:

- maximum 6 position rows
- maximum 11 total requested substitutes
- maximum 25 waitlisted requests per post

The six-row schema limit is preserved. Current soccer position vocabulary and
compatibility rules can reject duplicate or incompatible rows before all six
rows are meaningful in the API flow; that validation remains intentional.

The waitlist cap is checked before creating the next waitlisted request.

## Saved Cards

The approved saved-card limit is 5 active cards per user.

Detached and inactive local card rows do not count toward the active-card cap.
The sixth active card is rejected before a new local payment-method row is
persisted. Provider runtime behavior and payment-provider evidence remain
outside this pass.

## Chat Limits

Approved chat values:

| Surface | Message body | Page size | History cap |
|---|---:|---:|---:|
| Game chat | 300 characters | 50 messages | 200 visible text messages |
| Need a Sub chat | 300 characters | 50 messages | 200 visible text messages |

Existing message-rate values are preserved but not approved by WS02-04B1.
Rate-control evidence remains outside this pass.

## Platform Notice Field And List Limits

Approved source-owned Platform Notice values:

- title: 150 characters
- message: 4000 characters
- selected-user search: 200 characters
- campaign history search: 200 characters and at least 3 meaningful characters
- cancellation reason: 1000 characters
- campaign history page size: maximum 30
- recipient page size: default 50, maximum 100

The selected-audience cap is not reused for recipient pagination, history
pagination, lookup pagination, worker batching, or delivery concurrency.

## Venue Image Upload Boundaries

Approved source-owned venue image values:

- maximum 3 selected venue photos in the current official-game create flow
- maximum image size 8 MiB
- allowed types: JPEG, PNG, WebP

The frontend create-official-game flow enforces selected-photo count, file type,
and file size before upload. The backend validates declared file type and size
before issuing upload authorization, then verifies stored object size and type
before marking an image complete in the database.

Cloudflare R2 runtime evidence, provider object-retention behavior, CDN/edge
limits, and signed-URL behavior remain outside this pass.

## Boundaries Preserved But Not Newly Approved

Some existing admin/internal values remain unchanged because they were not part
of the WS02-04B1 owner decision. Examples include admin-review list sizes,
admin-user lookup sizes, moderation queues, inbox pagination, rate-control
thresholds, provider SDK settings, infrastructure worker behavior, and
deployment provider limits.

Preserving those values in source does not approve them for production. They
require later evidence or owner decisions where applicable.

## Enforcement Ownership

WS02-04B1 keeps enforcement in the source component that owns the behavior:

- request schemas own field shape, field length, and route-level query bounds
- services own normalized collection limits, deduplication, eligibility checks,
  and pre-mutation rejection
- frontend form/data modules own local counters, help text, and preflight
  selection/upload checks
- current non-legacy backend tests own source-level enforcement evidence
- production-readiness docs own the approved value record and remaining gaps

No model or migration changes were required.

## Current Test Evidence

Current non-legacy backend tests cover:

- Platform Notice 500 selected-user accept path
- Platform Notice 501 unique selected-user rejection before mutation
- Platform Notice selected-user deduplication before limit enforcement
- Platform Notice ineligible selected-user rejection
- Platform Notice title, message, search, cancellation, recipient, and history
  limits
- Need a Sub public card default/max/min/cursor pagination
- Need a Sub position-row schema maximum and duplicate-row rejection
- Need a Sub 11-substitute accept path and 12-substitute rejection
- Need a Sub 25-waitlist cap and 26th waitlisted request rejection
- saved-card fifth active-card accept path and sixth active-card rejection
- game chat and Need a Sub chat message body, page-size, and history caps
- venue image declared type/size validation before upload authorization
- venue image stored object size/type mismatch rejection before completion
- Browse Games default/min/max/cursor pagination
- My Games and My Need a Sub default/min/max/cursor pagination

Frontend unit tests cover the Platform Notice selected-user cap and UI add
blocking behavior at 500 users.

## API-M09 Status

WS02-04B1 advances API-M09 only for source-owned request, pagination,
collection, and upload boundaries listed here. API-M09 is not complete.

Remaining API-M09 gaps include:

- provider or hosting-edge request/body/header limits
- transport-layer limits and upstream proxy behavior
- staging/runtime evidence that external limits and application limits align
- provider upload behavior beyond source-owned declared/stored checks
- rate-control and abuse-control thresholds
- timeout, cancellation, retry, and backpressure behavior

## Explicit WS02-04B2 And WS02-04C Deferrals

The following remain outside WS02-04B1:

- WS02-04B2 runtime/provider evidence for request limits, body/header/URL
  limits, edge/provider precedence, upload-provider behavior, and staging proof
- WS02-04C timeout, cancellation, retry, backpressure, rate, worker, and
  provider-runtime behavior
- migration, model, and infrastructure changes
- global transport middleware changes
- provider dashboard or production-environment changes
