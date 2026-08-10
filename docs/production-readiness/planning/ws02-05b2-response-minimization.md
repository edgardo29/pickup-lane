# WS02-05B2 Response Minimization And Audience-Specific API Contracts

Status: implemented as source-owned response-contract cleanup.

Branch: `pr/WS02-05B2`

Baseline: `6825e8442e15969f98e43146087c5f7680ce2d35`

## Scope

WS02-05B2 owns the API-M14 response-minimization portion of WS02-05B.

This pass separates broad shared read models into audience-appropriate
contracts for:

- signed-out and public callers
- authenticated ordinary users
- game and Need-a-Sub participants
- hosts and owners
- admins
- internal and provider-owned evidence

It does not change persisted data, migrations, provider configuration,
deployment configuration, CI, permanent hosting, API versioning, request body
limits, cache policy, or WS02-05A error/media behavior.

## Audience Model

Public and signed-out responses expose only product display fields required for
discovery, detail rendering, legal/policy display, and safe image rendering.

Authenticated self responses expose account and profile fields that belong to
the signed-in user experience.

Participant responses expose conversation and game participation state needed by
the current product UI, without moderation or administrative workflow state.

Host responses may include host-owned game context that is not useful to public
callers. That context remains masked from signed-out and non-host callers.

Admin responses retain operational fields needed by admin user, financial,
image, moderation, and review workflows.

Provider and internal evidence remains server-owned. Raw provider event payloads
are not returned through HTTP response contracts.

## Response Contracts Changed

`GameDetailRead` is now used for public game detail and generic game list
responses. It omits creator, cancellation actor, completion, policy, publish,
sport, deletion, and audit timestamp fields that are not needed for public game
rendering.

`SelfUserRead` is now used by self/auth/account routes. It retains legitimate
self-account fields, including `email_verified_at`, and omits provider identity
and audit timestamps.

`AdminUserRead` is now used by admin user routes where richer operational state
remains required.

`PaymentSummaryRead` and `RefundSummaryRead` are now used by ordinary payment
and refund read routes. They retain product-visible amount, status, and
association fields while omitting provider bookkeeping, idempotency, failure
diagnostics, reconciliation, and audit details.

`AdminPaymentRead` and `AdminRefundRead` preserve admin financial fields needed
by active admin money workflows.

`PaymentEventRead` no longer exposes raw provider payload data through HTTP.
Stored provider evidence remains internal.

`VenueImagePublicRead` and `GameImagePublicRead` expose public display image
fields only. Admin image routes retain `VenueImageAdminRead` and
`GameImageAdminRead` for operational metadata.

`ChatMessageParticipantRead` and `SubPostChatMessageParticipantRead` are used
for participant chat responses. Admin moderation responses keep their richer
moderation contracts.

`PolicyDocumentPublicRead` keeps public legal display fields and record
identity while omitting management and lifecycle fields that are not required to
render policy content.

## Fields Removed By Category

Identity and ownership fields removed from public responses include creator,
actor, provider, and administrative user identifiers where the caller has no
authority-specific need.

Provider and payment internals removed from ordinary responses include provider
identifiers, idempotency state, reconciliation fields, failure diagnostics, and
arbitrary provider payloads.

Workflow and moderation state removed from public or participant responses
includes review lifecycle state, removal/restoration actor fields, source
labels, and admin-only moderation evidence.

Audit and lifecycle metadata removed from public responses includes generic
created, updated, deleted, published, completed, retired, and management status
fields where those fields are not part of the product display contract.

Image storage metadata removed from public responses includes object keys,
storage/provider fields, upload internals, and upload lifecycle metadata.

## Frontend Caller Migration

Frontend game image consumers no longer sort public images by internal creation
timestamps. They use public display fields only:

- primary flag
- sort order
- stable image identity

The same selector supports old and new backend image payloads because it ignores
extra storage and timestamp fields when present.

No frontend caller now depends on public image `created_at` for display order.

## Compatibility Strategy

Old frontend plus new backend remains compatible for active game detail,
checkout, profile, policy, image display, and admin money flows because active
product fields were retained or masked with stable null/default semantics where
needed.

New frontend plus old backend remains compatible for image display because the
new selector consumes only fields already present in public image payloads and
ignores additional old-backend metadata.

New frontend plus new backend uses the minimized audience-specific contracts.

No API versioning, version headers, permanent host changes, or calendar-based
deprecation windows were introduced.

## Temporary Compatibility Fields

`GameDetailRead.host_user_id` remains present but is null for signed-out and
non-host callers. It is still available to hosts and admins. Retirement trigger:
the frontend no longer needs host identity from the game detail payload and has
a dedicated viewer-capability signal.

`GameDetailRead.host_guest_max` remains present with a public default and the
real host/admin value for authorized callers. Retirement trigger: host guest
management uses a dedicated host-owned response.

Participant identity responses retain party-grouping identifiers required by
current game-detail and checkout rendering. Retirement trigger: the backend
provides explicit current-viewer and party-grouping projection fields.

`SelfUserRead.profile_photo_url` remains in self responses as a dormant account
display compatibility field. It is not an ordinary user-editable request field.

`PolicyDocumentPublicRead.id` remains in public policy reads so list/detail
records keep stable identity.

## PaymentEvent Raw-Payload Decision

Raw provider event payloads are no longer exposed through `PaymentEventRead`.
Provider evidence may remain stored internally for reconciliation and audit, but
HTTP callers receive only typed operational event fields.

## Image Boundary

Public image routes now return display-only image contracts.

Admin image routes and upload completion keep operational metadata required for
active admin and direct-upload workflows. Upload-ticket responses remain scoped
to upload authorization and completion rather than general public image reads.

## Chat And Moderation Boundary

Participant chat routes now return participant-safe message fields needed for
conversation display.

Admin moderation contracts remain richer because moderators need review,
visibility, removal, restoration, evidence, and action state. WS02-05B2 does
not redesign the moderation system.

## Policy And Legal Boundary

Policy and legal read APIs remain active. Public policy reads are minimized to
display and identity fields. Management fields such as active flags, retirement
state, and source-owned timestamps are not part of the public read contract.

## Raw And Open Structures

WS02-05B2 removes the high-priority raw provider payload exposure from payment
event HTTP responses.

Existing admin review, moderation, notification, and support structures that
carry typed or product-owned operational evidence remain in place where they are
active admin workflows. Broad redesign of those systems remains outside this
pass.

## API-M14 Outcome

API-M14 advances from partial to source-owned for the response-minimization
surfaces addressed by WS02-05B2:

- public game detail
- self and admin user reads
- ordinary and admin financial reads
- payment-event HTTP responses
- public and admin image reads
- participant and admin chat reads
- policy/legal public reads

The backend response contract, not frontend hiding, is now the authoritative
filter for these surfaces.

## API-M19 Remaining Items

Permanent external HTTP-chain evidence remains outside WS02-05B2, including:

- permanent hosting and ingress behavior
- edge or proxy generated responses
- final TLS and HSTS ownership
- CDN and shared-cache behavior
- permanent staged response captures
- API versioning or long-term deprecation policy, if a future public API needs
  one

## Impact

- No database model change.
- No migration.
- No provider configuration change.
- No deployment or CI change.
- No permanent-host change.
- No WS02-05A media, error, cache, docs, tombstone, or pagination behavior
  change.
