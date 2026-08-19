# WS03-04B Self-Owned Account, Notification, And Financial Authorization Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS03-04B - Self-owned account, notification, and financial record authorization` |
| Trusted test scope | `backend/tests/workflows/self_owned_account_notification_financial_authorization` |
| Requirement declaration | `backend/tests/support/requirements/ws03_04b.json` |
| Authoritative sources | Approved `WS03-04` intake, accepted `WS03-04A` authorization matrix, accepted `WS03-01`, `WS03-02`, `WS03-03A`, and current B-owned source |
| Evidence layers | pytest, FastAPI route-table inspection, PostgreSQL-backed API requests, local Firebase token fakes, local Stripe service fakes, governance boundaries |

## 1. Scope

This record covers the `WS03-04B` local authorization evidence for ordinary
self-owned account, profile, settings, stats, notification, inbox, saved-card,
credit, payment, refund, and host publish fee routes.

It does not cover relationship authorization for games, checkout, bookings,
participants, waitlists, chats/messages, My Games, or Need-a-Sub. It does not
cover final active-admin or high-risk review, deployed runtime behavior, real
Firebase or Stripe provider behavior, provider dashboards, durable payment or
refund reconciliation, genuine database-concurrency closure, export/unmask/read
audit policy, browser evidence, migrations, or production operations.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS03-04B-R1` | B route inventory and matrix dependency alignment remain exactly scoped to 11 families and 28 route keys. | pytest |
| `WS03-04B-R2` | Current-account routes bind reads and mutations to the authenticated local user and do not accept caller-selected target users. | pytest |
| `WS03-04B-R3` | B ordinary behavior preserves authenticated, active, recent-authenticated, and provider-verified-email distinctions. | pytest |
| `WS03-04B-R4` | Notification and inbox routes are current-user scoped, including notification ownership, selected-notice recipient ownership, and global-seen token ownership. | pytest |
| `WS03-04B-R5` | Saved-card routes enforce current-user ownership, provider-customer binding, recent-auth boundaries, and provider-call ordering. | pytest |
| `WS03-04B-R6` | Ordinary-user financial reads for credits, payments, refunds, and host fees cannot be widened through filters or object IDs. | pytest |
| `WS03-04B-R7` | Ordinary users cannot enter active-admin broad-read branches visible in B-adjacent services. | pytest |
| `WS03-04B-R8` | Negative/default-deny proof covers 401, 403, 404, cross-user denial, caller-controlled fields, and rejected-mutation side effects. | pytest |
| `WS03-04B-R9` | Requirement declaration, markers, testing record, and register update remain traceable and scoped. | pytest plus checker |
| `WS03-04B-R10` | Provider/runtime/admin/final-parent and later-owner facts remain outside local pytest closure. | deferred/governance |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R9` | The accepted A matrix and current FastAPI route table agree for every B-owned route key and dependency. | A route is added, removed, re-owned, or dependency-shifted without updating evidence. | B evidence no longer proves the actual source. | Route-table and matrix equality checks. | workflow |
| `R2`, `R4`, `R5`, `R6` | Ordinary users read or mutate only their own self-owned rows. | A caller supplies another user's ID or filter and receives or changes that user's data. | Privacy and authorization breach. | Current-user route dependencies, object-owner checks, and forbidden/concealed denials. | workflow |
| `R3`, `R5`, `R8` | Provider-unverified users are allowed on B ordinary routes, while active-account and recent-auth gates still apply where source requires them. | Verified-email policy is over-applied or missing credential/state gates are weakened. | Users are incorrectly blocked or sensitive actions become too easy. | Provider token fakes with email verification off plus explicit active/recent denial checks. | workflow |
| `R7` | Ordinary users cannot use active-admin broad-read branches visible in B-adjacent services. | Ordinary-user routes accidentally gain admin breadth. | Unauthorized access to broader notification or financial records. | Current-user route dependency checks and ordinary-user forbidden assertions. | workflow |
| `R4`, `R5`, `R8` | Rejected writes do not change protected state or call provider mutation fakes after local authorization should deny. | A blocked request still updates a row, defaults/detaches a card, marks a notification read, or writes a seen state. | Unauthorized side effects and misleading evidence. | DB state assertions and local provider fake call assertions after rejection. | workflow |
| `R10` | Local evidence does not claim deployed, provider-dashboard, runtime, admin-final, relationship, or concurrency closure. | Local tests are reported as stronger evidence than they are. | Production-readiness record becomes inaccurate. | Deferred requirement and explicit record boundaries. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | anonymous, invalid token, current ordinary user, suspended user, other ordinary user, active-admin branch | covered/grouped | These actor classes cover the B dependency and service-denial shapes without duplicating every equivalent route. |
| States / lifecycle | active, suspended, stale recent-auth, fresh recent-auth, unread/read notification, selected notice recipient/non-recipient, active saved card | covered/grouped | These states map to the B authorization and side-effect boundaries. |
| Actions | current-user read, profile/settings update, self-delete, notification read, inbox seen/read, saved-card list/get/setup/sync/default/detach, financial list/object read | covered/grouped | The selected actions represent all B-owned route families. |
| Inputs / boundaries | missing auth, invalid token, forbidden fields, wrong user token, wrong card ID, wrong Stripe customer, other-user filters | covered | These are the material B authorization and mass-assignment boundaries. |
| Time | stale provider auth time, recent provider auth time, published platform notice | covered/grouped | Recent-auth and visible notice state are time-dependent in B. |
| Dependencies | PostgreSQL, current FastAPI route table, Firebase token verifier fake, Stripe service fake | covered | Fakes are installed at the application-owned boundary and no provider network is called. |
| Concurrency / idempotency | selected notice read idempotency, saved-card detach current-state checks | covered/deferred | Serial local idempotency is covered; genuine database-concurrency proof remains outside B. |
| Authorization / privacy / security | 401, 403, 404, current-user scoping, admin branch denial, verified-email non-requirement | covered | These are the core B authorization risks. |
| Persistence / rollback | accepted mutations persist expected rows; rejected mutations leave protected rows unchanged | covered | DB assertions verify meaningful effects and prohibited effects. |
| Recovery | provider timeout/dashboard/reconciliation recovery | deferred | These require later provider/runtime or durable-worker evidence, not B local pytest. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | Missing authorization header. | API returns 401. |
| empty | yes | Empty/invalid confirmation and forbidden extra fields. | API rejects and state remains unchanged. |
| corrupt | yes | Invalid token and wrong-user inbox seen token. | API returns 401 or 400 with no protected state change. |
| exceed | no | Size limits are owned by earlier request-boundary passes. | Covered elsewhere. |
| duplicate | yes | Repeated selected platform notice read. | Idempotent local read state remains single-row. |
| delay | yes | Stale recent-auth token on high-risk routes. | API returns 403 before provider/delete side effects. |
| reorder | no | Not material to this local authorization scope. | Not applicable. |
| interrupt | no | Provider interruption and partial recovery are later-owned. | Deferred. |
| race | no | Genuine concurrent database behavior is later-owned. | Deferred to `WS04`. |
| expire / revoke | yes | Invalid or expired token class. | API returns 401. |
| tamper | yes | Wrong owner IDs, wrong customer, wrong seen token. | API denies with 400/403/404 and no prohibited side effect. |
| retry | yes | Repeated selected notice read and repeated own-card detach. | Idempotent result. |
| recover | no | Runtime/provider recovery is outside B. | Deferred. |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1`, `R3`, `R9` | Matrix and route drift guard | route-table inspection and pytest | `test_self_owned_account_notification_financial_authorization_contract.py` | Compares the accepted matrix to the current FastAPI app route table and dependency identities for all B-owned routes. |
| `R2`, `R3`, `R8` | Current-user account/profile/settings/stats routes and field boundaries | API and PostgreSQL | same test file | Proves unverified provider users are accepted on representative B ordinary routes and forbidden fields are rejected without protected state changes. |
| `R3`, `R5`, `R8` | Credential, active-account, and recent-auth denials | API, PostgreSQL, Firebase fake, Stripe fake | same test file | Proves 401/403 classes and no delete/default provider side effects before authorization succeeds. |
| `R2`, `R3`, `R8` | Self-delete confirmation and fresh recent-auth behavior | API, PostgreSQL, Firebase fake | same test file | Proves invalid confirmation is rejected and valid self-delete acts on the token user's local account while leaving another user untouched. |
| `R4`, `R8` | Notifications and inbox | API and PostgreSQL | same test file | Proves current-user notification lists, app-update feed/counts, game-activity feed, valid and wrong-user global-seen tokens, concealed wrong-owner objects, selected-notice recipient ownership, and read idempotency. |
| `R3`, `R5`, `R8` | Saved cards | API, PostgreSQL, Stripe fake | same test file | Proves current-user card scoping, recent-auth defaulting and own-card detach/idempotency, wrong-owner denials before provider calls, forbidden request fields, and wrong-customer sync rejection. |
| `R6`, `R7`, `R8` | Credits, payments, refunds, host fees, and admin branch denial | API and PostgreSQL | same test file | Proves ordinary list/default-balance/object reads stay current-user scoped and other-user/admin-only paths deny or do not widen results. |
| `R10` | Later provider/runtime/admin/concurrency facts | governance | requirement JSON and this testing record | Correctly deferred with zero pytest mapping; local evidence is not enough for these facts. |

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Profile/settings update | Current user's allowed fields update. | Other user, role, account status, email, photo URL, settings owner, and timestamps are not caller-writable through B routes. | Rejected request leaves protected fields unchanged. |
| Self-delete | Token user's account is unlinked and marked deleted after recent-auth and confirmation. | Stale-auth or invalid-confirmation requests do not call the Firebase deletion fake and do not stage deletion. | Failed local authorization has no account mutation. |
| Notification and inbox read state | Current user's app/game feeds and counts are scoped to their rows; valid current-user global-seen tokens update only that user's seen state; current user's notification/selected notice can be marked read. | Other user's notification or selected notice is concealed and remains unread; wrong-user seen token does not update either seen state. | Repeated selected notice read remains one persisted read row. |
| Saved card default/sync/detach | Current user's own active card can become default and detach with recent auth. | Wrong-owner card IDs do not call provider fakes; wrong-customer sync creates no local card; forbidden fields are rejected. | Rejected requests leave local card rows unchanged; repeated own-card detach returns detached state without a second detach call. |
| Financial reads | Current user's own credit list, credit balance, payment, refund, and host-fee rows are returned. | Other-user filters and object IDs do not expose or widen ordinary access. | Read-only scope has no mutation. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| Relationship authorization for games, checkout, bookings, participants, waitlists, chats/messages, My Games, and Need-a-Sub | deferred | Not B-owned under the approved WS03-04 decomposition. | `WS03-04C` |
| Final active-admin/high-risk route review and parent-gap disposition | deferred | B only proves ordinary users cannot enter the visible admin branches. | `WS03-04D` |
| Live Firebase, live Stripe, deployed runtime, provider dashboard, and production evidence | deferred | B uses local fakes and repository source only. | `WS05`, `WS09`, `WS10`, and release/runtime evidence |
| Durable payment/refund reconciliation and webhook lifecycle closure | deferred | Local B reads do not prove provider lifecycle or durable jobs. | `WS05` |
| Genuine database-concurrency behavior | deferred | B serial tests prove local authorization effects, not races. | `WS04` |
| Export, unmask, read-audit, and sensitive-access policy closure | deferred | Outside B self-owned ordinary route proof. | `WS03-04D`, `WS09`, `WS10` |

## 9. Adequacy Conclusion

The selected evidence is adequate for `WS03-04B` when the focused pytest scope,
affected compatibility scopes, checker domain/suite validation, and diff/scope
checks pass. `WS03-04B-R1` through `WS03-04B-R9` have executable local evidence.
`WS03-04B-R10` is deliberately deferred/governance and has no pytest mapping.

Checker `PASS` is structural compliance only. Human adequacy still depends on
reviewing this record, the requirement declaration, the focused test behavior,
and the execution-register update against the approved Gate A plan.
