# WS09-02C - Sensitive Administrative-Read Audit Coverage

## 1. Gate A Result

**Gate A status: corrected plan candidate; independent read-only plan review pending before Gate B.**

`WS09-02C` remains a coherent executable child of `WS09-02`. The accepted decomposition assigns it the remaining cross-domain sensitive-read coverage after `WS09-02A` and `WS03-05D`, and both prerequisites are now accepted. Its semantic boundary remains:

> Can especially sensitive administrative data be disclosed without a safe, durable access record?

The parent remains incomplete until C is accepted. C also owns final WS09-02 parent accounting.

The corrected master requires sensitive-read auditing where private messages or detailed financial data are exposed outside ordinary user flows, while prohibiting a second audit store and a new audit investigation/search/export product.

`WS03-05D` already owns moderation-specific private-message, review-case, and audit-context disclosure. It consumes the existing fail-closed `record_sensitive_admin_read()` mechanism and explicitly leaves cross-domain sensitive-read coverage outside those moderation surfaces to later work. C must not duplicate D.

## 2. Production Outcome

When WS09-02C is complete:

- the remaining especially sensitive administrative financial reads identified in Section 3, including money collections, game-management views and previews, hidden community-game payment instructions, and staff-accessible booking, waitlist, publish-fee, checkout, payment, refund, and credit reads, are attributable through `AdminAction`;
- the read audit durably commits before protected financial detail is loaded for response disclosure;
- audit failure prevents the protected disclosure;
- the audit row contains actor, resource-specific action, typed target, time, outcome, and correlation through the accepted foundation;
- no raw financial detail, payment-provider identifier, card detail, failure message, refund reason, money-issue narrative, or other protected response content is copied into audit reason or metadata;
- existing active-admin authorization remains the access model;
- existing financial-consumer and active-admin audit API response shapes, pagination, and frontend workflows remain unchanged; the internal `AdminActionRead`/`AdminActionCreate` schemas gain the nullable `target_waitlist_entry_id`, while audit list/detail show it through the existing primary-target shape;
- existing WS03-05D sensitive-read behavior remains unchanged;
- WS09-02 can be marked complete after C merges.

The existing foundation already provides the correct separate-session recorder: it reloads the admin, requires a registered `sensitive_read` action, validates typed targets, persists and commits the `AdminAction`, and converts audit infrastructure failure into the established safe 503 before returning to the consumer.

## 3. Exact Sensitive-Read Consumer Inventory

The eleven `/admin/money` routes are not the entire disclosure boundary. Current game-management and generic booking, waitlist, publish-fee, checkout, payment, refund, and credit routes also expose detailed financial or payment-method data to administrators outside ordinary user flows. The following tables are the exact C consumer inventory. Keep existing response contracts; add audit at the owning service boundary before protected loading. A bounded page is still sensitive when its items contain financial detail.

Instrument the seven detail/history read surfaces with one action per successful request:

| Route | New action | Required target |
|---|---|---|
| `GET /admin/money/financial-outcomes/{financial_outcome_id}` | `read_admin_money_financial_outcome_detail` | `target_financial_outcome_id` |
| `GET /admin/money/users/{user_id}` | `read_admin_money_user_detail` | `target_user_id` |
| `GET /admin/money/issues/{money_issue_id}` | `read_admin_money_issue_detail` | `target_money_issue_id` |
| `GET /admin/money/credits/{game_credit_id}` | `read_admin_money_credit_detail` | `target_game_credit_id` |
| `GET /admin/money/payments/{payment_id}` | `read_admin_money_payment_detail` | `target_payment_id` |
| `GET /admin/money/refunds/{refund_id}` | `read_admin_money_refund_detail` | `target_refund_id` |
| `GET /admin/money/refunds/{refund_id}/events` | `read_admin_money_refund_events` | `target_refund_id` |

The refund-event history is audited once per successful request against the owning refund, not once per returned event.

### Other staff-only, resource-bound disclosure

Record one committed action per successful request, using the real enclosing game or selected participant as the typed target. A game-bound action is truthful for the whole game-scoped disclosure; it does not pretend that an unbounded response is a bounded item collection.

| Route | New action | Required target | Protected content |
|---|---|---|---|
| `GET /admin/official-games/{game_id}/money` | `read_admin_official_game_money` | `target_game_id` | Full payments, refunds, credits, and credit usages |
| `GET /admin/official-games/{game_id}/bookings` | `read_admin_official_game_bookings` | `target_game_id` | Per-booking buyer and monetary totals |
| `GET /admin/official-games/{game_id}/waitlist` | `read_admin_official_game_waitlist` | `target_game_id` | Each entry's payment-method brand/last four and authorized amount |
| `POST /admin/official-games/{game_id}/cancel-preview` | `read_admin_official_game_cancel_preview` | `target_game_id` | Per-booking refund/cash/credit impact |
| `POST /admin/official-games/{game_id}/participants/{participant_id}/remove-preview` | `read_admin_official_game_remove_preview` | `target_participant_id` | Booking, refund, cash, and credit impact for the selected participant |
| `GET /admin/community-games/{game_id}` | `read_admin_community_game_payment_detail` | `target_game_id` | Unmasked payment-method and payment-instruction snapshots, plus publish-fee detail |

These are six additional request-level actions. For official/community game reads, an ID/type/deleted-at-only `Game` projection must establish the correct game kind before audit; a generic existing Game ID of the wrong kind is not sufficient. For remove-preview, also project `GameParticipant.id` and `game_id` to reject a wrong-parent participant before audit. Missing, deleted, wrong-kind, or wrong-parent resources retain the route's safe 404 and create no action. Move protected game, participant, waitlist entry, booking, payment, refund, credit, snapshot, and preview-calculation loads after commit. The official-game waitlist receives one truthful game-bound action per successful request, including an empty page, as the official-game bookings view does. Validate offset/limit and other pure request inputs first. The current POST preview routes are reads, not the mutation executions excluded by Section 12. Audit only the standalone preview route-facing service boundary: `build_official_game_cancellation_preview()` is also called by cancellation execution, and `preview_official_game_player_removal()` is also called by removal execution with `for_update=True`. Neither internal mutation call may create a second read action or open a separate audit transaction. Leave both underlying calculations callable from their mutations unchanged.

### Generic routes with administrator financial access

These routes are not prefixed `/admin`, but current services let active administrators read another person's financial records or a hidden game's payment instructions. Ordinary public/own-user/host reads remain ordinary flows and are not C consumers. Preserve that distinction at the service boundary, including direct service callers.

| Route and staff branch | New action | Required target | Recording rule |
|---|---|---|---|
| `GET /payments/{payment_id}` when payer is another user | `read_staff_payment_detail` | `target_payment_id` | Once per successful cross-user detail |
| `GET /refunds/{refund_id}` when underlying payment's payer is another user | `read_staff_refund_detail` | `target_refund_id` | Once per successful cross-user detail |
| `GET /payments` when active-admin broad-list access is used | `read_staff_payment_list_item` | `target_payment_id` | Once per returned item, including an own item on a broad admin page |
| `GET /refunds` when active-admin broad-list access is used | `read_staff_refund_list_item` | `target_refund_id` | Once per returned item, including an own item on a broad admin page |
| `GET /game-credits?user_id=<other-user-id>` | `read_staff_game_credit_list_item` | `target_game_credit_id` | Once per returned credit; omitted/own `user_id` remains an ordinary own-user read |
| `GET /bookings/{booking_id}` when buyer is another user | `read_staff_booking_detail` | `target_booking_id` | Once per successful cross-user detail |
| `GET /bookings` when active-admin broad-list access is used | `read_staff_booking_list_item` | `target_booking_id` | Once per returned item, including an own item on a broad admin page |
| `GET /waitlist-entries/{waitlist_entry_id}` when the entry belongs to another user | `read_staff_waitlist_entry_detail` | `target_waitlist_entry_id` | Once per successful cross-user detail |
| `GET /waitlist-entries` (admin-only) | `read_staff_waitlist_entry_list_item` | `target_waitlist_entry_id` | Once per returned item, including an own item |
| `GET /host-publish-fees/{host_publish_fee_id}` (admin-only) | `read_staff_host_publish_fee_detail` | `target_host_publish_fee_id` | Once per successful detail |
| `GET /host-publish-fees` (admin-only) | `read_staff_host_publish_fee_list_item` | `target_host_publish_fee_id` | Once per returned fee |
| `GET /checkout/bookings/{booking_id}/status` when buyer is another user | `read_staff_checkout_status` | `target_booking_id` | Once per successful cross-user status disclosure |
| `GET /community-game-details/{community_game_detail_id}` when an active admin opens a hidden game | `read_staff_hidden_community_payment_detail` | `target_game_id` | Once per successful hidden-game payment-snapshot disclosure |
| `GET /community-game-details?game_id=<hidden-game-id>` when an active admin opens a hidden game | `read_staff_hidden_community_payment_list` | `target_game_id` | Once per successful filtered hidden-game payment-snapshot page |

These are eight request-level and six per-item actions. For payment/refund detail, determine ownership and target existence using only payment/refund ID and payer-ID projections (refund joins its payment); for booking, waitlist-entry, and checkout detail use only the resource ID and buyer/entry-user ID. Never hydrate protected ORM rows before an administrator cross-user audit. Non-admin cross-user requests retain denial and create no action. Revalidate the active administrator inside the private audit transaction, not only from a stale request-session object. On active-admin broad payment/refund/booking collections, use the per-item audit even if a filter happens to select only the administrator's own records; a non-admin's own-user collection remains unchanged. The admin-only waitlist-entry and host-publish-fee collections audit every returned item. On cross-user game-credit lists, validate the requested `user_id` format and cross-user authorization as today, select bounded credit IDs before audit, and hydrate only after commit; do not add a User-existence requirement because the current list can return an empty page for an unknown ID. Preserve all existing generic route schemas, filters, ordering, pagination, and ordinary own-user behavior.

The generic community-game detail reads are public for visible games; an unfiltered list also selects visible games only. They need no C action in those ordinary flows, and the `/games/{game_id}/host-edit` path remains host-only. For a hidden game, an active administrator can currently pass `user_can_view_hidden_game()` and receive the host's payment-method/instruction snapshot through the generic detail route or a list filtered by `game_id`; this is an alternate staff disclosure to the admin community-game view. On those hidden-game admin branches, audit once against the real community `Game` before loading `CommunityGameDetail`. For detail, project only `CommunityGameDetail.id` and `game_id` joined to Game ID/type/visibility/deleted-at; for the filtered list, project only Game ID/type/visibility/deleted-at. Reject missing, deleted, wrong-kind, or unauthorized targets under existing safe visibility behavior before audit. Validate offset/limit first. After a confirmed audit commit, run the existing visibility and response builder; do not expose a hidden snapshot on audit failure. Auditing every active-admin hidden-game request, even if that administrator is also a host or member, avoids a race in which a relationship disappears between the precheck and the accepted admin visibility fallback. Ordinary non-admin host/member access remains unchanged and unaudited.

The cross-user checkout-status route has an additional transaction edge: after access is established, the current service can expire stale pending checkouts and commit that state change before constructing the response. On the staff branch, perform only the ID/buyer projection before the separate read-audit commit; then run the existing checkout-status workflow, including its locking, expiration, and commit, unchanged. Do not record a second read action or include this query in the request's mutation transaction. If its later state transition or response construction fails, retain the already committed read action and return the existing safe failure without disclosing checkout detail. The own-buyer branch retains its current behavior without a C action.

The remaining inspected neighboring routes are not comparable staff financial-detail disclosures in this pass: official-game roster/participant and game-card responses include participant/public price but not authorization/card or booking/payment/refund ledger detail; `/game-credits/balance` exposes one aggregate available-balance number rather than grant detail; `/payment-events` and `/payment-events/{id}` expose event status/identifiers but not raw envelopes or detailed financial payloads; `/community-games/publish-attempts/{attempt_id}` can admit another host's active administrator, but its status response contains status, identifiers, and an error message, not the attempt's stored amount, payment method, or a client secret (`client_secret` is forced null); `/user-payment-methods` is own-user only; and `/bookings/me`, `/waitlist-entries/me`, and `/host-publish-fees/me` remain own-user/host paths. Actual mutation execution responses retain their existing mutation attribution. If Gate B source inspection reveals another staff-accessible route returning comparable protected detail, correct this Gate A inventory before implementing it, rather than leaving an unaudited sibling path.

### Collection-route boundary

Keep the current collection response schemas and admin UI. Because each returned item exposes sensitive financial detail, durably audit each item actually selected for the returned page, using its own real typed target. Use the following four additional actions:

| Route | Action per returned item | Required target |
|---|---|---|
| `GET /admin/money/issues` | `read_admin_money_issue_list_item` | `target_money_issue_id` |
| `GET /admin/money/credits` | `read_admin_money_credit_list_item` | `target_game_credit_id` |
| `GET /admin/money/payments` | `read_admin_money_payment_list_item` | `target_payment_id` |
| `GET /admin/money/refunds` | `read_admin_money_refund_list_item` | `target_refund_id` |

For a page with N returned items, record exactly N distinct actions in one private audit transaction and one commit before loading any protected item payload. A zero-item page creates no item action because it discloses no item detail. Do not audit the `limit + 1` lookahead item unless it is returned on a later page. Its existence is used only for existing `has_more`/cursor behavior; no detail from it is returned. A page request never uses a fabricated user or collection target, and the query text, filters, cursor, returned financial fields, and page membership are not stored in audit metadata.

First apply the existing validated filters, order, and cursor to an ID-and-sort-key-only projection, capped at the existing 100-item maximum plus one lookahead ID. This projection may use existing SQL predicates but must not materialize money ORM objects, related records, or protected response fields. Freeze the first N IDs and their order. The existing money-issue text search already selects matching `User.id` values; preserve that projection-only behavior. Reject duplicate selected IDs rather than writing duplicate audit rows.

Add a bounded `record_sensitive_admin_read_batch(authenticated_admin_id, action_type, target_ids)` operation beside the existing recorder. The caller supplies one of the ten registered list-item action types and distinct IDs of its exact required target type: 1–100 IDs for the four `/admin/money` and four other generic list actions, or 1–200 IDs for the admin-only waitlist-entry and host-publish-fee list actions, matching those routes' existing limits. An empty page skips the helper. In one private transaction, reload and reauthorize the actor once, validate the action policy, action-specific batch bound, and every target using only ID/deleted-at projections, create all N `AdminAction` rows with one request correlation identifier, flush, and commit once. Any missing/deleted target, policy mismatch, invalid server-owned batch bound, insert failure, or uncertain/failed commit aborts the whole batch and returns only the stable safe audit-unavailable 503; it must not fall back to unaudited list output. Do not call the single-row helper N times. Only after confirmed commit load and serialize the frozen IDs, in their selected order, using existing summary builders. Never rerun the collection query to add newly matching, unaudited rows. If a selected row disappears after commit, fail the response closed and retain the committed audit rows. Preserve existing filter, cursor-context, `has_more`, `next_cursor`, and response behavior for stable data. No frontend change or new audit store is required.

Apply the same bounded ID-only selection / one atomic batch / post-commit hydration rule to generic `/payments`, `/refunds`, `/bookings`, `/waitlist-entries`, `/host-publish-fees`, and cross-user `/game-credits` list branches. They have offset/limit pagination rather than `/admin/money` cursors: select at most the existing 100 returned IDs for payment, refund, booking, and cross-user game-credit pages, or the existing 200 returned IDs for admin-only waitlist-entry and host-publish-fee pages, in the existing filter/order/offset context; audit exactly those IDs and hydrate those same IDs in order. A zero-row page returns empty without a fabricated action. Validate booking/payment/waitlist/fee status filters and all other request-format errors before selection/audit. Keep `/bookings/me`, `/waitlist-entries/me`, and `/host-publish-fees/me` on their existing own-user/host paths; the generic detail service also preserves the own-resource branch. If an audited row vanishes before hydration, fail closed rather than filling the page with an unaudited replacement.

## 4. Sensitive-Read Action Contract

Register all 31 new actions in the existing central `AdminAction` policy: 21 request-level actions and ten per-item collection actions in Section 3.

Every action must use:

```text
category = "sensitive_read"
outcome = "succeeded" through the existing recorder or its bounded batch extension
requires_reason = False
metadata_builder_key = "none"
reason = None
metadata = None
allows_audit_note = False
idempotency_key = None
```

Each action allows exactly its required typed target from the tables above. `target_booking_id` and `target_host_publish_fee_id` already exist; the generic waitlist-entry actions require the new `target_waitlist_entry_id` described in Section 8. Do not attach optional user, game, participant, payment, refund, or related-resource targets merely because they are available during response construction. Every row in a collection batch has the same authenticated actor and request correlation identifier, but its own action type and resource target; reason and metadata remain null.

This matches the accepted WS03-05D sensitive-read contract, whose actions use resource-specific typed targets, no reason, no metadata, and no linked audit-note correction.

No new audit metadata profile is needed.

## 5. Disclosure Ordering

For each request-level sensitive-read consumer, including read-only POST previews and the admin cross-user branches of generic routes, the service boundary must enforce this order:

```text
AUTHENTICATED ADMIN + ROUTE TARGET ID
-> RECORD AND COMMIT SENSITIVE-READ AUDIT
-> LOAD PROTECTED FINANCIAL DETAIL
-> SERIALIZE RESPONSE
-> RETURN RESPONSE
```

The implementation must not:

- load the target's detailed ORM object before `record_sensitive_admin_read()`;
- construct response context before the audit commits;
- query related payments, refunds, cards, issues, events, booking/checkout totals, waitlist payment authorization, host fees, game payment snapshots, preview calculations, or other protected financial records for response construction before the audit commits; only the narrow ID/type/deleted-at/owner/parent and collection ID/sort-key projections specified in Section 3 may precede it;
- hold protected values in memory while attempting the audit transaction;
- call ordinary `record_admin_action()` for these reads.

The route's existing authentication dependency may load the authenticated administrator. Route parameters and target UUIDs are not protected payload and may be known before auditing. Pre-audit reference/ownership/game-type checks must select only the minimum columns named in Section 3 and never use full ORM `db.get()` or load protected relationships.

After the audit commits, the existing request-scoped session may perform the normal detail queries and serialization.

For all ten item-audited collections, use the same ordering with one bounded exception: an ID/sort-key-only page-selection query and pure request validation may run before audit. The batch audit for every returned item must commit before any selected item's protected ORM object, response summary, or related data is loaded. A collection page is never partially disclosed when the batch audit fails. Game-bound views/previews, including the official-game waitlist, instead use one action against the real game or participant target before their potentially unbounded protected loads.

If the later protected-data load or response serialization fails after the audit has committed, do not remove or rewrite the audit row. Preserve the accepted sensitive-read foundation semantics rather than attempting cross-session rollback of an already durable audit record.

## 6. Authorization And Failure Behavior

Preserve the current binary active-admin model. Do not introduce moderator roles, named permissions, new recent-authentication requirements, RBAC, ABAC, or a special money-reader role.

Required behavior:

- unauthenticated/non-admin access remains denied by the existing route dependency;
- suspended, deleted, or otherwise inactive administrators must fail the helper's active-admin revalidation;
- a missing request-level target, wrong game kind, wrong-parent participant, or non-admin cross-user attempt retains its safe 404/403 behavior after minimum-column validation and creates no sensitive-read action; booking, checkout, and waitlist detail paths decide own-versus-cross-user access from ID/owner projections; a target lost between pre-audit validation and the private audit commit fails closed with the stable safe 503;
- server-owned audit policy, action/target configuration, target-validation race, or persistence failure fails closed with the established `AUDIT_UNAVAILABLE_DETAIL` 503; this is distinct from a genuinely invalid client request rejected before audit;
- protected financial data must not be loaded or returned after that audit failure;
- no database/internal audit error detail may escape to the client;
- a successful request-level staff disclosure emits exactly one action; a successful item-audited collection emits one action for each returned item and none for an empty page; own-user generic reads emit no C action.

The accepted single-row `record_sensitive_admin_read()` currently rethrows its internal 400 policy/target-validation and 404 target-reference exceptions. For C consumers, add one narrow service-side recording adapter that calls that accepted helper after pre-audit request and reference validation, preserves its active-admin 403 and stable 503, and maps any helper-origin 400/404 (server-owned action/target mismatch or target disappearing after projection) to exactly `AUDIT_UNAVAILABLE_DETAIL` 503. Do not expose action names, target-field names, constraint names, SQL, or internal exception text. Keep genuine request-validation 400 and pre-audit not-found/wrong-parent 404 outside this adapter and unchanged. The batch helper must use the same safe mapping itself. Do not alter WS03-05D's existing helper call sites or accepted behavior.

## 7. Target Existence And Deleted-Resource Compatibility

The existing sensitive-read helper validates typed target references without hydrating protected payload columns. Preserve that minimal-reference behavior. Every request-level C service first performs an ID/deleted-at-only existence projection for its typed target (plus the minimum kind/parent/owner columns specified in Section 3), returning the existing safe 404/403 before the C recording adapter when the resource is already unavailable. The helper then independently revalidates the target in its private transaction; a race or internal policy mismatch after that precheck is the safe 503 described in Section 6. Do not use a full-row `db.get()` for the precheck.

Current `get_admin_money_user_detail()` accepts a retained User row found by primary key even when `deleted_at` is set; it uses that row for historical financial/account data. The sensitive-read helper currently rejects every soft-deleted target. Freeze the compatibility rule: `read_admin_money_user_detail` alone may validate an existing User ID without rejecting a non-null `deleted_at`. Add an explicit action-policy allowance for this one action and `target_user_id`, pass that policy into the ID/deleted-at projection validator, and leave the generic default rejection unchanged. Missing User IDs still produce the current safe 404 with no action; the actor must independently pass active-admin revalidation and must never use this target exception to authorize a deleted administrator. No other new or existing action gains deleted-target access.

For every other C action, use the current target-existence rule: the typed target must exist, and any target model with `deleted_at` set is unavailable. The new waitlist-entry target uses the same ID-only validator; its model has no `deleted_at` column, so a retained row is validated by ID as current waitlist detail reads are. For game-bound actions also enforce the correct game kind before audit, and for the selected participant enforce its requested game parent. The single-row adapter turns a target lost after those checks into the safe 503, not a false 404. Do not change retained-record visibility or broaden access to deleted resources elsewhere.

## 8. Schema, Model, Migration, And Display Contract

WS09-02C reuses the existing `AdminAction` table. The 31 actions use these existing target columns:

- `target_user_id`
- `target_money_issue_id`
- `target_game_credit_id`
- `target_payment_id`
- `target_refund_id`
- `target_financial_outcome_id`
- `target_game_id`
- `target_participant_id`
- `target_booking_id`
- `target_host_publish_fee_id`

The generic waitlist-entry detail/list actions cannot use an existing column truthfully: a game may have many entries, and historical entries can share a game and user. Add one nullable typed `target_waitlist_entry_id` column to `AdminAction` and its canonical migration, with the same UUID/index convention as other target pointers. Add it to the model/migration target-required expression, central target-field inventory, ID-only reference validator/model map, safe not-found detail map, and audit read/create schema. Do not add a database FK: the canonical `admin_actions` migration runs before the `waitlist_entries` table migration, and existing typed target pointers use service-level reference validation rather than per-target FKs. No second table or broad target abstraction is needed.

Required shared-contract work:

1. Add all 31 action types to `backend/services/admin_action_policy.py`, with the narrow deleted-User target allowance defined in Section 7 and the exact new waitlist-entry target policy.
2. Add all 31 action names to the `AdminAction` model action-type constraint/enumeration representation used by current code.
3. Update canonical `backend/alembic/versions/0004_create_admin_actions_table.py` so a fresh database accepts all 31 actions and has the new typed target column, index, and target-required constraint term. Keep model, schema, policy, and migration aligned.
4. Keep target-required behavior aligned with all typed-target fields, including `target_waitlist_entry_id`.
5. Do not add a new table, a second audit ledger, or unrelated generic target columns.
6. Do not add audit-note eligibility for these sensitive reads.
7. Register all 31 actions with an explicit `AdminActionDisplayRule` and their exact Section 3 `PrimaryTargetRule`; do not rely on the unknown-action fallback. Add neutral display labels and action-specific ID-only target summaries. Register `target_waitlist_entry_id` in the existing ID-only target-type map rather than the ORM-loading target-display map. Do not use the existing money/game/participant/booking/fee target-record loader for these actions: existing target-display builders can select full ORM records and money labels can include issue `latest_summary` or financial amounts. Before collecting IDs for `load_records_by_field()`, separate these 31 actions and render their primary target type, full internal target UUID, and an ID-based destination only where one already exists. The new action-specific branch must not fall through to `build_target_summary()`'s truncated deleted-User fallback or full-record display rules. Do not query target User, Game, GameParticipant, WaitlistEntry, Booking, HostPublishFee, MoneyIssue, GameCredit, Payment, Refund, or AdminFinancialOutcome records merely to display a new read action; existing authorized actor-label lookup remains allowed. Keep accepted mutation-action display unchanged.

Recommended labels:

- `Admin money financial outcome viewed`
- `Admin money user detail viewed`
- `Admin money issue detail viewed`
- `Admin money credit detail viewed`
- `Admin money payment detail viewed`
- `Admin money refund detail viewed`
- `Admin money refund events viewed`
- `Admin money issue list item viewed`
- `Admin money credit list item viewed`
- `Admin money payment list item viewed`
- `Admin money refund list item viewed`
- `Official game money viewed`
- `Official game bookings viewed`
- `Official game waitlist viewed`
- `Official game cancellation preview viewed`
- `Official game player removal preview viewed`
- `Community game payment detail viewed`
- `Staff payment detail viewed`
- `Staff refund detail viewed`
- `Staff payment list item viewed`
- `Staff refund list item viewed`
- `Staff game credit list item viewed`
- `Staff booking detail viewed`
- `Staff booking list item viewed`
- `Staff waitlist entry detail viewed`
- `Staff waitlist entry list item viewed`
- `Staff host publish fee detail viewed`
- `Staff host publish fee list item viewed`
- `Staff checkout status viewed`
- `Staff hidden community payment detail viewed`
- `Staff hidden community payment list viewed`

The label is the neutral action text above; the target summary is the type plus full internal UUID (for example, `Payment <uuid>` or `Game <uuid>`), with no amount, narrative, user identity, or payment-provider identifier. This action-specific branch applies to both audit list and explicit detail responses and never hydrates protected money detail merely to render a read-action label.

Build destinations from action type and persisted ID only: `/admin/money/financial-outcomes/{id}`, `/admin/money/users/{id}`, `/admin/money/issues/{id}`, `/admin/money/credits/{id}`, `/admin/money/payments/{id}`, and `/admin/money/refunds/{id}` for the corresponding `/admin/money` and generic payment/refund/credit staff target actions; `/admin/official-games/{id}` for official-game-targeted actions; `/admin/community-games/{id}` for community-game-targeted actions. Booking, waitlist-entry, host-publish-fee, and checkout-status actions have no existing ID-only administrator page destination, so use `None`; the participant-targeted removal-preview action likewise uses `None`. Do not resolve game kind or a participant's parent by hydrating either record during display.

Payment, refund, and credit detail pages currently embed the latest 100 related `AdminAction` rows as mutation/activity history. Filter **all** policy-category `sensitive_read` action types in SQL **before** ordering and `LIMIT 100` in `list_payment_audit_actions()`, `list_refund_admin_activity()`, and `list_credit_audit_actions()`; derive that action-type set from the central policy rather than copying a fragile C-only literal list. Keep existing visibility checks and response shape. This prevents repeated reads from displacing useful mutation/correction history, including where a refund history also matches a money-issue target. Do not filter sensitive reads out of the global admin audit list or explicit audit detail: those remain the authoritative complete ledger.

## 9. Route And Service Integration

Prefer placing audit ordering at the narrow service boundary that controls the protected disclosure rather than scattering ad hoc recorder calls after data has already been loaded.

For each request-level C route, including the game-management and cross-user generic branches:

1. retain each route's existing dependency: `require_active_admin` for staff-only routes and the existing active/app-user dependency for generic own-or-admin routes; do not turn an ordinary own-user route into an admin-only route;
2. pass the authenticated actor identity into the detail/history service where necessary and require active-admin status inside the separate recorder transaction on every staff branch;
3. validate path IDs and every non-sensitive request parameter that can produce a 400 before auditing, without querying protected records;
4. call the narrow C safe-error adapter around `record_sensitive_admin_read(...)` with the exact action and exact target;
5. only after it returns successfully, execute the existing protected query and serializer;
6. preserve current response schema.

Do not add audit logic to frontend code.

For `GET /admin/money/users/{user_id}`, parse `saved_cards_cursor` with the existing pure `parse_offset_cursor()` rule before the audit. For refund events, parse the existing encoded/context-bound cursor using the refund ID, event filters, and current cursor-context calculation before the audit, without loading Refund or RefundEvent. Preserve the existing 400 errors for malformed or mismatched cursors. FastAPI path/query validation and collection filter, unsupported-parameter, and cursor validation must likewise finish before any audit write. The service must not later discover a request-format error after committing a `succeeded` action. Test invalid values with no action and no protected load.

For each of the ten item-audited collection routes, the owning service performs the ID-only page selection and one atomic batch audit described in Section 3, then hydrates only the audited IDs. Keep the route dependency and financial-consumer response schema unchanged. The batch extension belongs beside `record_sensitive_admin_read()` in the accepted audit service, not in the route or a second audit subsystem. For generic payment/refund/booking/waitlist-entry/checkout detail, use a minimum ID/owner projection to distinguish own-user from cross-user before the existing full-row loader; only the cross-user branch calls the C adapter. Host-publish-fee detail is admin-only and uses an ID-only precheck. For generic community-game detail, use the narrow detail/Game or filtered Game projection in Section 3 to select the active-admin hidden-game branch; visible/public and non-admin host/member branches retain their existing responses without C audit. For game-bound reads and previews, move the existing protected loader/calculator behind the single committed action while retaining ID-only kind/parent checks first. Wrap the two standalone preview routes around their existing calculation services; do not insert a recorder into either shared preview calculation used by mutation execution. In the checkout-status staff branch, the committed read action precedes the existing expiry calculation and request-session commit, without changing that workflow's locking or side effects.

Do not create a generic decorator or universal sensitive-read framework. The accepted foundation owns the reusable recorder; C requires only the narrow safe-error adapter and bounded batch extension described above.

## 10. Financial Data Minimization

The audit row itself must not copy the protected financial data being viewed.

Forbidden audit reason/metadata content includes, at minimum:

- card brand, last four digits, expiry, status, or saved-card inventory;
- payment amount or refund amount;
- provider payment intent IDs;
- provider charge IDs;
- provider event IDs;
- payment failure code/message;
- payment/refund idempotency keys;
- refund reason;
- money-issue summary or narrative;
- recommended-action narrative;
- credit amount/balance;
- user email or display name;
- booking/game labels derived from protected context;
- community payment-method handles, instructions, or preview tokens;
- raw provider payload or reconciliation detail.

The typed internal target ID, authenticated actor, action name, database timestamp, outcome, and correlation identifier are sufficient for WS09-02C.

## 11. Cache And Response Behavior

Preserve the accepted private-admin cache behavior from WS03-05D. Do not add route-specific cache headers if centralized middleware already applies `Cache-Control: private, no-store` correctly to these authenticated admin responses.

Gate B validation must confirm representative `/admin/money`, game-bound, hidden community-game detail, booking, waitlist, host-publish-fee, checkout-status, and other generic cross-user responses retain the expected private/no-store behavior; add centralized coverage if a generic route lacks it.

No frontend response contract should gain the audit action ID.

## 12. Mutation Endpoints Are Not C Consumers

Do not broaden WS09-02C into mutation auditing.

Actual POST mutation executions may return money detail after a successful mutation, but their privileged mutation attribution belongs to existing mutation actions and WS09-02B/current domain contracts:

- financial-outcome creation;
- money-issue resolve;
- money-issue credit retry;
- refund retry;
- refund reconcile;
- other existing admin money mutations.

C must not emit a second `sensitive_read` row solely because a mutation response contains the resulting resource detail.

`POST .../cancel-preview` and `POST .../remove-preview` are explicitly **read-only financial previews** in Section 3; their HTTP method does not make them mutation executions, and they require C's commit-before-disclosure audit.

If a mutation currently returns more protected data than necessary, that is a response-minimization question outside this pass unless it directly prevents the C disclosure invariant from being implemented safely.

## 13. WS03-05D Compatibility

Do not change or duplicate these accepted WS03-05D sensitive-read actions:

- `read_game_chat_moderation`
- `reveal_game_chat_message_content`
- `read_need_sub_chat_moderation`
- `reveal_need_sub_chat_message_content`
- `read_review_case_sensitive_detail`

Their existing semantics remain authoritative:

- resource-specific targets;
- `metadata=None`;
- `reason=None`;
- fail-closed audit before protected disclosure;
- no audit notes;
- no alternate ordinary `record_admin_action()` path.

WS09-02C tests should include compatibility regression proving the shared policy and migration additions do not weaken those accepted actions.

## 14. Audit Access Compatibility

The new records remain visible only through the existing active-admin audit surfaces.

Do not:

- create a new audit search endpoint;
- add an export feature;
- add a specialized money-read audit UI;
- introduce named permissions;
- expose these records to ordinary users;
- expose raw protected money data through audit target display.

The existing audit list/detail behavior should recognize and safely display all 31 new action types and the new typed waitlist-entry target. The three embedded payment/refund/credit mutation histories remain task-specific displays and exclude sensitive-read rows before their 100-row cap; no audit row is deleted or hidden from the global ledger.

## 15. Concurrency And Transaction Semantics

Sensitive reads are not mutation transactions. Do not add row locks merely to make the read and audit appear atomic.

The required invariant is disclosure ordering, not a serializable snapshot coupling the audit row and read result.

Required semantics:

- audit session commits first;
- protected request-session reads occur afterward;
- no blind retry of audit commit after an uncertain commit outcome;
- if audit commit outcome is uncertain, fail closed and do not disclose;
- if protected data changes between audit commit and the subsequent read, normal current read semantics apply;
- one request-level staff disclosure creates one read-audit record, even if its service issues multiple SQL queries after the audit; one item-audited collection request creates one committed record per returned item, with no partial batch; ordinary own-user generic reads create none.

Do not lock financial rows just for auditability.

## 16. Expected Files

Gate B should expect a bounded backend change set centered on:

- `backend/services/admin_action_policy.py`
- `backend/services/admin_action_service.py` for the narrow deleted-User rule and atomic batch recorder
- the current `AdminAction` model and read/create schema for the new waitlist-entry target and action types
- `backend/alembic/versions/0004_create_admin_actions_table.py`
- `backend/routes/admin_money_routes.py`
- the relevant admin-money detail and collection query services, including ID-only page selection
- official/community game route and service boundaries for the game-bound financial reads, waitlist, and read-only previews
- generic booking, waitlist-entry, host-publish-fee, checkout, community-game-detail, payment, refund, and game-credit service boundaries for staff reads and item-audited lists
- audit display/summary service code
- the three embedded admin-money history queries and focused backend tests for all identified staff financial reads and admin audit behavior
- canonical migration tests
- `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` as merge-state accounting

Do not create a new database migration solely as a repair layer if the repository convention for the current production-readiness baseline is to update the canonical `admin_actions` migration before production baseline release.

No frontend source change is expected because financial-consumer response contracts remain unchanged. Gate B must verify the existing money, official-game money/booking/waitlist/preview, admin and generic community-game detail, and generic booking/waitlist/host-fee/checkout workflows continue to work with the audited responses.

## 17. Required Gate B Tests

### 17.1 Detail/history and collection read contracts

For each of the 21 request-level C actions, including seven `/admin/money` details, six game-bound reads/previews, and eight generic staff details/status reads, prove:

- active admin can successfully read;
- exactly one correct sensitive-read `AdminAction` is created;
- correct authenticated admin is the actor;
- exact action type is used;
- exact required target is persisted;
- outcome is `succeeded`;
- reason is null;
- metadata is null;
- correlation identifier is present;
- response shape remains compatible.

For each of the ten item-audited collection branches, prove a non-empty page writes exactly one action per returned target, all with the correct actor/action/typed target/correlation and null reason/metadata; a zero-item page writes none. Prove existing response fields, order, filter behavior, page-size cap, cursor or offset behavior remain compatible. For `/admin/money`, prove `has_more`, `next_cursor`, and that `limit + 1` lookahead is not audited until actually returned. Include duplicate-ID prevention and changed/deleted-row race behavior. Prove a normal user's own payment/refund/credit/booking/waitlist lists, applicable own-resource details, checkout status, and own-host publish-fee list still work without a C action, while an active administrator's broad payment/refund/booking list is audited even when filtered to own rows. For each admin-only waitlist-entry and host-publish-fee collection, prove requests returning 101 and 200 items preserve the requested page and order, commit exactly 101 or 200 actions in one batch before protected hydration, and never truncate or reject a valid page because of the audit bound. The official-game waitlist uses exactly one game-bound action per successful request, including empty pages.

### 17.2 Fail-closed ordering

For each distinct `/admin/money`, game-bound, generic cross-user, and item-audited collection integration pattern, force the audit recorder or collection batch commit to fail and prove:

- route returns the stable safe audit-unavailable response;
- protected detail query/loader is not called after the audit failure;
- protected financial response is not returned.

At least one test should demonstrate ordering through a real service/query boundary rather than only asserting mocked call sequence.

For each of the ten collection families, prove the pre-audit query returns only IDs/sort keys (and a payer/user ID where needed for ownership), no protected ORM item or related row is materialized before the batch commit, all N audit rows commit together, and a failed row or commit creates no partial batch or returned page. Exercise batch failure on a 200-item admin-only waitlist-entry or host-publish-fee page as well as the ordinary smaller pages. After commit, response hydration must be limited to the audited IDs. Use real PostgreSQL transaction evidence for atomicity and an uncertain-commit failure; do not rely only on mocked order. Prove the game-bound paths commit before loading payment snapshots, waitlist payment authorization, booking amounts, or preview calculations, and their game-money and official-waitlist responses each receive one truthful game-bound action.

For cross-user checkout status, prove the ID/buyer projection and private audit commit precede any booking/payment/credit/compensation hydration and the existing stale-checkout expiration commit. Exercise an expired pending checkout with real PostgreSQL state: its normal expiration behavior remains intact, audit failure causes neither expiration nor disclosure, and a later expiration or response failure retains the already committed read action without disclosing protected detail. Own-buyer checkout status must retain its prior transaction behavior without a C read action.

For generic community-game detail and filtered list, prove visible/public reads and non-admin hidden-game host/member reads remain unchanged and unaudited; an active administrator's hidden-game read records one `target_game_id` action before payment snapshots load, even when that administrator also has a host/member relationship. Prove a missing detail or wrong-kind/deleted/missing parent game cannot create an action or disclose content, a hidden filtered empty page follows the one-game-action rule, and an unfiltered list stays visible-only. Force audit failure on both hidden staff paths and prove no snapshot load or response.

### 17.3 Target/reference behavior

Test:

- missing resource;
- invalid or mismatched target;
- deleted/retained target behavior where applicable;
- no audit row for an unavailable target when current semantics require not-found;
- retained financial access behavior does not regress because of generic deleted-target validation.

Specifically prove a retained soft-deleted User succeeds for `read_admin_money_user_detail`, while a missing User fails without an action, a deleted actor still fails authorization, and every other action keeps the original deleted-target rejection.

For the new game-bound paths, prove wrong-kind/deleted games and remove-preview participants from another game return safe 404 with no action or protected load. For generic payment/refund/booking/waitlist-entry/checkout detail, prove the ID/owner-only projection rejects non-admin cross-user access before hydration, allows ordinary own-user access unchanged, and audits only the active-admin cross-user branch. For admin-only host-publish-fee detail, prove the ID-only precheck precedes audit and that no amount or waiver reason loads before commit. Include stale/suspended/deleted/non-admin actor revalidation inside the audit transaction, not only route-dependency denial. Prove retained/historical waitlist entries can be audited by their own typed ID even when the same game and user have another entry; no fabricated game/user target substitutes for the entry.

### 17.4 Invalid request validation

Prove malformed or context-mismatched `saved_cards_cursor` and refund-event cursor inputs, plus representative invalid collection filters/cursors and unsupported parameters, retain their existing 400 behavior without committing a `succeeded` read action or loading protected response data.

Prove invalid game-bound pagination and generic payment/refund/booking/waitlist/host-fee status filters are rejected before auditing. Inject a missing/wrong server-owned action policy, wrong typed target, and a target disappearing between ID-only precheck and helper validation: C's single-row adapter and batch helper must return exactly the stable `AUDIT_UNAVAILABLE_DETAIL` 503 with no database/schema/action/target detail and no protected load. Contrast with a genuinely invalid client request (existing 400), pre-audit missing/wrong-parent resource (existing safe 404), and inactive actor (403). Re-run representative accepted WS03-05D reads to confirm its helper call sites and response behavior did not change.

### 17.5 No metadata leakage

Assert the new actions persist no reason and no metadata even when the protected response contains:

- card metadata;
- payment/provider identifiers;
- amounts;
- failure messages;
- refund reasons;
- money-issue summaries;
- community-game payment instructions or handles;
- official-game preview amounts and tokens;
- user identity fields;
- waitlist payment-method brand/last four and authorized amount;
- host-publish-fee amount, payment reference, and waiver reason;
- checkout credit balance, applied credit, fee, and amount due.

### 17.6 Policy constraints

Prove each new action:

- is category `sensitive_read`;
- cannot be recorded with ordinary `record_admin_action()`;
- accepts only its exact target fields;
- rejects extra targets;
- rejects metadata including `{}`;
- does not allow an audit note.

Prove no C action is emitted for actual mutation execution responses solely because they include result detail, and no staff cross-user financial read in the Section 3 inventory can disclose through an alternate generic route without its C action.

Specifically prove both standalone preview POSTs commit their read actions before calculation, while cancellation execution's internal `build_official_game_cancellation_preview()` and removal execution's internal `preview_official_game_player_removal(..., for_update=True)` create no read action and retain existing transaction/locking behavior.

### 17.7 Existing D regression

Re-run focused sensitive-read tests covering the five accepted WS03-05D actions to prove the shared policy/migration change did not alter their behavior.

### 17.8 Audit display

Prove list/detail serialization of each new read action:

- uses its neutral label;
- resolves the correct target type;
- does not query or expose protected money payload solely for target display;
- remains readable only to an active admin.

Use isolated new read actions to prove both audit list and detail display select no protected money/User ORM rows and never render issue summaries, amounts, names, or provider identifiers. Also prove existing mutation-action labels and destinations are unchanged.

Create more than 100 sensitive reads against the same payment, refund, and credit, with older mutation/correction rows. Prove each embedded detail history still returns the latest eligible mutation/correction rows because `sensitive_read` is excluded in SQL before `LIMIT 100`, while the global admin audit list/detail still contains the read rows. Cover refund history linked through a money-issue target and use the central policy category set rather than a copied C action-name filter.

### 17.9 Canonical migration

Run real PostgreSQL migration coverage proving:

- fresh upgrade accepts all 31 new action types;
- existing action types remain valid;
- `target_waitlist_entry_id` exists with its index, appears in the target-required constraint, validates a real waitlist-entry ID, and is rejected for actions that do not allow it;
- no unintended target column or FK is introduced; the accepted typed-pointer convention remains intact;
- downgrade/re-upgrade remains valid according to current migration-test convention;
- model/policy/canonical migration action and target-field sets stay aligned, including the audit response schema.

### 17.10 Cache behavior

Verify representative admin-money, game-management, and generic cross-user responses retain centralized `private, no-store` behavior.

### 17.11 Broader regression

Run the focused high-risk suites covering:

- admin authorization;
- admin actions;
- WS03-05D sensitive reads;
- admin money user/payment/refund/credit/issue/financial-outcome detail;
- all four admin-money collection families, including their frontend-facing response contracts;
- official-game money, bookings, waitlist, cancellation/removal previews, and community-game payment-detail response compatibility;
- generic payment/refund/booking/waitlist/checkout cross-user details, host-fee detail, hidden community-game payment reads, all admin-broad/only lists, cross-user game-credit lists, and ordinary public/own-user/host finance regressions;
- embedded payment/refund/credit mutation-history behavior under repeated sensitive reads;
- migration/model parity;
- public safe error behavior.

Because this changes the shared central audit action policy and canonical `admin_actions` constraint, run one complete backend suite after focused corrections are green.

If that complete suite exposes unrelated or localized failures, investigate them accurately. Do not claim a fully green suite unless it actually completes green. After localized corrections, use focused reproductions rather than repeatedly rerunning the complete suite unless the correction changes shared behavior broadly enough to invalidate the prior full run.

## 18. Security And Privacy Review Checklist For Gate B

Before Gate B is considered complete, inspect the final diff for:

- no secret/provider credential;
- no raw card or provider payment data copied to audit;
- no PII copied into reason/metadata;
- no detailed financial values in audit display labels;
- no protected response-data query or ORM hydration before audit commit; collection ID/sort-key projection is the explicit narrow exception;
- no game/participant/ownership projection loads protected rows, and no wrong-kind/wrong-parent preview is audited;
- no fallback path that returns protected content when audit recording fails;
- no second audit store;
- no duplicate read audit from both route and service;
- no ordinary `record_admin_action()` use for the new reads;
- no new moderator/permission hierarchy;
- no generic audit investigation/search/export feature;
- no unnecessary lock or retry behavior;
- no changed mutation semantics;
- no collection item returned without a committed resource-specific read action;
- no booking, waitlist authorization, host-fee, or checkout detail returned through a staff branch without its committed action;
- no waitlist-entry action recorded against an ambiguous game/user surrogate instead of its typed entry ID;
- no read-only POST financial preview mistaken for a mutation exclusion;
- no repeated sensitive reads displace capped payment/refund/credit mutation history, while the global ledger remains complete;
- no helper-origin 400/404 or PostgreSQL/schema detail escaping C's safe 503 boundary;
- no pre-audit protected ORM hydration, false successful action for malformed input, or partial collection-audit batch.

## 19. Execution-Register Closeout

Current accepted `develop` contains 44 accepted executable passes and 25 remaining units. `WS09-02A` and `WS09-02B` are accepted children; `WS09-02C` is not accepted, and parent `WS09-02` is incomplete. The WS09-02C implementation branch and PR must carry the register diff describing the factual state that will become true atomically when that PR merges; carrying the diff does not claim that C is accepted before merge.

The proposed post-merge register state is **45 accepted / 0 implemented-but-unmerged / 24 remaining**: add exactly one accepted executable child (`WS09-02C`) to 44 and remove exactly that child from the 25 remaining units. Keep `WS09-02A` and `WS09-02B` accepted, mark the WS09-02 parent complete without counting it as an additional executable pass, remove C from the remaining-work composition, and update the summary, accepted-pass list, parent/decomposition rows, and WS09-02 narrative consistently. Do not mark WS09-03 or later observability/privacy units complete. Verify the register's counts against the actual accepted state before writing the PR diff; if accepted `develop` changes materially first, return to Gate A rather than silently changing the designed transition.

## 20. Non-Goals

WS09-02C does not implement:

- moderation/private-message sensitive reads already accepted under WS03-05D;
- privileged mutation coverage already accepted under WS09-02B;
- a second audit table;
- audit search/export/investigation product;
- general access analytics;
- user-facing access history;
- provider event auditing;
- generic data-loss-prevention infrastructure;
- moderator or named permissions;
- new recent-auth requirements;
- production IAM/database grants;
- retention, archival, legal-hold, or audit-deletion policy;
- alerting or dashboards;
- broad response redesign of the money workspace;
- frontend audit instrumentation.

## 21. Gate C Review Focus

The later independent Gate C review must be especially aggressive on:

1. whether every actual sensitive financial-detail disclosure identified in Section 3 is covered, including generic hidden community-game, booking, waitlist-entry, host-publish-fee, checkout-status, payment, refund, credit, and read-only POST preview paths;
2. whether any protected data is loaded before durable audit commit;
3. whether audit failure truly prevents disclosure;
4. whether all ten item-audited collection branches emit complete committed per-item batches before loading financial details, with no unaudited extra row, and whether actual mutation responses were kept out of C;
5. whether target validation breaks retained/deleted-resource semantics;
6. whether reason/metadata/display introduces protected financial data;
7. whether the new waitlist-entry target and shared policy/migration changes preserve WS03-05D and existing target validation;
8. whether the same request can accidentally emit zero or duplicate read records;
9. whether audit list/detail access remains restricted;
10. whether embedded mutation histories remain useful after heavy read-audit traffic and global audit remains complete;
11. whether server-owned audit validation failures expose only the stable safe 503 without changing client 400, pre-audit 404, actor 403, or accepted D behavior;
12. whether checkout-status expiration retains its existing state-change semantics after the read-audit commit, with no pre-audit protected load or side effect;
13. whether implementation expanded into a new audit product or permission system.

Passing tests do not replace this semantic review.

## 22. Gate A Acceptance Criteria

Gate A is satisfied when the implementation plan establishes all of the following:

- C remains one coherent executable pass;
- A and D prerequisites are accepted;
- the remaining sensitive-read population is explicitly bounded;
- 21 request-level C actions and ten item-audited collection actions cover the exact `/admin/money`, game-bound, hidden community-game, booking, waitlist, publish-fee, checkout, and other generic cross-user staff disclosure inventory;
- collection pages retain existing response/pagination contracts while auditing each returned item before protected hydration;
- resource-specific action and target contracts are defined;
- read audit must commit before protected load/disclosure;
- audit failure is fail-closed;
- no protected financial data enters audit reason/metadata;
- current active-admin authorization is preserved;
- the narrow retained/deleted-User compatibility rule is fixed;
- invalid request inputs are rejected before a successful-read audit is committed;
- existing D sensitive-read consumers remain unchanged;
- shared schema/policy/display/migration effects, including the one new waitlist-entry target and ID-only audit display, are accounted for;
- capped embedded mutation histories exclude sensitive reads before their limit without removing read rows from the global audit ledger;
- C-owned policy/target validation errors are safely translated to the stable 503 while preserving client 400, pre-audit 404, actor 403, and accepted D behavior;
- focused and complete backend validation expectations are specified;
- exact current and proposed post-merge parent/register states are explicit;
- no new audit product or second store is introduced.

## 23. Material Blockers

**No remaining design blocker identified in the correction self-review; independent Gate A re-review is still required.**

The required reusable sensitive-read recorder exists, the moderation prerequisite exists, the relevant typed financial target fields already exist in `AdminAction`, and the remaining consumer boundary can be planned from current repository truth.

If accepted repository truth changes the Section 3 sensitive-read population or makes this implementation contract invalid before Gate B, return to Gate A rather than silently expanding or narrowing coverage.

## 24. Stop Boundary

Stop after Gate A.

This Gate A plan does not authorize Gate B implementation, staging, a commit, a push, or a PR. Those actions require their own instruction under the current workflow.
