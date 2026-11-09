# F31 — Edit Official Game

## 1. Existing Route(s)

- `/admin/official-games/:gameId/edit`

## 2. Purpose

Edit Official Game lets staff change the schedule, location, game setup, price,
booking settings, and player notes of an active official game before it starts,
including after players have paid. Host and roster are managed elsewhere.

## 3. Main Functionality

### 3.1. Game

Staff can change the date, start and end time, format, player group, skill level,
indoor or outdoor setting, total spots, and price per player.

### 3.2. Location and Details

Staff can change the venue and location details for an active game. They can
also change guest access and maximum guests per booking (0, 1, or 2),
waitlist, game chat, player instructions (up to 220 characters), and parking note
(up to 160 characters), and add an optional internal reason (up to 500
characters).

### 3.3. Review & Save

A review shows the updated game, including any changed venue and address. **Save changes** saves and returns to
[Official Game Manage](official-game-manage.md). Leaving without saving also
returns to Official Game Manage.

## 4. Important Behavior & Decisions

### 4.1. Editable Games

Only active, published official games can be edited. Validation for the schedule,
capacity, and price matches [Create Official Game](create-official-game.md),
including the 30-day local scheduling limit.

### 4.2. What Cannot Change

The host, roster, game type, payment type, and policy cannot be changed here.
Venue and address may be corrected on an active game; replacement mode remains
available after cancellation. The game title follows the venue name and format.

### 4.3. Capacity Floor

Total spots cannot be reduced below the number of players currently on the
roster.

### 4.4. Checkout-Sensitive Changes

Changing the schedule, location, timezone, format, player group, skill level, environment,
total spots, price, guest settings, or waitlist setting cancels checkouts that are still in
progress and returns any credit reserved for them, so no player completes payment
under outdated terms.

### 4.5. Audit

Each save is recorded in the [Admin Action Log](admin-action-log.md) with the
changed fields and the optional reason.

### 4.6. Changes After Paid Bookings

Staff may change schedule, location, format, player group, skill level,
environment, and price while confirmed paid bookings exist. Existing bookings
stay confirmed unless their players withdraw; mandatory reconfirmation is not
required. A price increase does not raise the amount already paid by existing
bookings. A promotional or availability-driven price decrease does not
automatically refund or credit existing players for the difference. Capacity
protections and the checkout treatment in section 4.4 still apply.

### 4.7. Player Notice and Withdrawal

Affected players receive both in-app and email notice explaining what changed
and that they may keep their confirmed booking or request to leave. No player
must reconfirm, and an edit alone never removes a player or issues a refund or
credit. A player for whom the changed details no longer work may request
removal and choose a refund to the original payment method or game credit,
including after the usual cancellation cutoff. The refund or credit is provided
when the removal and corresponding request are processed, not on edit or
request submission. No significant-change threshold or fixed list of
qualifying fields applies. The player-facing rule is summarized in
[Cancellation & Refunds Policy](../public/cancellation-refunds-policy.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Edit for an active future game. | The form loads with the current values. |
| 2 | ☐ | Change the price and save. | The new price appears on Official Game Manage and the change is audited. |
| 3 | ☐ | Change the start time while a player is in checkout. | The checkout is cancelled, reserved credit is returned, and the new time is saved. |
| 4 | ☐ | Change only player instructions. | The instructions update and no checkout is cancelled. |
| 5 | ☐ | Save with an internal reason. | The audit entry shows the reason. |
| 6 | ☐ | Leave without saving. | Official Game Manage opens with no changes. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Reduce total spots below the roster count. | Saving is rejected and the game is unchanged. |
| 8 | ☐ | Enter a past start or an end before the start. | The step reports the schedule problem and does not advance. |
| 9 | ☐ | Edit a game that has started, or is cancelled or completed. | Saving is rejected. |
| 10 | ☐ | Enter text beyond a field limit. | Input stops at the limit or the step reports the limit. |
| 11 | ☐ | Fail to load the game. | An error appears and no form is shown. |
| 12 | ☐ | Fail to save. | An error appears, the form keeps the entered values, and the game is unchanged. |
| 13 | ☐ | Change official-game details after paid bookings exist. | Permitted changes save; existing bookings stay confirmed, and affected players receive in-app and email notice explaining the changes and the choice to keep the booking or request removal. No reconfirmation, automatic removal, refund, or credit occurs. |
| 14 | ☐ | Raise the price after paid bookings, then make a new booking. | Earlier paid bookings retain their original price; the new price applies to later bookings without charging earlier players more. |
| 15 | ☐ | Lower the price for a promotion or to fill spots. | Existing players receive no automatic refund or credit for the difference; the new price applies to later bookings. |
| 16 | ☐ | Request removal because changed official-game details no longer work, including after the usual cutoff. | The player can choose an original-method refund or game credit; the confirmed booking remains until removal and the corresponding request are processed, when the selected relief is provided. |
| 17 | ☐ | Try to reduce capacity below the roster or edit while checkouts are in progress. | The capacity floor still blocks the reduction; checkout-sensitive edits cancel pending checkouts and return reserved credit. |
| 18 | ☐ | Save an official-game edit without any affected player requesting removal. | Existing bookings remain confirmed at their original paid prices, and the edit alone creates no refund, credit, or player-removal action. |
| 19 | ☐ | Change the venue and address of an active game that has confirmed paid bookings. | The review shows the changed venue and address; saving updates the game's location and title, cancels checkouts still in progress, keeps existing bookings confirmed, and sends affected players the change notice. |
| 20 | ☐ | Edit an official game to start exactly 30 days ahead, then try 31 days ahead. | The 30-day schedule saves when otherwise valid; the 31-day schedule is rejected without changing the game, independent of Browse Games' 14-day display window. |

## 6. Open Items to Resolve

**None**.
