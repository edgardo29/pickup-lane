# F29 — Create Official Game

## 1. Existing Route(s)

- `/admin/official-games/new`

`/admin/official-games/new?replace_game_id=:gameId` opens the same page in
replacement mode after an official game is cancelled.

## 2. Purpose

Create Official Game lets staff publish a game that Pickup Lane runs. Official
games use in-app payment and the official cancellation and refund policy. The
page creates the listing, associates it with a venue, and handles optional
reusable venue photos; hosts,
rosters, and later changes are handled from
[Official Game Manage](official-game-manage.md).

## 3. Main Functionality

### 3.1. Game

Staff choose the date, start time, end time, format, player group, skill level,
indoor or outdoor setting, total spots, and price per player.

### 3.2. Location

Staff enter the venue name, street address, city, state, ZIP code, and optional
neighborhood and parking note. They can add up to three venue photos in JPG,
PNG, or WebP format, each under 8 MB, and remove them before publishing. The
first photo becomes the primary photo.

### 3.3. Details

Staff choose whether guests are allowed and the maximum guests per booking
(0, 1, or 2), and whether the waitlist and game chat are enabled.

### 3.4. Review & Create

A preview shows the listing as it will appear. Creating publishes the game and
returns to [Official Games](official-games.md).

### 3.5. Replacement Mode

When opened from a cancelled game, the page loads that game and fills in
everything except the location. Venue, address, parking note, and photos start
empty so staff enter the corrected location. The new game records which game it
replaces.

## 4. Important Behavior & Decisions

### 4.1. Official Game Rules

A new official game is published and active immediately, uses in-app payment and
the official policy, is priced in US dollars, and starts with no host and no
players. Staff cannot set the host, roster, game type, payment type, or policy
from this page. The game title is generated from the venue name and format.

### 4.2. Schedule and Capacity

The start must be in the future, no more than 30 days ahead in the game's
local calendar, and the end after the start. This creation and editing limit
is separate from Browse Games' 14-day display window. Times use the game's
timezone, not the staff member's device timezone. Total spots must be at least
the number of players the format needs (and at least 6) and at most 99. Price
cannot be negative.

### 4.3. Venues

A venue represents the facility or sports complex, not an individual playing
field. Reuse the existing venue record for the same facility; create a new
record only when that facility does not already exist. Street address alone
does not establish a match. Scheduling an official game does not itself change
an existing venue's approval status. Staff arrange and confirm the playing
space; optional field instructions belong in the game's description. Photos
belong to the venue and can be reused by other games at that facility.

### 4.4. Photo Upload Failures

Photo upload readiness is checked before the game is created; if uploads are
unavailable, no game is created. If the game is created but a photo upload fails,
the page shows that the game exists and offers to open it, rather than reporting
the whole creation as failed.

### 4.5. Location Changes and Replacements

An active official game's location may be changed through
[Edit Official Game](edit-official-game.md), including after paid bookings.
Replacement mode remains available when a game has been cancelled.

### 4.6. Audit

Each creation is recorded in the [Admin Action Log](admin-action-log.md),
including the replaced game for replacements.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Complete all steps with valid data and no photos. | The game is created as a published, active official game with no host or players, and Official Games opens. |
| 2 | ☐ | Create a game with three valid photos. | The game is created and its venue shows the photos, with the first as primary. |
| 3 | ☐ | Create a game at a facility with an existing venue record, including one with a different approval status. | The existing facility record is reused without changing its approval status or creating a duplicate. |
| 4 | ☐ | Open replacement mode from a cancelled game. | Non-location details are prefilled; venue, address, parking note, and photos are empty. |
| 5 | ☐ | Create the replacement. | The new game is created and its audit entry records the replaced game. |
| 6 | ☐ | Review the preview before creating. | It reflects the entered schedule, location, price, and settings. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Continue with required fields missing. | The step names the missing fields and does not advance. |
| 8 | ☐ | Enter a past start, or an end before the start. | The step reports the schedule problem and does not advance. |
| 9 | ☐ | Enter fewer total spots than the format needs, or a negative price. | The step reports the problem and does not advance. |
| 10 | ☐ | Add a fourth photo, an unsupported file type, or a file over 8 MB. | The file is rejected with the photo rules message. |
| 11 | ☐ | Create with photos while photo uploads are unavailable. | No game is created and an error appears. |
| 12 | ☐ | Fail a photo upload after the game is created. | The page shows the created game with a link to open it and reports the photo failure. |
| 13 | ☐ | Open replacement mode with a game that cannot be loaded. | A retryable error appears and the page does not fall back to a normal create. |
| 14 | ☐ | Enter a time that does not exist in the game's timezone because of a daylight-saving change. | The time is rejected before submission. |
| 15 | ☐ | Try to send host, roster, or payment settings with the creation. | The backend rejects them. |
| 16 | ☐ | Create an official game exactly 30 days ahead, then try 31 days ahead. | The 30-day schedule is eligible when otherwise valid; the 31-day schedule is rejected, independent of Browse Games' 14-day display window. |
| 17 | ☐ | Create a game at a facility not yet recorded, or enter a different facility at an address already in use. | A new venue record is created for the distinct facility; an address match alone does not cause reuse. |

## 6. Open Items to Resolve

**None**.
