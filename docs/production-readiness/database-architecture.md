# Pickup Lane Database Architecture

## 1. Scope and authority

This document defines Pickup Lane's database architecture: what each area
stores, how the records connect, and the rules that keep them consistent.
Section 3 identifies approved changes that are not yet in the repository
schema. For exact definitions of the existing tables, see the
[data-model baseline](data-model-baseline.md). The 54 finalized
[page specifications](feature-pages/page-inventory.md) define the product behavior this
database supports.

## 2. Existing table catalog

Every table in this catalog is **existing and retained**. The linked baseline
sections provide the complete definitions. A main table holds the current
state; where a separate history or event table exists, it keeps earlier
changes or processing evidence.

**[Accounts, authentication, settings, and policy](data-model-baseline.md#accounts-authentication-and-user-settings)**

| Table | Responsibility |
|---|---|
| users | One Pickup Lane account: profile, Firebase sign-in link, role, account status, and hosting eligibility. Firebase keeps passwords and reset links; games, bookings, notices, and staff records refer to the account here. |
| user_settings | An account's notification choices and selected location. These preferences can change without changing the account's identity record. |
| user_stats | Stored totals for a player's game and hosting activity, used for the profile. Their freshness depends on updates from the underlying activity records. |
| user_payment_methods | An account's saved Stripe card references and default-card choice. Stripe retains the actual payment-method details. |
| policy_documents | Identifies each version of a legal or policy document so the accepted version can be recorded and retrieved later. |
| policy_acceptances | Records which policy version an account accepted and when. Booking-specific acceptance is stored separately. |

**[Games, venues, and hosting](data-model-baseline.md#games-venues-and-hosting)**

| Table | Responsibility |
|---|---|
| venues | One sports facility or complex, including its location and approval state. Official and community games can reuse the same facility record. |
| venue_images | Images associated with a facility for use across games at that venue; images for a particular game are stored separately. |
| venue_approval_requests | A request to approve a facility and the staff decision on it. The venue record holds the facility's current approval state. |
| games | The shared record for an official or community game: venue, creator and host, schedule, capacity, price, and separate publication, visibility, joining, and game states. |
| community_game_details | Details supplied for a community game, including its description and host instructions. Shared schedule and listing fields remain on the game. |
| game_images | Images attached to one game, distinct from images that belong to its venue. |
| game_status_history | Past changes to a game's status. The game record holds the current state; this table retains the change history. |
| host_publish_entitlements | A host's right to publish a community game, including first-free or separately granted rights. It is distinct from a fee payment. |
| host_publish_fees | The fee and its outcome for publishing a community game. The payment record separately tracks any money charged. |
| community_publish_attempts | Attempts to complete paid community-game publication. They record publication progress separately from the fee and payment records. |

**[Bookings, roster, and waitlist](data-model-baseline.md#bookings-guests-participants-and-waitlists)**

| Table | Responsibility |
|---|---|
| bookings | One buyer's reservation for a game and their party, with the agreed price and current reservation and payment state. Individual roster places are separate. |
| booking_policy_acceptances | The policy version accepted for a particular booking, kept apart from the account's general policy acceptances. |
| booking_status_history | Past changes to a booking's state, retained alongside the booking's current status. |
| game_participants | Individual roster places for players, hosts, staff-added players, and guests. One booking can account for more than one place. |
| participant_status_history | Past changes to a roster place, such as a participant joining or being removed. The participant record holds its current state. |
| waitlist_entries | A player's place in a game's waitlist, with queue order, payment-method and consent context, and the state of any offer or promotion. |

**[Payments and financial records](data-model-baseline.md#payments-refunds-credits-and-financial-records)**

| Table | Responsibility |
|---|---|
| payments | Charges associated with bookings, community publishing, or staff actions, including the payment provider's transaction state. Refunds are separate records. |
| payment_events | Provider and application events for a payment, preserving what happened beyond the payment's latest status. |
| payment_confirmation_attempts | Attempts to confirm a booking after payment, including outcomes needed to retry or reconcile confirmation. |
| payment_compensations | Work needed when a payment and booking workflow diverge. It tracks the correction separately from the payment and any resulting refund. |
| payment_method_operations | Attempts to save, synchronize, choose, or remove a card, including uncertain provider outcomes, so repeated requests can be handled safely. |
| refunds | Cash returned or being returned through a payment provider, with its amount, source payment, and current processing result. Game credit is recorded separately. |
| refund_events | Provider and workflow updates for a refund, retained so staff can trace its processing and reconciliation. |
| game_credits | Credit granted to a player, its remaining balance, source, and current state. Each use or restoration is recorded separately. |
| game_credit_usage | Each credit reservation, redemption, release, reversal, or restoration associated with a booking or payment. |
| admin_financial_outcomes | A staff decision about the financial consequence of a community-game publishing fee, linked to the relevant fee and resulting records. |
| money_issues | A financial problem that needs staff follow-up, linked to the affected payment, refund, credit, booking, or user as applicable. |
| money_issue_events | The sequence of updates and follow-up actions for a money issue; the issue record holds its current state. |

**[Need a Sub](data-model-baseline.md#need-a-sub-posts-and-requests)**

| Table | Responsibility |
|---|---|
| sub_posts | A Need a Sub listing for an outside game, with its owner, schedule, requested help, and current post state. |
| sub_post_positions | Each type of opening requested by a Need a Sub post, including the position, player group, and number of substitutes needed. |
| sub_post_requests | A player's application to fill a Need a Sub opening and the current decision or withdrawal state. |
| sub_post_status_history | Past changes to a Need a Sub post, kept separately from its current state. |
| sub_post_request_status_history | Past changes to a player's Need a Sub application, including decisions and withdrawals, kept separately from its current state. |
| sub_post_chats | A conversation attached to a Need a Sub request. Messages and read positions are stored in separate tables. |
| sub_post_chat_messages | Individual messages in a Need a Sub conversation, including each message's current moderation state. |
| sub_post_chat_reads | How far each person has read in a Need a Sub conversation, without changing the messages themselves. |
| sub_post_chat_message_detections | Moderation detections associated with Need a Sub messages, separate from the message's current moderation state. |

**[Notifications and communications](data-model-baseline.md#notifications-and-communications)**

| Table | Responsibility |
|---|---|
| notifications | Individual notifications generated for a user's Inbox, with their content, destination, and read state. |
| platform_notices | Announcements written by staff for a broad or selected audience, distinct from automatically generated Inbox notifications. |
| platform_notice_recipients | The users chosen for a targeted platform notice and its delivery state, with one record for each notice and recipient. |
| platform_notice_global_seen_states | Each user's last-seen position for notices sent to everyone, so global notices need no separate recipient row per user. |
| platform_notice_selected_reads | Whether each selected recipient has read a targeted platform notice, with one record per notice and user, separate from delivery state. |
| game_chats | Conversation threads attached to games. Individual messages and each user's read position are kept separately. |
| chat_messages | Individual messages in a game conversation, including their current moderation state. |
| game_chat_reads | How far each person has read in a game conversation, without changing the messages. |
| game_chat_message_detections | Moderation detections associated with game-chat messages, separate from the message's current moderation state. |
| admin_target_notices | Notices sent to affected accounts after staff actions, such as changes to a game or post. These are separate from general platform announcements. |

**[Administration, moderation, and auditing](data-model-baseline.md#administration-moderation-and-auditing)**

| Table | Responsibility |
|---|---|
| admin_actions | A record of staff actions and sensitive information viewed by staff, including who acted, when, what was targeted, and the outcome. Some target IDs are audit references rather than enforced foreign keys. |
| admin_rejected_attempts | Records rejected privileged attempts so denied actions remain visible even when no staff action was completed. |
| admin_review_cases | A staff case for reviewing reported or detected content or conduct, with its target and current disposition. |
| admin_review_case_events | The sequence of actions and enforcement links in a review case, while the case holds its current state. |
| admin_review_case_notes | Notes staff add while investigating or closing a review case, kept separate from the case's status history. |
| admin_review_signals | Signals that start a review case or attach to one, preserving the source of the concern. |
| admin_content_moderation_findings | Staff findings about problematic content and the enforcement context associated with a review case. |
| support_flags | Operational problems requiring staff attention, linked to affected records and their current resolution state. They are distinct from content review cases. |

**[Deferred jobs and workers](data-model-baseline.md#durable-jobs-and-worker-operations)**

| Table | Responsibility |
|---|---|
| durable_jobs | Work saved for background processing, with a claim period, retry state, and unique request key so interrupted work can resume without duplicate jobs. |
| durable_job_events | Each job's state and attempt history, preserving what happened even after its current job status changes. |
| durable_worker_heartbeats | One record per worker identity, showing its latest activity and current job so stalled processing can be detected. |

## 3. Approved changes and retained designs

The five schema changes here are **approved but not implemented** in the
repository baseline. This section owns their final design. The linked page
specifications own the corresponding product behavior.

### 3.1. Administrator access management

**Existing:** users has a constrained player/admin role but no distinct
permission; admin_actions records staff actions. **Approved:** add
users.can_manage_admin_access as a non-null Boolean with database default
false, constrained so true is possible only for an administrator. No new role,
permissions table, or owner column.

A usable manager is an active, undeleted admin with this permission and a
currently enabled, linked Firebase identity with a present, verified email.
Access changes require recent authentication and a fresh permission check. A
privileged, auditable one-time bootstrap assigns the admin role and permission
to the first named owner in one transaction, outside ordinary registration;
separate privileged recovery handles loss of all managers and must not silently
rerun bootstrap. The current [bootstrap command](../../backend/bootstrap_admin.py)
grants only the role and cannot run in production.

One shared transaction-level guard covers grants, revocations, demotions,
suspension, deletion staging, and self-deletion, preserving both the last
usable access manager and the existing last-active-admin protection. Acquire
the guard before reading and locking affected user rows; reread actor
permission, target state, and the usable-manager count, then reject a change
that would leave none. Write the change and audit record in the same
transaction. An expressly authorized permission revocation and demotion can
be atomic, with both changes audited; demotion never silently discards the
permission. Existing admin_actions receives distinguishable permission-change
action types and actor, target, reason, before/after, and time evidence.
Record bootstrap and emergency recovery distinctly. Because admin_actions
requires a user actor, retain the privileged external operator's identity in
the privileged-operations audit.

**Provider limitation:** users.email_verified_at is synchronized during
authentication, not a reliable standalone test of another manager's current
Firebase usability. The guard checks current provider state and fails closed
when it cannot verify a remaining manager. A database transaction cannot
prevent an independent later Firebase disable or verification change.

### 3.2. Support-flag review history

**Existing:** support_flags has open/resolved status and resolution details;
admin_actions can target a flag and record resolution. **Approved:** add
nullable support_flags.reviewed_at (timestamp with time zone) and
reviewed_by_user_id (foreign key to users) for the latest review. Add the
review_support_flag action type to the existing admin_actions constraint and
policy. Each review creates an action linked through target_support_flag_id
with actor, reason/note, and time. This target field is an existing logical
audit link, not a declared foreign key in the baseline.

Administrators may review an open support flag. Lock the flag and recheck its
state and reviewer authorization; reject a review submitted after the flag
has been resolved. Write the review action and latest-review pair atomically.
Repeated reviews preserve earlier actions; the latest successful review
updates both fields together without rewriting the original failure.
Reviewing does not automatically change the open/resolved state. No distinct
review-outcome choices were defined by the page specifications: an action
outcome of succeeded means the review action
executed. Existing resolve_support_flag actions and resolution outcomes remain
separate.

A review requires an idempotency key. Under the same row lock, look up a prior
review for the same administrator, flag, and key; return that result only when
the normalized reason and other request details match. Conflicting reuse of
a key is rejected without another review. Concurrent submissions follow the
same locked-state check. No separate review-outcome field or table is approved.

### 3.3. Deleted-account consistency

**Existing:** users constrains account_status and hosting_status separately;
the deletion service writes the desired final values. **Approved:** a users
check constraint: account_status = 'deleted' implies hosting_status =
'not_eligible' **and** deleted_at IS NOT NULL. This applies to the final deleted
state, not intermediate pending_deletion. No new status, column, or table.
Check existing rows and all deletion paths before introducing the constraint.

### 3.4. Changed-official-game removal requests

**Existing:** bookings retain the reservation and price snapshot; refunds,
game_credits, game_credit_usage, and related money records retain financial
outcomes. None stores the player's pending request and choice. **Approved:** a
new game_change_removal_requests table, with:

| Required persisted fact | Final design |
|---|---|
| Identity and relationships | UUID primary key; required booking FK to bookings and requester FK to users; nullable processing-administrator FK to users. |
| Choice | Required, constrained original-payment-method refund or game-credit choice. |
| Lifecycle | Required, constrained status: pending, processing, completed, rejected, or retryable failed; submission and processing timestamps, with absent processing times nullable until applicable. A new request starts pending. |
| Concurrent requests | Database partial uniqueness on booking for statuses pending, processing, and failed. Completed and rejected rows remain as history. |
| Financial linkage | Stable, request-scoped operation keys in existing financial records and their booking/payment references; no duplicated amount, currency, provider, financial-status field, financial table, or mandatory new FK on a financial record. |

Submitting a request changes no booking, roster, refund, or credit. Authorized
processing claims and rechecks the booking and financial records, including
the requester's relationship to the booking and current eligibility. Before
changing the booking or calculating relief, processing accounts for existing
refunds, previously issued credits, and paid guests to prevent duplicate
financial outcomes or incorrect booking changes. Allowed transitions are
**pending → processing → completed**; **pending → rejected** only when the
request becomes ineligible before processing effects begin, not at staff
discretion; and **processing → failed → processing** for recoverable failures.
A failed request remains active and is retried through the same record.
Completion requires both booking removal and actual fulfillment of the chosen
financial relief, including reconciliation of an asynchronous refund.
Transactional locking, stable keys for each financial
leg, provider idempotency, and existing ledger uniqueness prevent duplicate
removals or money. Record the processing administrator, outcome, and
corresponding administrative action. Eligibility, transition order, and
eligible amounts are application transaction rules; the database enforces
references, allowed choice/status values, and one active request per booking.

For a booking paid partly in cash and partly with existing game credit, the
**original payment method** choice refunds the eligible cash-paid portion to
that method and restores the previously used credit. The **game credit**
choice grants the full eligible amount as game credit, covering both original
cash and credit value; it does not also restore the old credit on top of that
full grant. A cash refund cannot exceed cash actually paid, accounting for
prior refunds. The existing refund, credit, and credit-usage ledgers remain
the authoritative financial record: refunds hold original-method cash
returns, game_credits holds newly issued credit, and game_credit_usage records
restoration of previously redeemed credit where applicable. Each financial
leg uses a stable request-scoped operation key and its existing booking or
payment link. This follows [Edit Official Game
§4.7](feature-pages/pages/admin/edit-official-game.md#47-player-notice-and-withdrawal) and
[Official Game Manage
§4.3](feature-pages/pages/admin/official-game-manage.md#43-removing-players).

The exact physical names and server defaults for the request's choice,
status, and timestamp columns are migration-level details not prescribed by
the approved design. They must express the types, nullability, initial state,
and integrity rules above without adding another product decision.

### 3.5. Used-credit integrity

**Existing:** game_credits stores a non-null integer-cent available balance,
status active/used/reversed, and a unique idempotency key. Its checks constrain
the balance range and reversed-credit zero balance, but not used-credit zero
balance. **Approved:** a check constraint requiring credit_status = 'used' to
imply available_cents = 0. Verify existing records first; cancellation
restoration must update balance and status together. Retain used-credit rows
for financial history. No new table, column, or record is required.

### 3.6. Venue reuse without schema change

A venue denotes the facility or sports complex, not each playing field.
Optional field instructions belong in games.description; official-game staff
arrange the actual space. Use one shared lookup and creation routine for
official, community, edit, and direct-creation paths. Match conservatively on
normalized facility **name and full address**, accounting consistently for
case, spacing, and conservative address-format variants; an address alone
does not prove identity. Reuse one unambiguous active, nondeleted facility
without changing its approval status. Inactive, soft-deleted, duplicate, or
ambiguous candidates require explicit administrative resolution.

The current [venue lookup](../../backend/services/venue_service.py) excludes
inactive and deleted records, while
[official-game creation](../../backend/services/official_game_service.py)
rejects a matching venue unless approved. The shared process must resolve
these application differences without silently reactivating, merging,
replacing, or creating a duplicate facility. Check existing duplicate
candidates before rollout.

Before rechecking and inserting, writers using the shared routine acquire a
transaction-level advisory lock on a normalized location bucket based on
country, state, and postal code. This locking key coordinates concurrent
creation attempts; facility identity still depends on the normalized name
and full address above. The lock cannot prevent a writer that bypasses the
routine from creating a duplicate. No field-reservation system,
venue table/column, approval workflow, or venue uniqueness constraint is
approved; a uniqueness rule on address could incorrectly combine different
facilities. See [Create Official Game
§4.3](feature-pages/pages/admin/create-official-game.md#43-venues) and
[Edit Game §4.3](feature-pages/pages/hosting/edit-game.md#43-location-and-save-outcome).

## 4. Implementation considerations

1. **Check data and target first.** Confirm the actual database revision and
   whether it can be rebuilt. Inspect deleted-account rows, usable
   administrators, existing support-flag history, used credits with nonzero
   balances, and duplicate facility candidates. Preserve a safe data snapshot.
   Repository schema declarations do not prove deployed data state.
2. **Align existing tables.** Update the users model and canonical migration
   for the permission and deleted-state check; support_flags for the latest
   review pair and reviewer FK; admin_actions for permission/review action
   types; and game_credits for the used-credit check. Do not invent past
   support-flag reviews. Keep model and migration constraints aligned.
3. **Add the request table.** Give game_change_removal_requests its own
   canonical model and migration after bookings and users. Constrain its
   references, choice, five statuses, and active-request uniqueness. Existing
   financial ledgers retain money, credit, and provider outcomes.
4. **Align the owning services.** Update authorization, bootstrap and
   emergency recovery, account deletion, support review, changed-game
   processing, and credit restoration to maintain their approved invariants.
   Venue reuse is an application change using existing tables. Verify
   unauthorized and concurrent changes, retry/idempotency behavior, mixed
   payments, interrupted processing, and provider uncertainty before rollout.
5. **Deploy and recover deliberately.** Release schema support before
   dependent application paths; preserve request, money, and audit history
   across failures. Under the current
   [database standard](../coding-standards/database.md), editing
   an already-applied canonical revision requires an authorized clean local
   rebuild; a data-bearing database needs an agreed data-preserving path.
   Verify migration ordering, model parity, existing-row compatibility, and
   safe recovery as part of later implementation.

Production bootstrap and recovery operator controls, current Firebase lookup
failure handling, the encoding of request-scoped operation keys, interrupted
processing recovery, and venue normalization/location-bucket encoding are
implementation details within this approved design. They are not additional
product decisions. No database was migrated or tested for this document.
