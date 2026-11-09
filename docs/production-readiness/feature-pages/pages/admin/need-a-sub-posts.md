# F34 — Need a Sub (Admin)

## 1. Existing Route(s)

- `/admin/need-a-sub`

## 2. Purpose

Need a Sub (Admin) lets staff find Need a Sub posts for support and moderation.
It is a browsing list; investigation and enforcement happen on
[Need a Sub Post (Admin)](need-a-sub-post-detail.md). Need a Sub is its own
product area, separate from official and community games.

## 3. Main Functionality

### 3.1. Lifecycle Tabs

Posts are grouped into **Active**, **Full**, **Completed**, **Cancelled**,
**Expired**, and **Removed** tabs. Active shows active posts that still need
subs; Full shows posts whose sub needs are filled. Changing the tab reloads the
list.

### 3.2. Search

Staff can search by team name, sub need, location, city, state, or owner name or
email. Search runs after at least three characters and a short pause.
**Clear search** returns to the unsearched list.

### 3.3. Date-Grouped Cards

Cards are grouped by game date, with a count for each date and an overall count.
Each card shows:

- How many subs are needed.
- Owner name, location name, city and state, and time range.
- Confirmed subs out of subs needed.
- Signals such as **Hidden**, a non-active post status, and the number of
  pending or confirmed requests.

Selecting a card opens Need a Sub Post (Admin).

### 3.4. Load More

Posts load in batches of 24. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. Ordering

Active and Full list the soonest posts first. Completed, Cancelled, Expired, and
Removed list the most recent posts first.

### 4.2. Current Statuses

Posts and requests that are past due are expired before the list is shown, so
tabs reflect current status.

### 4.3. Removed Posts Stay Visible to Staff

Removed posts remain available here for support history even though they no
longer appear in player views.

### 4.4. Deleted Owners

A deleted owner is shown as "Deleted User".

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Need a Sub (Admin). | The Active tab shows active posts that still need subs, soonest first, grouped by date. |
| 2 | ☐ | Open the Full tab. | Only posts whose sub needs are filled appear. |
| 3 | ☐ | Open the Completed, Cancelled, Expired, and Removed tabs. | Each shows only posts in that state, most recent first. |
| 4 | ☐ | Search by team name, location, and owner email. | Matching posts appear in the current tab. |
| 5 | ☐ | View a hidden post with pending requests. | The card shows Hidden and the pending request count. |
| 6 | ☐ | Load more than 24 posts. | The next posts append under the correct dates without duplicates. |
| 7 | ☐ | Select a card. | Need a Sub Post (Admin) opens for that post. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 8 | ☐ | Open the list after an active post's time has passed. | The post no longer appears under Active and appears under its updated status. |
| 9 | ☐ | Remove a post, then open the Removed tab. | The post appears there and remains unavailable to players. |
| 10 | ☐ | Type fewer than three characters. | The list stays unsearched. |
| 11 | ☐ | Search with no matches. | "No Need a Sub posts found" appears with no Load More control. |
| 12 | ☐ | Fail the first load or Load More. | An error appears; loaded cards stay visible after a Load More failure. |
| 13 | ☐ | Change tab or search while a request is pending. | A late response for the earlier view does not change the list. |

## 6. Open Items to Resolve

**None**.
