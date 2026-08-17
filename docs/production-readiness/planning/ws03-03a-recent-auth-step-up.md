# WS03-03A - Recent Authentication And Step-Up

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS03-03A` |
| Pass name | Recent Authentication And Step-Up |
| Track | `WS03 Identity, account state, authorization, and admin security` |
| Type | Narrow backend + frontend source correction plus trusted evidence and cross-pass compatibility correction |
| Primary controls | `IAM-008` |
| Supporting controls and boundaries | `IAM-003`, `IAM-010`, `IAM-011`, `IAM-017`, `PAY-011`, `ADM-013`, `FE-M04`, `EN-02`, `EN-03` |
| Authority basis | Current accepted `develop` implementation truth; locked production-readiness audits; 163-control checklist; final remediation plan; master blueprint `WS03-03`; approved identity decisions `IDB-01`, `IDB-02`, `IDB-03`, `IDB-04`; accepted `WS03-01`, `WS03-02`, and `EN-03` boundaries |
| Depends on | `WS03-01`; `WS03-02`; `EN-02`; `EN-03`; approved decisions `IDB-01` through `IDB-04` |
| Accepted baseline | `044f17b462837d9eb9a5f357aa85a49730ff7467` |
| Remediation branch | `pr/WS03-03A-remediation` |
| Trusted test scope | `backend/tests/workflows/recent_auth_step_up` |
| Requirement declaration | `backend/tests/support/requirements/ws03_03a.json` |
| Historical provenance | PR #128, historical branch `pr/WS03-03A`, historical base `cc5131cc19a27e7f2da313fe8622e03f9e5321e1`, historical head `ba9a1c7c5f63e39de9b2af6f818f33c6537d0001`, historical merge `d4d1d5fe49e2888ccbb09a68a0500c5d9e71786e` |

## 1. Purpose

WS03-03A proves the source-owned recent-authentication and step-up behavior
that currently protects approved high-risk account, administrative,
terminal-resource lifecycle, financial/provider-repair, platform-notice, and
saved-card mutations.

The pass requires trusted evidence that:

- the backend uses only the verified Firebase ID token `auth_time` claim as
  recent-authentication authority;
- the backend never accepts `iat`, frontend timestamps, browser storage,
  PostgreSQL timestamps, client booleans, purpose flags, or app-generated
  proofs as freshness authority;
- stale, missing, malformed, future, or too-old provider authentication times
  fail closed;
- the recent-authentication threshold is the current five-minute source-owned
  WS03-03A threshold after human approval of this plan;
- recent-auth failures use the stable public error contract
  `AUTH.RECENT_AUTH_REQUIRED`;
- current high-risk routes are registered with the correct recent-auth
  dependency wrappers;
- terminal admin community-game cancellation, terminal Need-a-Sub post
  removal, admin hosting restriction/restoration, paid official-player
  removal, generic admin game/venue soft-delete, and payment-event repair are
  treated as high-risk where current source semantics require it;
- every current active admin mutation route is classified at route/action level
  as recent-auth-required, intentionally not recent-auth-required, or
  retired/non-executing;
- routes intentionally left ungated remain classified and are not silently
  converted into high-risk bypasses;
- frontend step-up is caller-owned, uses Firebase email/password or Google
  reauthentication, refreshes the normal Firebase ID token, and does not create
  a generic blind mutation replay mechanism;
- the current add-password credential-linking flow requires step-up before
  Firebase `linkWithCredential` and does not introduce local account merge or
  relink authority;
- no application-owned persisted freshness state becomes an alternate auth
  authority.

This pass does not implement or prove Firebase App Check enforcement,
administrator MFA provider configuration, Firebase/GCP service-account
governance, provider IAM review, production hosting, deployment runtime proof,
or operational access-review evidence. Those remain WS03-03B, WS10, or later
provider/runtime work.

## 2. Why This Matters

Ordinary Firebase sessions can be long-lived. A valid current session is not
always enough protection for destructive account changes, elevated admin
mutations, financial repair actions, or saved-card state changes. If Pickup
Lane accepts any caller-provided freshness proof, stores its own freshness flag,
or retries destructive actions through a global frontend interceptor, an
attacker with a stale session could perform high-impact actions without
actually reconfirming identity.

The concrete risks are:

- treating an ID-token refresh as reauthentication when the provider
  `auth_time` is still stale;
- allowing a client timestamp or browser-storage value to satisfy step-up;
- letting an admin role, suspension, deletion, hosting restriction,
  community-game cancellation, Need-a-Sub removal, paid official-player
  removal, game/venue soft-delete, payment-event repair, refund, credit,
  notice, or official-game cancellation route bypass recent-auth because it
  used an older dependency wrapper;
- breaking existing preview, idempotency, final-admin, audit, provider
  reconciliation, or ownership safeguards by replacing them with recent-auth;
- replaying non-idempotent mutations after reauth from a generic transport
  layer;
- sending passwords, popup tokens, raw ID tokens, or provider internals to the
  backend or logs;
- overstating local source evidence as proof of App Check, admin MFA, provider
  credential scope, or production runtime closure.

## 3. Authority Reconstruction

### 3.1 Repository Truth And Provenance

Current accepted `develop` at
`044f17b462837d9eb9a5f357aa85a49730ff7467` is repository truth for the current
implementation state.

The authoritative production-readiness controls, approved decisions, accepted
dependency pass boundaries, and this reconciled/frozen plan define what must
be true. Historical PR #128 remains provenance only. It explains how the
current source shape entered the repository, but it does not define current
requirements and its historical tests are not trusted evidence under EN-01.

PR #128 was merged as `WS03-03A enforce recent authentication` and changed 47
files. The non-excluded implementation themes were:

- backend recent-auth parsing, policy, settings, dependencies, route wiring,
  and public error normalization;
- backend test support and historical current-suite updates from the pre-EN-01
  layout;
- the initial WS03-03A planning document;
- frontend step-up context, hooks, reauthentication helpers, caller-owned
  high-risk action wrapping, UI styling, and unit tests.

Gate A reconciliation found that the current accepted source already contains
most WS03-03A source implementation. Current trusted EN-01 evidence is missing
for WS03-03A. Later Gate C/correction review found that the prior frozen
18-route matrix was incomplete. Current source has additional high-risk admin
mutation semantics that were incorrectly absorbed into broad intentionally
ungated buckets: terminal Need-a-Sub removal, admin hosting
restriction/restoration, paid official-player removal, generic admin game and
venue soft-delete, and payment-event repair.

Gate B must therefore perform the approved production correction as a single
batch, not one route at a time, and rebuild the trusted evidence around the
corrected 25-route high-risk matrix and complete current admin mutation
partition.

### 3.2 Primary Control

| Control | Authoritative requirement for this pass | Current Gate A interpretation |
|---|---|---|
| `IAM-008` | Require recent authentication or step-up controls for Firebase-sensitive account changes and other approved high-risk actions. Administrator MFA is required unless a documented provider limitation and compensating control exists. | Source-owned recent-auth and frontend step-up behavior is executable in WS03-03A. Administrator MFA, App Check, and Firebase/GCP credential governance remain external/provider/governance work with zero pytest closure in WS03-03A. |

### 3.3 Supporting Findings And Dependencies

The locked audits found `IAM-008` failed because no enforced recent-auth,
step-up, MFA, or compensating-control policy existed for high-risk account and
admin actions at the time of the audit. The same audit also identified related
gaps:

- `IAM-003`: token refresh and mutation retry must be bounded, and
  non-idempotent mutations must not be blindly replayed.
- `IAM-010`: App Check was conditional and needed an owner decision.
- `IAM-011`: Firebase/GCP service-account scope, key handling, inventory,
  rotation, monitoring, and emergency revocation require provider and
  operational evidence.
- `IAM-017` and `PAY-011`: several privileged/admin-money actions had broad
  active-admin gates, but no recent-auth/MFA/dual-control evidence.
- `ADM-013`: current enforcement routes use active-admin and state/idempotency
  controls, but action-specific and runtime authorization evidence remains
  incomplete.

Approved decision `IDB-01` allows Firebase browser persistence, bearer-token
transport, bounded safe-read refresh, and no blind replay of payments,
bookings, messages, cancellations, admin actions, or other mutations.

Approved decision `IDB-02` makes Firebase authoritative for authentication
facts and PostgreSQL authoritative for Pickup Lane business identity, roles,
account state, permissions, and ownership. This matters because recent-auth is
a provider authentication fact, not an application-owned timestamp.

Approved decision `IDB-03` makes current Firebase email verification required
for sensitive user/admin actions and keeps administrators tied to a currently
verified identifier.

Approved decision `IDB-04` makes Firebase App Check applicable as defense in
depth for the supported web client, but says it does not replace
authentication, authorization, rate limiting, idempotency, or replay-safe
business operations. App Check adoption requires provider/staging validation
and is not a WS03-03A local pytest closure.

Accepted `WS03-01` supplies the identity-authority base: verified Firebase
identity first, then current PostgreSQL user/account/admin authority. Accepted
`WS03-02` supplies account lifecycle and final-local-admin protections that
recent-auth wrappers must preserve. `EN-03` supplies the provider, secret, and
safe-evidence boundary for Firebase/GCP control-plane facts.

### 3.4 Five-Minute Threshold Authority

Gate A found no separate owner-decision record or limits-register row that
independently approves a recent-authentication duration. The current accepted
source and historical PR #128 both use a five-minute window through
`DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS = 5 * 60`, surfaced on typed
backend settings as `recent_authentication_window_seconds`.

This plan treats five minutes as the explicit WS03-03A source-owned threshold
proposed for human Gate A approval. Human approval of this canonical plan is
the approval basis for that threshold. If the human reviewer does not approve
that threshold, WS03-03A must return for Gate A correction before Gate B
evidence is implemented.

### 3.5 High-Risk Admin Mutation Reconciliation

Current source shows these active admin mutations are high-risk under
`IAM-008`, `IAM-017`, `ADM-013`, `PAY-011`, `IDB-01`, and accepted
WS03-01/WS03-02 authority. Each must be protected with
`require_recent_active_admin` and represented in
`backend/services/recent_auth_policy.py`.

`POST /admin/community-games/{game_id}/cancel` is not routine reversible
moderation. It is a terminal admin lifecycle operation:

- the route currently uses `require_active_admin`;
- `admin_cancel_community_game` requires an active admin, normalizes a reason
  and idempotency key, checks existing idempotent admin actions, and locks the
  game row;
- it calls `apply_game_cancellation_state`, which cancels active participants,
  waitlist entries, bookings, chats, notification state, cancellation history,
  game lifecycle state, and open community-game review cases;
- it writes an `admin_cancel_community_game` audit action and host notice;
- the shared cancellation workflow may participate in payment, refund, credit,
  or money-issue handling when the game requires app player payment, while
  community games currently do not use in-app player payment;
- the frontend production caller is
  `frontend/src/pages/admin/community-games/AdminCommunityGameActionModal.jsx`
  through `cancelAdminCommunityGame` in `frontend/src/pages/admin/shared/adminApi.js`.

`POST /admin/need-a-sub/{post_id}/remove` is not equivalent to hide or
restore. The current route uses `require_active_admin` and calls
`remove_need_a_sub_post_by_admin`. Current service logic expires due posts and
requests, requires a reason and idempotency key, locks the post, records
`remove_sub_post`, sets `post_status = "removed"`, stores removal actor/time
and reason, writes status history, closes open moderation cases, closes post
chat, resolves chat notifications, notifies the owner, closes active requests
as `closed_by_admin`, notifies requesters, and records notice/request IDs in
audit metadata. Need-a-Sub admin guidance says remove/cancel is terminal by
default while hide/pause are reversible. This route must require recent auth;
Need-a-Sub hide, restore, and chat moderation remain intentionally ungated.

`POST /admin/users/{user_id}/restrict-hosting` and
`POST /admin/users/{user_id}/restore-hosting` mutate persistent user hosting
capability, write `restrict_hosting` / `restore_hosting` admin actions, send
account-security notifications, and change `hosting_status`. They are not
identity-linkage workflows owned by WS03-02, but they are privileged account
capability changes and must require recent auth. Their preview route remains
intentionally ungated.

`POST /admin/official-games/{game_id}/participants/{participant_id}/remove`
is not ordinary roster bookkeeping. Current source can remove an entire booking
party, cancel the booking, update payment status, release pending payments,
restore game credits, create refunds, create money issues on provider/ledger
failure, advance the waitlist, send notifications, and write an
`admin_remove_player` audit action. It must require recent auth. The
corresponding preview route, host assignment/removal, player add, official game
edit/create, photo, and chat moderation routes remain intentionally ungated.

`DELETE /games/{game_id}` is an active admin-only soft-delete route. Current
source rejects official games, marks a community game deleted, and can close an
open community-game content moderation case with lifecycle action
`admin_soft_deleted`. It is a terminal resource lifecycle mutation and must
require recent auth.

`DELETE /venues/{venue_id}` is an active admin-only venue soft-delete route.
Current source sets `is_active = False`, `venue_status = "inactive"`,
`deleted_at`, and `updated_at`. It is a terminal venue lifecycle mutation and
must require recent auth. Venue create/update tombstones and venue-image
upload/update workflows remain separately classified.

`PATCH /payment-events/{payment_event_id}` is the retained admin repair route
for linking a previously unmatched payment event and updating its processing
result while provider-owned event identity/payload remain immutable. It is a
financial/provider repair mutation and must require recent auth.

Reversible community administration, routine Need-a-Sub moderation, official
host/roster additions, previews, admin review/support case notes/closure,
venue-image upload lifecycle, ordinary game/venue/admin edits, and retired or
non-executing generic scaffolds remain outside recent-auth where the complete
route partition below explicitly says so.

## 4. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS03-03A-R1` | Provider `auth_time` is the only recent-auth authority. | Backend recent-auth logic accepts only the verified Firebase ID token `auth_time` claim parsed into the request-scoped identity. It must reject missing, malformed, boolean, non-finite, negative, overflow, naive, future, or stale values and must not use `iat`, frontend timestamps, local/browser storage, PostgreSQL timestamps, client booleans, purpose flags, or app-generated proofs. | Prevents stale sessions or caller-authored values from satisfying high-risk step-up. |
| `WS03-03A-R2` | The five-minute threshold and exact boundary semantics are centralized and tested. | The current WS03-03A recent-auth window is five minutes after human plan approval. Exact current time, before-boundary, at-boundary, after-boundary, future-time, timezone, and missing-time cases must be controlled in evidence. | A high-risk freshness control must be deterministic and fail closed at its edge. |
| `WS03-03A-R3` | Recent-auth denial uses a stable safe public error contract. | Stale or missing recent auth returns HTTP `403` with code `AUTH.RECENT_AUTH_REQUIRED` and public message `Confirm your identity to continue.` through the existing EN-02 error envelope, correlation, cache/security-header, and redaction behavior. It must not expose raw tokens, provider credentials, popup results, passwords, `auth_time`, stack traces, or provider internals. | Frontend step-up needs a stable public signal, while auth details must stay private. |
| `WS03-03A-R4` | Recent-auth wrappers layer on accepted identity and account authority. | `require_recent_app_user`, `require_recent_active_user`, and `require_recent_active_admin` add recent provider authentication while preserving current Firebase identity verification, local user lookup, active-account checks, verified-email requirements, local admin role checks, deletion/pending-deletion behavior, and final-admin protections. | Step-up must strengthen the existing dependency chain, not replace identity or lifecycle safeguards. |
| `WS03-03A-R5` | The approved high-risk route matrix is enforced. | The current route inventory in `backend/services/recent_auth_policy.py` must match registered FastAPI routes and their dependency wrappers for self-delete; saved-card default/detach; admin role/user lifecycle including hosting restrict/restore; admin money issue/refund/credit/financial-outcome actions; payment-event repair; official-game cancellation and paid-player removal execution; terminal community-game cancellation; terminal Need-a-Sub removal; generic admin game/venue soft-delete; and platform notice create/cancel. | Prevents high-risk account, admin, terminal lifecycle, financial/provider repair, notice, and saved-card mutations from silently reverting to ordinary active-session access. |
| `WS03-03A-R6` | Intentionally ungated routes are classified and preserved. | Public/general reads, normal profile/settings updates, ordinary game participation, checkout/add-card setup and sync, reversible community moderation, reversible Need-a-Sub moderation, previews, official-game edits/host/player-add/photo/chat actions, admin review/support case management, venue-image upload/update lifecycle, and retired/non-executing routes remain outside WS03-03A recent-auth unless they overlap the explicit high-risk list or a later owner reclassifies them. Terminal cancellation/removal, payment repair, hosting capability changes, and soft-delete routes are not part of these exceptions. | Recent-auth should not become a blanket mutation rule that hides unresolved ownership or breaks ordinary workflows. |
| `WS03-03A-R7` | Frontend email/password and Google step-up use Firebase reauthentication safely. | Email/password users re-enter their password only into Firebase credential reauthentication. Google users use Firebase popup reauthentication. Successful reauth forces a normal Firebase ID-token refresh. Failed or cancelled reauth fails closed. The password, popup result tokens, and provider credentials are not sent to the backend or stored by Pickup Lane source. | The frontend must perform real provider step-up without creating a new credential or token exposure path. |
| `WS03-03A-R8` | Step-up retry is caller-owned and not a blind global replay. | Only opted-in high-risk callers use `runWithStepUp` or `confirmStepUp`. The low-level API client must not globally intercept `AUTH.RECENT_AUTH_REQUIRED`, refresh tokens, or replay arbitrary bookings, payments, messages, cancellations, admin actions, or other mutations. | Keeps replay decisions with workflows that know whether the original mutation is safe, idempotent, or still uncertain. |
| `WS03-03A-R9` | Credential linking requires step-up and remains provider-owned. | The exposed add-password flow for Google users requires frontend step-up before Firebase `linkWithCredential`. It must not send the password to the backend and must not create local UID merge, email-based relink, or account takeover authority. | Linking credentials is Firebase-sensitive and must not bypass WS03-02 identity/lifecycle protections. |
| `WS03-03A-R10` | Freshness is not persisted or mirrored as app authority. | `auth_time` may be parsed into request-scoped identity for current-request evaluation only. No Postgres column, browser storage value, frontend state flag, request field, purpose flag, cache entry, or telemetry label may become application-owned freshness authority. | Prevents a second freshness source that can outlive, disagree with, or be authored outside Firebase. |
| `WS03-03A-R11` | Negative-space evidence fails closed for bypasses and overclaims. | Gate B evidence must inventory active backend and frontend source for high-risk route bypasses, complete admin mutation partition drift, route-family misclassification, duplicate recent-auth policy copies, request-shaped freshness, raw decoded-token authority, `iat`/local timestamp use, browser-storage freshness, generic replay interceptors, password/token forwarding, persisted `auth_time`, purpose flags, and pytest mappings for deferred provider/governance facts. | Prevents trusted evidence from passing while a new bypass, unclassified route, or false closure path exists. |
| `WS03-03A-R12` | Administrator MFA remains deferred provider/governance evidence. | WS03-03A may document source compensating controls but must not claim provider MFA capability, enrollment, enforcement, break-glass, admin sign-in runtime proof, access review, or provider limitation proof. No pytest may map this requirement. | IAM-008 includes administrator MFA, but local source tests cannot prove provider MFA posture. |
| `WS03-03A-R13` | Firebase App Check remains deferred provider/runtime evidence. | App Check is applicable by `IDB-04`, but WS03-03A must not implement or prove valid, missing, invalid, provider-unavailable, staged-enforcement, rollback, false-positive, or production App Check behavior. No pytest may map this requirement. | Keeps defense-in-depth provider work separate from the recent-auth source pass. |
| `WS03-03A-R14` | Firebase/GCP credential governance remains deferred provider/operations evidence. | Service-account mechanism, least privilege, key inventory, storage, rotation, revocation, monitoring, emergency procedure, ADC/workload-identity posture, permanent-host binding, and provider IAM review remain EN-03/WS10 or WS03-03B work. No pytest may map this requirement. | Prevents local code evidence from overstating credential control-plane readiness. |

## 5. Technical Design / Contracts

### 5.1 Backend Recent-Authentication Authority

Backend recent-auth logic is owned by `backend/services/auth_service.py`.

Required contracts:

- `parse_provider_authenticated_at` reads only `decoded_token["auth_time"]`.
- Missing, boolean, non-numeric, non-finite, negative, overflow, and invalid
  provider values produce `None`.
- `VerifiedFirebaseIdentity.authenticated_at` is request-scoped and optional.
- `is_recent_authentication` requires a timezone-aware provider time, normalizes
  to UTC, rejects future times, and accepts ages in the inclusive range
  `0 <= age <= window`.
- `recent_authentication_window` reads the central typed settings value.
- `require_recent_authentication` depends on the existing verified Firebase
  identity path and raises the public 403 detail when freshness is absent or
  stale.

Refreshing a Firebase ID token without Firebase reauthentication is not a
freshness event unless the provider updates `auth_time`. Local evidence must
prove the source depends on `auth_time`, not token issue time.

### 5.2 Backend Dependency Layering

Recent-auth dependencies must remain wrappers:

| Dependency | Required layering |
|---|---|
| `require_recent_authentication` | Verified Firebase identity plus provider `auth_time` evaluation. |
| `require_recent_app_user` | Existing current app user plus recent provider auth. |
| `require_recent_active_user` | Existing active local user plus recent provider auth. |
| `require_recent_active_admin` | Existing verified active local admin plus recent provider auth. |

These wrappers do not replace:

- Firebase token verification;
- current provider email verification where required;
- local user lookup by Firebase UID;
- local active/suspended/pending-deletion/deleted account checks;
- local role/admin checks;
- final-active-admin protections;
- idempotency keys;
- current-state tokens;
- preview tokens;
- audit records;
- provider reconciliation;
- target ownership and workflow-state checks.

### 5.3 Public Error Contract

Recent-auth failure uses:

| Field | Value |
|---|---|
| HTTP status | `403` |
| Public code | `AUTH.RECENT_AUTH_REQUIRED` |
| Public message | `Confirm your identity to continue.` |
| Envelope owner | Existing EN-02 / WS02-04A HTTP error normalizer |

Evidence must prove the response is a safe public error envelope and does not
include raw ID tokens, provider credentials, `auth_time`, passwords, OAuth
popup results, internal verification details, stack traces, or high-cardinality
personal/provider identifiers.

### 5.4 Current High-Risk Route Matrix

The source-owned high-risk inventory is
`backend/services/recent_auth_policy.py`. Gate B evidence must prove this
inventory and the registered FastAPI routes agree. The corrected matrix contains
25 routes: 22 admin-access high-risk routes plus current-user self-delete and
saved-card default/detach.

| Action | Actor | Route | Enforcement | Frontend caller | Provider MFA disposition |
|---|---|---|---|---|---|
| Self account deletion | Current user | `DELETE /auth/account` | `require_recent_app_user` | `useDeleteAccountSettings` | Deferred to WS03-03B |
| Admin role grant/removal | Admin | `PATCH /admin/users/{user_id}/role` | `require_recent_active_admin` | `AdminUserDetailPage role action` | Deferred to WS03-03B |
| Admin user deletion | Admin | `POST /admin/users/{user_id}/delete` | `require_recent_active_admin` | `AdminUserDeletePreviewModal` | Deferred to WS03-03B |
| Admin hosting restriction | Admin | `POST /admin/users/{user_id}/restrict-hosting` | `require_recent_active_admin` | `AdminUserHostingRestrictionModal` | Deferred to WS03-03B |
| Admin hosting restoration | Admin | `POST /admin/users/{user_id}/restore-hosting` | `require_recent_active_admin` | `AdminUserHostingRestorationModal` | Deferred to WS03-03B |
| Admin suspension | Admin | `POST /admin/users/{user_id}/suspend` | `require_recent_active_admin` | `AdminUserSuspensionModal` | Deferred to WS03-03B |
| Admin unsuspension | Admin | `POST /admin/users/{user_id}/unsuspend` | `require_recent_active_admin` | `AdminUserUnsuspensionModal` | Deferred to WS03-03B |
| Financial outcome create | Admin | `POST /admin/money/financial-outcomes` | `require_recent_active_admin` | `adminFinancialOutcomeApi` | Deferred to WS03-03B |
| Money issue resolve | Admin | `POST /admin/money/issues/{money_issue_id}/resolve` | `require_recent_active_admin` | `AdminMoneyIssuePage` | Deferred to WS03-03B |
| Money issue credit retry | Admin | `POST /admin/money/issues/{money_issue_id}/retry-credit` | `require_recent_active_admin` | `AdminMoneyIssuePage` | Deferred to WS03-03B |
| Refund retry | Admin | `POST /admin/money/refunds/{refund_id}/retry` | `require_recent_active_admin` | `AdminMoneyIssuePage` / `AdminMoneyRefundPage` | Deferred to WS03-03B |
| Refund reconcile | Admin | `POST /admin/money/refunds/{refund_id}/reconcile` | `require_recent_active_admin` | `AdminMoneyRefundPage` | Deferred to WS03-03B |
| Payment-event repair | Admin | `PATCH /payment-events/{payment_event_id}` | `require_recent_active_admin` | No current frontend caller | Deferred to WS03-03B |
| Game credit issue | Admin | `POST /admin/game-credits/issue` | `require_recent_active_admin` | Admin money credit workflows | Deferred to WS03-03B |
| Game credit reverse | Admin | `POST /admin/game-credits/{game_credit_id}/reverse` | `require_recent_active_admin` | Admin money credit workflows | Deferred to WS03-03B |
| Official game cancellation execute | Admin | `POST /admin/official-games/{game_id}/cancel` | `require_recent_active_admin` | `AdminOfficialGamePage` | Deferred to WS03-03B |
| Official paid-player removal execute | Admin | `POST /admin/official-games/{game_id}/participants/{participant_id}/remove` | `require_recent_active_admin` | `AdminOfficialGamePage` | Deferred to WS03-03B |
| Admin community game cancellation | Admin | `POST /admin/community-games/{game_id}/cancel` | `require_recent_active_admin` | `AdminCommunityGameActionModal` | Deferred to WS03-03B |
| Admin Need-a-Sub post removal | Admin | `POST /admin/need-a-sub/{post_id}/remove` | `require_recent_active_admin` | `AdminNeedASubRemovalModal` | Deferred to WS03-03B |
| Admin game soft-delete | Admin | `DELETE /games/{game_id}` | `require_recent_active_admin` | No current frontend caller | Deferred to WS03-03B |
| Admin venue soft-delete | Admin | `DELETE /venues/{venue_id}` | `require_recent_active_admin` | No current frontend caller | Deferred to WS03-03B |
| Platform notice create | Admin | `POST /admin/platform-notices` | `require_recent_active_admin` | `AdminPlatformNoticesPage` | Deferred to WS03-03B |
| Platform notice cancel | Admin | `POST /admin/platform-notices/{notice_id}/cancel` | `require_recent_active_admin` | `AdminPlatformNoticesPage` | Deferred to WS03-03B |
| Saved card default change | Current user | `PATCH /user-payment-methods/{payment_method_id}/default` | `require_recent_active_user` | `PaymentMethodsPage` | Not required for current-user saved-card management |
| Saved card detach | Current user | `DELETE /user-payment-methods/{payment_method_id}` | `require_recent_active_user` | `PaymentMethodsPage` | Not required for current-user saved-card management |

### 5.5 Complete Current Admin Mutation Partition

Gate A dynamically inspected the current FastAPI app and classified every
current admin-access mutation registration using method/path, dependency graph,
route status, route semantics, and current service effects. `backend/tests/legacy`
was excluded. The partition is:

- `RECENT_AUTH_REQUIRED`: 22 admin-access routes from the high-risk matrix.
- `RECENT_AUTH_NOT_REQUIRED`: 38 executing admin-access routes intentionally
  left at active-admin/verified-user authority for this pass.
- `RETIRED_OR_NON_EXECUTING_MUTATION`: 47 registered admin-access mutations
  that are 410 tombstones or disabled generic user mutations.

#### 5.5.1 RECENT_AUTH_REQUIRED

| Method | Route | Reason |
|---|---|---|
| `DELETE` | `/games/{game_id}` | Terminal admin game soft-delete. |
| `DELETE` | `/venues/{venue_id}` | Terminal admin venue soft-delete. |
| `PATCH` | `/admin/users/{user_id}/role` | Admin role grant/removal. |
| `PATCH` | `/payment-events/{payment_event_id}` | Financial/provider repair. |
| `POST` | `/admin/community-games/{game_id}/cancel` | Terminal community-game cancellation. |
| `POST` | `/admin/game-credits/issue` | Ledger credit issuance. |
| `POST` | `/admin/game-credits/{game_credit_id}/reverse` | Ledger credit reversal. |
| `POST` | `/admin/money/financial-outcomes` | Financial outcome creation. |
| `POST` | `/admin/money/issues/{money_issue_id}/resolve` | Money issue resolution. |
| `POST` | `/admin/money/issues/{money_issue_id}/retry-credit` | Credit repair retry. |
| `POST` | `/admin/money/refunds/{refund_id}/reconcile` | Refund provider reconciliation. |
| `POST` | `/admin/money/refunds/{refund_id}/retry` | Refund provider retry. |
| `POST` | `/admin/need-a-sub/{post_id}/remove` | Terminal Need-a-Sub removal. |
| `POST` | `/admin/official-games/{game_id}/cancel` | Terminal official-game cancellation. |
| `POST` | `/admin/official-games/{game_id}/participants/{participant_id}/remove` | Paid-player removal can refund, restore credit, cancel booking, advance waitlist, and create money issues. |
| `POST` | `/admin/platform-notices` | Privileged platform notice creation. |
| `POST` | `/admin/platform-notices/{notice_id}/cancel` | Privileged platform notice cancellation. |
| `POST` | `/admin/users/{user_id}/delete` | Admin account deletion. |
| `POST` | `/admin/users/{user_id}/restrict-hosting` | Persistent hosting capability restriction. |
| `POST` | `/admin/users/{user_id}/restore-hosting` | Persistent hosting capability restoration. |
| `POST` | `/admin/users/{user_id}/suspend` | Admin account suspension. |
| `POST` | `/admin/users/{user_id}/unsuspend` | Admin account unsuspension. |

#### 5.5.2 RECENT_AUTH_NOT_REQUIRED

| Method | Route | Classification |
|---|---|---|
| `PATCH` | `/admin/official-games/{game_id}` | Routine official-game edit; not cancellation/removal. |
| `PATCH` | `/admin/venue-images/{venue_image_id}` | Venue-image lifecycle update; WS06/provider-storage owner remains later. |
| `PATCH` | `/community-game-details/{community_game_detail_id}` | Staff community-game detail metadata update. |
| `POST` | `/admin/community-games/{game_id}/chat/messages/{message_id}/remove` | Routine admin chat moderation. |
| `POST` | `/admin/community-games/{game_id}/chat/messages/{message_id}/restore` | Routine admin chat moderation. |
| `POST` | `/admin/community-games/{game_id}/chat/messages/{message_id}/review` | Routine admin chat moderation. |
| `POST` | `/admin/community-games/{game_id}/flag-for-review` | Review workflow creation, not terminal enforcement. |
| `POST` | `/admin/community-games/{game_id}/hide` | Reversible community moderation. |
| `POST` | `/admin/community-games/{game_id}/hide-payment-text` | Reversible payment-text moderation. |
| `POST` | `/admin/community-games/{game_id}/pause-joining` | Reversible joining moderation. |
| `POST` | `/admin/community-games/{game_id}/restore` | Reversible community moderation. |
| `POST` | `/admin/community-games/{game_id}/restore-payment-text` | Reversible payment-text moderation. |
| `POST` | `/admin/community-games/{game_id}/resume-joining` | Reversible joining moderation. |
| `POST` | `/admin/need-a-sub/{post_id}/chat/messages/{message_id}/remove` | Routine Need-a-Sub chat moderation. |
| `POST` | `/admin/need-a-sub/{post_id}/chat/messages/{message_id}/restore` | Routine Need-a-Sub chat moderation. |
| `POST` | `/admin/need-a-sub/{post_id}/chat/messages/{message_id}/review` | Routine Need-a-Sub chat moderation. |
| `POST` | `/admin/need-a-sub/{post_id}/hide` | Reversible Need-a-Sub moderation. |
| `POST` | `/admin/need-a-sub/{post_id}/restore` | Reversible Need-a-Sub moderation. |
| `POST` | `/admin/official-games` | Official-game creation/editing surface, not terminal lifecycle. |
| `POST` | `/admin/official-games/{game_id}/cancel-preview` | Preview-only; no cancellation execution. |
| `POST` | `/admin/official-games/{game_id}/chat/messages/{message_id}/remove` | Routine admin chat moderation. |
| `POST` | `/admin/official-games/{game_id}/chat/messages/{message_id}/restore` | Routine admin chat moderation. |
| `POST` | `/admin/official-games/{game_id}/chat/messages/{message_id}/review` | Routine admin chat moderation. |
| `POST` | `/admin/official-games/{game_id}/host` | Official-game host assignment; roster/admin workflow, not account privilege. |
| `POST` | `/admin/official-games/{game_id}/host/remove` | Official-game host removal; roster/admin workflow, not account privilege. |
| `POST` | `/admin/official-games/{game_id}/participants/{participant_id}/remove-preview` | Preview-only; no removal execution. |
| `POST` | `/admin/official-games/{game_id}/players` | Official-game roster add without provider repair/terminal removal. |
| `POST` | `/admin/review-cases/{review_case_id}/close` | Admin review case-management outcome. |
| `POST` | `/admin/review-cases/{review_case_id}/notes` | Admin review note. |
| `POST` | `/admin/support-flags/{support_flag_id}/resolve` | Support flag case-management outcome. |
| `POST` | `/admin/users/{user_id}/delete-preview` | Preview-only; no account deletion execution. |
| `POST` | `/admin/users/{user_id}/hosting-restriction-preview` | Preview-only; no hosting state mutation. |
| `POST` | `/admin/users/{user_id}/suspension-preview` | Preview-only; no suspension execution. |
| `POST` | `/admin/venue-images/{venue_image_id}/complete` | Venue-image upload completion; WS06/provider-storage owner remains later. |
| `POST` | `/admin/venues/{venue_id}/images/upload-url` | Venue-image upload authorization; WS06/provider-storage owner remains later. |
| `POST` | `/community-game-details` | Staff community-game detail creation. |
| `POST` | `/games` | Admin game listing creation, not terminal lifecycle. |
| `PATCH` | `/games/{game_id}` | Admin game edit with current request-ownership bounds, not delete/cancel. |

#### 5.5.3 RETIRED_OR_NON_EXECUTING_MUTATION

| Method | Route | Classification |
|---|---|---|
| `DELETE` | `/admin/official-games/{game_id}/host` | Retired 410 direct host DELETE. |
| `DELETE` | `/admin/official-games/{game_id}/participants/{participant_id}` | Retired 410 direct participant DELETE. |
| `DELETE` | `/users/{user_id}` | Disabled generic user mutation; raises 403. |
| `PATCH` | `/booking-policy-acceptances/{booking_policy_acceptance_id}` | Retired 410 scaffold. |
| `PATCH` | `/booking-status-history/{history_id}` | Retired 410 scaffold. |
| `PATCH` | `/bookings/{booking_id}` | Retired 410 scaffold. |
| `PATCH` | `/game-chats/{game_chat_id}` | Retired 410 scaffold. |
| `PATCH` | `/game-images/{game_image_id}` | Retired 410 scaffold. |
| `PATCH` | `/game-participants/{participant_id}` | Retired 410 scaffold. |
| `PATCH` | `/game-status-history/{history_id}` | Retired 410 scaffold. |
| `PATCH` | `/host-publish-fees/{host_publish_fee_id}` | Retired 410 scaffold. |
| `PATCH` | `/need-a-sub/posts/{sub_post_id}/remove` | Retired 410 duplicate removal path. |
| `PATCH` | `/notifications/{notification_id}` | Retired 410 scaffold. |
| `PATCH` | `/participant-status-history/{history_id}` | Retired 410 scaffold. |
| `PATCH` | `/payments/{payment_id}` | Retired 410 scaffold. |
| `PATCH` | `/policy-acceptances/{policy_acceptance_id}` | Retired 410 scaffold. |
| `PATCH` | `/policy-documents/{policy_document_id}` | Retired 410 scaffold. |
| `PATCH` | `/refunds/{refund_id}` | Retired 410 scaffold. |
| `PATCH` | `/user-settings/{user_id}` | Retired 410 scaffold. |
| `PATCH` | `/user-stats/{user_id}` | Retired 410 scaffold. |
| `PATCH` | `/users/{user_id}` | Disabled generic user mutation; raises 403. |
| `PATCH` | `/venue-approval-requests/{venue_approval_request_id}` | Retired 410 scaffold. |
| `PATCH` | `/venues/{venue_id}` | Retired 410 scaffold. |
| `PATCH` | `/waitlist-entries/{waitlist_entry_id}` | Retired 410 scaffold. |
| `POST` | `/admin/actions` | Retired 410 direct audit-action creation. |
| `POST` | `/admin/actions/{admin_action_id}/notes` | Retired 410 direct audit-action notes. |
| `POST` | `/booking-policy-acceptances` | Retired 410 scaffold. |
| `POST` | `/booking-status-history` | Retired 410 scaffold. |
| `POST` | `/bookings` | Retired 410 scaffold. |
| `POST` | `/game-chats` | Retired 410 scaffold. |
| `POST` | `/game-images` | Retired 410 scaffold. |
| `POST` | `/game-participants` | Retired 410 scaffold. |
| `POST` | `/game-status-history` | Retired 410 scaffold. |
| `POST` | `/host-publish-fees` | Retired 410 scaffold. |
| `POST` | `/notifications` | Retired 410 scaffold. |
| `POST` | `/participant-status-history` | Retired 410 scaffold. |
| `POST` | `/payment-events` | Retired 410 provider-event creation path. |
| `POST` | `/payments` | Retired 410 scaffold. |
| `POST` | `/policy-acceptances` | Retired 410 scaffold. |
| `POST` | `/policy-documents` | Retired 410 scaffold. |
| `POST` | `/refunds` | Retired 410 scaffold. |
| `POST` | `/user-settings` | Retired 410 scaffold. |
| `POST` | `/user-stats` | Retired 410 scaffold. |
| `POST` | `/users` | Disabled generic user mutation; raises 403. |
| `POST` | `/venue-approval-requests` | Retired 410 scaffold. |
| `POST` | `/venues` | Retired 410 scaffold. |
| `POST` | `/waitlist-entries` | Retired 410 scaffold. |

If Gate B evidence finds that one of the `RECENT_AUTH_NOT_REQUIRED` routes
currently performs a WS03-03A high-risk action without recent-auth, the pass
must stop for Gate A correction instead of silently expanding the matrix.

### 5.6 Frontend Step-Up Contract

Frontend source owns user-facing recovery from `AUTH.RECENT_AUTH_REQUIRED`.

Required contracts:

- `frontend/src/lib/stepUpAction.js` recognizes the public error code from the
  normalized API error and retries only the supplied caller-owned action after
  `requestStepUp` succeeds.
- `frontend/src/lib/apiClient.js` parses public error codes but does not
  globally intercept recent-auth failures or replay mutations.
- `frontend/src/lib/reauthentication.js` selects password or Google provider
  reauth from Firebase provider data.
- Email/password reauth uses `EmailAuthProvider.credential` and
  `reauthenticateWithCredential`, then forces `firebaseUser.getIdToken(true)`.
- Google reauth uses `reauthenticateWithPopup`, then forces
  `firebaseUser.getIdToken(true)`.
- Reauth failure or cancellation does not refresh the token and does not replay
  the original action.
- `StepUpProvider` exposes only `confirmStepUp` and `runWithStepUp` to
  deliberate callers.
- `AdminCommunityGameActionModal` must wrap only the terminal `cancel` action in
  caller-owned `runWithStepUp`; ordinary reversible community actions remain
  direct.
- The cancellation retry must reuse the same cancellation idempotency key for
  the deliberate retry after successful step-up.
- The separate publish-fee financial-outcome step-up remains independently
  wrapped and must not be confused with the cancellation step-up.
- `AdminNeedASubRemovalModal` must wrap only the terminal `remove` action in
  caller-owned `runWithStepUp`; hide and restore remain direct.
- `AdminUserHostingRestrictionModal` and
  `AdminUserHostingRestorationModal` must wrap the execution calls in
  caller-owned `runWithStepUp` while preserving their existing idempotency
  keys and preview handling.
- `AdminOfficialGamePage` must wrap official-player removal execution in
  caller-owned `runWithStepUp` while preserving the preview token, selected
  outcome, reason, and existing stale-preview refresh behavior.
- No current frontend caller was found for `DELETE /games/{game_id}`,
  `DELETE /venues/{venue_id}`, or `PATCH /payment-events/{payment_event_id}`.
  If a frontend caller appears before Gate B, it must be inspected and wrapped
  before the plan can remain frozen.

The password is frontend-to-Firebase only. Pickup Lane backend APIs must not
receive passwords, provider popup results, OAuth access tokens, refresh tokens,
or raw provider credentials as part of step-up.

### 5.7 Credential-Linking Boundary

The current exposed credential-linking flow is add-password for a signed-in
Google user.

Required contracts:

- the settings/profile caller performs explicit step-up before
  `addPasswordToCurrentAccount`;
- `addPasswordToCurrentAccount` calls Firebase `linkWithCredential` for the
  current `firebaseUser`;
- no backend route receives the new password;
- no local merge/relink route uses email to attach a different Firebase UID to
  an existing Pickup Lane user;
- WS03-02's stable UID and same-email/different-UID protections remain intact.

### 5.8 No Persisted Freshness Authority

Recent-auth freshness must stay request-scoped.

Gate B evidence must inspect current models, migrations, schemas, services,
routes, settings, frontend source, and current trusted test helpers for:

- `auth_time` or `authenticated_at` persisted outside request identity;
- recent-auth booleans or timestamps in request/response schemas;
- browser `localStorage`, `sessionStorage`, IndexedDB, cookies, or cache values
  used as freshness;
- PostgreSQL user/account/admin timestamps used as recent-auth proof;
- purpose flags or test helpers that bypass route freshness with request-owned
  values;
- telemetry or logs that expose raw provider freshness values.

## 6. Current Source Findings

Gate A inspected current accepted source, not historical branch state.

Current source is aligned on provider-freshness primitives, but the prior
route matrix was incomplete. The approved correction now requires a batch
high-risk route reconciliation:

- `backend/settings.py` defines
  `DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS = 5 * 60` and includes
  `recent_authentication_window_seconds` on `BackendSettings`.
- `backend/services/auth_service.py` parses provider `auth_time`, stores it
  only in `VerifiedFirebaseIdentity.authenticated_at`, evaluates exact
  freshness boundaries, returns `AUTH.RECENT_AUTH_REQUIRED`, and defines the
  recent-auth dependency wrappers.
- `backend/services/recent_auth_policy.py` defines the high-risk action
  inventory and exposes route keys and the public error code. Gate B must
  reconcile it to the full 25-route matrix in this plan, including
  community-game cancellation, Need-a-Sub removal, hosting
  restriction/restoration, official-player removal execution, game
  soft-delete, venue soft-delete, and payment-event repair.
- Current FastAPI route registration must be reconciled so every route in the
  25-route matrix is wired to `require_recent_app_user`,
  `require_recent_active_user`, or `require_recent_active_admin` as specified.
  Any matrix route still using only `require_active_admin` is an in-scope Gate B
  production correction.
- `backend/services/community_game_enforcement_service.py` implements terminal
  admin community-game cancellation through `admin_cancel_community_game`, row
  locking, idempotent admin-action lookup, `apply_game_cancellation_state`,
  cancellation audit, review-case closure, and host notice behavior.
- `frontend/src/context/StepUpProvider.jsx`, `frontend/src/lib/stepUpAction.js`,
  `frontend/src/lib/reauthentication.js`, and
  `frontend/src/context/authProviderReauthenticationActions.js` provide the
  source-owned step-up path.
- `frontend/src/lib/apiClient.js` has no generic mutation replay interceptor.
- `frontend/src/pages/admin/community-games/AdminCommunityGameActionModal.jsx`
  is the current production caller for `cancelAdminCommunityGame`; it already
  has `runWithStepUp` for the subsequent financial-outcome operation but must
  also wrap the terminal cancellation action itself.
- `frontend/src/pages/admin/need-a-sub/AdminNeedASubRemovalModal.jsx` is the
  current production caller for Need-a-Sub hide, restore, and remove. Remove is
  terminal and must be wrapped; hide and restore must stay intentionally direct.
- `frontend/src/pages/admin/users/AdminUserHostingRestrictionModal.jsx` and
  `frontend/src/pages/admin/users/AdminUserHostingRestorationModal.jsx` are the
  current production callers for hosting capability mutation and currently call
  the API directly.
- `frontend/src/pages/admin/official-games/manage/AdminOfficialGamePage.jsx`
  wraps official-game cancellation but currently calls official-player removal
  execution directly.
- No current frontend source caller was found for admin game soft-delete,
  venue soft-delete, or payment-event repair.
- Current frontend unit tests for `reauthentication` and `stepUpAction` exist
  as corroborating validation, but they are not the trusted backend checker
  traceability layer for WS03-03A.
- Current trusted backend tests mention recent-auth as a later-owner surface in
  WS03-01/WS03-02, but no current trusted `recent_auth_step_up` workflow scope
  or `ws03_03a.json` requirement declaration exists.

The approved source correction is still narrow in kind: update recent-auth
policy entries, route dependencies, and existing frontend caller-owned step-up
wrapping for the routes identified in this plan. No service rewrite, schema
change, shared infrastructure change, provider change, migration, new frontend
test, or new proof layer is planned.

The five-minute threshold remains unchanged. It lacks a separate prior
decision/register row and was explicitly presented for human Gate A approval.

## 7. Implementation Scope

### 7.1 Gate A Scope

Gate A modifies only this canonical plan:

1. `docs/production-readiness/planning/ws03-03a-recent-auth-step-up.md`

Gate A does not create tests, requirement JSON, a `TESTING_RECORD.md`,
production source changes, frontend source changes, frontend tests,
migrations, commits, or a PR.

### 7.2 Gate B Remediation Type

Final Gate A classification: **narrow backend + frontend source correction plus
trusted evidence and cross-pass request-ownership compatibility correction**.

Gate B must implement only the approved production correction, requirement
metadata reconciliation, testing-record correction, and trusted evidence
correction described here, plus the cross-pass trusted evidence compatibility
correction in `backend/tests/workflows/request_ownership` listed below. The
cross-pass correction is evidence-only and does not create a new WS03-03A
requirement owner. No migration/model correction, shared testing-infrastructure
correction, provider/dashboard mutation, new frontend test, or browser runtime
proof is approved.

If Gate B evidence exposes another actual in-scope source defect, Gate B must
stop for Gate A correction instead of broadening this frozen file set.

### 7.3 Exact Gate B Editable File Set

Gate B may edit exactly these twenty-one files:

1. `backend/tests/support/requirements/ws03_03a.json`
2. `backend/tests/workflows/recent_auth_step_up/TESTING_RECORD.md`
3. `backend/tests/workflows/recent_auth_step_up/test_provider_auth_time_contract.py`
4. `backend/tests/workflows/recent_auth_step_up/test_recent_auth_dependency_contract.py`
5. `backend/tests/workflows/recent_auth_step_up/test_recent_auth_route_inventory_contract.py`
6. `backend/tests/workflows/recent_auth_step_up/test_frontend_step_up_contract.py`
7. `backend/tests/workflows/recent_auth_step_up/test_recent_auth_negative_space_contract.py`
8. `backend/services/recent_auth_policy.py`
9. `backend/routes/admin_community_routes.py`
10. `backend/routes/admin_user_routes.py`
11. `backend/routes/admin_need_a_sub_routes.py`
12. `backend/routes/admin_official_game_routes.py`
13. `backend/routes/game_routes.py`
14. `backend/routes/venue_routes.py`
15. `backend/routes/payment_event_routes.py`
16. `frontend/src/pages/admin/community-games/AdminCommunityGameActionModal.jsx`
17. `frontend/src/pages/admin/users/AdminUserHostingRestrictionModal.jsx`
18. `frontend/src/pages/admin/users/AdminUserHostingRestorationModal.jsx`
19. `frontend/src/pages/admin/need-a-sub/AdminNeedASubRemovalModal.jsx`
20. `frontend/src/pages/admin/official-games/manage/AdminOfficialGamePage.jsx`
21. `backend/tests/workflows/request_ownership/test_game_specialized_mutation_authority_contract.py`

Do not edit any other production backend source, frontend source, frontend
tests, migrations, shared testing infrastructure, other pass plans, other
requirement JSON files, or other `TESTING_RECORD.md` files during Gate B unless
a new Gate A correction approves that wider scope.

Existing frontend unit tests, frontend lint, and frontend build are required
validation because Gate B changes production frontend source. Frontend tests
remain outside the planned Gate B editable set.

### 7.4 Approved Production Correction Design

Gate B must apply the correction in this order:

1. Reconcile `RECENT_AUTH_PROTECTED_ACTIONS` to the 25-route matrix in this
   plan. Each entry must have a specific unique action ID, actor, method,
   route template, enforcement dependency, frontend caller or explicit
   no-current-frontend-caller note, protections derived from current source,
   provider MFA disposition, and `recent_auth_required = True`.
2. In route files, change only the high-risk route dependencies named in the
   matrix to `require_recent_active_admin`. Preserve all existing body models,
   route methods, paths, status codes, service calls, preview routes, state
   guards, idempotency behavior, and ordinary active-admin dependencies for
   intentionally ungated routes.
3. In `AdminCommunityGameActionModal.jsx`, wrap only the `cancel` action's API
   call in `runWithStepUp`. Keep hide, restore, pause, resume, payment-text
   restore, and other reversible actions unchanged. Preserve the existing
   cancellation idempotency key across the caller-owned retry. Keep the
   subsequent publish-fee financial-outcome step-up independent and unchanged in
   meaning.
4. In `AdminNeedASubRemovalModal.jsx`, wrap only `action === "remove"` in
   caller-owned `runWithStepUp`. Hide and restore remain direct and keep their
   current idempotency behavior.
5. In `AdminUserHostingRestrictionModal.jsx` and
   `AdminUserHostingRestorationModal.jsx`, wrap the execution call in
   caller-owned `runWithStepUp`, preserve current preview/stale-preview
   behavior for restriction, and preserve the existing idempotency key across
   deliberate retry.
6. In `AdminOfficialGamePage.jsx`, wrap only official-player removal execution
   in caller-owned `runWithStepUp`. Keep official-game cancellation's existing
   step-up independent. Preserve preview token, selected outcome, reason, and
   the existing 409 stale-preview refresh behavior.
7. Reconcile requirement metadata and evidence artifacts with the 25-route
   policy, the complete admin mutation partition, and the corrected R3/R5/R6/R8
   proof descriptions.

### 7.5 Cross-Pass Request-Ownership Compatibility Correction

The approved production correction legitimately strengthens selected routes
from `require_active_admin` to `require_recent_active_admin`. Current source shows
`require_recent_active_admin` depends on `require_active_admin` and adds the
WS03-03A recent-auth prerequisite, so it preserves the active-admin authority
required by WS02-05B1 while strengthening authentication freshness for
high-risk admin actions.

If the full backend regression fails
`backend/tests/workflows/request_ownership/test_game_specialized_mutation_authority_contract.py::test_specialized_mutation_routes_bind_purpose_schemas_and_actor_dependencies`
because the B1 specialized-route table still expects `ACTIVE_ADMIN_DEPENDENCY`
for an in-matrix specialized game route, Gate B must treat that as stale
WS02-05B1 trusted evidence, not a WS03-03A production regression.

Gate B may update only these route specs' expected dependency from
`ACTIVE_ADMIN_DEPENDENCY` to `RECENT_ACTIVE_ADMIN_DEPENDENCY` if needed:

- `POST /admin/community-games/{game_id}/cancel`
- `POST /admin/official-games/{game_id}/participants/{participant_id}/remove`

It must preserve `AdminCommunityGameEnforcementActionCreate`,
`AdminOfficialGamePlayerRemovalExecute`, every other route spec, every other
dependency expectation, the WS02-05B1 requirement marker, request/body schema
assertions, OpenAPI protected-field assertions, and all other
request-ownership behavior. Do not redesign WS02-05B1, add a new requirement,
move the test, or weaken a production route back to `require_active_admin`.

This compatibility correction does not change R1-R14, the R1-R11 required
states, the R12-R14 deferred/governance states, the five-minute threshold, the
25-route high-risk matrix, or the approved production correction set.

## 8. Testing And Evidence Design

### 8.1 Requirement Declaration Design

Gate B must create `backend/tests/support/requirements/ws03_03a.json` with
these states and checker-compatible scopes:

| Requirement ID | State | Scope | Source controls | Reason |
|---|---|---|---|---|
| `WS03-03A-R1` | `required` | `workflows/recent_auth_step_up` | `["IAM-008", "IDB-01", "IDB-02", "WS03-01", "WS03-03A"]` | Provider `auth_time` is the only accepted source-owned recent-auth authority. |
| `WS03-03A-R2` | `required` | `workflows/recent_auth_step_up` | `["IAM-008", "GOV-006", "WS03-03A"]` | The five-minute WS03-03A threshold and exact boundary behavior need controlled evidence after plan approval. |
| `WS03-03A-R3` | `required` | `workflows/recent_auth_step_up` | `["IAM-008", "EN-02", "WS02-04A", "WS03-03A"]` | Recent-auth denial must use the stable safe public error envelope. |
| `WS03-03A-R4` | `required` | `workflows/recent_auth_step_up` | `["IAM-004", "IAM-007", "IAM-008", "WS03-01", "WS03-02"]` | Recent-auth wrappers must preserve accepted identity, account-state, verified-email, and admin authority. |
| `WS03-03A-R5` | `required` | `workflows/recent_auth_step_up` | `["IAM-008", "IAM-017", "PAY-011", "ADM-013", "WS03-03A"]` | Current high-risk account/admin/terminal-lifecycle/financial-repair/notice/saved-card routes must require recent auth. |
| `WS03-03A-R6` | `required` | `workflows/recent_auth_step_up` | `["IAM-003", "IAM-008", "IDB-01", "WS03-03A"]` | Intentionally ungated and retired/non-executing routes must remain classified, and high-risk routes must not become silent bypasses. |
| `WS03-03A-R7` | `required` | `workflows/recent_auth_step_up` | `["IAM-008", "IDB-01", "WS03-03A"]` | Frontend password and Google step-up must use Firebase reauth safely and fail closed. |
| `WS03-03A-R8` | `required` | `workflows/recent_auth_step_up` | `["IAM-003", "FE-M04", "IDB-01", "WS03-03A"]` | Step-up retry must remain caller-owned with no blind global mutation replay. |
| `WS03-03A-R9` | `required` | `workflows/recent_auth_step_up` | `["IAM-005", "IAM-009", "IDB-02", "WS03-02", "WS03-03A"]` | Credential linking requires step-up and remains provider-owned without local relink authority. |
| `WS03-03A-R10` | `required` | `workflows/recent_auth_step_up` | `["IAM-006", "IAM-008", "IDB-02", "EN-03", "WS03-03A"]` | Freshness must not be persisted, mirrored, logged, or accepted as app-owned authority. |
| `WS03-03A-R11` | `required` | `workflows/recent_auth_step_up` | `["IAM-008", "IAM-010", "IAM-011", "EN-03", "WS03-03A"]` | Negative-space inventory must fail closed for bypasses, admin mutation partition drift, route-family misclassification, and false provider/governance closure. |
| `WS03-03A-R12` | `deferred` | `governance` | `["IAM-008", "WS03-03B", "WS10"]` | Administrator MFA provider/governance evidence cannot be closed by local WS03-03A pytest and must have zero pytest mappings. |
| `WS03-03A-R13` | `deferred` | `governance` | `["IAM-010", "IDB-04", "WS03-03B", "WS10"]` | Firebase App Check provider/runtime evidence cannot be closed by local WS03-03A pytest and must have zero pytest mappings. |
| `WS03-03A-R14` | `deferred` | `governance` | `["IAM-011", "EN-03", "WS03-03B", "WS10"]` | Firebase/GCP credential governance cannot be closed by local WS03-03A pytest and must have zero pytest mappings. |

### 8.2 Evidence Architecture

| Planned artifact | Requirements | Responsibility |
|---|---|---|
| `backend/tests/support/requirements/ws03_03a.json` | R1-R14 | Declare machine-readable requirement IDs, owning pass, source controls, states, and checker-compatible scopes. R12-R14 remain `deferred` / `governance`. |
| `TESTING_RECORD.md` | R1-R14 | Human evidence record for threat model, authority basis, five-minute approval note, corrected 25-route matrix, complete admin mutation partition, frontend retry risks, provider fake limits, deferred evidence, and adequacy. It must describe any synthetic probe route honestly and must not call it a real self-delete/local-user proof. |
| `test_provider_auth_time_contract.py` | R1, R2, R10 | Prove `auth_time` parsing, missing/malformed/future/stale/exact-boundary behavior, centralized five-minute setting use, no `iat` fallback, and request-scoped/non-persisted freshness semantics. |
| `test_recent_auth_dependency_contract.py` | R3, R4, R5 | Prove stale/missing recent auth returns the stable safe 403 public envelope; prove any synthetic probe as a controlled dependency/error-envelope check only; prove real protected-route stale/missing/fresh behavior for terminal community cancellation and terminal Need-a-Sub removal before their services execute; prove fresh recent auth reaches the existing route workflow or a route-level service sentinel; prove recent-app-user, recent-active-user, and recent-active-admin wrappers layer on accepted identity/account/admin dependencies without replacing them. |
| `test_recent_auth_route_inventory_contract.py` | R5, R6, R11 | Dynamically inspect registered FastAPI routes against `RECENT_AUTH_PROTECTED_ACTIONS`, prove every protected route has the expected wrapper, prove the 25 protected route keys match the current policy, and classify every current admin-access mutation route into `RECENT_AUTH_REQUIRED`, `RECENT_AUTH_NOT_REQUIRED`, or `RETIRED_OR_NON_EXECUTING_MUTATION` without broad prefix exceptions or deferred provider fact mappings. |
| `test_frontend_step_up_contract.py` | R7, R8, R9 | Inspect frontend source for password and Google Firebase reauth, forced ID-token refresh after success, fail-closed cancellation/failure, opted-in high-risk caller usage including community cancellation, Need-a-Sub remove, hosting restrict/restore, official-player removal, existing money/notice/user/saved-card callers, no low-level API replay interceptor, preserved idempotency or preview tokens across caller-owned retry where applicable, independent publish-fee financial-outcome step-up, and add-password step-up before Firebase linking. |
| `test_recent_auth_negative_space_contract.py` | R1, R5, R6, R8, R10, R11 | Static/dynamic fail-closed inventory for freshness bypasses, duplicated policies, request/client timestamp authority, persisted `auth_time`, browser-storage freshness, generic replay, password/token forwarding, unclassified high-risk routes, complete admin mutation partition drift, route-family misclassification across community/Need-a-Sub/official/user/game/venue/payment-event surfaces, current trusted helper bypasses, and any pytest mapping for R12-R14. |

No pytest may map `WS03-03A-R12`, `WS03-03A-R13`, or `WS03-03A-R14`.

### 8.3 Negative-Space Strategy

Gate B negative-space evidence must fail closed if a new active path appears
that could bypass WS03-03A invariants.

The inventory must evaluate:

- high-risk route keys registered without the expected recent-auth wrapper;
- terminal/destructive actions classified as reversible or routine moderation;
- any new current admin-access mutation route without explicit route/action
  classification;
- high-risk routes that use only `require_active_admin`;
- protected policy entries missing from registered routes, and registered
  route method/path pairs missing from the policy;
- recent-auth route wrappers that bypass base identity/account/admin
  dependencies;
- alternate recent-auth windows, duplicate constants, or policy copies outside
  the current owner;
- use of `iat`, request timestamps, browser timestamps, local storage,
  session storage, cookies, IndexedDB, Postgres timestamps, booleans, or
  purpose flags as freshness authority;
- raw decoded-token dictionaries passed into business services as recent-auth
  authority;
- current trusted backend test helpers that bypass recent-auth through unsafe
  request-shaped freshness values rather than explicit dependency overrides;
- frontend low-level API interceptors that replay mutations globally;
- high-risk frontend call sites missing caller-owned step-up wrapping;
- password, token, provider popup result, or credential forwarding to backend
  APIs, logs, telemetry, or storage;
- persisted or response-exposed `auth_time`;
- pytest mappings for deferred App Check, MFA, or credential-governance
  requirements.

The negative-space test may inspect source text, ASTs, current trusted test
helpers, and FastAPI route/dependency inventory where that is the lowest
reliable layer. It must stay narrower than WS03-04 object-level authorization,
WS07 browser cache isolation, and WS10 provider-governance evidence.

The route inventory must use structured route/action classification for
community-game, Need-a-Sub, official-game, admin-user, game, venue, and
payment-event administration. It must not contain blanket rules such as
`/admin/community-games`, `/admin/need-a-sub`, `/admin/official-games`,
`/games`, `/venues`, or `/payment-events` equals ordinary or routine.
Legitimate exceptions must be explicit.

### 8.4 TESTING_RECORD Design

Gate B must create
`backend/tests/workflows/recent_auth_step_up/TESTING_RECORD.md` from the
current template. It must include:

- recent-auth threat model;
- authority basis and current source truth/provenance;
- five-minute threshold approval note and reassessment trigger;
- provider `auth_time` versus token issue time and app-owned timestamps;
- exact boundary matrix;
- public error-envelope and redaction expectations;
- honest distinction between a controlled synthetic dependency/error-envelope
  probe and real protected-route evidence;
- real `POST /admin/community-games/{game_id}/cancel` stale/missing
  recent-auth rejection proof, including proof the cancellation workflow did not
  execute;
- real `POST /admin/need-a-sub/{post_id}/remove` stale/missing/fresh
  recent-auth proof, including proof stale/missing recent auth cannot execute
  `remove_need_a_sub_post_by_admin` or produce removal side effects;
- backend dependency-layering proof;
- corrected 25-route high-risk route matrix;
- complete current admin mutation partition with
  `RECENT_AUTH_REQUIRED`, `RECENT_AUTH_NOT_REQUIRED`, and
  `RETIRED_OR_NON_EXECUTING_MUTATION` categories;
- intentionally ungated route classifications with terminal cancellation,
  terminal removal, hosting capability mutation, paid-player removal,
  soft-delete, and payment-event repair outside ordinary/reversible categories;
- frontend step-up method matrix;
- caller-owned retry/no-blind-replay reasoning;
- add-password credential-linking boundary;
- no-persisted-freshness review;
- provider fake/source-inspection limitations;
- why Playwright is not required for this pass;
- frontend unit test role as corroborating validation only;
- App Check, admin MFA, and Firebase/GCP credential-governance deferrals with
  zero pytest mappings;
- current source defect handling rule;
- adequacy conclusion.

### 8.5 Specialized Proof Decisions

| Layer / proof type | Required for WS03-03A Gate B? | Reason |
|---|---|---|
| PostgreSQL mutation proof | Yes, narrowly for corrected community-cancel and Need-a-Sub remove route rejection and side-effect prevention. | Recent-auth freshness is still request-scoped and must not create database state. The real route proof should use a valid admin identity shape so failure reaches recent-auth, and must prove the protected service did not execute or that meaningful side effects did not occur. No schema or persisted freshness proof is expected. |
| Frontend unit tests | Yes as validation for the changed frontend source, not checker traceability. | Existing `frontend/tests/unit/reauthentication.test.js` and `frontend/tests/unit/stepUpAction.test.js` prove helper behavior in the frontend layer; the complete unit suite must run after the modal correction. Stable requirement mappings remain in backend pytest per EN-01. |
| Frontend lint/build | Yes. | Gate B changes production frontend source, so `npm run lint` and `npm run build` must pass. |
| Playwright/browser runtime | No. | The pass can prove source-owned step-up selection/retry boundaries through frontend unit/source evidence. Full browser identity-switch/cache/runtime behavior remains WS07-02, and provider reauth runtime/App Check behavior remains provider/runtime evidence. |
| Firebase provider sandbox/runtime | No for WS03-03A local closure. | Gate B may fake provider token claims and inspect Firebase client calls. Live provider proof of reauth, App Check, MFA, and credential governance remains deferred. |
| Alembic migration validation | No. | No schema change or persisted freshness authority is approved. |

## 9. Validation Plan

Gate B must run the validation below after implementing the approved source,
evidence, and cross-pass compatibility set. Historical PR #128 validation
counts are not expected values.

1. Exact WS02-05B1 compatibility node:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/request_ownership/test_game_specialized_mutation_authority_contract.py::test_specialized_mutation_routes_bind_purpose_schemas_and_actor_dependencies
```

This node must pass by updating stale B1 expected dependencies only for the
authorized in-matrix specialized routes:

- `POST /admin/community-games/{game_id}/cancel`
- `POST /admin/official-games/{game_id}/participants/{participant_id}/remove`

The purpose-specific schemas and all other request-ownership assertions must be
preserved.

2. Focused WS02-05B1 request-ownership scope as appropriate:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/request_ownership
```

This focused scope verifies the compatibility correction does not weaken B1's
specialized mutation authority, generic request-ownership, or negative-space
evidence.

3. Focused WS03-03A trusted backend evidence:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/recent_auth_step_up
```

This focused suite must include corrected high-risk proof that:

- all 25 protected routes are in the policy and registered route matrix;
- every current admin-access mutation route is classified into the required
  partition;
- stale or missing recent auth returns `AUTH.RECENT_AUTH_REQUIRED`;
- stale or missing recent auth cannot execute the community cancellation or
  Need-a-Sub removal service or produce meaningful side effects;
- fresh recent auth reaches the existing route workflow or a route-level service
  sentinel for those real route proofs;
- reversible community and Need-a-Sub actions remain intentionally ungated;
- frontend source wraps only the newly high-risk callers in caller-owned
  step-up and preserves idempotency keys or preview tokens for deliberate retry.

4. Accepted WS03 dependency regressions:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/identity_authority backend/tests/workflows/account_lifecycle_concurrency
```

5. Focused route-lifecycle and provider-payment compatibility:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/route_lifecycle_cleanup backend/tests/workflows/provider_payment_input_ownership
```

This focused scope verifies Need-a-Sub and official-game replacement routes
remain canonical after adding recent-auth wrappers, and that payment-event
repair remains the retained provider-payment input ownership route. These tests
are compatibility validation, not WS03-03A requirement ownership.

6. Relevant business-domain regression:

No current trusted non-excluded community-cancellation or Need-a-Sub removal
business-domain suite was identified during Gate A. Gate B must state this
explicitly and rely on focused WS03-03A route/dependency proof plus the full
trusted backend regression. If a current trusted suite appears before Gate B,
use the smallest one that proves existing workflow behavior remains correct
after adding the auth prerequisite.

7. Frontend validation:

```bash
cd frontend
npm run test:unit
npm run lint
npm run build
```

If a targeted frontend unit command can isolate step-up retry behavior without
adding a new proof layer, Gate B may run it in addition to the complete unit
suite. Do not add frontend tests in WS03-03A Gate B.

8. Domain checker:

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/recent_auth_step_up
```

9. Suite checker:

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

10. Generated traceability review:

- report exact mapping counts for `WS03-03A-R1` through `WS03-03A-R14`;
- confirm `WS03-03A-R12`, `WS03-03A-R13`, and `WS03-03A-R14` have exactly
  zero pytest mappings.

11. Full trusted backend regression:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests
```

The full trusted backend regression must be fully green. Do not accept
`1047 passed, 1 failed` or any other failed result as complete.

12. Diff integrity:

```bash
git diff --check
git status --short --untracked-files=all
```

Playwright validation is not automatically required. The changed frontend
contract is source/caller-owned and can be proven through backend trusted
evidence, frontend source inspection, existing unit tests, lint, and build. If
Gate B cannot honestly prove caller-owned cancellation retry at that layer, it
must stop for Gate A instead of silently adding browser evidence.

No Alembic upgrade/downgrade validation is required because no migration is
approved. If Gate B discovers a schema requirement, it must stop for Gate A.

## 10. Provider, Runtime, And Later-Pass Handoffs

### 10.1 Provider / Runtime Unknowns

WS03-03A local evidence cannot close:

- actual live Firebase project reauth behavior;
- deployed provider `auth_time` behavior after real email/password or Google
  reauthentication;
- production provider revocation and disabled-account propagation timing beyond
  accepted WS03-01 source-owned fakes;
- Firebase App Check registration, token verification, staged enforcement,
  false-positive handling, provider-unavailable behavior, rollback, or
  production enforcement;
- administrator MFA support, enrollment, factor policy, break-glass stance,
  access-review proof, or runtime/admin sign-in verification;
- Firebase/GCP service-account least privilege, key inventory, storage,
  rotation, revocation, monitoring, emergency procedure, ADC/workload identity,
  or permanent-host binding;
- provider dashboard settings, real control-plane users, offboarding, recovery
  owner, or provider evidence freshness;
- full browser cache/logout/account-switch isolation;
- production runtime, edge, logs, telemetry, and alerting evidence.

These must remain explicit provider/runtime/governance gaps in the testing
record and final Gate B report.

### 10.2 Later Owners

- `WS03-03B`: App Check provider/runtime implementation and evidence,
  administrator MFA provider evidence, and Firebase/GCP credential-governance
  closure where scoped.
- `WS03-04`: complete object-level authorization, IDOR matrix, route-family
  action permissions, and 403/404 concealment.
- `WS05`: durable financial/provider reconciliation and retry workers where
  unknown provider outcomes require durable repair.
- `WS07-02`: full browser auth persistence, logout/account-switch private data
  clearing, cross-tab isolation, and broader frontend retry/state behavior.
- `WS09`: telemetry, metrics, dashboards, bounded labels, and runtime
  observability for recent-auth outcomes if later approved.
- `WS10`: provider access, secrets, service-account governance, incident
  response, runbooks, recovery, rotation/revocation, and operational records.

## 11. Migration, Rollback, And Compatibility

No migration is approved for WS03-03A.

Auth freshness is not stored. No database backfill, data migration, index, or
schema change is expected.

This is a paired backend/frontend contract correction:

- backend high-risk admin routes in the 25-route matrix use the existing stable
  public `AUTH.RECENT_AUTH_REQUIRED` denial contract when admin recent-auth is
  stale or missing;
- frontend high-risk callers identified in this plan add opted-in caller-owned
  recovery for those same actions;
- reversible community/Need-a-Sub moderation, previews, ordinary edits, and
  non-high-risk roster/support/review/upload routes keep their current
  dependencies;
- no API version split, generic replay interceptor, client-supplied purpose
  flag, new public error code, or database migration is approved.

Rollback, if needed before merge, must revert the production correction files
for the 25-route matrix together: recent-auth policy entries, route dependency
changes, and caller-owned step-up wrapping. Evidence artifacts must then be
reconciled back to the resulting source truth through a new Gate A correction
rather than edited ad hoc.

If Gate B tests expose a source/schema/frontend defect beyond this frozen scope,
Gate B must stop for Gate A correction instead of patching outside the approved
file set.

## 12. Completion Criteria

WS03-03A Gate B is complete only when:

- the approved backend policy, backend route, and frontend modal corrections are
  implemented;
- the exact Gate B file set is implemented and no unauthorized file changes
  exist;
- the cross-pass request-ownership compatibility correction updates only the
  stale authorized dependency expectations and preserves WS02-05B1
  purpose-specific schema and bypass assertions;
- requirement declaration R1-R14 states/scopes match this plan;
- R12-R14 have zero pytest mappings;
- the corrected 25-route high-risk matrix is enforced;
- the complete current admin mutation partition is enforced;
- real community-game cancellation and Need-a-Sub removal route evidence proves
  stale/missing recent auth is rejected before protected services execute;
- the exact WS02-05B1 compatibility node passes;
- focused WS02-05B1 request-ownership validation passes or is otherwise
  explicitly reported if no broader focused run is needed beyond the node;
- focused WS03-03A backend evidence passes;
- dependency regressions for WS03-01 and WS03-02 pass;
- focused route-lifecycle and provider-payment compatibility validation passes;
- frontend unit tests, lint, and build pass;
- domain checker and suite checker pass;
- generated traceability counts are reported exactly;
- full trusted backend regression passes;
- `git diff --check` passes;
- final changed-file status is exactly this canonical plan plus the twenty-one approved
  Gate B editable files;
- `TESTING_RECORD.md` honestly records provider/runtime/governance gaps and
  adequacy;
- Gate B final report does not claim App Check, admin MFA, Firebase/GCP
  credential governance, provider runtime, or production closure.

## 13. Gate A Freeze

After human approval, the corrected canonical plan SHA-256 supersedes the
previous frozen SHA `710bcde8481d538cbfe3574a76140ab3d4203149e2bdad8a2a06f88181afa628`.

The expected final pass changed-file set is exactly twenty-two files:

1. `docs/production-readiness/planning/ws03-03a-recent-auth-step-up.md`
2. `backend/tests/support/requirements/ws03_03a.json`
3. `backend/tests/workflows/recent_auth_step_up/TESTING_RECORD.md`
4. `backend/tests/workflows/recent_auth_step_up/test_provider_auth_time_contract.py`
5. `backend/tests/workflows/recent_auth_step_up/test_recent_auth_dependency_contract.py`
6. `backend/tests/workflows/recent_auth_step_up/test_recent_auth_route_inventory_contract.py`
7. `backend/tests/workflows/recent_auth_step_up/test_frontend_step_up_contract.py`
8. `backend/tests/workflows/recent_auth_step_up/test_recent_auth_negative_space_contract.py`
9. `backend/services/recent_auth_policy.py`
10. `backend/routes/admin_community_routes.py`
11. `backend/routes/admin_user_routes.py`
12. `backend/routes/admin_need_a_sub_routes.py`
13. `backend/routes/admin_official_game_routes.py`
14. `backend/routes/game_routes.py`
15. `backend/routes/venue_routes.py`
16. `backend/routes/payment_event_routes.py`
17. `frontend/src/pages/admin/community-games/AdminCommunityGameActionModal.jsx`
18. `frontend/src/pages/admin/users/AdminUserHostingRestrictionModal.jsx`
19. `frontend/src/pages/admin/users/AdminUserHostingRestorationModal.jsx`
20. `frontend/src/pages/admin/need-a-sub/AdminNeedASubRemovalModal.jsx`
21. `frontend/src/pages/admin/official-games/manage/AdminOfficialGamePage.jsx`
22. `backend/tests/workflows/request_ownership/test_game_specialized_mutation_authority_contract.py`
