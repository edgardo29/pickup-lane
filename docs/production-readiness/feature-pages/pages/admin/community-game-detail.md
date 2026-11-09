# F33 — Community Game Detail

## 1. Existing Route(s)

- `/admin/community-games/:gameId`

## 2. Purpose

Community Game Detail lets staff investigate one user-hosted community game and
apply moderation when needed. Staff can review the listing, host, roster,
host payment information, publish fee, review flags, chat, and admin history,
then hide, pause, restore, or cancel the game. Community games stay
host-run; this page does not turn them into Pickup Lane-managed games.

## 3. Main Functionality

### 3.1. Overview

The **Overview** tab shows the game status, host and host eligibility, address,
neighborhood, registered players, guests, waitlisted players, host payment
methods, and the host publish fee when one exists.

### 3.2. Enforcement

The **Enforcement** tab shows the current state: public visibility, joining,
game status, payment information state, review status, publish fee, and, when
hidden, the hidden date and reason. It offers the actions that apply to the
current state:

- **Hide game** or **Restore game:** remove the game from, or return it to,
  player-facing views.
- **Pause joining** or **Resume joining:** stop or allow new joins and guest
  changes. A paused game leaves Browse but can still be opened from its link,
  where it shows **Joining Temporarily Paused**.
- **Hide payment info** or **Restore payment info:** hide or show the host's
  payment instructions on player-facing pages.
- **Flag for review:** create an internal review flag.
- **Remove suspended host:** when the host's account is suspended, explicitly
  remove the host for safety or serious misconduct. Removing the host cancels
  the game, as described in section 4.3; no replacement host is assigned.
- **Cancel game:** cancel the game permanently.

Each action requires a reason of up to 100 characters.

The tab also lists **Review Flags** with their status and resolution. An open
flag can be resolved as **Handled externally**, **No action needed**,
**Duplicate flag**, or **Invalid flag**, with a reason.

### 3.3. Publish-Fee Outcome on Cancellation

Cancelling also records what happens to the host's publish fee:

- If a fee was paid: **Manual review** (default), **Refund publish fee**,
  **Credit future publish**, or **Forfeit fee**.
- If no fee was paid: **No fee charged** (default) or **Manual review**.

The outcome is recorded after the cancellation and appears in
[Financial Outcome Detail](financial-outcome-detail.md).

### 3.4. Chat

The **Chat** tab lets staff moderate the game chat:

- Filter messages by **All messages**, **Needs review**, or **Removed**, 20 at a
  time, with previous and next pages.
- Each message shows its sender, a short excerpt, and any flags.
- Opening a message shows its full text, visibility, review status, and flags.
- **Mark reviewed** clears a message that needs review.
- **Remove** hides a message from the chat, with a required reason.
- **Restore** returns a message that an admin removed, with a required reason.

[Need a Sub Post (Admin)](need-a-sub-post-detail.md) and
[Official Game Manage](official-game-manage.md) use this same chat moderation.

### 3.5. Audit

The **Audit** tab lists admin actions on this game with the action, reason,
admin, and date, a page at a time.

## 4. Important Behavior & Decisions

### 4.1. Reversible and Terminal Actions

Hiding the game, pausing joining, and hiding payment information can be undone.
Cancellation cannot. Hide and restore are unavailable for cancelled or removed
games. Pause and resume are available only for active games. Cancellation is
available only for an active, published game before it starts.

### 4.2. Public Effect

The backend enforces each change; it is not only hidden in the interface.
A hidden game is unavailable to unrelated visitors as described in
[Game Details](../public/game-details.md). Paused joining blocks joins and guest
changes and removes the game from [Browse Games](../public/browse-games.md) until
joining resumes. The game stays publicly visible, so its Game Details link still
opens with the paused status and no Join or Add Guest actions; existing players
can still view their bookings and leave. Resuming restores eligible joining
actions. Hidden payment
instructions do not appear to players.

### 4.3. Host and Player Notices

The host receives a notice when the game is hidden, restored, paused, resumed,
cancelled, or has its payment information hidden or restored. Cancellation also notifies
participants through the normal game cancellation process. Review flags and
review cases do not notify anyone.

Suspension alone does not cancel or change the community game, its host, or
its player bookings. Removing a suspended host is an explicit staff action for
safety or serious misconduct, and it cancels the game; there is no
replacement-host workflow. Every registered player receives a cancellation
notice through the normal game cancellation process. The suspended-account
rules are owned by [User Detail](user-detail.md#410-suspended-player-experience).

### 4.4. Cancellation and Money

Cancellation requires recent identity confirmation. Players' payments for
community games are arranged with the host off the app, so cancellation does
not refund or credit players. The publish-fee outcome is a separate admin
decision; **Manual review** leaves money follow-up pending so urgent enforcement
is not blocked. If the cancellation succeeds but the outcome cannot be recorded,
the game stays cancelled and the page reports that the outcome failed.

A game cancelled by removing its suspended host follows the same rules. Any
payment dispute or refund remains between the players and the original
organizer; Pickup Lane does not process or guarantee it. Cancellation notices
for community games state this responsibility. See the
[Cancellation & Refunds Policy](../public/cancellation-refunds-policy.md).

### 4.5. Review Case Links

Hiding, pausing, cancelling, or hiding payment information on a game with an
open content-moderation case links the action to that case, as described in
[Review Case Detail](review-case-detail.md). Cancelling closes that case
automatically.

### 4.6. Review Flags

A game can have only one open review flag. Creating or resolving a flag does not
change the game.

### 4.7. Chat Moderation Rules

- Only messages that need review can be marked reviewed.
- Removing a message marks it reviewed and removes it for chat participants;
  unread chat counts are recalculated without it.
- Only messages removed by an admin can be restored.

### 4.8. Recorded Viewing

Opening this page, viewing chat messages, and opening a message's full text are
recorded as sensitive admin views. See [Admin Action Log](admin-action-log.md).

### 4.9. Repeated or Stale Actions

Repeating the same action does not apply it twice. If the game changed after the
page loaded, an action can be rejected; the page reloads the current state.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open an active community game. | The Overview shows host, roster counts, payment methods, and publish fee when present. |
| 2 | ☐ | Hide the game with a reason. | It disappears from player-facing views, the host is notified, and Restore game becomes available. |
| 3 | ☐ | Restore a hidden game. | It returns to player-facing views and the host is notified. |
| 4 | ☐ | Pause joining, then resume it. | While paused, the game is absent from Browse but its direct Game Details link shows Joining Temporarily Paused without Join or Add Guest; existing players can view bookings and leave, and bypassed new participation is rejected. After resume, it returns to Browse and eligible joining actions return. The host is notified each time. |
| 5 | ☐ | Hide and restore payment information. | Players stop seeing, then see again, the host's payment instructions. |
| 6 | ☐ | Cancel a game whose host paid the publish fee, choosing Refund publish fee, after confirming identity. | The game is cancelled, host and participants are notified, and a refund outcome is recorded. |
| 7 | ☐ | Cancel a game with no publish fee. | The default No fee charged outcome is recorded with the cancellation. |
| 8 | ☐ | Flag the game for review, then resolve the flag. | The flag appears as open, then as resolved with its outcome; the game itself is unchanged. |
| 9 | ☐ | Hide a game that has an open content-moderation case. | The case timeline shows the linked action. |
| 10 | ☐ | Filter chat by Needs review, open a message, and mark it reviewed. | The full text appears, and the message no longer needs review. |
| 11 | ☐ | Remove a chat message with a reason, then restore it. | Participants stop seeing it, then see it again. |
| 12 | ☐ | Open the Audit tab. | Recent admin actions on the game appear with action, reason, admin, and date. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 13 | ☐ | Submit any action without a reason, or with more than 100 characters. | The action cannot be submitted. |
| 14 | ☐ | Open a game that has started, or is cancelled or removed. | Cancel game is not offered; hide and restore are unavailable for cancelled or removed games. |
| 15 | ☐ | Decline identity confirmation when cancelling. | The game is not cancelled. |
| 16 | ☐ | Cancel successfully but fail to record the publish-fee outcome. | The game stays cancelled and the page reports that the outcome failed. |
| 17 | ☐ | Flag a game that already has an open flag. | Flag for review is not offered and a duplicate flag is rejected. |
| 18 | ☐ | Hide payment information that is already hidden, or when the host has none. | Hide payment info is not offered. |
| 19 | ☐ | Open a removed message that was not removed by an admin, such as one its sender deleted. | Restore is not offered for that message. |
| 20 | ☐ | Act after another admin changed the game. | The action is rejected or reconciled and the page shows the current state. |
| 21 | ☐ | Submit the same action twice. | It is applied and audited once. |
| 22 | ☐ | Open an official game ID on this page. | A not-found error appears. |
| 23 | ☐ | Open the page when the admin view cannot be recorded. | Game details are not shown and an error appears. |
| 24 | ☐ | Explicitly remove a suspended community-game host for safety or serious misconduct, with a reason. | The game is cancelled, no replacement host is offered or assigned, and the action is recorded in the Audit tab. |
| 25 | ☐ | Check registered players after removing a suspended host. | Every registered player receives a cancellation notice stating that payment disputes and refunds remain between the players and the original organizer; Pickup Lane issues no refund or credit. |
| 26 | ☐ | Suspend a community-game host without removing them. | The game's host, status, and player bookings are unchanged, and no cancellation notice is sent. |

## 6. Open Items to Resolve

**None**.
