# F54 — Platform Notices

## 1. Existing Route(s)

- `/admin/platform-notices` (History)
- `/admin/platform-notices/new` (Create)
- `/admin/platform-notices/:noticeId` (Notice detail)

All three are views of one page with History and Create tabs.

## 2. Purpose

Platform Notices lets staff publish Pickup Lane announcements to every eligible
user or to a chosen list of users, review published notices, and withdraw a
notice by cancelling it. Platform notices are separate from the notifications
that games, bookings, payments, Need a Sub, chat, and account events send on
their own.

## 3. Main Functionality

### 3.1. History

History lists published and cancelled notices, newest first, in batches of 30.
Each row shows the title, audience, publish time, and status. Staff can:

- Search titles and messages.
- Filter by **All statuses**, **Published**, or **Cancelled**.
- Refresh the list.
- Load more notices.

Selecting a row opens its detail.

### 3.2. Create a Notice

Creating a notice has three steps:

1. **Write Notice:** enter a title of up to 150 characters and a plain-text
   message of up to 4,000 characters.
2. **Choose Audience:** choose **All eligible users** or **Selected users**. For
   selected users, search by name, email, or user ID, choose one result, and
   add it. Added users appear in a scrollable list and can be removed.
3. **Review & Publish:** review the notice and audience, then confirm
   **Send Notice**.

After publishing, the new notice's detail opens.

### 3.3. Notice Detail

The detail shows the title, message, publish time, audience, and status. A
cancelled notice also shows when it was cancelled and why. For a
selected-user notice, the recipient list shows each recipient's read state and
loads more recipients in batches.

### 3.4. Cancel a Notice

On a published notice, **Cancel Notice** asks for a required reason of up to
1,000 characters and confirms the cancellation.

## 4. Important Behavior & Decisions

### 4.1. Publishing Is Immediate

There are no drafts, scheduling, delivery tracking, or editing. A published
notice's content and audience never change. Publishing requires recent identity
confirmation. Repeating the same publish request returns the original notice
rather than creating a second one.

### 4.2. Audiences

- **All eligible users:** visible to every current eligible user and to users
  who become eligible later, until cancelled.
- **Selected users:** visible only to the chosen users. At least one and at most
  500 unique users can be chosen. Every chosen user must exist and be eligible
  when publishing; otherwise nothing is published.

Eligible means an active account that is not deleted.

### 4.3. Where Users See Notices

Notices appear in the App Updates section of the user's
[Inbox](../player/inbox.md), which owns how they are displayed and marked as
seen. Notices do not appear in [Notification Lookup](notification-lookup.md).

### 4.4. Read State

Selected-user notices track whether each recipient opened them. All-user
notices show no per-user delivery or read counts.

### 4.5. Cancellation

Cancellation is the only change allowed after publishing. It is permanent,
requires recent identity confirmation, and immediately removes the notice from
every user's Inbox. Cancelling an already cancelled notice keeps the original
cancellation details.

### 4.6. History Search

Search must contain at least three letters or numbers and no more than 200
characters. A shorter search shows a prompt instead of results.

### 4.7. Audit

Publishing and cancelling are recorded in the
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Platform Notices. | History shows published and cancelled notices, newest first, with title, audience, time, and status. |
| 2 | ☐ | Search by a title word and filter by status. | Only matching notices appear and the list restarts from the first batch. |
| 3 | ☐ | Load more than 30 notices. | The next notices append in order without duplicates. |
| 4 | ☐ | Publish an all-users notice after confirming identity. | The detail opens; the notice appears in App Updates for current eligible users and for users who become eligible later. |
| 5 | ☐ | Publish a selected-users notice to three users. | Only those users see it; the detail lists the three recipients with their read state. |
| 6 | ☐ | A selected recipient opens the notice in their Inbox. | That recipient's state changes to Read in the detail. |
| 7 | ☐ | Cancel a published notice with a reason after confirming identity. | The status becomes Cancelled with time and reason, and the notice disappears from every Inbox. |
| 8 | ☐ | Check the Admin Action Log after publishing and cancelling. | Both actions appear with the acting admin. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | Continue with an empty title or message. | The step reports the missing fields and does not advance. |
| 10 | ☐ | Enter a title over 150 or a message over 4,000 characters. | Input stops at the limit. |
| 11 | ☐ | Choose Selected users without adding anyone. | The step asks for at least one user and does not advance. |
| 12 | ☐ | Add more than 500 users. | Adding stops at 500 with a limit message. |
| 13 | ☐ | Add the same user twice. | The user appears only once. |
| 14 | ☐ | Publish when a selected user was suspended or deleted after being added. | Publishing fails, nothing is published, and an error appears. |
| 15 | ☐ | Submit the same publish twice. | Only one notice is created. |
| 16 | ☐ | Decline or fail identity confirmation when publishing or cancelling. | No notice is published or cancelled. |
| 17 | ☐ | Try to cancel without a reason. | Cancellation does not proceed. |
| 18 | ☐ | Cancel a notice that is already cancelled. | The original cancellation time, reason, and admin are unchanged and no second audit entry is created. |
| 19 | ☐ | Search with fewer than three letters or numbers. | A prompt appears instead of results and no search runs. |
| 20 | ☐ | Search for text with no matches. | An empty result appears. |
| 21 | ☐ | Fail to load History or a notice detail, then retry. | An error with Retry appears; a successful retry shows the data. |
| 22 | ☐ | View a notice with a very long title or message. | The text displays fully and safely on desktop and mobile. |

## 6. Open Items to Resolve

**None**.
