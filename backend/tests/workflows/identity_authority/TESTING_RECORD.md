# WS03-01 Identity Authority Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS03-01` |
| Trusted test scope | `backend/tests/workflows/identity_authority` |
| Requirement declaration | `backend/tests/support/requirements/ws03_01.json` |
| Authoritative sources | Canonical WS03-01 plan; current accepted repository truth; approved decisions `IDB-01`, `IDB-02`, `IDB-03`; production-readiness controls; EN-01 trusted evidence model |
| Evidence layers | pytest; controlled Firebase/provider fakes; FastAPI dependency/API behavior; PostgreSQL-backed state; Pydantic schema inspection; dynamic route/source inventory; frontend source inventory; governance deferral for R11 |

## 1. Scope

This record covers local trusted evidence for the WS03-01 identity authority
boundary: Firebase ID-token verification as provider authority, local
PostgreSQL account authority after provider identity, verified-email policy for
WS03-01-owned route families, provider-derived snapshot semantics, ordinary
identity-field write protection, admin identity authority, Firebase project
settings contracts, and the source-level frontend persistence/transport/replay
boundary approved by `IDB-01`.

This record does not claim deployed Firebase project correctness, provider
dashboard settings, service-account IAM scope, production environment
injection, real provider revocation/disabled-user behavior, HTTPS/CDN/logging
evidence, deployed frontend bundle exposure, cross-instance propagation timing,
MFA, App Check, account linking/recovery lifecycle, or comprehensive browser
cache/account-switch isolation. Those remain R11 governance and later-owner
evidence.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS03-01-R1` | Protected request identity uses Authorization-header bearer transport and project-bound Firebase Admin token verification. | pytest |
| `WS03-01-R2` | Provider account state is current authority for UID, email, verification, disabled/deleted state, and provider availability errors. | pytest |
| `WS03-01-R3` | Local user, role, account status, deletion, ownership, and business authority are applied only after provider identity. | pytest |
| `WS03-01-R4` | Current Firebase email verification gates sensitive WS03-01 actions while allowed public/bootstrap/read exceptions remain open. | pytest |
| `WS03-01-R5` | Local email and `email_verified_at` are provider-derived snapshots, not independent authorization facts. | pytest |
| `WS03-01-R6` | Ordinary profile writes cannot set verifier, provider, admin, ownership, audit, or server-owned identity fields. | pytest |
| `WS03-01-R7` | Admin authority requires current verified provider identity plus active non-deleted local admin role. | pytest |
| `WS03-01-R8` | Active route/service/source inventory must fail closed for identity-authority bypasses. | pytest |
| `WS03-01-R9` | Frontend source uses explicit Firebase persistence, bearer-header transport, bounded safe-read refresh, and no generic mutation replay. | pytest |
| `WS03-01-R10` | Firebase project/credential settings and evidence-secret boundaries are repository-proven without real provider secrets. | pytest |
| `WS03-01-R11` | External provider/runtime/browser/operations facts remain explicitly deferred. | deferred |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1, R2, R10 | Protected identity is verified through the configured Firebase Admin app with revocation checking and provider-user lookup. | A token from another project, a revoked token, a missing UID, or a disabled/deleted provider account is accepted. | Spoofed or stale provider identity can authenticate. | Controlled Firebase Admin fakes assert project id, `check_revoked`, UID validation, `get_user`, and failure mapping. | provider_contract |
| R1, R3 | Credentials are accepted only from Authorization and become a narrow request identity before local lookup. | Tokens in URLs/forms/cookies or raw decoded dict claims become local authority. | Token-only or client-controlled identity bypasses app authorization. | Runtime dependency/API tests and source inventory. | workflow/API |
| R3, R7 | Local PostgreSQL state controls app user id, role, account status, deletion, and admin authority after provider identity. | Valid token or custom claims grant access without active local account/role. | Suspended, deleted, missing, or non-admin users perform protected/admin actions. | PostgreSQL-backed API tests for local states and admin denials. | workflow/API/PostgreSQL |
| R4, R5 | Current provider verification, not stale local snapshots, gates sensitive operations. | Stale `email_verified_at` authorizes joins, checkout, community publish/host-edit, Need-a-Sub, chat sends, or admin access. | Unverified provider accounts perform sensitive actions. | Runtime route-family tests clear stale snapshots, preserve rejected host-edit detail state, and restore missing snapshots from provider truth. | workflow/API/PostgreSQL |
| R5, R6 | Provider-derived snapshots are written only by provider-authenticated sync, and ordinary profile schemas exclude identity-owned fields. | `/users/me` writes `email_verified_at`, role, auth UID, provider email, or admin fields. | Mass assignment recreates the IAM-007/IAM-014 defect. | Schema/API tests for allowed fields, rejected identity fields, disabled generic user mutations, and sync conflict behavior. | workflow/API/schema |
| R8 | Current active routes and source do not introduce WS03-01 identity bypasses. | A new mutation uses only active-user auth, an admin route skips active admin, or source trusts decoded/custom claims. | Example tests pass while a nearby route bypasses the authority model. | Dynamic route inventory and static backend/frontend negative-space checks with explicit exception classifications. | workflow/source |
| R9 | Browser source keeps Firebase as the token store and does not blindly replay mutations. | App code duplicates bearer tokens in storage or generic fetch retries replay payments/bookings/messages/admin actions. | Token exposure or duplicate side effects after refresh. | Frontend source inventory for persistence, bearer headers, storage, URL/form placement, and replay. | workflow/source |
| R11 | Local pytest does not overclaim external provider/runtime closure. | Fake/provider-free evidence is reported as deployed Firebase or browser runtime proof. | Production-readiness status becomes misleading. | Deferred declaration and explicit testing-record limitations. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | anonymous caller, ordinary authenticated user, unverified user, verified user, local admin, non-admin, suspended/deleted/missing local user, provider account | covered/grouped | Identity authority changes by provider state and local role/account state. |
| States / lifecycle | valid/missing/malformed/expired/revoked/wrong-project-style tokens; disabled/deleted/unavailable provider users; active/suspended/pending-deletion/deleted local users; verified/unverified provider email; stale/missing snapshots | covered | These are the material WS03-01 failure modes. |
| Actions | protected reads, profile setup, auth sync, game/join/checkout, community publish/host-edit, Need-a-Sub interactions, private chat sends, admin entry points | covered/grouped | Representative runtime API tests exercise the frozen route-family policy without becoming WS03-04. |
| Inputs / boundaries | Authorization header, query/cookie/body credential attempts, identity-owned profile fields, frontend token placement, Firebase project settings | covered | These are the input boundaries controlled by WS03-01 and IAM-014/IDB-01. |
| Time | stale verified snapshot, missing snapshot restored, provider auth time for recent-auth plumbing | covered for WS03-01 | Snapshot time behavior is local; recent-auth/MFA timing remains later-owner. |
| Dependencies | PostgreSQL, FastAPI dependencies, Firebase Admin SDK boundary, frontend source, settings parser | covered locally | External provider/network calls are faked or deferred. |
| Concurrency / idempotency | duplicate first login, replay, cross-instance propagation | deferred/source-only for replay | Account lifecycle races are WS03-02; generic replay source boundary is R9. |
| Authorization / privacy / security | provider/local split, verified email, admin role, custom/client claims, bearer-token storage | covered | These are core identity authority safeguards. |
| Persistence / rollback | snapshot sync writes, profile writes, auth sync creates/updates, rejected writes with no side effects | covered where material | PostgreSQL-backed tests assert persisted effects or prohibited side effects. |
| Recovery | provider unavailable/config failure, safe public errors, external runtime unknowns | covered/deferred | Local source maps provider failures safely; real provider/runtime recovery is R11. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing Authorization, missing UID, missing local user, missing Firebase config/project | pytest |
| empty | yes | empty bearer token, blank/placeholder project id | pytest/settings |
| corrupt | yes | malformed token, invalid project id syntax, invalid provider credential | pytest/provider/settings |
| exceed | partial | ordinary identity fields outside approved schema | pytest/schema |
| duplicate | partial | sync email conflict with another local user | pytest/PostgreSQL |
| delay | partial | stale local verification timestamp | pytest/PostgreSQL |
| reorder | no | no WS03-01 ordering claim beyond provider-before-local pipeline | not applicable |
| interrupt | no | provider/runtime interruption closure is external | deferred |
| race | no | first-login/account lifecycle race is WS03-02 | deferred |
| expire / revoke | yes | expired/revoked credential mapping and fail-closed behavior | pytest/provider fake |
| tamper | yes | query/cookie/body token placement, custom claims, client role/admin fields | pytest/API/source |
| retry | yes | bounded `/auth/me` safe-read refresh and no generic mutation replay | pytest/source |
| recover | partial | verified provider can restore missing snapshot | pytest/PostgreSQL |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1, R2, R10 | Firebase Admin app initialization, token verification, revocation flag, provider-user lookup, disabled/deleted/unavailable states, safe errors. | provider fake, dependency | `test_firebase_identity_provider_contract.py` | Enough for repository-owned SDK call semantics and local error mapping; not real deployed Firebase proof. |
| R1, R2, R3 | Authorization-header-only request pipeline, request-scoped identity, local UID lookup, local account states, no token-only authority. | API, PostgreSQL, dependency | `test_protected_request_identity_pipeline_contract.py` | Enough for current request-time safeguards; object-level authorization remains WS03-04. |
| R4, R5, R8 | Verified-email route-family policy, community host-edit positive/negative runtime proof, stale snapshot clearing, missing snapshot restoration, and legitimate exceptions. | API, PostgreSQL | `test_verified_email_policy_contract.py` | Enough for representative frozen route families and snapshot semantics; not real Firebase runtime correctness. |
| R5, R6 | `/users/me` allowed fields, rejected identity/server fields, disabled generic user mutations, provider-authenticated sync and conflicts. | API, schema, PostgreSQL | `test_user_identity_field_authority_contract.py` | Enough for identity-specific field ownership; broader request ownership remains WS02-05B1. |
| R7, R8 | Admin access positive and denial matrix, custom/client claims, recent-admin wrapper layering. | API, PostgreSQL, dependency | `test_admin_identity_authority_contract.py` | Enough for base admin identity authority; MFA/recent-auth policy remains WS03-03. |
| R9 | Firebase browser-local persistence, credential flows, bearer-header transport, storage/URL/form negative space, bounded safe-read refresh, no generic replay. | frontend source | `test_frontend_auth_persistence_transport_contract.py` | Enough for source-level IDB-01 boundary; not browser runtime cache isolation. |
| R1, R3, R4, R6, R7, R8, R9 | Dynamic route/source bypass inventory and explicit exception classification. | backend/frontend source, FastAPI route table | `test_identity_authority_negative_space_contract.py` | Enough to catch local WS03-01 bypass drift; intentionally narrower than WS03-04 IDOR/object authorization. |
| R10 | Firebase settings parser, placeholder/syntax checks, project id passed to SDK, no real provider identifiers in example/evidence. | settings/source/provider fake | `test_firebase_project_settings_contract.py` | Enough for repository configuration contracts; not deployed env injection. |
| R11 | Provider/runtime/later-pass boundary. | governance | Requirement JSON and this record | Correctly has no executable pytest mapping. |

### Evidence Quality Checks

- Runtime tests assert actual HTTP status, details, and persisted database state
  where those effects are the safeguard.
- Rejected profile writes prove identity fields did not change.
- Provider fakes sit at the Firebase Admin boundary and use obviously
  synthetic identities, emails, and project ids.
- Route inventories derive candidates from the current registered FastAPI app
  and require explicit classifications for weaker-looking routes.
- Static inventories skip historical tests and do not read, execute, or cite
  `backend/tests/legacy`.
- Frontend source checks avoid whole-file snapshots and do not modify frontend
  source.
- R11 has zero pytest mappings.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Auth sync | Creates or updates local user snapshots from provider-authenticated identity, including email and verification timestamp. | Conflicting local email must not create a second identity row. | Conflict fails safely with no new user for the conflicting UID. |
| Verified-email action with stale local timestamp | Denies the action when provider reports unverified and clears stale `email_verified_at`. | Stale snapshot must not authorize the action. | The stale snapshot is removed as part of the provider-authoritative path. |
| Community host-edit detail update | Verified current provider identity plus matching active local host can update persisted community detail payment snapshots. | Unverified current provider state must deny the host-edit mutation and leave existing community detail snapshots unchanged. | Rejection clears stale verification state and preserves the preexisting detail row. |
| Verified provider with missing local timestamp | Allows verified-authority path and restores `email_verified_at`. | Missing local snapshot must not block current provider-verified authority. | Snapshot is synchronized from provider state. |
| Ordinary profile update | Persists only approved profile fields. | Provider UID, email, verification, role/admin, account status, deletion, profile-photo/provider URL, permissions, ownership, timestamps, and other identity-owned fields must remain unchanged. | Validation failure leaves identity fields unchanged. |
| Admin access | Returns admin identity only for active non-deleted local admin with current verified provider identity. | Custom claims, client role data, missing local user, suspended/deleted local state, and non-admin role must not grant access. | Denials have no local role/account side effect. |
| Frontend source inventory | Confirms current source placement of persistence and token transport. | Must not introduce app-managed bearer-token persistence or generic mutation replay. | Source inspection only; no frontend write occurs. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS03-01-R11` | deferred | Actual provider/runtime/browser/operations facts cannot be proved by local pytest. | Provider/runtime evidence, WS03-03, WS07-02, WS08, WS10 |
| Real Firebase project/dashboard/IAM | deferred | Controlled fakes prove repository call semantics, not deployed provider configuration. | Provider/operations evidence |
| Real token revocation and disabled/deleted provider propagation | deferred | Local fakes cover fail-closed code paths only. | Provider/runtime evidence, WS03-02/WS03-03 as applicable |
| HTTPS/CDN/logging/telemetry/bundle exposure | deferred | Source tests cannot prove deployed transport and observability behavior. | WS08, WS09, WS10/runtime owners |
| MFA, App Check, recent-auth policy closure | covered elsewhere/deferred | WS03-01 proves base identity/admin dependency; step-up policy is later. | WS03-03 |
| Account linking, recovery, deletion lifecycle, first-login races | covered elsewhere/deferred | WS03-01 is identity authority, not lifecycle/concurrency closure. | WS03-02 |
| Object-level authorization, IDOR, resource ownership matrix | covered elsewhere | Negative space stays at identity-authority bypasses. | WS03-04 |
| Browser private-cache clearing, cross-tab/account-switch isolation | covered elsewhere/deferred | WS03-01 owns source persistence/transport/replay only. | WS07-02 |
| Checker/traceability adequacy | manual | Checker PASS is structural compliance only. | Gate C/human review |

## 9. Adequacy Conclusion

This evidence is adequate for WS03-01 Gate B when focused identity-authority
pytest, domain checker, suite checker, generated traceability, full trusted
backend regression, diff integrity, and human review all pass.

Requirements R1 through R10 have executable trusted evidence. R11 is
intentionally deferred/governance with zero pytest mappings. The local evidence
is strong for repository-owned source and request-time safeguards, but it does
not close deployed Firebase, runtime, operations, browser-cache, MFA/App Check,
or later lifecycle/object-authorization obligations. Checker `PASS` remains
machine-compliance evidence only; this record supplies the semantic adequacy
boundary for Gate C review.
