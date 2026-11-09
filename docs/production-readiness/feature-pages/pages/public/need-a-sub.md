# F20 — Need a Sub

## 1. Existing Route(s)

- `/need-a-sub` (browse view)

`/player-hub` redirects here. The Create Sub Post panel shares this URL and is documented separately in [Create Sub Post](../hosting/create-sub-post.md).

## 2. Purpose

Need a Sub lets anyone discover summary cards for substitute requests for soccer games outside Pickup Lane. Signed-in owners can also find their own current posts; opening full post details requires an account.

## 3. Main Functionality

### 3.1. Find Posts

- Everyone can browse **All Posts** summary cards. Signed-in users can also switch to **My Posts**.
- A date strip offers 14 dates in two sets of seven. Selecting a date shows posts for that day; switching sets selects the first date in the new set.
- Posts are grouped by start hour and ordered by start time. Cards show venue, city/state, time, player group, format, indoor/outdoor setting, exact types of subs needed, open counts, and confirmed spots.
- Selecting a card opens [Need a Sub Post Detail](need-a-sub-post-detail.md) for an authenticated visitor; guests are directed to Sign In or Create Account with that post as the return destination. **Load More** appends later posts when available.

### 3.2. Start a Post

**Create Post** switches to the create panel on the same URL. The creation workflow belongs to [Create Sub Post](../hosting/create-sub-post.md).

### 3.3. Guest Browsing

Signed-out visitors can browse summary cards and use public date navigation. They cannot use My Posts or create, request, or message until the required account steps are completed.
An unverified signed-in account can also browse public posts; verification is required when attempting to create a post, as described in [Create Sub Post](../hosting/create-sub-post.md).

## 4. Important Behavior & Decisions

### 4.1. Listing Rules

The public list contains only summary cards for visible, active, future posts on the selected date; full post details require authentication at both the page and backend. After sign-in or account creation, a guest returns to the selected post if it is still available. If it is unavailable, the established fallback applies. My Posts further limits results to posts owned by the signed-in user. Cancelled, removed, expired, and past posts do not appear. Connected history belongs to [My Games](../player/my-games.md).

### 4.2. Counts and Ordering

Card open counts are reduced by confirmed subs, not pending requests. A full need can remain visible on its card. Posts with the same start time follow creation order. The first batch contains up to 40 posts; later batches continue the same ordering.

### 4.3. Keeping Results Current

Changing tab or date starts a fresh first batch. The list refreshes when the browser regains focus or visibility. A loading skeleton, empty message, and error alert communicate the result state. If loading another batch fails, already shown posts remain and **Load More** can be tried again.

### 4.4. Separate From Pickup Lane Games

These are requests for outside games, not Pickup Lane game listings or bookings. Request, waitlist, and chat behavior belongs to [Need a Sub Post Detail](need-a-sub-post-detail.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Need a Sub signed out. | Public summary cards and date controls appear without signing in; My Posts and creation controls remain unavailable. |
| 2 | ☐ | Open Need a Sub signed in, including with an unverified account. | All Posts for today loads with the date strip and Create Post action; an unverified email does not block public browsing. |
| 3 | ☐ | Switch dates and the two seven-day sets. | Fourteen local calendar dates are offered; selecting a date loads that day's posts, while changing the set selects its first date. |
| 4 | ☐ | Switch between All Posts and My Posts. | All Posts shows eligible public posts; My Posts shows only the signed-in owner's eligible posts for that date, starting from its first batch. |
| 5 | ☐ | View a mixed set of posts. | Only active, visible, future posts on the selected date appear, sorted by start time and creation order; cancelled, removed, expired, past, and wrong-date posts are absent. |
| 6 | ☐ | View posts with mixed needs, pending requests, and confirmations. | Each card retains its configured need labels; its open and filled counts reflect confirmations rather than pending reviews. |
| 7 | ☐ | Select a post card or Create Post while signed in. | The card opens its detail page; Create Post opens the create panel on the same route. |
| 8 | ☐ | Browse more than 40 posts on one date. | Load More appends later posts in order and disappears when no further batch remains. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | Select a date or tab with no eligible posts. | The relevant empty message appears instead of cards or Load More. |
| 10 | ☐ | Fail the initial list request. | An error alert appears and no stale cards from the previous date or tab remain. |
| 11 | ☐ | Fail Load More, then try it again. | Existing cards remain; a later successful attempt appends the next batch. |
| 12 | ☐ | Change date or tab while a list request is pending. | A late response for the old selection cannot replace or append to the current results. |
| 13 | ☐ | Return to a visible page after a post changes status or count. | The refreshed first batch reflects currently eligible posts and counts. |
| 14 | ☐ | Open a summary card as a guest, then sign in or create an account. | The visitor is prompted for an account and returns to the selected post after authentication if that post remains available; full details are not shown to the guest. |
| 15 | ☐ | Open a guest-selected post that becomes unavailable during authentication. | The unavailable post is not exposed; the account flow uses its established fallback destination. |

## 6. Open Items to Resolve

**None**.
