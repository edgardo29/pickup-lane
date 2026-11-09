# F53 — Notification Lookup

## 1. Existing Route(s)

- `/admin/notifications`
- `/admin/notifications/:notificationId`

The second route opens the same page with that notification's detail window
open.

## 2. Purpose

Notification Lookup lets staff answer one support question: which generated
notifications did a specific user receive, and what happened with them? It is
a read-only inspector of a user's notification history. Platform notices are
managed separately in [Platform Notices](platform-notices.md).

## 3. Main Functionality

### 3.1. Find a Recipient

Staff type at least three characters of a user's name, email, or user ID, then
choose a user from the results. Until a user is chosen, only the search is
shown. Clearing the chosen user clears the results.

### 3.2. Notification History

After a user is chosen, that user's notifications load automatically, newest
first, in batches of 50. Rows use the same title and subject display as the
user's [Inbox](../player/inbox.md), with their time. **Load More** adds the next
batch.

### 3.3. Notification Detail

Selecting a row opens a detail window titled with the row's source and title.
It shows:

- **Message:** the context line and message text.
- **Support details:** recipient name and email, read status, read time when
  read, event time, destination status with an **Open destination** link when
  available, and the notification ID with a copy control.

## 4. Important Behavior & Decisions

### 4.1. Read-Only

The page cannot create, resend, retry, edit, delete, or mark notifications as
read or unread. It has no payment, refund, or other repair controls.

### 4.2. One Recipient at a Time

History is searched only by recipient. There is no global browsing, notification
search, or filtering by type, read state, or date, and no total count.

### 4.3. Current Destination Status

The detail compares the stored notification with current app state. A
destination can be available, unavailable, broken, or not applicable.

- **Game links** stop being available when the game is deleted, unpublished,
  cancelled, expired, or removed. A game that has started or completed keeps its
  link.
- **Need a Sub links** stop being available when the post is no longer active or
  its start time has passed.
- **Need a Sub chat links** are also disabled, with a reason, when the post was
  removed or cancelled, the chat closed, the access window ended, or the user
  lost access to the chat.

### 4.4. Platform Notices Excluded

Platform notices never appear in this history and cannot be opened here.

### 4.5. Direct Links

Opening a notification's direct link shows its detail window. Closing the
window returns to `/admin/notifications`.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Notification Lookup. | Only the recipient search appears; no results or detail are shown. |
| 2 | ☐ | Search by name, email, and user ID, then select a user. | That user's latest notifications load automatically, newest first, without opening a row. |
| 3 | ☐ | Load more than 50 notifications. | The next notifications append in order without duplicates; Load More disappears after the last batch. |
| 4 | ☐ | Select a row. | The detail window shows the message, recipient, read status, event time, destination status, and notification ID. |
| 5 | ☐ | Open a read and an unread notification. | Read time appears only for the read notification. |
| 6 | ☐ | Open a notification with an available destination. | **Open destination** goes to the current destination. |
| 7 | ☐ | Copy the notification ID. | The ID is copied and the control confirms it. |
| 8 | ☐ | Open a direct notification link, then close the detail. | The detail opens on load; closing returns to the lookup page. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | Type fewer than three characters. | No recipient search runs. |
| 10 | ☐ | Select a user with no notifications. | "No notifications found" appears. |
| 11 | ☐ | Change or clear the selected user. | Earlier rows, selected detail, paging, and errors clear before the new history loads. |
| 12 | ☐ | Select rows quickly while detail is loading. | Only the most recently selected notification's detail is shown. |
| 13 | ☐ | Open notifications for a cancelled game, a started game, and a started Need a Sub post. | The cancelled game and the started post show their destination as unavailable or broken with no Open destination link; the started game still offers its link. |
| 14 | ☐ | Open a chat notification after the user lost chat access. | The destination is unavailable. |
| 15 | ☐ | Look for a platform notice the user received. | It does not appear in the history, and its ID does not open here. |
| 16 | ☐ | Open a notification ID that does not exist. | A not-found error appears. |
| 17 | ☐ | Fail the history or detail request. | An error appears without stale rows or detail from another request. |
| 18 | ☐ | Inspect the page for edit controls. | No resend, retry, delete, or read-state controls exist. |

## 6. Open Items to Resolve

**None**.
