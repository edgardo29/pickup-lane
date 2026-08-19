# WS02-05B2 - Response Minimization And Audience-Specific API Contracts

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS02-05B2` |
| Track | `WS02` |
| Type | API response-minimization / audience-specific contract evidence reconstruction |
| Primary controls | `API-M14`, `IAM-014` |
| Supporting controls | `API-M13`, `API-M18`, `PAY-004`, `PAY-005`, `PAY-006`, `PAY-008`, `PAY-009`, `STO-006`, `STO-009`, `GOV-006`, `WS02-05A`, `WS02-05B1`, `WS03-01` |
| Gate A accepted baseline | `29906d6c6be44bd81d31b6988345fab10af22908` |
| Historical PR provenance | PR `#125`, merge `59deb5bec92dfb24170bbe63269b6429cb4e325c`, head `c027fd3cb7ec916228cbf6133807db72bd354e79`, baseline parent `6825e8442e15969f98e43146087c5f7680ce2d35` |
| Depends on | `WS02-04`, `WS02-04B2A2A`, `WS02-04B2A2B1`, `WS02-04B2A2B2`, `WS02-04B2A2B3`, `WS02-05A`, `WS02-05B1`, `WS03-01`, payment/provider, image/storage, chat/moderation, and policy/legal owner boundaries |
| Trusted test scope | `backend/tests/workflows/response_minimization` |
| Production correction set | None approved by Gate A |
| Frontend correction set | None approved by Gate A |
| Gate B evidence type | Requirement declaration, testing record, focused trusted backend tests, runtime API response proof, Pydantic/schema inspection, generated OpenAPI response-schema inspection, current frontend caller/source inventory, and negative-space response-model/bypass inventory |

## 1. Purpose

WS02-05B2 proves that current API responses expose only the fields appropriate
for the caller audience on the pass-owned response surfaces.

In plain English: public callers, signed-in users, participants, hosts, admins,
moderators, and provider/internal workflows do not all have the same right to
see the same data. The backend response contract must enforce that separation.
The frontend hiding a field is not enough.

This pass owns the response-minimization side of `API-M14` and the response
field-level authorization side of `IAM-014`. It does not change request-body
ownership, payment/provider correctness, storage lifecycle, policy/legal
authoring, cache policy, docs exposure, permanent runtime behavior, or external
provider evidence.

## 2. Why This Matters

Pickup Lane stores operational fields that are useful internally but unsafe or
unnecessary in public and ordinary-user responses:

- ownership, actor, account, role, and verifier fields;
- payment provider identifiers, idempotency state, failure diagnostics, and raw
  provider payloads;
- image storage object keys, bucket/provider details, upload lifecycle, and
  internal metadata;
- moderation findings, review lifecycle, removal/restoration actors, and admin
  action evidence;
- lifecycle, audit, deletion, completion, and management timestamps that do not
  belong to a product-visible response;
- broad ORM/table-shaped read models reused across audiences.

`API-M14` requires separate request, internal, public, and administrative
schemas, plus response filtering. `IAM-014` requires purpose-specific schemas
and explicit field authorization. This pass makes those boundaries testable for
the current repository state.

## 3. Authority And Repository Truth

Current accepted `develop` at
`29906d6c6be44bd81d31b6988345fab10af22908` is repository truth for the current
implementation state.

Authoritative production-readiness sources and this reconciled/frozen plan
define what must be true for Gate B. Historical PR `#125`, its branch, its
description, and its old test file are provenance only.

The current stale historical plan text claimed implementation-complete status.
Gate A replaces that with this frozen design, requirement set, and evidence
architecture.

## 4. Audience Model

B2 uses these current response audiences:

- signed-out/public callers: public discovery, public game detail, public image
  display, public policy/legal display, and generally visible Need-a-Sub cards;
- authenticated ordinary users: their own account/profile, saved-card display,
  checkout state, payments/refunds they are authorized to view, My Games, and
  Need-a-Sub participation;
- self/account callers: the signed-in user's profile/account response, including
  provider-derived display snapshots that current frontend workflows need;
- participants: game and Need-a-Sub chat/message/roster context needed for
  participation UI;
- hosts/owners: host-owned game context, host guest capacity, current viewer
  capability, and owner-owned Need-a-Sub/post state where current workflows need
  it;
- admins: operational user, game, financial, image, review, moderation, support,
  and audit fields needed by active admin workflows;
- moderation/support/admin operations: richer evidence and workflow state behind
  active admin authorization;
- internal/provider-owned evidence: raw Stripe payloads, provider facts, storage
  object facts, internal reconciliation data, and other server/provider state.

The backend, not the frontend, must enforce the audience boundary. Admin
responses may remain richer when an active admin workflow needs the fields.

## 5. Gate A Reconciliation Findings

### Current Source Truth

Current source already contains audience-specific response contracts for the
main B2 surfaces:

- public game detail and generic game list use `GameDetailRead` through
  `build_game_detail_read`;
- browse and My Games use card/list projection schemas rather than `GameRead`;
- public game participant reads use `PublicGameParticipantRead`;
- self/auth/account routes use `SelfUserRead`;
- admin user routes use admin/user operational schemas;
- ordinary payment/refund routes use `PaymentSummaryRead` and
  `RefundSummaryRead`;
- payment-event HTTP reads use `PaymentEventRead` without `raw_payload`;
- public game and venue image routes use `GameImagePublicRead` and
  `VenueImagePublicRead`;
- admin image and upload routes use admin/upload schemas with operational
  metadata;
- participant game chat and Need-a-Sub chat message routes use
  `ChatMessageParticipantRead` and `SubPostChatMessageParticipantRead`;
- admin chat/moderation routes use `AdminChatMessageRead` and related admin
  response schemas;
- public policy-document reads use `PolicyDocumentPublicRead`.

Current source also contains later surfaces that must be classified by Gate B
negative-space evidence rather than ignored, including saved payment methods,
Need-a-Sub public/owner/admin responses, admin money, admin review, admin
community/official game, support, notification, inbox, and webhook response
families.

### Historical PR Provenance

Historical PR `#125` merged production and frontend changes for response
minimization. Its production/frontend intent was:

- add or use audience-specific game, user, financial, image, chat, and policy
  read schemas;
- use public/detail response mapping for game reads;
- split self and admin user responses;
- split ordinary and admin payment/refund responses;
- remove raw provider payload from `PaymentEventRead`;
- split public/admin image responses;
- split participant/admin chat responses;
- adjust frontend image ordering away from `created_at`;
- retain temporary compatibility fields where current callers needed them.

The historical changed-file set included backend routes, schemas, two services,
frontend Browse Games image/detail code, a frontend unit test, the old plan, and
one historical backend test file. The historical backend test file must not be
used to derive current B2 requirements or evidence.

### Historical Production/Frontend Change Summary

Historical production changes introduced `GameDetailRead`, `SelfUserRead`,
`AdminUserRead`, `PaymentSummaryRead`, `AdminPaymentRead`,
`RefundSummaryRead`, `AdminRefundRead`, public/admin image reads, participant
chat reads, and public policy reads. It changed routes to use those schemas and
added explicit `build_game_detail_read` mapping for game detail/list responses.

Historical frontend changes made Browse/Checkout image selection sort by public
display fields rather than public image `created_at`.

### Original Omissions

The historical plan and implementation did not provide current EN-01 trusted B2
evidence:

- no current requirement declaration JSON for B2;
- no current `TESTING_RECORD.md`;
- no fresh trusted runtime API response tests under a B2 workflow root;
- no generated OpenAPI response-schema proof;
- no current response-model bypass inventory;
- no current frontend caller compatibility inventory;
- no negative-space audit over later accepted routes.

### Material Later Evolution

Accepted later work changed the surrounding ownership model:

- `WS02-05A` owns media type, HTTP error, cache, OpenAPI/docs exposure,
  tombstones, pagination inventory, and external HTTP-chain handoffs.
- `WS02-05B1` owns request ownership and mass-assignment boundaries, including
  generic game write ownership.
- `WS03-01` owns identity authority, Firebase/PostgreSQL authority split,
  verified-email policy, and ordinary profile write boundaries.
- `WS02-04B2A2B2` owns provider/payment request inputs, retired generic
  payment/refund/event mutations, narrow payment-event repair fields, saved-card
  SetupIntent input shape, and provider/payment handoffs.
- `WS02-04B2A2B3` owns policy/legal request ownership while preserving B2's
  public policy response minimization ownership.
- Later admin official/community game, admin money, admin review, support,
  notification, and Need-a-Sub work added explicit admin and public schemas that
  Gate B negative-space proof must classify.
- Current frontend source still consumes `GameDetailRead.host_user_id`,
  `GameDetailRead.host_guest_max`, and `email_verified_at`; it does not use
  raw payment provider payloads or public image storage metadata.

## 6. Stable Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS02-05B2-R1` | Public and ordinary game responses are audience-specific. | Public game detail, generic public game list, browse cards, My Games cards, cancellation/host-edit returns, and public roster/count responses expose only product-required game, roster, capacity, schedule, location, price, cancellation, chat, and compatibility fields for the caller audience. Broad `GameRead` and request/internal fields stay out of public/ordinary game responses. | Prevents creator, actor, lifecycle, policy, audit, and table-shaped game fields from leaking to public or ordinary callers. |
| `WS02-05B2-R2` | Host/admin game richness is explicit. | Host-only game context may include host identity and host guest capacity when the caller is the host or an admin. Admin game/official/community responses may retain operational fields only behind active admin authorization. | Keeps current host/admin workflows working without making host/admin data public. |
| `WS02-05B2-R3` | Self/user/admin identity responses follow WS03 authority. | Self/auth/account responses expose current product-required self fields and provider-derived snapshots such as `email_verified_at`; public/ordinary routes do not expose provider UID, audit timestamps, deletion marker, or admin-only state. Admin user routes retain operational identity fields behind admin authorization. | Prevents identity/provider/admin state leakage while preserving current create-game verification and profile UI needs. |
| `WS02-05B2-R4` | Ordinary financial responses exclude provider/internal details. | Ordinary payment, refund, payment-event, checkout-adjacent, and saved-card display responses expose only product-required amount, currency, status, association, card display, and timing fields. Provider IDs, idempotency keys, raw payloads, reconciliation internals, failure diagnostics, and bookkeeping fields stay out of ordinary responses. Admin financial routes may retain required operational fields. | Avoids payment/provider data exposure without claiming WS05 provider correctness. |
| `WS02-05B2-R5` | Public image responses exclude storage/provider internals. | Public game and venue image reads expose display identity, URL, role, primary flag, sort order, and user-facing text only. Storage provider, object key, bucket/account, upload lifecycle, uploader, status, content type, size, ETag, and audit timestamps stay out of public responses. Admin/upload responses retain required operational metadata. | Prevents storage topology and upload metadata leakage while preserving public image display and admin upload management. |
| `WS02-05B2-R6` | Participant chat responses exclude moderation/admin evidence. | Game chat and Need-a-Sub participant message responses expose conversation display fields only. Review status, visibility workflow, detections, reviewer/admin IDs, removal/restoration actors, moderation source, and admin evidence appear only in admin/moderation responses. | Prevents participant chat APIs from revealing moderation workflow state while preserving admin review needs. |
| `WS02-05B2-R7` | Public policy/legal reads expose display/version fields only. | Public policy-document reads expose stable identity, policy type, version, title, content URL/text, and effective time. Management state such as active flag, retirement state, authoring lifecycle, and audit timestamps is not part of public policy reads. | Public legal display needs stable renderable content, not management internals. |
| `WS02-05B2-R8` | Response filtering and OpenAPI schemas are truthful. | Routes in B2 scope declare appropriate `response_model`s or are explicitly classified exceptions; FastAPI/Pydantic response filtering is the backend boundary; generated OpenAPI response schemas match minimized contracts; broad ORM/table-shaped schemas, raw dict/`Any`, provider payloads, and missing response models cannot bypass minimization on B2-owned surfaces. | Schema names alone do not prove runtime exposure. Gate B must catch bypasses and docs/runtime drift. |
| `WS02-05B2-R9` | Current frontend compatibility is preserved and documented. | Current production frontend callers remain compatible with minimized responses. Temporary compatibility fields are retained while current callers need them, and current image ordering uses public display fields rather than internal timestamps or storage metadata. | Response minimization must not silently break current product workflows or rely on old caller assumptions. |
| `WS02-05B2-R10` | Later-owner and external-evidence boundaries remain explicit. | B2 does not claim request ownership, mass-assignment closure, provider correctness, storage processing/lifecycle, policy/legal authoring, cache/docs/tombstone ownership, permanent HTTP-chain evidence, browser/e2e proof, migrations, concurrency, observability, privacy/retention, or public API versioning. | Prevents local response tests from overclaiming production readiness outside B2. |

## 7. Requirement Declaration Design

Gate B must create `backend/tests/support/requirements/ws02_05b2.json` with
this checker-compatible declaration:

| ID | State | Scope | Source controls | Reason |
|---|---|---|---|---|
| `WS02-05B2-R1` | `required` | `workflows/response_minimization` | `["API-M14", "IAM-014", "WS02-05B2", "WS02-05A", "WS02-05B1"]` | Public and ordinary game response fields are B2-owned and must be runtime-proven. |
| `WS02-05B2-R2` | `required` | `workflows/response_minimization` | `["API-M14", "IAM-014", "WS02-05B2", "WS02-05B1"]` | Host/admin game response richness must be deliberate, not accidental public leakage. |
| `WS02-05B2-R3` | `required` | `workflows/response_minimization` | `["API-M14", "IAM-014", "WS02-05B2", "WS03-01"]` | User response fields must align with current identity authority. |
| `WS02-05B2-R4` | `required` | `workflows/response_minimization` | `["API-M14", "IAM-014", "PAY-004", "PAY-005", "PAY-006", "PAY-008", "PAY-009", "WS02-05B2", "WS05"]` | Ordinary financial responses must not expose provider/internal fields; provider correctness remains later. |
| `WS02-05B2-R5` | `required` | `workflows/response_minimization` | `["API-M14", "IAM-014", "STO-006", "STO-009", "WS02-05B2", "WS06"]` | Public image responses must not expose storage/provider internals. |
| `WS02-05B2-R6` | `required` | `workflows/response_minimization` | `["API-M14", "IAM-014", "WS02-05B2", "WS02-04C3A"]` | Participant chat responses must not expose moderation/admin evidence. |
| `WS02-05B2-R7` | `required` | `workflows/response_minimization` | `["API-M14", "GOV-006", "WS02-05B2", "WS02-04B2A2B3"]` | Public policy/legal response fields are B2-owned while policy/legal writes remain elsewhere. |
| `WS02-05B2-R8` | `required` | `workflows/response_minimization` | `["API-M14", "API-M18", "IAM-014", "WS02-05B2", "WS02-05A"]` | Runtime response filtering, OpenAPI truth, and bypass inventory are required for honest response-minimization evidence. |
| `WS02-05B2-R9` | `required` | `workflows/response_minimization` | `["API-M14", "API-M18", "WS02-05B2", "WS07"]` | Current frontend caller compatibility is a B2 acceptance condition. |
| `WS02-05B2-R10` | `deferred` | `governance` | `["API-M13", "API-M14", "API-M16", "API-M18", "API-M19", "IAM-014", "PAY-004", "PAY-005", "PAY-006", "PAY-008", "PAY-009", "STO-006", "STO-009", "WS02-05A", "WS02-05B1", "WS03-01", "WS05", "WS06", "WS09", "WS10"]` | Later-owner and external evidence cannot be closed by B2 local response tests and must have no pytest mapping. |

## 8. Current Response Contracts By Surface

### 8.1 Game Responses

Current public/detail routes:

- `GET /games/{game_id}` returns `GameDetailRead` through
  `build_game_detail_read`.
- `GET /games` returns `list[GameDetailRead]`.
- `POST /games/{game_id}/cancel` and `PATCH /games/{game_id}/host-edit`
  return `GameDetailRead`.
- `GET /games/browse` returns `GameCardListRead`.
- `GET /games/{game_id}/participants` and `/game-participants/me` use public
  participant response schemas.

`GameDetailRead` omits `created_by_user_id`, `sport_type`, `policy_mode`,
published/completed actor fields, cancellation actor/source, created/updated/
deleted timestamps, and other broad `GameRead` fields. `build_game_detail_read`
sets `host_user_id` to `None` and `host_guest_max` to `0` unless the caller is
the host or an admin.

Current admin generic create/update/delete routes may still return `GameRead`
behind active admin authorization. Admin official/community game routes use
their own admin response schemas.

### 8.2 User/Account Responses

`/auth/me`, `/auth/sync-user`, `/auth/account`, `/users/me`, and
`PATCH /users/me` use `SelfUserRead`. It includes current self-display and
workflow fields such as `role`, `email`, `email_verified_at`, profile fields,
account/hosting status, and `member_since`.

`SelfUserRead` omits `auth_user_id`, created/updated/deleted audit fields, and
admin-only operational fields. `email_verified_at` remains a provider-derived
snapshot needed by current frontend verification gates; it is not an
authorization source.

Admin user routes use admin/user operational schemas behind
`require_active_admin`.

### 8.3 Payments, Refunds, Payment Events, And Saved Cards

Ordinary `/payments` routes return `PaymentSummaryRead`. Ordinary `/refunds`
routes return `RefundSummaryRead`. These summaries exclude provider payment/
refund IDs, idempotency key, failure diagnostics, raw provider payloads,
metadata blobs, and update timestamps.

`PaymentEventRead` excludes `raw_payload`; raw Stripe payloads remain stored and
processed internally. `POST /payment-events` remains a retired mutation
tombstone, and payment-event repair is admin-only and narrow.

Saved payment-method self routes currently expose card display and local saved
card state through `UserPaymentMethodRead` without exposing the stored Stripe
payment-method ID. Gate B negative-space evidence must classify this surface and
fail if current ordinary saved-card responses expose provider/internal fields
without an authoritative product need.

Admin money routes may retain provider identifiers, idempotency, failure
diagnostics, and audit timing required by active admin financial workflows.
That admin richness is not a public or ordinary-user contract.

### 8.4 Images

Public game-image routes return `GameImagePublicRead`. Public venue-image
routes return `VenueImagePublicRead`.

Public image responses expose display identity, image URL, role, primary flag,
sort order, and user-facing venue text where applicable. They omit uploader,
image status, storage provider, object key, bucket, account, content type, byte
size, ETag, upload lifecycle, created/updated/deleted timestamps, and provider
metadata.

Admin image routes and upload-ticket/complete routes use `GameImageAdminRead`,
`VenueImageAdminRead`, and `VenueImageUploadRead`. Those may retain operational
metadata needed by admin upload/management workflows. WS06 owns final file
safety, processing, R2 lifecycle, cleanup, provider controls, and storage
runtime evidence.

### 8.5 Chat And Need-a-Sub Chat

Participant game chat message routes use `ChatMessageParticipantRead`.
Participant Need-a-Sub chat message routes use
`SubPostChatMessageParticipantRead`.

Participant responses include display conversation fields such as message ID,
chat ID, sender identity/display snapshots, message type/body, pinned status
where applicable, and created/updated times needed for current chat ordering.
They omit review status, visibility workflow, reviewer IDs, removal/restoration
actors, removal source, detection lists, and admin moderation evidence.

Admin official/community/Need-a-Sub moderation routes use admin chat schemas
with the richer moderation fields behind active admin authorization.

### 8.6 Policy And Legal Reads

Public policy-document reads use `PolicyDocumentPublicRead`. The public
contract includes policy identity, type, version, title, content URL/text, and
effective time. It excludes active/retired management state and audit
timestamps.

Policy/legal write ownership and tombstones remain with B3 and 05A as
applicable. B2 owns only the public response shape.

### 8.7 Negative-Space Surfaces

Gate B must also inventory current response surfaces outside the original 30
historical changed files, including:

- saved payment methods;
- Need-a-Sub public, owner, request, and admin responses;
- admin official/community game responses;
- admin money, admin review, support, rejected-attempt, action/audit, platform
  notice, notification, inbox, user settings/stats, waitlist, booking, and game
  credit responses;
- raw-body provider webhook responses and small operational dictionary
  endpoints.

The inventory must classify each as one of:

- in B2 scope and already minimized;
- in B2 scope and requiring a Gate A correction before implementation;
- explicit admin/internal/provider exception;
- later-owner/non-B2 scope with reason.

## 9. Temporary Compatibility Fields

The following fields remain intentionally retained:

- `GameDetailRead.host_user_id`: current frontend game detail and chat
  capability logic still compares the current user to this field. Public and
  non-host responses must receive `null`; host/admin responses may receive the
  actual host id.
- `GameDetailRead.host_guest_max`: current host guest-management UI still needs
  the host/admin value. Public and non-host responses receive `0`.
- `SelfUserRead.email_verified_at`: current frontend create-game and
  verification flows use it as display/control state. WS03 remains the
  authorization authority, and stale local snapshots must not grant access.
- `SelfUserRead.profile_photo_url`: remains a dormant self-display
  compatibility field; ordinary users do not write it through `/users/me`.
- `PolicyDocumentPublicRead.id`: public legal/policy records keep stable
  identity for list/detail rendering.

Retirement requires current caller proof and a separate approved compatibility
plan. Gate B must not remove these fields merely because they look internal.

## 10. Correction Design

### Backend Corrections

No backend production correction is approved by Gate A.

Gate B is an evidence reconstruction pass unless trusted evidence finds a
material current leak on a B2-owned response surface. If that happens, Gate B
must stop and return for Gate A correction rather than silently adding
production files.

### Frontend Corrections

No frontend correction is approved by Gate A.

Current frontend callers still require the retained compatibility fields above
and current image display code uses public image fields only. If Gate B finds a
current frontend dependency on a field that B2 must remove, Gate B must stop and
return for Gate A correction.

## 11. Gate B Editable File Set

Gate B may edit only these files unless a human approves a Gate A correction:

1. `backend/tests/support/requirements/ws02_05b2.json`
2. `backend/tests/workflows/response_minimization/TESTING_RECORD.md`
3. `backend/tests/workflows/response_minimization/test_game_response_audience_contract.py`
4. `backend/tests/workflows/response_minimization/test_user_response_audience_contract.py`
5. `backend/tests/workflows/response_minimization/test_financial_response_minimization_contract.py`
6. `backend/tests/workflows/response_minimization/test_image_response_minimization_contract.py`
7. `backend/tests/workflows/response_minimization/test_chat_policy_response_minimization_contract.py`
8. `backend/tests/workflows/response_minimization/test_response_model_openapi_negative_space_contract.py`
9. `backend/tests/workflows/response_minimization/test_current_frontend_response_compatibility_contract.py`

Do not edit production source, frontend source, migrations, configuration,
shared testing infrastructure, other pass plans, or `TESTING_RECORD.md` files
outside this scope.

## 12. Evidence Architecture

Gate B evidence must prove material response exposure, not only schema names.

| File | Requirements | Required responsibilities |
|---|---|---|
| `test_game_response_audience_contract.py` | R1, R2 | Runtime API proof for public/non-host/host/admin game detail/list/cancel/host-edit response fields; public roster/count shapes; `GameRead` reserved to admin routes; `host_user_id`/`host_guest_max` masking and authorized visibility. |
| `test_user_response_audience_contract.py` | R3 | Runtime/API and schema proof that self responses expose `SelfUserRead` fields, omit provider UID and audit/deletion/admin-only fields, retain `email_verified_at` as a snapshot, and admin user routes retain operational fields behind admin authorization. |
| `test_financial_response_minimization_contract.py` | R4 | Runtime/API proof that ordinary payments/refunds exclude provider IDs, idempotency, metadata, failure diagnostics, and update timestamps; payment events exclude `raw_payload`; saved-card self responses do not expose stored Stripe payment-method IDs; admin financial responses remain explicitly admin-only and operational. |
| `test_image_response_minimization_contract.py` | R5 | Runtime/API proof that public game/venue image reads exclude storage/provider/upload metadata and audit fields while retaining display identity/order fields; admin image/upload responses retain required operational metadata behind admin authorization. |
| `test_chat_policy_response_minimization_contract.py` | R6, R7 | Runtime/API proof that participant game and Need-a-Sub chat message responses exclude moderation/admin fields; admin chat moderation responses retain needed evidence; public policy reads exclude active/retired/audit management fields. |
| `test_response_model_openapi_negative_space_contract.py` | R8 | Static/source and generated OpenAPI proof that B2 routes use audience-specific response models, minimized schemas appear in OpenAPI, raw dict/`Any`/provider payload structures are classified, missing-response-model exceptions are explicit, and no route bypass exposes a broader ORM/table-shaped response on B2-owned surfaces. |
| `test_current_frontend_response_compatibility_contract.py` | R9 | Source inventory proof over current frontend callers: retained compatibility fields are still needed, public image ordering uses `id`, `is_primary`, and `sort_order` rather than `created_at` or storage fields, and ordinary callers do not consume removed provider/storage/moderation fields. |
| `TESTING_RECORD.md` | R1-R10 | Records scope, risks, scenarios, proof layers, accepted gaps, deferred R10, no historical-test reliance, and adequacy conclusion. |
| `ws02_05b2.json` | R1-R10 | Declares every stable requirement with checker-compatible state, scope, source controls, and reason. |

Tests must not copy one field list and compare only Pydantic class members when
the risk is runtime HTTP serialization. Use runtime API proof for surfaces where
FastAPI response filtering is the safety boundary.

## 13. Proof-Layer Decisions

| Proof layer | Gate B decision | Reason |
|---|---|---|
| Backend schema correction | No planned correction | Current source appears to have B2-owned schema splits. If evidence finds a leak, return to Gate A. |
| Backend route correction | No planned correction | Current routes appear to use minimized response models on B2-owned surfaces. If evidence finds a bypass, return to Gate A. |
| Backend service/serializer correction | No planned correction | Current explicit game/image serializers appear adequate. If evidence finds over-broad construction, return to Gate A. |
| Frontend compatibility correction | No planned correction | Current frontend uses retained compatibility fields and public image selector fields. |
| Requirement JSON | Required | EN-01 checker/traceability needs stable B2 requirement declarations. |
| `TESTING_RECORD.md` | Required | Human/Gate C review needs proof-layer adequacy and non-closure records. |
| Backend API tests | Required | Runtime HTTP exposure is the material risk. |
| Pydantic/schema inspection | Required | Needed for model field boundaries and negative-space classification. |
| Generated OpenAPI response-schema inspection | Required | B2 must prove docs/schema exposure matches current response contracts without taking over 05A behavior. |
| PostgreSQL proof | Required where persisted/auth audience state is needed | Public/host/admin/user/payment/image/chat/policy runtime responses need realistic persisted rows and authorization. Static inventory does not need DB. |
| Frontend unit tests | No new tests required | Existing image selector unit test may be run as validation; Gate B evidence uses backend static source inventory unless frontend source changes are later approved. |
| Frontend build/lint | Not required for planned Gate B | No frontend source change is approved. If a frontend correction is later approved, add appropriate frontend validation in a Gate A correction. |
| Playwright/browser proof | Not required | Current response-field compatibility can be proven at API/source/unit layers. |
| Provider/network proof | Not required | B2 does not prove Stripe/Firebase/R2 provider correctness or runtime provider state. |
| Migration proof | Not required | No database schema change is approved. |
| Genuine concurrency proof | Not required | Response field minimization is not a race/concurrency invariant. |
| Controlled time | Not required except simple fixed timestamps in factories | No time-window behavior is owned by B2. |

## 14. Gate B Validation Strategy

Gate B must run the narrowest useful checks plus final regression evidence:

```bash
git diff --check
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/workflows/response_minimization
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/response_minimization
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests
```

If no frontend source changes are made, the optional frontend compatibility
sanity check is:

```bash
cd frontend
npm run test:unit
```

Do not run Playwright/e2e for B2 unless a later approved Gate A correction
introduces a browser-only compatibility risk.

## 15. Cross-Pass Ownership

| Owner | B2 relationship |
|---|---|
| `WS02-05A` | Owns HTTP media, stable errors, OpenAPI error representation, cache classification, docs exposure, tombstone representation, pagination inventory, and external HTTP-chain handoffs. B2 may inspect generated OpenAPI response schemas for response-shape truth only. |
| `WS02-05B1` | Owns request ownership and mass-assignment cleanup. B2 must not change request schemas to simplify response contracts. |
| `WS03-01` | Owns Firebase/PostgreSQL identity authority, verified-email policy, provider UID/email verification, and profile write authority. B2 aligns response exposure with WS03 but does not reopen identity authority. |
| `WS02-04B2A2B2` / `WS05` | Own provider/payment input ownership, saved-card provider validation, payment/refund/provider lifecycle, webhook correctness, reconciliation, refunds, credits, durable jobs, and provider/runtime evidence. B2 owns ordinary/admin HTTP response minimization only. |
| `WS02-04B2A2B3` | Owns policy/legal request ownership. B2 owns public policy read response minimization only. |
| `WS06` | Owns image file validation, processing, object lifecycle, R2 controls, cleanup, provider evidence, and storage runtime proof. B2 owns public/admin HTTP image representation only. |
| Moderation/admin owners | Own review, moderation, enforcement, support, and admin workflow behavior. B2 must preserve necessary admin evidence fields behind admin authorization. |
| `WS09` / `WS10` | Own observability, dashboards, alerts, incident response, privacy/retention, recovery, external evidence handling, and operational proof. |

## 16. Non-Goals

B2 does not:

- change production source unless a new Gate A correction approves it;
- change frontend source unless a new Gate A correction approves it;
- modify request schemas, request-body limits, or mass-assignment boundaries;
- modify database models or migrations;
- prove Stripe, Firebase, R2, edge, CDN, hosting, TLS, CORS provider, or
  permanent deployment behavior;
- prove payment/refund lifecycle correctness, reconciliation, retries, or
  durable jobs;
- prove image file safety, image processing, lifecycle cleanup, or R2 controls;
- prove legal text adequacy, legal review, privacy/retention policy, or policy
  authoring workflow;
- add public API versioning or deprecation policy;
- redesign admin moderation, support, audit, or money workflows;
- use out-of-scope test roots for B2 evidence.

## 17. External And Later Gaps

The following remain outside B2 closure:

- permanent edge/CDN/proxy/TLS/runtime response captures;
- production docs/OpenAPI exposure policy beyond 05A source evidence;
- shared-cache behavior and private-response cache proof beyond 05A;
- payment provider dashboard and runtime webhook evidence;
- provider event ordering, missing/stale event recovery, refund/provider
  reconciliation, and durable job behavior;
- saved-card provider lifecycle correctness and provider dashboard evidence;
- image file validation, image processing, R2 lifecycle, cleanup, and recovery;
- full admin/moderation process design, evidence retention, and operational
  review policy;
- privacy/retention/deletion policy and final legal review;
- browser/e2e identity-cache and history isolation;
- load, race, and concurrency evidence outside response filtering;
- future response versioning/deprecation if Pickup Lane exposes a public API
  contract beyond current app clients.

## 18. Completion Criteria

Gate B is complete only when:

- `backend/tests/support/requirements/ws02_05b2.json` declares R1-R10 exactly;
- `backend/tests/workflows/response_minimization/TESTING_RECORD.md` records the
  B2 risk model, proof layers, covered scenarios, deferred R10, and adequacy;
- trusted B2 tests under `backend/tests/workflows/response_minimization` prove
  every required executable requirement;
- deferred R10 has no pytest mapping and is recorded as governance/later-owner
  evidence;
- runtime API tests prove actual HTTP response exposure for B2-owned surfaces;
- generated OpenAPI response-schema checks prove minimized response schemas are
  documented truthfully;
- negative-space evidence classifies raw/open structures, missing response
  models, and later routes without using historical tests as authority;
- current frontend compatibility and temporary compatibility-field needs are
  proven from current source;
- no production/frontend correction was made outside an approved Gate A
  correction;
- `git diff --check`, focused B2 tests, checker commands, and required backend
  regression complete with honest results;
- out-of-scope test roots remain unused for B2 evidence.
