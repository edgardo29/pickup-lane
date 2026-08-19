# Production-Readiness Pass Plan: WS03-04B - Self-Owned Account, Notification, And Financial Record Authorization

## At A Glance

| Field | Value |
| --- | --- |
| Parent pass | `WS03-04 - Complete authorization matrix and negative proof` |
| Executable child | `WS03-04B - Self-owned account, notification, and financial record authorization` |
| Gate | Gate A - executable-pass design only |
| Current branch | `pr/WS03-04B` |
| Accepted develop baseline | `0e2d590e59898850c9bbbcbd0e0f7b4eafbecabc` |
| Approved intake | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` |
| Approved intake SHA-256 | `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4` |
| Accepted prerequisite child | `WS03-04A - Authorization matrix foundation and route drift guard` |
| Accepted WS03-04A plan SHA-256 | `ff0a00b158408148c9f91c6087f66d409389f28f8006c32e658ab9dd6f0784b4` |
| Approved dependency graph | `WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D` |
| B-owned route families | `11` |
| B-owned route keys | `28` |
| Planned requirement declaration | `backend/tests/support/requirements/ws03_04b.json` |
| Planned trusted evidence scope | `backend/tests/workflows/self_owned_account_notification_financial_authorization` |
| Planned production source edits | None required by Gate A reconciliation. Gate B is planned as trusted evidence, requirement declaration, and register update over current accepted source. |
| Gate B stop condition if source defect appears | Stop and return to Gate A correction before changing production source. |

## Executable Pass Identity And Intake

`WS03-04B` is the second executable child selected by the approved `WS03-04`
Stage 0 intake. It is eligible for Gate A because the corrected pass branch
`pr/WS03-04B` was created from accepted `develop` baseline
`0e2d590e59898850c9bbbcbd0e0f7b4eafbecabc`, and the current execution register
records `WS03-04A` as accepted with `WS03-04B`, `WS03-04C`, and `WS03-04D`
remaining.

The approved child graph remains unchanged:

```text
WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D
```

`WS03-04B` may proceed after `WS03-04A` without waiting for `WS03-04C`.
`WS03-04D` remains after both B and C because it owns final admin/high-risk
review and parent-gap disposition. This plan does not redesign the parent
decomposition, does not absorb relationship-workflow authorization from
`WS03-04C`, and does not absorb admin/high-risk authorization closure from
`WS03-04D`.

## 1. Purpose

This pass closes the ordinary-user authorization proof for the self-owned
account, notification, inbox, saved-card, credit, payment, refund, and
host-publish-fee route families allocated to `WS03-04B` by the accepted
`WS03-04A` authorization matrix.

The planned Gate B work proves that a signed-in ordinary user can read or mutate
only the records that current source binds to that user, that request-supplied
IDs and filters cannot widen ordinary-user access, and that denied requests do
not mutate another user's account, read state, saved cards, credits, payments,
refunds, or host-publish-fee records.

## 2. Authority Read

| Source | Gate A use |
| --- | --- |
| `docs/production-readiness/00-READ-ME-FIRST.md` | Authority order, current `develop` truth, frozen artifact rules, excluded-test rule, and stop boundaries. |
| `docs/production-readiness/01-PROGRAM-CONTEXT.md` | WS03 current-pass workflow, accepted-source model, later-child planning rule, execution-register requirement, and evidence language. |
| `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` | Gate A responsibilities, repository-wide impact scan, exact Gate B file-set rules, validation, SHA reporting, and stop conditions. |
| `docs/production-readiness/planning/templates/PASS-PLANNING-TEMPLATE.md` | Canonical plan structure and required design detail. |
| `docs/production-readiness/planning/templates/TESTING-RECORD-TEMPLATE.md` | Gate B testing-record structure and adequacy language. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | Current accepted prerequisites, `WS03-04A` accepted state, and remaining B/C/D parent state. |
| `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` | Frozen parent decomposition, B scope, B/C independence, D handoff, and no-gap/no-overlap allocation. |
| `docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md` | Accepted matrix schema, owner vocabulary, route drift guard, and later-child handoff rules. |
| `backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json` | Current accepted route-family allocation, B route inventory, auth dependencies, policy dimensions, and source references. |
| `backend/tests/workflows/authorization_matrix_foundation/TESTING_RECORD.md` | Accepted A evidence boundary and downstream B handoff. |
| `backend/tests/support/requirements/ws03_04a.json` | Accepted A requirement states and deferred behavioral-closure boundary. |
| Master blueprint and final remediation plan | Parent controls `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, and `IAM-017`; WS03-04 maximum scope, proof before acceptance, and stop conditions. |
| Accepted WS03 predecessor evidence | `WS03-01` identity authority, `WS03-02` account lifecycle, `WS03-03A` recent-auth, and `WS03-03B` App Check boundaries. |
| Accepted cross-workstream evidence | `WS02-04B2A2B2` provider-payment input ownership and inbox seen-token evidence; `WS02-05B2` response minimization evidence. |
| Approved verified-email policy | Accepted `WS03-01` policy from `IDB-03`: verified email is required for hosting, joining, booking, checkout payment creation, Need-a-Sub interactions, private messages, elevated privileges, and admin actions; it is not required for limited account/profile setup or current read/status/private-history surfaces. Saved-card setup/default/detach policy is owned by payment/recent-auth scopes, not silently absorbed by `WS03-01`. |
| Repository standards | Backend ownership, backend test structure, application testing standards, database rules, frontend caller ownership, auth, profile, inbox, notifications, payment methods, game credits, and Stripe notes. |
| Current production source | B-owned route modules, services, schemas, models, frontend callers, and registered FastAPI route table. |

## 3. Frozen Inputs And Prerequisite Verdict

| Check | Result |
| --- | --- |
| Corrected branch and accepted baseline | Pass. `pr/WS03-04B` was created from accepted `develop` baseline `0e2d590e59898850c9bbbcbd0e0f7b4eafbecabc`; current branch `HEAD`, local `develop`, `origin/develop`, and merge-base resolve to that baseline. |
| Approved intake SHA | Pass. `ws03-04-intake.md` hashes to `e8dd5cda0aad2325df5c25d7d80f0e01a4849a9a1de205e91f0ac8d919869eb4`. |
| `WS03-04A` accepted in current `develop` | Pass. The execution register includes `WS03-04A`; the accepted plan and matrix artifacts are present. |
| `WS03-04A` plan SHA | Pass. The current plan hashes to `ff0a00b158408148c9f91c6087f66d409389f28f8006c32e658ab9dd6f0784b4`. |
| B/C ordering | Pass. The intake and register do not impose a B -> C or C -> B dependency. |
| B route inventory from accepted matrix | Pass. `WS03-04B` owns `11` route families and `28` route keys. |
| A matrix blockers affecting B | Pass. No `blocked` B owner or `blocked_owner_decision` gap is present. |
| Current Gate A editable scope | Pass. Only this canonical plan may be created. |

Prerequisite verdict: `WS03-04B` is eligible for Gate A design.

## 4. Gate A Outcome

Outcome: `READY FOR GATE B AFTER HUMAN APPROVAL`.

Gate B is designed as an evidence and register pass over current accepted source.
Gate A reconciliation found no current production-source correction required for
the B-owned verified-email, default-deny, write-field, or IAM-017 contract. If
Gate B discovers that a production source correction is required to satisfy any
`WS03-04B` requirement, Gate B must stop and return for Gate A correction that
names the needed production file.

Current active-admin broad-read branches visible inside notification, credit,
payment, and refund services are recorded as a `WS03-04D` review boundary, not
a B production correction. B must prove ordinary users cannot reach those
branches and must not claim provider-verified admin closure.

## 5. Requirements

| ID | State | Scope | Controls | Requirement |
| --- | --- | --- | --- | --- |
| `WS03-04B-R1` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-012`, `IAM-013`, `IAM-015`, `WS03-04A` | Gate B must consume the accepted `WS03-04A` matrix and prove the `WS03-04B` route inventory remains exactly the current `11` B-owned route families and `28` B-owned route keys, with no B/C/D ownership overlap and no unclassified B route drift. |
| `WS03-04B-R2` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-012`, `IAM-013`, `IAM-017`, `WS03-01`, `WS03-02`, `WS03-03A` | Current-account routes must bind reads and mutations to the authenticated local user derived from the Firebase bearer token. `/auth/me`, `/users/me`, `/user-settings/me`, and `/user-stats/me` must not accept a caller-selected target user. `PATCH /users/me` and `PATCH /user-settings/me` must update only the current user's profile/settings fields. `DELETE /auth/account` must act on the token user's account and preserve the recent-auth requirement. |
| `WS03-04B-R3` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-007`, `IAM-012`, `IAM-017`, `WS03-01`, `WS03-02`, `WS03-03A` | Gate B must preserve the accepted dependency distinction between an authenticated existing app user, an active product user, a recent active/current user, and a provider-verified user. Current approved authority does not require provider-verified email for B-owned ordinary self/profile/setup/read/status/history behavior or saved-card management; it does require valid provider token identity, active-account enforcement where current routes require it, recent-auth where current routes require it, and current-user/object ownership. Active-admin broad-read branches visible inside some B service paths remain `WS03-04D` final admin/high-risk review, not B closure. If Gate B finds a B-owned ordinary route action that should require provider-verified email under accepted authority, it must stop for Gate A correction instead of silently changing source. |
| `WS03-04B-R4` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-013`, `IAM-015` | Notification and inbox routes must be current-user scoped. User notification lists/counts must filter by `Notification.user_id == current_user.id`; individual notification reads or read-state mutations for another ordinary user's notification must be denied with the current concealment behavior and no read-state side effect; selected platform notices must require a recipient row for the current user; global-seen updates must require a valid signed token for the current user. |
| `WS03-04B-R5` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-013`, `IAM-017`, `WS02-04B2A2B2`, `WS03-03A` | Saved-card routes must be current-user scoped. Local saved-card IDs must belong to the current user; SetupIntent and Stripe payment-method customer IDs must match the current user's stored Stripe customer before a saved-card row is created or revived; default-card and detach actions must require recent active user authorization and must not touch another user's cards or make provider calls after a wrong-owner local card ID is rejected. |
| `WS03-04B-R6` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-013`, `IAM-015` | Ordinary-user financial reads must not be widenable through query filters or object IDs. Payment reads/lists must remain scoped to `Payment.payer_user_id == current_user.id`; refund reads/lists must remain scoped through the refund's payment payer; game-credit balance/list reads must default to the current user and reject another `user_id` for a non-admin caller; host-publish-fee `/me` reads must return only rows where `HostPublishFee.host_user_id == current_user.id`. |
| `WS03-04B-R7` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-012`, `IAM-016`, `IAM-017` | Admin exceptions visible in current services must not be converted into B closure. B must prove ordinary users cannot gain admin breadth through B routes. Active-admin read breadth, minimum-necessary admin data, admin notification lookup, admin money routes, and final high-risk review remain owned by `WS03-04D` or later named owners. |
| `WS03-04B-R8` | required | `workflows/self_owned_account_notification_financial_authorization` | `IAM-012`, `IAM-013`, `IAM-015`, `TST-005` | Negative proof must cover unauthenticated/invalid-credential `401` behavior, authenticated-but-forbidden `403` behavior, concealed foreign-resource `404` behavior, rejected cross-user object IDs, wrong-user list filters, signed-token user mismatch, saved-card owner mismatch, provider-customer mismatch, stale/missing recent-auth attempts, and caller-controlled field attempts. Rejections must be paired with persisted-state checks showing no prohibited mutation to another user's records. |
| `WS03-04B-R9` | required | `workflows/self_owned_account_notification_financial_authorization` | `GOV-006`, `TST-005`, `WS03-04` | Requirement declarations, pytest requirement markers, test names, and the testing record must be traceable to this plan, the accepted intake, the accepted A matrix, current source, and accepted predecessor repository evidence. They must not use historical archive tests as current evidence. |
| `WS03-04B-R10` | deferred | `governance` | `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`, `PAY-005`, `PAY-006`, `WS04`, `WS05`, `WS09`, `WS10` | Live/deployed/provider proof, Stripe dashboard proof, durable payment/refund reconciliation, genuine database-concurrency closure, admin/high-risk final review, export/unmask/read-audit policy, and `WS03-04C` relationship authorization are outside B. This requirement must have zero local pytest mappings in Gate B. |

The planned requirement declaration is
`backend/tests/support/requirements/ws03_04b.json`. It must declare
`R1` through `R9` as `required` with scope
`workflows/self_owned_account_notification_financial_authorization`, and `R10`
as `deferred` with scope `governance`.

## 6. Technical Design / Contracts

### 6.1 B Route Inventory

Gate B must treat the accepted A matrix as the authoritative B route inventory
unless current source drift makes that matrix stale. The B-owned inventory is:

| Family | Routes | Gate B proof focus |
| --- | --- | --- |
| `self_auth_ws03_04b_ws03_04b` | `DELETE /auth/account`; `GET /auth/me` | Current-token account read/deletion; recent-auth preservation for self-delete; no request-selected target account. |
| `self_users_ws03_04b_ws03_04b` | `GET /users/me`; `PATCH /users/me` | Current-user profile read/update; no target-user substitution; identity/admin/server-owned fields remain outside ordinary self-write authority. |
| `self_user_settings_ws03_04b_ws03_04b` | `GET /user-settings/me`; `PATCH /user-settings/me` | Current-user one-to-one settings read/update; no target-user substitution; only settings fields change. |
| `self_user_stats_ws03_04b_ws03_04b` | `GET /user-stats/me` | Current-user stats read only. |
| `self_notifications_ws03_04b_ws03_04b` | `GET /notifications/me`; `GET /notifications/{notification_id}`; `PATCH /notifications/{notification_id}/read` | Current-user notification list/object/read-state proof; wrong-owner objects concealed and not mutated for ordinary users. |
| `self_inbox_ws03_04b_ws03_04b` | `GET /inbox/app-updates`; `PUT /inbox/app-updates/global-seen`; `PUT /inbox/app-updates/platform-notices/{notice_id}/read`; `GET /inbox/counts`; `GET /inbox/game-activity` | Current-user inbox feeds/counts; selected platform notice recipient check; signed global-seen token user binding; no cross-user read-state mutation. |
| `self_user_payment_methods_ws03_04b_ws03_04b` | `GET /user-payment-methods`; `POST /user-payment-methods/setup-intent`; `POST /user-payment-methods/sync`; `GET /user-payment-methods/{payment_method_id}`; `PATCH /user-payment-methods/{payment_method_id}/default`; `DELETE /user-payment-methods/{payment_method_id}` | Current-user saved-card reads, setup, sync, default, and detach; recent-auth preservation for default/detach; wrong-owner local IDs and wrong-customer provider objects rejected. |
| `self_game_credits_ws03_04b_ws03_04b` | `GET /game-credits`; `GET /game-credits/balance` | Current-user credit list/balance; non-admin `user_id` substitution cannot read another user's credits. |
| `self_payments_ws03_04b_ws03_04b` | `GET /payments`; `GET /payments/{payment_id}` | Ordinary-user payment list/object reads scoped to payer. |
| `self_refunds_ws03_04b_ws03_04b` | `GET /refunds`; `GET /refunds/{refund_id}` | Ordinary-user refund list/object reads scoped through the payment payer. |
| `self_host_publish_fees_ws03_04b_ws03_04b` | `GET /host-publish-fees/me` | Current-user host publish fee list scoped to `host_user_id`. |

Gate B must fail if the current route table contains a B-owned route not listed
above, a listed B route disappears, a listed B route is assigned to another
child without a human-approved Gate A correction, or a route's backend
authorization dependencies drift from the accepted matrix.

### 6.2 Verified-Email Authorization Contract

Accepted `WS03-01` authority makes current Firebase/provider email
verification required for participation/payment/admin actions such as hosting,
joining, booking, checkout payment creation, Need-a-Sub interactions, private
messages, elevated privileges, and admin actions. It also explicitly permits
unverified users to complete limited account/profile setup and use current
read/status/private-history surfaces that are not themselves verified-email
mutation gates.

Current `WS03-04B` ordinary self-owned behavior falls on the permitted side of
that policy. No B-owned ordinary route action is frozen as
provider-verified-email-required in this plan. Every B-owned route still
requires a valid Firebase bearer token and the current local-user/account,
recent-auth, ownership, provider-customer, and state checks listed below.

| Verified-email classification | B route/action keys | Gate B proof composition |
| --- | --- | --- |
| Unverified authenticated user may use ordinary B behavior when all other current authorization checks pass | All 28 B-owned route keys for current-user/self-owned behavior: `/auth/me`; `/auth/account`; `/users/me`; `/user-settings/me`; `/user-stats/me`; `/notifications/*`; `/inbox/*`; `/user-payment-methods/*`; `/game-credits*`; `/payments*`; `/refunds*`; `/host-publish-fees/me` | Positive proof must exercise representative unverified-provider users across the dependency classes: authenticated-only self/profile read or setup, active-account read/status, recent-auth saved-card/self-delete, and financial read. Matrix/source proof must confirm no B route-level dependency uses `require_verified_user` or `require_active_admin`. |
| Provider-verified email required for B-owned ordinary behavior | None | Negative proof is by boundary: checkout payment creation, relationship mutations, Need-a-Sub interactions, private messages, and admin actions are outside B and remain covered by accepted `WS03-01`, `WS03-04C`, or `WS03-04D` ownership. Gate B must not add a fake B requirement for a route it does not own. |
| Unverified user still denied by non-email authorization | B routes where another check fails: missing/invalid token, deleted/pending account, suspended user on active-account routes, stale recent-auth for self-delete/default/detach, wrong-owner local IDs, wrong provider customer, wrong signed inbox token, or foreign resource | Negative proof must show provider-unverified status does not bypass the real denial reason. For example, an unverified but stale-recent-auth user is denied by recent-auth before self-delete/card side effects; an unverified wrong-owner saved-card request is denied before provider mutation; and an unverified wrong-user inbox token is rejected without read-state changes. |
| Active-admin broad-read branches visible inside B services | `GET /notifications/{notification_id}`; `GET /game-credits`; `GET /game-credits/balance`; `GET /payments`; `GET /payments/{payment_id}`; `GET /refunds`; `GET /refunds/{refund_id}` | B proves ordinary users cannot enter these branches or use them to widen access. Provider-verified admin identity, admin data minimization, and any source correction for these broad-read branches remain `WS03-04D` final admin/high-risk scope. |

Current source is consistent with this B-owned ordinary-behavior
classification: the accepted A matrix shows `get_verified_firebase_identity`
on B routes for credential verification, but no B route-level dependency uses
`require_verified_user`. The A matrix `role_rules` phrase "verified
identity/email" for some B rows is reconciled here as credential/provider
identity verification for B ordinary behavior, not provider-email verification
for those routes. Gate B therefore does not include production source edits
for B ordinary verified-email behavior. If the route table or authority changes
before Gate B and a B-owned ordinary action genuinely requires provider email
verification, Gate B must stop for a Gate A correction that adds the specific
route/source file and proof changes.

### 6.3 Current User And Account-State Contract

Current source distinguishes four user concepts:

| Concept | Current source | B handling |
| --- | --- | --- |
| Authenticated existing app user | `get_current_app_user` through a verified Firebase token and a non-deleted/non-pending local user | Allowed for account/support-style current-user reads and updates where current route authority uses this dependency. |
| Active product user | `require_active_user` or explicit `require_active_account(current_user)` | Required for product actions in B such as inbox, saved-card routes, host-publish-fee `/me`, and payment/refund reads. |
| Recent active/current user | `require_recent_app_user` or `require_recent_active_user` layered with `require_recent_authentication` | Required for self-delete and saved-card default/detach actions. |
| Provider-verified user | `require_verified_user`, which layers active account plus current Firebase email verification | Not required by B-owned ordinary route behavior under current approved authority. Admin broad-read branches remain D-owned and B must not claim them. |

Gate B must test the current distinction rather than collapsing it into one
global rule. Suspended users may still pass the authenticated-user dependency
for limited account/support flows. Deleted and pending-deletion users remain
outside the authenticated current-user boundary under accepted `WS03-02`
evidence.

### 6.4 Default-Deny, Status-Code, And Side-Effect Contract

Gate B must prove denial behavior through representative dependency and service
classes plus the matrix route-coverage guard. It must not create redundant
per-route tests when the same dependency and service class already proves the
behavior honestly.

| Denial class | B surfaces | Expected result and no-side-effect requirement |
| --- | --- | --- |
| Missing, malformed, expired, revoked, wrong-project, disabled, or otherwise invalid Firebase credential | All B routes through `get_verified_firebase_identity` | `401` for authentication failures before any route-owned business mutation. Provider configuration or provider lookup unavailability remains `503` and is not B behavioral closure. |
| Local user missing, deleted, or pending deletion after valid provider identity | All B routes that require a current app user | Current source returns `404 User not found.` through the accepted identity/account pipeline. B may rely on accepted `WS03-02` for exhaustive lifecycle proof and must include matrix/source coverage that B routes still use that pipeline. |
| Suspended or otherwise inactive local account on active-account routes | Inbox, saved cards, payments, refunds, host-publish-fee `/me` | `403 Active account required.` before product or provider side effects. Limited account/profile/support routes intentionally do not collapse into this active-account rule. |
| Stale, missing, malformed, future, or too-old provider `auth_time` | `DELETE /auth/account`; `PATCH /user-payment-methods/{payment_method_id}/default`; `DELETE /user-payment-methods/{payment_method_id}` | `403` with the accepted recent-auth error contract before account deletion, default-card, detach, database, or provider side effects. |
| Ordinary user attempts another user's admin/broad read path | Game-credit `user_id` substitution; payment `payer_user_id` substitution; payment/refund object owned by another payer | `403 Admin access required.` or current service-equivalent forbidden response before records are returned or changed. Active-admin breadth is not B closure. |
| Foreign or unauthorized object is concealed | Notification object/read-state, selected platform notice recipient, saved-card local ID, absent payment/refund rows | `404` where current source intentionally conceals the resource; rejected mutations must leave read-state, saved-card, provider, payment, and refund rows unchanged. |
| Caller-supplied token/customer/input belongs to another user | Inbox global-seen token, Stripe SetupIntent customer, Stripe payment-method customer, existing saved-card row owned by another user | Current source rejects with `400`, `403`, `404`, or `409` according to the existing service contract; Gate B must prove no prohibited row is created, revived, defaulted, detached, or marked read. |

### 6.5 Field And Mass-Assignment Boundary

Gate B must identify every B-owned write surface where caller-controlled input
could affect identity, ownership, account state, privilege, payment/provider
identity, or other server-controlled state. The frozen field contract is:

| Write surface | Caller-controlled fields | Server-controlled fields that must not be caller writable | Gate B proof owner |
| --- | --- | --- | --- |
| `DELETE /auth/account` | `confirmation` must be exactly `DELETE` after trimming | target user id, auth UID, email, role, account status, provider deletion target, support flags, relationship cleanup targets | B proves invalid/extra fields fail and stale recent-auth denial produces no account/provider side effects; accepted `WS03-02` owns account-deletion failure-state depth. |
| `PATCH /users/me` | `phone`, `first_name`, `last_name`, `date_of_birth`, `home_city`, `home_state` | `auth_user_id`, `email`, `email_verified`, `email_verified_at`, `role`, `account_status`, `deleted_at`, provider timestamps, `profile_photo_url`, permissions, ownership, admin/payment/provider/audit state | B proves current-user row targeting and no cross-user target field; accepted `WS03-01` plus current `UserUpdate(extra="forbid")` owns identity-field rejection. |
| `PATCH /user-settings/me` | notification preference booleans, `location_permission_status`, `selected_city`, `selected_state` | `user_id`, account/role/status fields, notification rows, admin flags, provider/payment state | B proves only the current user's settings row changes; current `UserSettingsUpdate(extra="forbid")` supplies schema enforcement for extra fields. |
| `PATCH /notifications/{notification_id}/read` | path `notification_id` only | `user_id`, notification type/category/domain/content, related records, read state for other users | B proves wrong-owner notification is concealed and not marked read. |
| `PUT /inbox/app-updates/global-seen` | signed `seen_token` only | `user_id`, selected notice read rows, notification rows, arbitrary sequence owner, account state | B proves token user binding and no read-state change for wrong-user or invalid token; accepted `WS02-04B2A2B2` owns the signed-token format/source boundary. |
| `PUT /inbox/app-updates/platform-notices/{notice_id}/read` | path `notice_id` only | recipient `user_id`, notice audience, global read state, other recipient read rows | B proves recipient ownership and idempotent current-user read row only. |
| `POST /user-payment-methods/setup-intent` | `set_as_default` only | user id, Stripe customer id, provider setup identity, card identity, method status, defaulting another user's card | B proves current user/customer are server selected; no provider/customer fields are request writable. |
| `POST /user-payment-methods/sync` | `setup_intent_id`, `set_as_default` | user id, Stripe customer id, payment method customer, card fingerprint, method status, defaulting another user's card | B proves provider customer mismatch and existing other-user saved-card collision do not create or revive rows. |
| `PATCH /user-payment-methods/{payment_method_id}/default` | path `payment_method_id` only | user id, Stripe customer id, provider customer, other users' default flags | B proves recent-auth, owner check before provider call, and no wrong-user default changes. |
| `DELETE /user-payment-methods/{payment_method_id}` | path `payment_method_id` only | user id, Stripe customer id, provider customer, other users' method status/default flags | B proves recent-auth, owner check before provider call, idempotent own detach, and no wrong-user detach/default changes. |

Read-only B routes are not mass-assignment surfaces. Their request filters must
still be tested for access widening where this plan calls them out, but they do
not accept bodies that can write identity, ownership, account, privilege,
payment/provider, or audit state.

### 6.6 IAM-017 Self/High-Risk And Financial Mutation Contract

For B, `IAM-017` applies to self-service account deletion, saved-card state
changes, provider-backed saved-card setup/sync, and read-state/account-setting
mutations according to their risk. Gate B must freeze each dimension without
claiming final admin/high-risk closure owned by `WS03-04D`.

| Mutation/action | Action-specific permission | Recent auth | Confirmation | Idempotency | Current-state checks | Auditability / later owner |
| --- | --- | --- | --- | --- | --- | --- |
| `DELETE /auth/account` | B proves the action targets the token user's account only; no request-selected target. | Required by accepted `WS03-03A` and B must preserve denial before side effects. | B proves `confirmation=DELETE` is required. | Accepted `WS03-02` owns pending/unknown provider outcome and repeat-delete boundaries; B proves no other-user side effects. | Accepted `WS03-02` owns deleted/pending/final-admin lifecycle depth; B proves current-user binding. | Accepted `WS03-02` owns support flags/failure tracking; broader audit/governance remains `WS09`/`WS10`. |
| `PATCH /users/me`; `PATCH /user-settings/me` | B proves self-only row targeting. | Not required by approved current policy. | Not applicable; ordinary profile/settings update. | Ordinary last-write update; no special idempotency claim. | B proves current local user/settings row; accepted identity evidence owns forbidden identity fields. | Not an elevated/audited mutation in B. |
| `PATCH /notifications/{notification_id}/read` | B proves notification belongs to current user. | Not required. | Not applicable. | Marking read is repeat-safe for the same notification. | B proves foreign notification concealed and unchanged. | No separate audit requirement for ordinary notification read-state. |
| `PUT /inbox/app-updates/global-seen` | B proves signed token belongs to current user. | Not required. | Not applicable. | Current source uses monotonic `greatest` on the user's global seen sequence. | B proves invalid/wrong-user token produces no state change. | Signed-token source lifecycle remains accepted `WS02-04B2A2B2`; no admin audit. |
| `PUT /inbox/app-updates/platform-notices/{notice_id}/read` | B proves selected recipient row belongs to current user. | Not required. | Not applicable. | Current source uses insert-on-conflict-do-nothing for the same `(notice_id, user_id)`. | B proves published/not-cancelled selected notice plus current recipient. | Platform-notice creation/cancel/admin audit remains outside B. |
| `POST /user-payment-methods/setup-intent` | B proves setup is for current user's server-selected Stripe customer. | Not required by accepted `WS03-03A` route matrix. | Not applicable. | Provider create-timeout/retry depth is outside B; B only proves local authorization ordering. | B proves active account and no request-writable customer/user id. | Live Stripe/provider recovery remains `WS05`/provider evidence. |
| `POST /user-payment-methods/sync` | B proves SetupIntent and payment method customer match current user's Stripe customer. | Not required by accepted `WS03-03A` route matrix. | Not applicable. | Accepted provider-input evidence covers duplicate/limit compatibility; B proves no wrong-customer row creation. | B proves active account, provider status, customer match, duplicate/other-owner rejection. | Live Stripe/provider reconciliation remains `WS05`; admin financial review remains `WS03-04D`. |
| `PATCH /user-payment-methods/{payment_method_id}/default` | B proves card belongs to current user before provider defaulting. | Required by accepted `WS03-03A` and B must preserve denial before provider calls. | Not applicable; recent-auth is the approved step-up. | Setting the same own active card as default is repeat-safe under current service state. | B proves active card, current Stripe customer, owner check, and other-user defaults unchanged. | Live provider dashboard/default-state proof remains outside B. |
| `DELETE /user-payment-methods/{payment_method_id}` | B proves card belongs to current user before provider detach. | Required by accepted `WS03-03A` and B must preserve denial before provider calls. | Not applicable; recent-auth is the approved step-up. | Detaching an already detached own card returns current detached state without another state transition. | B proves active account, owner check, provider-call ordering, and other-user cards unchanged. | Live provider detach/recovery remains `WS05`/provider evidence. |

### 6.7 Notification And Inbox Contract

Notification list and object behavior is repository-owned by
`backend/services/notification_service.py`:

- `list_my_notifications` passes `current_user.id` to
  `list_user_notifications_workflow`;
- `query_notifications` starts from `Notification.user_id == user_id`;
- `get_visible_notification_or_404` returns another ordinary user's
  notification as `404`;
- `mark_notification_read_workflow` sets `allow_admin_read=False`, so an admin
  exception does not mutate another user's notification through the ordinary
  read-state path.

Inbox behavior is repository-owned by `backend/services/inbox_service.py`:

- selected platform notices require a `PlatformNoticeRecipient.user_id` row for
  the current user;
- selected read-state rows are keyed by `(notice_id, user.id)`;
- global seen tokens include `user_id` and are rejected when the signed user id
  differs from the current user;
- app and game-activity notification feeds/counts filter by
  `Notification.user_id == user.id`.

Gate B must pair each denial path with persisted-state checks, especially
wrong-owner notification read, wrong-recipient platform notice read, and
wrong-user global seen token.

### 6.8 Saved-Card Contract

Saved-card behavior is repository-owned by
`backend/services/payment_method_service.py`:

- local card reads call `get_owned_payment_method_or_404`, which requires
  `UserPaymentMethod.user_id == current_user.id`;
- default and detach actions call the same owner check before provider mutation;
- setup/sync use `current_user.stripe_customer_id`;
- sync rejects a SetupIntent or Stripe payment method whose customer id does
  not match the current user's customer id;
- duplicate-card, active-card limit, and provider-input ownership remain
  compatible with accepted `WS02-04B2A2B2` evidence.

Gate B may use local provider fakes only to prove app-owned authorization
ordering and no prohibited side effects. It must not describe that evidence as
live Stripe, deployed, runtime, or production proof.

### 6.9 Financial Read Contract

Ordinary-user financial records use these source-owned record owners:

| Record | Owner field for B ordinary-user proof |
| --- | --- |
| `Payment` | `Payment.payer_user_id` |
| `Refund` | `Refund.payment_id -> Payment.payer_user_id` |
| `GameCredit` | `GameCredit.user_id` |
| `HostPublishFee` | `HostPublishFee.host_user_id` |

Gate B must prove that ordinary users cannot widen list results through
`payer_user_id`, `payment_id`, `booking_id`, `game_id`, `refund_id`,
`host_publish_fee_id`, `requested_by_user_id`, `approved_by_user_id`, or
`user_id` filters. Admin broad reads that current services permit are not B
closure; they remain for `WS03-04D`.

### 6.10 Admin Exception Boundary

B-owned route families include some current service behavior that allows active
admins to read broader information through otherwise user-facing services. B
must handle this precisely:

- B proves ordinary users are current-user scoped.
- B may include compatibility assertions that admin-capable branches are not
  accidentally reachable by ordinary users.
- B must not claim final admin, minimum-necessary data, export, unmask,
  read-audit, or high-risk closure.
- B must leave `WS03-04D` as the owner for final admin/high-risk review and
  parent-gap disposition.

### 6.11 Requirement And Evidence Contract

Gate B must create a new requirement declaration and trusted workflow scope.
Every pytest test in the scope must use stable
`@pytest.mark.requirement(...)` markers for `WS03-04B-R1` through
`WS03-04B-R9`. `WS03-04B-R10` is deferred/governance and must have no pytest
mapping.

The Gate B testing record must use the testing-record template and explain:

- the B route inventory, counts, and matrix source;
- current-user, active-user, recent-auth, and provider-verified-user distinctions;
- verified-email applicability for every B-owned route/action;
- `401`/`403`/`404` denial classes, ordinary-user negative proof, and persisted-state checks;
- B-owned field and mass-assignment boundaries;
- IAM-017 dimensions for self/high-risk and financial mutations;
- admin exception boundary and `WS03-04D` handoff;
- local provider fakes versus live/deployed/provider evidence;
- why production source did or did not need changes;
- remaining downstream owners without filler or overclaiming.

## 7. Implementation Scope

### Gate B Editable File Set

Gate B may edit exactly:

```text
backend/tests/support/requirements/ws03_04b.json
backend/tests/workflows/self_owned_account_notification_financial_authorization/test_self_owned_account_notification_financial_authorization_contract.py
backend/tests/workflows/self_owned_account_notification_financial_authorization/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

No production source file is included in the Gate B editable set. If Gate B
requires a production source edit, a matrix edit, a migration, a frontend edit,
or another test file to complete B honestly, Gate B must stop and return to
Gate A correction.

### Exact Expected Final Changed-File Set

The expected final changed-file set after B completes and before Gate D
publication is exactly:

```text
docs/production-readiness/planning/passes/ws03/ws03-04b-self-owned-account-notification-financial-authorization.md
backend/tests/support/requirements/ws03_04b.json
backend/tests/workflows/self_owned_account_notification_financial_authorization/test_self_owned_account_notification_financial_authorization_contract.py
backend/tests/workflows/self_owned_account_notification_financial_authorization/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

The approved Stage 0 intake and accepted `WS03-04A` artifacts are current
`develop` inputs for B and are not Gate B-editable files.

## 8. Implementation Impact And Compatibility Review

| Area | Impact decision |
| --- | --- |
| FastAPI route table | Read-only input. Gate B must re-read current `backend.main.app`, compare B route keys to the accepted matrix, and fail on drift. |
| Route modules | Read-only source proof: `auth_routes.py`, `user_routes.py`, `user_settings_routes.py`, `user_stats_routes.py`, `notification_routes.py`, `inbox_routes.py`, `user_payment_method_routes.py`, `game_credit_routes.py`, `payment_routes.py`, `refund_routes.py`, and `host_publish_fee_routes.py`. |
| Auth service | Read-only compatibility proof for `get_current_app_user`, `require_active_user`, `require_active_account`, `require_recent_app_user`, `require_recent_active_user`, and the absence of `require_verified_user` from B-owned route dependencies. |
| Domain services | Read-only source proof for account deletion, user profile/settings/stats, notification, inbox, payment method, game credit, payment, refund, and host-publish-fee services. |
| Models | Read-only fixtures over `User`, `UserSettings`, `UserStats`, `Notification`, platform-notice read-state models, `UserPaymentMethod`, `GameCredit`, `Payment`, `Refund`, and `HostPublishFee`. |
| Schemas/OpenAPI | Read-only compatibility with accepted response-minimization contracts; no response model changes planned. |
| Frontend callers | Read-only compatibility. Current self-facing callers use `/auth/me`, `/auth/account`, `/users/me`, `/user-settings/me`, `/user-stats/me`, `/game-credits/balance`, `/host-publish-fees/me`, `/inbox/*`, and `/user-payment-methods/*`. Current admin money/notification callers use `/admin/...` routes outside B. |
| Request/response compatibility | No API contract changes planned. Gate B tests should assert behavior through existing API/service contracts, not rewrite schemas. |
| Settings and environment | No configuration changes. Tests may use synthetic `INBOX_TOKEN_SECRET` and local provider fakes already supported by the backend test harness. |
| Provider/network calls | No live provider calls. Stripe and Firebase side effects must be faked only where needed to prove local authorization ordering. |
| Database/schema/migrations | No model or migration changes planned. Tests use the dedicated local test database and existing cleanup inventory. |
| Existing trusted tests | Gate B validation must include the B focused scope plus A matrix compatibility and affected predecessor/compatibility scopes named below. |
| Execution register | Gate B must update the register with the proposed B accepted state that becomes true only when the substantive B PR merges into `develop`. |

## 9. Testing And Evidence

Gate B must create one focused trusted pytest file:

```text
backend/tests/workflows/self_owned_account_notification_financial_authorization/test_self_owned_account_notification_financial_authorization_contract.py
```

The test file must be ordinary-suite trusted evidence and should include these
proof groups:

| Proof group | Required behavior |
| --- | --- |
| Matrix/scope guard | Load `authorization_matrix.json`, assert B has exactly 11 families and 28 route keys, assert every B route still exists in current `backend.main.app`, assert recorded auth dependencies still match current route dependencies, assert no B route has `blocked` ownership, and assert no B test maps to deferred `WS03-04B-R10`. |
| Verified-email classification | Use synthetic provider identities to prove provider-unverified users are not rejected merely for being unverified on representative B-owned ordinary allowed classes, while matrix/source inspection confirms no B route-level dependency uses `require_verified_user`. Pair this with negative proof that unverified users still fail missing/invalid-token, active-account, recent-auth, wrong-owner, wrong-customer, and wrong-token checks. Record active-admin broad-read branches as D-owned and prove ordinary users cannot enter them. |
| Current-account self routes and field boundaries | Use synthetic Firebase token verification and DB-backed API requests to prove `/auth/me`, `/users/me`, `/user-settings/me`, and `/user-stats/me` return current-user data; prove profile/settings updates affect only the current user's row; prove caller-controlled identity, account, role, ownership, provider, and server-managed fields are not accepted or do not change protected state, relying on accepted `WS03-01` where it already owns identity-specific field rejection. |
| Self-delete ownership, recent-auth, and IAM-017 | Use a provider fake to prove stale/missing recent-auth denial occurs before deletion side effects, invalid confirmation is rejected, and fresh recent-auth self-delete acts on the token user's local account while leaving another user untouched. Relationship cleanup side effects are compatibility checks only and do not become C closure. |
| Default-deny status classes | Prove representative `401` credential failures, `403` active-account/recent-auth/admin-only/provider-customer failures, and `404` concealed foreign-resource failures across the B dependency/service classes; use matrix coverage to show equivalent routes are covered without duplicating every route. |
| Notifications | Create notifications for two users; prove `/notifications/me` lists only the current user's rows even with filters; prove `GET /notifications/{notification_id}` and `PATCH /notifications/{notification_id}/read` deny another ordinary user's notification with concealment where current source does so and leave its read state unchanged. |
| Inbox | Create global and selected platform notices plus notification rows; prove app-updates, game-activity, and counts are current-user scoped; prove selected platform notice reads require current-recipient ownership and are idempotent for the same recipient; prove wrong-user global-seen tokens reject without updating either user's seen state. |
| Saved cards and IAM-017 | Use DB rows and Stripe fakes to prove list/get/default/detach use the current user's card rows only; wrong-owner local card IDs are rejected before provider calls; SetupIntent and payment-method customer mismatches do not create or revive a local saved-card row; default/detach preserve accepted recent-auth and do not change another user's default or detached state. |
| Credits and financial reads | Create credits, payments, refunds, and host-publish-fee records for two users; prove non-admin lists/default filters return only the current user's records; prove query filters for another user's IDs do not widen ordinary-user access; prove object reads for another user's payment/refund deny under current forbidden behavior. |
| Admin exception boundary | Prove ordinary player users do not enter admin-read branches. Record, without claiming D closure, where current services permit active-admin broad reads. |
| Requirement/checker traceability | Assert declaration states and markers map `R1`-`R9`; assert `R10` stays deferred/governance with zero pytest mappings. |

Gate B must also create:

```text
backend/tests/workflows/self_owned_account_notification_financial_authorization/TESTING_RECORD.md
```

The testing record must be reviewer-facing and must explain what proof actually
ran. It must not call local source/pytest evidence live, deployed, production,
or real-world proof.

## 10. Validation Strategy

Gate B must run this validation set after implementation:

```text
git status -sb --untracked-files=all
LC_ALL=C shasum -a 256 docs/production-readiness/planning/passes/ws03/ws03-04-intake.md
LC_ALL=C shasum -a 256 docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md
backend/.venv/bin/python -m py_compile backend/tests/workflows/self_owned_account_notification_financial_authorization/test_self_owned_account_notification_financial_authorization_contract.py
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest backend/tests/workflows/self_owned_account_notification_financial_authorization
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest backend/tests/workflows/authorization_matrix_foundation
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest backend/tests/workflows/identity_authority backend/tests/workflows/account_lifecycle_concurrency backend/tests/workflows/recent_auth_step_up backend/tests/workflows/provider_payment_input_ownership backend/tests/workflows/response_minimization
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/self_owned_account_notification_financial_authorization
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
- the B focused pytest scope passes;
- the A matrix scope still passes, proving B did not drift route keys or auth
  dependencies;
- affected trusted predecessor scopes pass for identity, account lifecycle,
  recent-auth, provider-payment input ownership, inbox seen-token behavior, and
  response minimization;
- checker domain and suite compliance pass;
- `git diff --check` passes;
- `git diff --cached --name-only` is empty;
- actual changed files equal the expected final changed-file set.

## 11. Integration / Operational Expectations

Gate B does not deploy, call live providers, change runtime settings, create a
migration, or change production code. The accepted outcome is a local,
repository-derived proof set plus the proposed execution-register update.

The register update must describe the state that becomes true atomically only
when the substantive `WS03-04B` PR merges into `develop`. Human Gate B or Gate C
approval does not by itself make B accepted.

The register update must:

- add `WS03-04B` to accepted executable passes, with plan path
  `passes/ws03/ws03-04b-self-owned-account-notification-financial-authorization.md`,
  requirement declaration `ws03_04b.json`, total requirements `10`, required
  `9`, blocked `0`, deferred `1`, and scope
  `workflows/self_owned_account_notification_financial_authorization` plus
  governance;
- keep the approved `WS03-04` child graph
  `WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D`;
- record `WS03-04A` and `WS03-04B` as accepted after the substantive B merge;
- record `WS03-04C` and `WS03-04D` as remaining;
- keep the parent `WS03-04` incomplete after B because relationship and
  admin/high-risk authorization are not closed by this child;
- avoid stating or implying that B becomes accepted before merge.

## 12. Not Part Of This Pass

- No `WS03-04C` relationship authorization for games, checkout, bookings,
  participants, waitlists, chats, messages, community games, My Games, or
  Need-a-Sub workflows.
- No `WS03-04D` final admin route/list/high-risk review, minimum-necessary
  admin data proof, export/unmask/read-audit policy, or final parent-gap
  disposition.
- No live Stripe, Firebase, deployed runtime, provider dashboard, production, or
  external evidence.
- No durable payment/refund reconciliation, webhook lifecycle closure, durable
  job proof, or support repair workflow closure.
- No genuine database-concurrency proof, schema change, or migration.
- No frontend UI changes, browser/e2e proof, or Playwright proof.
- No correction to separate production-readiness onboarding or documentation
  issues.

## 13. Related Controls And Remaining Evidence

| Owner | Remaining after B |
| --- | --- |
| `WS03-04C` | Relationship authorization for player/host/community/Need-a-Sub surfaces, including nested resource and workflow-state proof. |
| `WS03-04D` | Admin route/list/high-risk authorization, admin breadth review across any current service exceptions, and final `WS03-04` parent-gap disposition. |
| `WS05` | Stripe webhook/payment/refund/credit durable lifecycle and provider reconciliation proof, including the accepted A matrix `/stripe/webhook` gap. |
| `WS04` | Genuine database-concurrency closure where financial/account operations need race proof beyond serial local behavior. |
| `WS09`/`WS10` | Audit, sensitive access, runtime/provider governance, operational evidence, and recovery/provider-access evidence. |

## 14. Stop And Correction Boundaries

Gate B must stop and return for Gate A correction if any of these occur:

- the approved intake SHA changes;
- the accepted A plan SHA changes;
- the current route table or accepted A matrix no longer has exactly the B route
  inventory listed in this plan;
- an A matrix drift check fails because route dependencies or route keys changed;
- any production source file must be modified to satisfy a B requirement;
- `authorization_matrix.json` must be modified;
- any file outside the exact Gate B editable set is required;
- ordinary-user and admin behavior cannot be separated without redesigning B/D
  ownership;
- a live/deployed/provider/runtime proof is needed for acceptance;
- a migration or database-concurrency design is required;
- a test needs historical archived tests as current evidence;
- validation cannot pass without changing this plan.

## 15. Completion Criteria

Gate B is complete only when all of the following are true:

- `backend/tests/support/requirements/ws03_04b.json` declares `R1` through
  `R9` as required and `R10` as deferred/governance with zero pytest mappings;
- the focused trusted pytest file proves the B route inventory, verified-email
  classification, current-user account/profile/settings/stats ownership,
  B-owned field boundaries, notification/inbox ownership, saved-card ownership,
  credit/payment/refund/host-fee ordinary-user scoping, `401`/`403`/`404`
  denial classes, rejected-mutation side effects, IAM-017 mutation dimensions,
  and admin exception boundary described in this plan;
- the testing record explains the actual local proof and remaining boundaries
  in ordinary engineering language;
- the execution register contains the proposed accepted B state and remaining
  `WS03-04C`/`WS03-04D` parent state that becomes true only on merge;
- all validation commands in this plan pass;
- the actual changed-file set equals the expected final changed-file set;
- nothing is staged before Gate C/human review;
- no Gate C, Gate D, commit, push, PR update, merge, deployment, provider call,
  migration, or production behavior implementation has occurred during Gate B.

## 16. Gate A Stop Boundary

Gate A created only this canonical plan. Gate A did not implement Gate B
evidence, edit the frozen intake, edit accepted `WS03-04A` artifacts, change
production source, stage files, commit, push, create or update a PR, merge, or
begin Gate B.
