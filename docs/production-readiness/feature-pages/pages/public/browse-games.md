# F15 — Browse Games

## 1. Existing Route(s)

- `/games/browse`

`/games` redirects to this page.

## 2. Purpose

Browse Games is Pickup Lane's public discovery page. Anyone, signed in or not,
can see the upcoming official Pickup Lane games and community games for a
selected day and pick one to view its details.

Browse is for discovery only. It does not reserve spots, send notifications,
or show games that are not publicly listed. Joining, checkout, waitlists, and
rosters belong to Game Details.

## 3. Main Functionality

### 3.1. Choose a Date

- Users can browse 14 dates: today and the next 13 days.
- The date strip shows seven dates at a time: today through six days later,
  then the following seven days.
- The previous and next arrows switch between the two sets of dates. They do not
  change the selected date.
- On opening or selecting a date, the strip shows the set containing it.
- The page opens on today unless a date is chosen.
- The selected date is part of the page link, so a link to a specific day can
  be shared or bookmarked.

### 3.2. View the Day's Games

- The selected day's games are grouped by start hour, earliest first. Each hour
  shows the total number of games starting in that hour.
- Official and community games appear together in one list, ordered by start
  time.
- The day's games load in batches. A **Load More** control shows the rest of
  the day's games.

### 3.3. Game Cards

Each card shows:

- Game type: **Official** or **Community**.
- A **Full** badge when every spot is taken.
- A game or venue image, or a default image when none exists.
- Title: the venue name for official games, or the host's game title for
  community games.
- City and state.
- Start and end time.
- Player group, format, and indoor or outdoor setting.
- Spots filled out of total spots.
- Price per player, or **Free**.

### 3.4. Select a Game

Selecting a card opens that game's Game Details page.

## 4. Important Behavior & Decisions

### 4.1. Which Games Appear

A game appears only when it is published, active, publicly visible, open for
joining, not deleted, and scheduled on the selected date. Hidden, paused,
draft, cancelled, completed, and removed games never appear.

### 4.2. Registration Cutoff

- A game stays listed until registration closes, 5 minutes after its start time.
- After that the game is removed from Browse. Cards never show a "closed" state.

### 4.3. Full and Waitlist Games

- Full games stay listed before the registration cutoff, whether or not their
  waitlist accepts players. Browse does not show a separate waitlist badge.

### 4.4. Spot Counts

- Filled spots include confirmed players and their guests.
- Players who are in the middle of checkout also count, but only while their
  temporary hold is still valid. An expired hold stops counting immediately.
- Waitlisted players do not count toward filled spots.

### 4.5. Dates and Timezone

- "Today" and the 14-day date window use the Pickup Lane market timezone,
  America/Chicago at launch. A game appears under its start date in that
  game's local timezone, even when that differs from the market date. Card
  times and hour groups use the Browse market timezone; the viewer's device
  timezone does not change them.
- The 14-day window moves forward when the day changes in the market timezone.
- The window controls what Browse displays. It does not limit how far ahead
  games can be scheduled. A game scheduled further ahead appears once its date
  enters the window.

### 4.6. Date Links

- A link with a missing or invalid date selects today and displays today's games,
  whether opened directly or introduced while Browse is already open.
- A date before today opens today. A date after the last available day opens the
  last available day.
- These corrections replace the link in the browser history, so Back does not
  return to the invalid link.

### 4.7. Ordering

Games with the same start time are listed in the order they were created.

### 4.8. Keeping the List Current

- While the page is open and visible, it refreshes about once a minute and
  whenever the user returns to it.
- The current list stays visible during a refresh.
- A successful refresh returns the list to its first batch, so games loaded
  through **Load More** must be loaded again.
- A failed background refresh leaves the current list unchanged.

### 4.9. Empty and Error States

- A day with no games shows a short message suggesting another date.
- If the day's games cannot load, the page shows an error with a retry option.
- If **Load More** fails, the games already shown stay visible and a retry
  option appears.

### 4.10. Same Page for Everyone

- Browse looks the same for guests and signed-in users.
- Cards do not show whether the viewer has joined, is waitlisted for, or is
  hosting a game.

### 4.11. Information Kept Off Cards

- Cards never show host payment instructions.
- Skill level is not shown on cards. It is shown on Game Details.

## 5. Tests & Edge Cases

These scenarios define expected results to verify; they do not indicate that
automated tests have been written or passed.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Browse signed out and signed in. | Both visitors can see the same public games without signing in; cards show no personal participation or hosting state. |
| 2 | ☐ | Open Browse with no selected date. | Today's results load, and the page link is replaced with today's date. A loading state appears until the first result arrives. |
| 3 | ☐ | Open a valid link to a date in the available window. | That date is selected, its games load, and the seven-date set containing it is visible. |
| 4 | ☐ | Use the date strip across its full range. | Exactly 14 dates are available in two sets of seven. The arrows switch sets without changing the selected date and are disabled at the ends. |
| 5 | ☐ | Select another date. | The link gains a normal history entry; old games, pagination, and errors clear while the new date loads. Back returns to the prior selected date. |
| 6 | ☐ | List a mix of official, community, and nonpublic games. | Published, active, visible, join-open games for the selected date appear together; draft, hidden, paused, cancelled, completed, removed, deleted, and wrong-date games do not appear or count toward hour totals. |
| 7 | ☐ | View games before and at the registration cutoff. | A game remains listed while registration is open and disappears when its cutoff is reached, exactly five minutes after start; no closed card appears. |
| 8 | ☐ | View full games with and without an accepting waitlist. | Both remain listed before the cutoff and show **Full**; neither gets a separate waitlist badge. |
| 9 | ☐ | View games with confirmed players and guests. | Each confirmed player and guest occupies one displayed spot; waitlisted, cancelled, removed, and refunded participants do not. |
| 10 | ☐ | View a game during checkout and after its hold expires. | A valid temporary hold occupies its participant spots; at expiration those spots stop counting, even if cleanup has not run. |
| 11 | ☐ | View an official and a community card. | Each shows the correct type, title, location, market-time range, player group, format, environment, spot count, and price or **Free**. |
| 12 | ☐ | View cards with and without an image. | Available game or venue media is shown; a missing image leaves the card with its default visual. |
| 13 | ☐ | Inspect cards for restricted detail. | Host payment instructions and skill level are absent from Browse cards. |
| 14 | ☐ | Select a game card. | Its Game Details page opens; Browse itself does not reserve a spot. |
| 15 | ☐ | View games at different start times, including ties. | Hour sections and cards run earliest first; games sharing a start time follow creation order. |
| 16 | ☐ | View an hour containing more games than the first batch. | Its heading shows the total eligible games for that hour, not just loaded cards; hours with no loaded cards have no section yet. |
| 17 | ☐ | Open a date with no eligible games. | A short empty message suggests another date; no game cards or Load More control appear. |
| 18 | ☐ | Load a day with more than 40 games. | The first 40 appear, Load More retrieves later games in order without duplicate cards, and the control disappears after the last batch. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 19 | ☐ | Directly open a link with an invalid or impossible date. | Browse selects today, loads today's games, and replaces the invalid link, so Back does not return to it. |
| 20 | ☐ | Open a link before today or beyond the last available day. | The selected date moves to the nearest available boundary and the link is replaced. |
| 21 | ☐ | Keep Browse open across midnight in the market timezone. | On the next visible refresh, the 14-day window moves forward; an out-of-range selected date and link normalize to the new window. |
| 22 | ☐ | Browse across daylight-saving changes or from a device in another timezone. | The strip still contains 14 consecutive market calendar dates; card times and hour groups use the market timezone, regardless of device timezone; each game is assigned by its own local start date. |
| 23 | ☐ | View a day with exactly 40 games. | All games appear with no Load More control. |
| 24 | ☐ | Fail the initial request, then retry. | An error with Retry replaces results; a successful retry shows the selected day's games or its empty state. |
| 25 | ☐ | Fail Load More, then retry. | Already loaded cards remain visible, an inline Retry appears, and a successful retry adds the remaining games without duplicates. |
| 26 | ☐ | Make a later-page game hidden, cancelled, deleted, or past cutoff before Load More. | The later request excludes that game and updates hour totals to the currently eligible set. |
| 27 | ☐ | Change dates while a request is pending. | A late response for the old date cannot replace or append to the newly selected date's results. |
| 28 | ☐ | Refresh while Load More is pending. | A late Load More response cannot append cards from the superseded list after the refreshed first batch replaces it. |
| 29 | ☐ | Leave the page open and visible, then change game availability or spot counts. | Refresh occurs about once a minute or on return to the page, and the next successful result reflects the current listing and counts. Hidden tabs do not start interval refreshes. |
| 30 | ☐ | Refresh a previously expanded list. | Existing cards stay visible while refreshing; success replaces them with the current first batch and resets Load More. |
| 31 | ☐ | Fail a background refresh. | Existing cards and pagination stay visible without a full-page error; a later successful refresh can update them. |
| 32 | ☐ | Use date navigation, Load More, and Retry with keyboard or assistive technology. | Dates and arrows have clear labels and selected or disabled states; Load More is disabled while loading, and Retry remains operable. |
| 33 | ☐ | View a game scheduled beyond the current 14-day Browse window. | It is absent until its date enters the rolling window, then appears if it still meets the public listing rules. |
| 34 | ☐ | Let a temporary hold expire on a full game while Browse stays open. | On the next successful refresh, the filled spot count drops and the **Full** badge disappears when a spot becomes available. |
| 35 | ☐ | List a game whose local start date differs from its Browse market date. | The game appears under its own local calendar date within the 14-day Browse window, regardless of the viewer's device timezone. |
| 36 | ☐ | Introduce an invalid date URL while Browse is already open. | The selection resets to today, today's games replace the previous date's results, and the URL is corrected with history replacement. |

## 6. Open Items to Resolve

**None**.
