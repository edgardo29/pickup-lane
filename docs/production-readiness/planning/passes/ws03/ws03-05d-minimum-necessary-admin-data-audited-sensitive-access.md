# WS03-05D - Minimum-Necessary Admin Data and Audited Sensitive Access

This pass minimizes sensitive data returned through existing admin moderation and audit surfaces, makes private-message access excerpt-first with explicit controlled reveal, and records sensitive administrative reads before protected content is disclosed.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

Pickup Lane already exposes private moderation and audit information to active administrators. Several of those responses are broader than the current admin tasks require: chat moderation lists preload full message bodies, review-case mutations return full sensitive detail, and some audit surfaces expose raw audit fields that the current UI does not use.

This work establishes a minimum-necessary disclosure boundary across those existing surfaces. Normal chat moderation becomes excerpt-first, full private-message content moves behind an explicit per-message reveal request, review-case detail is audited before disclosure, review-case mutation responses become acknowledgements rather than sensitive-detail responses, and audit collection/detail responses are narrowed to the data their existing workflows need.

The existing append-only administrative audit foundation supplies the reusable sensitive-read recording mechanism. This pass consumes that mechanism and registers the moderation-specific read actions required by these disclosures. The existing moderation taxonomy and evidence lifecycle, review-case lifecycle, enforcement behavior, admin-action immutability, authorization model, and centralized private/no-store response handling remain intact.

The authorization model remains binary: only an active administrator may use admin surfaces. This work does not introduce moderator or staff tiers, named permissions, generalized RBAC or ABAC, a second audit store, a privacy center, a new audit investigation product, a new export product, or a generalized data-access framework.

Cross-domain sensitive-read coverage outside the moderation and audit-context surfaces described here is outside this work.

### 1.1 Existing Chat Moderation Exposure

The shared admin chat response currently places unrestricted `message_body` in the normal moderation-row shape used by Community Game, Official Game, and Need a Sub moderation lists and mutation responses. The shared frontend moderation panel renders that body directly and reuses the already-loaded value when an administrator opens the message modal.

The current chat summary response also includes latest-message preview and lifecycle fields that the three admin summary UIs do not use. Those fields create another unaudited message-derived disclosure path.

The resulting system must therefore separate normal excerpt presentation from explicit full-content reveal at the API and schema level rather than hiding already-delivered full content in the frontend.

### 1.2 Existing Review-Case Exposure

Review-case detail intentionally contains bounded moderation evidence, signal context, events, and private administrator notes. That detail is sensitive even though it is already bounded.

The normal detail GET currently returns those fields without a sensitive-read audit, and note/close mutations return the full detail object as a side effect. The resulting system must keep the existing bounded review detail while making the detail GET the deliberate audited disclosure boundary.

### 1.3 Existing Audit-Context Exposure

The admin audit workspace already has a compact collection endpoint at `/admin/actions/log` and an explicit detail endpoint at `/admin/actions/{admin_action_id}`.

A second generic `/admin/actions` collection exposes the broad raw admin-action representation, including fields not needed by the current audit-list task. The Official Game Activity tab currently depends on that broad collection, so it must move to the compact log contract before the raw collection is retired.

The explicit audit-detail response and embedded domain audit histories must also be minimized to the fields their current interfaces use.

### 1.4 Existing Sensitive-Read Recording And Cache Behavior

The existing `record_sensitive_admin_read()` helper already owns the required audit transaction boundary. It opens a short-lived audit session, reloads and revalidates the active administrator, accepts only registered `sensitive_read` actions, validates typed targets, writes an immutable succeeded `AdminAction`, commits before returning, returns only the audit action UUID, fails closed with safe errors, and does not commit or roll back the caller's request-scoped session.

The existing API security-header middleware already applies `Cache-Control: private, no-store` to private admin responses. This work preserves and verifies that centralized behavior rather than duplicating route-specific cache logic.

## 2. What Must Be True

These requirements define the disclosure, authorization, audit, compatibility, and privacy behavior that must hold when this work is complete. They are intentionally specific where response shape or ordering is part of the security boundary.

### 2.1 Normal Chat Moderation Is Excerpt-First

Community Game, Official Game, and Need a Sub chat-moderation list responses must not contain unrestricted full message bodies.

The server-generated `message_excerpt` must reuse the existing `safe_chat_message_preview()` contract. That transformation is exact:

1. normalize surrounding and repeated whitespace using `" ".join(message_body.strip().split())`;
2. replace recognized phone-number matches with `[phone]`;
3. replace recognized email-address matches with `[email]`;
4. replace recognized link matches with `[link]`;
5. if the resulting string is at most 160 characters, return it unchanged;
6. otherwise return `preview[:157].rstrip() + "..."`.

The 160-character limit remains the single backend chat safe-preview bound. A second excerpt algorithm or independently configured excerpt length must not be introduced.

A normal moderation row contains exactly:

- `id`;
- `sender_display_name`;
- `message_excerpt`;
- `visibility_status`;
- `review_status`;
- `created_at`;
- `removed_source`; and
- `detections`.

Each detection contains exactly:

- `category`;
- `severity`.

The normal moderation row must not contain:

- `chat_id`;
- `sender_user_id`;
- `sender_initials`;
- `message_type`;
- `updated_at`;
- reviewer, remover, or restorer IDs or timestamps;
- detection IDs;
- `rule_key`;
- `matched_preview`;
- detection timestamps;
- unrestricted `message_body`;
- an alternate raw body field; or
- another field outside the exact normal-row contract.

The admin chat summary contains exactly:

- `chat_status`;
- `message_count`;
- `needs_review_count`;
- `removed_count`.

The summary must not contain `chat_id`, `latest_message_id`, `latest_message_preview`, `latest_message_at`, `created_at`, `updated_at`, or `closed_at`. Summary responses must not remain an alternate path for message-derived text.

The frontend must never receive the full body merely to truncate or redact it locally.

Where practical, list queries should avoid hydrating unrestricted message bodies. Regardless of query implementation, normal list serialization must make accidental full-body disclosure impossible.

The list envelope contains exactly:

- `messages`;
- `total_count`;
- `offset`;
- `limit`.

### 2.2 Full Private-Message Content Requires Explicit Reveal

Full message content may be returned only when an active administrator explicitly requests one specific message through a resource-bound reveal endpoint.

The reveal routes are:

- `/admin/community-games/{game_id}/chat/messages/{message_id}/content`
- `/admin/official-games/{game_id}/chat/messages/{message_id}/content`
- `/admin/need-a-sub/{post_id}/chat/messages/{message_id}/content`

Community Game and Official Game routes may share a backend primitive, but the caller must provide the expected game type and the service must enforce it.

The reveal response contains exactly:

- `id`;
- `message_body`.

The reveal route must not return the full moderation-row object or unrelated message metadata.

A reveal response is usable only by the UI context that initiated it. Each request must carry or be associated with a current request generation plus the parent resource kind and ID, selected message ID, and current moderation pagination/filter context. A success or error from that request may update reveal state only while all of those values still match and the component is still mounted with the reveal modal open for that message.

Closing the modal, selecting another message, changing the parent resource, changing pagination or filters, or unmounting the component invalidates the active reveal request. A late response from an invalidated request must be ignored and must never repopulate a stale full message body or stale reveal error into the current context. Request cancellation may be used as an optimization, but stale-response rejection is required even when cancellation races with completion.

### 2.3 Sensitive Reads Are Audited Before Protected Disclosure

A sensitive-read audit must durably commit before protected content is loaded for response serialization or returned to the caller.

The disclosure order is:

1. receive stable authenticated-actor and route/resource identifiers;
2. validate only the minimum identity or classification needed to establish the intended protected resource;
3. call `record_sensitive_admin_read()`;
4. allow the helper to reload and revalidate the administrator and durably commit the sensitive-read audit;
5. only after successful audit commit, load, serialize, and return the protected content.

Protected message bodies, review evidence, private notes, or other protected payload must not be preloaded and held in memory while the audit transaction is attempted.

If audit persistence fails or its commit outcome is uncertain, protected content is not disclosed.

Sensitive reads must use `record_sensitive_admin_read()`, not ordinary `record_admin_action()`.

### 2.4 Sensitive-Read Actions Are Resource-Specific

This work registers exactly five moderation-specific `sensitive_read` actions. Their policy is fully specified so consumers cannot add optional reason or metadata payloads during implementation.

All five actions use:

- `category = "sensitive_read"`;
- `outcome = "succeeded"`, generated by the sensitive-read helper;
- `requires_reason = False`;
- `metadata_builder_key = "none"`;
- `reason=None` at every D consumer call site;
- `metadata=None` at every D consumer call site.

The `"none"` metadata builder is a strict absence policy added to the existing centralized metadata validation path: it accepts only `metadata=None`, returns `None`, and rejects every non-`None` metadata value, including an empty object, with the existing safe validation behavior. No sensitive-read-specific metadata keys are added to another metadata profile.

These actions do not add a new recent-authentication requirement. They preserve the existing binary active-admin boundary and the helper-owned active-admin reload immediately before audit persistence.

The five actions therefore persist neither reason nor metadata.

For each action, the allowed target fields are exactly the required target fields listed below. No additional typed target may be attached.

#### 2.4.1 `read_game_chat_moderation`

Use this action when a non-empty Community Game or Official Game chat-moderation page returns private-message excerpts.

Allowed and required target:

- `target_game_id`.

#### 2.4.2 `reveal_game_chat_message_content`

Use this action for one explicit game-chat full-content reveal.

Allowed and required targets:

- `target_game_id`;
- `target_message_id`.

#### 2.4.3 `read_need_sub_chat_moderation`

Use this action when a non-empty Need a Sub chat-moderation page returns private-message excerpts.

Allowed and required target:

- `target_sub_post_id`.

#### 2.4.4 `reveal_need_sub_chat_message_content`

Use this action for one explicit Need a Sub chat-message full-content reveal.

Allowed and required targets:

- `target_sub_post_id`;
- `target_sub_chat_message_id`.

#### 2.4.5 `read_review_case_sensitive_detail`

Use this action when one bounded review-case detail response is disclosed.

Allowed and required target:

- `target_review_case_id`.

All five actions are server-generated, preserve the existing audit correlation behavior, and remain immutable through the existing `AdminAction` contract.

The policy registry and canonical database action-type constraint must remain in parity.

No new audit target column is required.

An empty chat moderation page that returns no message excerpt does not require a sensitive-read audit row. A count or identity query may determine that no protected content will be returned before deciding whether to record the read.

### 2.5 Authorization And Resource Binding Are Enforced In Services

Route dependencies remain defense in depth. Sensitive service functions must independently enforce active-admin access.

Direct service calls by any of the following must not disclose protected content:

- ordinary users;
- suspended administrators;
- deleted administrators;
- inactive administrators;
- an actor whose role or state becomes stale before the private audit transaction reloads it.

For game-chat reveal:

- the requested message must belong to the supplied `game_id`;
- a Community Game route may reveal only a Community Game message;
- an Official Game route may reveal only an Official Game message.

For Need a Sub reveal:

- the requested message must belong to the supplied `post_id`.

A valid message ID paired with the wrong parent or wrong game type must use the existing safe not-found convention and must not reveal cross-resource existence.

### 2.6 Chat Mutation Responses Do Not Disclose Full Content

Mark-reviewed, remove, and restore remain moderation mutations, not content-read endpoints.

Their success responses contain exactly:

- `message_id`;
- `audit_action_id`;
- `idempotent_replay`.

They must not contain unrestricted message bodies or a full moderation-row object.

The existing privileged-action audit remains the audit of the mutation. No additional sensitive-read record is created merely because the mutation response contains its minimum non-content acknowledgement fields.

The frontend must continue to obtain authoritative post-mutation state through its normal refresh path.

### 2.7 Review-Case Detail Is Audited And Mutation Responses Are Minimized

The field composition of the existing `AdminReviewCaseListRead` and `AdminReviewCaseDetailRead` contracts is preserved exactly. This pass does not add or remove list/detail fields; it changes the sensitive-detail disclosure boundary and the mutation response contracts.

The existing bounded review-case detail remains the sensitive detail surface. Before findings, evidence excerpts, signals, events, or private notes are loaded for the response:

1. validate the stable review-case identifier;
2. durably record `read_review_case_sensitive_detail`;
3. only then load and serialize the bounded detail.

The detail contract must not grow to include raw source message bodies or a new history explorer.

Add-note and close-case mutations use separate exact acknowledgement schemas and never return `AdminReviewCaseDetailRead`.

The add-note response contains exactly:

- `review_case_id: UUID`;
- `case_version: int`, the positive resulting/current case version;
- `note_id: UUID`, identifying the newly created note or the original note on exact replay;
- `audit_action_id: UUID`, identifying the note mutation audit action and returning the original action ID on exact replay;
- `idempotent_replay: bool`.

The close response contains exactly:

- `review_case_id: UUID`;
- `case_version: int`, the positive resulting/current case version;
- `case_status: "closed"`;
- `closure_outcome`, one of `enforcement_applied`, `no_action_needed`, or `invalid_signal`;
- `audit_action_id: UUID`, identifying the close mutation audit action and returning the original action ID on exact replay;
- `idempotent_replay: bool`.

Neither mutation response contains note body, findings, evidence, signals, events, private notes, target detail, or another field from the full review-case detail projection.

After every successful add-note or close response, including an exact idempotent replay, the still-mounted review-case detail page must issue the normal audited detail GET for the same `review_case_id` before replacing the displayed authoritative case detail. It must not reconstruct or synthesize authoritative detail from the acknowledgement response.

The separate Review Cases collection behavior remains unchanged. This pass does not add a new list-refresh mechanism to the detail page.

The existing review-case target-first locking, `case_version`, note, closure, event, and idempotency behavior must remain unchanged. The existing conflict codes remain exact: `review_case_version_conflict` for stale expected versions, `review_case_idempotency_conflict` for reuse of an idempotency key with a different request fingerprint, and `review_case_transition_conflict` for invalid surviving transitions or inconsistent replay/target state.

### 2.8 Audit Context Is Minimum-Necessary

Audit-ledger reads themselves do not generate recursive sensitive-read audit rows. The API contracts below are exact; fields not listed are not returned by that response.

The shared audit reason preview has one exact server-side transformation. Normalize with `" ".join((reason or "").split())`. If the normalized value is empty, return `None`. If it is at most 140 characters, return it unchanged. Otherwise return `normalized[:137] + "..."`. This existing 140-character preview contract is reused by every compact audit row that exposes `reason_preview`.

#### 2.8.1 Global Audit Collection

`/admin/actions/log` remains the global collection used by the admin Audit workspace.

Each global compact-log row contains exactly:

- `id: UUID`;
- `action_label: str`;
- `admin_label: str`;
- `target_label: str`;
- `reason_preview: str | None`;
- `created_at: datetime`.

It does not return raw administrator IDs/email, outcome, target kind, raw target columns, duplicate target summaries, destination fields, metadata, correlation, idempotency identity, or full reason.

For compact audit responses, `admin_label` is the administrator's trimmed first/last name when one is available; otherwise it is `Admin ` followed by the first eight characters of the administrator UUID. It never falls back to email. For a user primary target, the compact target label similarly uses the user's trimmed first/last name when available and otherwise `User ` plus the first eight characters of the user UUID; it does not use email as a target-label fallback. Other target labels continue to use their existing non-raw display rules.

The normal global log envelope contains exactly:

- `actions: list[AdminActionLogItemRead]`;
- `action_type_options: list[AdminActionLogActionTypeOptionRead]`;
- `limit: int`;
- `next_cursor: str | None`;
- `has_more: bool`.

Each `action_type_options` item contains exactly:

- `action_type: str`;
- `label: str`.

The options remain available on the normal global audit collection because the current Audit workspace uses them for its action-type filter.

#### 2.8.2 Explicit Audit Detail

`/admin/actions/{admin_action_id}` remains the explicit audit-detail endpoint.

Its response uses a dedicated minimum-necessary model and contains exactly:

- `id: UUID`;
- `action_type: str`;
- `action_label: str`;
- `admin_label: str`;
- `admin_email: str | None`;
- `created_at: datetime`;
- `reason: str | None`;
- `primary_target: AdminActionTargetSummaryRead | None`.

`AdminActionTargetSummaryRead` contains exactly:

- `target_type_label: str`;
- `label: str`;
- `destination_path: str | None`.

The detail does not expose raw audit metadata, outcome, correlation ID, idempotency key, administrator UUID, a separate target-user email field, every typed target field, secondary target-detail arrays, raw target field/type/ID values, or other unused `AdminAction` internals. The `admin_label` and user-target label use the non-email fallback rules defined in section 2.8.1. The stored reason remains available on this explicit detail surface because the current detail UI displays it; list and embedded-history surfaces receive only the 140-character preview.

#### 2.8.3 Broad Raw Collection And Official Game Activity

The generic raw `GET /admin/actions` collection must not remain as an alternate bulk-disclosure path.

The Official Game Activity caller must move to `/admin/actions/log` before the frontend `listAdminActions` helper and the broad raw collection route are retired.

The compact log supports `target_game_id` as an allowed filter. The cursor payload and `query_context_hash` validation bind `target_game_id` together with the existing filters so a cursor issued for one game cannot be replayed against another game or against an unfiltered collection.

The compact log keeps one response envelope for both the global Audit workspace and `target_game_id` queries. When `target_game_id` is present for Official Game Activity, the envelope still contains exactly:

- `actions: list[AdminActionLogItemRead]`;
- `action_type_options: list[AdminActionLogActionTypeOptionRead]`;
- `limit: int`;
- `next_cursor: str | None`;
- `has_more: bool`.

For a `target_game_id` response, `action_type_options` is exactly an empty list because Official Game Activity does not provide an action-type filter. This avoids returning the unrelated global option catalog without introducing a second collection-envelope shape.

The Official Game Activity tab automatically loads at most two compact-log pages of 50 rows each. It stops after the second page even if another cursor exists, preserving the current maximum of 100 recent actions without adding pagination UI.

Each Activity card displays exactly:

- Action, from `action_label`;
- Target, from `target_label`;
- Changed by, from `admin_label`;
- When, from `created_at`;
- Log reference, from `id`.

The cards must not display a separate player email or administrator email and must not require raw target columns, raw emails, metadata, correlation, idempotency identity, full reason, or action-type options.

Internal bounded target-scoped audit retrieval may remain where domain services genuinely need it. Internal reuse does not justify exposing the broad raw HTTP collection.

#### 2.8.4 Embedded Audit Histories

The complete current embedded `AdminAction` history population covered by this minimization is:

- Community Game detail `audit_actions`;
- Need a Sub post detail `audit_actions`;
- Admin User detail `audit_actions`;
- admin Money detail `audit_actions`;
- admin Notification detail `audit_actions` and `audit_action_count`.

Embedded audit rows are minimized per current UI task rather than forced into a broader union shape.

Community Game detail `audit_actions` rows contain exactly:

- `id: UUID`;
- `action_label: str`;
- `reason_preview: str | None`;
- `created_at: datetime`.

Need a Sub post detail `audit_actions` rows contain exactly:

- `id: UUID`;
- `action_label: str`;
- `reason_preview: str | None`;
- `created_at: datetime`.

Admin User detail `audit_actions` rows contain exactly:

- `id: UUID`;
- `action_label: str`;
- `admin_label: str`;
- `reason_preview: str | None`;
- `created_at: datetime`.

Admin Money detail `audit_actions` rows contain exactly:

- `id: UUID`;
- `action_label: str`;
- `admin_label: str`;
- `reason_preview: str | None`;
- `created_at: datetime`.

These rows use the same 140-character reason-preview transformation defined above. Community Game and Need a Sub do not gain administrator identity that their current embedded histories do not display. Admin User and Money preserve the responsible-administrator context their current UIs use, but expose a display label instead of a raw administrator UUID.

None of these embedded rows exposes `action_type`, administrator email, raw reason, metadata, raw target columns, target kind, correlation, idempotency identity, or other unused audit internals. Existing enclosing pagination/count fields remain unchanged where those detail endpoints already provide them.

The admin Notification detail UI does not render its embedded audit-action collection. Its `audit_actions` and `audit_action_count` fields are therefore removed from the notification detail response rather than replaced with another unused summary.

No new audit screen or second audit-detail workflow is introduced.

### 2.9 Necessary Moderation Context Remains Available

Minimum-necessary does not mean removing every field that appears personal or financial.

Existing operational fields needed to understand and moderate a Community Game or Need a Sub target remain available, including legitimate game/post state and payment context required by the existing moderation task.

A field is removed or minimized only when it is unnecessary for the existing admin task or when the same task can use a safer excerpt/detail boundary.

### 2.10 Sensitive Responses Remain Private And Non-Cacheable

All admin responses covered by this work continue to receive:

`Cache-Control: private, no-store`

through the existing centralized security-header mechanism.

This must hold for representative:

- chat moderation lists;
- full-message reveal responses;
- review-case detail;
- audit log;
- audit detail.

Route-specific cache handling is not added unless a verified path bypasses the centralized mechanism.

### 2.11 No Unrestricted Sensitive Export Exists

This work must not create or retain a bulk/raw export path for:

- chat bodies;
- review evidence;
- private review notes;
- raw audit records.

Existing admin routes and frontend API calls must not provide an unrestricted export-equivalent path for the protected content covered here. The broad raw `/admin/actions` collection is not an acceptable substitute for a bounded audit interface.

### 2.12 Existing Behavior And Security Boundaries Remain Compatible

The implementation must preserve:

- Community Game, Official Game, and Need a Sub ownership and type checks;
- the four-field chat summary contract and existing moderation views;
- existing pagination limits;
- mark-reviewed, remove, and restore semantics;
- moderation mutation idempotency;
- existing moderation notices and enforcement behavior;
- the bounded review-case detail model except for the new audited disclosure boundary;
- review-case locking, version, conflict, note, closure, event, and idempotency behavior;
- append-only `AdminAction` behavior;
- active-admin-only audit access;
- the existing audit-log list/detail user workflow;
- Official Game Activity's bounded recent-history behavior with at most 100 actions and no pagination UI;
- centralized private-route cache handling;
- existing guest and public privacy behavior.

The following security properties must hold across the implementation:

- normal chat lists never return unrestricted bodies;
- chat mutation responses never return unrestricted bodies;
- full message bodies require explicit resource-bound reveal;
- protected reads are durably audited before disclosure;
- direct service callers cannot bypass active-admin authorization;
- cross-parent and cross-type identifiers cannot reveal content;
- review-case detail stays bounded and is audited before disclosure;
- review mutations do not return sensitive detail for convenience;
- audit reason/metadata never contains the protected content being read;
- audit collection/detail payloads do not expose unused raw internal audit state;
- audit reads do not recursively audit themselves;
- frontend revealed-content state is ephemeral;
- no unrestricted sensitive export exists; and
- existing privileged mutation semantics are not weakened.

## 3. Design

The implementation separates normal minimum-necessary list data from explicit sensitive detail, uses the existing audit helper as the commit-before-disclosure boundary, and keeps each API response structurally incapable of exposing data its task does not require.

### 3.1 Chat API And Schema Separation

Normal chat summary, moderation-row, reveal, and mutation responses use distinct schema types.

The summary schema contains only:

- `chat_status`;
- `message_count`;
- `needs_review_count`;
- `removed_count`.

The moderation-row schema contains only:

- `id`;
- `sender_display_name`;
- `message_excerpt`;
- `visibility_status`;
- `review_status`;
- `created_at`;
- `removed_source`;
- `detections`.

Each moderation-row detection contains only:

- `category`;
- `severity`.

The reveal schema contains only:

- `id`;
- `message_body`.

The mutation-result schema contains only:

- `message_id`;
- `audit_action_id`;
- `idempotent_replay`.

The list envelope contains only:

- `messages`;
- `total_count`;
- `offset`;
- `limit`.

The shared chat moderation service generates `message_excerpt` by calling the existing `safe_chat_message_preview()` helper. That helper's whitespace collapse, phone/email/link redaction, 160-character maximum, and `...` truncation behavior defined in section 2.1 are the single excerpt contract. The implementation does not create a second safe-preview implementation.

The existing broad admin chat response type may be split or replaced as needed, but the final response-model boundary must make normal full-body serialization impossible.

A non-empty excerpt page records the applicable game-chat or Need a Sub chat sensitive read before excerpts are serialized and returned. Empty pages do not create a sensitive-read audit.

Reveal services validate the stable parent/message relationship and expected game type before recording the resource-specific read action. They load the unrestricted body only after the audit helper returns successfully.

Mutation serializers return only the minimum acknowledgement and do not reuse reveal or list serializers.

### 3.2 Sensitive-Read Policy And Persistence

The five actions defined in section 2.4 are registered in the existing admin-action policy with the exact category, target, reason, metadata, and active-admin behavior frozen there.

All five policy entries use `metadata_builder_key="none"`. The dedicated `"none"` metadata branch rejects every non-`None` metadata input, including `{}`, and D consumers always call `record_sensitive_admin_read()` with `reason=None` and `metadata=None`. No new sensitive-read metadata keys are added to the existing audit metadata allowlist.

The canonical database finite action set remains synchronized with the policy registry. The existing typed targets are sufficient, so this work adds no new target column and no second audit table.

The current pre-production canonical-migration approach remains in use for the action-type finite set. The implementation does not introduce a repair migration solely for these new action names.

The sensitive-read call flow uses the existing `record_sensitive_admin_read()` helper without changing its foundational transaction contract.

Before calling the helper, the consumer may perform only the minimum lookup needed to establish stable target identity or classification. It must not hydrate the protected payload that the request is attempting to disclose.

After the helper commits and returns its audit UUID, the consumer may load and serialize the protected response.

### 3.3 Review-Case Disclosure And Mutation Results

The review-case service preserves the field composition of the existing `AdminReviewCaseListRead` and `AdminReviewCaseDetailRead` schemas exactly.

Detail retrieval is split into two phases:

1. establish the stable review-case identity needed to record the read;
2. after `read_review_case_sensitive_detail` commits, load the bounded findings, evidence excerpts, signals, events, and private notes required by the unchanged detail response.

Add-note and close-case operations keep their existing transaction, locking, case-version, idempotency, replay, and conflict behavior. Their response builders use the exact acknowledgement schemas in section 2.7 and no longer depend on the full sensitive detail model.

For an exact add-note replay, `note_id` is the ID of the originally committed note. For an exact close replay, the acknowledgement reports the existing closed case version and original closure outcome without creating another close effect.

After every successful new or replayed note/close response, the review-case page performs the audited detail GET for the same case before replacing the displayed authoritative detail. The acknowledgement is never used to synthesize a full case projection.

### 3.4 Audit Collection, Detail, And Embedded-History Minimization

The audit display layer owns the exact compact representations defined in section 2.8.

The global compact log serializes only `id`, `action_label`, `admin_label`, `target_label`, `reason_preview`, and `created_at`. The normal global envelope includes the action-type option list used by the current filter UI. A `target_game_id` Activity response keeps the same envelope but returns `action_type_options=[]` as defined in section 2.8.3.

The shared reason-preview builder keeps its current exact 140-character normalization/truncation behavior and is reused by the global log and all compact embedded rows.

Audit detail uses its own minimum-necessary response model with one compact primary-target summary. It does not inherit from `AdminActionRead` and does not serialize the broad typed target set or `target_details` array.

The broad raw HTTP collection is removed after its remaining frontend caller moves to the compact log. The compact log query supports `target_game_id`, and that filter is part of the cursor context. Cursor validation rejects reuse when the game filter or other bound query context changes.

Community Game, Need a Sub, Admin User, and Money details use the exact per-surface embedded audit rows from section 2.8.4. Notification detail removes its unused `audit_actions` and `audit_action_count` response fields.

Audit-log, audit-detail, and embedded audit-history reads do not call `record_sensitive_admin_read()` because the audit ledger is not recursively audited.

### 3.5 Shared Chat Moderation Frontend

The shared admin chat moderation panel renders `message_excerpt` during normal browsing and does not keep unrestricted message bodies in list state.

When an administrator explicitly opens a message for full content, the panel:

- issues the separate reveal request for that selected message;
- captures a current reveal request generation together with parent resource kind/ID, selected message ID, and current pagination/filter context;
- shows a loading state while the reveal is pending;
- shows a safe reveal error without breaking moderation controls;
- applies a reveal success or error only if its request generation and complete captured context still match the mounted, open modal's current context;
- stores an accepted revealed body only in component-local state for the selected message;
- invalidates the active reveal generation and clears the revealed body when the modal closes;
- invalidates and clears it when the selected message changes;
- invalidates and clears it when parent context changes;
- invalidates and clears it when pagination or filter context changes;
- invalidates it when the component unmounts;
- ignores late successes and errors from invalidated requests;
- may additionally abort obsolete network requests, but does not rely on cancellation alone for stale-response safety;
- never places the revealed body in URL or query parameters;
- never places it in browser storage;
- never places it in persistent or global application state;
- never places it in telemetry payloads; and
- never writes it to console logging.

Existing mark-reviewed, remove, and restore behavior remains available.

### 3.6 Review-Case Frontend

The review-case page no longer expects note or close mutations to return a full detail object.

After every successful new or idempotently replayed add-note or close request, the page uses the exact acknowledgement only for mutation completion and performs a fresh audited GET for that same case before replacing the displayed authoritative detail. It does not locally reconstruct case detail from the acknowledgement.

Existing stale-version conflict handling and authoritative reload behavior remain unchanged.

### 3.7 Audit Workspace And Official Game Activity

The existing Audit workspace keeps its list-then-detail interaction and consumes the exact global compact-log and minimum-detail contracts from section 2.8.

The global Audit workspace receives `action_type_options` because it renders the action-type filter. Individual log rows use only the six fields defined in section 2.8.1, and the detail modal uses the dedicated detail response rather than relying on broad list target data.

The Official Game Activity tab uses compact-log requests filtered by `target_game_id`. Those responses return `action_type_options=[]`. The tab loads the first 50-row page and follows at most one returned cursor for a second 50-row page. It never requests a third page and adds no pagination UI.

Activity presentation uses only Action, Target, Changed by, When, and Log reference as defined in section 2.8.3.

Community Game, Need a Sub, Admin User, and Money embedded audit-history UIs consume the exact per-surface compact rows defined in section 2.8.4. Notification detail stops receiving the unused embedded audit collection.

### 3.8 Compatibility And Data-Minimization Discipline

The implementation should remove sensitive or unnecessary response data only where the existing task does not need it or where a safer excerpt/detail boundary is defined in this plan.

It must not indiscriminately strip operational game/post state or payment context needed for moderation.

Existing moderation, review-case, audit, enforcement, authorization, pagination, and notification behavior remains unchanged except for the deliberate response minimization and disclosure/audit boundaries defined here.

## 4. Failures And Edge Cases

These cases define how the sensitive-access boundary behaves when authorization, resource identity, audit durability, navigation context, or protected-content retrieval does not proceed normally.

1. **Administrator is no longer authorized**
   - **Condition:** The route previously authenticated an administrator, but the actor is ordinary, suspended, deleted, inactive, or has become stale before the sensitive-read helper reloads the account.
   - **Required behavior:** The service and helper reject the read using the existing safe authorization behavior. No protected body, evidence, private note, or other protected response data is returned.

2. **Message belongs to another parent**
   - **Condition:** A valid game-chat or Need a Sub message ID is supplied with the wrong `game_id` or `post_id`.
   - **Required behavior:** Use the existing concealed not-found or safe 4xx convention. Do not reveal whether the message exists under another parent and do not return content.

3. **Game message is requested through the wrong game type**
   - **Condition:** A Community Game message is requested through an Official Game reveal route, or an Official Game message is requested through a Community Game reveal route.
   - **Required behavior:** Reject through the existing safe not-found behavior without revealing cross-type existence or content.

4. **Sensitive-read validation fails**
   - **Condition:** The actor, action policy, target shape, or minimum resource classification is invalid.
   - **Required behavior:** Return the established safe 4xx result and disclose no protected content.

5. **Sensitive-read audit cannot be durably recorded**
   - **Condition:** Audit insertion, flush, database access, commit, or commit-outcome certainty fails.
   - **Required behavior:** Fail closed with the established safe audit-unavailable response, including the stable `503` behavior for durability or commit uncertainty. Do not load or return protected content and do not expose database internals.

6. **Chat moderation page is empty**
   - **Condition:** A moderation page contains no message excerpt to disclose.
   - **Required behavior:** Return the normal empty bounded page without creating a sensitive-read audit solely for the empty result.

7. **Full-message reveal request fails after the normal list loaded**
   - **Condition:** The explicit reveal request is denied, not found, or fails because auditing or retrieval cannot complete.
   - **Required behavior:** Keep the normal excerpt-first moderation interface usable, show a safe reveal error, and retain no stale full body from another message or context.

8. **Audit cursor is reused under a different game context**
   - **Condition:** A compact-log cursor issued with one `target_game_id` is submitted with another game ID or without the original game filter.
   - **Required behavior:** Reject the cursor using the existing safe invalid-cursor behavior. Do not return records from a different query context.

9. **A mutation succeeds but refreshed sensitive detail is unavailable**
   - **Condition:** A chat moderation or review-case mutation commits successfully, but the subsequent normal refresh or audited detail request fails.
   - **Required behavior:** Do not reinterpret the mutation as failed and do not embed protected detail in the mutation response as a fallback. The UI shows the mutation acknowledgement/current minimum state it has and allows a later authoritative refresh.

10. **Unexpected internal error occurs around a sensitive read**
    - **Condition:** Database, provider, serialization, or other internal code raises while a protected response is being prepared.
    - **Required behavior:** Return only the existing sanitized error response. SQL, database parameters, provider internals, exception payloads, protected message text, moderation evidence, and private notes must not appear in the client response.

11. **A stale reveal response completes after UI context changes**
    - **Condition:** A reveal request completes after the modal closes, another message is selected, the parent resource changes, pagination or filters change, or the component unmounts.
    - **Required behavior:** The late success or error fails the current request-generation/context check and is ignored. It must not repopulate a full body or stale error into the new/current context, even if network cancellation did not prevent completion.

12. **Sensitive response attempts to bypass centralized cache handling**
    - **Condition:** A covered route does not receive the normal private-route security-header behavior.
    - **Required behavior:** The implementation must correct the verified bypass without weakening the centralized `private, no-store` contract or creating inconsistent caching behavior across equivalent admin surfaces.

## 5. Testing

Testing must prove that minimum-necessary response shapes are enforced at the API boundary, protected data is audited before disclosure, resource binding cannot be bypassed, frontend full-content state remains ephemeral, and the existing moderation/review/audit behavior does not regress. Real PostgreSQL is required where audit transactions, commit ordering, constraints, or cursor/query behavior depend on database semantics.

### 5.1 Chat Minimum-Necessary Contract

For Community Game, Official Game, and Need a Sub moderation, verify:

- summary JSON contains exactly `chat_status`, `message_count`, `needs_review_count`, and `removed_count`;
- summary JSON contains no latest-message preview or removed identity/lifecycle fields;
- `message_excerpt` uses the existing `safe_chat_message_preview()` transformation;
- whitespace runs are collapsed before redaction and truncation;
- recognized phone, email, and link matches are replaced with `[phone]`, `[email]`, and `[link]` before the length check;
- a transformed value of 160 characters or fewer is returned unchanged;
- a transformed value longer than 160 characters is exactly `preview[:157].rstrip() + "..."`;
- no second excerpt limit or alternate excerpt algorithm exists;
- normal list rows contain exactly the fields in section 2.1;
- detections contain exactly `category` and `severity`;
- list responses contain no unrestricted body, alternate raw body, reviewer/remover/restorer identities or timestamps, `matched_preview`, `rule_key`, or other detection internals;
- the frontend renders the server excerpt rather than a hidden full body;
- pagination and moderation-view behavior remain correct;
- the list envelope contains exactly `messages`, `total_count`, `offset`, and `limit`; and
- mark-reviewed, remove, and restore responses contain exactly `message_id`, `audit_action_id`, and `idempotent_replay`.

### 5.2 Controlled Reveal And Resource Binding

Verify:

- an active administrator can reveal one valid Community Game message;
- an active administrator can reveal one valid Official Game message;
- an active administrator can reveal one valid Need a Sub message;
- the reveal response contains exactly `id` and `message_body`;
- the message must belong to the routed parent;
- Community Game and Official Game type binding is enforced;
- wrong-parent and wrong-type combinations disclose no content and do not reveal cross-resource existence;
- full body is returned only after the sensitive-read audit commits;
- audit failure returns no body; and
- raw database or internal details are not exposed.

### 5.3 Sensitive-Read Audit Integration

Using real PostgreSQL where transaction behavior matters, verify:

- all five actions in section 2.4 are registered as `sensitive_read` with exactly their allowed/required target fields;
- all five have `category="sensitive_read"`, `requires_reason=False`, and `metadata_builder_key="none"`;
- every D sensitive-read call site passes `reason=None` and `metadata=None`;
- any non-`None` metadata input is rejected by the `none` metadata policy and no new sensitive-read metadata keys are accepted;
- policy and canonical database action finite sets remain in parity;
- successful protected reads create immutable succeeded audit records with the correct actor, typed targets, database time, and correlation behavior;
- those sensitive-read records persist `reason IS NULL` and no metadata payload;
- protected body/evidence/private notes are not loaded or serialized before audit commit;
- ordinary, suspended, deleted, inactive, and stale administrators fail after the helper-owned reload;
- the helper does not commit or roll back unrelated pending work in the caller's request-scoped session;
- audit durability or commit uncertainty prevents disclosure; and
- protected payload canaries never appear in audit reason, metadata, logs, or returned errors.

Existing audit-foundation tests continue to prove the helper's generic transaction behavior. Tests for this work prove that each concrete consumer uses that helper correctly.

### 5.4 Review-Case Response Contract

Verify:

- `AdminReviewCaseListRead` and `AdminReviewCaseDetailRead` field composition remains unchanged;
- detail retrieval records `read_review_case_sensitive_detail` before loading or returning evidence, signals, events, and private notes;
- audit failure prevents detail disclosure;
- detail does not gain raw source message bodies or a new history explorer;
- add-note responses contain exactly `review_case_id`, `case_version`, `note_id`, `audit_action_id`, and `idempotent_replay` with the types defined in section 2.7;
- exact add-note replay returns the original `note_id` and original `audit_action_id` and creates no duplicate effect;
- close responses contain exactly `review_case_id`, `case_version`, `case_status`, `closure_outcome`, `audit_action_id`, and `idempotent_replay` with the types and finite values defined in section 2.7;
- exact close replay returns the existing closed state, original closure outcome, and original `audit_action_id` and creates no duplicate effect;
- neither mutation response contains full review detail or note body;
- after every successful new or replayed note/close, the still-mounted detail page obtains authoritative detail through the audited GET before replacing displayed detail; and
- existing target-first locking, case-version, note, closure, event, idempotency, and exact conflict codes (`review_case_version_conflict`, `review_case_idempotency_conflict`, `review_case_transition_conflict`) remain correct.

### 5.5 Audit-Context Minimization

Verify:

- each global `/admin/actions/log` row contains exactly `id`, `action_label`, `admin_label`, `target_label`, `reason_preview`, and `created_at`;
- the global log envelope contains exactly `actions`, `action_type_options`, `limit`, `next_cursor`, and `has_more`;
- each `action_type_options` item contains exactly `action_type` and `label`;
- compact `admin_label` uses trimmed administrator first/last name when available and otherwise `Admin ` plus the first eight UUID characters, never email;
- compact user-target labels use trimmed user first/last name when available and otherwise `User ` plus the first eight UUID characters, never email;
- a blank normalized reason produces `reason_preview=None`;
- `reason_preview` collapses whitespace, is unchanged through 140 characters, and when longer equals the first 137 normalized characters followed directly by `...`;
- `/admin/actions/{admin_action_id}` contains exactly the eight fields defined in section 2.8.2;
- audit detail `primary_target`, when present, contains exactly `target_type_label`, `label`, and `destination_path`;
- raw metadata, outcome, correlation, idempotency identity, administrator UUID, target-user email, typed target columns, and secondary target-detail arrays are absent from the minimized API responses;
- the broad generic raw `/admin/actions` HTTP collection no longer provides an alternate bulk raw response;
- Official Game Activity uses the compact log filtered by `target_game_id`;
- the `target_game_id` response keeps the normal five-field envelope and returns `action_type_options=[]`;
- `target_game_id` is bound into cursor query context;
- a cursor cannot be reused for another game or without its original game filter;
- Official Game Activity loads one 50-row page when sufficient;
- it follows at most one cursor for a maximum of 100 rows;
- it never requests a third page;
- it renders exactly Action, Target, Changed by, When, and Log reference;
- it does not render separate player or administrator emails;
- Community Game and Need a Sub embedded rows contain exactly `id`, `action_label`, `reason_preview`, and `created_at`; Admin User and Money embedded rows additionally contain `admin_label`;
- those embedded rows use the same 140-character reason-preview contract;
- Notification detail no longer returns `audit_actions` or `audit_action_count`; and
- audit-log/detail and embedded-history reads do not create recursive sensitive-read actions.

### 5.6 Frontend Sensitive-State Behavior

Verify the shared chat moderation UI:

- renders excerpts in normal rows;
- does not receive full bodies in list state;
- makes a separate reveal request only for explicit full-content viewing;
- associates every reveal with a request generation, parent kind/ID, message ID, and pagination/filter context;
- shows reveal loading and safe error states only for the current valid request context;
- keeps an accepted revealed body only in local state for the selected message;
- invalidates and clears reveal state on modal close, message change, parent/context change, pagination/filter change, and unmount;
- ignores a delayed successful reveal after modal close;
- ignores a delayed successful reveal after selecting another message;
- ignores a delayed successful reveal after pagination or filter change;
- ignores a delayed successful reveal after parent-resource change;
- ignores delayed success or error after unmount;
- does not rely solely on request cancellation to prevent stale state;
- does not place revealed content in URL/query state, browser storage, persistent/global state, telemetry, or console output; and
- preserves existing moderation controls and refresh behavior.

Verify the review-case UI uses only the exact note/close acknowledgements, obtains authoritative case detail through the audited GET after every successful new or replayed mutation, and retains its existing stale-version recovery behavior.

### 5.7 Cache And Export Protection

Verify representative chat list, reveal, review-detail, audit-log, and audit-detail responses receive:

`Cache-Control: private, no-store`.

Verify the current admin route and frontend API surface provides no unrestricted bulk/raw export-equivalent path for chat bodies, review evidence, private review notes, or raw audit records.

### 5.8 Regression And Compatibility

Run focused regression coverage for the affected behavior, including:

- administrative audit;
- Community Game chat moderation;
- Official Game chat moderation;
- Need a Sub chat moderation;
- review cases;
- admin audit UI behavior;
- frontend moderation behavior;
- migration/model/policy parity;
- response-security headers;
- moderation mutation idempotency;
- moderation notices and enforcement integration.

Also run formatting, lint, compilation, static validation, and `git diff --check` appropriate to the changed code.

Broader regression suites are warranted when the final shared change footprint or a concrete regression concern requires them. A broad green suite does not replace the specific semantic proof above.

## 6. Done When

This checklist defines the engineering completion bar for WS03-05D.

- [ ] Admin chat summaries contain exactly `chat_status`, `message_count`, `needs_review_count`, and `removed_count`.
- [ ] Normal moderation rows and detections match the exact minimum-necessary fields defined in section 2.1.
- [ ] `message_excerpt` reuses `safe_chat_message_preview()` with whitespace collapse, `[phone]`/`[email]`/`[link]` redaction, a 160-character maximum, and exact `preview[:157].rstrip() + "..."` truncation.
- [ ] Normal chat lists and summaries provide no alternate unrestricted or message-preview disclosure path.
- [ ] Full message bodies are returned only through explicit resource-bound reveal endpoints.
- [ ] Reveal responses contain exactly `id` and `message_body`.
- [ ] Game/post parent binding and Community/Official type binding prevent cross-resource disclosure.
- [ ] Late reveal successes or errors cannot repopulate state after modal close, message/context/page/filter change, parent change, or unmount.
- [ ] Mark-reviewed, remove, and restore responses contain only `message_id`, `audit_action_id`, and `idempotent_replay`.
- [ ] The five resource-specific sensitive-read actions use the exact target policies in section 2.4, `reason=None`, `metadata=None`, `metadata_builder_key="none"`, and remain in policy/database parity.
- [ ] Every protected read covered by this work durably records its sensitive-read audit before protected content is loaded for response serialization or disclosed.
- [ ] Audit failure or commit uncertainty fails closed without protected disclosure or internal error detail.
- [ ] Direct service calls cannot bypass active-admin authorization.
- [ ] `AdminReviewCaseListRead` and `AdminReviewCaseDetailRead` field composition remains unchanged while review-case detail becomes audited before sensitive fields are loaded.
- [ ] Add-note responses contain exactly `review_case_id`, `case_version`, `note_id`, `audit_action_id`, and `idempotent_replay`.
- [ ] Close responses contain exactly `review_case_id`, `case_version`, `case_status`, `closure_outcome`, `audit_action_id`, and `idempotent_replay`.
- [ ] New and replayed review mutations obtain authoritative case detail only through the audited detail GET; no new detail-page list-refresh mechanism is introduced.
- [ ] Existing review-case target-first locking, version, idempotency, replay, event, and closure behavior remains unchanged, including the exact `review_case_version_conflict`, `review_case_idempotency_conflict`, and `review_case_transition_conflict` codes.
- [ ] Global `/admin/actions/log` rows and envelopes match the exact compact contracts in section 2.8.1.
- [ ] Compact administrator and user-target labels never use email as a fallback and use the exact name/short-ID fallback rules in section 2.8.1.
- [ ] Audit reason previews use the exact existing 140-character normalization/truncation contract, including `None` for a blank normalized reason.
- [ ] Audit detail uses the exact eight-field minimum response and three-field primary-target summary in section 2.8.2.
- [ ] The broad raw `/admin/actions` HTTP collection no longer exposes an alternate bulk response.
- [ ] `target_game_id` filtering is supported by the compact log and bound into cursor query context.
- [ ] `target_game_id` Activity responses keep the normal envelope and return `action_type_options=[]` as defined in section 2.8.3.
- [ ] Official Game Activity loads at most two 50-row compact-log pages and displays only Action, Target, Changed by, When, and Log reference.
- [ ] Community Game, Need a Sub, Admin User, and Money embedded audit histories use the exact per-surface compact contracts in section 2.8.4.
- [ ] Notification detail no longer returns its unused embedded `audit_actions` or `audit_action_count`.
- [ ] Audit-log, audit-detail, and embedded-history reads do not recursively generate sensitive-read audit records.
- [ ] Existing operational moderation context needed for the current task remains available.
- [ ] Covered sensitive admin responses continue to receive `Cache-Control: private, no-store`.
- [ ] No unrestricted export-equivalent path remains for chat bodies, review evidence, private review notes, or raw audit records.
- [ ] Revealed message bodies remain ephemeral and never enter URLs, browser storage, persistent/global state, telemetry, or console logging.
- [ ] Existing moderation, review-case, audit, enforcement, authorization, pagination, notification, and guest/public privacy behavior remains correct.
- [ ] Focused backend, frontend, PostgreSQL, migration/model/policy, cache-header, and regression validation passes.
