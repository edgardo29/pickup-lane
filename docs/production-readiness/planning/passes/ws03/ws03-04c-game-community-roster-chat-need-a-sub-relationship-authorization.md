# Production-Readiness Pass Plan: WS03-04C - Game, Community, Roster, Chat, And Need-a-Sub Relationship Authorization

## At A Glance

| Field | Value |
| --- | --- |
| Parent pass | `WS03-04 - Complete authorization matrix and negative proof` |
| Executable child | `WS03-04C - Game, community, roster, chat, and Need-a-Sub relationship authorization` |
| Gate | Gate A - executable-pass design only |
| Current branch | `pr/WS03-04C` |
| Accepted develop baseline | `ffdfc6d744f88879b86d0a91bab83770d7540062` |
| Approved intake | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` |
| Approved intake SHA-256 | `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4` |
| Accepted prerequisite artifact | `WS03-04A - Authorization matrix foundation and route drift guard` |
| Accepted WS03-04A plan SHA-256 | `ff0a00b158408148c9f91c6087f66d409389f28f8006c32e658ab9dd6f0784b4` |
| Accepted sibling compatibility input | `WS03-04B - Self-owned account, notification, and financial record authorization` |
| Approved dependency graph | `WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D` |
| C-owned route families | `15` |
| C-owned route keys | `64` |
| Planned requirement declaration | `backend/tests/support/requirements/ws03_04c.json` |
| Planned trusted evidence scope | `backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization` |
| Planned production source edits | None. Gate B is planned as trusted evidence, requirement declaration, testing record, and register update over current accepted source. |
| Gate B stop condition if source defect appears | Stop and return for Gate A correction before changing production source. |

## Executable Pass Identity And Intake

`WS03-04C` is the relationship-authorization executable child selected by the
approved `WS03-04` Stage 0 intake. Its one primary outcome is trusted evidence
that ordinary game, community-game, roster, checkout, booking, waitlist,
chat/message, public venue/image, My Games, and Need-a-Sub routes enforce the
current user's source-defined relationship and lifecycle permissions.

The approved child graph remains unchanged:

```text
WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D
```

`WS03-04A` is the technical prerequisite because it owns the accepted route
matrix and drift guard. `WS03-04B` is an accepted sibling and compatibility
input in the current baseline, but the approved intake does not impose a
`B -> C` dependency. `WS03-04D` remains after both B and C because it owns final
admin/high-risk review and parent-gap disposition.

The pass is a coherent merge unit because it adds one C requirement declaration,
one C trusted workflow scope, one C testing record, and the proposed register
state for this child. No production behavior changes are planned. A rollback or
forward fix is therefore bounded to evidence/register files unless Gate B
discovers a source defect, in which case the run must stop for Gate A correction.

When merged, the safe repository state is: accepted source behavior remains
unchanged; C-owned ordinary relationship authorization has trusted local proof;
B-owned self-account/financial behavior remains separate; and D still owns
admin/high-risk breadth, final parent-gap disposition, and any remaining
cross-child closure.

## 1. Purpose

This pass closes ordinary relationship-authorization proof for the C-owned
routes in the accepted `WS03-04A` authorization matrix. Gate B will prove that
public routes expose only public catalog data, authenticated relationship reads
bind to the current user's allowed relationship, relationship mutations cannot
act for another user or wrong role, chat sender/read state is derived from the
authenticated user, and rejected relationship actions leave protected state and
provider-call boundaries unchanged.

## 2. Why This Matters

These routes sit on the product's most sensitive ordinary-user boundaries:
players join or leave games, hosts manage community games, users see private
game details after they have a valid relationship, chat membership controls who
can send and read messages, and Need-a-Sub posts/requests expose scheduling and
identity context. A missing relationship check here could let one signed-in user
view another user's booking, mutate another roster spot, act as a host, enter a
private chat, or trigger payment-related side effects for a game they do not
own. This pass makes those ordinary-user boundaries reviewable and traceable
before the remaining D-owned admin/high-risk work begins.

## 3. Authority Read

| Source | Gate A use |
| --- | --- |
| `docs/production-readiness/00-READ-ME-FIRST.md` | Authority order, current execution state, instruction adherence, frozen artifacts, sensitive-information rules, tracked-documentation safety, publication boundaries, and excluded-test rule. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | Stable program routing, WS03 context, trusted-evidence model, applicable-standard routing, and accepted-source model. |
| `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` | Stage/Gate responsibilities, later-child planning rules, Gate A file-set design, validation, correction routing, credential-safety enforcement, and stop conditions. |
| `docs/production-readiness/planning/templates/PASS-PLANNING-TEMPLATE.md` | Canonical plan structure, pass-shape requirements, validation command safety, and document self-review. |
| `docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` | Gate B testing-record scope, evidence-safety rules, and human adequacy expectations. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | Current accepted A/B state, remaining C/D state, and register update contract. |
| `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` | Frozen parent decomposition, C scope, B/C independence, D handoff, and no-gap/no-overlap allocation. |
| `docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md` | Accepted matrix schema, owner vocabulary, route drift guard, and later-child handoff rules. |
| `backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json` | Current accepted route-family allocation, C route inventory, owner fields, negative-proof owner, and uncovered-gap state. |
| `backend/tests/workflows/self_owned_account_notification_financial_authorization/*` | Accepted B sibling compatibility boundary for self-owned account, notification, and financial authorization. |
| `backend/tests/support/requirements/ws03_04a.json`; `backend/tests/support/requirements/ws03_04b.json` | Accepted A/B requirement states and deferred boundaries. |
| Master blueprint and final remediation plan | Parent controls `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, and `IAM-017`; proof-before-acceptance model; downstream stop conditions. |
| Accepted WS03 predecessor evidence | `WS03-01` identity and verified-email authority, `WS03-02` account lifecycle, `WS03-03A` recent-auth, and `WS03-03B` App Check/admin-provider boundaries. |
| Accepted cross-workstream evidence | Request ownership, response minimization, provider-payment input ownership, rate-limit, timeout, and request-bound evidence used only as compatibility inputs. |
| Repository standards | Backend ownership, backend testing, app testing standards, database rules, and feature docs for games, community games, My Games, Need-a-Sub, notifications, venue images, and payments. |
| Current production source | C-owned route modules, services, schemas, models, frontend callers, and the current FastAPI route table. |

## 4. Frozen Inputs And Prerequisite Verdict

| Check | Result |
| --- | --- |
| Current branch and baseline | Pass. Current branch is `pr/WS03-04C`; `HEAD`, `origin/develop`, and merge-base resolve to `ffdfc6d744f88879b86d0a91bab83770d7540062`. |
| Approved intake SHA | Pass. The intake hashes to `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`. |
| `WS03-04A` accepted in current `develop` | Pass. The accepted A plan, matrix artifact, requirement declaration, tests, testing record, and register state are present in current accepted source. |
| `WS03-04A` plan SHA | Pass. The current A plan hashes to `ff0a00b158408148c9f91c6087f66d409389f28f8006c32e658ab9dd6f0784b4`. |
| `WS03-04B` sibling state | Pass. Current accepted source includes the B plan, requirement declaration, tests, testing record, and register state. B is a compatibility input, not a C technical prerequisite. |
| C route inventory from accepted matrix | Pass. `WS03-04C` owns `15` route families and `64` route keys. |
| A matrix blockers affecting C | Pass. No C-owned route is blocked. The accepted A uncovered gap is a Stripe webhook lifecycle gap owned outside C. |
| Approved child boundary | Pass. No Stage 0 issue found. C remains bounded to relationship authorization; B-owned self-account/financial surfaces and D-owned admin/high-risk closure remain outside this child. |
| Current Gate A editable scope | Pass. Gate A edits this canonical plan only. |

Prerequisite verdict: `WS03-04C` is eligible for Gate A completion.

## 5. Gate A Outcome

Outcome: `READY FOR GATE B AFTER HUMAN APPROVAL`.

Gate B is designed as an evidence and register pass over current accepted source.
Gate A reconciliation found no current production-source correction required for
the C-owned relationship-authorization contracts. If Gate B discovers that
production source must change, or that an implementation/evidence file outside
the frozen Gate B editable file set is required, Gate B must stop for Gate A
correction.

## 6. Requirements

| ID | State | Scope | Controls | Requirement |
| --- | --- | --- | --- | --- |
| `WS03-04C-R1` | required | `workflows/game_community_roster_chat_need_a_sub_relationship_authorization` | `IAM-012`, `IAM-013`, `IAM-015`, `WS03-04A` | Consume the accepted A matrix and prove the C route inventory remains exactly `15` route families and `64` route keys, with no B/C/D ownership overlap, blocked C route, or unclassified C route drift. |
| `WS03-04C-R2` | required | same | `IAM-012`, `IAM-013`, `WS03-01`, `WS03-02` | Preserve the approved dependency and verified-email distinction for every C-owned route/action: public catalog reads may remain unauthenticated; current relationship/private reads require the current authenticated dependency used by source; relationship mutations require current provider-verified email where source uses `require_verified_user`. |
| `WS03-04C-R3` | required | same | `IAM-013`, `IAM-015`, `WS02-05B2` | Public game, community-detail, venue, venue-image, game-image, and Need-a-Sub reads expose only public/listable records and public response fields; hidden, inactive, removed, deleted, unpublished, or non-public resources are omitted or concealed unless the source-defined current-user relationship permits visibility. |
| `WS03-04C-R4` | required | same | `IAM-013`, `IAM-015` | Current-user relationship reads for bookings, checkout status, game participants, waitlist entries, My Games, Need-a-Sub owned posts, Need-a-Sub requests, and status histories bind records to the authenticated user or source-defined relationship and cannot be widened by caller-supplied user/object IDs. |
| `WS03-04C-R5` | required | same | `IAM-013`, `IAM-017`, `PAY-005` | Game roster, checkout, guest, cancel, and host-edit mutations enforce current verified-user relationship, host/player role, game state, lifecycle window, capacity, duplicate-state, and saved-card compatibility boundaries. |
| `WS03-04C-R6` | required | same | `IAM-013`, `IAM-017`, `PAY-005`, `PAY-006` | Community-game publish and community-detail host-edit behavior bind to the current verified host, current game state, accepted host-payment rules, publish-attempt ownership, and public concealment of hidden payment text/host-only fields. |
| `WS03-04C-R7` | required | same | `IAM-013`, `IAM-015` | Game chat and general chat-message routes prove membership authorization, sender binding, read-state binding, hidden/removed message concealment, nonmember denial, and separation from D-owned admin moderation breadth. |
| `WS03-04C-R8` | required | same | `IAM-013`, `IAM-015`, `IAM-017` | Need-a-Sub post, request, status-history, position, and scoped chat routes enforce post owner, requester, public viewer, confirmed-chat-member, lifecycle-window, sender, and read-state boundaries. |
| `WS03-04C-R9` | required | same | `IAM-012`, `IAM-013`, `IAM-017`, `WS02-05B1` | Field and mass-assignment proof covers every C-owned write surface where caller input could affect owner, requester, host, participant, booking, waitlist, game state, chat sender, read-state user, payment/provider identity, status, moderation, or admin/server-controlled fields. |
| `WS03-04C-R10` | required | same | `IAM-012`, `IAM-013`, `IAM-015`, `TST-005` | Negative/default-deny proof covers unauthenticated or invalid-credential `401`, authenticated-but-forbidden `403`, concealed `404`, wrong relationship IDs, hidden-resource direct reads, blocked lifecycle states, caller-controlled actor substitution, and rejected mutations with no prohibited side effects. |
| `WS03-04C-R11` | required | same | `GOV-006`, `TST-005`, `WS03-04` | Requirement declarations, pytest requirement markers, matrix checks, test names, and the testing record remain traceable to this plan, the approved intake, accepted A/B artifacts, current source, and accepted predecessor repository evidence. |
| `WS03-04C-R12` | deferred | `governance` | `IAM-016`, `IAM-017`, `PAY-005`, `PAY-006`, `WS03-04D`, `WS04`, `WS05`, `WS09`, `WS10` | D-owned admin/high-risk route proof, minimum-necessary admin data, sensitive export/unmask/read-audit policy, durable Stripe/webhook/provider reconciliation, real provider/runtime evidence, genuine database-concurrency closure, moderation closeout, and final parent-gap disposition remain outside C. This requirement has zero pytest mappings. |

The planned requirement declaration is
`backend/tests/support/requirements/ws03_04c.json`. It must declare `R1`
through `R11` as required and `R12` as deferred/governance with no pytest
mapping.

## 7. Technical Design / Contracts

### 7.1 C Route Inventory

Gate B must treat the accepted A matrix as the authoritative C route inventory
unless current source drift makes that matrix stale.

| Family | Routes | Gate B proof focus |
| --- | --- | --- |
| `relationship_bookings_ws03_04c_ws03_04c` | `GET /bookings`; `GET /bookings/me`; `GET /bookings/{booking_id}` | Current-user booking list/object scoping; non-admin filters cannot widen access; foreign booking behavior follows current `403`/`404` contract; D owns active-admin broad listing. |
| `relationship_chat_messages_ws03_04c_ws03_04c` | `GET /chat-messages`; `POST /chat-messages`; `GET /chat-messages/{chat_message_id}` | Game chat message membership; sender derived from current user; nonmember denial; hidden/removed message concealment; admin moderation filters remain D-owned. |
| `relationship_checkout_ws03_04c_ws03_04c` | `GET /checkout/bookings/{booking_id}/status`; `POST /checkout/games/{game_id}/payment-intent` | Checkout status current booking buyer scoping; payment-intent creation for verified non-host current user on visible/joinable game; B owns saved-card ownership compatibility; WS05 owns durable provider reconciliation. |
| `relationship_community_game_details_ws03_04c_ws03_04c` | `GET /community-game-details`; `GET /community-game-details/games/{game_id}/host-edit`; `PUT /community-game-details/games/{game_id}/host-edit`; `GET /community-game-details/{community_game_detail_id}` | Public detail visibility; host-only edit/read; payment-method text moderation concealment; host edit state/window and field boundary. |
| `relationship_community_games_ws03_04c_ws03_04c` | `POST /community-games/publish`; `GET /community-games/publish-attempts/{attempt_id}` | Verified host publish ownership, publish-fee/payment-attempt local authorization, attempt-status owner binding; live provider reconciliation remains outside C. |
| `relationship_game_chats_ws03_04c_ws03_04c` | `POST /game-chats/for-game/{game_id}`; `POST /game-chats/{game_chat_id}/read`; `GET /game-chats/{game_chat_id}/read-state` | Host/participant membership, current-user read-state binding, nonmember denial, and caller-controlled acting-user rejection. |
| `relationship_game_participants_ws03_04c_ws03_04c` | `GET /game-participants/me`; `GET /game-participants/{participant_id}` | Current user's participant rows; foreign participant denial unless D-owned active-admin branch. |
| `relationship_games_ws03_04c_ws03_04c` | `GET /games`; `GET /games/browse`; `GET /games/participant-counts`; `GET /games/{game_id}`; `POST /games/{game_id}/booking-guests/add`; `POST /games/{game_id}/cancel`; `POST /games/{game_id}/guests/add`; `POST /games/{game_id}/guests/remove`; `PATCH /games/{game_id}/host-edit`; `POST /games/{game_id}/join`; `POST /games/{game_id}/leave`; `GET /games/{game_id}/participants` | Public browse/detail visibility; hidden detail/roster relationship access; verified player join/leave/booking guests; verified host guests/cancel/edit; no cross-user roster, booking, waitlist, or host-state mutation. |
| `relationship_my_games_ws03_04c_ws03_04c` | `GET /my-games`; `GET /my-games/need-a-sub` | Current user's game and Need-a-Sub relationship lists only, with private response cache headers. |
| `relationship_need_a_sub_posts_ws03_04c_ws03_04c` | `GET /need-a-sub/posts`; `POST /need-a-sub/posts`; `GET /need-a-sub/posts/cards`; `GET /need-a-sub/posts/mine`; `GET /need-a-sub/posts/{sub_post_id}`; `PATCH /need-a-sub/posts/{sub_post_id}`; `PATCH /need-a-sub/posts/{sub_post_id}/cancel`; `GET /need-a-sub/posts/{sub_post_id}/chat`; `POST /need-a-sub/posts/{sub_post_id}/chat`; `GET /need-a-sub/posts/{sub_post_id}/chat/messages`; `POST /need-a-sub/posts/{sub_post_id}/chat/messages`; `POST /need-a-sub/posts/{sub_post_id}/chat/read`; `GET /need-a-sub/posts/{sub_post_id}/chat/read-state`; `GET /need-a-sub/posts/{sub_post_id}/positions`; `GET /need-a-sub/posts/{sub_post_id}/status-history` | Public post/card/detail/position visibility; owner create/edit/cancel/mine/status-history; confirmed-only scoped post chat; sender/read-state current-user binding; no owner spoofing or chat access by pending/waitlisted/declined/canceled/unrelated users. |
| `relationship_need_a_sub_requests_ws03_04c_ws03_04c` | `GET /need-a-sub/my-requests`; `GET /need-a-sub/posts/{sub_post_id}/requests`; `POST /need-a-sub/posts/{sub_post_id}/requests`; `PATCH /need-a-sub/requests/{request_id}/accept`; `PATCH /need-a-sub/requests/{request_id}/cancel`; `PATCH /need-a-sub/requests/{request_id}/cancel-by-owner`; `PATCH /need-a-sub/requests/{request_id}/decline`; `PATCH /need-a-sub/requests/{request_id}/no-show`; `GET /need-a-sub/requests/{request_id}/status-history` | Requester list/create/cancel and owner list/accept/decline/cancel/no-show boundaries; lifecycle windows; status-history owner/requester visibility. |
| `relationship_public_game_images_ws03_04c_ws03_04c` | `GET /game-images`; `GET /game-images/{game_image_id}` | Public active game-image list/detail only; hidden/removed/deleted image concealment; retired mutation routes outside C. |
| `relationship_public_venue_images_ws03_04c_ws03_04c` | `GET /venue-images` | Public active venue-image list only; storage/provider values must be sanitized test data when asserted. |
| `relationship_public_venues_ws03_04c_ws03_04c` | `GET /venues`; `GET /venues/{venue_id}` | Public active venue list/detail; inactive/deleted venue concealment; admin venue mutations remain outside C. |
| `relationship_waitlist_entries_ws03_04c_ws03_04c` | `GET /waitlist-entries/me`; `GET /waitlist-entries/{waitlist_entry_id}` | Current user's waitlist rows; foreign waitlist row denial unless D-owned active-admin branch. |

Gate B must fail if the current route table contains a C-owned route not listed
above, a listed C route disappears, a listed C route is assigned to another
child without human-approved Gate A correction, or a route's backend
authorization dependencies drift from the accepted matrix.

### 7.2 Verified-Email Authorization Contract

Accepted identity authority requires provider-verified email for hosting,
joining, booking or checkout mutations, Need-a-Sub writes, private-message
writes, elevated privileges, and admin actions. It does not require verified
email for public catalog reads. Current source uses that distinction for the
C-owned routes.

| Classification | C route/action keys | Gate B proof composition |
| --- | --- | --- |
| Public unauthenticated reads permitted when the resource is public | `GET /games`; `GET /games/browse`; `GET /games/participant-counts`; public-visible `GET /games/{game_id}`; `GET /community-game-details`; public-visible `GET /community-game-details/{community_game_detail_id}`; `GET /need-a-sub/posts`; `GET /need-a-sub/posts/cards`; public-visible `GET /need-a-sub/posts/{sub_post_id}`; `GET /need-a-sub/posts/{sub_post_id}/positions`; `GET /game-images`; `GET /game-images/{game_image_id}`; `GET /venue-images`; `GET /venues`; `GET /venues/{venue_id}` | Positive public reads must prove only public/listable rows are returned. Negative proof must prove hidden, inactive, removed, deleted, unpublished, and otherwise non-public rows are omitted or concealed. |
| Authenticated current or active app user required, but provider-verified email not itself required | Current relationship reads such as bookings, checkout status, game participants, waitlist entries, My Games, Need-a-Sub mine/chat/read/messages/status-history, request lists, and read-state routes where current source uses `get_current_app_user` or `require_active_user` | Positive proof must exercise representative unverified authenticated users where current source permits active/current reads. Negative proof must show unverified status does not bypass active-account, relationship, object-owner, lifecycle, or hidden-resource denials. |
| Provider-verified email required | Relationship mutations and private-message writes where current source uses `require_verified_user`: checkout payment creation; game join/leave/guest/cancel/host-edit flows; community publish and detail host-edit; game chat creation; chat message create; Need-a-Sub post create/update/cancel; Need-a-Sub request create/accept/decline/cancel/no-show; Need-a-Sub chat ensure/message create | Positive proof must use verified current users with the right relationship. Negative proof must show unverified active users are rejected before relationship mutation or provider side effects. |
| Active-admin broad branches | Admin-capable branches inside booking, participant, waitlist, checkout status, community publish-attempt, chat-message, and Need-a-Sub history services | C proves ordinary users cannot enter these branches. D owns final active-admin breadth, minimum-necessary admin data, and high-risk/admin closure. |

If Gate B finds a C-owned relationship mutation that bypasses provider-verified
email contrary to approved authority, or a public read that returns private
relationship-only fields, Gate B must stop for Gate A correction.

### 7.3 Public Visibility, Relationship Concealment, And Private Cache Contract

Gate B must distinguish public catalog visibility from relationship visibility:

- public browse/list routes return only visible, published, active, non-deleted,
  joinable or listable records under current source rules;
- public detail routes return hidden or inactive records only when current
  source allows the current user's host, active participant, booking buyer,
  waitlist, owner, confirmed-requester, or admin relationship;
- hidden game roster access is narrower than hidden game detail access and must
  follow current source;
- public Need-a-Sub responses exclude owner-only/manage fields and exact private
  owner/manage state unless the current user has private access;
- public game/venue image reads expose only active/public image rows;
- public venue reads expose only active venues;
- hidden game detail, hidden community-game detail, My Games, and any other
  relationship-visible private response class must assert the current required
  cache/privacy header, including `Cache-Control: private, no-store` where the
  source sets it.

Concealment must use current source behavior. If the service intentionally
returns `404` for hidden or foreign resources, Gate B must assert `404`; if it
returns `403` for a relationship mismatch, Gate B must assert `403` and pair
the result with a no-side-effect check for mutations.

### 7.4 Complete Finite State And Lifecycle Classification

Gate B may use parametrized representative tests when equivalent states truly
share the same behavior, but it must first enumerate the authoritative value set
from current models/services and classify every relevant value completely and
mutually exclusively as allowed, denied, concealed, public-only, relationship-
only, not applicable, or later-owner.

The classification must include at least:

- account state and verified-email state from accepted WS03 identity/account
  authority, including suspended, deleted, revoked, disabled, inactive, and
  unverified states where current predecessor evidence makes them relevant;
- game `game_type` (`official`, `community`), `publish_status` (`draft`,
  `published`, `archived`), `game_status` (`active`, `completed`, `cancelled`,
  `expired`, `removed`), `public_visibility_status` (`visible`, `hidden`), and
  `join_enforcement_status` (`open`, `paused`);
- booking `booking_status` (`pending_payment`, `confirmed`, `waitlisted`,
  `partially_cancelled`, `cancelled`, `expired`, `failed`) and `payment_status`
  (`not_required`, `unpaid`, `requires_action`, `processing`, `paid`, `failed`,
  `partially_refunded`, `refunded`, `credit_restored`, `disputed`);
- participant `participant_type` (`registered_user`, `guest`, `host`,
  `admin_added`), `participant_status` (`pending_payment`, `confirmed`,
  `waitlisted`, `cancelled`, `late_cancelled`, `removed`, `refunded`),
  `attendance_status` (`unknown`, `attended`, `no_show`, `excused_absence`,
  `not_applicable`), and `cancellation_type` (`none`, `on_time`, `late`,
  `host_cancelled`, `admin_cancelled`, `payment_failed`);
- waitlist `waitlist_status` (`active`, `promoted`, `accepted`, `declined`,
  `expired`, `cancelled`, `removed`, `payment_processing`, `payment_failed`);
- game chat and Need-a-Sub chat `chat_status` (`active`, `closed`);
- chat message and Need-a-Sub chat message `visibility_status` (`visible`,
  `removed`) and `review_status` (`clear`, `needs_review`, `reviewed`);
- community detail `payment_text_moderation_status` (`visible`, `hidden`);
- community publish attempt `attempt_status` (`requires_payment_method`,
  `requires_action`, `processing`, `succeeded`, `failed`, `cancelled`,
  `expired`);
- venue `venue_status` (`pending_review`, `approved`, `rejected`, `inactive`)
  plus `is_active` and `deleted_at`;
- venue image `image_status` (`pending_upload`, `active`, `hidden`, `removed`)
  and game image `image_status` (`active`, `hidden`, `removed`);
- Need-a-Sub post `post_status` (`active`, `completed`, `cancelled`,
  `expired`, `removed`) and `public_visibility_status` (`visible`, `hidden`);
- Need-a-Sub request `request_status` (`pending`, `confirmed`, `declined`,
  `sub_waitlist`, `canceled_by_player`, `canceled_by_owner`,
  `no_show_reported`, `expired`, `closed_by_admin`);
- stale relationship states such as expired promotions, canceled bookings,
  removed participants, removed messages, closed chats, closed-by-admin
  requests, deleted images/venues, and historical status rows;
- time-window authorization such as start/end/expires/promotion windows using
  controlled or frozen application time rather than uncontrolled wall clock
  comparisons.

### 7.5 Current Relationship Read Contract

C-owned read scoping is based on source-owned relationships:

| Surface | Relationship that grants ordinary-user access |
| --- | --- |
| Bookings | `Booking.buyer_user_id == current_user.id`, unless D-owned active-admin branch. |
| Checkout status | Booking buyer, unless D-owned active-admin branch. |
| Game participants | `GameParticipant.user_id == current_user.id` or current source guest/host relationship, unless D-owned active-admin branch. |
| Waitlist entries | `WaitlistEntry.user_id == current_user.id`, unless D-owned active-admin branch. |
| My Games | Current user's hosted, participant, booking, waitlist, or connected Need-a-Sub relationships according to current service rules. |
| Community-game host edit/detail | Game host. |
| Community publish attempt | Attempt host, unless D-owned active-admin branch. |
| Game chat/read-state/messages | Source-defined game chat member: host or active/eligible participant. |
| Need-a-Sub owner views/history | `SubPost.owner_user_id == current_user.id`, unless D-owned active-admin branch. |
| Need-a-Sub requester views/history | `SubPostRequest.requester_user_id == current_user.id`, or owning post owner for request review/history, unless D-owned active-admin branch. |
| Need-a-Sub scoped chat | Post owner or current confirmed requester while the chat lifecycle remains open. |

Gate B must prove representative list, object, status-history, and read-state
routes cannot be widened by passing another user's IDs or object IDs.

### 7.6 Mutation, Provider-Ordering, And Rejected-Side-Effect Contract

Gate B must identify the concrete protected effects for each rejected mutation
class. A rejected request must leave the named state unchanged and, where a
provider fake is installed, must prove local authorization failed before any
provider call.

| Mutation class | Required authorization/state contract | Protected effects that rejected attempts must not change |
| --- | --- | --- |
| Checkout payment-intent creation | Current verified non-host user, visible/open/joinable game, eligible player/account state, no duplicate active participant/waitlist state, B-owned saved-card ownership compatibility. | No new/changed `bookings`, `payments`, `payment_events`, `game_participants`, `waitlist_entries`, game-credit usage rows, capacity counters, promotion rows, or Stripe/provider fake calls. |
| Join game / waitlist | Current verified user, visible/open/joinable game, not host, profile/age eligibility, capacity or waitlist state, no duplicate active participant/waitlist. | No new/changed booking, participant, waitlist, guest, payment, credit, capacity, notification, or provider state for any user. |
| Leave game | Current user must have active participant/booking/waitlist state for that game; host cannot leave through player flow. | No foreign participant/booking/waitlist cancellation, roster-order change, refund/payment state change, capacity/promotion change, notification, or provider call. |
| Booking guests | Current user must have an active relationship to their own booking/participant. | No foreign booking guest count, guest participant row, participant count, capacity, payment total, or notification change. |
| Host guests | Current user must be the game host. | No guest row, host guest count, capacity, roster, notification, or payment/provider change for a non-host attempt. |
| Host cancel/edit | Current verified host, current game state/window, and community-game ownership. | No game status/detail/visibility/field change, participant/waitlist cancellation, refund/payment/provider change, notification, or host-owned text change for non-host or stale-state attempts. |
| Community publish/detail host-edit | Current verified host, allowed game/publish state, and accepted host-payment rules. | No community publish attempt, payment row, created game, community detail, hidden payment text, notification, or provider call for wrong-host/stale/unverified attempts. |
| Game chat/message/read-state | Source-defined game membership and active chat/message visibility. | No chat creation, message row, sender field, read-state row, message counters, review/moderation fields, notification, or provider/network side effect for nonmembers or spoofed senders. |
| Need-a-Sub post/request/chat | Owner/requester/confirmed-member relationship, active lifecycle state, source-defined time windows. | No post status/detail, request status/history, position fill count, chat creation, message row, read-state row, notification, or admin/moderation field change for unrelated, stale, wrong-role, or spoofed-user attempts. |

### 7.7 Field And Mass-Assignment Boundary

Gate B must identify every C-owned write surface where caller-controlled input
could affect identity, ownership, relationship state, payment/provider identity,
moderation state, visibility, read-state, or admin/server-controlled fields.
The frozen field contract is:

| Write surface | Caller-controlled fields | Server-controlled fields that must not be caller writable |
| --- | --- | --- |
| `POST /checkout/games/{game_id}/payment-intent` | path `game_id`, checkout body fields accepted by current schema, saved payment method reference where supported | payer user, booking buyer, participant user, waitlist user, payment owner, provider customer/payment identity, game host, payment/refund lifecycle fields |
| `POST /games/{game_id}/join`; `POST /games/{game_id}/leave` | path `game_id`, current schema body fields if any | participant user, booking buyer, waitlist user, roster order, payment state, host identity, other users' guests |
| `POST /games/{game_id}/booking-guests/add`; `POST /games/{game_id}/guests/add`; `POST /games/{game_id}/guests/remove` | path `game_id`, guest count/body fields allowed by current schema | booking owner, guest owner, participant owner, host identity, other users' guest rows |
| `POST /games/{game_id}/cancel`; `PATCH /games/{game_id}/host-edit` | path `game_id`, host-edit/cancel fields allowed by current schema | host user, game type, status/lifecycle fields outside host authority, admin moderation fields, payment/refund/provider state |
| `POST /community-games/publish`; `GET /community-games/publish-attempts/{attempt_id}` | publish payload and attempt id | host user, publish attempt owner, payment provider/customer, admin review fields, settlement/reconciliation state |
| `PUT /community-game-details/games/{game_id}/host-edit` | host detail/payment-method fields accepted by schema | host user, game owner, hidden payment moderation fields, admin review state, unrelated game detail rows |
| `POST /game-chats/for-game/{game_id}`; `POST /game-chats/{game_chat_id}/read`; chat message routes | path IDs and message body | sender user, acting user, read-state user, chat owner, visibility/moderation/admin fields |
| Need-a-Sub post/request/chat writes | path IDs, post/request/chat bodies, reason fields | owner user, requester user, post status outside source lifecycle, request status outside allowed transitions, history actor/source, position owner, sender user, read-state user, notification recipients, admin/moderation fields |

Read-only C routes are not mass-assignment surfaces. Their query filters and
path IDs must still be tested for access widening where this plan calls them
out.

### 7.8 IAM-017 Relationship And High-Risk Dimensions

For C, `IAM-017` applies only to relationship mutations that can create or
change a spot, payment attempt, host-published game, game visibility/detail,
roster row, guest row, chat message, Need-a-Sub post/request, or similar
ordinary-user state.

| Mutation/action class | C establishes | Remaining outside C |
| --- | --- | --- |
| Checkout payment-intent creation | Action-specific relationship permission, verified-user requirement, non-host check, game state/capacity checks, B saved-card compatibility, and no provider call after authorization denial. | Durable Stripe/webhook/provider reconciliation, provider idempotency depth, refunds, disputes, and production runtime proof remain WS05/WS10. |
| Join/leave/waitlist/guest flows | Player/host relationship permission, duplicate prevention, current-state checks, controlled-time lifecycle windows, persisted own-row effects, and rejected no-side-effect behavior. | Genuine concurrent database race closure and durable payment/refund audit remain WS04/WS05/D/WS10. |
| Host cancel/edit/community detail/publish | Host ownership, verified-user requirement, source-defined state/window checks, public concealment, and no local publish/provider side effect after denial. | Final admin moderation, high-risk host/admin overrides, minimum-necessary admin data, and provider reconciliation remain D/WS03-05/WS05/WS09. |
| Game chat/message/read state | Game membership permission, sender/read-state current-user derivation, closed/removed lifecycle denial, and nonmember no-side-effect behavior. | Admin message review, export, unmask, retention, and audit remain D/WS09. |
| Need-a-Sub post/request/chat lifecycle | Owner/requester/confirmed-member permission, verified-user write requirement, source-defined time/state checks, sender/read-state derivation, and rejected no-side-effect behavior. | Admin removal/moderation closeout, sensitive audit, and final high-risk policy remain D/WS03-05/WS09. |

If Gate B finds a relationship mutation that needs a new recent-auth,
confirmation, idempotency, current-state, or audit policy decision beyond this
plan, Gate B must stop for Gate A correction.

### 7.9 Requirement And Evidence Contract

Gate B must create a new requirement declaration and trusted workflow scope.
Every pytest test in the scope must use stable `@pytest.mark.requirement(...)`
markers for the requirements it actually proves. `WS03-04C-R12` is
deferred/governance and must have zero pytest mappings.

The Gate B testing record must use the testing-record template and explain the
actual local proof, relationship contracts, lifecycle-state classification,
negative proof, side-effect assertions, field boundaries, and downstream
owner limits. It must not call local source/pytest/provider-fake evidence live,
deployed, production, real-world, or provider-runtime proof.

## 8. Implementation Scope

### Gate B Editable File Set

Gate B may edit exactly:

```text
backend/tests/support/requirements/ws03_04c.json
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_matrix_scope_and_dependencies_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_public_visibility_and_private_cache_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_current_relationship_reads_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_game_roster_checkout_host_mutations_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_community_publish_detail_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_game_chat_message_membership_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_need_a_sub_relationship_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_field_assignment_and_default_deny_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

No production source file is included in the Gate B editable set. If Gate B
requires a production source edit, a matrix edit, a migration, a frontend edit,
or another implementation/evidence file to complete C honestly, Gate B must
stop and return for Gate A correction.

### Exact Expected Final Changed-File Set

The expected final changed-file set after C completes and before Gate D
publication is exactly:

```text
docs/production-readiness/planning/passes/ws03/ws03-04c-game-community-roster-chat-need-a-sub-relationship-authorization.md
backend/tests/support/requirements/ws03_04c.json
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_matrix_scope_and_dependencies_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_public_visibility_and_private_cache_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_current_relationship_reads_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_game_roster_checkout_host_mutations_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_community_publish_detail_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_game_chat_message_membership_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_need_a_sub_relationship_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_field_assignment_and_default_deny_contract.py
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

The approved Stage 0 intake and accepted `WS03-04A`/`WS03-04B` artifacts are
current `develop` inputs for C and are not Gate B-editable files.

## 9. Implementation Impact And Compatibility Review

| Area | Impact decision |
| --- | --- |
| FastAPI route table | Read-only input. Gate B must compare C route keys to the accepted matrix and fail on drift. |
| Route modules | Read-only source proof: booking, checkout, game, community detail/publish, game chat/message, My Games, Need-a-Sub post/request/status/chat, participant, waitlist, venue, venue-image, and game-image routes. |
| Auth service | Read-only compatibility proof for public/optional auth, `get_current_app_user`, `require_active_user`, `require_verified_user`, active-admin branches, and the verified-email distinction. |
| Domain services | Read-only source proof for booking, checkout, game, roster, guest, community-game publish/detail, game chat/message, My Games, Need-a-Sub post/request/chat/lifecycle, public game image, venue image, venue, participant, and waitlist services. |
| Models | Read-only fixtures over the relationship, lifecycle, payment-attempt, chat, image, venue, and Need-a-Sub models named in this plan. |
| Schemas/OpenAPI | Read-only compatibility with accepted response-minimization and request-ownership contracts; no response model changes planned. |
| Frontend callers | Read-only compatibility. Current callers under Browse/Game Details/Create Game/My Games/Need-a-Sub should continue to receive the same API shapes. |
| Request/response compatibility | No API contract changes planned. Gate B tests assert behavior through existing API/service contracts. |
| Settings and environment | No configuration changes. Tests use existing local test settings and sanitized environment-variable references. |
| Provider/network calls | No live provider calls. Stripe, Firebase, R2, and other provider side effects are faked only where needed to prove local authorization ordering. |
| Database/schema/migrations | No model or migration changes planned. Tests use the dedicated local test database and existing cleanup inventory. |
| Existing trusted tests | Gate B validation includes the C focused scope plus A/B compatibility and affected predecessor/compatibility scopes named below. |
| Execution register | Gate B updates the register with the proposed C accepted state that becomes true only when the substantive C PR merges into `develop`. |
| Local handoff/docs | Ignored local handoff files are local-only state. They must never be committed and never override tracked authority. |

## 10. Testing And Evidence Architecture

Gate B must keep one workflow scope but split trusted pytest evidence into
cohesive files because the C surface crosses endpoint families, read and
mutation behavior, public/private visibility, payment-adjacent side effects,
chat membership, and Need-a-Sub lifecycle contracts.

| Test file | Primary proof groups |
| --- | --- |
| `test_matrix_scope_and_dependencies_contract.py` | Matrix inventory, current FastAPI route drift, owner/negative-proof owner checks, dependency classification, accepted A/B compatibility inputs, and `R12` zero pytest mapping. |
| `test_public_visibility_and_private_cache_contract.py` | Public game/community/venue/image/Need-a-Sub visibility, hidden/inactive/removed/deleted concealment, public response minimization, and private cache/privacy headers for hidden relationship-visible responses and My Games. |
| `test_current_relationship_reads_contract.py` | Current-user scoping for bookings, checkout status, participant rows, waitlist entries, My Games, Need-a-Sub mine/request/history reads, wrong-user IDs, and admin-branch separation for ordinary users. |
| `test_game_roster_checkout_host_mutations_contract.py` | Checkout payment-intent, join, leave, guest, cancel, host-edit, capacity, stale lifecycle, host/player role separation, persisted own effects, and rejected no-side-effect/provider-ordering proof. |
| `test_community_publish_detail_contract.py` | Community publish, publish-attempt status, detail host-edit, hidden payment text, host ownership, publish lifecycle, and no local provider side effect after denial. |
| `test_game_chat_message_membership_contract.py` | Game chat ensure/read/read-state/messages, current-user sender/read-state derivation, nonmember denial, hidden/removed messages, closed chat states, and admin moderation boundary. |
| `test_need_a_sub_relationship_contract.py` | Need-a-Sub public post visibility, owner post lifecycle, requester lifecycle, owner/requester status-history, confirmed-only scoped chat, sender/read-state derivation, and time-window/lifecycle classifications. |
| `test_field_assignment_and_default_deny_contract.py` | Cross-cutting caller-controlled field attempts, `401`/`403`/`404` classes, protected field overwrite/rejection, and named prohibited side effects for representative rejected mutations. |

The test files may share fixtures and helpers inside the same workflow package
only when they remain in the exact Gate B editable file set. Helper logic must
serve the C evidence scope and must not import from historical archived tests.

Gate B must also create:

```text
backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/TESTING_RECORD.md
```

The testing record must be reviewer-facing and must explain what proof actually
ran. It must distinguish local source inspection, local pytest evidence,
provider fakes, compatibility tests, and checker/traceability results.

## 11. Validation Strategy

Gate B must run this validation set after implementation, using sanitized
environment-variable references rather than literal credential values:

```text
git status -sb --untracked-files=all
LC_ALL=C shasum -a 256 docs/production-readiness/planning/passes/ws03/ws03-04-intake.md
LC_ALL=C shasum -a 256 docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md
backend/.venv/bin/python -m py_compile backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_matrix_scope_and_dependencies_contract.py backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_public_visibility_and_private_cache_contract.py backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_current_relationship_reads_contract.py backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_game_roster_checkout_host_mutations_contract.py backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_community_publish_detail_contract.py backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_game_chat_message_membership_contract.py backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_need_a_sub_relationship_contract.py backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization/test_field_assignment_and_default_deny_contract.py
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest backend/tests/workflows/authorization_matrix_foundation
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest backend/tests/workflows/self_owned_account_notification_financial_authorization
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest backend/tests/workflows/identity_authority backend/tests/workflows/account_lifecycle_concurrency backend/tests/workflows/recent_auth_step_up backend/tests/workflows/provider_payment_input_ownership backend/tests/workflows/request_ownership backend/tests/workflows/response_minimization backend/tests/platform/chat_rate_limits
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
git diff --check
git status --short --untracked-files=all
git diff --cached --name-only
```

Validation expectations:

- the approved intake SHA remains
  `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`;
- the accepted A plan SHA remains
  `ff0a00b158408148c9f91c6087f66d409389f28f8006c32e658ab9dd6f0784b4`;
- the C focused pytest scope passes;
- the A matrix scope still passes, proving route keys and owner allocations did
  not drift;
- the B self-owned authorization scope still passes as accepted sibling
  compatibility evidence;
- affected trusted predecessor scopes pass for identity, account lifecycle,
  recent-auth, provider-payment input ownership, request ownership, response
  minimization, and chat rate limits;
- checker domain and suite compliance pass;
- `git diff --check` passes;
- `git diff --cached --name-only` is empty;
- actual changed files equal the expected final changed-file set.

## 12. Register Update Contract

Gate B must update the execution register with the proposed C accepted state
that becomes true only when the substantive C PR merges into `develop`. Human
Gate B or Gate C approval does not by itself make C accepted.

The register update must:

- add `WS03-04C` to accepted executable passes, with this plan path,
  requirement declaration `ws03_04c.json`, total requirements `12`, required
  `11`, blocked `0`, deferred `1`, and scope
  `workflows/game_community_roster_chat_need_a_sub_relationship_authorization`
  plus governance;
- keep the approved graph `WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D`;
- record A, B, and C as accepted only after the substantive C merge;
- record `WS03-04D` as remaining;
- keep parent `WS03-04` incomplete after C because final admin/high-risk review
  and parent-gap disposition are not closed by this child;
- avoid stating or implying that C becomes accepted before merge.

## 13. Not Part Of This Pass

- No B-owned self-account, notification, inbox, saved-card, credit, payment,
  refund, or host-publish-fee authorization redesign.
- No D-owned final admin route/list/high-risk review, minimum-necessary admin
  data proof, sensitive export/unmask/read-audit policy, or final parent-gap
  disposition.
- No live Stripe, Firebase, R2, deployed runtime, provider dashboard,
  production, or external evidence.
- No Stripe webhook, durable payment/refund/credit reconciliation, durable job
  proof, provider repair workflow, or live provider recovery proof.
- No genuine database-concurrency proof, schema change, or migration.
- No frontend UI changes, browser/e2e proof, or Playwright proof.
- No moderation closeout beyond proving C-owned public visibility and hidden
  text/resource concealment in current source.
- No additional documentation cleanup.

## 14. Related Controls And Remaining Evidence

| Control / owner | C establishes | Remaining after C |
| --- | --- | --- |
| `IAM-012` | Current route inventory, dependency classification, owner allocation, and drift proof for C-owned route keys. | Final parent matrix disposition and D-owned admin/high-risk route closure. |
| `IAM-013` | Current-user relationship authorization for C-owned ordinary game/community/roster/chat/Need-a-Sub reads and mutations. | Admin broad access and high-risk exception review in D. |
| `IAM-015` | Public/private response scoping, hidden-resource concealment, private cache/privacy headers, and ordinary-user data-minimization boundaries for C routes. | Minimum-necessary admin data, sensitive export/unmask/read-audit, and broader audit policy in D/WS09. |
| C portion of `IAM-017` | Relationship mutation permission, verified-user distinction, current-state/lifecycle checks, field boundaries, rejected side effects, and local provider-call ordering. | Recent-auth/admin confirmation where not in current C source, provider idempotency/reconciliation, true concurrency, runtime/provider evidence, and final high-risk closure. |
| `WS03-04D` | Not owned by C. | Admin route/list/high-risk authorization, active-admin breadth review across service exceptions, minimum-necessary admin data, sensitive access policy, and final parent-gap disposition. |
| `WS05` | Not owned by C. | Stripe webhook/payment/refund/credit durable lifecycle and provider reconciliation proof, including the accepted A matrix `/stripe/webhook` gap. |
| `WS04` | Not owned by C. | Genuine database-concurrency closure where booking, roster, payment, waitlist, and Need-a-Sub lifecycle operations need race proof beyond serial local behavior. |
| `WS03-05` | C proves only C-owned public concealment and hidden text/resource behavior. | Moderation states, safe notices, minimum-necessary moderation/admin data, and moderation lifecycle policy. |
| `WS09`/`WS10` | Not owned by C. | Audit, sensitive access, runtime/provider governance, operational evidence, recovery, and provider-access evidence. |

## 15. Stop And Correction Boundaries

Gate B must stop and return for Gate A correction if any of these occur:

- the approved intake SHA changes;
- the accepted A plan SHA changes;
- current accepted source no longer matches the baseline and prerequisite state
  frozen in this plan;
- the current route table or accepted A matrix no longer has exactly the C route
  inventory listed in this plan;
- an A matrix drift check fails because route owner, negative-proof owner, or
  route keys changed;
- any production source file must be modified to satisfy a C requirement;
- `authorization_matrix.json` must be modified;
- any file outside the exact Gate B editable file set is required for C
  evidence;
- ordinary-user and admin behavior cannot be separated without redesigning C/D
  ownership;
- a live/deployed/provider/runtime proof is needed for acceptance;
- a migration or database-concurrency design is required;
- a test needs historical archived tests as current evidence;
- validation cannot pass without changing this plan.

The run must return to Stage 0 only if the approved intake/decomposition, C/D
ownership boundary, or child dependency graph is wrong. Additional C evidence
files, corrected validation design, or a newly discovered C source defect are
Gate A correction issues, not Stage 0 redesigns.

## 16. Completion Criteria

Gate B is complete only when all of the following are true:

- `backend/tests/support/requirements/ws03_04c.json` declares `R1` through
  `R11` as required and `R12` as deferred/governance with zero pytest mappings;
- the split focused pytest files prove the C route inventory, dependency and
  verified-email classification, complete lifecycle-state classification,
  public/relationship visibility, private cache/privacy headers, relationship
  read scoping, game roster/checkout/guest/cancel/host-edit authorization,
  community publish/detail authorization, game chat/message authorization,
  Need-a-Sub post/request/chat authorization, field and mass-assignment
  boundaries, `401`/`403`/`404` denial classes, rejected-mutation side effects,
  IAM-017 relationship dimensions, and downstream admin/provider/runtime
  boundaries described in this plan;
- the testing record explains the actual local proof and remaining boundaries
  in ordinary engineering language;
- the execution register contains the proposed accepted C state and remaining
  `WS03-04D` parent state that becomes true only on merge;
- all validation commands in this plan pass;
- the actual changed-file set equals the expected final changed-file set;
- nothing is staged before Gate C/human review;
- no Gate C, Gate D, commit, push, PR update, merge, deployment, provider call,
  migration, or production behavior implementation has occurred during Gate B.

## 17. Document Self-Review

Gate A self-review confirms:

- this plan uses current accepted baseline
  `ffdfc6d744f88879b86d0a91bab83770d7540062`;
- the approved intake and accepted A plan SHAs remain valid;
- the original C boundary remains valid and no Stage 0 issue was found;
- B is described as an accepted sibling compatibility input, not a C technical
  prerequisite;
- the exact Gate B editable file set and expected final changed-file set exclude
  stale documentation-cleanup files and include only C plan/evidence/register
  files;
- validation commands use sanitized environment-variable references and contain
  no literal credential-bearing URLs;
- the test architecture is split into cohesive files inside one workflow scope;
- lifecycle, cache/privacy, field-boundary, and rejected-side-effect proof
  obligations are explicit enough for Gate B to execute without redesign;
- this plan contains no literal credentials, credential-bearing service URLs,
  private keys, tokens, provider-private values, personal/payment data, raw
  sensitive logs, local absolute paths, local usernames, session-only state, or
  internal chat material.

## 18. Gate A Stop Boundary

Gate A created only this canonical plan for WS03-04C. Gate A did not implement
Gate B evidence, edit the frozen intake, edit accepted `WS03-04A` or
`WS03-04B` artifacts, change production source, stage files, commit, push,
create or update a PR, merge, or begin Gate B.
