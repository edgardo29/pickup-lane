# WS03-01 Identity Authority And Verifier-Controlled Fields

## Scope

WS03-01 establishes a source-owned identity authority model for protected backend requests.

Firebase is authoritative for:

- Firebase authentication UID
- primary authentication email
- email verification
- authentication provider and credential state
- Firebase ID-token validity
- token revocation
- disabled or deleted Firebase account state

PostgreSQL is authoritative for:

- Pickup Lane internal user id
- profile and display fields
- profile/contact phone
- local role
- local suspension, deletion, and inactive state
- application permissions
- resource ownership
- application business state

PostgreSQL may retain provider-derived email and verification timestamps only as snapshots. They are not independent authorization sources.

## Request-Time Identity Pipeline

Protected requests continue to use header-only bearer authentication.

The backend now resolves one request-scoped Firebase identity object from the Authorization header. Routes and services no longer need to read arbitrary decoded token dictionaries for UID, email, or verification facts.

The identity pipeline:

- extracts the bearer credential from the Authorization header only
- verifies the credential through the Firebase Admin SDK
- requires SDK revocation and disabled-user checks
- resolves the current Firebase user record through the SDK
- exposes only safe request facts: Firebase UID, current primary email, and current email-verification state
- resolves the local Pickup Lane user by Firebase UID
- applies PostgreSQL-owned role, active-account, deletion, and ownership rules after provider identity is established

No raw Firebase ID token is exposed downstream.

## Firebase Project Binding

Backend Firebase Admin initialization now requires an explicitly configured non-secret Firebase project id. Production-like environments must provide this setting and cannot use the documented placeholder.

Source contains only placeholder documentation. No real project id, service-account identifier, or credential value is recorded here.

## Revocation And Disabled Accounts

Firebase token verification uses the maintained Firebase Admin SDK with revocation checking enabled. Disabled, deleted, malformed, expired, revoked, and wrong-project credentials fail closed and are treated as authentication failures.

Provider infrastructure failures, such as certificate fetch or provider lookup unavailability, fail closed as dependency-unavailable behavior where the existing error taxonomy supports it. Provider exception details are not exposed.

## Verified-Email Route Policy

Verification is not required for public game reads, browse/detail reads, limited profile setup, auth sync, logout, or other approved account-bootstrap and recovery flows.

Verification is required before:

- official game join, booking-guest, checkout payment, and user game mutation paths
- community game publish and host-edit mutation paths
- Need-a-Sub create, request/respond, participation mutation, and private message-send paths
- private game-chat message-send paths
- every admin operation through the verified admin dependency

Chat and message reads remain active-user reads unless separately governed by admin authorization.

## Primary Email Authority

Ordinary profile updates no longer accept `email` as a writable profile field. The local email column remains a Firebase-derived snapshot and may be updated only from the provider-authenticated identity path.

Old clients that attempt to submit email through `/users/me` receive request validation failure; client input cannot create a conflicting local auth-email authority.

## Verification Snapshot Semantics

`email_verified_at` remains a provider-derived snapshot for display/reference behavior. It is not sufficient to authorize verification-required workflows.

When a verification-required dependency sees the current Firebase account as unverified, any stale local verification timestamp is cleared before access is denied. When Firebase reports the account as verified again, the snapshot can be restored through the same provider-authoritative path.

## Admin Authority

Admin access requires:

- current valid Firebase identity
- current provider-verified email
- active local PostgreSQL account
- local PostgreSQL role of `admin`

Firebase custom claims and client-side claims do not grant Pickup Lane admin authority.

## Browser Persistence And Replay

The frontend explicitly configures Firebase Auth browser-local persistence with the Firebase client SDK. Pickup Lane still does not manually store bearer tokens in application storage.

The existing safe-read auth refresh behavior remains bounded. This pass does not add automatic replay for non-idempotent mutations such as payments, bookings, cancellations, chat sends, refunds, credits, or admin mutations.

## IAM-014 Status

Ordinary users remain unable to write verifier-controlled or server-owned profile fields, including verification state, provider UID, role, suspension/deletion state, admin authority, provider timestamps, and profile-photo URL. WS03-01 additionally removes ordinary profile email mutation.

## Source-Owned Evidence

WS03-01 source evidence includes:

- Firebase Admin SDK verification with project-bound app initialization
- revocation checking enabled for protected-request verification
- disabled/deleted provider user denial
- central request-scoped Firebase identity dependency
- explicit verified-user dependency
- verified-admin dependency
- route-family inventory tests for representative sensitive mutations
- stale verification snapshot tests
- primary-email authority tests
- token transport tests
- settings validation for Firebase project binding

## Provider And Runtime Evidence Still Required

Runtime evidence outside source remains required for the actual deployed Firebase project, provider IAM controls, service-account scope, and production environment variable injection.

This document intentionally records no real provider identifiers or credentials.

## Handoffs

WS03-02:

- concurrent first login
- account linking
- recovery lifecycle
- account deletion lifecycle
- cross-instance lifecycle transitions
- schema or constraint changes needed for those flows

WS03-03:

- recent authentication
- step-up authentication
- administrator MFA
- App Check
- provider/service-account control-plane verification

WS03-04:

- complete route/object authorization matrix
- object-level authorization and IDOR review
- role/resource ownership audit beyond the prerequisites covered here

WS07-02:

- comprehensive logout/account-switch private cache clearing
- cross-tab identity isolation
- browser-history identity isolation
- full frontend private-data cache tests

## Impact

No database migration, provider dashboard change, deployment architecture change, CI architecture change, or permanent-host change is introduced by WS03-01.
