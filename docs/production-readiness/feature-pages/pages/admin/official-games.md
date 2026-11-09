# F28 — Official Games

## 1. Existing Route(s)

- `/admin/official-games`

## 2. Purpose

Official Games is the staff entry point for finding games that Pickup Lane runs
and opening their management page. It is a browse and filter list; creating a
game belongs to [Create Official Game](create-official-game.md), and managing
one belongs to [Official Game Manage](official-game-manage.md).

## 3. Main Functionality

### 3.1. Lifecycle Tabs

Games are grouped into **Active**, **Full**, **Completed**, **Cancelled**,
**Expired**, and **Removed** tabs. Active shows active games with open spots;
Full shows active games at capacity. Changing the tab reloads the list.

### 3.2. Search and Date

- Search by title, venue, city, or state. Search runs after at least three
  characters and a short pause. **Clear search** returns to the unsearched list.
- Choose a single date to show only games on that local game date.

### 3.3. Date-Grouped Cards

Cards are grouped by local game date. Each card shows:

- The venue photo, or a placeholder when there is none.
- Title, location, time range, and format details.
- Booked spots out of total spots, and price.
- A **Missing host** label on active games that have no assigned host.

Selecting a card opens Official Game Manage.

### 3.4. Load More

Games load in batches of 24. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. What Is Listed

Only published official games appear. Community games and deleted games never
appear. Cancelled, expired, and removed games stay available in their tabs for
history.

### 4.2. Ordering

Active and Full list the soonest games first. Completed, Cancelled, Expired, and
Removed list the most recent games first.

### 4.3. Booked Spots

Booked spots count confirmed players and players with an active checkout hold.

### 4.4. No Actions on Cards

The list does not offer create, edit, or cancel controls on cards. Staff create
games from the admin navigation.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Official Games. | Active official games with open spots appear, soonest first, grouped by date. |
| 2 | ☐ | Open each other tab. | Each tab shows only official games in that state in the documented order. |
| 3 | ☐ | Search by title, venue, and city. | Matching games appear in the current tab. |
| 4 | ☐ | Choose a date. | Only games on that local date appear; clearing it restores all dates. |
| 5 | ☐ | View an active game without a host. | The card shows Missing host. |
| 6 | ☐ | Load more than 24 games. | The next games append without duplicates. |
| 7 | ☐ | Select a card. | Official Game Manage opens for that game. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 8 | ☐ | Type fewer than three characters. | The list stays unsearched. |
| 9 | ☐ | Apply a search or date with no matches. | "No official games found" appears with no Load More control. |
| 10 | ☐ | Look for a community or deleted game. | Neither appears. |
| 11 | ☐ | View a game whose venue photo cannot be loaded. | The card shows the placeholder without reporting the photo as missing. |
| 12 | ☐ | View a completed or cancelled game without a host. | No Missing host label appears. |
| 13 | ☐ | Fail the first load or Load More. | An error appears; loaded cards stay visible after a Load More failure. |
| 14 | ☐ | Change tab, search, or date while a request is pending. | A late response for the earlier view does not change the list. |

## 6. Open Items to Resolve

**None**.
