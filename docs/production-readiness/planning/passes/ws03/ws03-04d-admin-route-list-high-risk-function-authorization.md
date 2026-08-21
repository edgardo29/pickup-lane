# WS03-04D - Admin Route, List, And High-Risk Function Authorization

## 1. Overview

| Field | Value |
|---|---|
| Pass | `WS03-04D - Admin route, list, and high-risk function authorization` |
| Parent pass | `WS03-04 - Complete authorization matrix and negative proof` |
| Execution mode | First-time implementation, final executable child |
| Track | `WS03` |
| Primary controls | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017` |
| Authority basis | Approved `WS03-04` intake, accepted A/B/C evidence, accepted authorization matrix, current backend source, master blueprint, and final remediation plan |
| Dependencies | Accepted `WS03-04A`, `WS03-04B`, and `WS03-04C` |
| Intake record | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` |
| Canonical plan path | `docs/production-readiness/planning/passes/ws03/ws03-04d-admin-route-list-high-risk-function-authorization.md` |
| Requirement declaration | `backend/tests/support/requirements/ws03_04d.json` |
| Trusted evidence scope | `backend/tests/workflows/admin_route_list_high_risk_function_authorization` |

`WS03-04D` is the final child in the approved authorization decomposition:

```text
WS03-04A -> {WS03-04B, WS03-04C} -> WS03-04D
```

`WS03-04A` owns the authorization matrix foundation and drift guard.
`WS03-04B` owns self-owned account, notification, inbox, saved-card, game
credit, payment, refund, and host-fee authorization. `WS03-04C` owns ordinary
game, community-game, roster, chat, My Games, and Need-a-Sub relationship
authorization. `WS03-04D` owns the remaining admin route, privileged read/list,
high-risk function, retired admin-surface, and final `WS03-04` accounting
responsibilities. It does not reopen accepted A/B/C scope.

The accepted authorization matrix assigns D `40` route families and `187` route
keys. Every D route is behind the active-admin dependency chain. The matrix
marks `22` D route keys as recent-admin high-risk actions and `45` D route keys
as retired routes that currently return `410`.

No production source edit is planned. This plan defines the proof required for
the current source behavior. Completion depends on satisfying the criteria in
Section 9.

## 2. Purpose

Admin routes can inspect broad private data and mutate privileged account,
game, roster, moderation, notice, support, and financial state. This pass
requires trusted evidence that only the current verified active admin user can
reach those routes, that current high-risk actions keep recent-admin
authentication where the source requires it, and that rejected privileged
requests leave named protected state unchanged.

D also records the final `WS03-04` accounting that is evaluated by the
completion criteria in Section 9.

## 3. Scope

### Included

This pass owns:

- route ownership, route drift protection, shared active-admin access, and
  recent-admin classification for the current D-owned route table;
- user, account, role, hosting, and current-admin administration;
- games, rosters, venues, images, Need-a-Sub, chat, and moderation
  administration;
- money, credits, payments, refunds, host fees, financial outcomes, and
  financial repair administration;
- notices, support, reviews, rejected attempts, admin actions, admin reads,
  policy/history reads, notifications, and retired route behavior;
- D requirement, test, testing-record, and execution-register outputs.

### Not Included

This pass does not:

- change backend, frontend, schema, migration, provider, deployment, or runtime
  source behavior;
- prove live Stripe, Firebase/GCP, Cloudflare/R2, hosting, production-data, or
  deployed-runtime behavior;
- redesign admin roles into named permissions;
- add dual-control, new confirmation prompts, or provider MFA;
- implement a new moderation taxonomy or safe-notice policy;
- implement minimum-necessary admin data, excerpt-first sensitive reads,
  controlled unmask, denied export, or admin read auditing;
- implement durable audit-log architecture or sensitive-access audit storage;
- prove Stripe webhook lifecycle, durable financial reconciliation, or live
  provider retry behavior;
- reopen accepted A/B/C authorization scope;
- use `backend/tests/legacy/` as source, proof, design input, or evidence.

### Dependencies And Later Owners

Accepted prerequisites:

- `WS03-04A` is the source of truth for route/action ownership, matrix
  classification, drift detection, and A uncovered-gap registration.
- `WS03-04B` is accepted for self-owned account, notification, inbox,
  saved-card, game-credit, payment, refund, and host-fee authorization.
- `WS03-04C` is accepted for ordinary game, community, roster, chat, My Games,
  and Need-a-Sub relationship authorization.

Named later owners that constrain D:

- `WS05` owns Stripe webhook lifecycle, durable payment/refund/credit
  reconciliation, durable financial/notification workflows, provider retry
  behavior, and provider-runtime proof.
- `WS03-05` owns moderation states, safe notices, minimum-necessary admin data,
  excerpt-first sensitive access, controlled unmask behavior, and denied export
  behavior.
- `WS09-02` owns append-only administrative audit trail, sensitive-access
  controls, read-audit, and sensitive-read/unmask/export audit behavior.
- `WS10-01` owns data classification, retention, privacy, legal hold, archive,
  deletion, and broader export-handling policy.
- `WS03-03B` and `WS10-02` own provider/admin MFA, Firebase/GCP control-plane
  facts, secrets, provider access, rotation, revocation, and offboarding
  evidence.
- `WS06` owns later R2/storage lifecycle and provider evidence beyond the local
  venue-image admin authorization ordering D proves.

No current executable owner was found for a broad redesign from the current
active-admin model to named permissions, dual-control, or new confirmation
prompts. Current authority does not make that redesign a D requirement. If an
owner requires those controls before `WS03-04` can close, D must leave the
parent incomplete and return for owner decision, intake, or Gate A correction.

## 4. Requirements

| ID | Requirement | What it means | Why it matters |
|---|---|---|---|
| `WS03-04D-R1` | D route inventory remains exact. | The accepted authorization matrix is the exact source for D ownership: `40` route families and `187` route keys, with no B/C overlap, no blocked D route, and no unclassified drift. | D must cover the admin/high-risk surface assigned by the parent. |
| `WS03-04D-R2` | Every D route requires the current verified active admin user. | Missing or invalid credentials produce current `401` behavior; authenticated users who are ordinary, unverified, inactive, suspended, deleted, or stale-role are forbidden before admin behavior is reachable. | Admin breadth must not be available to invalid or ordinary users. |
| `WS03-04D-R3` | The `22` recent-admin route keys keep recent-authentication before high-risk effects. | Stale admin sessions are rejected before account, role, hosting, game, venue, participant, money, credit, refund, payment-event, notice, or Need-a-Sub removal effects run. | A valid admin session alone is not enough for the most dangerous current actions. |
| `WS03-04D-R4` | Admin list, search, lookup, aggregate, and detail reads keep admin-only scope. | Active admins can use current filters, pagination, cursors, object lookup, and missing-object behavior; non-admins cannot use path IDs or query filters to enter admin read branches. | Admin reads intentionally expose more breadth than ordinary user routes. |
| `WS03-04D-R5` | User, account, role, and hosting admin actions preserve their protections. | Delete, role change, suspend, unsuspend, restrict hosting, restore hosting, and preview/read branches prove recent-auth where required, current-state checks, self/final-admin protections, idempotency where source defines it, and no unauthorized account/role/hosting side effects. | These actions can remove users, alter privilege, or block account capability. |
| `WS03-04D-R6` | Game, official-game, community-game, roster, venue, venue-image, Need-a-Sub, and chat moderation actions preserve object and state authorization. | D proves active-admin or recent-admin gates, object binding, lifecycle checks, tombstones, successful effects, and rejected-request no-side-effect behavior for materially distinct game and moderation branches. | Admin game and moderation routes can change who can play, host, join, chat, or see a game. |
| `WS03-04D-R7` | Money, credit, payment, refund, host-fee, payment-event, and financial-outcome actions preserve financial authorization and state protections. | D proves admin gates, recent-auth where current source requires it, object/list scope, provider-fake ordering where applicable, state/idempotency protections, and no unauthorized financial side effects. | Financial admin actions can affect balances, refunds, provider-adjacent state, and money review outcomes. |
| `WS03-04D-R8` | Notice, notification, policy/history, support, review, rejected-attempt, admin-action, and moderation administration remains admin-only. | D proves admin-only access, recent-auth for notice create/cancel, review/support/action state checks, tombstones where routes are retired, and no unauthorized notice/review/moderation side effects. | Administrative communication and review surfaces must not be exposed or mutated by ordinary users. |
| `WS03-04D-R9` | D write surfaces reject caller control over server-owned fields. | Caller input cannot set or override admin actor, target ownership, role/account lifecycle outside allowed actions, provider identity, financial status outside source transitions, recipient scope outside source rules, moderation actor, audit/action actor, timestamps, or other server-controlled fields. | Authorization can fail if body fields can rewrite privileged state after route gating. |
| `WS03-04D-R10` | Default-deny behavior covers every D denial class. | D proves required `401`, `403`, `404`, retired `410`, ordinary-user, stale-role, stale recent-auth, cross-object/path-ID, missing-object, and rejected-mutation cases, with protected state unchanged where a mutation was attempted. | Success cases alone do not prove unauthorized users are blocked safely. |
| `WS03-04D-R11` | D requirements, tests, matrix checks, testing record, and source controls remain traceable. | Requirement JSON, pytest markers, test names, matrix inspection, and `TESTING_RECORD.md` preserve the meanings in this plan and map evidence to behavior actually proven. | Reviewers need to know D evidence proves the frozen contract instead of redefining requirements around convenient tests. |
| `WS03-04D-R12` | Final `WS03-04` parent accounting is honest. | A/B/C/D obligations and the accepted A uncovered-gap register are accounted for. Remaining provider/runtime, Stripe webhook, audit, privacy, moderation, safe-notice, export/unmask/read-audit, provider MFA, and named-permission/dual-control questions are either named later work, not current-source requirements, or blockers. | D is the final child, but the parent may close only when every remaining obligation is proven or legitimately assigned without blocking completion. |

## 5. Technical Design

### Route Inventory And Shared Admin Entry

The exact D route inventory is owned by:

```text
backend/tests/workflows/authorization_matrix_foundation/authorization_matrix.json
```

Implementation evidence must compare that matrix to the current FastAPI route
table. The plan summarizes human-facing domains rather than hand-maintaining
all machine route families.

Every D route preserves the current dependency chain recorded by the matrix:

```text
get_current_app_user
get_verified_firebase_identity
require_active_user
require_verified_user
require_active_admin
```

Expected entry behavior:

- missing or invalid credentials are rejected with current `401` behavior;
- authenticated users who are not allowed into admin behavior are rejected
  before route-specific work runs;
- ordinary, unverified, inactive, suspended, deleted, and stale-role users do
  not receive admin data or mutate protected state;
- active admins receive only the current source's admin behavior;
- rejected users cannot reach privileged path-ID, query-filter, or body-field
  branches.

### Recent-Admin High-Risk Routes

The current matrix marks these `22` route keys as recent-admin routes:

```text
DELETE /games/{game_id}
DELETE /venues/{venue_id}
PATCH /admin/users/{user_id}/role
PATCH /payment-events/{payment_event_id}
POST /admin/community-games/{game_id}/cancel
POST /admin/game-credits/issue
POST /admin/game-credits/{game_credit_id}/reverse
POST /admin/money/financial-outcomes
POST /admin/money/issues/{money_issue_id}/resolve
POST /admin/money/issues/{money_issue_id}/retry-credit
POST /admin/money/refunds/{refund_id}/reconcile
POST /admin/money/refunds/{refund_id}/retry
POST /admin/need-a-sub/{post_id}/remove
POST /admin/official-games/{game_id}/cancel
POST /admin/official-games/{game_id}/participants/{participant_id}/remove
POST /admin/platform-notices
POST /admin/platform-notices/{notice_id}/cancel
POST /admin/users/{user_id}/delete
POST /admin/users/{user_id}/restore-hosting
POST /admin/users/{user_id}/restrict-hosting
POST /admin/users/{user_id}/suspend
POST /admin/users/{user_id}/unsuspend
```

Evidence must prove stale recent-admin authentication is rejected before every
materially different high-risk effect class. Routes not listed here still
require active admin and verified email, but must not be described as
recent-auth protected.

### Materially Distinct Behavior Matrix

| Domain | Materially different behaviors | Why they require separate treatment |
|---|---|---|
| Admin identity and stale-role entry | `/admin/me`, active-admin identity response, stale-role denial, and inactive/deleted/suspended/unverified denials. | Identity reads exercise the shared admin gate without mutating state, while stale-role and account-state failures prove rejected users cannot enter later admin branches. |
| User, account, role, and hosting | Delete preview/execution, role change, suspend, unsuspend, hosting restrict/restore, self/final-admin protection, and idempotency where source defines it. | These actions mutate account capability or privilege and differ in current-state checks, recent-auth requirements, notifications, admin-action records, and protected side effects. |
| Admin list, read, lookup, and history | User, game, money, payment, refund, credit, notice, support, review, rejected-attempt, image, lookup, action, status-history, policy, booking-policy, venue-approval, waitlist, and host-fee reads. | Admin reads expose broad data through different filters, pagination, cursors, object lookup, unsupported-filter handling, and missing-object behavior. |
| Official games, rosters, and participants | Official-game create/edit, cancellation preview/execution, host assignment/removal, player add, immediate participant delete, removal preview/execution, and participant/booking/waitlist/money/chat reads. | These branches differ in lifecycle checks, venue/address snapshots, host/player state, capacity, booking/payment/refund effects, participant binding, notifications, and recent-admin requirements. |
| Generic game, venue, and venue-image administration | Generic game create/update/delete, venue delete, venue-image upload readiness/initiation/completion/update, admin image reads, and retired venue create/update tombstones. | Game, venue, and image branches have different lifecycle, ownership, storage-preparation, completion-state, metadata, tombstone, and provider-adjacent ordering behavior. |
| Community games and moderation | Community-game reads, chat summary/messages, chat review/remove/restore, payment-text hide/restore, game hide/restore, pause/resume joining, cancellation, and review flag actions. | Visibility, joining, lifecycle, review, chat-message binding, notification, and audit/action effects differ materially; community cancellation is recent-admin high risk. |
| Need-a-Sub and chat moderation | Need-a-Sub reads, post hide/restore/remove, and chat review/remove/restore. | Remove is recent-admin high risk; hide/restore and chat moderation differ in post/message binding, owner-notice, idempotency, visibility, and rejected side effects. |
| Game credits | Credit issue and credit reversal. | Issue depends on target user, booking/payment/game source binding, amount eligibility, idempotency keys, and ledger creation; reversal depends on credit state, usage creation, status transition, and idempotency. |
| Financial outcomes | `no_fee_charged`, `refund`, `credit`, `forfeit`, and `manual_review`. | Variants differ in amount handling, applied status, refund or credit creation, entitlement state, money-issue staging, target-notice behavior, provider-fake ordering, and admin-action effects. |
| Money issues | Money issue resolve and retry-credit. | Resolve proves issue type/status rules and no false resolution; retry-credit proves credit release versus restore branches, ledger effects, issue events, idempotency, and failed-retry state. |
| Refunds and payment events | Refund retry, refund reconciliation, payment-event update/repair, and provider-fake call ordering where source calls provider-adjacent code. | These branches differ in refund state, refund-event recording, provider-facing ordering, repairable versus provider-owned payment-event fields, and rejected financial side effects. |
| Financial reads | Money, credit, payment, refund, refund-event, financial-outcome, host-fee, and user financial reads. | Financial reads have different filters, object lookup, unsupported-filter rejection, cursor behavior, and private operational response fields. |
| Platform notices | Notice create, selected-recipient versus all-eligible recipients, list/detail/recipient reads, and cancellation. | Create/cancel require recent-admin proof and differ in recipient mode, fingerprint conflict, row creation, sequence behavior, cancellation idempotency, actor/timestamp recording, and admin-action effects. |
| Support, review, rejected attempts, and admin actions | Support flag list/detail/resolve, review-case list/detail/note/close, rejected-attempt reads, and admin action list/detail/log/note behavior. | These routes bind to different target records and have different review/support transitions, note/action creation, and rejected side effects. |
| Admin notifications and policy/history | Admin notification reads, policy/history reads, booking-policy reads, and broad retired notification routes. | These routes remain admin-only but differ from B-owned self-notification proof and mutable notice behavior. |
| Retired route classes | Admin action mutation, legacy booking/policy mutation, status-history mutation, game-chat mutation, image mutation, participant mutation, host-fee mutation, notification mutation, payment/refund mutation, user-setting/stat mutation, venue mutation, venue-approval mutation, waitlist mutation, and old official-game host/participant mutation. | Retired calls must return current `410` behavior and must not create or change business rows; representative tombstone proof is valid only where implementation and protected state are materially equivalent. |

### Field And Mass-Assignment Boundaries

D-owned write evidence must prove callers cannot control server-owned fields or
effects.

| Surface | Server-owned fields or effects that remain protected |
|---|---|
| User/account/role/hosting actions | admin actor, target identity, self/final-admin decisions, account lifecycle outside the allowed action, provider identity, audit actor, timestamps, and notification metadata |
| Game/community/official/roster actions | host/player identity outside allowed admin action, participant ownership, game lifecycle outside source transition, payment/refund/provider state, moderation actor, audit actor, and timestamps |
| Need-a-Sub/chat/moderation actions | target post/message binding, owner identity, visibility/review state outside source transition, moderation actor, notice recipient, audit actor, and timestamps |
| Venue and image actions | storage/provider identifiers, upload completion state, image ownership, venue state outside source transition, metadata not accepted by schema, and audit actor |
| Money/credit/payment/refund actions | provider customer/payment/refund identity, ledger owner, credit owner, financial status outside source transition, idempotency source, reconciliation source, audit actor, and timestamps |
| Notices/support/review/admin actions | notice creator/canceller, recipient scope outside source rules, support/review state outside source transition, target records, audit actor, and timestamps |
| Retired routes | all business state; body fields must not become business mutations |

Read-only D routes are not mass-assignment surfaces, but their path IDs and
query filters still require proof against access widening.

### State, Idempotency, Provider Ordering, And Rejection Rules

Current-source behavior determines the exact state and idempotency rules D must
prove. Evidence must not invent stricter product policy, but it must prove the
rules that exist now:

- account/role/hosting protections, including self/final-admin handling;
- game lifecycle, roster, participant, capacity, booking, waitlist, and
  moderation state checks;
- Need-a-Sub post/message binding and idempotent removal where source defines
  it;
- credit issue/reversal eligibility and ledger state;
- financial-outcome, money-issue, refund, and payment-event state transitions;
- platform-notice fingerprint/cancellation idempotency and recipient state;
- support and review current-state transitions;
- retired-route tombstone behavior.

Where source can call provider-adjacent code, D proof uses local fakes or
source inspection to show authorization and state checks occur before provider
effects. It does not prove live provider behavior.

Rejected mutation evidence must name the protected state for each materially
distinct behavior and prove it remains unchanged. A broad "forbidden" status
assertion is not enough for D.

## 6. Implementation Outputs

D implementation produces:

- one D requirement declaration with `R1` through `R12`;
- trusted backend tests under the D workflow evidence scope;
- one D `TESTING_RECORD.md` describing risks, scenario groups,
  representative-equivalence reasoning, side-effect matrices, and evidence
  adequacy;
- a proposed execution-register update that records D accepted state and the
  final `WS03-04` parent disposition that becomes true only after the D PR
  merges.

No production source, frontend source, schema, migration, provider, runtime,
authorization matrix, intake, or frozen-plan edit is planned for D. If correct
completion requires one, implementation must stop for the workflow's correction
path instead of broadening the file scope.

## 7. Testing And Evidence

The plan defines required proof layers. The detailed scenario catalog,
individual assertions, side-effect matrices, representative-equivalence
reasoning, and adequacy analysis belong in the D testing record.

Focused D evidence must cover these proof layers:

- route inventory, route ownership, dependency drift, recent-admin
  classification, and A/B/C prerequisite consumption;
- shared admin access, default-deny behavior, current status-code behavior, and
  rejected-state invariants;
- API and PostgreSQL behavior for the materially distinct domains defined in
  Technical Design;
- field and mass-assignment protection for D-owned write surfaces;
- state, idempotency, and protected-side-effect behavior for successful and
  rejected privileged mutations;
- provider-fake ordering where current source can call provider-adjacent code;
- retired-route `410` behavior and no business mutation from tombstones;
- requirement mapping, testing-record adequacy, and final parent accounting.

Accepted compatibility evidence must remain valid for:

- `WS03-04A` authorization matrix foundation and drift guard;
- `WS03-04B` self-owned account, notification, inbox, saved-card, credit,
  payment, refund, and host-fee authorization;
- `WS03-04C` ordinary relationship authorization;
- affected predecessor/platform scopes for identity authority, account
  lifecycle, recent-auth, App Check/admin-provider security, provider-payment
  input ownership, request ownership, response minimization, and chat rate
  limits.

This plan defines the proof required for the current source behavior.
Completion depends on satisfying the criteria in Section 9.

The D `TESTING_RECORD.md` must map every materially distinct behavior from
Technical Design to exact scenarios and evidence. It owns the detailed setup,
assertions, side-effect matrices, representative-equivalence reasoning, and
adequacy analysis.

## 8. Validation

Validation is grouped by proof category:

- focused D authorization proof for the
  `admin_route_list_high_risk_function_authorization` workflow scope;
- accepted A/B/C compatibility proof for matrix, self-owned authorization, and
  relationship authorization scopes;
- affected predecessor and platform regression proof for identity authority,
  account lifecycle, recent-auth, App Check/admin-provider security,
  provider-payment input ownership, request ownership, response minimization,
  and chat rate limits;
- PostgreSQL-backed local evidence for persisted effects, prohibited side
  effects, idempotency, state transitions, and object binding;
- provider-fake evidence for local authorization ordering around provider-
  adjacent refund, payment-event, storage, or financial workflows;
- domain checker and suite checker proof for trusted test architecture;
- test-to-requirement mapping proof for `R1` through `R12`;
- final security, sensitive-content, exact changed-file, staged-file, and
  diff-whitespace checks.

Validation commands and examples must use sanitized references such as
`DATABASE_URL="$TEST_DATABASE_URL"` rather than literal credentials. Validation
records must not describe local tests or provider fakes as live, deployed,
production-runtime, or live-provider proof.

## 9. Completion Criteria

D is complete when:

- [ ] `R1` through `R12` are declared with the meanings in this plan.
- [ ] The D matrix inventory remains exactly `40` route families and `187`
  route keys, with all D routes active-admin protected, `22` recent-admin
  route keys, and `45` retired `410` route keys.
- [ ] Every materially distinct behavior branch named in this plan is either
  proven by D evidence, proven by accepted A/B/C or predecessor evidence, or
  explicitly recorded as a legitimate later-owned boundary.
- [ ] Successful privileged branches prove the current source's meaningful
  persisted effects.
- [ ] Rejected privileged branches prove the named protected state remains
  unchanged.
- [ ] Field and mass-assignment boundaries are proven for all D-owned write
  surfaces.
- [ ] The D testing record explains the evidence actually collected without
  overclaiming local or fake-provider proof.
- [ ] D validation passes for focused scope, compatibility scope, affected
  predecessor/platform scope, checker scope, test-to-requirement mapping, and
  final security/file-scope checks.
- [ ] The execution register records D's proposed accepted state and final
  `WS03-04` parent disposition that becomes true only after merge.
- [ ] No unresolved D blocker, ownerless required obligation, or scope mismatch
  remains.

`WS03-04` may be proposed complete after D merges only if every parent
obligation is accepted by A/B/C/D evidence or legitimately assigned to a named
later owner without blocking parent completion. If any required D obligation is
unproved, or if any required remaining obligation has no owner-approved
downstream disposition, the register must leave the parent incomplete or
blocked rather than claim completion.

## 10. Appendix A: Exact Repository File Scope

| Scope item | Exact value |
|---|---|
| Frozen intake artifact | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` |
| Frozen canonical plan artifact | `docs/production-readiness/planning/passes/ws03/ws03-04d-admin-route-list-high-risk-function-authorization.md` |
| Gate B editable file set | The exact paths listed below |
| Expected final changed-file set | The exact paths listed below |
| Read-only prerequisite artifacts | Accepted `WS03-04A`, `WS03-04B`, `WS03-04C`, accepted authorization matrix, current backend source |

Gate B may edit exactly:

```text
backend/tests/support/requirements/ws03_04d.json
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_matrix_scope_and_dependencies_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_gate_and_default_deny_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_list_read_scope_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_user_high_risk_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_game_roster_moderation_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_money_credit_refund_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_notice_support_review_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_tombstone_field_traceability_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

The final D pass changed-file set is exactly:

```text
docs/production-readiness/planning/passes/ws03/ws03-04d-admin-route-list-high-risk-function-authorization.md
backend/tests/support/requirements/ws03_04d.json
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_matrix_scope_and_dependencies_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_gate_and_default_deny_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_list_read_scope_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_user_high_risk_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_game_roster_moderation_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_money_credit_refund_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_notice_support_review_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/test_admin_tombstone_field_traceability_contract.py
backend/tests/workflows/admin_route_list_high_risk_function_authorization/TESTING_RECORD.md
docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md
```

The frozen intake, source code, authorization matrix, and accepted A/B/C
artifacts are read-only for D implementation. The canonical plan changes only
through the owning Gate A correction path.

Implementation must stop for Gate A correction if correct completion requires:

- production source, frontend, schema, migration, provider, runtime, or
  configuration edits;
- an authorization matrix change;
- a frozen intake or canonical-plan change;
- a new requirement, proof layer, owner decision, or policy decision;
- a file outside the frozen editable file set;
- a broader interpretation of B/C/D ownership;
- claiming provider/runtime/audit/privacy/moderation proof that D does not
  actually collect;
- including a credential, secret, credential-bearing URL, private provider
  value, personal/payment data, raw sensitive log, local machine path, session
  state, or internal chat material in tracked artifacts.

Implementation may repair test implementation defects inside the frozen
editable file set when this plan already requires the proof and no broader
decision is needed.

## 11. Appendix B: Controls And Later Owners

| Control / decision / obligation | What D establishes | Remaining owner or disposition |
|---|---|---|
| `IAM-012`, `IAM-013`, `IAM-015` | D route ownership, admin list/read scope, default-deny behavior, and route drift protection for D-owned routes. | Complete for D when evidence proves the branches in this plan. |
| `IAM-016` | Current active-admin gate and verified-user dependency for all D routes. | Named-permission or narrower-permission redesign has no current executable owner and is not a current D requirement; if owner requires it before `WS03-04` completion, it blocks completion pending owner decision and new planning. |
| `IAM-017` | Current recent-admin gate and state/idempotency proof for the `22` current high-risk route keys. | Provider/admin MFA remains `WS03-03B` and `WS10-02`. Dual-control and additional confirmation prompts have no current executable owner and are not current D requirements; if required before `WS03-04` completion, they block completion pending owner decision and new planning. |
| `ADM-007`, `ADM-013` | User, account, role, hosting, admin-action, and administrative support/review behavior remains active-admin or recent-admin protected with current-state checks and rejected-action side-effect proof. | Durable audit trail and sensitive-access controls remain `WS09-02`; moderation/safe-notice/minimum-necessary admin-data work remains `WS03-05`. |
| `ADM-015` | D proves current admin moderation, notice, support, review, and related privileged behavior for authorization, state binding, and rejected side effects. | Moderation taxonomy, safe notices, and minimum-necessary admin data remain `WS03-05`; append-only audit and read-audit remain `WS09-02`. |
| `PAY-005`, `PAY-006` | Local admin money, credit, refund, payment-event, provider-fake ordering, and rejected financial side-effect proof for D-owned routes. | Stripe webhook lifecycle, durable payment/refund/credit reconciliation, provider retry behavior, provider runtime proof, and durable financial/notification workflows remain `WS05`. |
| `GOV-006`, `TST-005` | Stable D requirement declaration, pytest markers, testing record, checker validation, and final parent accounting. | No later action unless D evidence or register state changes. |
| `WS03-04A-G001` for `POST /stripe/webhook` | D preserves the accepted A gap disposition and does not treat the provider callback as D-owned admin-route proof. | Covered elsewhere by `WS05`; it does not block `WS03-04` completion because the provider callback payment lifecycle belongs to WS05 payment/webhook work. |
| Moderation states, safe notices, minimum-necessary admin data, controlled unmask, and denied export behavior | D proves authorization and rejected-side-effect behavior for current admin/moderation/notice routes only. | `WS03-05`. |
| Append-only administrative audit trail, sensitive-access controls, read-audit, and sensitive-read/unmask/export auditing | D proves local admin-action or related records where current source already creates them. | `WS09-02`. |
| Data classification, retention, legal hold, archive, deletion, and broader export-handling policy | D does not define table lifecycle or legal/privacy policy. | `WS10-01`. |
| Provider control-plane, secrets, service-account governance, provider access, rotation, revocation, and offboarding | D uses local tests and sanitized evidence only. | `WS10-02`, with Firebase/admin-MFA overlap in `WS03-03B`. |
| Venue-image storage provider lifecycle and R2 evidence | D proves admin authorization ordering and no unauthorized local source effects only. | `WS06` for storage/provider lifecycle and `WS10-02` for provider access evidence. |

No production-source correction is planned by this Gate A design. `WS03-04`
parent completion remains conditional on D evidence satisfying `R1` through
`R12` and on any ownerless required obligation being treated as a blocker
rather than hidden as future work.
