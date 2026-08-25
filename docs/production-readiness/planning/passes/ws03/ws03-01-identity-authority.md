# WS03-01 - Identity Authority And Verifier-Controlled Field Protection

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS03-01` |
| Pass name | Identity Authority And Verifier-Controlled Field Protection |
| Track | `WS03` |
| Type | Domain implementation and trusted evidence reconstruction |
| Primary controls | `IAM-001`, `IAM-002`, `IAM-003`, `IAM-004`, `IAM-006`, `IAM-007`, `IAM-014` |
| Authority basis | Locked production-readiness checklist and audits; final remediation plan; approved decisions `IDB-01`, `IDB-02`, `IDB-03`; master blueprint `WS03-01`; accepted dependency pass boundaries; current accepted repository source |
| Depends on | `WS02-01`, `WS02-05A`, `WS02-05B1`, `WS02-05B2`, `EN-01`, `EN-02`, `EN-03`, approved decisions `IDB-01`, `IDB-02`, `IDB-03` |
| Accepted baseline | `9c81d2afd076cb38dbd182dcabc671125700407b` |
| Remediation branch | `pr/WS03-01-remediation` |
| Historical provenance | PR #126, `pr/WS03-01`, base `59deb5bec92dfb24170bbe63269b6429cb4e325c`, head `18344bd8c5539d051743f93eb2753b51ea665e75`, merge `c89a96b1ef409ef0fa315971cc958fd563bbec96` |
| Trusted test scope | `backend/tests/workflows/identity_authority` |

## 1. Purpose

WS03-01 establishes the repository-owned identity authority boundary for
protected Pickup Lane requests.

The pass makes it explicit which identity facts come from Firebase, which
application facts come from PostgreSQL, how protected requests combine those
facts, and which fields an ordinary user must never write. It also defines the
verified-email policy for WS03-01-owned route families and the narrow
browser-persistence/replay assumptions approved by `IDB-01`.

Current accepted `develop` is the repository truth for the current
implementation state. The authoritative production-readiness controls,
approved decisions, accepted dependency pass boundaries, and this reconciled
plan define what must be true. Historical PR #126 is provenance only: it may
explain where current behavior came from, but it does not define current
requirements and its historical tests are not trusted evidence.

Gate A reconciliation found no approved production or frontend correction for
this pass. WS03-01 Gate B is therefore an evidence reconstruction pass unless
new trusted evidence proves an in-scope implementation defect.

## 2. Why This Matters

Identity failures collapse several safety boundaries at once. If a protected
request trusts the wrong project, an unrevoked cached token, a disabled
provider account, a stale local verification timestamp, or client-supplied role
data, a user could perform actions they should not control.

The concrete risks are:

- accepting Firebase tokens that are not valid for the intended project;
- authorizing a request after token revocation or provider-account disablement;
- allowing a stale PostgreSQL snapshot to act as current email verification;
- letting ordinary profile updates write verifier, provider, or admin fields;
- granting admin access from client-side or Firebase custom claims instead of
  the local active admin role;
- persisting bearer tokens outside Firebase Auth or blindly replaying
  non-idempotent mutations after a refresh;
- overclaiming local test evidence for provider/runtime facts that only a real
  Firebase project or deployed runtime can prove.

This pass narrows those risks to explicit contracts and trusted evidence while
leaving object-level authorization, account lifecycle, MFA/App Check, and
browser private-cache isolation with their later owners.

## 3. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS03-01-R1` | Protected requests use project-bound Firebase ID-token verification and header-only bearer transport. | Backend-protected identity paths extract bearer credentials only from `Authorization`, verify them through the maintained Firebase Admin SDK using an app initialized for the configured Firebase project, require revocation checking, and fail closed for malformed, expired, revoked, syntactically invalid, or wrong-project credentials. | Prevents spoofed, stale, misplaced, or non-header credentials from becoming authenticated Pickup Lane requests. |
| `WS03-01-R2` | Provider account state is current provider authority. | The backend resolves the current Firebase user record during verification, treats provider UID, primary email, email verification, disabled/deleted state, and provider availability as provider-owned facts, and exposes safe authentication failures or dependency-unavailable errors without leaking provider internals. | A cryptographically valid token is not enough if the provider account is disabled, deleted, unavailable, or no longer controls the email facts. |
| `WS03-01-R3` | Local user/account authority is applied after provider identity. | PostgreSQL resolves the app user by Firebase UID and remains authoritative for Pickup Lane user id, local role, account status, deletion/pending-deletion state, permissions, resource ownership, and business state. Token claims alone cannot make a user active, local, or authorized. | Separates authentication from current application authorization and prevents token-only access. |
| `WS03-01-R4` | Current Firebase email verification gates sensitive WS03-01 actions. | Verified-email-required dependencies authorize from the current provider identity, not from a stale local snapshot. Sensitive game, checkout, community, Need-a-Sub, private-message-send, and admin actions require current Firebase email verification; public reads and limited bootstrap/recovery flows do not. | Enforces the approved verified-email policy without blocking legitimate bootstrap or public browsing. |
| `WS03-01-R5` | Provider-derived local snapshots are not independent authority. | Local email and `email_verified_at` are synchronization/display/reference snapshots. They may update only through provider-authenticated paths, conflicts fail safely, stale verified snapshots are cleared when Firebase reports unverified, and missing snapshots can be restored when Firebase reports verified. | Prevents two independent authorities for the same email or verification fact. |
| `WS03-01-R6` | Ordinary profile writes cannot control verifier, provider, admin, or server-owned identity fields. | Ordinary `/users/me` profile updates may write only approved profile fields. They must reject provider UID, primary auth email, email verification state or timestamp, role/admin status, account status, deletion state, provider timestamps, profile-photo/provider-managed URL, permissions, ownership, and other server-controlled identity fields. | Closes the original `email_verified_at` mass-assignment class without duplicating the broader WS02-05B1 request-ownership pass. |
| `WS03-01-R7` | Admin identity combines current provider verification with local admin authority. | Admin entry points require a valid current Firebase identity, current provider-verified email, an active non-deleted local PostgreSQL account, and the local `admin` role. Firebase custom claims, client claims, and frontend state do not grant Pickup Lane admin authority. | Keeps elevated access under current provider identity plus local application authority. |
| `WS03-01-R8` | Route-family identity inventory catches WS03-01 bypasses. | Gate B evidence must inventory active route families for identity-bound bypasses: protected mutations using weaker dependencies, verified-required actions using only active auth, admin routes bypassing verified active-admin dependencies, raw decoded-token authority, custom-claim admin authority, and stale snapshot authorization. | Prevents a narrow set of examples from hiding newly added identity-authority bypasses. |
| `WS03-01-R9` | Browser auth persistence and retry behavior follow `IDB-01`. | Frontend source uses explicit Firebase browser auth persistence, sends Firebase ID tokens to FastAPI as bearer headers, does not manually persist bearer tokens in app storage, bounds safe read refresh behavior, and does not blindly replay non-idempotent authenticated mutations. | Implements the approved persistence/replay decision without taking over full browser private-state isolation. |
| `WS03-01-R10` | Firebase project/settings source contracts are repository-proven without exposing secrets. | Production-like backend settings require Firebase credentials and a non-placeholder valid Firebase project id; Firebase Admin initialization passes the project id to the SDK app; local evidence uses controlled fakes and does not record real project ids, service-account identifiers, or credentials. | Supports project-bound verification while keeping provider secrets and runtime facts out of repository artifacts. |
| `WS03-01-R11` | Provider/runtime closure remains external and explicitly deferred. | Local pytest evidence must not claim to prove deployed Firebase project identity, provider IAM/service-account scope, dashboard auth-provider settings, real token revocation state, HTTPS termination, log/bundle exposure, production env injection, cross-instance propagation timing, MFA/App Check, or full browser cache isolation. | Prevents local tests from overstating production readiness for facts that require provider, runtime, operations, or later-pass evidence. |

## 4. Technical Design / Contracts

### 4.1 Authoritative Controls And Decisions

The primary checklist controls require:

- `IAM-001`: protected requests must use the maintained Firebase Admin SDK for
  the explicitly configured project, accept only Firebase ID tokens, and
  validate signature, issuer, audience, time, subject, and syntax.
- `IAM-002`: bearer tokens must travel through HTTPS Authorization headers, not
  URLs/forms, app-managed browser storage, unnecessary forwarding, logs, or
  telemetry.
- `IAM-003`: Firebase browser persistence must be an explicit risk decision,
  refresh/retry must be bounded, and non-idempotent mutations must not be
  blindly replayed.
- `IAM-004`: cryptographic token validity, Firebase account validity, local
  account state, and current authorization must remain distinct, with
  suspension/deletion/disablement/role removal/revocation taking effect within
  a documented interval across instances and caches.
- `IAM-006`: UID, email, verification status, display/profile data, phone,
  provider links, role, account status, ownership, and permissions need a
  documented source-of-truth and synchronization policy.
- `IAM-007`: operations need a verified-email policy, and admin identity must
  use a verified, currently controlled identifier.
- `IAM-014`: field-level authorization must use purpose-specific schemas and
  explicit mapping, rejecting mass assignment of roles, ownership, account
  state, payment state, provider IDs, timestamps, and admin fields.

The locked audits found:

- `IAM-001` was `PARTIAL`: Firebase Admin verification existed, but explicit
  project/audience binding and revocation checking were not proven.
- `IAM-002` was `PARTIAL`: Authorization-header transport was visible, but
  HTTPS, log, telemetry, and bundle evidence were not complete.
- `IAM-003` needed a decision: explicit browser persistence and replay policy
  were not recorded.
- `IAM-004` was `PARTIAL`: token/local-user separation existed, but
  disabled/revoked provider behavior and cross-instance timing were not proven.
- `IAM-006` needed a decision: Firebase/PostgreSQL source-of-truth ownership
  and snapshot semantics were not fully documented.
- `IAM-007` was `FAIL`: ordinary users could write `email_verified_at`, and
  verified-email/admin-identifier policy needed an owner decision.
- `IAM-014` was `FAIL`: the reachable field-write gap was the ordinary
  authenticated profile update path for `email_verified_at`.

Approved decisions resolve the decision gaps:

- `IDB-01` approves explicit Firebase browser-local persistence, Firebase ID
  tokens sent to FastAPI as bearer tokens, bounded refresh for safe reads, no
  blind replay of payments/bookings/messages/cancellations/admin actions or
  other mutations, and later recent-auth/step-up controls for sensitive
  account/admin actions.
- `IDB-02` makes Firebase authoritative for authentication identity and facts,
  and PostgreSQL authoritative for business identity, profile data, roles,
  permissions, account restrictions, and resource ownership. Provider-derived
  PostgreSQL values are snapshots or references, not independent auth
  authority.
- `IDB-03` permits unverified users to sign in, complete limited profile setup,
  browse generally available game information, access verification/recovery,
  and sign out. It requires verified email before hosting, joining, booking,
  paying, Need-a-Sub interactions, private messages, elevated privileges, and
  admin actions. Firebase remains authoritative for verification, ordinary
  users may not write verification timestamps, and every administrator must use
  a currently verified identifier.

### 4.2 Current Implementation Findings

Gate A inspected the current accepted source, not historical branch state.

Current source appears aligned with the repository-owned WS03-01 behavior:

- `backend/settings.py` includes `FIREBASE_PROJECT_ID`, rejects placeholders
  and missing credentials/project id in production-like environments, and keeps
  example values non-secret.
- `backend/firebase_admin_client.py` requires `firebase_project_id` before auth
  use, initializes Firebase Admin with `projectId`, calls
  `auth.verify_id_token(..., check_revoked=True, clock_skew_seconds=10)`, then
  resolves `auth.get_user(uid)` and rejects disabled provider users.
- `backend/services/auth_service.py` centralizes Authorization-header bearer
  parsing, builds a request-scoped `VerifiedFirebaseIdentity`, maps provider
  configuration/unavailability safely, resolves local users by Firebase UID,
  applies local active/deleted state, synchronizes provider-derived snapshots,
  requires current provider verification for `require_verified_user`, and
  layers `require_active_admin` on verified user plus local active admin role.
- `backend/schemas/user_schema.py` keeps ordinary `UserUpdate` to profile
  fields only with `extra="forbid"`. It no longer includes `email` or
  `email_verified_at`.
- `backend/routes/user_routes.py` disables generic user create/update/delete
  mutations and routes `/users/me` through `UserUpdate`.
- `backend/services/auth_account_service.py` derives auth sync payloads from
  the provider-verified identity path and fails local email conflicts safely.
- Current representative route families use `require_verified_user` for
  sensitive game, checkout, community-game publish/host-edit, Need-a-Sub
  create/request/respond/mutation, and private-message-send operations; use
  `require_active_user` or optional auth for allowed reads/status surfaces; and
  use `require_active_admin` or later `require_recent_active_admin` wrappers
  for admin entry points.
- `frontend/src/lib/firebase.js` configures `browserLocalPersistence`;
  credential sign-in flows call the persistence guard; `frontend/src/lib/authApi.js`
  sends tokens in Authorization headers and uses a one-time forced-refresh
  retry for `/auth/me`; `frontend/src/lib/apiClient.js` has no generic auth
  retry/replay interceptor.
- Frontend `localStorage` use found during Gate A is an email-verification
  cooldown timestamp, not app-managed bearer-token persistence.

Current trusted EN-01 evidence is missing for WS03-01. Existing historical
implementation tests are not trusted. That missing trusted evidence is the
reason for this pass, not proof of a current source defect.

### 4.3 Identity Authority Matrix

| Fact / field | Authority | Current semantics required by this pass |
|---|---|---|
| Firebase UID / auth identity | Firebase/provider | Token subject and provider user record identify the auth principal; local users are looked up by that stable provider identity. |
| Firebase ID-token validity | Firebase Admin SDK / provider | SDK verification validates token syntax, time, issuer/audience/project, subject, and revocation status for the configured app. |
| Primary authentication email | Firebase/provider | Current provider email is authoritative; PostgreSQL email is a snapshot updated only through provider-authenticated sync. |
| Current email verification | Firebase/provider | `email_verified` from the provider user record is the authorization fact for verification-required operations. |
| Provider credential/account state | Firebase/provider | Disabled/deleted/unavailable provider accounts fail closed before local authorization. |
| Pickup Lane user id | PostgreSQL | Internal user identity remains local business identity and never substitutes for provider authentication. |
| Display/profile names, date of birth, home city/state, profile phone | PostgreSQL/application | Ordinary users may update approved profile fields through purpose-specific profile schemas. |
| Local email snapshot | PostgreSQL snapshot of Firebase | Stored for display/reference/sync only; conflicts fail safely and do not override provider authority. |
| `email_verified_at` | PostgreSQL snapshot of Firebase verification | Display/sync/eligibility timestamp only; stale values cannot authorize verification-required operations. |
| Role/admin status | PostgreSQL/application | Local role is authoritative for Pickup Lane admin authority after current verified provider identity. |
| Account status, suspension, deletion, pending deletion | PostgreSQL/application | Local account restrictions are applied after provider identity and before role/action authorization. |
| Permissions and resource ownership | PostgreSQL/application | Business authorization and object relationships remain local application state; full object-level coverage is later WS03-04. |
| Firebase custom claims / client claims | Not Pickup Lane admin authority | They must not grant Pickup Lane admin access in WS03-01. |
| Provider links and actual dashboard/provider settings | Firebase/provider or later account lifecycle owner | Not modeled as local independent authority in WS03-01; full linking/recovery/provider evidence remains later. |

No field is approved to have two independent authorities. If Gate B finds a
dual authority, the pass must stop for Gate A correction.

### 4.4 Protected-Request Identity Pipeline

The required pipeline is:

1. Receive the bearer credential only from the `Authorization` header.
2. Verify the credential through Firebase Admin for the configured app/project.
3. Require revocation checking and provider-user lookup.
4. Reject malformed, expired, revoked, wrong-project, missing-UID, disabled, or
   deleted provider identities.
5. Convert provider state into one request-scoped identity object containing
   Firebase UID, current provider email, current provider verification, provider
   account state, and recent-auth timestamp when present.
6. Avoid passing raw bearer tokens or arbitrary raw decoded-token dictionaries
   to business services as authority.
7. Resolve the local PostgreSQL user by Firebase UID.
8. Apply local account state, deletion/pending-deletion, role, permissions,
   resource ownership, and workflow state after provider identity.

Provider configuration or provider lookup failures fail closed through safe
dependency-unavailable behavior. Provider exception details must not leak to
clients.

### 4.5 Verified-Email Policy

Current provider email verification is required for:

- game hosting, joining, waitlist/join-like user mutations, booking-guest
  mutations, checkout payment-intent creation, cancellation, and host-edit
  actions in current game routes;
- community-game publish and host-edit mutation paths;
- Need-a-Sub post creation/update/cancel, spot requests, owner/requester
  request actions, chat creation, and private chat message sends;
- private game-chat creation/message-send workflows;
- admin entry points through `require_active_admin` and later
  `require_recent_active_admin` wrappers;
- receiving elevated privileges or performing admin actions.

Current provider email verification is not required for:

- public or optional-auth browse/detail reads for generally available games
  and community/Need-a-Sub listing surfaces;
- limited account bootstrap, `/auth/sync-user`, `/auth/me`, verification and
  recovery flows, and sign-out;
- ordinary self/profile setup fields that are allowed before full verified
  participation;
- current read/status/private-history surfaces that require an active local
  account but do not perform a verification-required mutation.

Payment creation through checkout is WS03-01 verified-email scope. Saved-card
setup/default/detach and recent-auth policy are payment/recent-auth owners; the
WS03-01 route inventory may classify them, but it must not silently take over
their provider/payment lifecycle.

### 4.6 Snapshot Semantics

`email` and `email_verified_at` in PostgreSQL are provider-derived snapshots.
They may support display, account setup state, hosting eligibility state, and
sync auditing. They do not independently authenticate or authorize a
verification-required operation.

Gate B evidence must prove both stale directions:

- if PostgreSQL says verified but Firebase currently says unverified, a
  verification-required action is denied and the stale timestamp is cleared;
- if Firebase currently says verified but PostgreSQL lacks the timestamp, the
  provider-authoritative path can restore the snapshot and authorize according
  to current provider state.

### 4.7 Ordinary-User Field Ownership

Ordinary profile writes are limited to approved profile fields:

- `phone`;
- `first_name`;
- `last_name`;
- `date_of_birth`;
- `home_city`;
- `home_state`.

Ordinary profile writes must reject at validation or the route/service boundary:

- `auth_user_id`;
- `email`;
- `email_verified`;
- `email_verified_at`;
- `role`;
- `account_status`;
- `deleted_at`;
- provider-created/updated/auth timestamps;
- `profile_photo_url` while server/provider-owned;
- permissions, ownership, admin, payment, provider, audit, or other
  server-controlled identity fields.

WS02-05B1 owns broad request/mass-assignment evidence. WS03-01 owns the
identity-specific field authority and must avoid re-proving unrelated generic
game/payment/request-body ownership.

### 4.8 Admin Authority

Pickup Lane admin access requires:

- a valid current Firebase identity;
- current provider-verified email;
- a local PostgreSQL user matched by Firebase UID;
- local account status `active`;
- no deletion marker;
- local PostgreSQL role `admin`.

Current later `require_recent_active_admin` wrappers add recent-auth checks for
specific higher-risk actions, but they still depend on `require_active_admin`.
WS03-01 must prove the base identity/admin authority is intact without taking
over all recent-auth/MFA/App Check requirements.

Firebase custom claims, browser state, frontend route guards, and client-sent
role data are not Pickup Lane admin authority.

### 4.9 IAM-003 Browser Persistence And Replay Boundary

The approved browser model is:

- Firebase Auth may persist normal player sessions across browser restarts
  through explicit Firebase browser persistence.
- Pickup Lane backend calls use Firebase ID tokens as bearer credentials.
- Ordinary browser caching is not the authentication mechanism.
- Pickup Lane source must not manually duplicate bearer tokens into
  `localStorage`, `sessionStorage`, IndexedDB, URLs, forms, logs, or telemetry.
- Auth refresh for safe reads may be bounded.
- Non-idempotent mutations, including payments, bookings, messages,
  cancellations, admin actions, and other mutations, must not be blindly
  replayed.
- Mutation retry requires idempotency or a safe way to determine the original
  outcome.

WS03-01 owns the source-level persistence/transport/replay boundary described
above. WS07-02 owns comprehensive logout/account-switch private-cache clearing,
cross-tab identity isolation, browser-history identity isolation, and complete
frontend private-data cache testing.

### 4.10 Provider And Runtime Boundary

Local Gate B evidence may truthfully prove:

- settings parsing requires Firebase project id and credentials in
  production-like environments;
- documented placeholders are rejected where required;
- Firebase Admin initialization passes the configured project id to the SDK;
- `verify_id_token` is called with `check_revoked=True`;
- controlled provider test doubles simulate disabled/deleted/unavailable users
  and provider exception classification;
- source does not store real provider identifiers or credentials.

Local Gate B evidence must not claim to prove:

- the actual deployed Firebase project or dashboard settings;
- real Firebase service-account IAM scope;
- production/preview/staging environment injection;
- real revoked-token or disabled-user behavior in Firebase;
- real HTTPS termination, CDN/edge/header behavior, logs, telemetry, or bundle
  contents;
- cross-instance cache propagation intervals;
- administrator MFA, App Check, provider-account linking, or recovery
  lifecycle behavior.

Those are provider/runtime/later-pass evidence responsibilities.

## 5. Implementation Scope

### 5.1 Remediation Type

Final Gate A classification: evidence reconstruction only.

Current source appears to satisfy the repository-owned WS03-01 obligations, but
trusted EN-01 evidence and requirement declarations do not yet exist for this
pass. Gate B must create trusted evidence artifacts for the frozen requirements.

No production source correction is approved by Gate A.
No frontend source correction is approved by Gate A.
No migration is approved by Gate A.
No provider/dashboard/runtime change is approved by Gate A.

If Gate B evidence exposes a real WS03-01 implementation defect, Gate B must
stop and return for a Gate A correction unless the defect is solely in an
already authorized evidence artifact.

### 5.2 Exact Gate B Editable File Set

Gate B may edit only these files unless a human approves a Gate A correction:

1. `backend/tests/support/requirements/ws03_01.json`
2. `backend/tests/workflows/identity_authority/TESTING_RECORD.md`
3. `backend/tests/workflows/identity_authority/test_firebase_identity_provider_contract.py`
4. `backend/tests/workflows/identity_authority/test_protected_request_identity_pipeline_contract.py`
5. `backend/tests/workflows/identity_authority/test_verified_email_policy_contract.py`
6. `backend/tests/workflows/identity_authority/test_user_identity_field_authority_contract.py`
7. `backend/tests/workflows/identity_authority/test_admin_identity_authority_contract.py`
8. `backend/tests/workflows/identity_authority/test_frontend_auth_persistence_transport_contract.py`
9. `backend/tests/workflows/identity_authority/test_identity_authority_negative_space_contract.py`
10. `backend/tests/workflows/identity_authority/test_firebase_project_settings_contract.py`

Do not edit production source, frontend source, migrations, shared test
infrastructure, other pass plans, or other `TESTING_RECORD.md` files during
Gate B without human-approved Gate A correction.

### 5.3 File Reasons

| File | Reason |
|---|---|
| `ws03_01.json` | EN-01 checker/traceability needs stable WS03-01 requirement declarations. |
| `TESTING_RECORD.md` | Human/Gate C review needs threat model, scenario inventory, proof-layer adequacy, provider/runtime gaps, and deferred-boundary discussion. |
| `test_firebase_identity_provider_contract.py` | Proves Firebase Admin verification call semantics, project-bound app setup, provider-user lookup, disabled/deleted/revoked/unavailable handling, and safe error mapping with controlled provider fakes. |
| `test_protected_request_identity_pipeline_contract.py` | Proves Authorization-header-only extraction, request-scoped identity construction, local user lookup by UID, active/deleted/pending account checks, and no token-only authority. |
| `test_verified_email_policy_contract.py` | Proves current provider verification gates sensitive actions, bootstrap/read exceptions remain allowed, and stale/missing verification snapshots behave as snapshots. |
| `test_user_identity_field_authority_contract.py` | Proves ordinary profile schemas/routes reject provider, verifier, admin, and server-owned identity fields while provider-authenticated sync owns email/verification snapshots. |
| `test_admin_identity_authority_contract.py` | Proves admin access requires current verified provider identity plus active local admin role, and custom/client claims do not grant admin authority. |
| `test_frontend_auth_persistence_transport_contract.py` | Proves the WS03-01-owned frontend source boundary for Firebase browser persistence, bearer-header transport, no app-managed bearer token storage, and no generic mutation replay. |
| `test_identity_authority_negative_space_contract.py` | Provides source/inventory checks for identity bypasses across active routes/services without becoming the full WS03-04 authorization matrix. |
| `test_firebase_project_settings_contract.py` | Proves Firebase project id/credential settings behavior and safe placeholder/secrets boundaries. |

## 6. Testing And Evidence

### 6.1 Requirement Declaration Design

Gate B must create `backend/tests/support/requirements/ws03_01.json` with this
checker-compatible declaration:

| ID | State | Scope | Source controls | Reason |
|---|---|---|---|---|
| `WS03-01-R1` | `required` | `workflows/identity_authority` | `["IAM-001", "IAM-002", "IAM-004", "IDB-02", "WS03-01"]` | Protected requests require project-bound Firebase ID-token verification, revocation checking, and header-only bearer transport. |
| `WS03-01-R2` | `required` | `workflows/identity_authority` | `["IAM-001", "IAM-004", "IAM-006", "EN-02", "WS03-01"]` | Provider user state and safe provider failure handling are part of current identity authority. |
| `WS03-01-R3` | `required` | `workflows/identity_authority` | `["IAM-004", "IAM-006", "IAM-014", "IDB-02", "WS03-01"]` | Local account state and local authorization must be applied after provider identity. |
| `WS03-01-R4` | `required` | `workflows/identity_authority` | `["IAM-004", "IAM-006", "IAM-007", "IDB-03", "WS03-01"]` | Current Firebase verification, not stale local snapshots, gates sensitive WS03-01 actions. |
| `WS03-01-R5` | `required` | `workflows/identity_authority` | `["IAM-006", "IAM-007", "IAM-014", "IDB-02", "IDB-03", "WS03-01"]` | Local email and verification timestamps are provider-derived snapshots only. |
| `WS03-01-R6` | `required` | `workflows/identity_authority` | `["IAM-006", "IAM-014", "IDB-02", "IDB-03", "WS02-05B1", "WS03-01"]` | Ordinary users must not write verifier, provider, admin, or server-owned identity fields. |
| `WS03-01-R7` | `required` | `workflows/identity_authority` | `["IAM-004", "IAM-006", "IAM-007", "IAM-014", "IDB-02", "IDB-03", "WS03-01"]` | Admin authority combines current verified provider identity with active local admin role. |
| `WS03-01-R8` | `required` | `workflows/identity_authority` | `["IAM-004", "IAM-007", "IAM-014", "IDB-03", "WS03-01"]` | Active route/service inventory must detect WS03-01 identity-authority bypasses. |
| `WS03-01-R9` | `required` | `workflows/identity_authority` | `["IAM-002", "IAM-003", "IDB-01", "WS03-01", "WS07-02"]` | Source-level browser persistence, token transport, bounded read refresh, and no blind mutation replay must match the approved decision. |
| `WS03-01-R10` | `required` | `workflows/identity_authority` | `["IAM-001", "IAM-006", "WS02-01", "EN-03", "WS03-01"]` | Firebase project/settings source contracts are repository-proven without exposing provider secrets. |
| `WS03-01-R11` | `deferred` | `governance` | `["IAM-001", "IAM-002", "IAM-003", "IAM-004", "IAM-006", "IAM-007", "IAM-014", "EN-03", "WS03-03", "WS07-02", "WS08", "WS10"]` | External provider/runtime/browser/operations facts cannot be closed by local WS03-01 pytest and must have zero pytest mappings. |

`WS03-01-R11` must remain unmapped to pytest evidence. It is represented by
the requirement declaration, `TESTING_RECORD.md`, and human/Gate C review of
the explicit deferred boundary.

### 6.2 Evidence Architecture

| File | Requirements | Required responsibilities |
|---|---|---|
| `test_firebase_identity_provider_contract.py` | R1, R2, R10 | Service/dependency proof with controlled Firebase Admin fakes: configured app project id, `verify_id_token` app binding, `check_revoked=True`, clock skew, UID syntax, provider `get_user`, disabled/deleted provider denial, invalid/expired/revoked/wrong-project-style failure mapping, provider config/unavailable handling, and no provider detail leakage. |
| `test_protected_request_identity_pipeline_contract.py` | R1, R2, R3 | API/dependency proof that protected requests accept bearer credentials from Authorization only, reject malformed/missing credentials, construct only the safe request-scoped identity object, resolve local users by Firebase UID, reject missing/deleted/pending local users, apply active-account checks, and do not authorize from token-only or arbitrary raw decoded dictionaries. |
| `test_verified_email_policy_contract.py` | R4, R5, R8 | PostgreSQL-backed/API proof for unverified denial on representative sensitive mutations, bootstrap/read exceptions, stale `email_verified_at` clearing, provider-verified snapshot restoration, checkout/game/community/Need-a-Sub/chat-send policy, and explicit classification of active-user read/status exceptions. |
| `test_user_identity_field_authority_contract.py` | R5, R6 | Schema/API/service proof that `/users/me` accepts only approved profile fields and rejects `auth_user_id`, `email`, `email_verified`, `email_verified_at`, `role`, `account_status`, `deleted_at`, `profile_photo_url`, provider timestamps, permissions, and admin/server-owned fields; generic user mutations remain disabled; provider-authenticated sync owns email/verification snapshot writes and conflict handling. |
| `test_admin_identity_authority_contract.py` | R7, R8 | API/dependency proof that admin entry points require current provider verification plus active local admin role; unverified, suspended, deleted, demoted, missing local user, and non-admin users are denied; Firebase custom claims and client-supplied role data do not grant admin authority; recent-admin wrappers remain layered on base active admin. |
| `test_frontend_auth_persistence_transport_contract.py` | R9 | Frontend source inventory proof that Firebase auth uses `browserLocalPersistence`, credential flows await persistence setup, ID tokens are sent in Authorization headers, bearer tokens are not manually persisted in app storage, `/auth/me` uses bounded safe-read refresh, and there is no generic fetch interceptor that blindly replays non-idempotent mutations. |
| `test_identity_authority_negative_space_contract.py` | R1, R3, R4, R6, R7, R8, R9 | Dynamic/static inventory over active backend/frontend source for WS03-01 bypasses: direct `auth.verify_id_token` outside the Firebase client, raw decoded-token authority, custom-claim admin grants, protected mutation routes using weaker dependencies, verified-required actions relying only on active-user auth, admin routes bypassing verified active-admin dependencies, ordinary schemas accepting identity-owned fields, and manual bearer-token storage/replay patterns. This must stay narrower than WS03-04 object-level authorization. |
| `test_firebase_project_settings_contract.py` | R10 | Settings/config proof for production-like Firebase credential/project requirements, placeholder rejection, project-id syntax, provider-free settings parsing where applicable, and no real provider identifiers/secrets in examples or planned evidence. |
| `TESTING_RECORD.md` | R1-R11 | Human-readable risk record covering threat model, authority matrix, request-time provider/local pipeline, verification policy, snapshot semantics, ordinary-user field ownership, admin authority, IAM-003 boundary, provider mocking limits, PostgreSQL proof needs, negative-space inventory, handoffs, external gaps, and adequacy conclusion. |
| `ws03_01.json` | R1-R11 | Declares the stable requirements with checker-compatible states, scopes, source controls, and reasons. |

### 6.3 Proof-Layer Decisions

| Proof layer | Gate B decision | Reason |
|---|---|---|
| Production backend source | No planned correction | Current source appears aligned with repository-owned WS03-01 behavior. Gate B must stop for Gate A correction if a source defect is proven. |
| Frontend source | No planned correction | Current source appears aligned with explicit Firebase persistence, header bearer transport, and no generic replay. Gate B source-inventory evidence is enough unless a source defect is proven. |
| Requirement JSON | Required | EN-01 checker and traceability require stable declarations. |
| `TESTING_RECORD.md` | Required | Gate C needs adequacy reasoning and external-provider gap documentation. |
| Service/dependency unit evidence | Required | Firebase Admin and provider-state behavior is best proven with controlled fakes at the provider boundary. |
| Runtime/API evidence | Required | Protected-request denial, verified-email policy, admin denial, and profile field rejection are request-time behavior. |
| Schema/request evidence | Required | Ordinary identity field writes are prevented by purpose-specific schemas and route/service boundaries. |
| PostgreSQL-backed evidence | Required | Local user/account/role/snapshot state affects authorization and sync outcomes. |
| Settings/config evidence | Required | Firebase project binding and placeholder rejection are configuration contracts. |
| Frontend source evidence | Required | IAM-003's WS03-01-owned source boundary is frontend-auth setup and token handling. |
| Frontend unit/lint/build | Not required for planned Gate B | No frontend source change is approved. If a frontend correction is later approved, validation must be redesigned. |
| Playwright/browser proof | Not required | Browser-local persistence and token storage/replay boundaries can be proven by source/unit-style evidence for WS03-01; full browser state isolation is WS07-02. |
| Provider/network evidence | Deferred | Real Firebase project/dashboard/IAM/runtime behavior cannot be closed locally. |
| Migration evidence | Not required | No schema or migration change is approved. |
| Concurrency evidence | Not required for WS03-01 | Concurrent first login and account lifecycle races are WS03-02. |

### 6.4 Negative-Space Strategy

Gate B evidence must fail closed if current source introduces a WS03-01 bypass.
The negative-space inventory must inspect active code only and must not cite or
execute historical tests.

Required negative-space checks include:

- no protected identity route bypasses the central auth dependency family for
  WS03-01-owned behavior;
- no direct Firebase Admin token verification outside the approved client
  boundary;
- no business route/service treats arbitrary raw decoded-token dictionaries,
  Firebase custom claims, or client role claims as local authority;
- no verified-required mutation uses only active-user authentication;
- no admin route bypasses `require_active_admin` or a later wrapper that
  depends on it;
- no ordinary profile schema accepts provider/verifier/admin/server-owned
  identity fields;
- stale local verification snapshots do not authorize protected actions;
- frontend source does not store bearer tokens manually, pass them in URLs or
  forms, or install a generic mutation replay path.

The route inventory should classify exceptions rather than silently ignore
them. Public reads, optional-auth reads, bootstrap/profile setup, status reads,
retired route tombstones, payment-method/recent-auth surfaces, and later-owner
admin/payment/account-lifecycle flows must be recorded with reasons.

### 6.5 TESTING_RECORD Design

Gate B must create `backend/tests/workflows/identity_authority/TESTING_RECORD.md`
using the current template. It must explain:

- threat/risk model;
- identity authority matrix;
- protected request-time provider/local pipeline;
- verified-email route policy;
- snapshot semantics for local email and `email_verified_at`;
- ordinary-user field ownership;
- admin authority;
- IAM-003 persistence/replay boundary;
- provider mocking limitations;
- PostgreSQL proof needs;
- route/inventory negative space;
- handoffs to WS03-02, WS03-03, WS03-04, WS07-02, WS08, WS09, and WS10;
- remaining external/provider/runtime gaps;
- adequacy conclusion.

It must distinguish executable pytest evidence from checker/traceability
evidence and from human/provider/runtime review. It must not claim local pytest
proof for `WS03-01-R11`.

### 6.6 Gate B Validation Strategy

Gate B must run:

```bash
git diff --check
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests/workflows/identity_authority
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/identity_authority
```

```bash
DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

```bash
APP_ENV=test DATABASE_URL="$TEST_DATABASE_URL" backend/.venv/bin/python -m pytest -q backend/tests
```

Gate B must report generated traceability counts for `WS03-01-R1` through
`WS03-01-R11`, with `R11` exactly zero pytest mappings.

There is no planned frontend source change, so frontend lint/build/unit tests
are not required by this frozen design. If Gate B receives an approved
frontend-source correction later, the validation ladder must be amended through
Gate A correction before implementation.

There is no current trusted auth-specific existing suite outside the new
`workflows/identity_authority` scope. If Gate B changes production source after
human-approved correction, it must also run the materially affected existing
trusted modules in addition to the full backend regression.

## 7. Integration / Operational Expectations

WS03-01 becomes the identity authority baseline consumed by later WS03 and
cross-pass work.

Later passes and features must preserve:

- Firebase/provider ownership of auth identity and current verification facts;
- PostgreSQL ownership of local roles, account restrictions, permissions,
  resource ownership, and business state;
- local snapshots as snapshots only;
- verified-email requirement for sensitive actions and admin authority;
- central provider/local identity dependencies for protected requests;
- no ordinary profile writes to provider, verifier, admin, or server-owned
  identity fields;
- no local pytest claim that provider/runtime facts are fully closed.

Provider/runtime operators must still supply separate evidence for Firebase
dashboard/project/IAM/runtime behavior before the broader controls can close.

## 8. Not Part Of This Pass

WS03-01 does not:

- create or change production source during Gate A;
- create tests, requirement JSON, or `TESTING_RECORD.md` during Gate A;
- change database models or migrations;
- prove the real deployed Firebase project, provider IAM, service-account
  scope, dashboard auth-provider settings, production env injection, real token
  revocation, or provider outage behavior;
- prove HTTPS termination, edge/CDN/proxy behavior, production logs, telemetry,
  or bundled artifact exposure;
- implement or prove concurrent first login, account linking, recovery
  lifecycle, deletion lifecycle, or cross-instance account lifecycle
  transitions owned by WS03-02;
- implement or prove recent authentication, step-up, administrator MFA, App
  Check, or Firebase/GCP provider-control-plane validation owned by WS03-03;
- perform complete object-level authorization, IDOR, role/resource ownership,
  function authorization, or exhaustive route authorization owned by WS03-04;
- perform comprehensive logout/account-switch private-cache clearing,
  cross-tab identity isolation, browser-history isolation, or full frontend
  private-state testing owned by WS07-02;
- reopen WS02-01 settings foundations, WS02-05A HTTP/OpenAPI/cache contracts,
  WS02-05B1 generic request ownership, or WS02-05B2 response minimization
  unless Gate B proves a direct authority conflict.

## 9. Related Controls And Remaining Evidence

| Control / Decision | What this pass establishes | What remains later |
|---|---|---|
| `IAM-001` | Repository source and trusted evidence for configured-project Firebase Admin verification, ID-token-only protected request verification, revocation flag use, UID validation, provider user lookup, and fail-closed invalid token behavior. | Real deployed Firebase project, provider dashboard, real token/audience/issuer behavior, service-account scope, and runtime evidence. |
| `IAM-002` | Repository evidence for Authorization-header token transport, no app-managed bearer token storage, no URL/form token acceptance in WS03-01 identity paths, and safe source-level token handling. | HTTPS termination, production logs/telemetry, deployed bundle/log scans, unnecessary forwarding proof outside repository source. |
| `IAM-003` / `IDB-01` | Source evidence for explicit Firebase browser-local persistence, bounded `/auth/me` safe-read refresh, and no generic blind replay of non-idempotent mutations. | Full frontend private-cache clearing, cross-tab/browser-history behavior, complete browser runtime coverage, and broader recent-auth/idempotency evidence. |
| `IAM-004` | Repository evidence distinguishing token validity, provider account validity, local user/account state, and current authorization for WS03-01 dependencies. | Cross-instance timing, provider/runtime disabled/revoked proof, broader account lifecycle propagation, and operational interval evidence. |
| `IAM-006` / `IDB-02` | Source-of-truth matrix and evidence that Firebase owns auth facts while PostgreSQL owns local business identity/profile/role/account/ownership facts; provider-derived local values are snapshots. | Provider links, account lifecycle edge cases, operational sync/audit evidence, and database/concurrency lifecycle guarantees in later passes. |
| `IAM-007` / `IDB-03` | Repository evidence for verified-email policy on WS03-01 route families, current-provider verification authority, stale snapshot denial, and verified admin identifier requirement. | Provider/runtime proof of real verification state, recovery/abuse controls, and later high-risk auth policy evidence. |
| `IAM-014` | Identity-specific field-level authorization: ordinary users cannot write provider, verifier, admin, or server-owned identity fields, and generic user mutations remain disabled. | Broader request ownership remains WS02-05B1; complete object/function/list authorization remains WS03-04; payment/provider fields remain payment owners. |
| `EN-01` | New trusted requirement declarations, current workflow tests, generated traceability, and human testing record for WS03-01. | Gate B implementation and Gate C review. |
| `EN-02` | WS03-01 provider/auth errors use safe public error mapping rather than raw provider details. | Broader observability/log evidence remains EN-02/WS09/runtime. |
| `EN-03` | Provider secrets and real provider identifiers stay out of repository evidence; provider facts are explicitly external. | Provider evidence collection, redacted operational records, and runtime proof. |

## 10. Completion Criteria

WS03-01 is complete when:

- [ ] `WS03-01-R1` through `WS03-01-R11` are declared with the states/scopes in
  this plan.
- [ ] `WS03-01-R1` through `WS03-01-R10` have credible trusted evidence.
- [ ] `WS03-01-R11` remains deferred/governance with zero pytest mappings.
- [ ] The trusted evidence modules in `backend/tests/workflows/identity_authority`
  pass.
- [ ] The domain checker passes for `backend/tests/workflows/identity_authority`.
- [ ] The suite checker passes.
- [ ] Generated traceability reflects the final mappings and zero mappings for
  `R11`.
- [ ] The full trusted backend regression passes.
- [ ] `TESTING_RECORD.md` records the threat model, scenarios, proof layers,
  handoffs, provider/runtime gaps, and adequacy conclusion.
- [ ] No production/frontend/migration/provider change has been made unless a
  later human-approved Gate A correction authorizes it.
- [ ] No unresolved authority ambiguity, dual-authority field, or provider
  fail-open behavior remains.

Pass completion is not the same as full closure of every primary control.
Several controls still require provider, runtime, operations, browser, and
later WS03 evidence before broader production-readiness closure.

## 11. Stop Conditions

Gate B must stop and return for Gate A correction if:

- any identity field is found to have two independent authorities;
- current source allows ordinary users to write provider, verifier, admin, or
  server-owned identity fields;
- a verified-required action is proven to authorize from stale local
  `email_verified_at` instead of current provider verification;
- admin access can be granted by Firebase custom claims, client claims, or
  frontend state without active local admin role and current verified provider
  identity;
- provider state is unavailable and current source fails open;
- a production, frontend, migration, provider, shared test-infrastructure, or
  broader pass-plan file is required to implement the fix;
- local evidence would need to claim a provider/runtime fact that is not
  repository-verifiable.

Evidence-artifact mistakes inside the exact Gate B file set may be corrected in
Gate B. Production or broader-scope mistakes require a new human-approved Gate
A correction.

## 12. Rollback And Compatibility

Gate A changes only this planning document.

The planned Gate B changes are requirement/test/evidence artifacts only and
should have no runtime compatibility impact. If Gate B later proves a source
defect requiring production or frontend changes, rollback/compatibility must be
reassessed in a Gate A correction before implementation.

Current source compatibility expectations:

- existing profile setup may continue to update approved profile fields before
  verification;
- current frontend flows may continue to display `email_verified_at` as a
  snapshot/control state;
- current public browse/detail reads remain available without verified email;
- existing admin and recent-admin wrappers remain compatible as long as they
  continue to layer on current provider identity and local admin authority.

## 13. Gate A Decision / Freeze

Gate A reconciles WS03-01 as:

- current accepted `develop` is repository truth for current implementation
  state;
- authoritative controls, approved decisions, accepted dependency pass
  boundaries, and this canonical plan define what must be true;
- historical PR #126 is provenance only;
- no current production/frontend defect is approved by Gate A;
- Gate B is evidence reconstruction only unless trusted evidence proves an
  in-scope mistake;
- the exact Gate B editable file set is frozen in Section 5.2;
- `WS03-01-R1` through `WS03-01-R10` are required and executable under
  `workflows/identity_authority`;
- `WS03-01-R11` is deferred/governance and must have zero pytest mappings.

After human approval, the SHA-256 of this file is the frozen canonical-plan
hash for WS03-01 Gate B.
