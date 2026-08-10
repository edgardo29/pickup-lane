# WS03-02 Account Lifecycle and Concurrency

## Scope

WS03-02 verifies account provisioning, local account-state lifecycle behavior, concurrent first login, and final-admin offboarding protections against current `develop`-line code. It preserves WS03-01 identity authority boundaries:

- Firebase owns UID, provider email, provider verification state, provider token validity, and disabled/deleted provider identity outcomes.
- PostgreSQL owns the internal user id, profile, role, local account status, hosting status, permissions, ownership, audit, notifications, and support follow-up state.

No destructive identity migration, email-based UID relinking, default/shared admin, or production hosting architecture decision is included in this slice.

## Source Evidence Added

- Concurrent first-login proof covers two independent PostgreSQL sessions syncing the same verified Firebase UID/email at the same time. Exactly one `users` row is created, both callers resolve to the same internal user id, and one `user_settings` plus one `user_stats` row exists.
- Repeat same-UID sync preserves the internal user id and repairs missing one-per-user context rows.
- Same UID with changed provider email updates the local snapshot without relinking.
- Different UID with the same email is rejected without taking over the existing local account.
- Pending-deletion and deleted local accounts are not recreated or silently reactivated by sync. Suspended local accounts stay suspended through sync.
- Admin role and account-status changes are enforced from PostgreSQL on the next request with the same provider token.
- Self-delete failure modes are covered for provider failure restore, provider success followed by app cleanup failure, provider mutation timeout with unknown outcome, and repeated deletion attempts after completed cleanup.
- Final active admin protections are covered for demotion, suspension, deletion, and concurrent demotion attempts.

Provider-disabled and provider-deleted identity failures remain covered by WS03-01 shared authentication tests.

## Provisioning Invariants

Current schema and service behavior provide the WS03-02 source-owned invariants without a migration:

- `users.auth_user_id` is nullable for deletion/anonymization states, but non-null Firebase UID values are unique.
- `users.email` is nullable for deletion/anonymization states, but non-null email snapshot values are unique.
- `user_settings.user_id` is the primary-key foreign key to `users.id`, so settings are one-per-user.
- `user_stats.user_id` is the primary-key foreign key to `users.id`, so stats are one-per-user.

The stable identity linkage key is Firebase UID, not email. Repeated sync, recovery, same-UID email changes, and supported context repair retain the existing Pickup Lane internal user id. WS03-02 does not introduce broad foreign-key rewriting, user-row replacement, user merging, or ownership transfer.

## Lifecycle Semantics

PostgreSQL remains authoritative for local account lifecycle states: `active`, `suspended`, `pending_deletion`, and `deleted`. WS03-02 does not introduce a generic `inactive` state.

Suspension is a local product/account restriction. It does not disable or mutate the Firebase provider identity. A request that was already authorized before a committed local state change is not claimed to be cancelled by source evidence. New protected requests after the transition commit reread PostgreSQL-backed state and enforce the current local role/account status. No process-local role or account-status cache was found or introduced for protected route decisions, so source behavior remains DB-backed across app instances. This is source evidence only; it is not deployed multi-instance timing evidence.

## Recovery and Enumeration

Ordinary sign-in credential mismatch errors now use one public message for `invalid-credential`, `wrong-password`, and `user-not-found`: `Email or password is incorrect.` Forgot/reset recovery remains Firebase-owned and enumeration-resistant in the current frontend flow: account-not-found sends the user to the same check-email experience that says a reset link was sent if an account exists.

Signup email availability is intentionally different product behavior. WS03-02 does not redesign or remove `/auth/email-availability`, and it does not create a separate Pickup Lane recovery authority.

Credential linking remains provider-side linking for the current Firebase identity. WS03-02 does not add a local account-merge, email-based UID reassignment, or recovery path that attaches a Firebase UID by matching PostgreSQL email.

## Account Deletion

The existing staged deletion workflow is unchanged. Source behavior stages `pending_deletion`, attempts provider deletion, checkpoints provider/local progress, unlinks the local auth id when the provider deletion is known to have succeeded, then runs local cleanup and anonymization.

Provider deletion failure restores the prior local account status when possible. Provider success followed by local cleanup failure leaves the account pending deletion, clears the auth link, and opens an `account_delete_partial_failure` support flag. Provider mutation timeout with unknown outcome leaves the account pending deletion, preserves the auth link, and opens support follow-up because the external outcome must be reconciled before retry. Duplicate/repeated deletion after completed cleanup is rejected without retrying provider deletion.

Durable retry/reconciliation workers are not added in WS03-02; ambiguous or partial provider/local outcomes remain manual/support repair and WS05 handoff territory.

## Administrator Lifecycle

Administrator bootstrap remains source-constrained to promoting an existing Firebase-backed Pickup Lane account after provider checks. No default/shared admin identity, public admin-grant endpoint, impersonation, break-glass account, or break-glass session was added.

Final active local administrator protection remains backend authoritative. WS03-02 evidence covers role demotion, suspension, admin deletion/offboarding, and a deterministic concurrent demotion proof that cannot commit zero eligible local admins. Existing audit, reason, idempotency, and stale-preview checks remain intact.

Source can prove local admin invariants and bootstrap constraints. It cannot prove actual production admins are individually named/recoverable, Firebase/GCP emergency recovery, provider factor reset processes, provider control-plane ownership, or revocation propagation timing.

## Production Code Changes

Backend production code did not require changes for the WS03-02 proofs. The database uniqueness and service-level conflict handling already provide the provisioning and lifecycle guarantees in scope.

Frontend production code now normalizes ordinary sign-in credential mismatch errors (`invalid-credential`, `wrong-password`, and `user-not-found`) to the same public message: `Email or password is incorrect.`

## Evidence Boundaries

Source can prove UID uniqueness behavior, no email-based relink, first-login concurrency, local lifecycle enforcement, final-local-admin invariants, and recovery response normalization.

Source cannot fully prove actual named admin-account operations, provider emergency recovery, provider factor reset, provider control-plane ownership, revocation propagation timing, deployed cross-instance behavior, or permanent hosting architecture.

## Data Model and Migration Decision

No migration was added. No Alembic revision, database model, new constraint, or new index changed for WS03-02. Current tracked constraints already include uniqueness for `users.auth_user_id` and `users.email`, plus one-per-user primary-key ownership for `user_settings.user_id` and `user_stats.user_id`.

If future evidence shows a missing database invariant, pause before adding a migration and make that owner decision explicitly.

## Validation Notes

WS03-02 validation used focused backend lifecycle/concurrency tests, shared authentication regressions, the full current backend suite, frontend unit tests, frontend lint/build, Python compile, diff/static checks, and a sensitive-content scan. The backend test-contract checker cannot currently certify `backend/tests/shared/authentication` because that existing shared test folder has no `_backend_test_contract.py`; WS03-02 does not add a new contract framework. `ruff` is not installed in the current backend virtualenv and was not introduced as new tooling.

## Handoffs

- WS03-03: recent auth, MFA, App Check, step-up, and other advanced auth controls remain unstarted.
- WS03-04: full IDOR/object authorization review remains deferred.
- WS04: broad database architecture, migration, transaction, and locking framework work remains deferred.
- Durable deletion cleanup retries and reconciliation remain deferred to WS05.
- WS07-02: browser cache/account-switch isolation remains deferred.
- Permanent TLS, proxy/CDN, direct-origin, and staging external HTTP-chain evidence remain deferred.
- Render/Vercel remain temporary demo/resume infrastructure only, not the permanent hosting architecture.
