# WS03-02 Account Lifecycle Concurrency Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS03-02` |
| Trusted test scope | `backend/tests/workflows/account_lifecycle_concurrency` |
| Requirement declaration | `backend/tests/support/requirements/ws03_02.json` |
| Authoritative sources | Frozen WS03-02 canonical plan; current accepted repository truth; `IAM-005`; `IAM-009`; `IAM-018`; approved decisions `IDB-01`, `IDB-02`, `IDB-03`; accepted WS03-01 plan |
| Evidence layers | pytest; real PostgreSQL; independent SQLAlchemy sessions/connections; FastAPI dependency/API behavior; source/static inventory; controlled provider fakes; generated checker traceability; governance deferral for R12 |

## 1. Scope

This record covers trusted repository evidence for WS03-02 account provisioning,
stable Firebase UID to local `users.id` linkage, concurrent first login,
one-per-user `UserSettings` and `UserStats` rows, same-UID repeat sync and
provider snapshot refresh, different-UID/same-email conflict behavior, local
account-state lifecycle enforcement, account deletion failure boundaries,
source-owned recovery/linking behavior, and final active local administrator
protection.

This record does not claim live Firebase configuration, provider recovery abuse
controls, factor reset, emergency revocation, provider control-plane
governance, production named-admin operations, deployed multi-instance
propagation timing, browser cache/account-switch runtime behavior, complete
object-level authorization, durable deletion retry workers, or global WS04
database architecture.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS03-02-R1` | Firebase UID is the stable provider key and local `users.id` remains the stable Pickup Lane identity. | pytest |
| `WS03-02-R2` | Concurrent first login for the same Firebase UID creates one local user. | pytest |
| `WS03-02-R3` | One `UserSettings` and one `UserStats` row exist per local user and missing rows are repairable. | pytest |
| `WS03-02-R4` | Same-UID repeat sync preserves local identity and safely refreshes provider snapshots. | pytest |
| `WS03-02-R5` | A different Firebase UID with the same email cannot take over, merge into, or relink the old account. | pytest |
| `WS03-02-R6` | Local `active`, `suspended`, `pending_deletion`, and `deleted` states remain authoritative and enforced. | pytest |
| `WS03-02-R7` | Self/admin account deletion has safe provider/local failure boundaries and no blind retry of unknown outcomes. | pytest |
| `WS03-02-R8` | Repository-owned recovery, sign-in, and linking behavior does not create enumeration or local takeover paths. | pytest |
| `WS03-02-R9` | New protected requests use current PostgreSQL state, not process-local role/account cache authority. | pytest |
| `WS03-02-R10` | Local source prevents removal of the final active local administrator. | pytest |
| `WS03-02-R11` | Active-source inventory fails closed for lifecycle, recovery, and admin bypasses. | pytest |
| `WS03-02-R12` | External provider/runtime/operations facts remain unclosed by local pytest. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1, R4, R5 | Firebase UID, not email, links provider identity to a local user. | Email change or reused email attaches the wrong Firebase UID to an existing local user. | Account takeover or identity merge. | Provider-authenticated sync, local uniqueness, conflict checks, and no local merge/relink path. | workflow/API/service/PostgreSQL |
| R2, R3 | Simultaneous first login creates one user plus one settings and one stats row. | Two sessions create duplicate users or partial context rows. | Split identity, missing preferences/stats, inconsistent authorization. | PostgreSQL uniqueness, transaction rollback, re-read of winner, and context primary keys. | workflow/PostgreSQL concurrency |
| R3, R4 | Missing one-per-user context rows are repaired without duplication. | Repair creates duplicate rows or fails to restore required local context. | Profile/settings/stats behavior breaks after partial provisioning. | Primary-key dependent tables and sync repair helper. | workflow/service/PostgreSQL |
| R6, R9 | Current PostgreSQL account/role state is read on new protected requests. | Process-local state or provider/client claims keep a stale user active or admin. | Suspended/deleted/demoted accounts retain access. | FastAPI dependency path resolves provider identity then current local user state. | workflow/API/PostgreSQL |
| R6, R7 | Deletion states do not resurrect through sync or retry. | Pending/deleted accounts are recreated, or ambiguous provider deletes are replayed blindly. | Account recovery without authority or duplicate external mutation. | Staged states, support flags, auth-link preservation/clearing rules, and terminal sync denial. | workflow/service/PostgreSQL/provider fake |
| R8 | Recovery/linking remains Firebase/provider owned and public responses are safe where repository-owned. | Sign-in/reset reveals account existence, or local source creates merge/reassignment authority. | Account enumeration or takeover. | Frontend/backend source inventory and current error/flow checks. | workflow/source/static |
| R10 | Admin bootstrap grants local admin only to an existing linked active local user that matches a non-disabled Firebase identity, and the final active local administrator cannot be removed by local mutation paths. | Bootstrap creates or exposes unsafe admin grant authority, ordinary sync self-grants admin, or concurrent demotions/deletions/suspensions leave zero active local admins. | Unauthorized admin elevation or administrative lockout. | Source/route inventory, row locks, final-admin counts, previews, and guarded rejections. | workflow/source/static/service/PostgreSQL concurrency |
| R11 | Active-source inventory catches new bypass paths. | A new route/helper creates users, relinks by email, caches role/status, retries unknown deletion, or bypasses final-admin checks. | Point tests pass while nearby source regresses. | Dynamic route/source inventory with explicit classifications. | workflow/source/static |
| R12 | Local pytest does not overclaim external/provider/operations closure. | Fake-provider evidence is reported as live Firebase or production governance. | Misleading readiness status. | Deferred declaration, zero pytest mappings, and explicit gaps. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | new Firebase user, existing local user, different Firebase UID with same email, ordinary user, suspended user, pending-deletion user, deleted user, admin, final admin, non-final admin | covered/grouped | These actors materially change provisioning, lifecycle, and admin removal authority. |
| States / lifecycle | `active`, `suspended`, `pending_deletion`, `deleted`; role `player`/`admin`; verified/unverified provider snapshots | covered/grouped | The source-owned lifecycle matrix depends on these finite current states. |
| Actions | sync, first login, repeat login, email snapshot refresh, protected request, self-delete, admin delete, demote, suspend, forgot password, sign-in, provider-side credential link | covered/grouped | These are the WS03-02-owned behavior groups from the frozen plan. Self-delete and admin-delete failure boundaries are distinguished because they have separate workflow owners. |
| Inputs / boundaries | Firebase UID, provider email snapshot, Authorization bearer token, delete confirmation, frontend auth error codes, source paths | covered | Inputs are limited to repository-owned boundaries; provider secrets/tokens are synthetic only. |
| Time | before/after committed local state change, provider timeout unknown outcome, provider success followed by local cleanup failure, repeated delete after cleanup | covered | Local tests prove next-request and failure-state behavior, not production propagation timing. |
| Dependencies | PostgreSQL, SQLAlchemy sessions, FastAPI dependencies, Firebase client/Admin boundaries | covered/deferred | PostgreSQL behavior is executable; live Firebase and deployed runtime facts are R12 deferrals. |
| Concurrency / idempotency | simultaneous same-UID first login, same-email/different-UID race, concurrent final-admin demotion | covered | Real independent sessions and deterministic barriers prove material races. |
| Authorization / privacy / security | stale role/status denial, no email relink, no local recovery authority, no final-admin lockout | covered | These are the core account lifecycle security risks. |
| Persistence / rollback | create user/context rows, sync repair, rejected conflict side effects, deletion support flags, staged/restore states | covered | Tests assert final persisted state after success/failure. |
| Recovery | forgot-password equivalence, Firebase-owned reset, unknown provider delete support state, manual repair | covered/deferred | Source-owned recovery is tested; provider/ops recovery remains deferred. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing local context rows; missing local user after cleared auth link | pytest |
| empty | yes | delete confirmation belongs to WS02-04B2A2A; no new WS03-02 input rule | covered elsewhere |
| corrupt | partial | wrong/stale provider/client role/status data must not authorize | pytest/source |
| exceed | no | no WS03-02 size/bounds claim | not applicable |
| duplicate | yes | duplicate UID/email/context row attempts | pytest/PostgreSQL |
| delay | partial | committed state change seen on next protected request | pytest |
| reorder | yes | deletion provider success before local cleanup failure | pytest/provider fake |
| interrupt | yes | self/admin provider failure, self/admin provider timeout/unknown outcome, self/admin provider success followed by local cleanup failure | pytest/provider fake |
| race | yes | first login and final-admin mutation races | pytest/PostgreSQL |
| expire / revoke | partial | provider revoke/disable timing is external; WS03-01 fakes provider denials | deferred/covered elsewhere |
| tamper | yes | local source must not accept request/body/frontend role, UID, email, or merge authority | pytest/source |
| retry | yes | repeated delete after cleanup and unknown-outcome no blind retry | pytest |
| recover | partial | same-UID sync repairs context rows; provider/ops recovery remains external | pytest/deferred |

### Deletion Failure Boundary Matrix

| Workflow | Scenario | Evidence | Persisted Contract Proved |
|---|---|---|---|
| Self-delete | Definitive provider failure | `test_account_deletion_failure_boundary_contract.py` | Account is staged, provider failure is not reported as complete, prior local status/auth link are restored, and no support flag is opened when restoration succeeds. |
| Self-delete | Provider outcome unknown | `test_account_deletion_failure_boundary_contract.py` | Account remains `pending_deletion`, auth link is preserved for reconciliation, provider call count stays at one across a repeat attempt, and support metadata records `auth_identity_deleted: "unknown"` with app cleanup incomplete. |
| Self-delete | Provider success plus local cleanup failure | `test_account_deletion_failure_boundary_contract.py` | Account remains `pending_deletion`, auth link is cleared because provider deletion is known complete, support metadata records app cleanup failure, and no full deletion success is claimed. |
| Self-delete | Completed and repeated deletion | `test_account_deletion_failure_boundary_contract.py` | Successful cleanup anonymizes/deletes and clears the auth link; a repeated delete is rejected without another provider call. |
| Admin delete | Definitive provider failure | `test_account_deletion_failure_boundary_contract.py` | Target account is staged, provider failure is not reported as complete, prior local status/auth link are restored, and no successful delete audit is created. |
| Admin delete | Provider outcome unknown | `test_account_deletion_failure_boundary_contract.py` | Target remains `pending_deletion`, auth link is preserved, support metadata records unknown provider outcome and incomplete app cleanup, provider call count stays at one across a repeat attempt, and no successful `delete_user` admin action is emitted. |
| Admin delete | Provider success plus local cleanup failure | `test_account_deletion_failure_boundary_contract.py` | Target remains `pending_deletion`, auth link is cleared because provider deletion is known complete, support metadata records app cleanup failure, provider call count stays at one, and no successful `delete_user` admin action is emitted. |
| Admin delete | Other lifecycle boundaries | `test_final_admin_lifecycle_contract.py`; `test_account_deletion_failure_boundary_contract.py` | Final active admin deletion is rejected before provider mutation; admin delete preview/staging is exercised by the admin-delete failure scenarios without relying on last-admin or stale-preview guards. |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1, R3, R4, R5 | Stable UID linkage, live DB constraints, same-UID snapshot refresh, context repair, same-email conflict. | service, PostgreSQL | `test_account_provisioning_identity_contract.py` | Enough for current source-owned provisioning; does not prove live Firebase account linking. |
| R2, R3, R5 | Same-UID first-login race and different-UID/same-email race. | real PostgreSQL concurrency | `test_concurrent_first_login_contract.py` | Uses independent sessions/connections and barriers; does not create global WS04 policy. |
| R4, R6, R9 | Local lifecycle states and next-request local state freshness. | API, service, PostgreSQL | `test_lifecycle_state_enforcement_contract.py` | Enough for source behavior after committed state changes; not deployed propagation timing. |
| R6, R7 | Self/admin deletion staging, provider failure restore, unknown outcome support, local failure support, repeated delete, non-resurrection. | service, PostgreSQL, provider fake | `test_account_deletion_failure_boundary_contract.py` | Fakes force provider boundaries for both self-delete and admin-delete failure classes; not live Firebase proof. |
| R1, R5, R8 | Sign-in/reset equivalence, Firebase-owned reset/linking, no local merge/reassignment, signup availability boundary. | frontend/backend source/static | `test_recovery_and_linking_contract.py` | Enough for repository source; provider abuse controls and runtime recovery remain deferred. |
| R9, R10 | Admin bootstrap source constraints plus final-admin demotion, suspension, self-delete, admin-delete, and concurrent demotion. | source/static, service, PostgreSQL concurrency | `test_final_admin_lifecycle_contract.py` | Enough for local bootstrap and final-admin safeguards; not named-admin/provider governance. |
| R1, R5, R6, R7, R8, R9, R10, R11 | Active-source inventory for bypasses. | source/static, AST inspection, and FastAPI route/dependency inventory | `test_account_lifecycle_negative_space_contract.py` | Discovers active account/auth/user/admin-user route and service candidates, requires every discovered candidate to have an explicit classification, and fails closed on unclassified or contract-violating lifecycle bypasses while staying narrower than WS03-04. |
| R12 | External provider/runtime/operations gap. | governance | Requirement declaration and this record | Correctly unmapped to pytest. |

### Evidence Quality Checks

- PostgreSQL constraint evidence inspects the live test database.
- Concurrency evidence uses real independent SQLAlchemy sessions and records
  distinct PostgreSQL backend process ids.
- Barriers and events coordinate concurrency; no sleep-based race proof is
  used.
- Successful mutations assert final persisted rows and state.
- Rejected mutations assert prohibited side effects did not occur.
- Provider fakes sit at the app-owned Firebase deletion boundary.
- R10 bootstrap evidence imports the active bootstrap script, inspects AST/source
  for existing active local-user lookup, linked-auth requirement, Firebase
  disabled/UID-match checks before local role assignment, no ordinary-sync admin
  self-grant, and no registered bootstrap/admin-grant route.
- Static inventories use active repository source and explicitly avoid
  historical evidence.
- Negative-space route discovery reads the current FastAPI app route table for
  WS03-02 account-lifecycle prefixes and requires exact classification equality.
- Negative-space source discovery scans current account/auth/user/admin-user
  route and service owners by active source signals, then fails if a candidate
  is unclassified or if a stale classification points at a removed file.
- AST checks reject non-approved `User` construction, non-null
  `auth_user_id` reassignment, and unexpected one-to-one context-row
  construction outside the classified current owners.
- R12 has zero pytest mappings.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| First login sync | One `users` row, one `user_settings` row, one `user_stats` row. | Duplicate user/context rows or permanent loser failure. | Loser rolls back/re-reads winner where same UID/email is idempotent. |
| Same-UID repeat sync | Same `users.id`; email/verification snapshots refresh; missing context rows restored. | Role/status/admin authority or internal id changes. | Existing healthy context rows are not duplicated. |
| Different UID same email | Conflict with no new local user for the new UID. | Existing user's UID, email, or id changes. | Failed attempt leaves prior owner intact. |
| Lifecycle state changes | New protected requests enforce current DB state. | Provider/client stale data reactivates or re-admins a user. | Denials leave local state unchanged. |
| Self/admin deletion | Staging, provider boundary, support state, auth-link behavior, and final cleanup follow current source. | Unknown outcome blindly retried; provider success reported as complete after local failure; successful admin delete audit emitted after failure. | Partial/unknown failures are manual/support follow-up; durable retry is WS05. |
| Recovery/linking source | Sign-in/reset public behavior stays generic where owned; linking remains provider-side. | Local merge/reassignment/recovery authority appears. | Active route/source inventory fails when a relevant new candidate lacks explicit classification or contradicts the WS03-02 account-lifecycle contract. |
| Final-admin mutations and bootstrap | Bootstrap only changes role on an existing linked active local user after provider/local checks; non-final operations may proceed; final-admin removal attempts reject. | Bootstrap creates a local user, ordinary sync self-grants admin, unauthenticated route grants admin, or zero active local admins are committed. | Concurrent final-admin mutation serializes so only one demotion succeeds. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS03-02-R12` | deferred | External provider/runtime/operations facts cannot be proved by local pytest. | Provider/runtime/governance evidence |
| Live Firebase recovery settings and abuse controls | deferred | Local source and fakes do not expose dashboard settings, rate limits, factor reset, or emergency revocation. | WS03-03 / provider operations |
| Real provider delete/revoke propagation timing | deferred | Local fakes prove boundary handling only. | Provider/runtime evidence |
| Named admin accounts, shared-account prohibition, offboarding, break-glass | deferred | Repository source proves bootstrap/final-local-admin safeguards, not provider/HR/process records. | Operations/governance |
| Production multi-instance/account-state propagation interval | deferred | Local tests prove next request against PostgreSQL, not deployed topology timing. | Runtime/WS04/hosting evidence |
| Global DB connection budget and transaction taxonomy | deferred | WS03-02 consumes current concrete schema/session/locks only. | WS04-01 / WS04-02 |
| Durable deletion retry/reconciliation worker | deferred | WS03-02 proves safe support state, not worker implementation. | WS05 |
| Complete object-level authorization / IDOR matrix | covered elsewhere | Negative-space inventory stays at identity lifecycle bypasses. | WS03-04 |
| Browser cache/account-switch runtime isolation | covered elsewhere/deferred | WS03-02 source recovery checks are not browser runtime tests. | WS07-02 |
| Checker/generated traceability adequacy | manual | Checker PASS is structural compliance only. | Gate C/human review |

## 9. Adequacy Conclusion

This evidence is adequate for WS03-02 Gate B when focused WS03-02 pytest,
WS03-01 regression, domain checker, suite checker, generated traceability, full
trusted backend regression, diff integrity, and human review all pass.

Requirements R1 through R11 have executable trusted evidence. R12 is deferred
governance with zero pytest mappings. The local evidence is strong for current
repository source, PostgreSQL invariants, and request-time behavior, but it
does not close live Firebase, deployed runtime propagation, named-admin
operations, browser-cache isolation, WS04 database architecture, WS05 durable
reconciliation, or complete WS03-04 authorization obligations. Checker `PASS`
remains machine-compliance evidence only; this record supplies the semantic
adequacy boundary for Gate C review.
