# WS03-04C Relationship Authorization Testing Record

## At A Glance

| Field | Value |
|---|---|
| Owning pass | `WS03-04C - Game, community, roster, chat, and Need-a-Sub relationship authorization` |
| Trusted test scope | `backend/tests/workflows/game_community_roster_chat_need_a_sub_relationship_authorization` |
| Requirement declaration | `backend/tests/support/requirements/ws03_04c.json` |
| Authoritative sources | Frozen WS03-04C plan, approved WS03-04 intake, accepted WS03-04A matrix artifact, accepted WS03-04B sibling evidence, and current source |
| Evidence layers | Local pytest API/service tests, PostgreSQL-backed persistence assertions, local provider fakes at app-owned boundaries, matrix/traceability checks, and governance deferrals |

## 1. Scope

This record covers trusted local proof for ordinary-user relationship
authorization across games, community games, checkout, bookings, rosters,
waitlists, game chat/messages, My Games, public venue/image reads, and
Need-a-Sub posts, requests, status history, positions, and scoped chat.

The scope proves current source behavior in the local test application and
database. It does not claim deployed, live-provider, production-runtime,
browser, migration, real concurrency, Stripe webhook, durable payment/refund
reconciliation, admin/high-risk breadth, sensitive admin data, export/unmask,
or read-audit proof.

## 2. Requirements

| Requirement ID | Meaning In This Scope | Evidence State |
|---|---|---|
| `WS03-04C-R1` | Accepted matrix inventory and owner/drift guard for C-owned route keys | pytest |
| `WS03-04C-R2` | Dependency and verified-email distinction for public reads, relationship reads, and verified mutations | pytest |
| `WS03-04C-R3` | Public/listable resource visibility and private-resource concealment | pytest |
| `WS03-04C-R4` | Authenticated current-user relationship reads | pytest |
| `WS03-04C-R5` | Game roster, checkout, guest, cancel, and host-edit mutation authorization | pytest |
| `WS03-04C-R6` | Community publish/detail host ownership and host-payment-text concealment | pytest |
| `WS03-04C-R7` | Game chat membership, sender, read-state, and removed-message boundaries | pytest |
| `WS03-04C-R8` | Need-a-Sub owner, requester, public viewer, lifecycle, and chat-member boundaries | pytest |
| `WS03-04C-R9` | Field and mass-assignment boundaries for C-owned writes | pytest |
| `WS03-04C-R10` | Default-deny, 401/403/404, wrong-ID, and rejected-mutation side-effect proof | pytest |
| `WS03-04C-R11` | Requirement, marker, matrix, and testing-record traceability | pytest and checker |
| `WS03-04C-R12` | Deferred admin/provider/runtime/governance closure outside C | deferred/governance with zero pytest mappings |

## 3. Invariants And Risks

| Requirement(s) | Invariant | What Could Go Wrong | Consequence / Risk | Safeguard | Owning Test Layer |
|---|---|---|---|---|---|
| `R1`, `R11` | C route inventory, owner fields, and pytest markers match the frozen plan and accepted matrix. | Route drift or marker drift silently changes what C proves. | Authorization gaps could be hidden by stale evidence. | Matrix scope and marker traceability tests. | workflow |
| `R2` | Public reads, authenticated relationship reads, active-user reads, and verified-user mutations retain the approved dependency distinction. | An unverified user mutates relationship state or a public route becomes private-only by accident. | Unauthorized writes or broken public access. | Dependency classification tests against the current FastAPI route table plus behavioral verified/unverified examples. | workflow |
| `R3`, `R6` | Public resources expose only public/listable records and host-private resources remain concealed unless the current relationship permits access. | Hidden games, inactive venues, hidden images, hidden payment text, or removed posts leak publicly. | Privacy and payment-instruction exposure. | Public visibility and private cache tests. | workflow |
| `R4` | Current-user read routes bind returned rows to the authenticated user or relationship. | Caller-supplied IDs widen reads to another user's booking, participant, waitlist, or request. | Cross-user data exposure. | Current relationship read tests with own and foreign rows. | workflow |
| `R5`, `R6`, `R8` | Successful mutations persist only the authorized current user's or host's intended state. | A player acts as host, a host edits another game, or a requester changes another request. | Roster, community-game, checkout, or Need-a-Sub state corruption. | Mutation tests prove persisted owner/host/requester state. | workflow |
| `R7`, `R8` | Chat sender and read-state users are derived from the authenticated user and membership relationship. | A caller spoofs sender/read-state user IDs or sends in a chat they cannot access. | Private conversation exposure or impersonation. | Game chat and Need-a-Sub chat tests. | workflow |
| `R9`, `R10` | Caller-controlled fields cannot set server-owned identity, ownership, payment/provider, moderation, visibility, status, or read-state fields. | Body fields overwrite protected state or rejected calls leave rows behind. | Privilege escalation or hidden side effects after denial. | Schema extra-field tests and no-side-effect assertions. | workflow |
| `R12` | Admin/high-risk, provider-runtime, and final parent-gap closure stay outside C. | C evidence is overclaimed as final parent or provider proof. | Reviewer approves a broader security claim than this pass proves. | Requirement declaration, zero pytest mappings, and record deferrals. | governance |

## 4. Scenario Discovery

| Dimension | Relevant Values / Classes | Coverage Decision | Reason |
|---|---|---|---|
| Actors | anonymous, invalid token, current user, owner, host, participant, requester, confirmed chat member, pending user, unrelated user, ordinary non-admin | covered or grouped | These actor classes define C ordinary-user authorization. D-owned admin breadth is deferred. |
| States / lifecycle | public/hidden, active/inactive/removed, published, open/closed chat, pending/confirmed/canceled Need-a-Sub requests, joinable/blocked mutation states | covered or grouped | Finite source states are classified in the matrix/lifecycle test and representative behavior tests. |
| Actions | list/detail reads, status reads, create/update/cancel/join/leave/guest mutations, chat read/message/read-state operations | covered | They match the 15 route families and 64 route keys frozen for C. |
| Inputs / boundaries | caller-supplied user IDs, actor IDs, owner IDs, payment/provider fields, status fields, moderation fields, hidden filters, wrong object IDs | covered | These are the fields most likely to widen relationship authorization. |
| Time | current publish/join windows and current verified-auth dependency | grouped | C uses current source behavior and recent synthetic auth timestamps. Genuine race/time-boundary proof remains outside C where frozen. |
| Dependencies | FastAPI route table, auth dependency graph, PostgreSQL test database, local provider fakes for authorization ordering | covered | The tests inspect current app dependencies and assert persisted state through the test DB. |
| Concurrency / idempotency | genuine database races and durable provider idempotency | deferred | Frozen plan assigns these to later WS04/WS05 evidence. |
| Authorization / privacy / security | public/private resource visibility, current-user binding, verified-user mutation, chat membership, default deny, no side effects | covered | These are the core C risk classes. |
| Persistence / rollback | successful roster/community/chat/Need-a-Sub writes, rejected no-row/no-provider-call/no-state-change behavior | covered | Mutation tests assert durable rows and named prohibited side effects. |
| Recovery | provider reconciliation and operational recovery | deferred | Later provider/runtime work owns this evidence. |

## 5. Failure Transformations

| Transformation | Applies? | Scenario / Boundary | Evidence Decision |
|---|---|---|---|
| omit | yes | unauthenticated protected reads and writes | 401 tests cover missing credentials. |
| corrupt | yes | invalid bearer token | 401 test covers invalid credentials. |
| duplicate | yes | duplicate/blocked roster or lifecycle state | grouped through current source lifecycle and no-side-effect checks; durable concurrency remains deferred. |
| expire / revoke | limited | current verified-user dependency and active-account predecessor behavior | covered through accepted predecessor compatibility and local verified/unverified proof. |
| tamper | yes | caller-supplied ownership, actor, sender, read-state, status, moderation, and provider fields | field-boundary and wrong-relationship tests cover. |
| retry | limited | repeated/durable provider operations | deferred to WS05 except local provider-call ordering proof. |
| race | no | genuine concurrent booking/roster/payment/Need-a-Sub updates | deferred to WS04. |

## 6. Selected Evidence

| Requirement(s) | Scenario Group | Proof Layer | Current Evidence | Why This Is Enough / Not Enough |
|---|---|---|---|---|
| `R1`, `R2`, `R11`, `R12` | Matrix scope, current route table, dependency classification, requirement declaration, marker mapping, zero deferred mappings | pytest and checker | `test_matrix_scope_and_dependencies_contract.py`; domain and suite checker | Proves current app routes still match the accepted C matrix and markers do not remap deferred governance work into pytest. |
| `R3`, `R6`, `R10` | Public game, browse, venue, game-image, venue-image, and Need-a-Sub visibility plus hidden/private cache behavior | pytest/API/PostgreSQL | `test_public_visibility_and_private_cache_contract.py` | Proves public rows are listable, non-public rows are omitted/concealed, and relationship-private responses use private cache headers where source sets them. |
| `R4`, `R10` | Booking, checkout status, participant, waitlist, My Games, Need-a-Sub mine/request/history current-user reads | pytest/API/PostgreSQL | `test_current_relationship_reads_contract.py` | Proves current-user binding and wrong-user ID denial for representative equivalent read classes. |
| `R5`, `R10` | Join, checkout, guest, cancel, host-edit, verified-user, host/player role, provider-ordering, rejected side effects | pytest/API/PostgreSQL/provider fake | `test_game_roster_checkout_host_mutations_contract.py` | Proves successful writes persist expected relationship state and rejected writes do not create protected rows or provider calls. |
| `R6`, `R10` | Community publish, community detail host edit, publish-attempt owner status, hidden host-payment text | pytest/API/PostgreSQL | `test_community_publish_detail_contract.py` | Proves current verified host binding, owner-only edit/status reads, and public concealment of hidden payment text. |
| `R7`, `R10` | Game chat ensure, messages, read-state, sender binding, removed-message concealment, nonmember/closed-chat denial | pytest/API/PostgreSQL | `test_game_chat_message_membership_contract.py` | Proves chat access follows membership and the authenticated sender/read user, not caller-controlled IDs. |
| `R8`, `R10` | Need-a-Sub public positions, owner/requester lifecycle, confirmed chat, read-state, sender binding | pytest/API/PostgreSQL | `test_need_a_sub_relationship_contract.py` | Proves owner/requester/confirmed-member classes without testing every equivalent status permutation one by one. |
| `R9`, `R10`, `R11` | Write-schema extra-field rejection, server-controlled field inventory, default deny | pytest/API/PostgreSQL | `test_field_assignment_and_default_deny_contract.py` | Proves C write schemas forbid protected fields and representative rejected calls leave no named prohibited rows. |

## 7. Important Side Effects

| Operation / Scenario | Required Successful Effects | Prohibited Effects On Rejection / Failure | Rollback / Idempotency Expectation |
|---|---|---|---|
| Game join | Booking and participant rows bind to the current verified user. | Unverified join creates no booking, participant, waitlist, payment, or notification changes for the rejected game. | No duplicate/race proof claimed. |
| Host guest and host edit | Host guest rows and allowed host-edit fields persist for the current host. | Wrong host cancel/edit does not cancel the game, change host identity, or create payment/booking side effects. | Durable concurrency proof deferred. |
| Checkout payment intent | Local authorization rejects unverified users before payment rows or provider calls. | No provider fake call and no relationship rows for the rejected game. | Provider idempotency/reconciliation deferred. |
| Community publish/detail | Successful free publish creates a host-owned community game, host participant, community detail, and waived host fee. | Unverified publish creates no game/payment/publish-attempt rows; wrong-host detail edit is rejected. | Live provider proof deferred. |
| Game chat/message | Successful message persists with current sender; read-state persists for current user. | Nonmember and closed-chat writes do not add messages. | Admin moderation closeout deferred. |
| Need-a-Sub lifecycle/chat | Owner/requester actions and confirmed chat message persist to the correct current relationship. | Wrong owner, unrelated member, and wrong chat ID do not mutate request/chat state. | Durable race/idempotency proof deferred. |

## 8. Gaps / Deferrals / Covered Elsewhere

| Requirement / Scenario | State | Reason | Owner / Later Evidence |
|---|---|---|---|
| `WS03-04C-R12` | deferred | Admin/high-risk authorization breadth, final parent-gap disposition, provider-runtime evidence, durable reconciliation, true concurrency, sensitive admin data, export/unmask, read-audit, and moderation closeout are outside C. | `WS03-04D`, `WS04`, `WS05`, `WS09`, `WS10`, `WS03-05` |
| B-owned self-account/financial surfaces | covered elsewhere | WS03-04B already owns account, notification, inbox, saved-card, credit, payment, refund, and host-fee authorization. | Accepted WS03-04B evidence |
| A matrix foundation | covered elsewhere | C consumes the accepted matrix and proves no C route drift; it does not redesign the matrix artifact. | Accepted WS03-04A evidence |
| Live provider/deployed/runtime behavior | deferred | This record uses local fakes and local source/test evidence only. | Later provider/runtime gates |

## 9. Adequacy Conclusion

The selected local evidence is adequate for the frozen WS03-04C Gate B scope:
`R1` through `R11` have executable evidence, and `R12` remains deferred
governance with zero pytest mappings.

Checker `PASS` is structural compliance only. Human review must still decide
whether the scenarios above adequately prove the frozen authorization contract.

This record contains no literal credentials, credential-bearing URLs, raw
sensitive logs or unredacted errors, provider-private values, personal or
payment data, local machine paths, usernames, session state, internal chat
material, or other prohibited sensitive values.

Final validation results are recorded in the Gate B handoff report.
