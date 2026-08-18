# Production-Readiness Pass Intake: WS03-04

## At A Glance

| Field | Value |
|---|---|
| Intake date | `2026-08-18` |
| Intake record path | `docs/production-readiness/planning/passes/ws03/ws03-04-intake.md` |
| Parent blueprint pass | `WS03-04 - Complete authorization matrix and negative proof` |
| Proposed executable pass | `WS03-04A - Authorization matrix foundation and route drift guard` |
| Track | `WS03` |
| Intake outcome | `decompose child` |
| Current develop basis | `22855d0d0b8e67be733de1fea6e3771f0587cfa9` |
| Intake sources | `00-READ-ME-FIRST.md`; `01-PROGRAM-CONTEXT.md`; `PASS-IMPLEMENTATION-WORKFLOW.md`; `PASS-INTAKE-TEMPLATE.md`; `PASS-EXECUTION-REGISTER.md`; master blueprint; final remediation plan; approved decisions; accepted WS03 predecessor plans; current source and trusted-test inventory |
| Proposed planning document | `docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md` |
| Proposed requirement declaration | `backend/tests/support/requirements/ws03_04a.json` |
| Proposed trusted evidence scope | `backend/tests/workflows/authorization_matrix_foundation` |

## 1. Purpose

This intake evaluates the parent blueprint pass `WS03-04 - Complete authorization matrix and negative proof` and decides the next executable pass boundary. It exists because the parent is the first WS03 pass that tries to cover the whole backend authorization surface after the accepted identity, account-state, recent-auth, and App Check foundations.

This intake does not implement WS03-04, does not create a Gate A plan, and does not select any later executable pass beyond the proposed next child scope.

## 2. Authority Read

| Source | Relevant meaning for this intake |
|---|---|
| `00-READ-ME-FIRST.md` | Durable production-readiness documents, not prior prompts or branch memory, are the authority. Gate work must stop at the requested boundary. |
| `01-PROGRAM-CONTEXT.md` | WS03 is the identity, account-state, authorization, and admin-security workstream. Current accepted `develop` plus accepted pass records define repository truth for new passes. |
| `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md` | Stage 0 decides the executable pass boundary, may only create the intake record, must apply the cohesion test and no-gap/no-overlap allocation, and must compute SHA-256 after the intake is complete. |
| `docs/production-readiness/planning/templates/PASS-INTAKE-TEMPLATE.md` | Defines the required intake structure and the allowed Stage 0 outcomes. |
| `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` | `WS03-01` and `WS03-02` are accepted. `WS03-03` is accepted through `WS03-03A` and `WS03-03B`. `WS03-04` is not yet selected and requires intake before implementation. |
| Master blueprint parent entry | `WS03-04` must inventory every protected route/action and enforce object, relationship, workflow-state, list/query, field, function, role, and concealment boundaries. |
| Final remediation plan | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, and `IAM-017` remain partial and require a complete API authorization matrix with negative proof. |
| Approved decisions / governance | `IDB-01` through `IDB-04` establish replay, identity authority, verified-email, and App Check boundaries. The master decision inventory records `ADM-014` as approved; minimum-necessary admin data remains primarily later WS03-05/WS09 scope unless required for WS03-04 authorization proof. |
| Accepted prerequisite pass plans | `WS03-01` establishes provider/local identity authority and verified admin identity. `WS03-02` establishes local account lifecycle states and current request-time local state. `WS03-03A/B` establish recent-auth/App Check boundaries that must not replace authorization. |
| Current accepted repository truth | FastAPI registers a broad route surface through `backend/main.py`; auth dependencies are centralized in `backend/services/auth_service.py`; source models define current user, game, participation, Need-a-Sub, chat, payment, notice, support, and admin state fields; no `ws03_04*` requirement declaration or trusted WS03-04 evidence scope exists yet. |

Do not use superseded prompts, old branch names, old PR descriptions, or historical implementation as authority.

## 3. Parent Blueprint Pass

| Field | Value |
|---|---|
| Parent pass | `WS03-04` |
| Parent title | `Complete authorization matrix and negative proof` |
| Parent track | `WS03` |
| Parent type | `Domain implementation and current tests` |
| Primary controls | `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017` |
| Blueprint dependencies | `WS03-01`, `WS03-02`; stable resource and state models |
| Blueprint maximum scope | Inventory every protected route/action and enforce object, relationship, workflow-state, list/query, field, function, role, and concealment boundaries. |

In plain language, WS03-04 is the pass family that turns "authenticated" into "authorized for this exact resource, state, field, list, and action." It must prove negative cases such as cross-user ID substitution, stale role or account state, hidden resources, unsafe list/search scope, mass-assignment, and incorrect 401/403/404 behavior.

## 4. Current Execution Register State

| Register item | State |
|---|---|
| Parent pass status | `not started / not yet selected` |
| Accepted child passes | None |
| Known closeout records | None for `WS03-04` |
| Remaining parent scope | Full parent scope remains: matrix, code corrections, negative tests, and uncovered-gap register for all protected route/action families. |
| Register ambiguity | No material ambiguity. The register's `39d07e71366b3177bd380f3c07eade0bb0210406` is a historical reconciliation SHA; the current accepted `develop` basis for this intake is `22855d0d0b8e67be733de1fea6e3771f0587cfa9`. |

The first substantive child PR must include the execution register in Gate B scope and record the accepted intake/child state after human approval and implementation acceptance.

## 5. Current Repository Truth

| Classification | Fact |
|---|---|
| Repository truth | Current branch `pr/WS03-04` was created from current `develop`/`origin/develop` at `22855d0d0b8e67be733de1fea6e3771f0587cfa9`. |
| Repository truth | `backend/main.py` registers the active API routers for auth, users, settings, stats, payment methods, venues/images, games, community games, checkout, bookings, participants, waitlists, chats, inbox, notifications, payments, payment events, refunds, policy records, platform notices, Need-a-Sub, support flags, and admin surfaces. |
| Repository truth | `backend/services/auth_service.py` centralizes the current identity helpers: `get_current_app_user`, `require_active_user`, `require_verified_user`, `require_active_admin`, `require_recent_active_user`, and `require_recent_active_admin`. |
| Repository truth | The user model defines current roles `player`/`admin` and account statuses `active`, `suspended`, `pending_deletion`, and `deleted`. |
| Repository truth | Game and Need-a-Sub source models define concrete resource/state fields such as `game_type`, `publish_status`, `game_status`, `public_visibility_status`, `join_enforcement_status`, `post_status`, and `public_visibility_status`. Additional status-bearing models exist for bookings, participants, waitlists, chats, payments, refunds, credits, notices, support flags, and admin records. |
| Repository truth | Accepted trusted-test scopes exist for identity authority, account lifecycle, recent auth, and App Check provider security. No `backend/tests/support/requirements/ws03_04*.json` file or `backend/tests/workflows/authorization_matrix_foundation` scope exists yet. |
| Authoritative requirement | `IAM-012` requires default-deny authorization beyond a valid token and local user. |
| Authoritative requirement | `IAM-013` requires server-side object, nested-resource, relationship, state, and function authorization for every identifier and operation. |
| Authoritative requirement | `IAM-015` requires list/search/aggregate/cursor/bulk/export scoping plus explicit 403/404 concealment semantics. |
| Authoritative requirement | `IAM-016` requires current backend administrator gates on every admin request. |
| Authoritative requirement | `IAM-017` requires high-risk actions to have action-specific permission, recent authentication where applicable, confirmation, idempotency, current-state checks, and auditability. |
| Repository truth | Accepted WS03 predecessor records provide repository source/test evidence for identity authority, account-state enforcement, recent-auth source controls, and App Check defense-in-depth boundaries. |
| Inference | The resource and state model prerequisite is satisfied enough for Stage 0 and Gate A design because active source exposes concrete route families and state fields. Final database/runtime/concurrency proof remains a later supporting obligation and must not be overclaimed. |
| Unknown | Full provider/runtime authorization behavior, staged role-removal timing, named permission governance, export/unmask policy, and audit-read controls are not proven by this intake. |

## 6. Executable-Pass Cohesion Assessment

This table assesses `WS03-04` as a single executable pass.

| Cohesion question | Verdict | Evidence/reason | Split implication |
|---|---|---|---|
| One primary outcome | No | The parent combines inventory/matrix creation, route corrections, negative API proof, admin high-risk action review, list/concealment policy, and uncovered-gap management. | Split. |
| One requirement/invariant family | Partial | All requirements are authorization-related, but they cover separate invariants: self-owned records, relationship resources, public concealment, admin gates, high-risk actions, and list/search scopes. | Supports split. |
| One prerequisite state | No | Some source-owned self/relationship authorization can proceed from WS03-01/02, while named admin permissions, export/unmask/audit policy, and runtime proof may require later or external evidence. | Split required by workflow. |
| One safe merge/rollback or forward-fix unit | No | A single PR touching every protected route family would mix unrelated user, payment, chat, admin, moderation, and support behavior and would be hard to review or forward-fix safely. | Split required by workflow. |
| One coherent evidence model | No | Evidence needs route-table inventory, static drift checks, API IDOR tests, list/search negative proof, stale state/role tests, and admin high-risk action proof. | Split. |
| One semantic review model | No | Reviewers would need to reason about ordinary-user self access, host/participant relationships, public visibility, payment records, admin/moderation/money actions, and sensitive admin reads at once. | Split. |
| Safe/useful intermediate state | Yes when decomposed | A first child can safely create the route/action inventory, policy classification, and drift guard without claiming source enforcement closure. Later children can close allocated surfaces. | Decompose with `WS03-04A` first. |

## 7. Decomposition Decision

| Decision | Applies? | Reason |
|---|---|---|
| Implement parent as one executable pass | no | The parent fails the one-prerequisite-state and one-safe-merge-unit cohesion checks and would combine too many unrelated authorization semantics. |
| Decompose into child passes | yes | Decomposition keeps the mandatory complete matrix while letting source corrections and negative proof land by coherent authorization surface. |
| Stop for prerequisite | no | `WS03-01` and `WS03-02` are accepted, and current source has inventoryable route/resource/state models for Gate A design. |
| Stop for owner decision | no | No Stage 0 owner decision is required to propose `WS03-04A`. Gate A must stop if it finds an active route family whose authorization policy cannot be defined from existing authority. |

Proposed child-pass map:

| Order | Child ID | Title | One primary outcome | Allocated controls/requirement areas | Prerequisites | Produced capability | Handoff to later child | Safe merged intermediate state | Evidence profile | Explicit non-goals |
|---|---|---|---|---|---|---|---|---|---|---|
| `1` | `WS03-04A` | Authorization matrix foundation and route drift guard | Complete active route/action inventory, child allocation, policy classification, uncovered-gap register, and fail-closed drift guard for WS03-04. | Matrix/inventory portions of `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017`; route-family ownership and 401/403/404 policy classification. | Accepted `WS03-01`, `WS03-02`, `WS03-03A`, `WS03-03B`; current FastAPI route table and source models. | A canonical authorization matrix foundation that B/C/D can implement against. | `WS03-04B`, `WS03-04C`, and `WS03-04D` consume the matrix and close their allocated surfaces. | Source behavior may remain unchanged; parent remains incomplete but future unclassified route drift fails closed. | Static/dynamic route inventory, source classification, trusted pytest for matrix/drift, governance `TESTING_RECORD.md`. | No route behavior corrections except narrow matrix-enabling defects approved by Gate A; no player/admin source enforcement closure; no runtime/provider proof. |
| `2` | `WS03-04B` | Self-owned account, notification, and financial record authorization | Ordinary users can access or mutate only their own self, notification/inbox, saved-card, credit, payment, refund, and host-fee records with correct account, verified, recent-auth, list, and concealment behavior. | `IAM-012`, `IAM-013`, `IAM-015`, and self/high-risk parts of `IAM-017` for self-owned non-admin surfaces. | Accepted `WS03-04A` plus accepted WS03 identity/account/recent-auth foundations. | Self-owned record authorization corrections and negative proof. | No handoff to `WS03-04C` is required by this intake; `WS03-04D` consumes B's closure for final admin/high-risk review and parent-gap disposition. | Self-owned surfaces close while relationship and admin authorization remain explicitly incomplete. | Backend API pytest for cross-user ID substitution, self list scoping, stale account/role, field boundaries, and 401/403/404 semantics; static negative-space checks. | No host/participant/Need-a-Sub relationship closure; no admin route closure; no Stripe/provider runtime proof. |
| `3` | `WS03-04C` | Game, community, roster, chat, and Need-a-Sub relationship authorization | Hosts, participants, requesters, message senders/readers, and public callers are authorized by resource relationship and workflow state across game/community/Need-a-Sub surfaces. | `IAM-012`, `IAM-013`, `IAM-015`, and workflow/action parts of `IAM-017` for games, checkout/join/leave/guest actions, bookings/participants/waitlists, public hidden resources, game chats/messages, community game details/publish, Need-a-Sub posts/requests/chats/status histories. | Accepted `WS03-04A` plus accepted WS03 identity/account/recent-auth foundations; no hard dependency on `WS03-04B` is imposed by this intake. | Relationship authorization corrections and negative proof for player/host/community workflows. | `WS03-04D` consumes C's relationship-surface closure for final admin/high-risk review and parent-gap disposition. | Player and host workflow authorization can be accepted while self-owned and admin authorization remain allocated to B and D. | Backend API pytest for cross-user, cross-role, nested-resource, stale-state, hidden-resource, list scope, and 401/403/404 substitutions; source drift checks. | No self-owned account/notification/financial record closure; no admin matrix closure; no minimum-necessary admin data redesign; no broad database/concurrency proof beyond needed local state setup. |
| `4` | `WS03-04D` | Admin route, list, and high-risk function authorization | Admin routes and privileged actions are protected by current active-admin/recent-auth/action-state authorization, and admin list/search/read surfaces have explicit scope and concealment proof or recorded downstream gaps. | `IAM-016`, admin/high-risk portions of `IAM-017`, and admin portions of `IAM-012`, `IAM-013`, and `IAM-015`; compatibility with `ADM-007`, `ADM-013`, and `ADM-015` without taking over WS03-05/WS09. | Accepted `WS03-04A`, `WS03-04B`, and `WS03-04C`; accepted `WS03-03A/B` for recent-auth/App Check boundaries. | Admin authorization corrections, negative matrix, and final WS03-04 uncovered-gap disposition. | Handoff unresolved named-permission, dual-control, export/unmask, read-audit, or minimum-necessary admin-data gaps to WS03-05/WS09/owner decision when outside WS03-04 source authority. | After B and C are both accepted, D can complete the parent or explicitly block parent closure on owner/dependency gaps. | Backend API pytest for unauthenticated/non-admin/suspended/deleted/stale-role denial, recent-auth-preserved actions, admin object/list/function scope, and static negative-space checks. | No provider MFA/runtime authorization proof; no audit-log architecture; no moderation taxonomy or safe-notice redesign beyond authorization gating. |

## 8. Parent Obligation Allocation

| Parent obligation/control | Primary child/owner | Supporting child/evidence | Overlap reason, if any | Final disposition |
|---|---|---|---|---|
| Inventory every protected route/action | `WS03-04A` | B/C/D verify their allocated route families remain classified | Cross-cutting evidence | Implemented by A, maintained by later children through compatibility/drift checks. |
| Create authorization matrix | `WS03-04A` | B/C/D consume and prove allocated entries | Shared prerequisite | Implemented by A as matrix foundation; final parent closure requires B/C/D completion. |
| `IAM-012` default-deny beyond valid token/local user | B/C/D by surface | A classification; WS03-01/02 regressions | Shared prerequisite and compatibility | Implemented by each surface child. |
| `IAM-013` object, nested-resource, relationship, state, and function authorization | `WS03-04C` for relationship workflows; `WS03-04B` for self-owned records; `WS03-04D` for admin functions | A matrix | None except matrix compatibility | Implemented by allocated child surfaces. |
| `IAM-015` list/search/aggregate/cursor/bulk/export scoping and concealment | B/C/D by owning surface | A policy classification | Cross-cutting 403/404 semantics | Implemented by allocated child surfaces; export/unmask gaps may be deferred only with explicit owner/dependency record. |
| `IAM-016` backend admin gate | `WS03-04D` | A admin-route inventory; WS03-01/02 identity/account compatibility | Shared prerequisite | Implemented by D. |
| `IAM-017` high-risk action authorization | `WS03-04D` for admin; `WS03-04B` for self-owned saved-card/account-like actions; `WS03-04C` for terminal game/Need-a-Sub workflow actions | WS03-03A recent-auth and WS03-03B App Check compatibility | Shared recent-auth/App Check prerequisites | Implemented by allocated child surfaces; provider MFA/runtime proof remains deferred. |
| Field and mass-assignment boundaries relevant to authorization | B/C/D by owning schema/route family | WS02-05B1 and WS03-01 compatibility | Compatibility only | Implemented where WS03-04 authorization depends on the field/function boundary. |
| Exhaustive current negative tests | B/C/D by surface | A drift guard and requirement traceability | Cross-cutting evidence | Complete only when all children accepted. |
| Uncovered-gap register | `WS03-04A` starts canonical gap register; `WS03-04D` owns final parent disposition | B/C pass-specific unresolved-gap sections | Cross-cutting evidence | Parent closes only when every gap is closed, deferred to named later owner, or blocks closure. |

No-gap/no-overlap verdict: Passes A through D cover the full parent scope. Overlap is limited to the shared authorization matrix/drift guard, accepted identity/account/recent-auth compatibility, and cross-cutting 401/403/404 semantics. No child owns the same route-family enforcement surface as another child.

## 9. Ordering, Shared Responsibility, And Completion

Dependency graph: `WS03-04A` -> `{WS03-04B, WS03-04C}` -> `WS03-04D`.

`WS03-04A` must run first because it creates the route/action inventory, matrix foundation, child ownership map, and drift guard that keep later work from silently skipping route families. `WS03-04B` and `WS03-04C` may proceed independently after A, in either order or in controlled parallel work, unless a future current-source review proves a concrete hard dependency between them. `WS03-04D` must run after both B and C are accepted because admin authorization consumes the non-admin surface closures and owns the final uncovered-gap disposition.

Shared prerequisites are accepted WS03 identity/account/recent-auth/App Check boundaries, current FastAPI route registration, current source models, and current non-legacy trusted-test conventions. Compatibility responsibility travels with each child: a child may need focused regressions to prove it did not weaken already accepted WS03-01 through WS03-03 behavior or previously accepted WS03-04 children.

The parent is complete only when all approved WS03-04 children are accepted and every parent obligation is implemented, explicitly deferred to a named downstream owner, or marked blocked. The execution register must be updated in each substantive child PR according to the workflow, with the final child marking parent completion only if no parent obligation remains unresolved.

## 10. Proposed Executable Pass

| Field | Value |
|---|---|
| Pass ID | `WS03-04A` |
| Title | `Authorization matrix foundation and route drift guard` |
| Parent pass | `WS03-04` |
| Primary controls | Matrix/inventory portions of `IAM-012`, `IAM-013`, `IAM-015`, `IAM-016`, `IAM-017` |
| Supporting controls / decisions | `IDB-01`, `IDB-02`, `IDB-03`, `IDB-04`; accepted `WS03-01`, `WS03-02`, `WS03-03A`, `WS03-03B`; EN-01 trusted-test conventions |
| Dependencies | Accepted `WS03-01`; accepted `WS03-02`; stable current source route/resource/state models; accepted recent-auth/App Check source boundaries for compatibility |
| Expected pass type | `Domain / current tests / governance evidence` |

`WS03-04A` is a coherent implementation and review unit because it establishes the complete authorization route/action map and drift guard needed before behavior changes are safely assigned. It produces a useful accepted state without pretending to close source enforcement for every route family.

## 11. Preliminary Requirement Shape

| Requirement area | Source | Expected evidence class |
|---|---|---|
| Active route/action inventory | Master blueprint; `IAM-012` through `IAM-017`; current FastAPI app | pytest/static route inventory |
| Actor/resource/state/function/list/field/concealment classification | Master blueprint; final remediation plan | governance/manual review plus pytest-supported source inventory |
| Child ownership and no-gap allocation | Stage 0 workflow; parent blueprint | governance/manual review |
| Undefined policy and uncovered-gap register | Blueprint stop condition; final remediation plan | governance/manual review plus trusted-test negative space |
| Route-drift guard | `IAM-012` through `IAM-017`; EN-01 trusted evidence conventions | pytest/static/dynamic inventory |
| Compatibility with accepted identity/account/recent-auth/App Check foundations | Accepted `WS03-01`, `WS03-02`, `WS03-03A`, `WS03-03B` | focused pytest/source checks |

Final requirement IDs and wording belong in Gate A.

## 12. Evidence And Testing Expectations

| Evidence class | Needed? | Reason |
|---|---|---|
| Backend pytest | yes | `WS03-04A` needs trusted route-table/source inventory and drift checks over active non-legacy source. |
| Frontend unit/component | no for A | Frontend route guards must not be treated as backend authorization. Later children may inspect frontend callers for compatibility, but A is backend/source inventory. |
| Browser / Playwright | no for A | A does not claim browser behavior. Later runtime/browser evidence remains separate and should not be run by default. |
| PostgreSQL / concurrency | no for A | A inventories current source/state models. Database race proof belongs to later surface children or WS04/WS08 where required. |
| Migration rehearsal | no | No schema migration is expected for A. |
| Provider evidence | no | Provider/App Check/MFA/runtime facts are outside A. |
| Runtime/staging evidence | no | A is local repository inventory and planning evidence only. |
| Governance/manual review | yes | Human review must approve the matrix foundation, child ownership map, and gap/defer/block classifications. |

Gate A must refine this into requirement-by-requirement evidence design.

## 13. Expected Artifacts

| Artifact type | Expected? | Candidate owner/path |
|---|---|---|
| Canonical pass plan | yes | `docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md` |
| Requirement declaration | yes | `backend/tests/support/requirements/ws03_04a.json` |
| `TESTING_RECORD.md` | yes | `backend/tests/workflows/authorization_matrix_foundation/TESTING_RECORD.md` |
| Source/configuration | tbd | Gate A should prefer tests/docs/matrix artifacts only for A; any production-source edit must be a narrow matrix-enabling correction. |
| Documentation/governance | yes | Matrix/gap/disposition content in the A plan/evidence record, with exact paths decided by Gate A. |
| Provider/runtime evidence | no | External provider/runtime evidence remains outside A. |
| Execution-register update | yes for every substantive first-time executable pass | `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` |

The approved intake record is expected to travel with the first substantive child PR as a frozen artifact, but it is not Gate B-editable.

## 14. Non-Goals And Boundaries

- Do not begin Gate A in this intake.
- Do not create the `WS03-04A` plan, requirement declaration, evidence scope, testing record, matrix artifact, or execution-register update during Stage 0.
- Do not modify application source, tests, provider configuration, runtime settings, migrations, or frontend code during Stage 0.
- Do not use frontend route guards as authorization proof.
- Do not claim Firebase provider, MFA, App Check rollout, staging, role-removal timing, export/unmask, read-audit, or production authorization facts from local source alone.
- Do not include or inspect `backend/tests/legacy/`.
- Do not let later children edit this intake unless the parent structure itself needs a new Stage 0 revision and new SHA approval.

## 15. Dependencies And Readiness

| Dependency | Required state | Current state | Intake verdict |
|---|---|---|---|
| `WS03-01` | Accepted identity authority and verifier-controlled field boundary | Accepted in execution register and available as accepted pass/evidence records | ready |
| `WS03-02` | Accepted local account lifecycle, roles, and current-request state boundary | Accepted in execution register and available as accepted pass/evidence records | ready |
| Stable resource and state models | Current source exposes concrete active resource families and status/state fields for route authorization design | Current source contains registered route families and status-bearing user, game, Need-a-Sub, chat, booking, payment, notice, support, and admin models | ready for Stage 0/Gate A design |
| `WS03-03A` | Recent-auth source controls preserved where high-risk actions depend on them | Accepted child of `WS03-03` | ready as supporting compatibility dependency |
| `WS03-03B` | App Check defense-in-depth boundary does not replace authorization | Accepted child of `WS03-03` | ready as supporting compatibility dependency |
| Current route table | Inventoryable active FastAPI route table | `backend/main.py` includes the route modules; no Stage 0 route family was found to be un-inventoriable | ready |
| Named permission/export/unmask/audit policy | Needed only where Gate A/D tries to close those facts | Not fully proven by local source; likely downstream or owner-governance dependent | not a blocker for A; potential later-child blocker |

No dependency blocks honest Gate A design for `WS03-04A`.

## 16. Stop Conditions For Gate A

- Stop if the baseline branch, current SHA, or working-tree state no longer matches the approved Stage 0 intake assumptions.
- Stop if Gate A would need to modify this intake or change the approved child map instead of designing `WS03-04A`.
- Stop if the active FastAPI route table cannot be generated or an active route family cannot be inventoried.
- Stop if any route/action policy required by A cannot be classified from accepted authority and current source; route that case to owner decision or Stage 0 revision.
- Stop if a proposed A requirement tries to claim player/admin route enforcement closure that belongs to B/C/D.
- Stop if frontend route guards are the only available authorization control for any backend operation.
- Stop if Gate A would require provider/runtime/MFA/export/unmask/read-audit claims that local repository evidence cannot prove.

## 17. Human Approval And Intake Outcome

Outcome: `READY FOR GATE A: WS03-04A - Authorization matrix foundation and route drift guard`.

Exact next allowed action after human approval is to create the Gate A plan for `WS03-04A` at:

```text
docs/production-readiness/planning/passes/ws03/ws03-04a-authorization-matrix-foundation.md
```

Human approval of this intake authorizes the child structure, ordering, parent obligation allocation, and only the next executable child's Gate A. It does not authorize implementation, Gate B, or Gate A for `WS03-04B`, `WS03-04C`, or `WS03-04D`.
