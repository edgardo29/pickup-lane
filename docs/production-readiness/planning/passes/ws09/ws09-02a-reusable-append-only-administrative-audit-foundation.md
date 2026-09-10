# WS09-02A — Reusable Append-Only Administrative Audit Foundation

Status: **Gate A approved; required review corrections incorporated**

Workstream: `WS09-02A`

Parent: `WS09-02`

Planned implementation branch: `pr/WS09-02`

Planning baseline and Gate A HEAD:
`31d3db4b2320a5656a081ac8f7bdc206c0b3cf7e`

Plan owner boundary: foundation only; `WS09-02B`, `WS03-05D`, and
`WS09-02C` remain separate consumers.

## 1. Gate A verdict

`WS09-02A` is **ready for implementation** with the design and safeguards in
this plan. No implementation blocker remains.

The independent Gate A review's required corrections to commit-owning audit
transaction isolation and its validation proof are incorporated into this final
plan. Commit-owning audit helpers no longer use the request-scoped database
session as their transaction owner.

This verdict is based on the following authority and repository evidence:

- `docs/production-readiness/00-READ-ME-FIRST.md`
- `docs/production-readiness/01-PROGRAM-CONTEXT.md`
- `docs/production-readiness/planning/program/pickup-lane-master-production-readiness-blueprint.md`,
  especially the administrative audit requirements in sections 5.11 and 8.7
- `docs/production-readiness/planning/workflows/PASS-IMPLEMENTATION-WORKFLOW.md`
- `docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md`
- the accepted split and boundary decisions in
  `docs/production-readiness/planning/passes/ws09/ws09-02-intake.md`
- the corrected OPP-11 access decision and the accepted prerequisite
  implementations named by the intake
- the relevant backend, database, testing, admin access, and audit agent notes
- direct inspection of the current models, canonical migrations, services,
  routes, schemas, middleware, and tests at the baseline

The Gate A review found several material issues that a simple database trigger
change would break. Their corrections are incorporated into the persistence,
writer-compatibility, failure, and testing design below.

## 2. Planned outcome

Gate B will leave Pickup Lane with one canonical administrative audit store,
`admin_actions`, whose records are attributable, correlation-ready, immutable
after insertion, and safe for both existing privileged mutations and future
sensitive-read consumers.

The implementation will also make retained `admin_rejected_attempts` records
immutable after insertion. It will not turn rejected attempts into a second
general-purpose audit system.

The completed foundation will provide:

1. a database-enforced immutable `AdminAction` record carrying actor, typed
   action, typed target/reference, database time, explicit outcome, bounded
   reason/context, correlation identifier, and existing idempotency identity;
2. database-enforced immutability for retained `AdminRejectedAttempt` rows;
3. a service-only append-a-correction primitive that creates a linked
   `append_audit_note` row and never changes the original row;
4. active-admin-only audit reads, enforced in the service layer as well as at
   the current route dependencies;
5. a reusable fail-closed service contract for recording future sensitive
   staff reads before protected content can be disclosed;
6. compatibility refactors for every current `record_admin_action` writer,
   including removal of all known post-insert `AdminAction` mutations; and
7. the factual execution-register reconciliation for the already accepted
   `WS03-05B` and `WS03-05C` merges.

`WS09-02A` does not claim complete privileged-mutation coverage or introduce a
concrete sensitive-read consumer. Those remain the explicit responsibilities
of B, D, and C.

## 3. Non-negotiable invariants

### 3.1 One audit store

- `AdminAction` remains the canonical store for successful, failed, pending,
  or uncertain privileged operations and, when later consumers are added,
  sensitive administrative reads.
- No parallel audit table, generic event store, provider log, or observability
  stream will be introduced by A.
- Existing domain histories such as `RefundEvent`, review-case events,
  financial outcomes, target notices, and moderation state histories retain
  their domain-specific responsibilities. They may be linked to an
  `AdminAction`; they do not replace it.
- `AdminRejectedAttempt` remains the bounded, operational record for the
  rejected-attempt scenarios already selected by earlier accepted work. A
  hardens it but does not expand it into duplicate denial coverage.

### 3.2 Immutable once inserted

- An `admin_actions` or `admin_rejected_attempts` row may be assembled while it
  is new in the SQLAlchemy unit of work.
- Once inserted, no application or ordinary runtime SQL path may `UPDATE` or
  `DELETE` that row.
- Corrections and clarifications are new linked audit rows. They never rewrite
  the original reason, metadata, outcome, target, actor, correlation, or time.
- Immutability applies to current writers as well as future writers; it is not
  merely a service convention.
- Schema-owner maintenance, migration, retention, legal-hold, archival, and
  extraordinary deletion processes are outside A. Final production runtime
  grants and separation from the schema owner remain owned by `WS04-01D`;
  retention/archive/legal-hold/export controls remain owned by `WS10-01` or
  later approved work.

### 3.3 Attribution and bounded context

Every newly created `AdminAction` will have all of the following at insert
time:

| Field | Gate B contract |
|---|---|
| `id` | Application-generated UUID, available before flush for same-transaction domain links. |
| `admin_user_id` | Authenticated admin actor UUID; existing restrictive actor FK behavior remains. |
| `action_type` | A policy-registered action type allowed by the database check constraint. |
| typed target columns | The exact applicable entity/reference IDs; policy cardinality and target validation remain authoritative. |
| `created_at` | Non-null PostgreSQL `now()` server default; normal writer APIs cannot override it. |
| `outcome` | Non-null finite disposition: `succeeded`, `failed`, or `pending`. |
| `correlation_id` | Non-null canonical UUID identifying the current request/operation correlation. |
| `reason` | Optional policy-controlled text, normalized and capped at the existing 1,000-character limit. |
| `metadata` | Optional policy-controlled, recursively bounded, redacted structured context; never raw request/provider payloads or protected content. |
| `idempotency_key` | Existing bounded optional operation identity, with existing action-specific uniqueness behavior preserved. |

`outcome` describes the disposition known for that immutable audit event; it
is not a mutable lifecycle field:

- `succeeded`: the audited operation represented by the row completed as
  intended in the owning transaction;
- `failed`: the row intentionally records a completed application-level
  failure outcome;
- `pending`: an external or multi-transaction operation was durably initiated
  but its domain/provider outcome was not yet known at that point.

A later domain result is expressed in the applicable linked domain history or
as a new audit event, never by changing `outcome`. Ordinary mutation writers
must pass an outcome explicitly; there will be no service default that can
silently classify a failure as success.

The correlation resolver will use the current correlation context established
by the existing correlation middleware. For a legitimate non-request execution
with no context, it will generate and set one canonical UUID rather than write
`NULL`. Callers may not put an arbitrary string or a second request identifier
into the record. `correlation_id` will have a B-tree index for incident
investigation; A does not add a search/export UI or public query filter.

### 3.4 Atomicity and durability

- The ordinary `record_admin_action` primitive continues to add/flush only; it
  does not commit. The service that owns the privileged domain mutation owns
  the transaction, so the domain state and audit row commit or roll back
  together.
- A database constraint, audit validation, or audit insert failure must roll
  back the related privileged mutation and return an existing safe application
  error. No writer may catch an audit failure and commit the business change
  without its audit row.
- The sensitive-read helper is intentionally different: it owns a small audit
  transaction in a dedicated short-lived `SessionLocal` session created by the
  helper. It must never call `commit()` or `rollback()` on the caller's
  request-scoped `db` session. The helper receives stable authenticated actor
  identity and target/reference values, reloads the admin in its own session,
  and revalidates active-admin status immediately before recording the audit
  row. It commits successfully before its caller obtains or serializes the full
  protected content. Any insert, flush, commit, or commit-outcome ambiguity
  rolls back/closes only the helper-owned session where possible and fails
  closed with a stable safe service error.
- The commit-owning append-only correction primitive follows the same session
  isolation rule. Its commit or rollback may affect only its helper-owned audit
  transaction, never unrelated pending work in the request-scoped session.
- The existing refund retry is also intentionally multi-transaction because it
  must establish a durable local idempotency identity before contacting
  Stripe. Section 8.1 preserves that accepted boundary without mutating its
  initial `AdminAction` later.

## 4. Scope boundaries

### 4.1 In A

- Extend and harden the existing `AdminAction` model, canonical migration,
  policy, schemas, services, and internal presentation.
- Add database update/delete guards for `AdminAction` and retained
  `AdminRejectedAttempt` records.
- Add the linked, service-only correction-row primitive.
- Refactor existing writers so the database guard can be enabled safely.
- Add the reusable sensitive-read audit category and recording service
  contract, including fail-closed behavior.
- Enforce active-admin audit-read authorization inside services and retain the
  existing route-level defense.
- Update focused and affected regression tests.
- Reconcile only the stale `WS03-05B`/`WS03-05C` execution-register facts
  specified in section 12.

### 4.2 Explicitly not in A

- `WS09-02B`: finding every privileged mutation that does not yet emit an
  audit row and adding that missing coverage.
- `WS03-05D`: private-message evidence access/retrieval and its concrete audit
  action/policy.
- `WS09-02C`: concrete sensitive-read instrumentation across private messages,
  financial/payment/refund/fee detail, identity/contact, or other protected
  surfaces.
- A generic “read sensitive data” action that loses the resource/target
  meaning. Each future consumer must register a specific action and target
  policy.
- Reopening the retired HTTP create or append-note endpoints.
- A new audit search, filtering, export, retention, archive, legal-hold, or
  deletion product.
- Moderator access, named permissions, data scopes, or a new authorization
  lattice. Corrected OPP-11 is binary: only an active admin may use admin
  surfaces.
- Final runtime/database roles and DDL/TRUNCATE privilege hardening
  (`WS04-01D`), provider control-plane hardening (`WS10-02`), or audit metrics
  and alerting (`WS09-03`).

## 5. Persistence and canonical migration design

Pickup Lane is pre-production and uses clean canonical schema history. Gate B
will modify the owning canonical migrations rather than append a repair
migration.

### 5.1 `admin_actions`

Update `backend/models/admin_action_model.py` and
`backend/alembic/versions/0004_create_admin_actions_table.py` together:

1. add non-null `outcome` using the existing bounded string/check-constraint
   style and allow exactly `succeeded`, `failed`, and `pending`;
2. add non-null PostgreSQL UUID `correlation_id`;
3. add `ix_admin_actions_correlation_id`;
4. turn `target_admin_action_id` into a self-referential FK to
   `admin_actions.id` with restrictive delete behavior;
5. retain the existing action-type check, typed target columns, actor FK,
   target indexes, idempotency indexes, and database `created_at` default;
6. create one table-owned trigger function that raises a stable database error
   (planned SQLSTATE `55000`, message `admin audit rows are immutable`) for row
   `UPDATE` or `DELETE`; and
7. attach a `BEFORE UPDATE OR DELETE FOR EACH ROW` trigger to
   `admin_actions`.

The ORM definition and canonical migration must have exact type, nullability,
check, FK, and index parity. The model will not supply an outcome default;
production writers and direct test fixtures must make the disposition
deliberate. The correlation value is supplied by the centralized builder,
never by scattered callers.

### 5.2 `admin_rejected_attempts`

Update `backend/models/admin_rejected_attempt_model.py` only if needed for
model/migration metadata parity, and update its owning canonical migration
`backend/alembic/versions/0045_create_admin_rejected_attempts_table.py` to
attach the same immutable-row behavior using its own table-named trigger and
function. The two canonical migrations must not share a function whose
lifecycle makes one table's downgrade depend on the other.

No new rejected-attempt fields or rejection scenarios are required by A. Its
existing bounded method/path/status/rejection/context contract remains intact.
The existing independently committed rejected-attempt service remains necessary
because it records selected failures after the rejected operation transaction
has rolled back.

The current account-deletion implementation anonymizes/soft-deletes the user;
it does not require physical deletion of audit actors. A future controlled hard
deletion that encounters restrictive or set-null audit relationships must be
designed with the later retention/identity policy rather than bypassing these
guards in application code.

### 5.3 Trigger and teardown rules

- The guard intentionally covers row `UPDATE` and `DELETE`, not `TRUNCATE`.
  The current PostgreSQL test cleanup truncates the entire schema between tests;
  blocking `TRUNCATE` would break isolation without adding runtime protection.
- Ordinary runtime inability to truncate or alter the table is a role/grant
  property to be proved by `WS04-01D`, not simulated by a row trigger.
- Canonical downgrade operations drop the rejected-attempt trigger first,
  then its table; the `admin_actions` downgrade drops its trigger/function and
  indexes/FKs in dependency-safe order.
- Gate B must rebuild disposable dev/test databases as the workflow requires;
  there is no production data backfill or dual-schema compatibility path.

## 6. Central service and policy changes

### 6.1 Policy classification

Extend the immutable `AdminActionPolicy` with an explicit category whose finite
values are:

- `mutation`
- `correction`
- `sensitive_read`

Classify every current action. Existing business actions are `mutation`;
`append_audit_note` is `correction`. A adds no concrete `sensitive_read` action.
That omission is deliberate: `WS03-05D` and `WS09-02C` own the exact
resource-specific actions and metadata/target policies.

Policy registration remains the single place to define:

- allowed and required typed targets;
- target cardinality;
- reason requirement;
- idempotency behavior;
- metadata profile and allowable context; and
- audit category.

The database action-type check and the policy registry must remain in parity.
Future consumers must update both through their canonical schema change.

### 6.2 `record_admin_action`

Refactor `record_admin_action` and its centralized builder so that:

- `outcome` is a required keyword;
- actor, action policy, targets, reason, metadata, and idempotency are validated
  exactly once;
- current canonical correlation is resolved centrally and placed on the row;
- the normal public service signature no longer accepts `created_at`;
- database time remains authoritative for `created_at`;
- it continues to add the row without committing; and
- it refuses a `sensitive_read` policy so ordinary mutation code cannot bypass
  the read helper’s commit-before-disclosure behavior.

All current production callers will be migrated in the same Gate B change.
Most pass `succeeded`; the finite exceptions discovered at Gate A are listed in
section 8.

The unused commit-owning `create_admin_action` service will be removed. It has
no production caller, the direct-create HTTP route is retired, and retaining a
second generic commit path would undermine the owning-transaction rule. Tests
that use it only to seed audit rows will use the canonical record primitive and
an explicit test transaction instead. The retired route and its compatibility
schema remain in place.

### 6.3 Append-only correction primitive

Keep and harden the existing service-level `append_admin_action_note` behavior,
but make its commit ownership explicit and isolated:

- the caller derives the actor ID from the authenticated admin principal; the
  service never accepts an actor ID from request payload data;
- the primitive does not use the caller's request-scoped `db` session as its
  transaction owner; it opens a dedicated short-lived `SessionLocal` session;
- inside that session, reload the actor and revalidate the binary active-admin
  rule immediately before recording;
- load and authorize access to the original action in that same helper-owned
  session;
- reject a missing original and reject a note whose target is itself an
  `append_audit_note` (no correction chains);
- create a new `append_audit_note` row with
  `target_admin_action_id=<original.id>`, the original typed targets copied for
  investigation, `outcome=succeeded`, current correlation, database time, and
  bounded/redacted reason/context;
- preserve the current idempotency behavior so a safe replay returns the same
  correction rather than appending duplicates;
- commit only the helper-owned correction transaction and return the committed
  correction identity; and
- on any failure, roll back/close only the helper-owned session. The original
  action remains byte-for-byte unchanged, and unrelated pending work in the
  caller's request-scoped session is neither committed nor rolled back.

The currently retired create and append-note HTTP routes continue returning
`410` after active-admin authentication. A does not create a public mutation
surface for audit records. The primitive is available to controlled future
internal workflows.

### 6.4 Sensitive-read recording primitive

Add one service entry point with the conceptual contract:

```text
record_sensitive_admin_read(
    *,
    authenticated_admin_id: UUID,
    action_type: policy-registered sensitive-read action,
    typed targets,
    optional bounded reason,
    optional policy-allowed context,
) -> committed admin_action_id: UUID
```

`authenticated_admin_id` is derived by the caller from the already-authenticated
admin principal. It is never accepted from request payload data. The helper does
not accept the request-scoped `db` session and does not return a live ORM object
attached to its private session.

Its required behavior is:

1. open a dedicated short-lived `SessionLocal` session owned only by this audit
   operation;
2. reload `authenticated_admin_id` in that session and run the corrected binary
   active-admin assertion there immediately before audit construction, so a
   stale route-level authorization result cannot authorize the disclosure;
3. require the action policy category to be exactly `sensitive_read`;
4. validate typed targets and bounded/redacted reason/context through the same
   canonical policy rules used by mutation records, but do not reuse a generic
   full-row reference loader for sensitive-read targets. Database-backed target
   validation must use a minimal existence/classification projection (for
   example, ID plus only the non-protected state needed by the policy) so the
   helper does not hydrate message bodies, financial detail, or other protected
   payload columns before the audit commit;
5. write `outcome=succeeded`, current correlation, and database time;
6. flush and commit the audit row in the helper-owned transaction, then return
   only its committed UUID identity;
7. on authorization, policy, target, reason, or context validation failure,
   roll back/close only the helper-owned session as needed and preserve the
   established safe 4xx behavior without disclosure;
8. on flush, database constraint, connection, commit, or ambiguous-commit
   failure, roll back where possible, close the helper-owned session, and raise
   a stable safe `503` audit-unavailable error without database/provider detail;
9. never call `commit()` or `rollback()` on the caller's request-scoped session,
   so unrelated pending request work cannot be accidentally committed or
   discarded by the audit helper; and
10. never accept or store the protected payload itself.

The caller contract is equally important:

```text
authorize request and derive authenticated_admin_id from that principal
identify the exact target/reference without loading full protected content
record_sensitive_admin_read(authenticated_admin_id=...)
only after the helper returns, fetch/serialize/return protected content
```

If target identity cannot be established without a limited lookup, the lookup
may return only the minimum identifier/classification necessary to audit. It
must not retrieve or expose the protected body before the audit commit. The
caller may already have a request-scoped session with reads or unrelated pending
work; the helper's dedicated transaction must not commit or roll back that
session. If the response fails after the audit commit, the conservative extra
audit row is acceptable. There is no idempotent suppression of actual
disclosures: each successful reveal attempt gets its own audit record and
correlation.

A can prove helper authorization, classification, normalization, correlation,
commit ordering, and failure behavior with a service harness. A full
PostgreSQL success-path record for a concrete read action and proof that content
is not returned before it is committed belong to the first consumer,
`WS03-05D`, and then the remaining inventory in `WS09-02C`.

## 7. Audit-read access and presentation

The correct OPP-11 contract is binary active-admin access. Gate B will:

- retain `Depends(require_active_admin)` on all existing `/admin/actions` and
  rejected-attempt list/log/detail routes;
- replace the current service predicates that effectively check only policy
  existence with an actual `user_is_active_admin`/active-admin assertion;
- apply the same service-level rule to display/embedded reads so a non-route
  caller cannot bypass authorization;
- preserve not-found behavior where needed without disclosing row existence to
  unauthorized users;
- preserve global admin/private cache behavior (`Cache-Control: private,
  no-store`); and
- keep the surfaces read-only, with no moderator, named-permission, or
  resource-scope branch.

API schemas will add `outcome` and `correlation_id` to the raw audit responses
needed for investigation. The compact human-readable log may expose the
outcome while the detail/raw representation carries the correlation identifier.
These are additive response fields; existing filters, pagination, stable
ordering (`created_at`, then `id`), target labeling, and action rendering remain
unchanged.

## 8. Existing-writer compatibility plan

Gate A found all current production files calling `record_admin_action` and all
assignments to persisted `AdminAction` attributes. Gate B must rerun that static
inventory after edits so no new writer is missed.

### 8.1 Refund retry provider checkpoint

Current issue: `backend/services/admin_money_refund_service.py` commits an
`update_refund` `AdminAction` before calling Stripe, then updates the committed
row’s metadata once Stripe returns and updates it again while applying local
state. This accepted multi-transaction checkpoint is necessary, but the row
updates are incompatible with append-only audit.

Planned replacement:

1. create and commit the initial immutable `update_refund` action with
   `outcome=pending`, its stable idempotency identity, targets, reason, and
   pre-provider bounded context;
2. call Stripe with the existing stable provider idempotency key;
3. after a provider response, reload and lock the `Refund`, then append and
   commit the existing typed `RefundEvent(event_type=provider_result_recorded)`
   linked by `admin_action_id`, using a deterministic derived refund-event
   idempotency key;
4. persist the provider ID/status and the refund’s provider-observation snapshot
   in that same checkpoint transaction;
5. in the remaining local-application transaction, reuse the checkpoint event
   instead of appending a duplicate provider-result event, and apply booking,
   payment, money-issue, notification, and other current domain effects; and
6. never update the initial `AdminAction`.

If step 5 fails, the immutable action still proves initiation and the committed
`RefundEvent`/refund snapshot still proves the provider result for existing
reconciliation paths. An idempotent retry finds the existing action and event;
it neither calls Stripe twice nor creates a duplicate event. Tests that
currently treat mutable action metadata as the durable checkpoint will be
changed to assert the authoritative typed refund history instead.

Provider configuration failures/timeouts that produce no known provider result
leave the initial immutable `pending` action. A will not invent a false final
outcome; existing timeout/reconciliation ownership remains intact.

### 8.2 Review-case targets and event IDs

Current issue: `backend/services/admin_review_service.py` sometimes fills
`target_review_case_id` on a pending action through the lifecycle linker, and
the note/close flows append `event_id` to action metadata after the action has
already been flushed.

Planned replacement:

- Resolve the applicable open review-case ID before the action’s first flush
  and include it in the initial typed targets.
- Make the linker operate only on a not-yet-persisted action, or split target
  resolution from event creation so no persistent attribute is changed.
- Keep `AdminReviewCaseEvent.admin_action_id` as the authoritative relationship.
- Stop copying the review event ID back into audit metadata; no current response
  contract requires it.
- Preserve the current review-case event, note, close, lifecycle, concurrency,
  and idempotent replay behavior in the owning transaction.

### 8.3 Need-a-Sub removal closure IDs

Current issue: `backend/services/need_a_sub_post_service.py` writes
`closed_request_ids` into action metadata after creating notices and changing
request state. Existing idempotent replay reads this bounded list, so simply
dropping it would be a regression.

Planned replacement:

- Under the existing removal transaction and locks, determine the active
  request set and stable `closed_request_ids` before the action’s first flush.
- Include the list in policy-validated initial metadata.
- Apply the same request transitions/notices and commit them with the already
  complete immutable action.
- Preserve current replay validation and response construction. Continue using
  `AdminTargetNotice.admin_action_id` for notice discovery.

### 8.4 Financial-outcome notice IDs

Current issue: `backend/services/admin_financial_outcome_service.py` adds notice
IDs to action metadata after the action may have been flushed or committed,
including paths that reload an existing action.

Planned replacement:

- Remove `add_notice_id_to_action_metadata` and every call to it.
- Treat the existing `AdminTargetNotice.admin_action_id` and
  `AdminFinancialOutcome.admin_action_id` relationships as authoritative.
- Query those typed relations anywhere a response needs notice IDs.
- Do not duplicate notice identity in immutable generic metadata.

### 8.5 Explicit current outcomes and database time

Every current production call will remove `created_at=...` and pass an explicit
outcome:

- ordinary successful mutation/action rows: `succeeded`;
- the known `admin_money_issue_service` branch that intentionally records an
  action for a caught `GameCreditLedgerError` and returns failure: `failed`;
- the pre-provider refund-retry action described above: `pending`;
- no other outcome is allowed. If a later result is uncertain, the initiating
  row remains `pending` and the applicable domain reconciliation history records
  what becomes known.

The failed game-credit retry action will replace the current raw
`str(GameCreditLedgerError)` metadata value with a stable non-sensitive failure
code. The existing admin-visible domain issue/event can retain only the safe
summary its contract permits; arbitrary exception text is not audit context.

Domain records keep their own exact application timestamps. Small timestamp
differences between a domain event and the audit row are expected because the
audit time becomes database-owned; deterministic audit ordering remains
`created_at`, then `id`.

### 8.6 Finite writer inventory

The baseline has 46 `record_admin_action` call sites across 25 production
service modules, plus the central correction constructor. Gate B must update
that complete population for the required outcome/database-time contract, then
rerun searches for constructors, raw SQL, attribute assignments, in-place JSON
changes, and bulk ORM updates/deletes to prove there is no unreviewed write
path.

This migration of current writers is compatibility work owned by A. It does
not assert that all privileged workflows emit an action; that inventory and
coverage decision belongs to B.

## 9. Failure, concurrency, and idempotency behavior

- Existing action-specific unique indexes remain the database concurrency
  backstop. Gate B will not replace them with a generic idempotency rule that
  changes current semantics.
- A uniqueness race rolls back the losing transaction and follows the existing
  safe replay/conflict behavior for that action.
- An attempt to mutate or delete a persisted audit row receives the stable
  database immutability error and poisons the current transaction until normal
  rollback. The service must not swallow it and continue committing other
  changes.
- Correction replay uses its existing uniqueness key; a different correction
  body with a reused key is a safe conflict, not a rewrite.
- A mutation-service audit insert failure rolls back the privileged state
  transition.
- A rejected-attempt insert remains separately committed only after the
  rejected operation has been rolled back, preserving the reason this table
  exists.
- Sensitive-read audit failure means no protected content is returned. A safe
  `503` is used for infrastructure/commit uncertainty; validation and
  authorization retain their established safe 4xx behavior. The helper-owned
  session is the only transaction it may commit or roll back.
- Commit-owning correction and sensitive-read helpers must be transactionally
  isolated from the FastAPI request-scoped session. A successful audit commit
  cannot commit unrelated pending request work, and an audit rollback cannot
  discard it. Active-admin status is reloaded and revalidated inside the
  helper-owned transaction rather than trusted from a potentially stale ORM
  object.
- Correlation context is copied at row construction and cannot be changed by a
  later async/task context transition.
- No audit writer is allowed to commit merely to obtain an audit ID; UUIDs are
  available before flush. The refund retry and sensitive-read exceptions commit
  for their documented durability/disclosure boundaries, not identity
  allocation.

## 10. Security and privacy safeguards

- Actor identity for correction and sensitive-read entry points is derived from
  the authenticated admin principal, never from a client-supplied actor ID. The
  commit-owning helper receives that stable identity, reloads the user in its
  own session, and revalidates active-admin status immediately before recording.
  Existing mutation services continue deriving the actor from their
  authenticated route context.
- Correlation IDs come from the trusted middleware/context resolver, not a body
  field. Existing inbound correlation validation/canonicalization remains the
  boundary.
- Existing recursive metadata size/depth/list/string limits and forbidden
  sensitive key/value checks remain mandatory.
- Sensitive-read policies may store identifiers, classifications, and a bounded
  operational reason only. They may not store message bodies, payment method
  details, tokens, secrets, raw HTTP data, raw provider responses, arbitrary
  exception text, or copies of protected records.
- Audit rows and rejected-attempt rows are readable only by active admins and
  use private/no-store response caching.
- Database/constraint/provider error detail is logged only through existing
  safe observability boundaries and is never echoed to a client through the
  audit helper.
- Audit preservation does not override approved identity minimization. Later
  retention/anonymization work must preserve the audit event while applying its
  approved identity policy.
- Trigger enforcement is defense in depth. Final runtime least privilege and
  schema ownership are not claimed until `WS04-01D` proves them.

## 11. Compatibility and rollout impact

### 11.1 Preserved contracts

- Existing action names, typed targets, action policies, reason/metadata bounds,
  idempotency indexes, list/detail/log routes, pagination, ordering, and display
  labels remain unless a focused compatibility fix above requires a documented
  internal metadata change.
- Existing privileged mutations continue to commit their audit record with the
  domain change.
- Existing audit UI/API consumers receive additive outcome/correlation data;
  they do not receive a new mutation surface.
- The retired audit create/note routes remain retired.
- Existing active-admin access remains allowed; non-admin and inactive/deleted
  admin access remains denied.

### 11.2 Deliberate internal representation changes

- Review-case `event_id` and financial-outcome `notice_ids` stop being copied
  into `AdminAction.metadata`; their existing typed relational records are the
  authoritative source.
- Refund provider checkpoints move from mutable action metadata to the existing
  typed `RefundEvent` plus refund provider snapshot.
- Need-a-Sub `closed_request_ids` remain available, but are final at the initial
  insert rather than patched in later.
- Caller-supplied audit `created_at` is removed in favor of database time.

Any backend schema or test that directly instantiates `AdminAction` must be
updated to provide the explicit outcome and canonical correlation. No external
client is entitled to create an audit row directly because those routes are
retired.

### 11.3 Deployment shape

This is a pre-production clean-schema change. Gate B will update model and
canonical migration in one commit series, rebuild disposable databases, and
run the migration lifecycle and complete backend regression suite before
handoff. There is no mixed-version rolling-deploy compatibility claim and no
production data migration.

## 12. Exact execution-register reconciliation for Gate B

The Gate A baseline register is factually stale: it still describes the old
`WS03-05B` PR #176 state and does not record the accepted corrected B or the
accepted C merge. Gate B must update
`docs/production-readiness/planning/program/PASS-EXECUTION-REGISTER.md` in the
substantive branch with the proposed state that becomes true atomically when
the substantive `WS09-02A` PR merges into `develop`. This Gate A plan does not
edit the register.

Before that merge, current repository truth after reconciling the already
merged B/C work is 41 accepted executable passes, 0 implemented-but-unmerged
passes, and 26 genuinely unimplemented units. `WS09-02A` is not currently
accepted, and neither its plan nor a later implementation on an unmerged branch
makes it accepted. Gate B or Gate C approval also does not make it accepted.
The register diff carried by the substantive PR describes the post-merge state
below and becomes factual only through manual merge.

### 12.1 Reconciliation point and counts

In the proposed post-merge register state, set the current reconciliation facts
to:

- accepted pre-`WS09-02A` baseline and B/C reconciliation anchor:
  `31d3db4b2320a5656a081ac8f7bdc206c0b3cf7e`; this is not represented as the
  future merge SHA, which is unknowable during Gate A;
- **42 accepted executable passes**, including `WS03-05A`, `WS03-05B`,
  `WS03-05C`, and the newly accepted `WS09-02A`;
- **0 implemented-but-unmerged executable passes** (`None`);
- **27 genuinely unimplemented executable units**;
- of the `WS03-05` children, only `WS03-05D` remains unimplemented;
- of the `WS09-02` children, `WS09-02B` and `WS09-02C` remain unimplemented;
  and
- parent `WS09-02` remains incomplete.

The count derivation follows the register's executable-unit semantics:

1. Reconcile the already merged `WS03-05B` and `WS03-05C` work to establish the
   factual pre-merge state of 41 accepted, 0 unmerged, and 26 remaining.
2. Replace the one remaining executable parent unit `WS09-02` with its three
   accepted Stage 0 executable children A, B, and C. Before accepting any child,
   that structural change would make the remaining count
   `26 - 1 + 3 = 28`.
3. The substantive merge accepts A, moving that one child from remaining to
   accepted. The final post-merge counts are therefore
   `41 + 1 = 42` accepted and `28 - 1 = 27` remaining.
4. Equivalently, the final remaining calculation is
   `26 - 1 WS09-02 parent + 2 remaining WS09-02 children = 27`.
5. `WS03-05D` was already included in the 26 pre-merge remaining units and
   stays included after merge. A satisfies D's audit-foundation prerequisite;
   it does not complete D or remove D from the remaining count.

As a consistency check, the pre-decomposition executable total is
`41 + 0 + 26 = 67`; replacing one executable parent with three children adds
two units, so the post-merge total is `42 + 0 + 27 = 69`.

Apply the same numbers consistently in the current-state bullets, summary
metrics, accepted-section heading, remaining-section heading, and any prose
that currently says 39 accepted, one unmerged, or describes the stale
composition of the remaining roadmap. Retain
`31d3db4b2320a5656a081ac8f7bdc206c0b3cf7e` as the exact historical baseline
and B/C reconciliation anchor; do not guess a future merge SHA.

### 12.2 Accepted table rows

Add these three rows to the accepted executable-pass table in workstream order:

| Executable pass | Parent | Plan | State |
|---|---|---|---|
| `WS03-05B` | `WS03-05` | `passes/ws03/ws03-05b-conflict-safe-moderation-review-case-lifecycle.md` | Accepted |
| `WS03-05C` | `WS03-05` | `passes/ws03/ws03-05c-moderation-enforcement-safe-notices.md` | Accepted |
| `WS09-02A` | `WS09-02` | `passes/ws09/ws09-02a-reusable-append-only-administrative-audit-foundation.md` | Accepted |

Preserve the existing `WS03-05A` accepted row and change the section heading to
42 accepted executable passes. The A row is proposed accepted-state content:
it does not assert acceptance while the branch is unmerged.

### 12.3 Accepted `WS09-02` decomposition and parent state

Add the accepted Stage 0 decomposition to the historical intake table with:

| Parent pass | Intake record | Historical SHA-256 | Accepted by executable pass | Accepted state |
|---|---|---|---|---|
| `WS09-02` | `docs/production-readiness/planning/passes/ws09/ws09-02-intake.md` | `c40b06efc13518fcf2345392eb6636a516179f3b1d34543713fc5808f9d901c5` | `WS09-02A` | Accepted three-child decomposition. A is accepted; B and C remain. Parent `WS09-02` is incomplete. |

Update the original parent-pass row and add a detailed `WS09-02` decomposition
record stating:

- the accepted Stage 0 decomposition defines these executable children:
  `WS09-02A - Reusable append-only administrative audit foundation`,
  `WS09-02B - Important privileged-mutation audit coverage`, and
  `WS09-02C - Sensitive administrative-read audit coverage`;
- the dependency graph is `WS09-02A -> WS09-02B` and
  `WS09-02A -> WS03-05D -> WS09-02C`;
- A is accepted only in the post-merge state;
- B remains unimplemented and becomes dependency-eligible after A, without
  being automatically selected;
- C remains unimplemented and still waits for accepted `WS03-05D` as well as
  A;
- parent `WS09-02` remains incomplete until B and C are accepted; and
- A unblocks `WS03-05D` but does not accept or complete D.

The remaining-work section must identify the 27-unit post-merge composition
and keep `WS09-02B`, `WS09-02C`, and `WS03-05D` visible with those dependencies.
It must not count the `WS09-02` umbrella as an executable remaining unit after
recording its decomposition.

### 12.4 `WS03-05` reconciliation

Update the `WS03-05` parent and historical decomposition text to say:

- A, B, and C are accepted;
- D is the only remaining child;
- D remains defined by corrected master section 8.1; and
- D depends on the reusable audit foundation in `WS09-02A`.

Keep the four-child historical decomposition and original dependency graph as
provenance; correct their state annotations rather than deleting the history.

Replace the stale B implementation narrative with the corrected accepted
history:

- corrected `WS03-05B` implementation commit:
  `8acf26f6b79da3e3312c595a544354dad6e56859`;
- accepted merge PR: **#177**;
- merge commit: `1fcd8c6cd06b6d70a9231d7cc423ef5bf9b13a9d`; and
- the corrected implementation retains the corrected-master target rather than
  the superseded PR #176 scope.

Add the accepted C history:

- `WS03-05C` implementation commit:
  `320a36961ab9dabcc07f8bb42c8f168f3ab89d79`;
- accepted merge PR: **#178**;
- merge commit: `31d3db4b2320a5656a081ac8f7bdc206c0b3cf7e`; and
- C owns the accepted moderation enforcement action preconditions,
  idempotency/reversal behavior, and safe target notices.

The old PR #176 information may remain only if clearly labeled superseded
historical provenance; it must not remain the current implemented-but-unmerged
state.

The complete register diff must not mark `WS09-02B`, `WS09-02C`, `WS03-05D`,
or either `WS09-02`/`WS03-05` parent complete. It must not change master scope,
reorder unrelated workstreams, or make any other roadmap-state claim.

## 13. Gate B evidence and validation plan

Gate B will produce repository and PostgreSQL evidence proportionate to this
cross-cutting schema/service change. Playwright/browser and live-provider tests
are not required because A adds no browser flow or provider integration.

### 13.1 Static and schema evidence

- Prove model/canonical-migration parity for both audit tables.
- Prove a single Alembic head and successful migration import/definition
  validation.
- On the dedicated disposable migration database, prove a clean base-to-head
  upgrade, downgrade to base where the affected revisions support downgrade,
  and re-upgrade to head. An already-applied copy of an edited canonical
  migration is not a supported upgrade source and must be rebuilt.
- Run schema drift checks after rebuild.
- Search the backend for every `AdminAction` constructor,
  `record_admin_action` call, direct SQL write, ORM bulk write, and persisted
  attribute assignment. Classify every result.
- Search for every audit list/detail/display entry point and show that all use
  the binary active-admin service rule.
- Run formatting/import/lint or compile checks configured for the changed
  backend files, plus `git diff --check`.

### 13.2 Focused persistence tests

Add a platform-level administrative-audit test area consistent with backend
test ownership. On PostgreSQL, prove:

- insertion succeeds with actor, registered action, valid targets, explicit
  outcome, canonical correlation, and database-generated time;
- missing/invalid outcome or correlation is rejected;
- raw SQL and ORM attempts to update each audit table fail with the stable
  trigger error;
- raw SQL and ORM attempts to delete each audit table fail likewise;
- after rollback and a fresh read, the original row is unchanged;
- normal test cleanup still works because row triggers do not claim to block
  schema-owner `TRUNCATE`;
- a correction creates a second, self-FK-linked action while the original
  remains unchanged;
- correction replay is idempotent and note-on-note is rejected; and
- policy registry, model, and database action-type/outcome constraints remain
  synchronized.

### 13.3 Transaction and helper tests

- Force an ordinary audit insert/flush failure and prove the corresponding
  privileged domain mutation is rolled back.
- Prove `record_admin_action` does not commit and rejects a sensitive-read
  policy category.
- Prove the sensitive-read helper requires an active admin, rejects a mutation
  or correction action, captures current correlation, commits before returning,
  never accepts protected payload data, preserves safe 4xx behavior for
  authorization/policy/target/context validation failures, and raises a safe
  `503` without allowing the test disclosure step when durable audit recording
  fails or commit outcome is ambiguous.
- Prove the sensitive-read validation path uses only the minimum target
  existence/classification projection before audit commit and does not call the
  generic full-row target loader or hydrate protected payload columns. Concrete
  protected-resource end-to-end proof remains with the first consumer.
- Prove the sensitive-read helper uses a distinct `SessionLocal` transaction:
  create unrelated pending state in the caller/request session, successfully
  commit a read-audit row, and show that the unrelated caller state remains
  uncommitted and can still be rolled back independently.
- Prove the inverse failure case: with unrelated pending caller state present,
  force the read-audit helper to fail and show that the caller state is neither
  committed nor rolled back by the helper.
- Prove the correction primitive has the same isolation property for both a
  successful correction commit and a forced correction failure.
- Prove authorization is revalidated inside each commit-owning helper's private
  session: an admin that passed the earlier route-level check but is changed to
  a non-active state before helper execution is denied, creates no audit row,
  and cannot reach the disclosure step.
- Prove correlation fallback for a legitimate non-request invocation produces
  a valid UUID and does not reuse stale context.
- Prove the correction primitive and read helper do not expose database error
  detail.

The absence of a concrete sensitive-read action in A is an intentional boundary,
not an untested production path. `WS03-05D` must add the first resource-specific
policy/check entry and PostgreSQL end-to-end success/failure-before-disclosure
test. `WS09-02C` then applies the same contract to its remaining approved
inventory.

### 13.4 Access/API tests

For admin action and rejected-attempt list/log/detail surfaces, prove:

- active admin allowed;
- anonymous request rejected with the established unauthenticated response;
- ordinary user and every non-active/deleted admin state denied;
- service-level direct calls cannot bypass the route guard;
- responses remain `private, no-store`;
- unknown IDs retain safe not-found behavior;
- retired create/correction HTTP routes remain `410` after authentication; and
- additive outcome/correlation serialization does not change paging, ordering,
  display, or target-reference behavior.

### 13.5 Existing-writer regressions

Run the focused suites covering at least:

- admin action and rejected-attempt APIs/services;
- refund retry transaction boundary, provider checkpoint, replay, and local
  apply failure/reconciliation behavior;
- review-case lifecycle, note, close, and enforcement linkage;
- moderation enforcement safe notices and financial-outcome notices;
- Need-a-Sub removal, active-request closure, notices, and idempotent replay;
- game-credit failure/action recording; and
- the other current writer services touched by the explicit outcome/time API
  migration.

Then run the complete backend test suite because the canonical schema and a
widely shared service signature changed. Record exact commands, counts, skips,
failures, and any environment prerequisites in the Gate C evidence. Do not use
SQLite as a substitute for PostgreSQL trigger/constraint proof.

### 13.6 No live operational proof in A

No Stripe call, provider control-plane action, production data inspection,
browser flow, deployment, or observability dashboard is necessary to accept A.
Those would not prove the local foundation and would cross the approved scope.

## 14. Done when

This section is the engineering completion bar for the implementation described
above.

- [ ] Every new `AdminAction` has an authenticated actor, registered action,
  valid typed targets, explicit outcome, canonical correlation, database time,
  and bounded/redacted context.
- [ ] PostgreSQL rejects row updates and deletes for `admin_actions` and
  `admin_rejected_attempts`, while normal test teardown remains viable.
- [ ] Corrections append one self-linked action and cannot alter or chain from
  the original action; their helper-owned commit cannot commit or roll back
  unrelated request-session work.
- [ ] All 46 baseline production writer calls use the new contract and no
  persisted audit attribute is patched after insertion.
- [ ] Refund retry provider-result durability, review lifecycle linkage,
  Need-a-Sub replay, financial notices, and failed credit retry behavior remain
  correct under immutability.
- [ ] Audit reads enforce binary active-admin access at route and service
  boundaries and retain private/no-store responses.
- [ ] The sensitive-read primitive uses an independent helper-owned session,
  revalidates active-admin status there, validates targets without hydrating
  protected payload columns, commits a bounded audit row before returning only
  its UUID identity, fails closed without accepting protected content, and
  cannot commit or roll back unrelated request-session work.
- [ ] Model/canonical-migration parity, clean migration lifecycle, focused
  persistence/transaction/access tests, affected writer regressions, and the
  complete backend suite pass on PostgreSQL.
- [ ] The execution register carries the proposed post-merge state from section
  12: the accepted B/C reconciliation, accepted `WS09-02` intake/decomposition,
  accepted `WS09-02A`, 42 accepted executable passes, zero unmerged, and 27
  remaining units, while `WS09-02B`, `WS09-02C`, `WS03-05D`, and parent
  `WS09-02` remain incomplete until their own substantive work is accepted.
