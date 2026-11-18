# F18 — Edit Game Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/hosting/edit-game.md`  
**Endpoints:** `GET /games/{game_id}`, `GET /venues/{venue_id}`, `GET /community-game-details/games/{game_id}/host-edit`, `PATCH /games/{game_id}/host-edit`, `PUT /community-game-details/games/{game_id}/host-edit`

## 1. Page requirements

| Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|
| 3.1 | Load the game, venue, and community details into the four-step form | Yes | — |
| 3.1 | Review, move between steps, and save; success returns to Game Details | Yes | — |
| 3.1 | Complete success only after both saves; a partial save names what saved, keeps the values, and retries only the failed part | Yes | — |
| 3.1 | Cancel or Back from the first step returns to Game Details; changed fields ask to keep editing or discard | Yes | — |
| 4.1 | Only the owner edits an active, published community game before it starts; others, missing, official, or inactive games cannot be changed | Yes | — |
| 4.1 | A changed start stays within the 21-day local scheduling limit | Yes | — |
| 4.1 | A suspended host can still edit games they already host | Yes | — |
| 4.2 | Before non-host players join, setup, location, price, and details can change under the creation rules | Yes | — |
| 4.2 | After a non-host player is confirmed, waitlisted, or pending payment, date, time, location, format, environment, and price lock and capacity can only increase; the backend rechecks on save | Yes | — |
| 4.2 | A prior paid booking blocks a price change | Yes | — |
| 4.3 | A location change reuses the existing facility's venue record or creates one; the old venue stays intact; an address alone is not a facility | Yes | — |
| 4.3 | No new publish fee; payment methods and notes save as community details | Yes | — |
| 4.3 | The game update and community-detail update are separate; no complete success after one; a retry does not replay the successful one | Yes | — |

## 2. Test scenarios

### 2.1 Backend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| 1 | Owner loads the community details for editing | Yes | Pass |
| 2 | Permitted setup, notes, rules, or payment changes save without a new game or fee | Yes | Pass |
| 3 | Location change reuses an existing facility, then creates a distinct facility at a shared address | Yes | Pass |
| 4 | Capacity increase and note edits after a player joins or waitlists | Yes | Pass |
| 6 | Signed out, non-owner, missing, or non-community game | Yes | Pass |
| 7 | Cancelled, inactive, unpublished, or already-started game | Yes | Pass |
| 8 | Protected fields rejected after a non-host player is active | Yes | Pass |
| 9 | Capacity decrease after players join, or price change after a paid booking | Yes | Pass |
| 10 | Invalid schedule, capacity, location, or paid-game payment details | Yes | Pass |
| 12 | Start exactly 21 days ahead saves; 22 days ahead is rejected | Yes | Pass |
| 13 | Suspended owner edits an existing hosted game | Yes | Pass |

### 2.2 Frontend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| 1 | Existing values load into the four-step form | Yes | Pass |
| 2 | A permitted save returns to Game Details | Yes | Pass |
| 5 | Cancel with and without unsaved changes | Yes | Pass |
| 6 | Non-owner or non-community game cannot be edited | Yes | Pass |
| 10 | Invalid values point to the affected step | Yes | Pass |
| 11 | Load failure or failed save shows an error without claiming success | Yes | Pass |
| 13 | Suspended owner can edit an existing hosted game | Yes | Pass |
| 14 | Game saves but community details fail: saved and failed parts shown, retry only the failed part | Yes | Pass |
| 15 | Game update fails: values kept, nothing claimed as saved, nothing replayed | Yes | Pass |

## 3. Work to do

None. All work is done.
