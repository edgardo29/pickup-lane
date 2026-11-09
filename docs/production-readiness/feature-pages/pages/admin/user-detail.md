# F40 — User Detail

## 1. Existing Route(s)

- `/admin/users/:userId`

## 2. Purpose

User Detail gives staff a support view of one account: who the user is, the
account's current state, recent game and Need a Sub activity, and past admin
actions. It is also where authorized staff manage administrator access,
suspend or restore the account, restrict or restore hosting, investigate
account-deletion failures, and delete the account through guarded steps.

## 3. Main Functionality

### 3.1. User Summary and Account State

- **User Summary:** full name, email, email verification status, role,
  member-since date, and a short user ID.
- **Account State:** account status, hosting status, and deletion status.

The page title is the user's name. **Back** returns to
[User Directory](user-directory.md), and **User Money** opens the account in
[User Money](user-money.md).

### 3.2. Accountability Summary

Counts of games played, games hosted, no-shows, late cancellations, and host
cancellations.

### 3.3. Activity Previews

- **Game Activity** shows the five most relevant games with location, date and
  game type, the user's role (player or host), and outcome.
- **Need a Sub Activity** shows the five most relevant posts created and
  requests made, with location, date, type, status, and subs needed or post
  status when relevant.

Rows open the game or post's admin page. **View all** opens
[User Game Activity](user-game-activity.md) or
[User Need a Sub Activity](user-need-a-sub-activity.md).

### 3.4. Admin Actions

This section lists up to 50 recent admin actions on the account with the action,
reason, admin, and time. It also holds the available account controls:

- **Suspend account** for an active account, or **Unsuspend account** for a
  suspended account.
- **Restrict hosting** for an eligible host, or **Restore hosting** for a
  restricted host.
- **Delete account**.
- **Grant administrator access** or **Revoke administrator access**, for an
  administrator authorized to manage access.

Account-state and access-management controls are unavailable for deleted or
pending-deletion accounts; deletion-failure follow-up remains available when
there is a recorded issue.

### 3.5. Suspend Account

A preview shows the current account state and any future official games the
user is assigned to host. Those assignments remain in place after suspension.
Staff enter a required reason of up to 500 characters and confirm.

### 3.6. Unsuspend Account

Staff enter a required reason of up to 500 characters and confirm. The account
returns to active.

### 3.7. Restrict Hosting

A preview shows the number of future community games the user hosts. Staff enter
a required reason of up to 500 characters and confirm. The user can no longer
publish new community games.

### 3.8. Restore Hosting

Staff enter a required reason of up to 500 characters and confirm. Hosting
returns to eligible.

### 3.9. Delete Account

A preview lists blockers and the account's impact: future bookings, roster
spots, guests, waitlist entries, Need a Sub posts and requests, payments,
refunds, credits, saved cards, and open support flags. When nothing blocks
deletion, staff enter a required reason of up to 500 characters, type
**DELETE**, and confirm.

### 3.10. Administrator Access

The platform owner or an administrator expressly authorized to manage access
can grant or revoke administrator access from this page. The page shows the
current access state, requires confirmation before a change, and records the
completed change in [Admin Action Log](admin-action-log.md). A community
organizer who has admin access does not gain access-management authority by
default.

### 3.11. Account-Deletion Follow-Up

When deletion cleanup has a partial failure, this page shows the available
failed-operation information, when it occurred, and whether follow-up remains
open. An authorized administrator can mark the issue reviewed or resolved
after investigating it. The failure record and action history remain available
for accountability; no separate support dashboard is needed.

## 4. Important Behavior & Decisions

### 4.1. Separate Controls

Account status, hosting status, and role are independent. Unsuspending does not
restore hosting, restoring hosting does not unsuspend, and restricting hosting
does not suspend the account. Granting or revoking administrator access changes
only the account's administrative access.

### 4.2. Guarded Changes

Every account control requires recent identity confirmation and a reason.
Suspension, hosting restriction, and deletion use a preview; if the account's
situation changed after the preview, the change is rejected and must be
previewed again. Repeating the same request does not apply the change twice.
Each completed change is recorded in the
[Admin Action Log](admin-action-log.md).

### 4.3. Blockers

- The last active admin cannot be suspended or deleted.
- A user assigned as host of a future official game cannot be deleted until
  that assignment is removed from
  [Official Game Manage](official-game-manage.md).

An official host assignment does not block suspension. Blocked suspension and
deletion attempts are not applied.

### 4.4. User Notifications

Suspension, unsuspension, hosting restriction, and hosting restoration each
create an account notice. The suspension notice must be readable in the
dedicated restricted-account experience while the user is suspended, without
depending on access to [Inbox](../player/inbox.md). The access rules are in
section 4.10.

### 4.5. Hosting Restriction Scope

Restricting hosting only blocks new community game publication. It does not
cancel or change games the user already hosts. Hosting can be restricted only
from eligible and restored only from restricted.

### 4.6. Account Deletion

Deletion removes the user's sign-in identity, detaches saved cards, cancels or
cleans up the user's future bookings, roster spots, guests, waitlist entries,
hosted community games, and Need a Sub posts and requests, and removes personal
details from the account. The account ends as deleted and not eligible to host.
If cleanup fails partway, the failure is recorded as a support flag rather than
silently ignored. Its follow-up belongs on this page, as described in
sections 3.11 and 4.12.

### 4.7. Acting on Your Own Account

If an admin suspends their own account, they lose workspace access and return
to [Admin Sign In](../authentication/admin-sign-in.md). If they delete their own
account, they are signed out.

### 4.8. Deleted Accounts

A deleted account's page shows its remaining history with personal details
removed. Game activity excludes deleted games.

### 4.9. Not Shown Here

Money ledgers, saved-card details, sign-in provider identifiers, full birth
dates, and private settings are not shown. Money support belongs to
[User Money](user-money.md).

### 4.10. Suspended Player Experience

A suspended player may authenticate and reach the dedicated
`/account-suspended` **Account Suspended** experience explaining the
restrictions and showing the suspension notice.
Suspension alone does not cancel existing bookings, hosted games, or Need a Sub
posts and requests. The player may view and fulfill previously accepted
commitments, manage games already hosted and existing Need a Sub arrangements,
or withdraw from commitments. They may not create a game or post, register for
an additional game, add guests, or initiate new participation. Staff may
explicitly revoke existing participation for safety or serious misconduct
through the relevant management workflow. Related player pages apply these
rules to their own actions.

Staff may explicitly remove a suspended host from an existing game for safety
or serious misconduct:

- **Official game:** an eligible replacement takes over and registered players
  are notified. If no eligible replacement is available, the game is cancelled
  and registered players are notified. These actions belong to
  [Official Game Manage](official-game-manage.md).
- **Community game:** removing the host cancels the game, and every registered
  player receives a cancellation notice. There is no replacement host. Payment
  disputes and refunds remain between the players and the original organizer.
  This action belongs to [Community Game Detail](community-game-detail.md).

Suspension itself does not trigger either outcome, cancel a hosted game, or
cancel existing player bookings.

### 4.11. Access-Management Authorization

Only the platform owner or an administrator expressly authorized for access
management may change another account's admin access. The backend must enforce
that distinction, even when the caller is otherwise an admin. The last person
who can manage administrator access cannot lose that authority. Changes need
confirmation and an audit record. The exact representation of the owner or
access-management authority remains an implementation detail to define; no
additional role type is assumed here.

### 4.12. Deletion-Failure Accountability

A deletion failure remains visible after review or resolution, with the
available cleanup context, failure time, resolution decision, actor, and time.
Only an authorized administrator can mark a failure reviewed or resolved;
the backend enforces this. A resolution records the investigation result and
does not erase the original failure.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open an active user's detail. | Summary, account state, accountability counts, activity previews, and admin actions appear; no money ledger appears. |
| 2 | ☐ | Select a game or Need a Sub activity row. | The matching official game, community game, post, or request admin page opens. |
| 3 | ☐ | Select View all in each activity section. | The matching full activity page opens. |
| 4 | ☐ | Suspend an active account with a reason after confirming identity. | The account becomes suspended, an account notice is created for the user, and the action appears in Admin Actions. |
| 5 | ☐ | Unsuspend a suspended account. | The account becomes active; hosting status is unchanged. |
| 6 | ☐ | Restrict an eligible host who has future community games. | The preview shows the future game count; after confirming, hosting is restricted, the games remain, and the user is notified. |
| 7 | ☐ | Restore a restricted host. | Hosting becomes eligible; account status is unchanged. |
| 8 | ☐ | Delete an account with future bookings and a Need a Sub post. | The preview shows the impact; after typing DELETE and confirming, the account is deleted, its future activity is cancelled, and personal details are removed. |
| 9 | ☐ | View a deleted account. | No account controls appear and personal details are removed. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 10 | ☐ | Try to suspend or delete the last active admin. | The preview reports the blocker and the action cannot be completed. |
| 11 | ☐ | Suspend a future official game host. | The preview lists the assignments without blocking suspension; after confirmation, the account is suspended and the games, host assignments, and player bookings remain unchanged. |
| 12 | ☐ | Change the user's situation after previewing, then confirm. | The change is rejected without being applied and must be previewed again. |
| 13 | ☐ | Submit any control without a reason, or delete without typing DELETE. | Confirmation stays unavailable. |
| 14 | ☐ | Decline or fail identity confirmation. | No change is made. |
| 15 | ☐ | Submit the same change twice. | It is applied and recorded only once. |
| 16 | ☐ | View a user whose hosting is not eligible. | No hosting control is offered. |
| 17 | ☐ | Suspend your own admin account. | You are returned to Admin Sign In. |
| 18 | ☐ | Delete your own account. | You are signed out. |
| 19 | ☐ | Fail account cleanup during deletion. | A partial-failure support flag is recorded and the deletion is not reported as clean. |
| 20 | ☐ | Open a user that does not exist. | A not-found error appears. |
| 21 | ☐ | Suspend a player and inspect their restricted account experience. | The player can authenticate and reach `/account-suspended`, sees the suspension notice and restrictions there even if Inbox is unavailable, and the account's existing commitments are not automatically cancelled. |
| 22 | ☐ | Attempt a new game, Need a Sub post, game registration, guest addition, or new request while suspended. | Each new-participation action is unavailable or rejected without creating a game, post, booking, guest, or request. |
| 23 | ☐ | Open an existing booking, hosted game, or Need a Sub arrangement while suspended. | The existing commitment remains accessible for permitted fulfillment, management, or withdrawal; suspension alone changes none of its status. |
| 24 | ☐ | Explicitly revoke a suspended player's existing non-host participation for safety or serious misconduct. | Only the selected participation is changed by the authorized admin action; suspension alone has not performed that revocation. |
| 25 | ☐ | Grant or revoke administrator access as the platform owner or an expressly authorized administrator. | Confirmation is required; only the requested access changes, and the completed change appears in Admin Actions and Admin Action Log. |
| 26 | ☐ | Attempt to change admin access as a community organizer with admin access but no access-management authorization. | The control is unavailable and a bypassed request is rejected by the backend without changing access or recording a successful action. |
| 27 | ☐ | Attempt to remove the last person authorized to manage administrator access. | The change is blocked by the backend and the account retains access-management authority. |
| 28 | ☐ | Open an account with a partial deletion failure. | Available failed-cleanup details, occurrence time, and outstanding follow-up state appear on User Detail even if deletion completed in part. |
| 29 | ☐ | Mark a deletion failure reviewed or resolved after investigation. | Only an authorized administrator can do so; the failure remains in history with the decision, actor, and time, and the follow-up state updates. |
| 30 | ☐ | Try to resolve a deletion failure without authorization or after its state changes. | The backend rejects the action; no false resolution is shown and the current failure state remains available. |
| 31 | ☐ | Try to delete a future official game host. | The preview lists the assignments and deletion cannot complete until they are removed. |
| 32 | ☐ | Suspend a user who hosts a future community game, then explicitly remove them as its host from Community Game Detail. | Suspension leaves the game active with its bookings; the explicit removal cancels the game, assigns no replacement host, and sends every registered player a cancellation notice. |

## 6. Open Items to Resolve

**None**.
