# WS03-05B - Conflict-Safe Moderation Review-Case Lifecycle

This work gives moderation review cases an explicit, assignable, reopenable,
mergeable, and conflict-safe lifecycle with immutable domain history.

This document is the engineering blueprint for this pass.

## 1. What This Work Does

This section defines the part of moderation review that changes and the
boundaries that remain stable. The result is a review-case aggregate that staff
and automated target-lifecycle rules can update without silently overwriting one
another.

Review cases currently group saved-content findings or chat signals under a
Community Game or Need a Sub post. They support listing, detail, internal notes,
manual closure, selected automatic content-case closures, and event rows. The
current model does not provide assignment, reopening, an explicit merge
workflow, stale-request detection, a complete one-open-case rule for chat, or a
database-enforced immutable and totally ordered event history.

This work establishes one server-enforced case lifecycle for both moderation
categories. It adds current assignee coordination, version preconditions for
reviewer writes, exact case identity and merge rules, attributed automatic
resolution, linked correction notes, deterministic lock ordering, and a usable
admin interface for the resulting workflow.

The accepted moderation taxonomy, scanner provenance, finding and chat-
detection identities, evidence formats, current/historical finding behavior,
and public chat rule keys remain unchanged. Enforcement side effects, user
notice policy, controlled unmasking, minimum-necessary response redesign, and a
reusable cross-domain audit system are outside this work. Existing active-admin
authorization remains authoritative.

## 2. What Must Be True

These requirements define the observable lifecycle and integrity guarantees of
a completed review case. They are the conditions that every API, service,
database constraint, and reviewer interaction must preserve.

### 2.1 Case Identity And Links

A moderation case has an exact aggregate identity made from its case type,
moderation category, and primary target kind and ID. The supported identities
are:

- Community Game saved content: `community_game`, `content_moderation`, and
  `target_game_id`;
- Community Game chat: `community_game`, `chat_moderation`, and
  `target_game_id`;
- Need a Sub saved content: `need_a_sub`, `content_moderation`, and
  `target_sub_post_id`;
- Need a Sub chat: `need_a_sub`, `chat_moderation`, and
  `target_sub_post_id`.

There may be at most one open case for each of those identities. Content and
chat cases for the same target remain separate. The one-open rule must not be
generalized to every review-case target or category that may exist elsewhere in
the data model.

Every case must retain its type, category, priority, exact target links,
creation reason, finding links, signal links, note links, enforcement-action
links, assignee state, resolution state, and merge links. The current automated
producers use the exact creation reasons `content_moderation_finding` and
`chat_moderation_detection`; a blank reason is invalid. Case priority is a
triage value; it must not replace or manufacture the distinct priority,
severity, risk area, category, or provenance stored on an accepted finding or
chat signal.

The current application has no moderation-report record or reporter workflow,
so this work does not invent a synthetic report link. The accepted finding and
signal records are the review inputs that must remain linked.

An identical automated trigger attaches to the existing open case and does not
create a duplicate. A closed case remains historical. New actionable evidence
after closure uses another valid open case unless an administrator explicitly
and validly reopens the closed case first.

### 2.2 States, Resolution, Reopening, And Merging

The externally visible case states remain `open` and `closed`. An open case may
receive findings, signals, internal notes, assignment changes, action links,
and a resolution. A closed case is read-only except for a valid reopen or merge
link operation.

Manual resolution continues to use the accepted outcomes
`enforcement_applied`, `no_action_needed`, and `invalid_signal`. It must record
the acting administrator, timestamp, nonblank reason, case version, and the
direct and merged-source case, finding, signal, and enforcement-action links
that existed at the decision.
Choosing `enforcement_applied` is valid only when the case already has a linked
enforcement action; this workflow does not perform that enforcement itself.

Automatic resolution is limited to the existing saved-content target-lifecycle
rules. Community Game or Need a Sub content cases may close when their target
enters a currently recognized non-actionable terminal state or is removed.
Clean rescans do not close cases, and target lifecycle changes do not
automatically close chat cases. Every automatic resolution records the stable
automation rule and version, trigger, target state before and after, resolution
reason, trigger actor when one exists, and linked admin action when one exists.

A closed, non-merged case may reopen only when its target still satisfies the
accepted actionability rule for its category and no other case with the same
aggregate identity is open. Reopening clears the current closure fields and
current assignment, but preserves the complete prior resolution in immutable
history. Reopening never reactivates a historical finding or changes accepted
finding or signal identity.

Merging links a closed, non-merged historical source case to the already open
destination case for the same aggregate identity. The source must have a
complete prior manual or automatic resolution, must not already point to a
merge destination, must have no incoming merged sources, and cannot be open.
The destination must be the one open case for the identity and must not itself
be a merge source. An open source is therefore an invalid merge input; a valid
merge never requires two open cases with the same identity.

A valid closed source has no current assignment. If the destination is assigned
to another eligible active administrator, the acting administrator must claim
or reassign the destination before merging; otherwise the destination keeps its
existing assignment. Findings, signals, notes, actions, events, and the
source's prior resolution stay on the case where they were created and are not
rewritten or reparented. Merge adds the directional relationship and immutable
events without changing the source's closure outcome, reason, mode, resolver,
automation attribution, timestamp, or closure references. The source becomes
terminal and cannot reopen or merge again. These rules preserve historical
identity, prevent chains and cycles, and retain the one-open-case invariant.

### 2.3 Assignment

An open case may be unassigned or assigned to one user who is currently an
active administrator. Assignment, reassignment, and release are explicit,
idempotent transitions with actor, before/after assignee, timestamp, reason,
and event history.

Assignment is coordination, not authorization. Every review route continues to
require an active administrator, and assignment never grants access. Any active
administrator may add an internal note. A case assigned to another active
administrator must be claimed or reassigned before a manual resolution; an
unassigned case may be resolved by any active administrator. Automatic
resolution may close an assigned case and must record and clear the prior
assignment as part of the transition.

If an assignee later becomes inactive, deleted, or ceases to be an
administrator, the stored assignment remains attributable but cannot prevent
another active administrator from claiming, reassigning, or resolving the
case. No assignment lease, presence indicator, expiry interval, workload
balancer, escalation timer, or separate queue is introduced because the current
admin model defines neither team queues nor service-level timing policy.

### 2.4 Internal Notes

Review-case notes are explicitly internal-only. Note bodies are server-
validated, length-bounded plain text and are rendered as text rather than
markup. The request contract accepts no attachment or user-visible-note mode.

Normal application workflows must not edit or delete a note. A correction is a
new note with an optional durable link to the note it corrects; that referenced
note must belong to the same case. The note row's nullable `corrects_note_id`
self-reference is the canonical source of truth for that relationship. A
correction cannot reference itself, and application validation must reject a
reference to a note from another case. The original and correction remain
visible and ordered in history. Note serialization exposes `corrects_note_id`
so the workspace can render the relationship without reconstructing it from
event metadata. A note may be added only while the case is open and within the
existing per-case note limit.

### 2.5 Ordered, Append-Only Domain History

Every review-relevant aggregate change must append a case event in the same
transaction as the changed state. This includes case creation, finding and
signal attachment or current-state changes, priority changes represented by
those source events, assignment and reassignment, notes, enforcement-action
links, manual or automatic resolution, merge links, and reopening.

Events have a gap-free, increasing sequence within each case and carry the case
version produced by that event. Ordering uses sequence, not timestamp. Event
types and actor kinds are finite and validated. Human events identify the
acting user. Automatic resolution events identify the automation rule and
version and separately preserve the triggering user or admin action when one
exists. Merge events identify both cases and direction.

A closure event owns normalized immutable reference rows for every direct or
merged-source finding, signal, enforcement action, and source case included in
the decision. This keeps resolution attribution queryable and foreign-keyed
without placing an unbounded ID array in event JSON. A reopen event links to the
case's applicable prior closure event. A source-side merge event links to the
source's retained prior closure event, and the destination-side reciprocal
event links to that source merge event and source case. These events do not copy
or replace the prior resolution reason or references.

Event payloads contain only the typed IDs, finite state values, safe operation
context, and before/after values needed to explain the transition. Raw message
text, raw finding evidence, note bodies, scanner expressions, credentials, and
exception text must not be copied into event metadata or logs.

The event table is immutable after insert. Normal service code exposes no
update or delete path, and PostgreSQL must reject a direct update or delete of
an event row. This is a review-case domain guarantee, not a replacement for the
application's broader administrative audit system.

### 2.6 Idempotency And Concurrent Review

Every reviewer mutation requires a nonblank idempotency key and the exact case
version the reviewer saw. Merge requires the seen versions of both source and
destination. An exact replay returns the prior action result without another
state change, note, action row, or event. Reuse of a key with different input is
a conflict.

The persisted action stores a request fingerprint, the case version or versions
to which it applied, and the resulting version or versions. Replay responses
distinguish those applied versions from the current case version so a later
transition cannot make an old successful action look newly applied.

After idempotency replay is checked, the service must compare the supplied
version with the locked current version. A mismatch returns HTTP `409` with a
stable error code and only a non-sensitive current snapshot: case ID, status,
version, priority, assignee ID, closure outcome, merge destination ID, and
update timestamp. It must not apply a best-effort write or expose findings,
signals, notes, evidence, or raw target content in the conflict response.

Creation, attachment, reopening, merging, manual resolution, automatic
resolution, assignment, and notes each commit their case state, domain event,
and applicable admin action atomically. A failure rolls back all effects from
the attempt.

All workflows that can create or mutate a case lock in one order:

1. the primary target row;
2. affected case rows ordered by case ID;
3. linked finding, signal, note, and admin-action rows in stable ID order.

A route may read an unlocked case only to discover its target, then it must
lock the target and re-read and validate the case before deciding. The content
scanner retains its accepted target-first contract. Chat projection adopts the
same parent-target-first rule.

The service performs a fast replay lookup before locking, then repeats that
lookup after acquiring its locks and before comparing versions. The second
lookup makes concurrent requests with the same key converge on the winner's
recorded result. The database uniqueness rule on the scoped action key remains
the final safeguard.

Retries are limited to the named one-open-case, scoped action-key, or accepted
source-attachment uniqueness races. A retry must roll back, discard stale ORM
state, reacquire the target and case rows, and make one fresh decision. Check,
foreign-key, event, note, evidence, or other integrity failures must not be
retried as creation races.

### 2.7 Admin API And Workspace Behavior

List and detail responses expose case version, assignment, merge relationship,
resolution attribution, and ordered event information needed to operate the
lifecycle. Listing supports both moderation categories and the existing status
and target filters, plus `mine` and `unassigned` coordination filters. Existing
pagination remains stable and deterministic. The pagination cursor is bound to
the complete result-shaping query context, including status, category, target
filter, and assignment mode. A cursor created for `all`, `mine`, or
`unassigned` cannot be reused under another assignment mode. For `mine`, the
authenticated administrator ID is also part of the cursor context so a cursor
created by one administrator cannot paginate another administrator's assigned
case set. A cursor/query-context mismatch is rejected rather than silently
reinterpreted.

The admin API provides explicit assignment, note, close, reopen, and merge
commands. Requests reject unknown fields and invalid finite values. All routes
use the existing active-admin dependency. Reopen and merge are ordinary review
workflow actions and do not introduce recent-authentication or a new permission
model.

The review-case workspace must show content and chat cases, current assignment,
case status and version, compatible merge links, immutable note corrections,
resolution history, and the totally ordered timeline. It sends the displayed
version with every mutation. On a version conflict it replaces stale local
state with the returned safe snapshot and reloads detail before allowing a new
decision. Controls remain disabled while their request is in flight.

Existing finding and signal response fields remain compatible. Target-derived
admin-action linking must name the expected case category and exact target
identity; it may not select the first open case across content and chat.

## 3. Design

The design makes the case row the current aggregate projection and the event
rows its immutable explanation. Database constraints prevent duplicate open
work, while short transactions and version preconditions make concurrent
review outcomes explicit.

### 3.1 Case Projection And Database Constraints

Extend the case projection with:

- a positive `case_version`, initialized by the creation event;
- a nonblank bounded creation-reason code, with the two current automated
  producer values defined in section 2.1;
- nullable current assignee and assignment timestamp;
- a finite resolution mode distinguishing manual and automatic closure;
- nullable automation rule ID and version for automatic closure;
- a nullable self-reference for `merged_into_case_id`.

The current closure columns remain the public resolution projection. Database
checks enforce a complete open or closed shape, valid manual and automatic
resolution attribution, a merge link only on a closed resolved source, no
self-merge, and assignment only on an open case. Service validation under lock
enforces that the merge destination is the distinct open case for the same
identity. A merged source keeps its prior resolution and gains only the merge
link.

The resolution shapes are exact. Open cases have no closure outcome, reason,
mode, timestamp, resolver, or automation identity. Manual closure uses mode
`manual`, one of the three requestable outcomes, and an administrator resolver.
Automatic closure uses mode `automatic` and requires a nonblank automation rule
ID and version; a user who triggered the target transition may remain visible
as `closed_by_user_id`, but the mode and rule identify the resolver. Merge is
not a resolution mode and `merged` is not a closure outcome. Adding a merge link
to a closed source does not change its existing manual or automatic resolution
shape.

Replace the content-only one-open indexes with two category-aware partial
unique indexes: one over Community Game target plus category and one over Need
a Sub target plus category, each restricted to its matching case type,
supported moderation categories, non-null primary target, and `open` status.
This enforces the four identities in section 2.1 without imposing a universal
one-case rule on user, payment, request, financial, or other case types.

Model constraints and canonical table migrations must describe the same finite
sets, columns, foreign keys, defaults, checks, and indexes. Under the current
clean-rebuild policy, the migrations that originally create review cases,
notes, events, and review-case admin-action values are updated directly; no
patch migration or data backfill is added. The genuinely new normalized
resolution-reference table receives the next schema revision.

### 3.2 State Transition Service

One review-case service owns target locking, state validation, version changes,
event creation, idempotency, and transaction completion. Routes only validate
HTTP shapes and pass the authenticated administrator to that service. Source
adapters call narrow case-creation and source-link operations rather than
mutating the case projection themselves.

The permitted transitions are:

| Current state | Command or trigger | Result |
|---|---|---|
| no case | accepted finding or chat-signal trigger | create one open, unassigned case and its creation event |
| open | accepted finding or signal change | retain identity, update derived priority when needed, append the source event |
| open | add note or change assignment | remain open and advance version |
| open | manual resolution | close with a manual outcome and clear assignment |
| open | accepted target-lifecycle rule | close automatically and clear assignment |
| closed, non-merged | reopen | become open with no current resolution or assignment |
| closed source with a complete prior resolution and no incoming or outgoing merge link | merge into the compatible open destination | preserve the source resolution and records, link both cases, and make the source terminal |

Every other transition is rejected. A repeated command succeeds only through
its exact idempotent replay. Closing an already closed case, reopening a merged
case, merging across identities, assigning a closed case, or writing a note to
a closed case is not treated as a harmless state change.

Manual and automatic closure snapshot the current linked findings, signals,
enforcement actions, and merged source cases as typed resolution-reference rows
owned by the closure event. Reopening points its event to that closure event
before clearing current closure fields. The source-side merge event points to
the retained closure event rather than overwriting or copying the prior
resolution.

### 3.3 Assignment And Reviewer Commands

Assignment accepts an active-admin user ID or null, a reason, an idempotency
key, and the expected case version. The existing admin user lookup, filtered to
active administrators, supplies assignee choices. The service revalidates the
selected user under the transaction; frontend filtering is not sufficient.

Assignment events record previous and next assignee IDs. Reassigning to the
already-current assignee with a new key is rejected as no state change; an exact
key replay returns the original result. Release uses the same transition with a
null next assignee. Manual resolution rejects a different assignee only while
that assignee is still an eligible active administrator; an ineligible stored
assignee is preserved in history but cannot strand the case.

Note creation adds fixed internal visibility and an optional correction link.
`AdminReviewCaseNote` gains a nullable `corrects_note_id` self-reference using
a restrictive foreign key. This column is the canonical durable correction
relationship; the `note_added` event repeats the referenced note ID only as
immutable transition history and is not the source of truth for reconstruction.
The database rejects self-reference, while the service validates the referenced
note under the locked case and requires it to belong to that same case before
inserting the correction. Note serialization returns `corrects_note_id` for the
workspace and API consumers. Existing status and edit/delete response fields may
remain for compatibility, but newly built database rows are constrained to
active, unedited, undeleted notes and no application mutation endpoint is
provided.

Reviewer operations use `assign_review_case`, `reopen_review_case`, and
`merge_review_case` admin-action types in addition to the existing
`add_review_case_note` and `close_review_case` types. Assignment, reassignment,
and release all use `assign_review_case` with explicit before/after values.
Policy, display rules, finite database values, target requirements, and
idempotency indexes remain in parity. Safe metadata records the request
fingerprint, applied and resulting versions, state codes, IDs, and hashes where
needed; it does not duplicate note or evidence text.

### 3.4 Reopen And Merge Mechanics

Reopen locks the target, the candidate case, and any current case with the same
identity. Saved-content cases use the accepted actionability predicates:
cancelled, completed, expired, removed, or soft-deleted targets cannot reopen.
Chat cases require the parent target to remain present but are not closed or
blocked merely because the related activity has ended. If a compatible open
case already exists, reopen returns a conflict identifying that case; it does
not silently merge or move accepted evidence.

Merge locks the shared target and both case rows by ID. It revalidates that the
source is closed with a complete retained manual or automatic resolution, has
no merge destination or incoming merged sources, and is distinct from the
destination. It also revalidates that the destination is the existing open case
for the same exact identity and is not itself a merge source. The source cannot
be reopened while that compatible open destination exists, so merge never
depends on or creates a two-open-case state.

The source keeps all of its child rows and existing resolution fields. A
source-to-destination self-reference and paired directional events make
navigation and history explicit. The source-side event identifies its retained
closure event; the destination-side event identifies the source case and its
reciprocal event. The destination version advances for the incoming link and
the source version advances for its outgoing link, but merge does not close or
re-resolve either case. A later destination resolution includes the merged
source case and its applicable child records in normalized closure references.

Because a valid source is closed and therefore unassigned, a valid merge has at
most the destination's current assignee. After locking both cases, the service
revalidates that assignee and requires the acting administrator to claim or
reassign the destination first when another eligible active administrator owns
it. Database checks prevent self-links and open merge sources; service
validation prevents repeated merges, chains, and cycles by rejecting an
already-merged source, a source with incoming merged cases, or a destination
that is itself merged.

Detail serialization returns concise linked-case summaries and routes staff to
the original case for its findings, signals, notes, and events. This avoids
rewriting the accepted finding identity, whose durable scope includes its
original review case and target context.

### 3.5 Event Sequence And Immutability

Creating an event is the only way to advance `case_version`. Case creation
atomically initializes both the case version and creation-event sequence to
`1`. For every later event, the builder holds the case lock, increments the
version, uses that value as both the new aggregate version and event sequence,
validates the event-specific actor and references, inserts the event, and
updates the case timestamp.

Each case has a unique `(review_case_id, event_sequence)` constraint. Reads sort
by sequence. Events may carry a restrictive self-reference to a prior event for
reopen or merge attribution.

Each resolution-reference row belongs to one closure event and has exactly one
typed reference: finding, signal, enforcement action, or merged source case. A
unique constraint prevents the same typed reference from appearing twice for
one closure. Finding and signal references also snapshot whether that record
was current at resolution; that field is null for action and source-case
references. The service derives the complete reference set after locking the
case and linked rows, inserts it with the closure event, and never accepts it
from the client.

The database rejects `UPDATE` and `DELETE` against review-case event and
resolution-reference rows through table-specific immutability triggers.
Application code never performs a history mutation, and rollback of the owning
transaction removes both the state change and its uncommitted event and
references.

Event and resolution-reference foreign keys to the case, actor, action,
finding, signal, note, related event, and related case use restrictive deletion
rather than cascades or `SET NULL` so a referential action cannot silently
rewrite or remove history. Current user and moderation deletion workflows
retain rows through soft-delete or historical state, so this preserves the
accepted runtime behavior while making accidental hard deletion explicit.

The finite event types are `case_created`, `finding_attached`,
`finding_cleared`, `signal_attached`, `signal_superseded`,
`signal_reactivated`, `note_added`, `assignment_changed`,
`enforcement_action_linked`, `closed`, `reopened`, `merged_into`, and
`merged_from`. Event actor kind is either `admin` or `automation`; an automatic
event may separately identify the user or admin action that triggered it.

The event builder has a typed payload builder for each event type. It rejects
impossible combinations such as an assignment event without a next or previous
assignee, an automatic closure without rule identity, a merge without a related
case, or a source event that references both a finding and signal. Priority
before/after values travel on the finding or signal event that caused the
derived case-priority change rather than producing a second event and version.

### 3.6 Creation, Source Updates, And Automatic Resolution

Saved-content and chat adapters acquire their parent target before finding or
creating a case. The category-aware uniqueness constraint is the final
safeguard if two independent sessions still attempt creation. On the named
constraint conflict, the losing transaction rolls back and performs one fresh
target-first reconciliation. Existing accepted finding and detection
identities, source hashes, evidence, and attachment idempotency remain the
inputs to that decision.

Finding attachment and clearing continue to follow the accepted saved-content
lifecycle. They now advance the case through the common event builder. Chat
signal attachment, supersession, and reactivation do the same, and case
priority is recomputed from current linked records rather than remaining
permanently elevated by a historical signal. Source severity remains on the
signal or detection and is not inferred from case priority.

Automatic closure uses one versioned target-lifecycle policy owned by the
review-case domain. Its rule ID is
`moderation_review_case.target_lifecycle_resolution` and its initial version is
`1`. Existing callers provide the exact lifecycle action, before/after target
state, trigger actor, timestamp, and linked admin action. The helper locks and
revalidates the target and case, applies the transition only if the content case
is still open, and appends one attributed closure event. If a concurrent human
transition wins, the automatic path observes the new state and performs no
second closure.

### 3.7 API Errors And Frontend State

The existing note and close routes keep their paths and add the expected
version requirement. `POST /admin/review-cases/{review_case_id}/assignment`
sets or releases the assignee. `POST /admin/review-cases/{review_case_id}/reopen`
reopens that case. `POST /admin/review-cases/{review_case_id}/merge` treats the
path case as the source and accepts the destination case ID and both expected
versions. The list route accepts `assignment=all|mine|unassigned`, with `all` as
the default. The list cursor preserves the existing `(updated_at, id)` ordering
position and also encodes the full filter context. That context includes the
assignment mode and, for `mine`, the authenticated administrator ID. Cursor
decoding validates those values against the current request and active viewer;
any mismatch uses the existing invalid/mismatched-cursor error behavior rather
than applying the cursor to a different result set.

Mutation schemas require bounded reasons, idempotency keys, positive expected
versions, and only the fields needed by that command. Validation failures use
the existing request-validation contract; missing resources remain `404`;
invalid transitions and stale versions use `409`. The conflict codes are
`review_case_version_conflict`, `review_case_idempotency_conflict`,
`review_case_assignment_conflict`, `review_case_open_identity_conflict`, and
`review_case_transition_conflict`; each response includes only the applicable
safe snapshot defined in section 2.6. Mutation results include
`idempotent_replay`, the applied and resulting versions, and the current case
projection; merge returns both source and destination projections.

The frontend keeps the server response as its only authoritative case
projection. It does not increment versions optimistically. After success it
replaces local detail with the returned case. After a stale conflict it shows a
concise conflict message, applies the safe snapshot, reloads the case, and
requires the administrator to reconsider the action.

The list page no longer hard-codes saved-content cases. Category and assignment
filters are explicit controls, and status tabs remain stable. The detail page
renders chat signal summaries as well as saved-content findings, assignee and
merge state, closure or reopen controls, linked cases, internal note
corrections, and event sequence. It does not expose new raw evidence or message
content.

## 4. Failures And Edge Cases

These cases cover invalid input, stale state, and races that could otherwise
produce duplicate work, lost reviewer decisions, or misleading history.

1. **Concurrent creation for one moderation identity**
   - **Condition:** Independent sessions attach findings or signals to the same
     target and category before either sees an open case.
   - **Required behavior:** The category-aware unique constraint permits one
     open case. The named loser rolls back and retries once from fresh locked
     state, producing no duplicate case or attachment event.

2. **Unrelated integrity failure during creation**
   - **Condition:** A check, foreign-key, event, evidence, or other constraint
     fails while creating or attaching to a case.
   - **Required behavior:** Roll back and surface the failure. Do not classify
     it as a creation race or retry it.

3. **Stale reviewer command**
   - **Condition:** The supplied version no longer matches after target and
     case locks are acquired.
   - **Required behavior:** Return the safe `409` snapshot and commit no note,
     assignment, state change, admin action, or event.

4. **Exact replay after another transition**
   - **Condition:** A client retries an already-applied key after the case has
     advanced again.
   - **Required behavior:** Return the recorded action as an idempotent replay
     without reapplying it; distinguish its applied version from the current
     case version.

5. **Idempotency-key mismatch**
   - **Condition:** The same actor and command key are reused with a different
     reason, body, assignee, correction link, outcome, merge target, or version.
   - **Required behavior:** Return `409` and make no change.

6. **Note races with resolution**
   - **Condition:** One administrator adds a note while another resolves the
     same seen case version.
   - **Required behavior:** Exactly one transition wins. The loser receives a
     stale conflict; no note may appear on the closed case through the losing
     request.

7. **Assignment changes during resolution**
   - **Condition:** Claim, reassignment, release, and resolution compete.
   - **Required behavior:** Version and assignment preconditions prevent a
     resolution from silently overriding the new assignee. An exact replay
     remains idempotent.

8. **Assignee becomes ineligible**
   - **Condition:** The assigned user is suspended, deleted, or loses the admin
     role before the case is resolved.
   - **Required behavior:** Preserve attribution, identify the assignee as no
     longer eligible, and allow another active administrator to claim or
     reassign the open case. Assignment grants no route access.

9. **Invalid reopen**
   - **Condition:** The case is merged, the target is missing or non-actionable,
     or another compatible case is already open.
   - **Required behavior:** Reject with `409`, preserve the prior resolution,
     and identify the existing open case when that is the conflict.

10. **Invalid or competing merge**
    - **Condition:** The source is open, lacks a complete prior resolution, or
      is already merged or has incoming merged sources; cases differ in
      identity; the destination is not open or is itself merged; a self-link,
      chain, or cycle is attempted; the destination is assigned to another
      eligible active administrator; or another transition wins first.
    - **Required behavior:** Reject without moving child rows or partially
      linking either case. Do not close or manufacture a resolution for the
      source. A valid closed-source merge competing with a destination
      transition is resolved by versions and stable lock order without
      deadlock.

11. **Human resolution races automatic resolution**
    - **Condition:** A target enters a terminal lifecycle state while a reviewer
      submits a manual decision.
    - **Required behavior:** Target-first locks establish one winner. The final
      case has one resolution, one matching closure event, truthful attribution,
      and no stale assignment.

12. **Scanner or chat projection races closure or reopen**
    - **Condition:** Source reconciliation overlaps a reviewer transition.
    - **Required behavior:** Revalidate under target-first locks. Never mutate a
      closed historical case, duplicate an open case, reactivate an accepted
      historical finding, or attach a source record to the wrong case.

13. **Ambiguous target-derived action link**
    - **Condition:** Content and chat cases are both open for one target and an
      action linker supplies only the target.
    - **Required behavior:** Require the expected category and exact identity;
      never link to whichever case sorts first.

14. **Event or admin-action write fails**
    - **Condition:** The current projection changes but its required history or
      admin action cannot be inserted.
    - **Required behavior:** Roll back the whole operation so current state and
      history cannot diverge.

15. **Direct history mutation**
    - **Condition:** SQL attempts to update or delete an existing case event.
    - **Required behavior:** PostgreSQL rejects the statement and leaves the
      event and case projection unchanged.

16. **Sensitive data reaches a conflict, event, or log**
    - **Condition:** A transition fails around a case containing private chat,
      finding evidence, notes, or target text.
    - **Required behavior:** Return and log only safe operation context,
      identifiers, finite state, and exception category. Do not include raw
      content, evidence, note text, SQL parameters, or tracebacks that disclose
      those values.

17. **Pagination cursor is reused under a different assignment context**
    - **Condition:** A cursor created for `all`, `unassigned`, or one
      administrator's `mine` result set is supplied with another assignment
      mode or another administrator's `mine` request.
    - **Required behavior:** Reject the cursor as mismatched. Do not reinterpret
      its `(updated_at, id)` position against a different result set.

## 5. Testing

Testing must prove the state machine at its owning layers and show that
concurrent sessions converge on one truthful case projection and history. Green
request tests alone are insufficient for database uniqueness, immutability, or
locking claims.

### 5.1 State And Validation Tests

Pure service and schema tests cover every allowed and prohibited transition,
all finite status, outcome, resolution-mode, event-type, actor-kind, category,
case-type, and priority values, the two accepted automated creation reasons,
blank creation-reason rejection, and malformed or extra request fields. They
verify internal-only note validation, durable same-case correction links,
self-reference rejection, assignment eligibility, closed-source/open-
destination merge compatibility, open-source rejection, actionable reopen
rules, exact replay, and mismatched key rejection. Merge tests reject an
already-merged source, a source with incoming merged cases, and a destination
that is itself merged, and prove that no merge resolution mode or `merged`
closure outcome is accepted or manufactured.

The tests prove that source severity and accepted provenance are preserved
separately from case priority. Mutation tests must reject unsupported finite
values and invalid cross-field combinations rather than relying only on happy
paths.

### 5.2 PostgreSQL And Migration Tests

PostgreSQL-backed tests prove one open case for each of the four moderation
identities, while allowing content and chat cases for the same target and not
imposing that cardinality on unrelated case types. They directly exercise
closure-shape, assignment, closed-source merge-link, event-reference, event-
sequence, note-immutability-shape, and finite-value constraints. Direct writes
must reject a merge link on an open or unresolved source and preserve the
source's prior manual or automatic resolution fields.

Direct database tests prove that event and resolution-reference updates and
deletes are rejected, resolution references enforce exactly one typed target
and no duplicates, event sequences are unique and ordered, note correction
self-references enforce referential integrity and reject self-links, failed
transitions roll back all related rows, and model, canonical migration, and
live-database definitions agree. Service-backed persistence tests additionally
prove a correction cannot reference a note from another case and that the
serialized durable relationship survives reload. A clean base-to-head build and
downgrade/rebuild cycle must produce the complete schema without a patch
revision for existing tables.

### 5.3 API And Authorization Tests

API tests cover list, detail, assignment, note, close, reopen, and merge for an
active administrator, plus anonymous, player, suspended, deleted, pending-
deletion, and stale-admin denial. Rejected requests assert both status and the
absence of case, note, event, assignment, and admin-action side effects.

Contract tests cover required versions and idempotency keys, bounded reasons,
unknown fields, invalid UUIDs and enums, stable conflict codes, safe conflict
snapshots, response-model and OpenAPI shape, and the absence of raw evidence or
note content in errors and logs. Pagination tests prove filter parity and
cursor-context binding across status, category, target type, and assignment
mode; they reject cross-mode cursor reuse and reject a `mine` cursor when the
authenticated administrator does not match the cursor's owner. Note response
tests prove `corrects_note_id` is returned from persisted state rather than
reconstructed from event metadata.

### 5.4 Deterministic Concurrency Tests

Independent PostgreSQL sessions and explicit barriers, not sleeps, force the
important races:

- saved-content case creation against saved-content creation;
- chat case creation against chat case creation;
- note against manual resolution;
- assignment against reassignment or resolution;
- manual resolution against automatic target-lifecycle resolution;
- reopen against new case creation;
- closed-source merge against a prohibited source reopen attempt;
- closed-source merge against destination assignment or resolution;
- finding or signal attachment against closure.

Each test asserts the committed winner, loser response, final version, open-
case count, note and action count, exact event sequence and references, source-
record ownership, assignment state, rollback freshness, and absence of partial
or stale rows. Lock-order tests use bounded joins or database lock timeouts to
prove completion without deadlock; a timeout is a failure, not a retry-based
pass.

### 5.5 Source And Lifecycle Compatibility Tests

Compatibility coverage reruns the accepted saved-content and chat taxonomy,
evidence, persistence, historical-finding, repeated-message, and source-
projection scenarios with the new case lifecycle. It proves that closed cases
remain historical, clean rescans do not close cases, reappearance does not
rewrite old findings, chat public rule keys remain stable, and category-aware
case selection never mixes content and chat.

The existing Community Game and Need a Sub terminal lifecycle callers are
covered for manual, admin, scheduled, deleted, completed, expired, cancelled,
and removed triggers where applicable. Tests verify the exact automatic rule
identity, before/after target state, linked action, assignment clearing, and
single closure event.

### 5.6 Admin Workspace And Regression Tests

Existing Node unit tests cover pure category and assignment filtering,
versioned API payload construction, event-sequence ordering, formatting, and
stale-conflict state helpers. The implementation must not add an unconfigured
React component-test framework. The production frontend build and applicable
static checks verify the route code, imports, and JSX.

A focused manual check with synthetic local cases verifies rendered content and
chat states, in-flight control disabling, assignment eligibility display, note
correction links, close/reopen/merge controls, linked-case navigation, and the
visible stale-conflict reload flow. This manual interaction check does not
replace the backend tests that own authorization, state, persistence, and
concurrency safeguards.

Affected admin route inventory, active-request bounds, recent-auth inventory,
admin-action policy/display parity, response-model negative-space, saved-
content moderation, chat moderation, and migration compatibility scopes must
remain green. Because this changes shared review-case persistence and several
transactional callers, the complete trusted backend suite is required once
after focused validation. Historical legacy tests are not acceptance evidence.

## 6. Done When

This checklist is the engineering completion bar for the pass. Every item must
be true in the resulting system, not merely described by code or a passing
mock.

- [ ] The four moderation case identities each enforce at most one open case
      without conflating content and chat or constraining unrelated case types.
- [ ] Open, manual-close, automatic-close, reopen, and closed-source merge
      behavior follows the explicit transition rules; merge never requires two
      open cases, changes the source's prior resolution, or moves accepted
      source records.
- [ ] Assignment coordinates active administrators without granting access,
      and ineligible assignees cannot strand an open case.
- [ ] Notes are internal, validated, attachment-free, immutable through normal
      workflows, and corrected only by linked follow-up notes.
- [ ] Every material case change advances one version through an ordered,
      attributed event; closure references are normalized and immutable; and
      PostgreSQL rejects history updates and deletes.
- [ ] Reviewer writes use exact idempotency and version preconditions, return
      safe stale-state conflicts, and never silently overwrite concurrent work.
- [ ] Target-first locks, category-aware uniqueness, and narrowly classified
      retries make creation, source attachment, resolution, reopen, and closed-
      source merge converge without deadlocks, duplicate open identities, or
      partial state.
- [ ] Existing automatic content-case closures are fully attributed, while
      clean rescans and chat cases retain their accepted closure behavior.
- [ ] Admin APIs and the review workspace support the complete lifecycle for
      saved-content and chat cases under the existing active-admin policy.
- [ ] The accepted moderation taxonomy, finding and detection identity,
      evidence, historical lifecycle, chat behavior, and public rule keys remain
      compatible.
- [ ] Models, canonical migrations, and the live PostgreSQL schema agree, and
      focused, concurrency, compatibility, frontend, migration, and complete
      trusted-backend validation pass.
