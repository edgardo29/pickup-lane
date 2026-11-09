# F41 — User Game Activity

## 1. Existing Route(s)

- `/admin/users/:userId/game-activity`

## 2. Purpose

User Game Activity shows staff the full history of one user's official and
community games, so they can answer support questions about attendance,
cancellations, and hosting beyond the preview on
[User Detail](user-detail.md).

## 3. Main Functionality

### 3.1. Game History

The page shows the total number of games in the history. Each row shows:

- **Location:** venue or game name, with city and state.
- **Date:** the scheduled date and time, and whether the game is official or
  community.
- **Role:** player or host.
- **Outcome:** such as upcoming, attended, no show, late cancel, host cancel,
  cancelled, completed, expired, or removed.

Selecting a row opens [Official Game Manage](official-game-manage.md) or
[Community Game Detail](community-game-detail.md).

### 3.2. Load More

Rows load in batches of 25. **Load More** adds the next batch.

### 3.3. Back

**Back** returns to the user's User Detail.

## 4. Important Behavior & Decisions

### 4.1. One Row per Game

A user's several connections to the same game, such as hosting and playing or
bringing guests, are combined into one row with one outcome.

### 4.2. Ordering

Upcoming games come first, soonest first. Past games follow, most recent first.

### 4.3. Outcome Priority

When several outcomes could apply, a host's own cancellation is reported first,
then no show, late cancel, host cancel, attended, upcoming, and cancelled.
Completed games the user hosted are reported as attended.

### 4.4. Excluded Games

Deleted games are not listed.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open the page for a user with upcoming and past games. | Upcoming games appear first, soonest first, followed by past games, most recent first. |
| 2 | ☐ | View a game the user hosted. | The row shows Host and the matching outcome. |
| 3 | ☐ | View games the user attended, missed, and late-cancelled. | Each row shows attended, no show, or late cancel. |
| 4 | ☐ | View a game where the user both played and brought guests. | Only one row appears for that game. |
| 5 | ☐ | Select an official and a community row. | The matching admin game page opens. |
| 6 | ☐ | Load more than 25 games. | The next games append without duplicates. |
| 7 | ☐ | Select Back. | The user's User Detail opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 8 | ☐ | Open the page for a user with no games. | "No game activity found for this user" appears. |
| 9 | ☐ | Include a deleted game in the user's history. | The deleted game is not listed. |
| 10 | ☐ | Cancel a game the user hosted. | The row shows host cancel. |
| 11 | ☐ | Fail the first load or Load More. | An error appears; loaded rows stay visible after a Load More failure. |
| 12 | ☐ | Open the page for a deleted user. | The user's game history and total still load; the page shows only game rows, with no user details. |

## 6. Open Items to Resolve

**None**.
