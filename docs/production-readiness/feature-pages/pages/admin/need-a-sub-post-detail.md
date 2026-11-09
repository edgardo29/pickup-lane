# F35 — Need a Sub Post (Admin)

## 1. Existing Route(s)

- `/admin/need-a-sub/:postId`

## 2. Purpose

Need a Sub Post (Admin), titled **Manage Need a Sub Post**, lets staff
investigate one Need a Sub post and its requests, chat, status history, and
admin history, and hide, restore, or remove the post when needed. It has no
payment, refund, or credit actions because Need a Sub has no in-app money.

## 3. Main Functionality

### 3.1. Summary

The summary shows the post's title, date, time, venue, format, player group,
skill level, environment, and price.

### 3.2. Overview

The **Overview** tab shows the status, visibility, owner, each sub need with
needed, confirmed, pending, and waitlisted counts, address, closure reason when
present, and notes.

### 3.3. Requests

The **Requests** tab lists requests, newest first, 50 per page, with the
requester, position, status, and request time. Expanding a request shows its
status history with action, who changed it, reason, and date.

### 3.4. Chat

The **Chat** tab shows the chat summary (chat status, message count, messages
needing review, and removed messages) and the chat moderation described in
[Community Game Detail](community-game-detail.md#34-chat).

### 3.5. Status and Audit

The **Status** tab shows the post's status history. The **Audit** tab lists
admin actions on the post, 50 per page.

### 3.6. Post Actions

- **Hide post** or **Restore post:** remove the post from, or return it to,
  player views.
- **Remove post:** remove the post permanently.

Each action requires a reason of up to 100 characters.

## 4. Important Behavior & Decisions

### 4.1. Reversible and Terminal Actions

Hiding can be undone. Removal cannot, and no actions are offered after a post is
removed. Removal requires recent identity confirmation.

### 4.2. Hidden Posts

A hidden post is unavailable to players, and new requests and acceptances are
blocked by the backend, not only hidden in the interface. The owner receives a
notice when the post is hidden or restored.

### 4.3. Removal Effects

Removing a post:

- Changes its status to removed and records the admin as the source.
- Closes the post chat.
- Closes live requests (pending, confirmed, or waitlisted) as
  `closed_by_admin`, leaving already finished requests unchanged.
- Notifies the owner that the post was removed and each affected requester that
  their request was closed.

Removal keeps the post and request histories for staff and does not convert
requests into `canceled_by_owner`, which remains an owner-cancellation status.

### 4.4. Review Case Links

Hiding or removing a post with an open content-moderation case links the action
to that case, and removal closes it automatically. See
[Review Case Detail](review-case-detail.md).

### 4.5. Current Statuses

Past-due posts and requests are expired before the page is shown. Removing a
post also first applies any due expiration.

### 4.6. Recorded Viewing and Repeated Actions

Viewing chat messages and opening a message's full text are recorded as
sensitive admin views; see [Admin Action Log](admin-action-log.md). Repeating
the same action does not apply it twice.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open an active post with requests. | Summary, overview with sub need counts, and requests with status history appear. |
| 2 | ☐ | Hide the post with a reason. | Players can no longer see or request it, the owner is notified, and Restore post becomes available. |
| 3 | ☐ | Restore a hidden post. | Players can see and request it again, and the owner is notified. |
| 4 | ☐ | Remove a post with pending, confirmed, waitlisted, and declined requests after confirming identity. | The post becomes removed; live requests become `closed_by_admin` with history preserved and their requesters are notified; the declined request is unchanged; the owner is notified; the chat closes. |
| 5 | ☐ | View a removed post. | Its history remains and no post actions are offered. |
| 6 | ☐ | Hide a post with an open content-moderation case. | The case timeline shows the linked action. |
| 7 | ☐ | Open the Chat tab and moderate a message. | Chat moderation behaves as described in Community Game Detail. |
| 8 | ☐ | Page through more than 50 requests or audit actions. | Previous and next pages show the remaining items without duplicates. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | Submit an action without a reason or with more than 100 characters. | The action cannot be submitted. |
| 10 | ☐ | Remove a post that another admin already removed. | Removal is rejected and the page shows the removed post. |
| 11 | ☐ | Decline identity confirmation when removing. | The post is not removed. |
| 12 | ☐ | Submit the same removal twice. | It is applied, audited, and notified once. |
| 13 | ☐ | Open a post with no chat. | The chat summary shows that no chat has been created. |
| 14 | ☐ | Open a post whose time has passed while it was active. | The page shows its updated status. |
| 15 | ☐ | Open a post that does not exist. | A not-found error appears. |

## 6. Open Items to Resolve

**None**.
