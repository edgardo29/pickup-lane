# F42 — User Need a Sub Activity

## 1. Existing Route(s)

- `/admin/users/:userId/need-a-sub-activity`

## 2. Purpose

User Need a Sub Activity shows staff the full history of one user's Need a Sub
posts and requests, so they can answer support questions beyond the preview on
[User Detail](user-detail.md).

## 3. Main Functionality

### 3.1. Activity History

The page shows the total number of activity items. Each row shows:

- **Location** and **Date** of the outside game.
- **Type:** created (a post by this user) or requested (a request this user
  made on another post).
- **Status** of the post or request.
- **Subs needed**, for posts the user created.
- **Post status**, for requests the user made.

Selecting a created row opens
[Need a Sub Post (Admin)](need-a-sub-post-detail.md). Selecting a requested row
opens [Need a Sub Request (Admin)](need-a-sub-request-detail.md).

### 3.2. Load More

Rows load in batches of 25. **Load More** adds the next batch.

### 3.3. Back

**Back** returns to the user's User Detail.

## 4. Important Behavior & Decisions

### 4.1. Posts and Requests Together

Posts the user created and requests the user made appear in one history, each as
its own row.

### 4.2. Ordering

Active upcoming items come first, soonest first. Other items follow, with the
most recent game date first and then the most recent activity first.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open the page for a user with posts and requests. | Both appear in one list with location, date, type, and status. |
| 2 | ☐ | View a created row. | It shows subs needed when the post needs subs. |
| 3 | ☐ | View a requested row. | It shows the request status and the post's status. |
| 4 | ☐ | Compare upcoming active items with past items. | Upcoming active items appear first, soonest first; others follow, most recent first. |
| 5 | ☐ | Select a created row and a requested row. | The admin post page and admin request page open. |
| 6 | ☐ | Load more than 25 items. | The next items append without duplicates. |
| 7 | ☐ | Select Back. | The user's User Detail opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 8 | ☐ | Open the page for a user with no Need a Sub activity. | An empty message appears. |
| 9 | ☐ | View a request on a post that was later removed or cancelled. | The row shows the request's status and the post's updated status. |
| 10 | ☐ | Fail the first load or Load More. | An error appears; loaded rows stay visible after a Load More failure. |

## 6. Open Items to Resolve

**None**.
