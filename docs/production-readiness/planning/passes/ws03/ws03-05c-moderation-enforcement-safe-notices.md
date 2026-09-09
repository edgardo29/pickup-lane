# WS03-05C - Moderation Enforcement And Safe Notices

This pass makes Pickup Lane's existing moderation enforcement actions state-correct, replay-safe, reversible where the product already supports reversal, and consistently paired with safe user-facing communication.

This document is the corrected Gate A engineering blueprint for this pass.

## 1. What This Work Does

Pickup Lane already supports account suspension, hosting restriction, content and joining controls, chat-message removal, and corresponding restoration actions. These paths already use domain services, row locking in several action families, idempotency keys, admin action records, and notifications, but their preconditions, replay behavior, conflict handling, and notice safety are not yet consistent.

This work establishes one production-safety contract for those existing actions. The server validates the exact target and current state under lock, records the committed transition truthfully, applies the mutation and its audit/review-case effects atomically, and creates the required safe user notice or notification whenever an intended recipient exists.

The pass covers these existing moderation and safety actions:

- account suspension and unsuspension;
- hosting restriction and restoration;
- Community Game visibility, joining, cancellation, and payment-text moderation;
- Need a Sub post visibility and removal;
- game-chat message removal and restoration for official and Community Games;
- Need a Sub chat-message removal and restoration.

Marking a message reviewed, flagging content for review, resolving a review case, ordinary game or post lifecycle changes, financial remedies, and account deletion are not enforcement actions in this pass.

Existing route authorization, active-admin enforcement, recent-authentication policy, and `admin_action_policy.py` remain authoritative. This pass does not add another role, permission, or moderation-action hierarchy.

Review-case linking continues to use the accepted WS03-05B contract. WS03-05C does not redesign review cases, add lifecycle states, or expand Review Cases product behavior.

Notices remain immediate in-app database records. No current action requires delayed delivery, so this pass does not add jobs, delivery retries, delivery channels, scheduling, or a generalized notice lifecycle.

This pass does not add an appeal product. Where user follow-up is appropriate, safe notice copy may direct the user to contact support.

## 2. What Must Be True

These requirements define the behavior every covered action must satisfy. The mutation, audit history, review-case effects, and user communication must remain consistent during retries, stale requests, competing actions, failures, and reversals.

### 2.1 Authorization And Input

- Every action uses the existing route authorization and recent-authentication requirement assigned to that route.
- Service entry points continue to enforce active-admin state where they do today.
- `admin_action_policy.py` remains the single definition of valid admin action and target shapes. No second permission or moderation-action registry is introduced.
- Nested resources must belong to the parent identified by the route. A game-chat message cannot be acted on through another game, and a Need a Sub chat message cannot be acted on through another post.
- Mutation request schemas reject unexpected fields.
- Reasons and idempotency keys must be strings, remain nonblank after normalization, and stay within their existing accepted limits.
- The internal admin reason is required for restrictive and restorative enforcement actions where the current action contract requires one.
- The internal reason is retained only in restricted admin/audit data and is never copied into user-facing notice text, notification text, API errors, or logs.

### 2.2 Action And State Matrix

The matrix below is the complete transition set owned by this pass. Preconditions are evaluated from locked authoritative state. Recorded `before` values are derived from that same locked state rather than from an earlier unlocked read.

| Action | Required current state | Result |
|---|---|---|
| Suspend account | Account is active and not deleted or pending deletion; suspension preview is current; last-active-admin and future-official-host protections pass | Account becomes suspended |
| Unsuspend account | Account is suspended and not deleted or pending deletion | Account becomes active |
| Restrict hosting | Hosting is eligible; account is not deleted or pending deletion; hosting-impact preview is current | Hosting becomes restricted |
| Restore hosting | Hosting is restricted; account is not deleted or pending deletion | Hosting becomes eligible |
| Hide Community Game | Exact target is a Community Game, is not cancelled or removed, and is visible | Public visibility becomes hidden |
| Restore Community Game | Exact target is a Community Game, is not cancelled or removed, and is hidden | Public visibility becomes visible |
| Pause Community Game joining | Exact target is an active Community Game whose joining state is open | Joining becomes paused |
| Resume Community Game joining | Exact target is an active Community Game whose joining state is paused | Joining becomes open |
| Cancel Community Game | Exact target is an active Community Game and satisfies the existing cancellation preconditions | Existing cancellation workflow completes and game becomes cancelled |
| Hide Community Game payment text | Payment snapshot exists, contains payment text, and its moderation state is visible | Payment-text moderation state becomes hidden |
| Restore Community Game payment text | Payment snapshot exists, contains payment text, and its moderation state is hidden | Payment-text moderation state becomes visible |
| Hide Need a Sub post | Post is not removed and is visible | Public visibility becomes hidden |
| Restore Need a Sub post | Post is not removed and is hidden | Public visibility becomes visible |
| Remove Need a Sub post | Post is not already removed and satisfies existing removal preconditions | Existing removal workflow completes, including current request closures, and post becomes removed |
| Remove game-chat message | Message belongs to routed official or Community Game and is visible | Message becomes removed and reviewed with `removed_source = admin` |
| Restore game-chat message | Message belongs to routed official or Community Game, is removed, and `removed_source = admin` | Message becomes visible and reviewed while retaining removal/restoration history |
| Remove Need a Sub chat message | Message belongs to routed post and is visible | Message becomes removed and reviewed with `removed_source = admin` |
| Restore Need a Sub chat message | Message belongs to routed post, is removed, and `removed_source = admin` | Message becomes visible and reviewed while retaining removal/restoration history |

Restoration never revives a cancelled, removed, deleted, sender-removed, or system-removed resource.

Completed and expired Community Games may still have visibility moderated where the existing product permits historical visibility control, but joining cannot be resumed after the game is no longer active.

A non-removed Need a Sub post may remain subject to visibility moderation because its content can remain visible in historical and administrative surfaces.

Chat restoration is valid only for a message whose current removal was performed by an administrator. Sender-removed and system-removed messages are not restorable through these admin actions.

### 2.3 Idempotency, Conflicts, And History

- Idempotency remains scoped by administrator, action type, exact target, and normalized idempotency key.
- Where an action already uses a preview token, the preview token remains part of replay-equivalence validation.
- Existing action-specific `AdminAction` partial unique indexes remain the final duplicate-action protection.
- Replay lookup scope and database uniqueness scope must match.
- No second idempotency table, generic idempotency service, or duplicate equivalent uniqueness mechanism is introduced.

The first successful request produces:

- exactly one target transition;
- exactly one `AdminAction`;
- one WS03-05B review-case link/event when an eligible open case exists;
- each notice or notification required for the action's available intended recipients.

An exact replay:

- returns the original admin action identity;
- returns only notice or notification identifiers already supported by that action family's existing response schema;
- reads notice identities from authoritative linked notice records rather than copied ID arrays;
- reads the target's current projection for current-state response fields;
- does not reapply the old mutation;
- does not create another notice or notification;
- does not rewrite an earlier action;
- does not overwrite a later valid opposing action.

Current family-specific response behavior remains intact:

- account and hosting actions continue returning their existing action and direct-notification identities;
- Community Game and Need a Sub actions continue returning their existing action and target-notice identities;
- chat actions retain their existing response shape and do not gain a new notice-ID field solely for this pass.

Reusing the same scoped idempotency key with different behavior-bearing input returns `409` without mutation. At minimum, replay comparison includes the normalized reason and, where applicable, the existing preview token.

Because the key is target-scoped, the same textual key used for another target is a separate operation rather than a collision.

A stale or prohibited state transition returns `409` without:

- target mutation;
- `AdminAction`;
- review-case event/link;
- target notice;
- notification;
- request closure;
- or other domain side effect.

A wrong nested target retains the route's existing concealed not-found behavior.

Only the specific PostgreSQL idempotency uniqueness race for the action being executed may recover as an exact replay. Other foreign-key, check, target-shape, review-case, notice, or unrelated uniqueness failures roll back and fail. A broad `IntegrityError` must not be interpreted as successful replay merely because an action can be found afterward.

Restrictive and restorative actions retain truthful actor, target, reason, before/after state, and timestamp in the existing `AdminAction` record.

A restoration creates a new action. It never rewrites the earlier restrictive action.

### 2.4 Safe User Notices

User communication is part of the enforcement transaction, but it does not require another durable state machine.

The authoritative persistence remains:

- `AdminAction` for the enforcement action, actor, exact target, internal reason, transition metadata, and idempotency identity;
- `AdminTargetNotice` for user-facing enforcement notices linked through `admin_action_id`;
- `Notification` for the existing in-app notification record.

WS03-05C must **not** add an `AdminAction.metadata.notice_outcome` object.

WS03-05C must **not** add:

- copied `notice_ids` arrays to `AdminAction`;
- copied `notification_ids` arrays to `AdminAction`;
- persisted suppression arrays;
- a `recipient_unavailable` notice status;
- delivery-state fields;
- delayed-delivery fields;
- retry-channel fields;
- or another notice-result table.

Existing redundant `AdminAction.metadata["notice_ids"]` writes in affected Community Game and Need a Sub enforcement paths should be removed where the same identities are already recoverable from `AdminTargetNotice.admin_action_id`.

For target-notice action families, replay and result construction query the linked `AdminTargetNotice` records by `admin_action_id`.

Notification identity remains where the current notice/notification implementation already owns it. It is not copied upward into another action-level identifier list.

Account suspension/unsuspension and hosting restriction/restoration retain their existing direct notification path and existing typed `target_notification_id` linkage.

#### Available-recipient rule

For an available intended recipient, successful enforcement requires the corresponding user-facing notice or notification to persist in the same transaction.

Failure to create required communication for an available recipient rolls back the enforcement action and its related side effects.

Current repository relationships mean:

- a valid account/hosting action has its target user;
- a Community Game has its required host relationship;
- a Need a Sub post has its required owner relationship;
- Need a Sub requester relationships used by the existing removal workflow remain required relationships;
- a chat message sender is the concrete covered relationship that may already be unavailable because the sender user reference is nullable and may have been cleared by deletion/anonymization behavior.

When a chat enforcement action executes and the authoritative locked message already has `sender_user_id = NULL`:

- the enforcement action may proceed if all domain preconditions otherwise allow it;
- no placeholder target notice is created;
- no notification is created for a nonexistent sender;
- the `AdminAction` retains the exact message target and its `target_user_id` remains null;
- the `AdminAction.metadata` contains the single finite internal marker
  `"notice_suppression_reason": "recipient_unavailable"`;
- that marker is present only when the locked message already has no sender and
  is omitted whenever an available sender exists;
- no notice status, result object, collection, table, or generalized
  notice/suppression lifecycle state is introduced;
- replay must not later create a notice merely because the request is repeated.

This is the only concrete no-recipient behavior established for this pass. Gate B must not generalize `recipient_unavailable` to action families whose current database invariants already require the intended recipient relationship.

If repository truth discovered during implementation contradicts one of those recipient invariants, Gate B must stop and report the contradiction rather than invent another suppression model.

#### Notice copy

Notice title and body are server-controlled and carry the complete safe user-facing explanation. WS03-05C does not persist a separate safe reason category; `user_safe_reason` is always `NULL`.

Restrictive notices state only:

- what Pickup Lane restricted or removed;
- the affected product area;
- a general safety/policy explanation;
- and, where appropriate, that the user may contact support if they believe the action was mistaken.

They must not claim that an active review case exists unless that is actually guaranteed by the committed state.

Restoration notices state what access or content was restored and any truthful next step.

No notice includes a duration unless the enforced state has a real stored duration. None of the current covered enforcement states introduces one.

Server-owned user-visible copy must never include:

- the administrator's internal reason;
- message text or saved-content text;
- moderation finding evidence;
- rule identifiers;
- detection details;
- reporter identity;
- another user's private identity;
- fraud-investigation details;
- abuse-detection internals;
- security-investigation details;
- provider internals;
- SQL;
- database parameters;
- or secret-like data.

For every `AdminTargetNotice` created by a WS03-05C enforcement path,
`user_safe_reason` is `NULL`. The server-controlled title and body carry the
safe general explanation. The administrator's private reason is never passed to
or persisted in this field.

#### Chat notices

Chat removal and restoration add only the four concrete target-notice types required by these existing actions:

- game-chat message removed;
- game-chat message restored;
- Need a Sub chat message removed;
- Need a Sub chat message restored.

When the sender exists, the notice points to:

- the affected recipient;
- the affected game or Need a Sub post;
- the linked `AdminAction`.

The `AdminAction` remains the authoritative exact message reference through `target_message_id` or `target_sub_chat_message_id`. The notice table does not need another exact-message foreign key for this pass.

When the sender does not exist, the no-recipient rule above applies.

#### Cancellation and removal recipient behavior

Community Game cancellation keeps the existing participant cancellation-notification workflow and adds/retains the safe admin target notice for the host.

The host must not also receive a duplicate generic cancellation notification when the admin target notice already communicates the enforcement outcome.

Need a Sub removal keeps its existing request-closing behavior and uses the existing target-notice path for the owner and affected requesters where currently required.

The owner/requesters must not also receive duplicate generic `sub_post_removed` communication for the same removal event.

Existing unrelated notification cleanup and cancellation/removal side effects remain unchanged.

### 2.5 Atomicity And Compatibility

The following database-backed effects commit or roll back together:

- target mutation;
- `AdminAction`;
- accepted WS03-05B review-case link/event;
- required target notice;
- required in-app notification;
- existing domain child-state changes owned by cancellation/removal.

A required available-recipient notice or notification failing to persist causes the enforcement mutation to roll back.

Community Game cancellation and Need a Sub removal continue using their existing domain workflows, including their current participant/request state changes and related notifications. WS03-05C hardens the enforcement boundary without duplicating those workflows.

Existing public behavior remains compatible, including:

- resource visibility;
- joining enforcement;
- account-state enforcement;
- hosting access;
- chat filtering;
- notification display;
- cancellation/removal behavior.

Existing admin request and response schemas remain compatible. No new response field is introduced solely to expose notice internals.

Admin pages may hide actions that are currently unavailable for usability, but frontend visibility is not an enforcement boundary. The server remains authoritative.

While a mutation is pending, competing controls for the same target are disabled.

After `409`, the frontend reloads authoritative target state before another action is attempted.

## 3. Design

The implementation should consolidate only behavior that is genuinely identical and currently drifts:

- locked-state validation;
- action-specific replay validation;
- safe notice creation.

Existing domain services and accepted security boundaries stay in place.

No generic moderation enforcement state machine is introduced.

### 3.1 Locked Mutation Flow

Each covered action follows this order inside its existing domain service:

1. authorize the administrator and validate request shape;
2. normalize the reason and idempotency key;
3. resolve the exact target and required parent relationship;
4. check for an already completed exact replay using the action's existing target-scoped identity;
5. lock the authoritative target row or existing domain lock set;
6. check again for an action committed by a competing transaction;
7. derive and validate current state from the locked row;
8. apply the domain mutation and record locked before/after state;
9. record the `AdminAction`;
10. link the action to an eligible open review case through the accepted WS03-05B service where applicable;
11. create each required safe notice/notification for available intended recipients;
12. if the concrete chat sender relationship is already null, create no sender
    notice or placeholder state and record only
    `AdminAction.metadata["notice_suppression_reason"] =
    "recipient_unavailable"`;
13. commit once;
14. return the persisted current projection and the identifiers already supported by the action family's existing response contract.

Account suspension and hosting restriction keep their existing preview-token checks and established multi-row lock ordering.

Community Game cancellation and Need a Sub removal keep their domain-specific transaction helpers.

Shared code is appropriate only for genuinely identical normalization, replay, or notice-copy behavior.

This pass must not replace the domain services with a generic enforcement framework.

### 3.2 Replay And Integrity Handling

Existing partial unique indexes on `admin_actions` remain the final duplicate-action protection and must cover every applicable action in the matrix with model/migration/live-schema parity.

No equivalent second uniqueness layer is added.

Replay lookup and database uniqueness scope must use the same:

- administrator;
- action type;
- exact target;
- normalized idempotency key.

Replay validation compares every behavior-bearing input for that action.

Replay reconstructs original communication from authoritative persistence:

- direct account/hosting notification through the existing action-linked notification identity;
- Community Game and Need a Sub target notices by querying `AdminTargetNotice.admin_action_id`;
- chat target notice by the same action linkage when `AdminAction.target_user_id` identifies an available sender at execution;
- no sender notice when the committed chat action has no sender target and no
  linked sender notice, with the committed action carrying the finite
  `recipient_unavailable` suppression reason.

The replay path must not decide to create communication again.

The result builder reads the target's **current** state while returning the **original** action identity and any original notice/notification identifiers already supported by that action family's API.

This remains correct when a later valid reversal has changed the resource since the original action.

For action families where a required recipient existed, a committed action whose required linked notice/notification is unexpectedly absent is an incomplete prior result, not a valid replay.

Integrity-error recovery must identify the violated PostgreSQL constraint or otherwise prove that the failure is the specific action's idempotency race before replay recovery is allowed.

Foreign-key, check, target-shape, notice, review-case, and unrelated uniqueness failures:

- roll back;
- are not treated as replay;
- return an appropriate sanitized conflict/server error;
- never expose SQL or database parameters.

### 3.3 Notice Persistence And Copy

`AdminTargetNotice` remains the persistence model for Community Game, Need a Sub, and new chat enforcement notices.

Its finite notice-type constraint and model declaration are extended only as required for the four concrete chat outcomes:

- game-chat message removed;
- game-chat message restored;
- Need a Sub chat message removed;
- Need a Sub chat message restored.

The clean-rebuild migration definition, SQLAlchemy model, and live PostgreSQL schema must agree.

Compact database checks apply to enforcement notice types and enforce only the target shapes that materially protect correctness.

They must remain compatible with intentional foreign-key deletion behavior, including later `SET NULL` anonymization of user/action references.

At notice creation time, the service validates the concrete requirements for that notice type, including where applicable:

- live linked `AdminAction`;
- creator;
- available recipient;
- target user relationship;
- target game/post/request;
- allowed finite notice type;
- nonblank server-owned title/body;
- exact target shape.

The service never receives or persists the private admin reason as user-facing
safe copy. Every WS03-05C target notice persists `user_safe_reason = NULL`.

For action families that already recover notice IDs from `AdminTargetNotice.admin_action_id`, Gate B removes redundant copies of those IDs from `AdminAction.metadata`.

No new `notice_outcome`, notification-ID collection, suppression collection, or delivery-state object is added.

### 3.4 Frontend Behavior

Existing admin controls remain the UI for these actions.

Control availability mirrors the server state matrix, including:

- active-only joining changes;
- valid restoration states;
- admin-only chat restoration.

Forms retain existing reason and idempotency behavior.

Submitting an action disables competing controls for that target until the request completes.

On success, the frontend applies or reloads returned authoritative state and refreshes affected summaries.

On `409`, the frontend:

- clears stale local mutation state;
- reloads the target;
- does not pretend the requested action succeeded;
- requires a new valid submission if the action is still available.

The frontend does not display:

- internal moderation reasons;
- notice persistence internals;
- suppression internals;
- a new appeal workflow.

## 4. Failures And Edge Cases

These cases cover the situations most likely to create incorrect state, duplicate side effects, unsafe explanations, or misleading replay behavior.

1. **State changed before the action acquired its lock**

   - **Condition:** Another request changes the relevant target first.
   - **Required behavior:** Validate locked state, return `409` when the transition is no longer valid, and create no partial side effects.

2. **Exact request is retried**

   - **Condition:** Same actor repeats the same action, target, normalized behavior-bearing input, and idempotency key.
   - **Required behavior:** Return the original action identity and existing family-supported communication identity, report current target state, and do not repeat mutation or communication.

3. **Idempotency key is reused for different input**

   - **Condition:** Scoped key matches but normalized reason or applicable preview token differs.
   - **Required behavior:** Return `409` and preserve all existing rows and state.

4. **Opposing actions compete**

   - **Condition:** Restriction and restoration requests overlap for the same target.
   - **Required behavior:** Target locking establishes a serial order. Each action succeeds only if its locked precondition is true. Audit history and notices reflect committed order.

5. **Restoration targets wrong removal source or terminal state**

   - **Condition:** Chat message was removed by sender/system, or resource is cancelled, removed, deleted, or otherwise outside the state matrix.
   - **Required behavior:** Reject restoration without changing historical fields or creating enforcement side effects.

6. **Required notice creation fails**

   - **Condition:** Validation, persistence, or notification creation fails for an available intended recipient.
   - **Required behavior:** Roll back target mutation, admin action, review-case effects, notice, notification, and domain child changes together.

7. **Chat sender is already unavailable**

   - **Condition:** Valid chat enforcement targets a persisted message whose authoritative `sender_user_id` is already null.
   - **Required behavior:** Apply the action only when its domain preconditions
     remain valid. Create no placeholder notice or notification. Persist only
     `AdminAction.metadata["notice_suppression_reason"] =
     "recipient_unavailable"`, add no notice lifecycle state, and ensure an
     exact replay does not attempt to notify a sender later.

8. **A normally required recipient relationship is unexpectedly missing**

   - **Condition:** Account/hosting, Community Game, Need a Sub owner/requester, or another action reaches a state that contradicts current repository recipient invariants.
   - **Required behavior:** Do not silently treat the condition as generic `recipient_unavailable`. Fail safely and report the repository/authority contradiction for correction.

9. **Sensitive text is supplied as the internal reason**

   - **Condition:** Admin reason contains source content, reporter canary, detection details, secret-like data, fraud details, or other restricted information.
   - **Required behavior:** Restricted audit reason may retain accepted admin input, but user notices, notifications, API errors, and logs contain none of it.

10. **Domain workflow fails after staging related effects**

    - **Condition:** Community cancellation, Need a Sub removal, review-case linking, notice creation, or another database operation raises before commit.
    - **Required behavior:** Roll back all staged target, child, audit, review, notice, and notification changes. Unrelated integrity failures are not retried as successful actions.

11. **Linked communication is unexpectedly absent on replay**

    - **Condition:** A committed action that required an available recipient has no authoritative linked notice/notification.
    - **Required behavior:** Treat the prior result as incomplete rather than creating a new notice during replay or pretending the original result was complete.

12. **Existing duplicate action metadata disagrees with authoritative notice rows**

    - **Condition:** Pre-WS03-05C action metadata contains copied notice IDs that disagree with linked notice rows.
    - **Required behavior:** The linked notice rows are authoritative. WS03-05C does not perpetuate or expand copied identifier state.

## 5. Testing

Testing must prove the contract at the layer that owns each risk. Real PostgreSQL is required for constraints, transactions, row locking, rollback, uniqueness races, and concurrency behavior.

Do not create a new testing framework or preserve useless tests merely to maintain counts.

### 5.1 Action And API Behavior

Exercise every matrix row through its service and API path.

Cover:

- valid transitions;
- already-applied states;
- prohibited states;
- terminal states;
- wrong nested targets;
- inactive administrators;
- stale administrators;
- current recent-authentication boundaries;
- strict request types;
- unexpected request fields;
- blank/invalid reason;
- blank/invalid idempotency key;
- exact replay;
- mismatched key reuse;
- current-state response after later valid reversal.

Verify WS03-05B integration remains category- and target-correct without changing its accepted behavior.

Rejected requests must leave unchanged, as applicable:

- target rows;
- `AdminAction`;
- review-case events;
- target notices;
- notifications;
- request closures;
- related domain rows.

### 5.2 Notice Safety And Atomicity

For every action family, assert:

- intended recipient;
- action linkage;
- exact supported target shape;
- finite notice type;
- safe fixed copy;
- `user_safe_reason` is null for every WS03-05C target notice;
- truthful next step;
- no duplicate user communication.

Use canary internal reasons and source content to prove those values do not appear in:

- target notices;
- notifications;
- API errors;
- application logs.

At persistence and API serialization boundaries, use canary private reasons to
prove that `user_safe_reason` is exactly null and that the canary does not
appear in the target notice or its linked notification.

Verify family-specific replay behavior:

- account/hosting reuse their original direct-notification identity;
- Community Game/Need a Sub notice IDs are recovered from linked `AdminTargetNotice` rows;
- chat replay does not duplicate the linked target notice;
- chat replay with an originally null sender preserves the original
  `recipient_unavailable` suppression reason and does not create a notice
  later.

Verify that redundant `AdminAction.metadata["notice_ids"]` persistence is not required for result construction and is removed from affected WS03-05C paths.

Cover:

- immediate notice creation;
- chat sender already unavailable;
- exact presence of the `recipient_unavailable` reason for a null sender and
  exact absence of that marker when a sender exists;
- replay without duplicate notice;
- restoration copy;
- cancellation recipient sets;
- Need a Sub removal recipient sets;
- duplicate-message prevention;
- injected notice persistence failure;
- injected notification persistence failure;
- complete transaction rollback.

Prove no unsupported:

- delayed state;
- delivery job;
- retry channel;
- suppression state machine;
- generic notice lifecycle.

### 5.3 PostgreSQL And Concurrency

Use independent PostgreSQL sessions and deterministic barriers for representative races.

Cover representative:

- same-action races;
- restriction/restoration races;
- hide/restore races;
- joining pause/resume races;
- post visibility races;
- chat remove/restore races.

Include account, content/post, and chat targets.

Assert:

- committed target state;
- exact `AdminAction` count;
- exact linked notice count;
- exact notification count where applicable;
- review-case effects;
- losing request behavior;
- rollback freshness;
- absence of partial rows.

Verify:

- every covered action's idempotency index;
- target-scoped replay lookup matches database uniqueness;
- notice finite-type constraint;
- notice target-shape constraints;
- unrelated integrity failures are not accepted as replay;
- model/migration/live-schema parity.

Run the repository's clean rebuild and applicable Alembic lifecycle checks because concrete chat notice types change the schema contract.

### 5.4 Compatibility

Run focused affected coverage for:

- account state;
- hosting;
- Community Game;
- Need a Sub;
- chat;
- cancellation;
- request lifecycle;
- review cases;
- notifications;
- admin authorization;
- recent authentication;
- public visibility.

Run frontend unit/static validation and a production build for changed admin/inbox surfaces.

After focused validation is green, run the risk-appropriate broader backend regression validation required by the shared action, notification, schema, and enforcement blast radius.

Do not repeatedly run broad suites without a concrete reason.

## 6. Done When

This checklist is the engineering completion bar for WS03-05C.

- [ ] Every covered action enforces its matrix preconditions from locked authoritative state.
- [ ] Nested targets are validated against the routed parent.
- [ ] Exact retries are side-effect free.
- [ ] Mismatched idempotency-key reuse returns `409`.
- [ ] Replay scope exactly matches the applicable target-scoped PostgreSQL uniqueness rule.
- [ ] Unrelated integrity failures are never converted into successful replay.
- [ ] Restriction and restoration history remains truthful without overwriting previous actions.
- [ ] Every available intended recipient receives exactly one required safe notice/notification.
- [ ] Every WS03-05C target notice persists `user_safe_reason = NULL`, and no
      private admin reason reaches user-visible notice or notification data.
- [ ] A chat message whose sender is already unavailable creates no placeholder
      communication, records only
      `notice_suppression_reason = "recipient_unavailable"`, and introduces
      no new notice lifecycle state.
- [ ] The suppression marker is absent whenever the chat sender exists.
- [ ] No `AdminAction.notice_outcome`, notice-ID array, notification-ID array, or suppression array is introduced.
- [ ] Existing redundant `AdminAction.metadata["notice_ids"]` writes are removed from affected paths where authoritative notice linkage already supplies the same information.
- [ ] Replay reconstructs notice effects from authoritative linked records rather than copied identifier metadata.
- [ ] User-visible communication contains only server-controlled safe information and a truthful next step.
- [ ] Private admin reasons never flow into user-facing notice fields, notification copy, API errors, or logs.
- [ ] Chat removal/restoration notices use only the four concrete new notice types required by this pass.
- [ ] No second permission hierarchy, enforcement state machine, generic idempotency store, generalized notice lifecycle, scheduler, delivery retry framework, or appeal workflow is introduced.
- [ ] Target mutation, audit/review-case effects, required notices/notifications, and existing domain child changes commit or roll back together.
- [ ] Existing authorization, recent-authentication, cancellation, removal, WS03-05B review-case behavior, API contracts, and public behavior remain compatible.
- [ ] Focused backend/API validation passes.
- [ ] Real PostgreSQL constraint, rollback, and concurrency validation passes.
- [ ] Model/migration/live-schema parity passes.
- [ ] Applicable migration lifecycle and clean-rebuild validation passes.
- [ ] Changed frontend unit/static/build validation passes.
- [ ] Risk-appropriate regression validation passes.
