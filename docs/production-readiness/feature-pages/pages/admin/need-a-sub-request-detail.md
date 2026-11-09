# F36 — Need a Sub Request (Admin)

## 1. Existing Route(s)

- `/admin/need-a-sub/requests/:requestId`

## 2. Purpose

Need a Sub Request (Admin) shows staff one player's request to fill a sub spot,
with its status history and the context of the post it belongs to. It is a
read-only support view reached from review cases, a user's Need a Sub activity,
and other admin links.

## 3. Main Functionality

### 3.1. Request

Shows the request status, requested position, requester, request ID, post ID,
and when the request was created.

### 3.2. Post Context

Shows the post's status, visibility, and start time.

### 3.3. Status History

Lists each status change for the request with its action, who made it, reason,
and time.

### 3.4. Back

**Back** opens the post in [Need a Sub Post (Admin)](need-a-sub-post-detail.md),
or the [Need a Sub (Admin)](need-a-sub-posts.md) list when the post is
unavailable.

## 4. Important Behavior & Decisions

### 4.1. Read-Only

The page has no actions. Moderation of the post happens on
Need a Sub Post (Admin).

### 4.2. Current Statuses

Past-due posts and requests are expired before the page is shown, so the
request and post statuses are current.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a request from a user's Need a Sub activity. | The request, post context, and status history appear. |
| 2 | ☐ | Open a request that changed status several times. | Every change appears with action, actor, reason, and time. |
| 3 | ☐ | Open a request on a post an admin removed. | The request shows closed by admin and the post shows removed. |
| 4 | ☐ | Select Back. | The parent post's admin page opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 5 | ☐ | Open a request whose waiting period has passed. | The request shows its updated expired status. |
| 6 | ☐ | Open a request that does not exist. | A not-found error appears. |
| 7 | ☐ | Fail to load the request. | An error appears without stale request data. |

## 6. Open Items to Resolve

**None**.
