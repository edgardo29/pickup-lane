# WS03-03A Recent Authentication And Step-Up

Status: source implementation scope for IAM-008.

WS03-03A adds recent-authentication enforcement for approved high-risk actions. It does not implement Firebase App Check, provider MFA configuration, Firebase/GCP credential governance, provider IAM review, or permanent production hosting evidence.

## Authority

- The backend accepts only the verified Firebase ID token `auth_time` claim as the provider-authentication time.
- The backend does not use `iat`, frontend timestamps, localStorage, sessionStorage, Postgres timestamps, client booleans, or app-generated proofs as recent-auth evidence.
- Refreshing an ID token without Firebase reauthentication does not make stale `auth_time` fresh.
- The recent-authentication window is five minutes, centralized as `DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS` and exposed on typed backend settings as `recent_authentication_window_seconds`.
- `auth_time` is parsed into `VerifiedFirebaseIdentity.authenticated_at` and is never persisted in Postgres or exposed back to clients.

## Error Contract

Recent-auth failures use the existing public error envelope with:

- HTTP status: `403`
- Code: `AUTH.RECENT_AUTH_REQUIRED`
- Public message: `Confirm your identity to continue.`

The response does not include raw tokens, provider credentials, `auth_time`, provider popup results, passwords, or internal verification details. The existing correlation and cache/security-header behavior remains in force.

## Backend Enforcement

Reusable dependencies:

- `require_recent_authentication`: evaluates provider `auth_time`.
- `require_recent_app_user`: current local app user plus recent provider auth.
- `require_recent_active_user`: active user plus recent provider auth.
- `require_recent_active_admin`: verified active admin plus recent provider auth.

These dependencies layer on the existing Firebase identity and local account/admin dependencies. They add a prerequisite only; they do not replace final-admin checks, idempotency keys, current-state tokens, preview tokens, audit records, provider reconciliation, or ownership checks.

## Frontend Step-Up

The frontend handles step-up only through opted-in high-risk handlers. There is no global mutation interceptor and no automatic replay of arbitrary bookings, payments, messages, cancellations, or admin mutations.

Supported methods:

- Email/password users re-enter their password. The password is passed only to Firebase client reauthentication and is not sent to the backend or storage.
- Google users use Firebase popup reauthentication.
- After successful Firebase reauthentication, the frontend obtains a fresh normal Firebase ID token and retries only the original confirmed high-risk operation.
- Cancelled or failed provider reauthentication fails closed and does not retry the operation.

Firebase credential linking that is currently exposed is the add-password flow for Google users. It requires frontend step-up before calling Firebase `linkWithCredential`. No local merge/relink authority is introduced.

## High-Risk Matrix

The source-owned route inventory is `backend/services/recent_auth_policy.py`.

| Action | Actor | Route | Recent auth | Enforcement | Frontend caller | Protections | Provider MFA |
|---|---|---|---|---|---|---|---|
| Self account deletion | Current user | `DELETE /auth/account` | Yes | `require_recent_app_user` | `useDeleteAccountSettings` | Typed confirmation, deletion workflow guards, Firebase authority | Deferred |
| Admin role grant/removal | Admin | `PATCH /admin/users/{user_id}/role` | Yes | `require_recent_active_admin` | No current exposed caller | Final-admin guard, idempotency, audit | Deferred |
| Admin user deletion | Admin | `POST /admin/users/{user_id}/delete` | Yes | `require_recent_active_admin` | `AdminUserDeletePreviewModal` | Current-state token, idempotency, audit | Deferred |
| Admin suspension | Admin | `POST /admin/users/{user_id}/suspend` | Yes | `require_recent_active_admin` | `AdminUserSuspensionModal` | Preview token, idempotency, audit | Deferred |
| Admin unsuspension | Admin | `POST /admin/users/{user_id}/unsuspend` | Yes | `require_recent_active_admin` | `AdminUserUnsuspensionModal` | Current state, idempotency, audit | Deferred |
| Financial outcome create | Admin | `POST /admin/money/financial-outcomes` | Yes | `require_recent_active_admin` | Community-game financial outcome flow | Idempotency, money issue linkage | Deferred |
| Money issue resolve | Admin | `POST /admin/money/issues/{money_issue_id}/resolve` | Yes | `require_recent_active_admin` | `AdminMoneyIssuePage` | Current issue state, idempotency | Deferred |
| Money issue credit retry | Admin | `POST /admin/money/issues/{money_issue_id}/retry-credit` | Yes | `require_recent_active_admin` | `AdminMoneyIssuePage` | Current issue state, idempotency | Deferred |
| Refund retry | Admin | `POST /admin/money/refunds/{refund_id}/retry` | Yes | `require_recent_active_admin` | `AdminMoneyIssuePage`, `AdminMoneyRefundPage` | Provider reconciliation, idempotency | Deferred |
| Refund reconcile | Admin | `POST /admin/money/refunds/{refund_id}/reconcile` | Yes | `require_recent_active_admin` | `AdminMoneyRefundPage` | Provider reconciliation, idempotency | Deferred |
| Game credit issue | Admin | `POST /admin/game-credits/issue` | Yes | `require_recent_active_admin` | No current exposed caller | Source validation, idempotency, ledger | Deferred |
| Game credit reverse | Admin | `POST /admin/game-credits/{game_credit_id}/reverse` | Yes | `require_recent_active_admin` | No current exposed caller | Usage guard, idempotency, ledger | Deferred |
| Official game cancellation execute | Admin | `POST /admin/official-games/{game_id}/cancel` | Yes | `require_recent_active_admin` | `AdminOfficialGamePage` | Preview token, refunds, audit | Deferred |
| Platform notice create | Admin | `POST /admin/platform-notices` | Yes | `require_recent_active_admin` | `AdminPlatformNoticesPage` | Idempotency, recipient selection audit | Deferred |
| Platform notice cancel | Admin | `POST /admin/platform-notices/{notice_id}/cancel` | Yes | `require_recent_active_admin` | `AdminPlatformNoticesPage` | Current notice state, audit | Deferred |
| Saved card default change | Current user | `PATCH /user-payment-methods/{payment_method_id}/default` | Yes | `require_recent_active_user` | `PaymentMethodsPage` | Owned saved-card check, persistent account-state change | Not required for current-user saved-card management |
| Saved card detach | Current user | `DELETE /user-payment-methods/{payment_method_id}` | Yes | `require_recent_active_user` | `PaymentMethodsPage` | Owned saved-card check, persistent account-state change | Not required for current-user saved-card management |

## Not Newly Gated

- Public/general reads, game browsing, normal navigation, notification reads.
- Normal profile edits and ordinary settings changes that are not credential/provider mutations.
- Ordinary join, booking, checkout, payment, participant chat, and Need a Sub participation.
- Checkout add-card behavior, profile/settings add-card behavior, `POST /user-payment-methods/setup-intent`, and `POST /user-payment-methods/sync`.
- Community hide/restore/remove and routine reversible moderation unless a route overlaps the explicit high-risk list.
- Official-game cancellation preview and routine official-game edits.
- Admin chat moderation reads/actions. No separate admin private-message unmask route exists in current source.
- Sensitive admin exports are not currently implemented; future export routes must be classified before exposure.

## Rolling Compatibility

WS03-03A pairs backend enforcement with frontend recovery in the same source change. The backend exposes a stable public code; the frontend handles it only in opted-in high-risk callers. There is no API version split, permanent bypass, or client-supplied purpose flag. Existing ungated ordinary flows continue to use current auth transport.

## Observability And Redaction

Recent-auth failures use the existing correlation ID and public error envelope. Code and tests must not log or expose ID tokens, passwords, OAuth popup result tokens, provider credentials, `auth_time`, personal labels, or high-cardinality identifiers. Telemetry should use bounded categories only.

## Admin MFA Disposition

IAM-008 requires administrator MFA unless a documented provider limitation and compensating control exists. Current provider MFA capability and enforcement evidence are unknown in source and are not satisfied by WS03-03A.

Temporary compensating controls in source:

- Verified current Firebase identity.
- Verified email for admin access.
- Active Postgres admin account.
- Five-minute recent-authentication requirement.
- No shared admin-account pattern in source.
- Final-admin guard for role changes.
- Current-state, preview, idempotency, provider reconciliation, and audit controls where implemented.

Provider MFA evidence remains a WS03-03B requirement.

## WS03-03B Handoff

WS03-03B should cover:

- Firebase App Check applicability for supported browser clients, recommended reCAPTCHA Enterprise verification, browser surface policy, source integration, staging observation, false-positive handling, provider-unavailable behavior, rollback, and production enforcement evidence.
- Admin MFA capability and evidence: provider support, enrollment policy, enforced factors, break-glass stance, access-review proof, and runtime/admin sign-in verification.
- IAM-011 credential governance: service-account mechanism, least privilege, key inventory, storage model, rotation, revocation, monitoring, emergency procedure, ADC or Workload Identity Federation direction where appropriate, and permanent-host binding.

App Check, provider MFA, and Firebase/GCP credential governance are intentionally untouched in WS03-03A.

## Migration And Provider Boundary

No database migration is expected. Auth freshness is not stored. Source evidence proves code behavior only; provider dashboard configuration, admin MFA, App Check enforcement, credential scope, and permanent production hosting evidence remain external until WS03-03B or later workstreams.
