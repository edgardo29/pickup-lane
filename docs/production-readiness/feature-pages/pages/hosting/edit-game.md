# F18 — Edit Game

## 1. Existing Route(s)

- `/games/:gameId/edit`

## 2. Purpose

Edit Game lets a community-game host update an already published game before it starts. It uses the form described in [Create Game](create-game.md), with additional limits once players have joined. [Game Details](../public/game-details.md) owns the entry to host editing and the ongoing roster.

## 3. Main Functionality

### 3.1. Review and Change the Existing Game

- The page loads the game, venue, and community details into the same four-step Game, Location, Notes, and Review form used for creation.
- The host can review proposed changes, move between steps, and save. A successful save returns to Game Details.
- A complete success is shown only after both the general game information and community-specific details are saved. If one save succeeds and the other fails, the page identifies what saved and what did not, keeps entered values, and offers a retry of the failed operation alone.
- Cancel or Back from the first step returns to Game Details; changed fields trigger a keep-editing or discard choice.

## 4. Important Behavior & Decisions

### 4.1. Who and What Can Be Edited

Only the owner can edit an active, published community game before its start. A changed start must remain within the 21-day local scheduling limit owned by [Create Game](create-game.md#41-host-and-schedule-eligibility). An unrelated user, missing game, official game, or inactive game cannot be changed through this page. Existing games remain manageable under the host's account even if the host is suspended or restricted from publishing new games; the new-publication rule belongs to [Create Game](create-game.md).

### 4.2. Changes After Players Join

Before any non-host player has active participation, the host can change game setup, location, price, and details subject to the creation rules. Once a non-host player has an active confirmed, waitlisted, or pending-payment place, date, time, location, format, indoor/outdoor setting, and player price are locked; capacity can only increase. A prior paid booking also blocks a price change even if the active roster later changes. The backend rechecks these limits when saving.

### 4.3. Location and Save Outcome

Changing the location reuses an existing venue record for the same facility, or creates one only if that facility does not already exist. The previous venue record is left intact; an address match alone does not identify the facility. A venue represents the facility, not an individual playing field; optional field instructions belong in the game description. Edit does not charge a new publication fee. Host payment instructions and notes may be updated as community-game details. Attendance and cancellation actions remain on [Game Details](../public/game-details.md).
The general game update and community-detail update are separate operations. The page must not report complete success after only one succeeds; a retry must not replay the successful operation.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Edit Game as the owner of an active future community game. | Existing values load into the four-step form, including venue and community details. |
| 2 | ☐ | Save permitted setup, notes, rules, or host payment changes before players join. | The saved details appear on Game Details; no new game or publish fee is created. |
| 3 | ☐ | Change a game's location before players join to an existing facility, then to a distinct facility at a shared address. | The first change reuses the existing venue record; the second creates a new record. Neither changes the old venue's identity or other games using it. |
| 4 | ☐ | Increase capacity or edit allowed notes after a player joins or waitlists. | The permitted changes save while the existing roster remains intact. |
| 5 | ☐ | Cancel with and without unsaved changes. | Unsaved edits prompt keep editing or discard; leaving returns to that game's details without saving. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Open as a signed-out visitor, non-owner, or with a missing or non-community game. | Sign-in or access checks prevent editing; no unauthorized game changes occur. |
| 7 | ☐ | Try to edit a cancelled, inactive, unpublished, or already-started game. | The change is rejected and the existing game remains unchanged. |
| 8 | ☐ | Change date, time, location, format, environment, or price after a non-host player is confirmed, waitlisted, or pending payment. | Save is rejected for the protected fields even if the form was opened before that player became active. |
| 9 | ☐ | Reduce capacity after active non-host participation, or change price after a paid booking exists. | Save is rejected and prior capacity or price remains in effect. |
| 10 | ☐ | Submit invalid schedule, capacity, location, or paid-game payment details. | Validation identifies the affected step; invalid values are not saved. |
| 11 | ☐ | Fail to load the editable game or fail a save request. | The page shows an error and does not claim that the entire edit was saved. |
| 12 | ☐ | Edit a community game to start exactly 21 days ahead, then try 22 days ahead. | The 21-day schedule can save if all other edit rules allow it; the 22-day schedule is rejected without changing the game. |
| 13 | ☐ | Edit an existing hosted game while the owner is suspended. | Permitted management and changes to the existing game remain available; the owner still cannot publish a new game. |
| 14 | ☐ | Save game fields successfully but fail the community-detail update. | The page identifies the saved and failed parts, retains entered community details, and retries only that failed update; it reports complete success only after both parts succeed. |
| 15 | ☐ | Fail the general game update before community details save. | The page retains entered values, identifies the unsaved part, and does not present complete success or replay an already successful operation. |

## 6. Open Items to Resolve

**None**.
