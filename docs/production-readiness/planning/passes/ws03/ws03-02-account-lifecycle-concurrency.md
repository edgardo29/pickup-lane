# WS03-02 - Provisioning, Account-State Lifecycle, And Concurrent First Login

## At A Glance

| Field | Value |
|---|---|
| Pass | `WS03-02` |
| Track | `WS03 Identity, account state, authorization, and admin security` |
| Type | Domain implementation / current trusted evidence |
| Primary controls | `IAM-005`, `IAM-009`, `IAM-018` |
| Authority basis | Current accepted `develop` implementation truth, locked audit findings, 163-control checklist, final remediation plan, master blueprint, approved identity decisions, accepted `WS03-01` plan |
| Depends on | `WS03-01`; `WS04-01` and `WS04-02` design inputs only where current schema/transactions make them concrete |
| Accepted baseline | `9900522abaccef0a91fa20d79c3e6b1660b1f16a` |
| Remediation branch | `pr/WS03-02-remediation` |
| Trusted test scope | `backend/tests/workflows/account_lifecycle_concurrency` |
| Requirement declaration | `backend/tests/support/requirements/ws03_02.json` |
| Historical provenance | PR #127, historical branch `pr/WS03-02`, historical base `c89a96b1ef409ef0fa315971cc958fd563bbec96`, historical head `4017e65c925cb26164a1f079acd45ef8bbebaeea`, historical merge `cc5131cc19a27e7f2da313fe8622e03f9e5321e1` |

## 1. Purpose

WS03-02 closes the repository-owned identity lifecycle gap left after
WS03-01. WS03-01 established that Firebase/provider identity is authenticated
first and PostgreSQL then decides local application authority. WS03-02 proves
that local user provisioning, repeated sync, account lifecycle transitions,
and first-login races preserve that authority split.

The pass requires trusted evidence that:

- a Firebase UID maps to one stable Pickup Lane user identity;
- provider email is a mutable snapshot, not the local-account join key;
- concurrent first login cannot create duplicate users or duplicate dependent
  context rows;
- same-UID repeat sync may refresh snapshots and repair expected context rows
  without replacing the user;
- different-UID/same-email attempts fail safely instead of taking over an old
  account;
- local `active`, `suspended`, `pending_deletion`, and `deleted` states are
  preserved and enforced on new protected requests;
- account deletion has explicit local/provider failure boundaries and does not
  blindly retry unknown external outcomes;
- repository-owned recovery and sign-in response behavior is
  enumeration-resistant where WS03-02 owns it;
- final active local administrator protections are covered where the source
  owns them.

This pass does not complete live Firebase recovery governance, provider control
plane access reviews, production revocation timing, deployed multi-instance
propagation measurements, durable deletion reconciliation workers, or the
global WS04 database architecture.

## 2. Why This Matters

Identity lifecycle bugs are high-impact because they can turn ordinary auth
state changes into account takeover, duplicate accounts, stale authorization,
or unrecoverable deletion outcomes.

Concrete failures this pass is designed to prevent include:

- two simultaneous first-login requests creating two local users for one
  Firebase UID;
- first login creating a user row but missing `UserSettings` or `UserStats`;
- a Firebase email change replacing or relinking the wrong local user;
- a different Firebase UID attaching to an existing account only because it
  presents the same email snapshot;
- a suspended or pending-deletion user becoming active again through sync;
- an open app process authorizing an admin/user role from cached local state
  after PostgreSQL has changed;
- a provider-delete timeout being treated as safe to retry without knowing
  whether Firebase deleted the identity;
- a final local admin being demoted, suspended, or deleted by concurrent local
  operations.

## 3. Authority Reconstruction

### 3.1 Repository Truth And Provenance

Current accepted `develop` at
`9900522abaccef0a91fa20d79c3e6b1660b1f16a` is repository truth for the
current implementation state.

The authoritative production-readiness sources and this reconciled plan define
what must be true. Historical PR #127 remains provenance only. Its changed
files were:

1. `backend/tests/shared/authentication/test_ws03_02_account_lifecycle_concurrency.py`
2. `docs/production-readiness/planning/passes/ws03/ws03-02-account-lifecycle-concurrency.md`
3. `frontend/src/lib/authErrors.js`
4. `frontend/tests/unit/authErrors.test.js`

Those historical tests and validation counts do not define trusted evidence
under the current EN-01 architecture. Useful behavior from PR #127 is retained
only after reconciliation against current authority and current source.

### 3.2 Primary Controls

| Control | Authoritative requirement for this pass | Current Gate A interpretation |
|---|---|---|
| `IAM-005` | Provision local users idempotently by Firebase UID with uniqueness and concurrent-first-login protection. Never attach a new UID to an old account merely because email matches. | Source-owned and executable. Requires current PostgreSQL schema evidence, service/API behavior, and real independent-session concurrency proof. |
| `IAM-009` | Keep account recovery and sign-in responses enumeration-resistant and abuse-controlled. Preserve recovery ownership, factor reset, and emergency revocation procedures. | Repository-owned sign-in/reset response behavior and local recovery/linking absence are executable. Provider dashboard settings, abuse controls, factor reset, emergency revocation, and live runtime recovery remain external/process evidence. |
| `IAM-018` | Use named administrator accounts, controlled bootstrap/offboarding, and prevent unsafe removal of the final recoverable administrator. Shared accounts are prohibited. Impersonation/break-glass are conditional and tightly controlled if implemented. | Source-owned bootstrap constraints and final active local admin protections are executable. Named admin-account operations, offboarding records, shared-account prohibition, impersonation, and break-glass governance remain external/process evidence. |

### 3.3 Locked Audit Findings

The locked audit findings classified all three controls as `PARTIAL`.

- `IAM-005`: current source already has `users.auth_user_id` uniqueness, active
  UID lookup, idempotent same-UID sync, email-collision conflict handling, and
  `IntegrityError` retry behavior, but no current trusted PostgreSQL
  simultaneous first-login proof.
- `IAM-009`: current source has Firebase password reset and generic sign-in
  mismatch handling for ordinary credential failures, but provider recovery
  abuse controls, Firebase dashboard settings, factor reset, emergency
  revocation, and signup email-availability policy evidence remain outside
  local pytest.
- `IAM-018`: current source has bootstrap checks and final-active-admin
  protections in role, suspension, self-delete, and admin-delete flows, but
  named admin account policy, offboarding, shared-account prohibition,
  impersonation, and break-glass evidence remain provider/operations owned.

### 3.4 Approved Decisions

The relevant approved decision records are:

- `IDB-01`: Firebase browser auth persistence and bearer-token transport are
  approved; logout/account switch cache reset and mutation replay controls are
  later-owned where not source-proven here.
- `IDB-02`: Firebase owns authentication identity and provider facts.
  PostgreSQL owns Pickup Lane business identity, roles, account restrictions,
  permissions, and resource ownership. Provider-derived local values are
  snapshots. Sync conflicts must fail safely.
- `IDB-03`: Firebase owns email verification. Unverified users may access
  recovery flows; sensitive user/admin actions require current verified
  provider identity where the owning pass requires it.
- `WS02-04B2A2A` active request rules: self-account deletion confirmation must
  be the trimmed case-insensitive value `DELETE`; WS03-02 owns the broader
  account deletion lifecycle.

No approved owner decision was found that turns `/auth/email-availability` into
a local recovery authority. This plan treats that endpoint as a current signup
preflight surface to classify and contain, not as evidence that provider abuse
controls or production enumeration risk are closed.

## 4. Prerequisites And Design Inputs

### 4.1 Accepted WS03-01 Dependency

WS03-02 preserves the accepted WS03-01 identity authority contract:

- Firebase UID, provider account state, provider email, and provider
  verification are provider facts.
- PostgreSQL owns the local app user id, local email snapshot, local role,
  account status, hosting status, permissions, resource ownership, audit, and
  support state.
- Protected requests authenticate current provider identity first, then resolve
  the local PostgreSQL user by Firebase UID.
- Token claims, frontend state, local request bodies, or profile update inputs
  cannot grant local identity, role, status, verification, or admin authority.
- WS03-01 explicitly handed concurrent first login, account linking, recovery
  lifecycle, deletion lifecycle, and cross-instance account lifecycle
  transitions to WS03-02.

WS03-02 does not reopen WS03-01 unless Gate B evidence finds a real authority
conflict.

### 4.2 WS04-01 And WS04-02 Design Inputs

WS04-01 and WS04-02 are not complete. WS03-02 may only consume design inputs
that are already concrete in current source and schema:

- current tests run against the dedicated PostgreSQL test database;
- `SessionLocal` creates independent SQLAlchemy sessions for service-level
  concurrency proof;
- current Alembic migrations create the relevant uniqueness and one-per-user
  constraints;
- current role/account-state mutation services use PostgreSQL transactions and
  `SELECT ... FOR UPDATE` style row locks where final-admin decisions require
  locked current state;
- first-login provisioning correctness depends on PostgreSQL uniqueness plus
  `IntegrityError` rollback/re-read behavior, so real database concurrency
  evidence is required.

WS03-02 must not invent the broader WS04 connection-budget, least-privilege,
transaction taxonomy, global lock ordering, deadlock policy, retry framework,
or migration rehearsal policy. If Gate B finds that WS03-02 cannot be proven
without those broader WS04 decisions, the pass must stop for Gate A correction.

## 5. Current Source Findings

### 5.1 Identity And Provisioning

Current source routes `/auth/sync-user` through
`backend/services/auth_account_service.py`. The service derives sync payloads
from verified Firebase identity, normalizes provider email, and creates or
updates local users through the database session.

Current behavior:

- existing non-terminal local users are looked up by Firebase UID;
- same-UID repeat sync preserves the internal `users.id`;
- same-UID email changes update the local email snapshot only after checking
  for another local owner;
- missing `UserSettings` and `UserStats` rows are repaired for an existing
  user;
- a new UID with an already-owned email fails with conflict instead of relinking
  to the old account;
- duplicate first-login insert races rely on PostgreSQL uniqueness and
  `IntegrityError` handling to roll back and re-read the winner when the winner
  has the same UID/email.

### 5.2 Database Invariants

Current model and migration truth agree for the WS03-02 invariants:

- `users.auth_user_id` is nullable to support deletion/anonymization states,
  with a unique constraint on non-null values.
- `users.email` is nullable to support deletion/anonymization states, with a
  unique constraint on non-null values.
- `users.account_status` is constrained to `active`, `suspended`,
  `pending_deletion`, and `deleted`.
- `users.role` is constrained to `player` and `admin`.
- `user_settings.user_id` is the primary key and a foreign key to `users.id`
  with cascade delete.
- `user_stats.user_id` is the primary key and a foreign key to `users.id` with
  cascade delete.

No WS03-02 migration is approved by this plan. Gate B evidence must inspect the
actual test database constraints, not rely only on ORM declarations.

### 5.3 Account Lifecycle States

Current source uses these local account states:

| Local state | Who/what enters it | Auth sync behavior | Protected request behavior | Can return to active? | Provider mutation involved |
|---|---|---|---|---|---|
| `active` | normal provisioning, admin unsuspension, restored deletion failure | allowed for same UID; snapshots/context rows may be refreshed | ordinary active-user routes allowed when other requirements pass | already active | no |
| `suspended` | admin suspension | same-UID sync must not unsuspend or replace the user | `require_active_user` and admin dependencies deny new protected requests | yes, through admin unsuspension | no |
| `pending_deletion` | self/admin deletion staging or partial/unknown delete outcome | sync must not recreate/reactivate | UID lookup excludes pending-deletion users; new protected requests fail | only through explicit repair/restore path, not ordinary sync | yes, when deletion workflow has reached provider boundary |
| `deleted` | completed self/admin deletion cleanup/anonymization | sync must not recreate by stale auth link or email | deleted rows have `deleted_at` and cleared auth link after cleanup; protected requests fail | no ordinary return path | provider deletion has succeeded or local cleanup has completed |

Suspension is a local product/account restriction. It does not itself disable
the Firebase provider account. Source tests may prove new protected requests
after the committed state change re-read PostgreSQL and deny access, but they
must not claim to cancel a request that was already authorized before the
change.

### 5.4 Account Deletion

Current self-delete and admin-delete workflows stage local deletion, interact
with Firebase through a provider boundary, and then checkpoint local cleanup:

- local state is staged to `pending_deletion`;
- provider deletion is attempted if an auth link exists;
- definitive provider failure attempts to restore the previous local state;
- provider mutation timeout/unknown outcome records support follow-up and
  preserves the auth link;
- provider success followed by local checkpoint or cleanup failure records
  support follow-up and clears the local auth link when Firebase deletion is
  known to have succeeded;
- successful local cleanup anonymizes/deletes local account state and leaves
  the account non-authenticatable;
- repeated deletion after completed cleanup is rejected without reissuing the
  provider delete.

Durable retry and automated reconciliation for partial deletion outcomes remain
WS05 territory. WS03-02 may prove the current safe boundary and support flag
state, not a future worker.

### 5.5 Account Recovery And Linking

Current source uses Firebase client SDK recovery:

- forgot-password sends Firebase reset email;
- `auth/user-not-found` on forgot-password routes to the same check-email
  experience as success;
- reset-password verifies and confirms Firebase reset codes;
- sign-in credential mismatch messages currently normalize
  `invalid-credential`, `wrong-password`, and `user-not-found` to
  `Email or password is incorrect.`;
- adding a password uses Firebase `linkWithCredential` for the current
  Firebase user;
- no current local route was found that merges local accounts, reassigns
  `auth_user_id` by matching email, or creates a separate Pickup Lane recovery
  authority.

Signup email availability remains a current public signup preflight. WS03-02
must classify it and ensure it is not used as a local recovery or relinking
authority. It must not claim provider abuse controls or production enumeration
risk are fully closed.

### 5.6 Local State Freshness

Current protected dependencies resolve provider identity and then query
PostgreSQL by Firebase UID for the current user. `require_active_user`,
`require_verified_user`, and `require_active_admin` enforce current local
account status, provider verification where required, role, and deletion state
on new requests. No process-local role/account-status cache was found in the
protected backend dependency path.

Local tests can prove new request behavior within a process and independent
database sessions. They cannot prove deployed multi-instance propagation
intervals, edge cache behavior, provider revocation timing, or production
connection pool behavior.

### 5.7 Administrator Lifecycle

Current source includes repository-owned `IAM-018` safeguards:

- bootstrap promotes only an existing local user with matching non-disabled
  Firebase identity;
- ordinary registration/profile inputs do not self-grant admin role;
- role demotion, suspension, self-delete, and admin-delete paths protect the
  final active local administrator;
- role/suspension/delete flows use current database state and locks where
  final-admin decisions can race.

WS03-02 keeps final active local administrator protection in scope because
`IAM-018` explicitly requires preventing unsafe final-admin removal and the
current source owns these local safeguards. Provider and operational admin
governance remain deferred.

## 6. Stable Requirements

Requirement declaration scopes are checker-compatible and relative to
`backend/tests`.

| ID | Requirement | State | Declaration scope | Source controls | Proof layer | External/later-owner boundary |
|---|---|---|---|---|---|---|
| `WS03-02-R1` | Stable UID/local-user linkage | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `IDB-02`, `WS03-01` | API/service/PostgreSQL | Provider account-linking UX/governance remains provider/client owned. |
| `WS03-02-R2` | Concurrent first login creates one local user | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `WS04-02`, `WS03-02` | PostgreSQL independent-session concurrency | Broader global DB concurrency framework remains WS04. |
| `WS03-02-R3` | One-per-user context rows are provisioned and repairable | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `IDB-02`, `WS03-02` | PostgreSQL schema/service | Future context tables remain their own owners. |
| `WS03-02-R4` | Same-UID repeat sync preserves user identity and refreshes snapshots safely | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `IAM-009`, `IDB-02`, `IDB-03` | API/service/PostgreSQL | Live provider email-verification behavior remains provider/runtime evidence. |
| `WS03-02-R5` | Different UID with same email cannot take over or merge into the old account | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `IDB-02` | API/service/PostgreSQL | Explicit future account-linking, if approved, requires a new owner decision. |
| `WS03-02-R6` | Local account lifecycle states are preserved and enforced | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `IAM-009`, `IDB-02`, `WS03-01` | API/service/PostgreSQL | Deployed cross-instance timing and provider disable/revoke timing remain external/runtime evidence. |
| `WS03-02-R7` | Account deletion has safe provider/local failure boundaries | required | `workflows/account_lifecycle_concurrency` | `IAM-009`, `IDB-01`, `WS02-04B2A2A`, `WS03-02` | service/PostgreSQL/provider fake | Durable retry/reconciliation remains WS05. |
| `WS03-02-R8` | Repository-owned recovery, sign-in, and linking behavior does not create enumeration or local takeover paths | required | `workflows/account_lifecycle_concurrency` | `IAM-009`, `IDB-01`, `IDB-02`, `IDB-03` | frontend-source/static plus backend-source/static | Provider abuse controls, factor reset, emergency revocation, and live Firebase recovery remain external/process evidence. |
| `WS03-02-R9` | New protected requests use current local PostgreSQL state, not process-local account/role cache | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `IAM-009`, `IAM-018`, `WS03-01` | API/dependency/PostgreSQL | Production propagation interval remains runtime evidence. |
| `WS03-02-R10` | Final active local administrator removal is prevented | required | `workflows/account_lifecycle_concurrency` | `IAM-018`, `IDB-02`, `IDB-03` | service/PostgreSQL concurrency | Named admin accounts, offboarding records, shared-account ban, break-glass, and provider recovery remain governance/provider evidence. |
| `WS03-02-R11` | Negative-space inventory catches lifecycle, recovery, and admin bypasses | required | `workflows/account_lifecycle_concurrency` | `IAM-005`, `IAM-009`, `IAM-018`, `WS03-01` | dynamic/static inventory | Whole-program authorization remains WS03-04; browser cache/account switch remains WS07-02. |
| `WS03-02-R12` | External provider/runtime/operations facts are not closed by local pytest | deferred | `governance` | `IAM-009`, `IAM-018`, `WS04`, `WS05`, `WS07`, `WS10` | non-executable governance record | Must have zero pytest mappings. |

`WS03-02-R1` through `WS03-02-R11` are required and executable in
`backend/tests/workflows/account_lifecycle_concurrency`. `WS03-02-R12` is
deferred/governance and must have zero pytest mappings.

## 7. Technical Design / Contracts

### 7.1 Stable Identity Contract

Firebase UID is the only stable provider-to-local linkage key for current
WS03-02 behavior. PostgreSQL `users.id` is the stable Pickup Lane internal
identity used by business relationships.

The contract is:

- current provider identity must be verified before local user authority;
- same Firebase UID maps to the same non-terminal local user;
- provider email may update the local email snapshot for the same UID;
- provider email must not reassign, merge, or transfer local identity;
- a different UID presenting an existing local email must fail safely;
- a recovery or linking flow must not attach a UID to a local account by email
  alone;
- terminal or pending-deletion local account states must not be resurrected by
  ordinary sync.

### 7.2 Concurrent First-Login Contract

First login for the same verified Firebase UID/email must be safe under real
PostgreSQL concurrency.

Gate B evidence must use:

- two independent SQLAlchemy sessions/connections;
- deterministic barriers or synchronization;
- real insert/commit behavior against the PostgreSQL test database;
- winner/loser assertions;
- final-state assertions for `users`, `user_settings`, and `user_stats`;
- no sleep-based race proof and no mocked database uniqueness.

Required final state:

- exactly one `users` row exists for the Firebase UID;
- exactly one local email snapshot exists for the email;
- both concurrent callers either return the same local user or the loser
  re-reads the winner through approved conflict handling;
- one `user_settings` row exists for that user;
- one `user_stats` row exists for that user;
- no orphan dependent row exists.

### 7.3 Repeat Sync And Repair Contract

Same-UID repeat sync may:

- update provider-derived email and verification snapshots;
- repair missing `UserSettings`;
- repair missing `UserStats`;
- preserve the local `users.id`;
- preserve local role, account status, hosting restrictions, ownership, and
  business relationships except where current provider verification refresh
  changes source-owned snapshot/eligibility state.

Same-UID repeat sync must not:

- create a replacement user;
- silently unsuspend a user;
- recreate a pending-deletion or deleted user;
- attach to another user's email;
- assign admin privileges.

### 7.4 Lifecycle Enforcement Contract

New protected requests must enforce current local PostgreSQL state after
provider identity is accepted.

The evidence should prove:

- active users can access representative active-user routes;
- suspended users are denied representative active-user routes;
- pending-deletion and deleted users are denied by local lookup/deletion state;
- admin role changes are reflected on the next admin-protected request;
- local sync does not undo suspension or terminal deletion state;
- the dependency path is not authorized by frontend role hints, token custom
  claims, or process-local user caches.

### 7.5 Account Deletion Failure Contract

Deletion behavior must distinguish these outcomes:

- definitive provider failure restores the prior local status when possible and
  does not mark provider deletion as complete;
- provider success followed by local cleanup/checkpoint failure leaves support
  evidence and prevents the local auth link from remaining usable;
- provider timeout or unknown mutation outcome leaves support evidence,
  preserves enough identity to reconcile, and does not blindly replay provider
  delete;
- completed deletion anonymizes/unlinks local account state;
- repeated deletion after completed cleanup is rejected without provider retry;
- sync during pending deletion must not recreate or reactivate the account.

Provider fakes may be used to force error boundaries. They must be described as
repository-owned boundary tests, not live Firebase proof.

### 7.6 Recovery And Linking Contract

WS03-02 repository-owned recovery behavior is limited to current source:

- ordinary sign-in credential mismatch errors must not distinguish
  account-not-found from wrong password/invalid credential;
- forgot-password account-not-found must navigate to the same check-email
  experience as success;
- reset-password remains Firebase-code based;
- credential linking is provider-side for the current Firebase user;
- local source must not expose account merge, email-based UID reassignment, or
  local recovery routes that become a second account authority;
- signup email availability is classified as a public signup preflight and not
  used as recovery/linking proof.

### 7.7 Final Active Local Administrator Contract

Local source must prevent zero active local admins through the owned mutation
paths:

- last active admin cannot be demoted;
- last active admin cannot be suspended;
- last active admin cannot self-delete;
- last active admin cannot be admin-deleted;
- concurrent admin role mutations must not both commit in a way that leaves
  zero active admins.

This is local repository evidence only. It does not prove actual production
admin identities are named, recoverable, MFA-protected, or properly offboarded.

## 8. Implementation Scope

### 8.1 Gate A Scope

Gate A modifies only this canonical plan:

1. `docs/production-readiness/planning/passes/ws03/ws03-02-account-lifecycle-concurrency.md`

Gate A does not create tests, requirement JSON, a `TESTING_RECORD.md`,
production source changes, frontend source changes, migrations, commits, or a
PR.

### 8.2 Gate B Remediation Type

Final Gate A classification: **A - evidence reconstruction only**.

Current source reconciliation found no required backend production correction,
frontend production correction, migration/model correction, or testing
infrastructure correction for WS03-02. The historical plan is materially
rewritten into the current template, but the Gate B work is trusted evidence
reconstruction against already-accepted source behavior.

If Gate B evidence exposes an actual in-scope source or schema defect, Gate B
must stop for a Gate A correction instead of broadening this frozen file set.

### 8.3 Exact Gate B Editable File Set

Gate B may edit exactly these files:

1. `backend/tests/support/requirements/ws03_02.json`
2. `backend/tests/workflows/account_lifecycle_concurrency/TESTING_RECORD.md`
3. `backend/tests/workflows/account_lifecycle_concurrency/test_account_provisioning_identity_contract.py`
4. `backend/tests/workflows/account_lifecycle_concurrency/test_concurrent_first_login_contract.py`
5. `backend/tests/workflows/account_lifecycle_concurrency/test_lifecycle_state_enforcement_contract.py`
6. `backend/tests/workflows/account_lifecycle_concurrency/test_account_deletion_failure_boundary_contract.py`
7. `backend/tests/workflows/account_lifecycle_concurrency/test_recovery_and_linking_contract.py`
8. `backend/tests/workflows/account_lifecycle_concurrency/test_final_admin_lifecycle_contract.py`
9. `backend/tests/workflows/account_lifecycle_concurrency/test_account_lifecycle_negative_space_contract.py`

Do not edit production backend source, frontend source, frontend tests,
migrations, shared testing infrastructure, other pass plans, other requirement
JSON files, or other `TESTING_RECORD.md` files during Gate B unless a new Gate
A correction approves that wider scope.

Existing `frontend/tests/unit/authErrors.test.js` is useful corroborating
validation, but it is not part of the planned Gate B editable set because no
frontend source/test correction is currently approved.

## 9. Testing And Evidence Design

### 9.1 Evidence Architecture

| Planned artifact | Requirements | Responsibility |
|---|---|---|
| `backend/tests/support/requirements/ws03_02.json` | R1-R12 | Declare machine-readable requirement IDs, owning pass, source controls, states, and checker-compatible scopes. R12 remains `deferred` / `governance`. |
| `TESTING_RECORD.md` | R1-R12 | Human evidence record for threat model, state matrix, proof layers, concurrency method, deletion failure boundaries, provider fake limits, external gaps, and adequacy. |
| `test_account_provisioning_identity_contract.py` | R1, R3, R4, R5 | Prove current database constraints from the live test DB, stable UID/internal-user behavior, same-UID email snapshot refresh, context-row repair, and same-email/different-UID conflict without relink. |
| `test_concurrent_first_login_contract.py` | R2, R3, R5 | Prove simultaneous first login with independent PostgreSQL sessions/connections, deterministic barriers, winner/loser handling, and final row counts for user/settings/stats. |
| `test_lifecycle_state_enforcement_contract.py` | R4, R6, R9 | Prove suspended, pending-deletion, and deleted local users are not silently reactivated by sync and that new protected requests enforce current PostgreSQL state. |
| `test_account_deletion_failure_boundary_contract.py` | R6, R7 | Prove self/admin deletion staging, definitive provider failure restore, provider-success/local-failure support state, unknown provider outcome support state, auth-link preservation/clearing rules, and repeated-delete rejection. |
| `test_recovery_and_linking_contract.py` | R1, R5, R8 | Prove source-level sign-in mismatch normalization, forgot-password account-not-found equivalence, Firebase-owned reset/linking, no local merge/reassignment path, and signup email availability containment. |
| `test_final_admin_lifecycle_contract.py` | R9, R10 | Prove bootstrap/source constraints relevant to local admins, final-admin demotion/suspension/self-delete/admin-delete protection, and deterministic concurrent admin mutation behavior. |
| `test_account_lifecycle_negative_space_contract.py` | R1, R5, R6, R7, R8, R9, R10, R11 | Dynamic/static inventory over active backend/frontend source for lifecycle bypasses, alternate provisioning paths, email-based relink, sync resurrection, local cache authority, unsafe deletion retry, local recovery authority, and final-admin bypasses. |

No pytest may map `WS03-02-R12`.

### 9.2 Negative-Space Strategy

Gate B negative-space evidence must fail closed if a new active path appears
that could bypass WS03-02 invariants.

The inventory must evaluate:

- local account lookup/relink by mutable email instead of Firebase UID;
- alternate provisioning paths outside central sync;
- direct routes that create local users from request-supplied UID/email;
- sync recreating `pending_deletion` or `deleted` users;
- sync unsuspending a suspended user;
- duplicate dependent-row provisioning paths;
- local account merge/reassignment behavior;
- provider-success/local-failure treated as full success;
- unknown provider outcome blindly retried;
- deleted accounts reattached by email;
- process-local account-status or role cache in protected dependencies;
- recovery flows creating a second local authority;
- final-admin protections bypassed by role, suspension, self-delete, or
  admin-delete paths.

The negative-space test may inspect source text and FastAPI route/dependency
inventory where that is the lowest reliable layer. It must stay narrower than
WS03-04 object-level authorization.

### 9.3 TESTING_RECORD Design

Gate B must create
`backend/tests/workflows/account_lifecycle_concurrency/TESTING_RECORD.md` from
the current template. It must include:

- provisioning threat model;
- stable identity invariant;
- concurrent first-login method and final-state assertions;
- dependent context-row uniqueness and repair;
- same-UID repeat-sync and provider snapshot refresh;
- different-UID/same-email conflict behavior;
- lifecycle state matrix;
- local state freshness and cache limitations;
- deletion stages and failure boundaries;
- unknown provider outcome and WS05 handoff;
- recovery/enumeration behavior and signup email-availability boundary;
- provider-side linking versus local merge prohibition;
- final active local admin boundary;
- PostgreSQL concurrency proof methodology;
- provider fake limitations;
- migration decision;
- WS03-01 dependency;
- WS04 design-input limits;
- provider/runtime/operations gaps;
- deferred R12 with zero pytest mappings;
- adequacy conclusion.

## 10. Validation Plan

Gate B must run the validation below after implementing the approved evidence
set. Historical PR #127 counts are not expected values.

1. Focused WS03-02 trusted evidence:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/account_lifecycle_concurrency
```

2. Accepted dependency regression for WS03-01:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests/workflows/identity_authority
```

3. Domain checker:

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope domain backend/tests/workflows/account_lifecycle_concurrency
```

4. Suite checker:

```bash
DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python backend/tests/check_backend_tests.py --scope suite
```

5. Generated traceability review:

- report exact mapping counts for `WS03-02-R1` through `WS03-02-R12`;
- confirm `WS03-02-R12` has exactly zero pytest mappings.

6. Full trusted backend regression:

```bash
APP_ENV=test DATABASE_URL='postgresql+psycopg://pickup-lane-user:pickup-lane@localhost:5432/pickup_lane_test_db' backend/.venv/bin/python -m pytest -q backend/tests
```

7. Diff integrity:

```bash
git diff --check
git status --short --untracked-files=all
```

No frontend lint/build/unit validation is required by the planned Gate B file
set because no frontend source or frontend test change is approved. If a future
Gate A correction approves frontend edits, validation must add the appropriate
frontend commands.

No Alembic upgrade/downgrade validation is required because no migration is
approved. If a future Gate A correction approves schema changes, validation
must be redesigned.

## 11. Provider, Runtime, And Later-Pass Handoffs

### 11.1 Provider / Runtime Unknowns

WS03-02 local evidence cannot close:

- live Firebase account recovery configuration;
- provider abuse controls and rate limits for recovery;
- factor reset and emergency revocation procedures;
- real disabled/deleted/revoked provider propagation timing;
- Firebase/GCP control-plane ownership and recovery;
- actual production named admin account inventory;
- provider MFA or backup-owner status;
- deployed multi-instance propagation interval;
- edge/CDN/browser cache propagation;
- production database connection budget and pool behavior.

These must remain explicit external/provider/runtime/process gaps in the
testing record and final Gate B report.

### 11.2 Later Owners

- `WS03-03`: recent auth, MFA, App Check, and advanced auth/provider controls.
- `WS03-04`: full object-level authorization and IDOR matrix.
- `WS04-01`: database engine/session lifecycle, connection budget, provider
  topology, and least-privilege roles.
- `WS04-02`: global transaction, invariant, lock, and deterministic
  concurrency framework.
- `WS05`: durable jobs, deletion reconciliation, retry workers, and repair
  automation for partial external outcomes.
- `WS07-02`: browser cache/account-switch isolation.
- `WS09/WS10`: broader audit/provider/governance evidence where applicable.

## 12. Migration, Rollback, And Compatibility

No migration is approved for WS03-02.

Current schema supports the required repository-owned invariants for accepted
source behavior. `auth_user_id` and `email` remain nullable for deletion and
anonymization states. Active, non-terminal accounts are expected to have a
Firebase UID through current provisioning/source paths; Gate B evidence must
prove no active current route creates a local user authority from request body
UID/email.

Because Gate B is evidence reconstruction only:

- there is no runtime rollback plan;
- no database backfill is required;
- no compatibility migration is required;
- no production traffic behavior should change;
- if tests expose a source/schema defect, stop for Gate A correction instead
  of patching outside the frozen scope.

## 13. Stop Conditions

Gate B must stop and return for Gate A correction if any of these occur:

- current source permits email-based UID takeover or local merge without
  approved linking authority;
- simultaneous first login cannot be proven deterministically against
  PostgreSQL without source/schema changes;
- current schema lacks an essential invariant that must be corrected by
  migration;
- a required proof depends on unfinished WS04 architecture rather than current
  concrete schema/transaction behavior;
- recovery/enumeration cannot be evidenced without frontend source changes;
- local account deletion failure handling is materially different from this
  plan;
- final local admin protection is not actually enforced by current source;
- the negative-space inventory requires editing shared test infrastructure or
  production source;
- provider/runtime evidence is needed to claim a local requirement closed.

## 14. Gate A Freeze

After this Gate A correction, the proposed frozen plan is this exact file:

`docs/production-readiness/planning/passes/ws03/ws03-02-account-lifecycle-concurrency.md`

The Gate A final report must include:

- branch, HEAD, and merge-base;
- confirmation only this file changed;
- `git diff --check`;
- `git status --short --untracked-files=all`;
- SHA-256 for this final canonical plan.

Human approval of this exact plan hash is required before Gate B may begin.
