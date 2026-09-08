# WS03-05B - Conflict-Safe Moderation Review-Case Lifecycle

This pass hardens the existing moderation Review Cases workflow without expanding the product. The surviving admin workflow remains list, detail, internal note, and manual closure. Saved-content and chat moderation remain separate case categories under the same Review Cases workspace.

This document is the final Gate A implementation blueprint for WS03-05B.

## 1. Scope

WS03-05B keeps the existing Review Cases product and adds only the production-safety mechanisms required to prevent stale closure decisions, duplicate writes, duplicate open cases, race-condition corruption, and misleading moderation history.

The final implementation must preserve:

- Review Cases list and detail;
- saved-content moderation cases;
- chat moderation cases in the same Review Cases workspace;
- immutable internal notes;
- manual closure;
- the existing legitimate automatic saved-content closure behavior;
- existing active-admin authorization;
- existing moderation taxonomy, finding identity, chat detection identity, evidence formats, and current/historical source behavior;
- the accepted baseline `create_review_case`, `add_review_case_note`, and `close_review_case` admin-action contracts;
- focused backend, PostgreSQL, concurrency, migration, frontend, and regression validation.

## 1.1 Binary Scope Decisions

The following mechanisms are **NEED** and must be implemented or preserved:

- `case_version` on each review case;
- `expected_case_version` on manual closure only;
- required idempotency keys for note creation and manual closure;
- safe HTTP `409` handling for stale manual closure, idempotency conflicts, and invalid state transitions;
- deterministic primary-target-first locking for every path that creates or mutates a moderation review case;
- category-aware one-open-case uniqueness in PostgreSQL;
- exact moderation target-shape constraints;
- atomic case/event/action writes;
- one immutable event per material case change;
- the resulting case version stored on each event and used as that case's event order;
- immutable notes and immutable events;
- exact automatic lifecycle-transition validation in application code;
- truthful automatic-closure lifecycle attribution in the closure event;
- category-correct source and enforcement linking;
- priority recalculation from current findings/signals;
- compact PostgreSQL constraints and append-only guards;
- deterministic real-PostgreSQL concurrency tests for the real races in this pass.

The following mechanisms are **DO NOT NEED** and must not remain in the final WS03-05B change set:

- assignment, reassignment, or unassignment;
- assignment filters or assigned-user state;
- reopen;
- merge;
- merged-case or linked-case relationships;
- formal note-correction relationships or `corrects_note_id`;
- `expected_case_version` on note creation;
- `creation_reason` on the case;
- persisted case-level `closure_mode`, `closure_rule_id`, or `closure_rule_version`;
- a separate `event_sequence` column in addition to event `case_version`;
- persisted event `actor_kind`;
- persisted event `automation_rule_id` or `automation_rule_version`;
- a separate persisted `trigger_actor_user_id` event column;
- `related_case_id` or `related_event_id`;
- a resolution-reference table;
- `reference_type`, `source_case_id`, or resolution-reference snapshot rows;
- a standalone resolution-reference API collection;
- expanded resolution-history API models;
- a dedicated resolution-reference or expanded history frontend viewer;
- note `note_status`, `edited_at`, `deleted_at`, or `updated_at` fields;
- separate `applied_case_version` and `resulting_case_version` response fields;
- duplicate before/after, priority, source, finding, signal, action, target, or attribution values copied into event JSON when typed rows already contain them;
- a fast pre-lock idempotency replay optimization;
- a generic race-retry framework;
- child-row lock choreography after the primary target and case are locked;
- the comprehensive PL/pgSQL review-workflow state machine;
- the WS03-05B requirement JSON;
- the WS03-05B `TESTING_RECORD.md`;
- WS03-05B requirement markers, checker compliance, trusted-root machinery, or pass-specific traceability infrastructure;
- the branch-added 60-second global backend test-cleanup statement timeout and its WS03-specific assertion.

## 2. Required Behavior

### 2.1 Case Identity And Category Separation

A moderation review case identity is:

- Community Game saved content: `community_game` + `content_moderation` + `target_game_id`;
- Community Game chat: `community_game` + `chat_moderation` + `target_game_id`;
- Need a Sub saved content: `need_a_sub` + `content_moderation` + `target_sub_post_id`;
- Need a Sub chat: `need_a_sub` + `chat_moderation` + `target_sub_post_id`.

PostgreSQL must permit at most one open case for each identity. A content case and a chat case for the same target are distinct and may both be open.

The one-open rule must not constrain unrelated review case types or categories.

For the two moderation case types, PostgreSQL must enforce the exact primary target shape:

- `community_game` has exactly `target_game_id` as its primary moderation target;
- `need_a_sub` has exactly `target_sub_post_id` as its primary moderation target.

A case's type, category, and primary target identity do not change after creation.

An identical source trigger attaches to the existing open case instead of creating another one. New actionable evidence after a prior case has closed creates or uses a new open case. It never reopens or rewrites the closed case.

### 2.2 Case Version

Every moderation review case has a positive integer `case_version`.

Case creation starts at version `1` with the `case_created` event. Every later material case change increments the version exactly once and writes one event carrying that resulting version in the same transaction.

Material changes are:

- finding attached;
- finding cleared;
- chat signal attached;
- chat signal superseded;
- chat signal reactivated;
- internal note added;
- eligible enforcement action linked;
- manual closure;
- legitimate automatic saved-content closure.

`case_version` is the only event-order counter. There is no separate `event_sequence`.

The event table must enforce a positive event `case_version` and uniqueness of `(review_case_id, case_version)`. Application code owns increment-by-one behavior while holding the case lock. Focused PostgreSQL concurrency tests prove production paths do not create duplicate or skipped versions.

### 2.3 Manual Closure Uses Optimistic Concurrency

Manual closure requires the exact positive integer `expected_case_version` from the case detail the administrator reviewed.

The frontend does not display this number as a user-facing workflow field. It stores the version from the detail response and sends it with the close request.

After the primary target and case are locked, the service compares `expected_case_version` with the current case version.

If they differ:

- no closure occurs;
- no admin action is created;
- no event is created;
- the transaction makes no review-case side effect;
- the API returns HTTP `409` with `review_case_version_conflict`;
- the conflict payload contains only the case status and current case version required to trigger a reload;
- the frontend requires a full case-detail reload before another closure attempt.

This prevents an administrator from closing a case after findings, chat signals, notes, enforcement context, or automatic lifecycle state changed after the administrator reviewed the page.

### 2.4 Note Creation Does Not Use Expected Version

Internal notes are append-only. Adding a note does not replace or finalize the case state.

The note request contains:

- `body`;
- `idempotency_key`.

It does not contain `expected_case_version`.

The service locks the primary target and case, rechecks that the case is still open, appends the note, advances the case version, creates the `note_added` event, creates the existing `add_review_case_note` admin action, and commits them atomically.

Two different administrators may add different notes sequentially to the same open case. A note is rejected only when the case has already closed or the request violates the note/idempotency contract.

A note that commits before a manual closure changes the case version, causing a stale closure request to fail and reload. A manual closure that commits first causes a later note request to fail because the case is closed.

### 2.5 Idempotency

Note creation and manual closure require a nonblank bounded idempotency key.

The existing review-case admin-action idempotency index remains the final database safeguard for:

- `create_review_case`;
- `add_review_case_note`;
- `close_review_case`.

For note creation, the idempotency fingerprint is based on the normalized note body.

For manual closure, the idempotency fingerprint is based on the normalized closure outcome, reason, and expected case version.

The service performs the idempotency lookup after the primary target and case locks are held and before applying the mutation.

An exact replay returns the original effect without creating another note, closure, admin action, event, or version increment.

Reusing the same scoped key with a different fingerprint returns HTTP `409` with `review_case_idempotency_conflict` and no side effect.

There is no separate fast replay lookup before locking and no generic idempotency framework beyond the existing admin-action mechanism.

### 2.6 Locking And Transactions

Every production path that creates or mutates a moderation review case uses this lock order:

1. lock the primary Community Game or Need a Sub target row;
2. locate or re-read the exact moderation case under that target;
3. lock that case row for update;
4. validate current state and apply the operation.

A reviewer route that starts from a review-case ID may perform an unlocked read only to discover the primary target. It then locks the target and re-reads the case before deciding.

No surviving operation needs a generic multi-case lock order because merge is removed.

No surviving operation requires a prescribed lock sequence over findings, signals, notes, or admin actions after the primary target and case are locked. The target lock serializes the source and reviewer operations that could otherwise change the case while closure is being decided.

All case projection changes, source changes owned by the operation, event insertion, admin-action insertion, and note insertion commit in one transaction. Any failure rolls the entire operation back.

### 2.7 One-Open-Case Uniqueness

The canonical case migration must replace the content-only moderation indexes with category-aware partial unique indexes:

- Community Game: unique on `target_game_id` + `case_category` for open `community_game` cases in the supported moderation categories;
- Need a Sub: unique on `target_sub_post_id` + `case_category` for open `need_a_sub` cases in the supported moderation categories.

Primary-target locking is the normal concurrency control. The database uniqueness constraint remains the final invariant.

The corrected implementation does not add a generic retry framework for one-open-case conflicts. A uniqueness failure outside the production lock contract is treated as an integrity failure and rolled back.

### 2.8 Open And Closed Lifecycle

The externally visible states remain `open` and `closed`.

An open case can receive findings, chat signals, internal notes, eligible enforcement-action links, and one closure.

A closed case receives no later note, finding/signal state change, enforcement link, resolution rewrite, or reopen transition.

Manual closure keeps the existing outcomes:

- `enforcement_applied`;
- `no_action_needed`;
- `invalid_signal`.

Manual closure records the existing closure outcome, reason, acting administrator, and timestamp on the case and writes the matching immutable `closed` event and `close_review_case` admin action.

`enforcement_applied` is valid only when the case already has an eligible directly linked enforcement action. WS03-05B does not execute enforcement.

### 2.9 Automatic Saved-Content Closure

Existing legitimate automatic closure remains limited to saved-content cases for Community Game and Need a Sub target lifecycle transitions.

Chat moderation cases do not auto-close from target lifecycle changes.

The review-case service owns an explicit set of accepted automatic lifecycle transition tuples. The service validates:

- target type;
- lifecycle action;
- previous target state;
- new target state;
- trigger actor type;
- expected closure outcome;
- required linked admin-action type when the lifecycle transition is an admin enforcement/operational action.

This is direct validation of the existing automatic closure behavior. It is not a generalized workflow engine or policy registry.

The automatic `closed` event keeps only the lifecycle context that is not already represented by typed case/event fields:

- `closure_source = "target_lifecycle"`;
- `lifecycle_action`;
- `previous_target_state`;
- `new_target_state`;
- `trigger_actor_type`.

The existing `actor_user_id` carries the triggering user when one exists, and `admin_action_id` carries the linked action when one exists. No additional actor-kind, automation-rule, or trigger-user columns are added.

The automatic closure transaction advances the case version and creates exactly one `closed` event. If a manual closure wins first, the automatic path observes the closed case and performs no second closure. If the automatic closure wins first, a stale manual closure fails its expected-version check.

### 2.10 Source And Enforcement Linking

Saved-content findings attach only to saved-content cases for the exact target identity.

Chat signals attach only to chat moderation cases for the exact target identity.

Target-derived enforcement linking requires the expected moderation category and exact target identity. It never selects whichever open case happens to sort first.

Finding and chat-signal current-state changes advance the case version and write the corresponding event.

Case priority is recalculated from current linked findings/signals. Historical or superseded source records do not permanently keep a case at an elevated priority.

### 2.11 Minimal Immutable History

The existing `admin_review_case_events` table remains the review-case history mechanism. No second history store is added.

The surviving event types are:

- `case_created`;
- `finding_attached`;
- `finding_cleared`;
- `signal_attached`;
- `signal_superseded`;
- `signal_reactivated`;
- `note_added`;
- `enforcement_action_linked`;
- `closed`.

Each event retains only the typed references it needs:

- review case;
- case version;
- actor user when present;
- admin action when present;
- finding when the event concerns a finding;
- signal when the event concerns a signal;
- note when the event concerns a note;
- created timestamp;
- narrowly scoped event metadata only for automatic lifecycle context that is not represented elsewhere.

Event ordering is `case_version` ascending. `created_at` remains the event timestamp but is not a second sequence authority.

The event table does not add:

- `event_sequence`;
- `actor_kind`;
- `related_case_id`;
- `related_event_id`;
- `automation_rule_id`;
- `automation_rule_version`;
- `trigger_actor_user_id`.

Source event metadata does not duplicate finding type, risk area, source field, source identity, priority before/after, action type, or typed IDs already available through the referenced records.

Manual closure does not copy case before/after projections into event JSON.

Raw target content, message text, finding evidence, note bodies, scanner expressions, credentials, SQL parameters, and exception payloads never enter review-case event metadata or conflict payloads.

### 2.12 No Resolution-Reference Table

WS03-05B does not create or retain `admin_review_case_resolution_references`.

The closure evidence state is already represented by:

- the closed case's immutable source associations;
- ordered finding attach/clear events;
- ordered signal attach/supersede/reactivate events;
- enforcement-action link events;
- the final `closed` event and case projection.

Because closed cases receive no later source mutation or enforcement linking, this ordered event history reconstructs which source state existed when the close event occurred without a second snapshot table.

Migration `0066_create_admin_review_case_resolution_references_table.py`, its model/export code, service builders, schemas, frontend presentation, and tests are removed from the branch.

### 2.13 Immutable Notes

A review-case note contains only:

- ID;
- review-case ID;
- author user ID;
- body;
- created timestamp.

The note table does not retain dormant edit/delete state. Remove:

- `corrects_note_id`;
- `note_status`;
- `edited_at`;
- `deleted_at`;
- `updated_at`.

There is no note update route and no note delete route.

A compact PostgreSQL immutability trigger rejects direct `UPDATE` and `DELETE` of review-case notes.

A later clarification is a new ordinary immutable note.

### 2.14 Compact Database Integrity

PostgreSQL owns only invariants that must remain true regardless of application caller:

- finite case type/status/category/priority/outcome values already owned by the schema;
- exact Community Game and Need a Sub moderation target shapes;
- positive case version;
- category-aware one-open-case uniqueness;
- valid open/closed closure shape using the existing case closure fields;
- immutable case type/category/primary target identity;
- no mutation of a completed closed-case projection;
- finite event types;
- event-type-specific direct reference shape;
- positive event case version;
- unique `(review_case_id, case_version)`;
- event immutability;
- note immutability;
- foreign-key integrity that preserves review history.

PostgreSQL does not own reviewer workflow eligibility, expected-version decisions, idempotent replay decisions, automatic lifecycle policy, category selection logic, or source reconciliation state machines.

The comprehensive `validate_admin_review_case_event_insert()` PL/pgSQL function is removed completely and is not replaced by another workflow validator.

## 3. API Contract

### 3.1 Final Routes

The Review Cases API contains exactly these pass-owned routes:

- `GET /admin/review-cases`;
- `GET /admin/review-cases/{review_case_id}`;
- `POST /admin/review-cases/{review_case_id}/notes`;
- `POST /admin/review-cases/{review_case_id}/close`.

All four use the existing active-admin authorization dependency.

Assignment, reopen, and merge routes are absent from route registration and OpenAPI.

### 3.2 List And Detail

List and detail preserve the existing case/target/finding/signal/note/event information required by the workspace.

The detail contract adds `case_version` so manual closure can send the exact reviewed version.

The corrected API does not expose:

- assignment fields;
- merge fields;
- linked cases;
- note correction relationships;
- `creation_reason`;
- persisted closure mode/rule fields;
- `event_sequence`;
- event actor-kind/automation-rule fields;
- resolution references;
- expanded resolution history.

### 3.3 Note Request

`POST /admin/review-cases/{id}/notes` accepts:

- `body`;
- `idempotency_key`.

It rejects extra fields, including `expected_case_version` and `corrects_note_id`.

### 3.4 Close Request

`POST /admin/review-cases/{id}/close` accepts:

- `outcome`;
- `reason`;
- `expected_case_version`;
- `idempotency_key`.

`expected_case_version` is a strict positive integer.

### 3.5 Mutation Responses And Conflicts

Note and close mutation responses keep:

- the resulting review-case detail;
- the created note for note creation;
- the existing audit action ID;
- `idempotent_replay`.

They do not add separate `applied_case_version` or `resulting_case_version` fields because the review case and event already carry the authoritative version.

The surviving conflict codes are:

- `review_case_version_conflict` for stale manual closure;
- `review_case_idempotency_conflict` for scoped key reuse with different input;
- `review_case_transition_conflict` when the requested surviving mutation is no longer legal, such as adding a new note to a closed case.

Case-creation uniqueness conflicts are internal integrity failures, not a new admin API contract.

## 4. Frontend

The Review Cases frontend keeps:

- list and detail;
- open/closed filtering;
- content/chat category filtering;
- target filtering;
- findings;
- chat signals;
- immutable notes;
- manual closure;
- existing closure summary;
- compact event activity;
- in-flight mutation disabling;
- stale-close conflict reload behavior.

The frontend stores `case_version` from detail and includes it only in the manual close payload.

The note payload does not include case version.

On `review_case_version_conflict`, the UI blocks another closure submission until the full detail request succeeds. The frontend never increments case version locally.

Remove:

- assignment filter/state/display/control;
- assignee lookup;
- reopen controls;
- merge controls;
- merge destination lookup;
- linked-case navigation;
- note correction selectors/display;
- expanded resolution history;
- `AdminResolutionReferenceList.js`;
- resolution-reference helpers or projections;
- dead API clients, lifecycle helpers, and CSS supporting rejected behavior.

No new frontend framework or admin workspace is introduced.

## 5. Canonical Migration Changes

Pickup Lane is pre-production and uses the accepted clean-rebuild canonical-migration policy. Gate B edits the canonical owners directly.

### 5.1 `0004_create_admin_actions_table.py`

Preserve:

- `create_review_case`;
- `add_review_case_note`;
- `close_review_case`;
- their accepted policy/display contracts;
- the existing review-case idempotency index membership.

Remove branch-added:

- `assign_review_case`;
- `reopen_review_case`;
- `merge_review_case`;
- their policy/display/service/test support.

### 5.2 `0053_create_admin_review_cases_table.py`

Add/keep only the required WS03-05B hardening:

- positive `case_version` with initial value `1`;
- exact Community Game and Need a Sub target-shape checks;
- category-aware one-open moderation indexes;
- primary moderation target foreign-key behavior that does not silently erase the case identity;
- a compact case-row guard preventing identity rewrite and later mutation of the completed closed projection.

Do not add/retain:

- `creation_reason`;
- `closure_mode`;
- `closure_rule_id`;
- `closure_rule_version`;
- assignment fields;
- merge fields.

### 5.3 `0057_create_admin_review_case_notes_table.py`

Keep only the immutable-note fields in section 2.13.

Remove:

- `corrects_note_id`;
- `note_status`;
- `edited_at`;
- `deleted_at`;
- `updated_at`.

Add the compact note update/delete rejection trigger.

### 5.4 `0059_create_admin_review_case_events_table.py`

Keep the existing event table and reduce it to the required history contract.

Add/keep:

- the surviving event types;
- event `case_version`;
- positive version check;
- unique `(review_case_id, case_version)`;
- direct finding/signal/note/admin-action references required by surviving event types;
- event-specific reference-shape checks;
- history-preserving foreign keys;
- event update/delete rejection trigger.

Remove/do not add:

- `event_sequence`;
- `actor_kind`;
- `related_case_id`;
- `related_event_id`;
- `automation_rule_id`;
- `automation_rule_version`;
- `trigger_actor_user_id`;
- assignment/reopen/merge event types;
- the comprehensive PL/pgSQL event-insert workflow validator.

### 5.5 Remove `0066`

Delete `0066_create_admin_review_case_resolution_references_table.py` from this branch.

There is no replacement resolution-reference migration.

### 5.6 Migration Support

Keep the existing migration/safety infrastructure aligned with the reduced SQL actually retained by these canonical migrations.

Remove SQL-safety allowances, parser expectations, and tests that exist only for the rejected comprehensive PL/pgSQL state machine or removed resolution-reference table.

A clean rebuild must leave one valid Alembic head and model/live-schema parity.

## 6. Backend Service Changes

`backend/services/admin_review_service.py` remains the owner of reviewer note/close behavior, case locking, case-version advancement, event creation, and automatic lifecycle validation.

The existing saved-content and chat source services use the same target-first case mutation contract.

Gate B must:

- remove assignment/reopen/merge/correction/history/reference service code;
- preserve accepted `create_review_case` behavior;
- add target-first locking to every moderation case create/mutate path;
- advance case version exactly once for each material event;
- require expected version only for manual close;
- preserve required note/close idempotency;
- remove pre-lock replay optimization added by PR #176;
- remove generic retry machinery added for races that target locking now serializes;
- preserve database uniqueness as the final one-open invariant;
- validate accepted automatic lifecycle transitions centrally;
- keep automatic closure event metadata limited to section 2.9;
- remove duplicate source/priority/before/after event metadata;
- keep category-correct finding, signal, and enforcement linking;
- recompute priority from current sources;
- prevent all source/case mutation against a closed historical case.

## 7. Failure And Race Behavior

### 7.1 Concurrent Case Creation

Two transactions attempt to create the same target/category case.

Required result:

- target-first locking serializes the creation decision;
- one open case exists;
- the second transaction reuses the case created by the first after it obtains the target lock;
- no duplicate case or duplicate creation event appears.

### 7.2 Concurrent Different Notes

Two administrators add different notes to the same open case.

Required result:

- both requests serialize through target/case locking;
- both notes may commit in order;
- each note receives its own case version and event;
- neither request fails merely because the other note committed first.

### 7.3 Duplicate Note Retry

The same note request is retried with the same idempotency key.

Required result:

- one note exists;
- one note event exists;
- one admin action exists;
- one version increment occurs;
- replay returns the original effect.

### 7.4 Note Versus Manual Closure

A note and a manual closure overlap.

Required result:

- if the note commits first, it advances the case version and the stale close request returns `409`;
- if the close commits first, the later note sees a closed case and returns `409`;
- no note is appended after closure;
- no partial loser side effect remains.

### 7.5 Finding Or Signal Versus Manual Closure

A finding/signal state change overlaps a manual closure.

Required result:

- target-first locking serializes the operations;
- if the source change commits first, case version advances and stale close returns `409`;
- if close commits first, the old case remains historical and later actionable evidence follows the new-open-case rule;
- no source crosses content/chat category boundaries.

### 7.6 Manual Versus Automatic Closure

Manual and legitimate automatic closure overlap.

Required result:

- one closure commits;
- if automatic closure commits first, manual close returns a version conflict;
- if manual closure commits first, the automatic path observes closed state and performs no second closure;
- one final closed projection and one close event remain.

### 7.7 Enforcement Link Versus Closure

An enforcement link overlaps closure.

Required result:

- target-first locking provides one serial order;
- `enforcement_applied` is accepted only when an eligible linked enforcement action exists in the locked current case state;
- no enforcement action attaches to the wrong category case.

### 7.8 Idempotency-Key Mismatch

The same scoped key is reused with different normalized input.

Required result:

- HTTP `409`;
- no case, note, event, or admin-action side effect.

### 7.9 Direct History Mutation

SQL attempts to update or delete an existing review-case note or event.

Required result:

- PostgreSQL rejects the statement;
- the existing history remains unchanged.

### 7.10 Sensitive Error Path

A mutation fails around a case containing private moderation content.

Required result:

- responses/logs contain safe identifiers, finite state, and error category only;
- raw target text, chat text, evidence, note body, SQL parameters, and sensitive exception payloads are absent.

## 8. Testing

Testing is risk-based and uses the owning layer. No WS03-specific compliance or evidence framework is created.

### 8.1 Schema And Service Tests

Cover:

- active-admin access to list/detail/note/close;
- strict close `expected_case_version` validation;
- note contract without expected version;
- required idempotency keys;
- note body and close reason bounds;
- finite closure outcomes;
- extra-field rejection;
- closed-case note rejection;
- closed-case second-close rejection except exact idempotent replay;
- exact replay and mismatched idempotency reuse;
- `enforcement_applied` precondition;
- automatic lifecycle transition validation;
- category-correct source/action selection;
- priority recomputation from current source rows.

### 8.2 PostgreSQL Tests

Use real PostgreSQL to prove:

- exact moderation target shapes;
- category-aware one-open uniqueness;
- content/chat separation for the same target;
- positive case version;
- positive event case version;
- unique `(review_case_id, case_version)`;
- event-specific reference shape;
- case identity immutability;
- completed closed-projection immutability;
- note update/delete rejection;
- event update/delete rejection;
- transaction rollback leaves no partial state.

There are no tests for creation reason, event sequence, actor kind, automation rule/version fields, resolution references, or the removed PL/pgSQL workflow validator because those mechanisms do not exist in the corrected design.

### 8.3 Deterministic Concurrency Tests

Use independent PostgreSQL sessions and explicit synchronization barriers, not sleeps, for:

- same target/category case creation versus case creation;
- different note versus different note;
- note versus manual closure;
- finding change versus manual closure;
- signal change versus manual closure;
- manual closure versus automatic lifecycle closure;
- enforcement linking versus closure.

Each test asserts the committed result, final case version, exact ordered events by event `case_version`, row counts, category ownership, and absence of partial loser effects.

### 8.4 API Contract Tests

Prove:

- final four-route inventory;
- assignment/reopen/merge routes absent;
- note request does not accept `expected_case_version` or correction fields;
- close requires `expected_case_version`;
- stale close returns safe `review_case_version_conflict`;
- idempotency mismatch returns safe `review_case_idempotency_conflict`;
- state conflict returns `review_case_transition_conflict`;
- list/detail contain `case_version` but do not expose rejected assignment/merge/correction/history/reference fields;
- error payloads do not leak moderation evidence or note text.

### 8.5 Frontend Tests

Existing Node tests cover:

- status/category/target filters;
- note payload without expected version;
- close payload with exact current case version;
- compact event ordering by case version;
- stale-close conflict blocking/reload;
- absence of assignment/reopen/merge/correction/linked-case/resolution-reference/history helpers and render paths.

Run the production frontend build and existing lint/static validation.

### 8.6 Migration And Regression Validation

Run:

- import/compile validation for affected backend modules;
- `git diff --check`;
- Alembic single-head check;
- clean base-to-head upgrade against the dedicated test PostgreSQL database;
- repository-supported downgrade/re-upgrade or clean rebuild proof;
- model/migration/live-schema parity checks already owned by the repository;
- focused review-case tests;
- affected saved-content moderation tests;
- affected chat moderation tests;
- affected enforcement/lifecycle integration tests;
- deterministic concurrency tests;
- frontend unit/static/build checks;
- the complete configured backend regression suite once after focused validation passes.

Do not add the PR #176 60-second global cleanup statement timeout. Restore the accepted baseline cleanup behavior while adding the new table inventory entries required by the corrected final schema. Because the resolution-reference table is removed, it is not added to the cleanup inventory.

## 9. Files And Branch Cleanup

Gate B must remove branch-only code supporting rejected scope across:

- models and model exports;
- schemas and schema exports;
- routes;
- services;
- admin-action policy/display registries;
- migration SQL and SQL-safety allowances;
- frontend API clients;
- lifecycle helpers;
- React components;
- CSS;
- test fixtures/helpers;
- tests;
- WS03 requirement JSON and testing-record artifacts.

The corrected implementation must not leave dead imports, stale constants, inactive schemas, unreachable service functions, unused CSS, obsolete event types, or migration expectations for removed features.

## 10. Done When

- [ ] The Review Cases product still consists of list, detail, note, and close under the existing active-admin guard.
- [ ] Saved-content and chat cases remain separate and both appear in Review Cases.
- [ ] Each moderation target/category has at most one open case.
- [ ] `case_version` advances once per material event and is the only event-order counter.
- [ ] Manual close requires the exact reviewed case version and returns a safe `409` when stale.
- [ ] Note creation does not require an expected version and different concurrent notes can both append in serial order while the case remains open.
- [ ] Note and close idempotent retries create no duplicate effects.
- [ ] Target-first locking serializes case creation, source mutation, notes, enforcement linking, and closure without a generic retry framework.
- [ ] Case identity and completed closure projection are protected from rewrite.
- [ ] Notes and events are append-only through application code and direct SQL.
- [ ] Automatic content closure validates the accepted lifecycle transition and records only the required lifecycle context in the close event.
- [ ] Closed cases receive no later source, note, enforcement, or state mutation.
- [ ] Category-correct source and enforcement linking prevents content/chat cross-linking.
- [ ] Case priority reflects current source state rather than historical maximums.
- [ ] No resolution-reference table or migration 0066 remains.
- [ ] No assignment, reopen, merge, linked-case navigation, formal correction, expanded history UI, resolution-reference UI/API, `creation_reason`, separate event sequence, actor-kind/automation-rule fields, or duplicate workflow state machine remains.
- [ ] The accepted baseline `create_review_case` admin-action contract remains intact.
- [ ] WS03-specific requirement/test/compliance machinery is removed.
- [ ] The branch-added 60-second global backend test cleanup timeout is removed.
- [ ] Canonical migrations, models, API contracts, frontend contracts, and live PostgreSQL schema agree.
- [ ] Focused, real-PostgreSQL concurrency, migration, frontend, affected regression, and complete backend validation pass.

Gate B stops after implementation and validation. It does not stage, commit, push, merge, update PR #176, modify the corrected master/workflow/execution-register documents, or begin Gate C.
