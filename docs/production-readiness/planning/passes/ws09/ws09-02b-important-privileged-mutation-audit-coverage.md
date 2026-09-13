# WS09-02B - Important Privileged-Mutation Audit Coverage

WS09-02B closes the remaining current gaps where an important administrator mutation can succeed without durable, actor-attributed audit truth.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

This pass completes audit coverage for the current privileged-mutation surface while preserving the append-only `AdminAction` foundation established by WS09-02A. It adds audit rows only where current administrator-controlled state changes lack sufficient durable attribution, and it keeps existing domain histories and rejected-attempt records authoritative where they already preserve the relevant truth without duplication.

Most important administrator mutations already have durable audit behavior. Account enforcement and role changes, official-game operations, Community Game and Need a Sub enforcement, chat moderation, review-case mutations, money operations, credits, venue-image administration, platform notices, support-flag resolution, and administrator user deletion already use `AdminAction` or an accepted domain-specific durable record.

The remaining live application audit gaps are:

- generic administrator game updates;
- staff Community Game detail creation;
- staff Community Game detail updates;
- generic administrator game soft deletion;
- venue soft deletion; and
- payment-event repair and reprocessing.

The repository also contains direct operational data-mutation tools that bypass the authenticated administrator surface. `backend/scripts/bootstrap_admin.py` promotes a user without a guaranteed pre-existing in-app administrator, while `backend/scripts/seed_demo_browse.py` and the callable portfolio seed in `backend/scripts/portfolio_seed/runner.py` can create or overwrite an administrator and broad application state. None can truthfully use `AdminAction.admin_user_id` for a production operator. WS09-02B therefore removes all three callable mutation paths from the production surface instead of fabricating actor attribution: each must refuse to run when `APP_ENV=production`. Final production first-admin/control-plane provisioning remains outside this pass; these scripts are not allowed production mutation mechanisms.

The generic administrator game-creation path does not need a duplicate `AdminAction`: the created `Game` row already identifies the creating administrator, target record, creation time, and resulting state. By contrast, `CommunityGameDetail` does not preserve the staff actor that created or updated the row, so its live staff mutations require audit coverage.

Generic administrator mutation scaffolds that reject the operation or return `410 Gone` remain outside audit coverage because they do not change state. User-owned product mutations also remain outside this pass.

This pass does not add sensitive-read auditing, which remains WS09-02C ownership, and it does not create a second audit store or a new audit investigation, search, or export product.

## 2. What Must Be True

These requirements define the audit guarantees that must hold across the current privileged-mutation surface when this work is complete.

### 2.1 Complete, Non-Duplicative Attribution

- Every current important privileged mutation has one truthful durable disposition.
- A disposition may be an `AdminAction`, an authoritative domain record that already preserves the required actor and result, or an existing rejected-attempt/failure record when no privileged mutation succeeded.
- The six uncovered live application mutation paths preserve the authenticated administrator as the actor instead of discarding that identity.
- `bootstrap_admin.py`, `seed_demo_browse.py`, and the callable portfolio seed are explicitly classified as non-production tooling and must refuse to open a database session or mutate data when `APP_ENV=production`; WS09-02B must not fake a seeded or promoted user as the acting administrator.
- Existing `AdminAction`, `AdminRejectedAttempt`, refund-event, money-issue, durable-job, review-case, lifecycle-history, and other accepted domain records are not duplicated merely to increase audit-row count.
- Generic game creation remains represented by the created `Game` row and its `created_by_user_id`.
- Retired, rejected, read-only, user-owned, and production-disabled bootstrap/demo-data paths do not gain administrative mutation audit rows.

### 2.2 Atomic Mutation Recording

- A new `AdminAction` required by this pass is staged in the same database transaction as the local mutation it describes.
- The business mutation and its required audit row commit together or roll back together.
- The existing `record_admin_action()` mutation contract remains the recorder. This pass does not replace it with the sensitive-read recorder or introduce another audit persistence path.
- Community Game detail creation/update and their audit action commit together before the existing post-commit moderation surfacing step runs.
- Payment-event changes, durable-job enqueue or exhausted-job requeue changes, and the required audit action remain in one caller-owned transaction.
- A true payment-event no-op does not create an `AdminAction`.
- Covered mutable rows are locked before audit before-state and effective-change metadata is derived, so concurrent requests cannot create stale or duplicate success records.
- Recorder validation and audit-row persistence failures return the existing stable `503` audit-unavailable response without exposing database, constraint, schema, or internal policy details.
- Lock timeouts, deadlocks, serialization failures, and commit-uncertain results remain bounded under the accepted database error contract and are not blindly retried.

### 2.3 Safe Audit Content

- Generic game updates use the existing `update_game` action type and record only safe field names describing the effective change, never free-text game values.
- Staff Community Game detail creation uses `create_community_game_detail`; staff detail updates use `update_community_game_detail`.
- Community Game detail audit metadata never copies payment-method snapshot values or payment instructions.
- Game soft deletion uses `delete_game`.
- Venue soft deletion uses `delete_venue`.
- Payment-event repair/reprocessing uses `update_payment_event` and a typed internal payment-event target.
- Payment-event audit metadata and display labels never expose the provider event identifier, event type, event envelope, provider timestamps, processing-error content, or other provider-owned payload.
- Audit-log and detail rendering for a payment-event target uses the internal audit target ID directly and must not load or hydrate the `PaymentEvent` ORM row merely to build a label.
- No new reason field, client audit identifier, or idempotency contract is added to these existing request APIs solely for auditing.

### 2.4 Audit-Contract Compatibility

- `update_game` continues using its existing target policy and action identity.
- `create_community_game_detail`, `update_community_game_detail`, `delete_game`, `delete_venue`, and `update_payment_event` are registered consistently in the action policy and database action-type constraint.
- Community Game detail actions use the existing game target rather than adding another typed target: the detail is one-to-one with a game, and its action type identifies the subresource being changed.
- The payment-event target is represented consistently anywhere the audit model, schemas, target policy, and display layer enumerate typed targets.
- Adding `target_payment_event_id` does not change the global mutation recorder into a target-existence validator. The payment-event workflow already loads and validates its own target before recording the action.
- `target_payment_event_id` is not added to generic ORM-backed target display/reference loading that would hydrate provider-owned payment-event columns.
- Existing active-admin restrictions for reading audit records remain unchanged.

## 3. Design

The implementation extends the current audit system only at uncovered consumers and makes the shared-contract additions required to represent those actions safely.

### 3.1 Current Privileged-Mutation Disposition

The current surface intentionally uses both `AdminAction` and authoritative domain records rather than forcing every durable fact into one table.

| Mutation family | Durable truth after WS09-02B |
| --- | --- |
| User role, suspension, hosting restriction/restoration, and administrator deletion | Existing `AdminAction`; rejected-attempt and deletion follow-up records remain authoritative for their bounded failure cases. |
| Official-game creation, update, cancellation, host, roster, removal, and related money effects | Existing `AdminAction` plus existing game, participant, refund, credit, and money-issue histories where applicable. |
| Community Game and Need a Sub enforcement | Existing `AdminAction` with existing lifecycle and review-case records where applicable. |
| Chat moderation | Existing transactional `AdminAction`. |
| Review-case note and close mutations | Existing `AdminAction` plus review-case note/event history. |
| Money outcomes, money-issue actions, refunds, reconciliation, and credits | Existing `AdminAction` for the administrator mutation; provider and asynchronous outcomes remain in their existing domain records. |
| Venue-image administration | Existing `AdminAction`. |
| Platform notices and support-flag resolution | Existing `AdminAction`; support-flag domain records remain authoritative for their own lifecycle facts. |
| Generic administrator game creation | Existing `Game` row with creator, target identity, creation time, and resulting state. |
| Generic administrator game update | Add transactional use of existing `update_game`. |
| Staff Community Game detail creation | Add transactional `create_community_game_detail` targeting the owning game. |
| Staff Community Game detail update | Add transactional `update_community_game_detail` targeting the resulting owning game. |
| Generic administrator game soft deletion | Add transactional `delete_game`. |
| Venue soft deletion | Add transactional `delete_venue`. |
| Payment-event repair/reprocessing | Add transactional `update_payment_event` with a typed payment-event target and optional linked payment target. |
| Operational `bootstrap_admin.py` role promotion | Remove from the production mutation surface: refuse execution before opening a database session when `APP_ENV=production`; do not fabricate an `AdminAction` actor. |
| Demo and portfolio seed workflows | Remove from the production mutation surface: both public callable seed entry points refuse execution before opening a database session when `APP_ENV=production`; do not fabricate an administrator actor or write seeded application state. |
| Retired or rejected generic mutation scaffolds | No audit row because no mutation occurs. |
| User-owned product mutations | Outside administrative mutation coverage. |
| Sensitive administrative reads | Outside WS09-02B; existing WS03-05D behavior and WS09-02C own read auditing. |

### 3.2 Generic Administrator Game Update

The generic administrator update route already passes the authenticated administrator to `update_game_workflow()`. The workflow must use that actor to stage the existing `update_game` action before its final commit. It must acquire the owning `Game` row with `SELECT ... FOR UPDATE` before capturing prior state or calculating effective changed fields. This follows the accepted game-first lock order and makes concurrent same-target actions describe the state each transaction actually observed after serialization.

The action must:

- target the game;
- use outcome `succeeded`;
- use the existing `official_game` metadata profile;
- store `changed_fields` as a sorted list of safe client-editable field names whose effective persisted values differ from the prior game state;
- store no request field values, descriptions, custom rules, game notes, parking notes, or other free-text content; and
- use no new reason or idempotency requirement.

Existing game validation, moderation-case lifecycle handling, connected-user notification behavior, and response shape remain unchanged. The existing optional admin service parameter must not fabricate an actor for a non-admin/internal call; the live administrator route supplies the authenticated actor and therefore emits the action.

A successful request that preserves current no-op behavior may record `update_game` with an empty `changed_fields` list if the workflow itself still performs its normal update lifecycle. Rejected validation creates no succeeded action.

### 3.3 Staff Community Game Detail Creation And Update

`POST /community-game-details` and `PATCH /community-game-details/{community_game_detail_id}` are live staff mutations. Both currently require an active administrator but discard that identity before their service workflows commit. WS09-02B must carry the authenticated administrator into those workflows and record the mutation atomically.

No new Community Game detail target column is needed. `CommunityGameDetail.game_id` is unique, so the owning game is the stable audit target, while distinct action types identify the subresource operation.

`create_community_game_detail` must:

- require `target_game_id`;
- target the game supplied by the validated new detail;
- use outcome `succeeded`;
- use the existing bounded `support` metadata profile;
- use this exact top-level metadata shape so it remains valid under the current `support` allowlist:

  ```json
  {
    "source": "admin_community_game_detail",
    "after": {
      "detail_present": true,
      "game_id": "<internal game UUID>"
    }
  }
  ```

- never copy `payment_methods_snapshot` contents or payment instructions into audit metadata.

`update_community_game_detail` must:

- require `target_game_id`;
- target the resulting validated game after any permitted `game_id` reassignment;
- use outcome `succeeded`;
- use the existing bounded `support` metadata profile;
- use this exact top-level metadata shape, keeping `changed_fields` nested under `after` rather than introducing an unsupported top-level key:

  ```json
  {
    "source": "admin_community_game_detail",
    "before": {
      "game_id": "<prior internal game UUID>"
    },
    "after": {
      "game_id": "<resulting internal game UUID>",
      "changed_fields": ["<sorted changed field names>"]
    }
  }
  ```

- limit `changed_fields` to exactly the submitted fields from `game_id`, `payment_methods_snapshot`, and `payment_instructions_snapshot` whose resulting persisted value differs from the locked prior row; and
- never store payment-method values, handles, payment instructions, or moderation text.

The update workflow must lock the `CommunityGameDetail` row before capturing its prior game ID or calculating changed fields. When `game_id` changes, the prior internal game ID remains in safe `before` metadata and the resulting game is the typed target. A successful empty or same-value PATCH may still produce an action with an empty business `changed_fields` list because the current workflow advances `updated_at`; the action truthfully represents the successful staff mutation request without inventing changed values.

The audit action and Community Game detail row must commit in the same transaction. The existing `surface_community_game_text()` call remains a post-commit moderation-surfacing step. Its later result is not copied into or treated as the outcome of the administrative detail action.

### 3.4 Game Soft Deletion

The recent-admin generic game delete path is an operational soft delete, not a cancellation and not a moderation-enforcement action. It therefore receives `delete_game`.

`delete_game` must:

- require `target_game_id`;
- use the existing `support` metadata profile;
- use outcome `succeeded`;
- use this exact metadata shape:

  ```json
  {
    "source": "admin_soft_delete",
    "before": {
      "deleted": false
    },
    "after": {
      "deleted": true
    }
  }
  ```

- commit in the same transaction as the game tombstone and existing moderation-case lifecycle closure.

The current rule that official games must be cancelled instead of deleted remains unchanged. The workflow acquires the owning `Game` row with `SELECT ... FOR UPDATE` before checking its live/deleted state, captures required before-state before applying the tombstone, stages the action after domain validation, and commits both together. Concurrent deletion attempts therefore serialize: only the transaction that observes the live row succeeds and records `delete_game`; a later waiter observes the tombstone and retains the current not-found behavior without another action.

The existing `admin_soft_deleted` review-case lifecycle transition intentionally has no linked `AdminAction` and rejects one if supplied. `delete_game` must therefore share the transaction with that lifecycle closure but must not be passed into or linked from the lifecycle transition. The lifecycle event remains the authoritative `no_action_needed` domain history for automatic case closure, while `delete_game` independently records the administrator's soft-delete mutation.

The existing audit display fallback already handles a game that later becomes tombstoned by showing the target type and internal identifier without a destination. No new mutation-time target-existence validation is required.

### 3.5 Venue Soft Deletion

The venue delete route must stop discarding the authenticated recent administrator and pass that actor into the deletion workflow.

`delete_venue` must:

- require `target_venue_id`;
- use the existing `support` metadata profile;
- use outcome `succeeded`;
- use this exact metadata shape, with the prior values read from the locked row:

  ```json
  {
    "source": "admin_soft_delete",
    "before": {
      "is_active": "<prior boolean>",
      "venue_status": "<prior bounded status>",
      "deleted": false
    },
    "after": {
      "is_active": false,
      "venue_status": "inactive",
      "deleted": true
    }
  }
  ```

- serialize `before.is_active` as the actual JSON boolean from the row; the placeholder above is not a string-valued contract;
- exclude the venue name, address, coordinates, and other venue content from audit metadata; and
- commit atomically with the existing transition to inactive status and `deleted_at`.

A missing or already-deleted venue keeps the current not-found behavior and creates no succeeded action. The deletion workflow locks the `Venue` row before checking that state and capturing the metadata snapshot, so concurrent delete attempts cannot both record success. No deletion-reason request field is added.

The existing tombstoned-target display fallback remains sufficient for the venue action.

### 3.6 Payment-Event Repair And Reprocessing

The recent-admin payment-event update path can relink an event to a payment and can create or requeue durable webhook-processing work. The `PaymentEvent` record preserves provider-processing state but does not identify which administrator performed the repair. The route currently discards that administrator identity, so it must pass the authenticated administrator into `update_payment_event_record()`. The workflow must lock the `PaymentEvent` row before reading its payment link or lifecycle state, then retain its existing payment-event-before-durable-job lock order while examining or changing durable work.

Add nullable `target_payment_event_id` to `AdminAction`. It is an internal audit pointer, not a provider identifier.

`update_payment_event` must:

- require `target_payment_event_id`;
- optionally include `target_payment_id` when an effective linked payment exists;
- use outcome `succeeded`;
- use the existing `money` metadata profile without adding a new top-level metadata key;
- store `before` with only the prior internal `payment_id` and `processing_status`;
- store `after` with only the resulting internal `payment_id`, resulting `processing_status`, `reprocess_requested`, and a bounded `durable_work_action`;
- limit `durable_work_action` to the exact vocabulary `none`, `ensured`, `requeued`, or `already_active`;
- use `ensured` when the workflow invokes the idempotent enqueue helper and durable work exists after that call, regardless of whether this transaction inserted the job or encountered an already-created equivalent;
- use `requeued` only when an exhausted durable job is actually moved back to runnable work, `already_active` only when equivalent work already exists in an active/non-exhausted state while the payment event itself changes, and `none` when no durable-work mutation or ensure operation is part of the successful local change;
- exclude `provider_event_id`, `event_type`, `event_envelope`, provider timestamps, processing-error content, and all other provider-owned detail; and
- commit in the same transaction as the payment-event change and any durable-job enqueue or exhausted-job requeue.

The current durable-job enqueue and requeue helpers use the caller's session without committing independently, so no new transaction mechanism is required.

A successful action represents the local administrator repair/requeue only. Later worker or Stripe outcomes remain authoritative in the existing payment-event and durable-job records and do not rewrite the immutable action.

A true no-op creates no audit row. A request is a true no-op only when it leaves the effective payment link unchanged, does not change/reset payment-event lifecycle fields, and does not attempt either durable-work ensure or exhausted-job requeue. An empty PATCH and a same-value payment-link PATCH with no reprocess request are true no-ops.

When the workflow invokes the idempotent durable-work ensure path, the administrative operation is auditable even if another transaction wins the enqueue race and the helper returns the equivalent existing job. That result records `durable_work_action: "ensured"` rather than being reclassified as a no-op. `requeued` is used only when an exhausted job is actually requeued. `already_active` is used only when reprocessing observes an existing active pending/retry/leased job, creates or requeues no job, and still makes an effective payment-event lifecycle change. If that active-job case also leaves every payment-event field unchanged, the request is a true no-op and creates no action. The existing successful API response behavior remains unchanged.

### 3.7 Shared Audit Contract And ID-Only Payment-Event Display

The new action types and payment-event target must fit the WS09-02A foundation rather than creating a second audit path.

The shared contract changes are:

- retain the existing `update_game` policy;
- add mutation policies for `create_community_game_detail`, `update_community_game_detail`, `delete_game`, `delete_venue`, and `update_payment_event`;
- allow exactly `target_game_id` for each Community Game detail policy and for `delete_game`, and require that target;
- allow exactly `target_venue_id` for `delete_venue` and require that target;
- allow exactly `target_payment_event_id` and optional `target_payment_id` for `update_payment_event`, and require the payment-event target;
- classify all five as mutation actions, use their specified existing metadata builders, require neither reason nor idempotency key, and retain the foundation's normal audit-note correction eligibility;
- update the existing canonical `admin_actions` migration together with the ORM rather than adding a repair migration;
- add the five new action types to both the ORM and canonical migration action-type constraints;
- add nullable UUID `target_payment_event_id` to the audit target-field set, ORM, canonical migration, target-required constraint, index set, and admin-action schemas that enumerate targets;
- keep `target_payment_event_id` as the same non-FK typed audit-pointer pattern used by existing cross-domain target columns;
- do not add a foreign key from `admin_actions.target_payment_event_id` to `payment_events.id`, because the canonical `admin_actions` migration runs before the later `payment_events` table migration;
- leave mutation target existence owned by `update_payment_event_record()`, which already loads the payment event, rather than registering `PaymentEvent` in generic mutation reference validation;
- preserve append-only behavior and current active-admin audit-read authorization.

The display registry must add exact action labels and primary-target order rather than relying on the generic action-name fallback:

| Action | Display label | Primary target order |
| --- | --- | --- |
| `create_community_game_detail` | `Community game detail created` | `target_game_id` |
| `update_community_game_detail` | `Community game detail updated` | `target_game_id` |
| `delete_game` | `Game deleted` | `target_game_id` |
| `delete_venue` | `Venue deleted` | `target_venue_id` |
| `update_payment_event` | `Payment event updated` | `target_payment_event_id`, then `target_payment_id` |

Payment-event display needs one explicit exception to the normal ORM-backed target renderer. The implementation must add an ID-only target-display mapping for `target_payment_event_id` rather than adding `PaymentEvent` to `TARGET_DISPLAY_RULES`.

The ID-only display path must:

- let `update_payment_event` select `target_payment_event_id` as its primary target;
- prevent `collect_primary_target_ids()` / `load_records_by_field()` from sending payment-event IDs through the ORM-backed bulk loader;
- let `build_target_summary()` recognize the ID-only target and directly produce a neutral `Payment event <internal UUID>` label;
- use target type label `Payment event`;
- set `destination_path` to `None`; and
- work for both audit log and audit detail serialization without querying `payment_events`.

This preserves the current display pipeline while ensuring that audit rendering does not hydrate `event_envelope`, `provider_event_id`, or other provider-owned columns.

`record_admin_action()` remains a policy/cardinality validator and caller-transaction participant. WS09-02B does not broaden it into global mutation target-reference validation.

### 3.8 Production-Disabled Direct Data-Mutation Tools

`backend/scripts/bootstrap_admin.py`, `backend/scripts/seed_demo_browse.py`, and `backend/scripts/portfolio_seed/runner.py` expose callable database-mutation entry points outside the authenticated HTTP administrator surface. The bootstrap promotes an existing user; both seeds can create or overwrite an administrator and broad domain state. The thin `backend/scripts/seed_portfolio_browse.py` launcher delegates to the runner, so guarding only the launcher would leave the importable runner callable in production.

WS09-02B must not solve that mismatch by attributing changes to the promoted/seeded administrator or by weakening the accepted `AdminAction.admin_user_id` contract. Instead:

- keep all three workflows available for non-production bootstrap, development, and portfolio setup;
- at the beginning of each public callable mutation function, load the typed partial settings contract and reject exactly `AppEnvironment.PRODUCTION` before constructing or entering `SessionLocal`;
- place the portfolio guard in `portfolio_seed.runner.seed_portfolio_browse()` so the launcher and direct imports share the same boundary;
- raise `BootstrapAdminError` from the bootstrap and `RuntimeError` from each seed, with a stable message stating that the operation is unavailable in production and no configuration or database detail;
- leave ordinary administrator role changes on the existing authenticated, audited role-change workflow;
- do not introduce a second audit table or a synthetic/bootstrap administrator account solely to make these tools fit `AdminAction`.

This gives the current production surface a truthful disposition: unauthenticated operational role and demo-data mutation paths are unavailable in production rather than falsely audited.

### 3.9 Locking, Flush, And Safe Audit-Failure Mapping

The new audit facts depend on the exact state observed by each successful transaction. Each covered update/delete workflow must therefore acquire its mutable target row with PostgreSQL `SELECT ... FOR UPDATE` before deriving before-state, changed fields, deletion eligibility, or payment-event work classification. Game workflows lock the owning `Game` first, consistent with the accepted game-first order. Payment-event repair locks `PaymentEvent` before its current latest-`DurableJob` lock. Locks are held only for the local database transaction; no provider call is added or made while they are held.

After domain validation and mutation staging, each workflow must call the existing `record_admin_action()`, explicitly flush the domain and audit changes, and then issue one commit. The implementation must classify failures without turning server-owned audit configuration into a client error:

- an `HTTPException` or unknown-target `ValueError` raised by the server-constructed `record_admin_action()` call is translated to `503` with the existing `AUDIT_UNAVAILABLE_DETAIL` message;
- an `IntegrityError` whose PostgreSQL diagnostic identifies table `admin_actions` is translated to the same stable `503`; the check uses structured diagnostic fields, not substring matching against raw database text;
- known pre-existing domain constraint conflicts retain their current safe domain response;
- unexpected database/internal detail is never returned through a domain conflict helper merely because the new audit row shared the flush or commit; and
- any lock timeout, deadlock, serialization failure, or commit-uncertain result uses the accepted bounded database/public-error behavior, attempts local rollback where possible, and is not blindly retried.

A pre-commit validation, flush, or deterministic constraint failure leaves neither the mutation nor its action committed. A commit-time connection failure can leave the caller unable to know the transaction outcome; the database still commits the mutation and action atomically, but the API must return a bounded safe error rather than claiming success, failure, or rollback without evidence. Refresh/serialization after a successful commit must not be described or handled as an audit rollback.

## 4. Failures And Edge Cases

These cases define the abnormal behavior that matters because an audit row must never make a rejected, rolled-back, or asynchronous operation look successfully completed.

1. **Audit recording fails before a covered mutation commits**
   - **Condition:** Policy validation, audit construction, database constraint enforcement, or persistence prevents the required `AdminAction` from committing.
   - **Required behavior:** For a recorder validation or pre-commit flush/constraint failure, roll back the owning local transaction and return `503` with `AUDIT_UNAVAILABLE_DETAIL`. The game, Community Game detail, venue, payment event, and durable-job state must not remain partially committed, and the response must contain no raw database, schema, constraint, or policy detail. If the commit result itself is uncertain, return bounded safe database failure behavior without claiming rollback or retrying blindly; database atomicity still prevents the mutation and action from committing independently.

2. **Concurrent operations target the same mutable row**
   - **Condition:** Two administrators concurrently update the same game/detail/payment event or attempt to delete the same game/venue.
   - **Required behavior:** Acquire the target lock before deriving audit state. Updates serialize and each successful action describes the locked predecessor/resulting state. For deletion, only the transaction that observes a live target records success; a later waiter observes the tombstone, returns the current not-found response, and creates no second action. Lock timeout, deadlock, or serialization errors remain bounded and are not blindly retried.

3. **Generic game update is rejected or contains no effective business-field change**
   - **Condition:** Existing game validation rejects the request, or the accepted request produces no changed client-editable business fields.
   - **Required behavior:** A rejected request creates no succeeded action. A successful no-op may retain current workflow semantics and record `update_game` with an empty `changed_fields` list, without inventing values.

4. **Community Game detail creation fails**
   - **Condition:** The target game is missing/not a Community Game, the detail violates payment-method business rules, or the game already has a detail row.
   - **Required behavior:** Preserve the current error response and create no `create_community_game_detail` success row. Audit failure itself must also leave the detail uncreated.

5. **Community Game detail update is invalid**
   - **Condition:** The detail is missing, a resulting game reference is invalid/not a Community Game, payment-method validation fails, or reassignment violates the one-detail-per-game constraint.
   - **Required behavior:** Preserve the current validation/conflict behavior and create no succeeded `update_community_game_detail` action. Audit failure rolls back the detail change.

6. **Community Game moderation surfacing fails after the detail transaction committed**
   - **Condition:** The detail row and its audit action commit successfully, then the existing post-commit `surface_community_game_text()` step fails.
   - **Required behavior:** Do not rewrite the immutable audit row as failed. The action truthfully records the already-committed staff detail mutation; moderation surfacing keeps its existing separate failure ownership.

7. **Game deletion is not permitted or lifecycle closure rejects linkage**
   - **Condition:** The game is missing/already deleted, the target is an official game that must use cancellation, or implementation attempts to pass/link `delete_game` into the `admin_soft_deleted` automatic review-case closure.
   - **Required behavior:** Preserve the current domain error behavior for invalid deletion. For valid Community Game deletion, keep `delete_game` and the lifecycle closure in one transaction but do not link the action into the automatic closure; any attempted invalid linkage must fail and roll back the transaction.

8. **Venue deletion cannot resolve an active target**
   - **Condition:** The venue is missing or already soft-deleted.
   - **Required behavior:** Preserve the current not-found behavior and create no `delete_venue` success row.

9. **Payment-event repair is invalid**
   - **Condition:** The payment event is missing, the linked payment is invalid, or reprocessing encounters a non-requeueable durable-job state.
   - **Required behavior:** Preserve the current validation/conflict response and create no `update_payment_event` success row.

10. **Payment-event request is a true no-op**
   - **Condition:** The effective payment link is unchanged, payment-event lifecycle fields remain unchanged, and the workflow does not attempt durable-work ensure or exhausted-job requeue.
   - **Required behavior:** Preserve the successful response but create no `AdminAction`. If the idempotent ensure path is invoked, the request is not a no-op even when another transaction already created the equivalent job; record `durable_work_action: "ensured"`. Observing an already-active job is recorded as `already_active` only when the transaction also changes payment-event lifecycle state; otherwise it remains a true no-op.

11. **Payment-event processing fails after a successful administrative repair/requeue**
    - **Condition:** The local repair/requeue commits successfully, but later asynchronous webhook processing fails or exhausts.
    - **Required behavior:** Keep the original `update_payment_event` action as the truthful record of the successful local administrative operation. Record later processing outcomes only in existing payment-event and durable-job state.

12. **An audited game or venue is later tombstoned**
    - **Condition:** Audit list/detail display resolves a game or venue target whose `deleted_at` is now set.
    - **Required behavior:** Preserve the existing safe fallback using target type and internal identifier with no destination.

13. **A direct data-mutation script is invoked in production**
    - **Condition:** The bootstrap, demo seed, or callable portfolio seed starts with `APP_ENV=production`, whether invoked by its launcher or imported directly.
    - **Required behavior:** Reject before opening a database session, Firebase lookup, or mutation. Return the stable script-level error, create no audit row, and leave all application state unchanged.

14. **Existing denial or domain-failure records already own the outcome**
    - **Condition:** An existing `AdminRejectedAttempt`, refund event, money issue, support flag, durable job, lifecycle history, or other accepted domain record already preserves the bounded failure/follow-up truth.
    - **Required behavior:** Keep that record authoritative and do not add a duplicate `AdminAction` merely for coverage symmetry.

## 5. Testing

Testing must prove the new coverage, privacy boundaries, and transaction ownership with focused PostgreSQL-backed coverage while reusing the existing test structure.

### 5.1 Generic Game Update

Prove that:

- a successful administrator update creates one `update_game` action with the correct actor, game target, and `succeeded` outcome;
- `changed_fields` contains only safe client-editable field names and no submitted values;
- successful existing no-op behavior does not fabricate changed values;
- independent concurrent same-target updates serialize at the game lock, and a waiter derives `changed_fields` from the state committed by its predecessor;
- rejected validation creates no succeeded action; and
- forced recorder-validation and audit-table constraint failures leave the game mutation uncommitted and return only the stable audit-unavailable response.

### 5.2 Staff Community Game Detail Creation And Update

Prove that:

- successful staff creation creates one `create_community_game_detail` action with the authenticated administrator and owning game target;
- successful staff update creates one `update_community_game_detail` action with the authenticated administrator and resulting game target;
- create metadata uses exactly the allowed top-level keys `source` and `after`, with `detail_present` and the internal game ID nested under `after`;
- update metadata uses exactly the allowed top-level keys `source`, `before`, and `after`, with the sorted `changed_fields` list nested under `after`;
- a permitted game reassignment records only safe prior/resulting internal game IDs plus changed field names;
- payment-method snapshot values and payment instructions never appear in audit metadata;
- an empty/same-value update preserves current semantics without fabricated `changed_fields`;
- independent concurrent updates serialize at the detail-row lock and each action's prior/resulting game IDs and changed fields match that transaction's locked transition;
- missing/invalid games, invalid payment methods, duplicate-detail conflicts, and invalid reassignment create no succeeded action;
- independent concurrent creates for the same game are bounded by the existing unique constraint, commit exactly one detail/action pair, and leave the loser with the established conflict and no action;
- forced recorder-validation and audit-table constraint failures roll back the detail create/update and expose only the stable audit-unavailable response; and
- existing post-commit moderation surfacing still occurs only after the detail plus audit transaction has committed.

### 5.3 Game Soft Deletion

Prove that:

- successful Community Game soft deletion creates one `delete_game` action in the same transaction as the tombstone and existing review-case lifecycle closure;
- the `admin_soft_deleted` lifecycle closure receives no linked `AdminAction`, while the independent `delete_game` row still commits atomically with it;
- metadata contains only the bounded soft-delete transition;
- audit log/detail rendering remains usable after the game is tombstoned;
- official-game rejection, unknown game, and repeated deletion create no succeeded action;
- independent concurrent deletion attempts produce exactly one committed tombstone/action while the waiter receives the current not-found result with no second action; and
- forced audit failure leaves both game and related review state uncommitted and returns only the stable audit-unavailable response.

### 5.4 Venue Soft Deletion

Prove that:

- successful deletion creates one `delete_venue` action with the correct actor and venue target;
- metadata is limited to the safe active/status/deletion transition;
- audit display remains usable after the venue is tombstoned;
- missing or repeated deletion creates no succeeded action;
- independent concurrent deletion attempts produce exactly one committed tombstone/action while the waiter receives the current not-found result with no second action; and
- forced audit failure leaves the venue active and undeleted and returns only the stable audit-unavailable response.

### 5.5 Payment-Event Repair And Reprocessing

Prove that:

- the recent-admin route passes the authenticated administrator into the payment-event workflow;
- linking, unlinking, or relinking a payment event creates one `update_payment_event` action only when the effective link changes;
- a reprocess operation creates one action when it resets payment-event lifecycle state, enqueues durable work, or requeues exhausted durable work;
- an empty request, a same-value link with no reprocess mutation, and a reprocess request that produces no effective local state/job change create no audit row;
- an already-active job is classified as `already_active` only when payment-event lifecycle state also changes; an entirely unchanged event/job pair is a no-op;
- the action always targets the internal payment-event ID and includes the resulting payment target only when one exists;
- invalid payment linkage, missing payment event, and non-requeueable conflicts create no succeeded action;
- independent concurrent repair/reprocess requests serialize at the payment-event lock, retain payment-event-before-job lock order, and record metadata matching the actual predecessor/resulting state;
- forced recorder-validation and audit-table constraint failures roll back payment-event and durable-job changes and return only the stable audit-unavailable response;
- metadata contains only the bounded internal before/after fields and durable-work classification;
- `durable_work_action` is always exactly one of `none`, `ensured`, `requeued`, or `already_active`;
- an idempotent enqueue race that returns an already-created equivalent job is classified as `ensured`, not falsely reported as newly `enqueued`; and
- no provider event identifier, event type, envelope, provider timestamp, or processing-error content appears in audit metadata or target labels.

### 5.6 Production-Disabled Direct Data-Mutation Tools

Prove that:

- `bootstrap_admin.py` refuses execution when `APP_ENV=production`;
- `seed_demo_browse()` and `portfolio_seed.runner.seed_portfolio_browse()` refuse execution when `APP_ENV=production`, including direct function imports that bypass the thin portfolio launcher;
- each production refusal occurs before `SessionLocal` is constructed and before Firebase, user-role, user-context, seeded-user, or other domain mutation work begins;
- the refusal messages are stable and contain no configuration/database detail;
- no refusal creates a synthetic or falsely attributed `AdminAction`;
- non-production bootstrap and seed behavior needed for local/development/portfolio setup remains available; and
- ordinary in-app administrator role changes continue using the existing authenticated audited workflow.

These tests replace the database-session and Firebase boundaries with sentinels/mocks where needed; no live Firebase or other provider call is required.

### 5.7 Shared Audit, Display, And Migration Compatibility

Prove that:

- the policy registry, ORM action-type constraint, and owning canonical `admin_actions` migration accept all five new action types and remain aligned;
- both Community Game detail actions require only the existing game target and do not introduce a new detail-target column;
- a fresh canonical upgrade creates nullable UUID `target_payment_event_id`, includes it in the target-required constraint, and creates its audit-target index without a foreign key to the later-created `payment_events` table;
- the single-head migration graph, full downgrade/re-upgrade lifecycle, model-to-head parity, and migration-drift checks remain clean without adding a repair migration;
- `target_payment_event_id` is allowed only by policies that explicitly permit it;
- audit-note correction of an `update_payment_event` action copies the payment-event target through the expanded shared target set without loading the provider event row;
- the audit model, canonical migration, API schema, target-field set, and display layer agree on the payment-event target;
- all five new actions use the exact display labels and primary-target order defined in the design;
- payment-event target rendering uses the dedicated ID-only branch and does not enter the ORM-backed target loader;
- list and detail rendering perform no `PaymentEvent` ORM query merely to label an `update_payment_event` action;
- `record_admin_action()` does not gain global mutation target-reference validation;
- tombstoned game and venue targets retain the existing fallback display behavior;
- active-admin-only audit reads remain unchanged; and
- existing action writers continue to satisfy the accepted append-only audit contract.

### 5.8 Transaction, Concurrency, And Safe-Error Compatibility

Use real PostgreSQL and independent sessions where database behavior is the safeguard. Prove that:

- target locks are acquired before audit snapshots/effective-change decisions and follow the accepted game-first and payment-event-before-job orders;
- concurrent same-target updates and deletions reach the deterministic results specified above without duplicate successful deletion actions;
- forcing synchronous recorder policy validation is translated to `503` with exactly `AUDIT_UNAVAILABLE_DETAIL` rather than the recorder's internal `400` detail;
- forcing an `admin_actions` insert constraint failure is identified through PostgreSQL diagnostics, rolls back the domain mutation, and returns the same stable `503` without table, constraint, SQL, or schema text;
- known pre-existing domain conflicts retain their established safe status/detail rather than being misclassified as audit failure;
- simulated commit uncertainty returns bounded safe behavior, is not automatically retried, and does not claim a known rollback outcome; and
- a post-commit refresh/serialization failure does not attempt to rewrite or roll back the already-committed immutable action.

Run the affected high-risk administrator authorization/inventory coverage together with focused Community Game detail, game, venue, payment-event, direct-script environment-boundary, administrative-audit, durable-job, database-concurrency, public-error, and canonical migration regressions. Then run the complete backend suite once because this pass changes the canonical `admin_actions` schema and the shared policy/display contract consumed by every audit writer. Also run the configured compile/lint checks for changed backend files, inspect the final diff for provider/private values in audit metadata and errors, and run `git diff --check`. No frontend/browser or live-provider execution is required because this pass does not change a client contract or provider interaction; backend serialization tests own the new audit labels and ID-only target display.

## 6. Done When

This pass is complete when the current important privileged-mutation surface has truthful durable attribution without duplicating domain truth.

- [ ] Generic administrator game updates create transactional `update_game` actions with safe changed-field metadata.
- [ ] Staff Community Game detail creation creates transactional `create_community_game_detail` actions targeting the owning game.
- [ ] Staff Community Game detail create/update actions use the exact repo-valid nested `support` metadata shapes and never store payment snapshot/instruction values.
- [ ] Generic administrator game soft deletion creates transactional `delete_game` actions with the exact bounded deletion metadata and without linking them into the `admin_soft_deleted` automatic review-case closure.
- [ ] Venue soft deletion creates transactional `delete_venue` actions with the exact bounded active/status/deletion metadata.
- [ ] Payment-event repair/reprocessing carries the authenticated administrator and creates `update_payment_event` only for an effective local mutation.
- [ ] True payment-event no-ops preserve the successful API contract without creating audit noise, any invoked idempotent durable-work ensure is audited as `ensured`, and `already_active` is used only when the payment-event itself changes.
- [ ] Payment-event `durable_work_action` is restricted to `none`, `ensured`, `requeued`, or `already_active`, with idempotent enqueue success classified truthfully as `ensured`.
- [ ] Payment-event audit metadata and display expose no provider event identifier, event type, envelope, provider timestamp, or processing-error content.
- [ ] Payment-event audit target rendering is ID-only and does not hydrate the provider event row merely to build the audit label.
- [ ] The five new action types and payment-event target are consistent across policy, ORM, the owning canonical migration, schemas, target-field handling, and display.
- [ ] `target_payment_event_id` is a nullable non-FK audit pointer because its target table is created later in the canonical migration sequence.
- [ ] Covered mutable targets are locked before audit state is derived; concurrent updates serialize truthfully, concurrent deletes produce one success action, and accepted lock ordering remains intact.
- [ ] Pre-commit audit-write failure rolls back each covered local mutation, including Community Game detail and payment-event durable-job changes, and returns only the stable audit-unavailable error; commit uncertainty remains bounded and is not blindly retried.
- [ ] Existing `AdminAction`, `AdminRejectedAttempt`, and authoritative domain/provider records remain non-duplicative.
- [ ] Bootstrap, demo-seed, and portfolio-seed callable entry points refuse `APP_ENV=production` before opening a database session, and no false/synthetic `AdminAction` attribution is introduced for those operational paths.
- [ ] Retired/rejected generic admin mutation scaffolds remain non-mutating and unaudited.
- [ ] Sensitive-read work remains outside this pass.
- [ ] Focused PostgreSQL/concurrency/error/migration proof and one complete backend regression confirm the new coverage without weakening existing audit authorization or append-only guarantees.
