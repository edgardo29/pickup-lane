# F22 — Need a Sub Post Detail

## 1. Existing Route(s)

- `/need-a-sub/posts/:postId`

`/need-a-sub/posts/:postId/manage` redirects here; owners manage requests within this page.

## 2. Purpose

This page explains one outside-game substitute need to authenticated visitors. Eligible signed-in players can request a specific spot, and owners can manage the post and its requests. Public discovery belongs to [Need a Sub](need-a-sub.md).

## 3. Main Functionality

### 3.1. Review the Post

- Show the number of subs needed, game setup, date/time, location, notes, payment due at venue, and each field-player or goalkeeper need.
- Exact street address and host notes are shown only to authenticated viewers permitted to see an accessible post. Guests cannot see full post details.
- A share action sends or copies a direct link. The back action returns to [Need a Sub](need-a-sub.md).

### 3.2. Request a Spot

- A nonowner selects one specified need. Available needs offer **Request Spot**; a full need offers **Join Waitlist** unless the post waitlist is full.
- The page shows the viewer's current pending, confirmed, or waitlisted status and allows cancellation while the post is still open.
- Signed-out visitors are directed to Sign In or Create Account with the post return path. Request and waitlist lifecycle rules are established in the Need a Sub feature notes.

### 3.3. Owner Actions and Chat

- The owner sees availability, pending/confirmed/waitlisted counts, and actions to manage requests, edit, or cancel an active upcoming post.
- Manage Requests opens a modal organized by need and request status. The owner can accept or decline pending requests, decline waitlisted requests, and remove confirmed subs.
- The post chat opens for the owner and current confirmed subs while its access window remains open. It supports text messages and older-message loading.

## 4. Important Behavior & Decisions

### 4.1. Public and Connected Access

The backend requires authentication for full post detail. Public summary cards remain available on [Need a Sub](need-a-sub.md). An owner or connected requester may retain private detail after public discovery closes. Cancelled, removed, or inaccessible posts do not expose active request controls. A verified email is required to create or cancel a request, make owner changes, create post chat, or send chat messages. Permitted signed-in reads do not require email verification. Need a Sub is separate from Pickup Lane game bookings and payments.

### 4.2. Request and Availability Rules

The owner cannot request their own post; a player may have only one active request per post. A suspended player cannot initiate a new request, but may access and handle an existing accepted arrangement or withdraw under [User Detail](../admin/user-detail.md#410-suspended-player-experience). Pending requests hold review slots for new requesters, while confirmed requests fill spots. The owner's availability summary and [list card](need-a-sub.md) count only confirmed subs; the detail request choice counts both pending and confirmed requests when deciding whether a new requester joins the waitlist. When a selected need's review slots are taken, new requests join that need's waitlist, subject to the post-wide cap of 25 waitlisted requests. A freed review slot can move the earliest eligible waitlisted request forward for that need. Request and owner changes close at the outside game's start.

### 4.3. Chat Access

Only the owner and currently confirmed requesters can read or send post chat until 24 hours after game end. Pending, waitlisted, cancelled, removed, unrelated, and signed-out viewers cannot use it. Post cancellation/removal closes normal chat immediately. Messages are text only, limited to 300 characters, five sends per minute per sender, and 200 visible messages per post.

### 4.4. Loading and Feedback

The page shows a loading skeleton, an unavailable/not-found result, or an error alert as appropriate. Successful request or owner actions refresh the detail; failed actions report an error without changing the confirmed state. A successfully loaded empty viewer or owner request list is distinct from a failed load. If either request list fails, the affected request information shows a clear error and Retry option; the page does not present it as a confirmed empty result.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a visible post signed out and signed in. | A guest is directed to authentication without full details; an eligible signed-in viewer sees the post facts, needs, and permitted address and host notes. |
| 2 | ☐ | View mixed needs with pending and confirmed requests. | Every configured need is visible; owner availability reflects confirmations, while requester availability and waitlisting account for pending holds as well. Selecting a need keeps the request choice in sync. |
| 3 | ☐ | Request a need with a free review slot. | The request becomes pending, the owner receives it for review, and the requester sees pending status rather than a confirmed spot. |
| 4 | ☐ | Request a need whose review slots are taken. | The requester joins that need's waitlist when it is open; the page shows waitlist status and position. |
| 5 | ☐ | Open the post with an active pending, confirmed, or waitlisted request. | The current status and matching cancel action appear; a second active request action is absent. |
| 6 | ☐ | Cancel a current request or leave its waitlist. | The active request ends, the detail refreshes, and any eligible next waitlisted request is handled under the need's queue rules. |
| 7 | ☐ | Open the post as its owner. | The owner sees availability and request counts, with management actions for an active upcoming post and no Request Spot action. |
| 8 | ☐ | Review owner requests by need and status. | The modal shows matching requests; accepted requests become confirmed, declined requests leave the active queue, and removed subs free their spots. |
| 9 | ☐ | Open and use chat as owner or confirmed sub. | The chat opens, recent messages and older-message loading work, valid text sends appear, and unread state clears on read. |
| 10 | ☐ | Share the post and follow its back link. | Sharing uses the device share action or copies the direct link; Back opens Need a Sub. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 11 | ☐ | Open a missing, removed, or otherwise inaccessible post. | The page shows an unavailable/not-found state and no request or manage action. |
| 12 | ☐ | Reach the post waitlist cap. | A full need no longer accepts another waitlist request; the page shows Waitlist Full. |
| 13 | ☐ | Race another request into the last review slot or change post status before submitting. | The backend applies current capacity/status, rejects an ineligible action, and the page shows an error rather than a false success. |
| 14 | ☐ | Attempt a request, cancellation, or owner review at or after game start. | The action is unavailable or rejected; the earlier request/confirmation state remains intact. |
| 15 | ☐ | Try chat as a pending, waitlisted, former, unrelated, or signed-out viewer. | Chat remains unavailable and protected message requests cannot disclose messages. |
| 16 | ☐ | Close chat through cancellation/removal or pass 24 hours after game end. | Normal chat read and send access ends even for a previously confirmed member. |
| 17 | ☐ | Send empty, overlong, too-frequent, or over-cap chat messages. | The message is rejected with feedback and is not displayed as sent. |
| 18 | ☐ | Fail a detail load or an action request. | The page reports the failure; an action failure does not claim success or erase the existing post. |
| 19 | ☐ | View an accessible post with a signed-in but unverified email, then attempt a request, request cancellation, owner change, chat creation, or chat send. | Permitted details remain readable; protected actions require verified email, report rejection, and do not change requests, the post, or chat. |
| 20 | ☐ | Fail the viewer's request-status load or the owner's request-list load while post detail succeeds. | The affected request information shows a clear error and Retry, not an empty status or owner list; a successful retry restores the real requests or a confirmed empty state. |
| 21 | ☐ | Request post detail directly from the backend without authentication. | The response cannot expose full post fields; any returned information is limited to the public summary, while private detail requires authentication. |
| 22 | ☐ | Follow a post card as a guest and complete authentication. | The selected post opens if still available; an unavailable post is not disclosed and uses the established fallback. |
| 23 | ☐ | Open an existing accepted Need a Sub arrangement while suspended, then attempt a new request. | Existing access, permitted coordination, owner management, and withdrawal remain available; the new request is blocked. |

## 6. Open Items to Resolve

**None**.
