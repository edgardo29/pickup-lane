# WS03-03A Recent Authentication And Step-Up Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS03-03A` |
| Trusted test scope | `backend/tests/workflows/recent_auth_step_up` |
| Requirement declaration | `backend/tests/support/requirements/ws03_03a.json` |
| Authoritative sources | Frozen WS03-03A canonical plan; current accepted repository truth; `IAM-008`; `IAM-003`; `IAM-010`; `IAM-011`; `IAM-017`; `PAY-011`; `ADM-013`; `FE-M04`; approved decisions `IDB-01` through `IDB-04`; accepted WS03-01, WS03-02, and EN-03 boundaries |
| Evidence layers | pytest; FastAPI route/dependency inventory; controlled provider-token fakes; controlled time at service boundary; runtime API error envelope; backend/frontend source and AST inspection; existing frontend unit tests as corroboration only; governance deferral for R12-R14 |

## 1. Scope

This record covers trusted WS03-03A repository evidence for source-owned recent
authentication and step-up: Firebase provider `auth_time` authority,
five-minute inclusive freshness evaluation approved at Gate A, safe public
recent-auth denial, dependency layering over accepted WS03-01/WS03-02 identity
and lifecycle authority, the corrected 25-route high-risk matrix, the complete
107-route admin-access mutation partition, frontend password and Google
reauthentication, caller-owned retry, the add-password credential-linking
boundary, and negative-space review for freshness, policy, route, caller, and
provider/governance overclaim bypasses.

This record does not claim live Firebase provider behavior, deployed
`auth_time` behavior, administrator MFA enrollment/enforcement, App Check
registration or runtime behavior, Firebase/GCP service-account governance,
provider IAM, deployment, production runtime, browser cache/account-switch
isolation, complete object-level authorization, durable provider repair
workers, or broader operational closure. Those remain provider/runtime/
governance or later-pass work.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS03-03A-R1` | Provider `auth_time` is the only recent-auth authority. | pytest |
| `WS03-03A-R2` | The five-minute threshold and exact boundary semantics are centralized and tested. | pytest |
| `WS03-03A-R3` | Recent-auth denial uses a stable safe public error contract. | pytest |
| `WS03-03A-R4` | Recent-auth wrappers layer on accepted identity and account authority. | pytest |
| `WS03-03A-R5` | The approved 25-route high-risk route matrix is enforced. | pytest |
| `WS03-03A-R6` | Intentionally ungated and retired/non-executing routes are classified and preserved. | pytest |
| `WS03-03A-R7` | Frontend email/password and Google step-up use Firebase reauthentication safely. | pytest |
| `WS03-03A-R8` | Step-up retry is caller-owned and not a blind global replay. | pytest |
| `WS03-03A-R9` | Credential linking requires step-up and remains provider-owned. | pytest |
| `WS03-03A-R10` | Freshness is not persisted or mirrored as app authority. | pytest |
| `WS03-03A-R11` | Negative-space evidence fails closed for bypasses and overclaims. | pytest |
| `WS03-03A-R12` | Administrator MFA remains deferred provider/governance evidence. | deferred / zero pytest mappings |
| `WS03-03A-R13` | Firebase App Check remains deferred provider/runtime evidence. | deferred / zero pytest mappings |
| `WS03-03A-R14` | Firebase/GCP credential governance remains deferred provider/operations evidence. | deferred / zero pytest mappings |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| R1, R2, R10 | Only provider `auth_time` parsed into request identity can satisfy the current five-minute freshness window. | Token issue time, app timestamps, stale provider values, browser state, or persisted values satisfy recent-auth. | Stale sessions can perform high-risk account/admin/money/card actions. | `auth_time` parser, controlled freshness evaluator, central settings window, no persisted freshness owner. | workflow/service/source |
| R3 | Stale or missing recent-auth returns the stable safe public 403 contract. | A different status/code hides step-up from the frontend, or raw provider details leak. | Broken recovery UX or sensitive data exposure. | Existing public error normalizer and recent-auth detail dictionary. | workflow/API/platform error envelope |
| R4, R5 | Recent-auth dependencies add one prerequisite while preserving base identity/account/admin checks. | Step-up replaces local account state, verified-email, admin role, final-admin, idempotency, state-token, preview-token, audit, payment, or workflow safeguards. | Recent-auth creates a weaker or confusing authorization path. | Wrapper dependency signatures, route-level dependency inventory, and source review of workflow safeguards. | workflow/dependency/source |
| R5, R6, R11 | The protected policy has exactly 25 current route keys; admin-access mutations partition exactly into 22 recent, 38 intentionally non-recent, and 47 retired/non-executing routes. | A new admin mutation appears unclassified, a terminal action is hidden by a broad family exception, a protected route uses ordinary admin auth, or a stale policy entry points at a removed route. | Point tests pass while a real high-risk mutation bypasses step-up. | Dynamic FastAPI route inventory, frozen/current policy comparison, and explicit route/action classifications. | workflow/source/static |
| R7 | Frontend step-up uses Firebase email/password or Google provider reauthentication and fails closed. | Passwords or popup tokens go to Pickup Lane APIs, token refresh happens without reauth, or failed/cancelled reauth retries. | Credential exposure or stale-session mutation. | Provider reauth helpers, modal state, cancellation rejection, forced normal ID-token refresh after success. | workflow/frontend source |
| R8 | Retry remains caller-owned and low-level transport never blindly replays mutations. | API client catches recent-auth globally and repeats payments, bookings, messages, cancellations, or admin actions. | Duplicate or unsafe side effects after reauth. | `runWithStepUp` used by deliberate high-risk callers only. | workflow/frontend source |
| R9 | Add-password linking requires step-up and stays on the current Firebase user. | New password is sent to backend or local source relinks another UID/email. | Account takeover or WS03-02 identity-lifecycle bypass. | Explicit `confirmStepUp` before Firebase `linkWithCredential` and no local relink route. | workflow/frontend/backend source |
| R12-R14 | Local pytest does not falsely close provider/governance facts. | Fake/source evidence is reported as live MFA, App Check, provider IAM, key inventory, or production proof. | Misleading production-readiness status. | Deferred declarations, zero pytest mappings, and explicit gaps. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | current user, active user, active verified admin, stale-session user/admin, frontend password user, frontend Google user | covered/grouped | These actors materially change recent-auth and step-up behavior. |
| States / lifecycle | missing, malformed, boolean, non-finite, negative, overflow, naive, future, stale, current, just-inside, exact-boundary, just-outside `auth_time`; active/suspended/deleted/local admin inherited states | covered/covered elsewhere | R1/R2 own auth-time states; WS03-01/WS03-02 own base identity/lifecycle states that wrappers must preserve. |
| Actions | self-delete; saved-card default/detach; admin role/delete/suspend/unsuspend/hosting restrict/hosting restore; money issue/refund/credit/outcome; payment-event repair; official-game cancellation and paid-player removal; community-game cancellation; Need-a-Sub removal; game/venue soft-delete; platform notice create/cancel; add-password linking | covered | These are the current high-risk or credential-linking actions in the frozen matrix. |
| Intentionally non-recent actions | reversible community and Need-a-Sub moderation, previews, official create/edit/host/player-add/chat, review/support case work, venue-image lifecycle, generic admin game create/edit, community detail create/edit | covered/classified | These routes remain ordinary by frozen policy and are explicitly checked for no recent-auth wrapper. |
| Retired/non-executing actions | 410 scaffolds, disabled generic user mutations, direct retired official host/player deletes, retired duplicate Need-a-Sub removal, retired payment-event creation | covered/classified | These routes remain registered but non-executing and must not be revived or recent-auth-gated as active workflows. |
| Inputs / boundaries | verified token claims, `iat`, frontend/browser/local timestamps, request body freshness, public error detail, password input, popup result, provider credential | covered | These inputs can become unsafe alternate freshness or credential paths. |
| Time | exact now, just inside five minutes, exactly five minutes, after five minutes, future time, timezone normalization | covered | Exact boundary semantics are central to R2 and use one deterministic baseline. |
| Dependencies | PostgreSQL local users, FastAPI dependency graph, Firebase client/Admin boundaries, settings owner, frontend source | covered/deferred | Local source/fakes are executable; live provider runtime remains deferred. |
| Concurrency / idempotency | blind retry/replay, idempotency/state-token/preview-token preservation, duplicate action after failed step-up | covered/grouped | R8 checks no blind global replay; underlying idempotency/state safeguards stay with owning workflows. |
| Authorization / privacy / security | recent-auth route bypass, base dependency replacement, error disclosure, password/token forwarding, app-owned freshness | covered | These are the WS03-03A security risks. |
| Persistence / rollback | prohibited persisted freshness, rejected recent-auth before protected-route side effects | covered | Source inspection proves no freshness state; real community-cancel and Need-a-Sub remove route probes reject before service sentinels execute. |
| Recovery | frontend retry only after successful step-up; failed/cancelled step-up fails closed | covered/deferred | Source proves local retry behavior; browser/provider runtime remains deferred. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | missing `auth_time`, missing route classification, missing policy entry, missing frontend caller step-up | pytest/source |
| empty | partial | empty password fails before Firebase reauth | pytest/source |
| corrupt | yes | malformed, boolean, non-finite, overflow `auth_time`; unsafe source patterns | pytest/source |
| exceed | yes | age greater than five minutes | pytest |
| duplicate | yes | duplicate recent-auth policy/window owners and generic replay paths | pytest/source |
| delay | yes | stale provider authentication time | pytest |
| reorder | partial | token `iat` fresh while `auth_time` stale/missing | pytest |
| interrupt | yes | reauthentication failure/cancel before retry | pytest/source |
| race | no | no new database race is approved; underlying workflow races remain with owning passes | not applicable |
| expire / revoke | partial | stale auth-time is covered; provider revocation runtime remains later owner | pytest/deferred |
| tamper | yes | request/client timestamp, boolean, purpose flag, browser storage freshness | pytest/source |
| retry | yes | caller-owned retry after step-up and no global mutation replay | pytest/source |
| recover | partial | frontend source recovers only by caller-owned reauth; provider/runtime recovery remains deferred | pytest/deferred |

### Controlled-Time Boundary Matrix

| Case | Age From Controlled Baseline | Expected |
|---|---|---|
| exactly current time | `0 seconds` | accepted |
| just inside boundary | `5 minutes - 1 second` | accepted |
| exactly at boundary | `5 minutes` | accepted |
| just outside boundary | `5 minutes + 1 second` | rejected |
| future provider time | negative age | rejected |
| missing or malformed provider time | no valid age | rejected |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| R1, R2, R10 | Provider `auth_time` parsing, no `iat` fallback, exact five-minute boundaries, timezone-aware evaluation, central settings owner, request-scoped identity. | service/source/static | `test_provider_auth_time_contract.py` | Enough for local source-owned freshness authority; not live Firebase proof. |
| R3, R4, R5 | Public 403 envelope, recent-app-user/recent-active-user/recent-active-admin dependency layering, controlled synthetic dependency probe, real community-cancel stale/missing/fresh route proof, real Need-a-Sub removal stale/missing/fresh route proof. | API/dependency/source | `test_recent_auth_dependency_contract.py` | Enough for current dependency graph, normalized error contract, and selected real route boundaries; other newly protected routes use compositional route-wrapper proof. |
| R5, R6, R11 | Current route-policy reconciliation, protected wrapper enforcement, 25-route policy equality, 107-route admin partition equality, no classification overlap, stale policy detection, and representative intentionally non-recent preservation. | FastAPI route table/source/static | `test_recent_auth_route_inventory_contract.py` | Enough for the frozen source-owned matrix; new admin mutations must be classified or fail closed. |
| R7, R8, R9 | Frontend Firebase reauth methods, forced token refresh after success, cancellation/failure closed path, caller-owned retry, all high-risk frontend callers, idempotency/preview-token preservation, independent financial-outcome step-up, add-password linking boundary, and no current caller for backend-only protected routes. | frontend source/static | `test_frontend_step_up_contract.py` | Enough for repository source; not browser/provider runtime. |
| R1, R5, R6, R8, R10, R11 | Negative-space inventory for alternate freshness authority, duplicate owners, replay, credential forwarding, unsafe helpers, persisted/response-exposed `auth_time`, admin partition drift, retired route revival, terminal action family misclassification, and deferred pytest mappings. | backend/frontend/trusted-test source and AST inspection | `test_recent_auth_negative_space_contract.py` | Fails closed for local bypasses and false closure; intentionally narrower than WS03-04/WS07/WS10. |
| R12-R14 | MFA, App Check, and credential-governance deferrals. | governance | Requirement declaration and this record | Correctly unmapped to pytest. |

### 25-Route Protected Matrix

| Route | Caller / status |
|---|---|
| `DELETE /auth/account` | `useDeleteAccountSettings` |
| `PATCH /admin/users/{user_id}/role` | `AdminUserDetailPage` role action |
| `POST /admin/users/{user_id}/delete` | `AdminUserDeletePreviewModal` |
| `POST /admin/users/{user_id}/restrict-hosting` | `AdminUserHostingRestrictionModal` |
| `POST /admin/users/{user_id}/restore-hosting` | `AdminUserHostingRestorationModal` |
| `POST /admin/users/{user_id}/suspend` | `AdminUserSuspensionModal` |
| `POST /admin/users/{user_id}/unsuspend` | `AdminUserUnsuspensionModal` |
| `POST /admin/money/financial-outcomes` | `adminFinancialOutcomeApi` |
| `POST /admin/money/issues/{money_issue_id}/resolve` | `AdminMoneyIssuePage` |
| `POST /admin/money/issues/{money_issue_id}/retry-credit` | `AdminMoneyIssuePage` |
| `POST /admin/money/refunds/{refund_id}/retry` | `AdminMoneyIssuePage` / `AdminMoneyRefundPage` |
| `POST /admin/money/refunds/{refund_id}/reconcile` | `AdminMoneyRefundPage` |
| `PATCH /payment-events/{payment_event_id}` | no current frontend caller |
| `POST /admin/game-credits/issue` | admin money credit workflows |
| `POST /admin/game-credits/{game_credit_id}/reverse` | admin money credit workflows |
| `POST /admin/official-games/{game_id}/cancel` | `AdminOfficialGamePage` |
| `POST /admin/official-games/{game_id}/participants/{participant_id}/remove` | `AdminOfficialGamePage` |
| `POST /admin/community-games/{game_id}/cancel` | `AdminCommunityGameActionModal` |
| `POST /admin/need-a-sub/{post_id}/remove` | `AdminNeedASubRemovalModal` |
| `DELETE /games/{game_id}` | no current frontend caller |
| `DELETE /venues/{venue_id}` | no current frontend caller |
| `POST /admin/platform-notices` | `AdminPlatformNoticesPage` |
| `POST /admin/platform-notices/{notice_id}/cancel` | `AdminPlatformNoticesPage` |
| `PATCH /user-payment-methods/{payment_method_id}/default` | `PaymentMethodsPage` |
| `DELETE /user-payment-methods/{payment_method_id}` | `PaymentMethodsPage` |

### Complete Admin Mutation Partition

The executable route inventory compares exact sets, not only counts:

- `RECENT_AUTH_REQUIRED`: 22 admin-access routes in the matrix above.
- `RECENT_AUTH_NOT_REQUIRED`: 38 executing admin-access routes intentionally
  left ordinary.
- `RETIRED_OR_NON_EXECUTING_MUTATION`: 47 registered admin-access mutations
  that are tombstones or disabled generic user mutations.

`RECENT_AUTH_NOT_REQUIRED` contains:

`PATCH /admin/official-games/{game_id}`;
`PATCH /admin/venue-images/{venue_image_id}`;
`PATCH /community-game-details/{community_game_detail_id}`;
`POST /admin/community-games/{game_id}/chat/messages/{message_id}/remove`;
`POST /admin/community-games/{game_id}/chat/messages/{message_id}/restore`;
`POST /admin/community-games/{game_id}/chat/messages/{message_id}/review`;
`POST /admin/community-games/{game_id}/flag-for-review`;
`POST /admin/community-games/{game_id}/hide`;
`POST /admin/community-games/{game_id}/hide-payment-text`;
`POST /admin/community-games/{game_id}/pause-joining`;
`POST /admin/community-games/{game_id}/restore`;
`POST /admin/community-games/{game_id}/restore-payment-text`;
`POST /admin/community-games/{game_id}/resume-joining`;
`POST /admin/need-a-sub/{post_id}/chat/messages/{message_id}/remove`;
`POST /admin/need-a-sub/{post_id}/chat/messages/{message_id}/restore`;
`POST /admin/need-a-sub/{post_id}/chat/messages/{message_id}/review`;
`POST /admin/need-a-sub/{post_id}/hide`;
`POST /admin/need-a-sub/{post_id}/restore`;
`POST /admin/official-games`;
`POST /admin/official-games/{game_id}/cancel-preview`;
`POST /admin/official-games/{game_id}/chat/messages/{message_id}/remove`;
`POST /admin/official-games/{game_id}/chat/messages/{message_id}/restore`;
`POST /admin/official-games/{game_id}/chat/messages/{message_id}/review`;
`POST /admin/official-games/{game_id}/host`;
`POST /admin/official-games/{game_id}/host/remove`;
`POST /admin/official-games/{game_id}/participants/{participant_id}/remove-preview`;
`POST /admin/official-games/{game_id}/players`;
`POST /admin/review-cases/{review_case_id}/close`;
`POST /admin/review-cases/{review_case_id}/notes`;
`POST /admin/support-flags/{support_flag_id}/resolve`;
`POST /admin/users/{user_id}/delete-preview`;
`POST /admin/users/{user_id}/hosting-restriction-preview`;
`POST /admin/users/{user_id}/suspension-preview`;
`POST /admin/venue-images/{venue_image_id}/complete`;
`POST /admin/venues/{venue_id}/images/upload-url`;
`POST /community-game-details`;
`POST /games`;
`PATCH /games/{game_id}`.

`RETIRED_OR_NON_EXECUTING_MUTATION` contains:

`DELETE /admin/official-games/{game_id}/host`;
`DELETE /admin/official-games/{game_id}/participants/{participant_id}`;
`DELETE /users/{user_id}`;
`PATCH /booking-policy-acceptances/{booking_policy_acceptance_id}`;
`PATCH /booking-status-history/{history_id}`;
`PATCH /bookings/{booking_id}`;
`PATCH /game-chats/{game_chat_id}`;
`PATCH /game-images/{game_image_id}`;
`PATCH /game-participants/{participant_id}`;
`PATCH /game-status-history/{history_id}`;
`PATCH /host-publish-fees/{host_publish_fee_id}`;
`PATCH /need-a-sub/posts/{sub_post_id}/remove`;
`PATCH /notifications/{notification_id}`;
`PATCH /participant-status-history/{history_id}`;
`PATCH /payments/{payment_id}`;
`PATCH /policy-acceptances/{policy_acceptance_id}`;
`PATCH /policy-documents/{policy_document_id}`;
`PATCH /refunds/{refund_id}`;
`PATCH /user-settings/{user_id}`;
`PATCH /user-stats/{user_id}`;
`PATCH /users/{user_id}`;
`PATCH /venue-approval-requests/{venue_approval_request_id}`;
`PATCH /venues/{venue_id}`;
`PATCH /waitlist-entries/{waitlist_entry_id}`;
`POST /admin/actions`;
`POST /admin/actions/{admin_action_id}/notes`;
`POST /booking-policy-acceptances`;
`POST /booking-status-history`;
`POST /bookings`;
`POST /game-chats`;
`POST /game-images`;
`POST /game-participants`;
`POST /game-status-history`;
`POST /host-publish-fees`;
`POST /notifications`;
`POST /participant-status-history`;
`POST /payment-events`;
`POST /payments`;
`POST /policy-acceptances`;
`POST /policy-documents`;
`POST /refunds`;
`POST /user-settings`;
`POST /user-stats`;
`POST /users`;
`POST /venue-approval-requests`;
`POST /venues`;
`POST /waitlist-entries`.

This set includes retired official direct host/player deletes, disabled
generic user mutations, retired generic scaffolds, retired duplicate
Need-a-Sub removal, and retired provider-event creation. The negative-space
test proves these routes still call a tombstone or disabled generic mutation
helper instead of executing a business workflow.

Official-player add remains intentionally non-recent because current service
behavior creates an admin-added confirmed booking with payment waived and no
provider payment object, records the admin action, and remains a reversible
roster operation. Official-player removal remains recent-auth protected because
it can cancel bookings, alter payment/credit/refund outcomes, advance waitlist
state, notify users, and create money issues.

### Evidence Quality Checks

- Exact boundary tests use one controlled timezone-aware UTC baseline.
- Runtime error evidence uses a controlled synthetic probe only for generic
  dependency/error-envelope proof.
- Community-game cancellation and Need-a-Sub removal have real route sentinel
  proof for stale/missing rejection and fresh reachability.
- Other newly protected routes use the approved compositional proof model:
  generic recent-auth dependency behavior is runtime-proven, and dynamic route
  inventory proves the exact registered route consumes
  `require_recent_active_admin`.
- Static inventories inspect active backend/frontend source only and exclude
  generated/dependency output.
- Frontend source checks use targeted contract snippets and call-order checks,
  not whole-file snapshots.
- Existing frontend unit tests are corroborating validation only and do not
  define WS03-03A requirements.
- R12, R13, and R14 have zero pytest mappings.

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Recent-auth evaluation | Request-scoped identity with provider `authenticated_at` may satisfy current request only. | No database, schema, request field, browser storage, cookie/cache, telemetry label, or test helper becomes freshness authority. | Not applicable; source inspection verifies no new persisted state. |
| Synthetic stale/missing recent-auth probe | No successful endpoint body execution is expected. | Probe endpoint body must not run; public response must not expose token, `auth_time`, password, popup, provider token, credential, exception, stack, or internal detail. | Dependency denial verifies the generic public error envelope without claiming production endpoint proof. |
| Stale/missing community cancellation | No successful mutation is expected. | `admin_cancel_community_game` must not execute, so no cancellation workflow, audit action, host/user notice, payment/credit cancellation handling, or lifecycle side effect can occur from the rejected request. | Denial ends the request before terminal cancellation workflow. |
| Fresh community cancellation | The request may reach the route workflow or route-level service sentinel. | The proof must not bypass recent-auth or retest the full cancellation business workflow. | Fresh provider `auth_time` satisfies the route-level prerequisite. |
| Stale/missing Need-a-Sub removal | No successful mutation is expected. | `remove_need_a_sub_post_by_admin` must not execute, so no post removal, audit action, notices, request closure, chat closure, or status-history side effect can occur from the rejected request. | Denial ends the request before terminal removal workflow. |
| Fresh Need-a-Sub removal | The request may reach the route workflow or route-level service sentinel. | The proof must not bypass recent-auth or retest the full removal business workflow. | Fresh provider `auth_time` satisfies the route-level prerequisite. |
| High-risk route registration | Protected routes use expected recent-auth wrappers and underlying workflow guards stay with their owners. | Policy entry must not be stale; unclassified high-risk candidate must not pass silently. | New high-risk routes require classification or Gate A correction. |
| Frontend step-up callers | Successful reauth refreshes the normal Firebase ID token and then the caller-owned action may retry. | Failed/cancelled reauth must not retry; previews/reversible actions must not be newly gated; password/provider result must not go to backend or storage. | Caller-owned retry preserves idempotency keys, preview tokens, selected outcome/reason, and existing stale-preview refresh behavior. |
| Publish-fee financial-outcome step-up after community cancellation | Financial outcome remains a separate operation after cancellation succeeds. | A financial-outcome step-up or failure must not replay an already-successful cancellation. | Separate `runWithStepUp` boundary preserves existing partial-success behavior. |
| Add-password linking | Step-up occurs before Firebase `linkWithCredential` on the current user. | No local UID merge/relink/email takeover route is introduced. | WS03-02 stable UID behavior remains the account lifecycle authority. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS03-03A-R12` administrator MFA | deferred | Local pytest cannot prove provider MFA capability, enrollment, enforcement, break-glass, limitation proof, or access review. | WS03-03B / WS10 / provider-governance evidence |
| `WS03-03A-R13` Firebase App Check | deferred | Local source tests cannot prove App Check registration, valid/missing/invalid runtime behavior, provider-unavailable behavior, staged enforcement, rollback, or production enforcement. | WS03-03B / WS10 / provider-runtime evidence |
| `WS03-03A-R14` Firebase/GCP credential governance | deferred | Local pytest cannot prove service-account role assignments, key inventory, storage, rotation, revocation, monitoring, workload identity, permanent hosting, or provider IAM. | EN-03 / WS03-03B / WS10 |
| Live Firebase reauthentication and deployed provider `auth_time` | deferred | Source/fakes prove Pickup Lane calls and local semantics only. | Provider/runtime evidence |
| Browser cache, logout, cross-tab, account-switch runtime isolation | covered elsewhere/deferred | WS03-03A proves caller-owned source boundaries, not full browser runtime state isolation. | WS07-02 |
| Complete object-level authorization and IDOR matrix | covered elsewhere | Recent-auth route inventory does not replace target ownership/action permission proof. | WS03-04 |
| Durable financial/provider reconciliation after uncertain outcomes | covered elsewhere/deferred | Recent-auth protects entry to current repair actions but does not prove provider repair workers. | WS05 |
| Playwright/browser runtime | not applicable | Frozen plan selected frontend source/unit corroboration, not browser runtime, for this pass. | Future owner if approved |
| Checker/generated traceability adequacy | manual | Checker PASS is structural compliance only. | Gate C/human review |

## 9. Adequacy Conclusion

This evidence is adequate for WS03-03A Gate B when the required focused
backend scopes, frontend unit/lint/build validation, domain checker, suite
checker, generated traceability, full trusted backend regression, diff
integrity, and human review all pass.

Requirements R1 through R11 have executable trusted evidence. Requirements R12
through R14 are intentionally deferred/governance with zero pytest mappings.
The local evidence is strong for current repository source, route registration,
dependency layering, frontend caller-owned step-up source, and no app-owned
freshness authority. It does not close live Firebase behavior, administrator
MFA, App Check, Firebase/GCP credential governance, provider runtime,
deployment, browser-cache isolation, WS03-04 object authorization, or WS10
operations. Checker `PASS` remains machine-compliance evidence only; this
record supplies the semantic adequacy boundary for Gate C review.
