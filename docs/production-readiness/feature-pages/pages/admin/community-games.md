# F32 — Community Games

## 1. Existing Route(s)

- `/admin/community-games`

## 2. Purpose

Community Games lets staff find user-hosted community games for support and
moderation. It is a lean browsing list; investigation and enforcement happen on
[Community Game Detail](community-game-detail.md).

## 3. Main Functionality

### 3.1. Lifecycle Tabs

Games are grouped into **Active**, **Full**, **Completed**, **Cancelled**,
**Expired**, and **Removed** tabs. Active and Full show only active games that
have open spots or are full, respectively. Changing the tab reloads the list.

### 3.2. Search

Staff can search by game title, venue, host name or email, city, or state.
Search runs after at least three characters and a short pause. **Clear search**
returns to the unsearched list.

### 3.3. Date-Grouped Cards

Cards are grouped by game date, with a game count for each date and an overall
count such as "Showing 24 of 60 games". Each card shows:

- Title and venue name.
- City and state, and time range.
- Host name.
- Confirmed spots out of total spots, and price.
- Up to two issue labels: **Hidden**, **Joining paused**, **Review required**,
  or **Payment text hidden**.

Selecting a card opens Community Game Detail.

### 3.4. Load More

Games load in batches of 24. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. Ordering

Active and Full list the soonest games first. Completed, Cancelled, Expired, and
Removed list the most recent games first.

### 4.2. Community Games Only

The list shows only community games. Official games are managed in
[Official Games](official-games.md). Deleted games are not listed.

### 4.3. Lean Cards

Cards show only information needed to pick a game and spot problems. Normal
states, such as an eligible host, a published listing, or present payment text,
are not shown as labels.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Community Games. | The Active tab shows upcoming active community games with open spots, soonest first, grouped by date. |
| 2 | ☐ | Open the Full tab. | Only active games with every spot taken appear. |
| 3 | ☐ | Open the Completed, Cancelled, Expired, and Removed tabs. | Each shows only games in that state, most recent first. |
| 4 | ☐ | Search by title, venue, host, and city. | Matching games appear in the current tab. |
| 5 | ☐ | Clear the search. | The unsearched list for the tab returns. |
| 6 | ☐ | View a hidden game with an open review flag. | Its card shows Hidden and Review required. |
| 7 | ☐ | Load more than 24 games. | The next games append under the correct dates without duplicates, and the overall count updates. |
| 8 | ☐ | Select a card. | Community Game Detail opens for that game. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | Type fewer than three characters. | The list stays unsearched. |
| 10 | ☐ | Search with no matches. | "No community games found" appears with no Load More control. |
| 11 | ☐ | Look for an official game or a deleted game. | Neither appears. |
| 12 | ☐ | Fail the first load or Load More. | An error appears; loaded cards stay visible after a Load More failure. |
| 13 | ☐ | Change tab or search while a request is pending. | A late response for the earlier view does not change the list. |

## 6. Open Items to Resolve

**None**.
