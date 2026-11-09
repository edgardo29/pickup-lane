# F30 — Official Game Manage

## 1. Existing Route(s)

- `/admin/official-games/:gameId`

## 2. Purpose

Official Game Manage is the staff control center for one official game. Staff
review the game, manage its host and roster, inspect bookings, waitlist, money,
chat, photos, and admin activity, and cancel the game when needed, without
bypassing booking, payment, credit, notification, or audit rules.

## 3. Main Functionality

### 3.1. Summary and Header

The summary shows the title, date, time, duration, environment, format, player
group, skill level, price, roster count, and venue. The header offers **Back**,
**Edit game** (opens [Edit Official Game](edit-official-game.md), which owns
  the rules for edits after paid bookings), and
**Cancel game**.

### 3.2. Overview

Shows status, host, address, neighborhood, roster count, players, and guests.

### 3.3. Roster and Host

- **Host:** assign a host from confirmed players on the roster, with
  confirmation, or remove the current host designation with a required reason of
  up to 1,000 characters.
- **Roster:** **Active** and **History** views. Staff can search users by name or
  email and add one as a player; search results explain when a user cannot be
  added (already on roster, current host, game full, game started, game cannot
  add players, or inactive user).
- **Remove a player:** opens a removal preview showing the affected booking and
  party, cash and credit impact, existing refunds, and the removal outcome.
  When an automatic outcome is available, staff enter a required reason of up to
  1,000 characters and confirm.
- **Changed-game removal requests:** staff can review a player's request to
  leave after official-game details change, including the player's chosen
  original-method refund or game credit, and process the corresponding removal
  and relief. The request alone does not remove the player or move money.

### 3.4. Bookings, Waitlist, and Money

- **Bookings:** each booking with its booking, payment, party, and timeline
  details.
- **Waitlist:** each entry with player, position, party, auto-charge and
  authorization state, and timeline.
- **Money:** the game's payments, refunds, credits, and credit usage, with links
  to [Payment Detail](payment-detail.md) and other money pages.

### 3.5. Chat, Photos, and Activity

- **Chat:** the chat summary and the chat moderation described in
  [Community Game Detail](community-game-detail.md#34-chat).
- **Photos:** the venue's primary and gallery photos.
- **Activity:** admin actions on this game with target, admin, and time.

### 3.6. Cancel Game

A cancellation preview shows the bookings, roster rows, and waitlist entries
affected; cash refunds, credit restorations, and credit releases; and the result
for each booking. Staff enter a required reason of up to 500 characters and
confirm. After cancelling, **Create replacement** opens
[Create Official Game](create-official-game.md) in replacement mode.

## 4. Important Behavior & Decisions

### 4.1. Host Designation

A host can be assigned or removed only before the game starts. The new host must
be an active user already confirmed on the roster as a player. Removing the host
designation keeps the person on the roster. The current host must lose the host
designation before being removed as a player. Old and new hosts are notified of
changes made by someone else.

Suspension alone leaves an existing host assignment and player bookings intact.
If an administrator explicitly removes a suspended host for safety or serious
misconduct, the game is reassigned to an eligible replacement and registered
players are notified. If no eligible replacement is available, the game is
cancelled and registered players are notified. Cancellation and any refund or
credit outcome follow section 4.4 and the
[Cancellation & Refunds Policy](../public/cancellation-refunds-policy.md).

### 4.2. Adding Players

Staff can add an active user to an active official game that has not started and
is not full. The player is confirmed without payment, capacity updates, and the
player is notified.

### 4.3. Removing Players

Every removal starts with a preview that does not change anything. Removal
requires recent identity confirmation. Depending on how the booking was paid, the
outcome is remove only, release the checkout hold, refund cash, restore credit,
or refund cash and restore credit. Cases that cannot be handled automatically,
such as active refunds or paid guests needing manual allocation, cannot be
executed from the preview. If the game changed after the preview, the removal
is rejected before any money moves. Credits are handled before cash refunds. A
failed refund or credit return creates a [Money Issue](money-issues.md) instead
of marking the booking refunded or the credit returned. Opening a spot can promote the waitlist. The removed player, or the
booking owner for a guest, is notified.

For a player's request to leave because changed official-game details no
longer work, staff process the requested removal and the player's chosen
original-method refund or game credit through an authorized workflow. The
booking stays confirmed until processing, and the edit or request alone never
issues money. This change-related path does not replace the ordinary
cancellation, facility-issue, or payment-error rules.

### 4.4. Cancellation

Only active games that have not started can be cancelled, and cancellation
requires recent identity confirmation. Cancelling cancels the roster, waitlist,
and bookings, refunds or restores money according to the preview, archives the
game chat, and notifies affected players. If credits cannot be restored or
released, cancellation stops, the game stays active, and a Money Issue is
created. A refund that fails during cancellation creates a Money Issue for that
refund. Each unresolved refund or credit gets its own issue, as described in
[Money Issues](money-issues.md).
Players' refund and credit terms follow the
[Cancellation & Refunds Policy](../public/cancellation-refunds-policy.md).

### 4.5. Recorded Viewing

Opening the Bookings, Waitlist, and Money tabs, and opening a removal or
cancellation preview, are recorded as sensitive admin views. Chat viewing follows
Community Game Detail. See [Admin Action Log](admin-action-log.md).

### 4.6. History Stays Available

Cancelled, completed, expired, and removed games remain viewable here for
history.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open an active official game. | The summary, Overview, and all tabs load for the game. |
| 2 | ☐ | Add an active user as a player. | The player is confirmed without payment, the roster count increases, and the player is notified. |
| 3 | ☐ | Assign a confirmed roster player as host, then replace them. | The host changes, and the old and new hosts are notified. |
| 4 | ☐ | Remove the host designation with a reason. | The game has no host and the person stays on the roster. |
| 5 | ☐ | Preview and remove a player who paid by card, after confirming identity. | The preview shows the cash refund; after confirming, the refund is created, the player is removed and notified, and the spot opens. |
| 6 | ☐ | Remove a player who paid with credit. | Credit is restored without a cash refund. |
| 7 | ☐ | Remove a player during a checkout hold. | The hold is released and any reserved credit is returned. |
| 8 | ☐ | Remove a player from a full game with a waitlist. | The opened spot can promote the waitlist. |
| 9 | ☐ | Preview and confirm cancellation with a reason. | Bookings, roster, and waitlist are cancelled, refunds and credits follow the preview, chat is archived, players are notified, and Create replacement appears. |
| 10 | ☐ | Open the Money tab and select a payment. | Payment Detail opens for that payment. |
| 11 | ☐ | Open the Activity tab after changes. | The host, roster, and cancellation actions appear. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 12 | ☐ | Search for a user who is already on the roster, inactive, or the host, or search on a full or started game. | The result explains why the user cannot be added and adding is blocked. |
| 13 | ☐ | Assign a host who is not a confirmed roster player. | Assignment is rejected. |
| 14 | ☐ | Try to remove the current host as a player. | Removal is unavailable until the host designation is removed. |
| 15 | ☐ | Preview removal for a booking with an active refund or a paid guest needing allocation. | The preview shows that it cannot proceed automatically and offers no confirmation. |
| 16 | ☐ | Change the booking after previewing a removal, then confirm. | The removal is rejected before any refund or credit change. |
| 17 | ☐ | Fail a refund during removal or cancellation. | A Money Issue is created for the refund and the booking is not shown as fully refunded. |
| 18 | ☐ | Fail a credit restoration during cancellation. | Cancellation stops, the game stays active, and a credit Money Issue is created. |
| 19 | ☐ | Open a game that has started or is cancelled. | Cancel game is disabled with the reason, and host changes and player additions are rejected. |
| 20 | ☐ | Enter a cancellation reason over 500 characters. | Input stops at 500 characters. |
| 21 | ☐ | Decline identity confirmation for removal or cancellation. | Nothing changes. |
| 22 | ☐ | Open a tab when its admin view cannot be recorded. | That tab's data is not shown and an error appears. |
| 23 | ☐ | Open a community game ID or a missing game on this page. | A not-found error appears. |
| 24 | ☐ | Return from a permitted official-game location or price edit after paid bookings. | The summary reflects the new game details, while existing bookings and their original paid amounts remain available for review. |
| 25 | ☐ | Review a player's request to leave after changed official-game details no longer work. | Staff can see the confirmed booking and the player's original-method refund or game-credit choice; the request alone has not removed the player or moved money. |
| 26 | ☐ | Process the player's change-related removal and chosen relief, including after the usual cancellation cutoff. | The booking is removed through the authorized workflow and the selected refund or credit is provided when the corresponding request and removal are processed; the action is recorded without double payment or credit. |
| 27 | ☐ | Explicitly remove a suspended official-game host for safety or serious misconduct when an eligible replacement is available. | The eligible confirmed roster player becomes host, the game and existing bookings remain active, and registered players are notified of the host change. |
| 28 | ☐ | Explicitly remove a suspended official-game host when no eligible replacement is available. | The game is cancelled, registered players are notified, and eligible paid value is refunded or restored as credit under the cancellation policy. |

## 6. Open Items to Resolve

**None**.
