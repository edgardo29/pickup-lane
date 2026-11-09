# F19 — My Games

## 1. Existing Route(s)

- `/my-games`

## 2. Purpose

My Games lets a signed-in player find games they host or joined and outside-game substitute posts they own or were confirmed for. It is a personal activity view; [Browse Games](../public/browse-games.md) and [Need a Sub](../public/need-a-sub.md) own public discovery.

## 3. Main Functionality

### 3.1. Switch Activity Views

- Choose **Games** or **Need a Sub**, then **Upcoming** or **History** within that area. Games/Upcoming opens first.
- Each view groups cards by scheduled date. Upcoming runs earliest first; History runs newest first. Each view loads in batches with **Load More**.

### 3.2. Open Connected Items

- Game cards show type, venue, time, location, format, spots, price, and relevant hosting or cancellation status, and link to [Game Details](../public/game-details.md).
- Need a Sub cards show the outside game, sub needs, confirmed/open counts, and owner or cancellation status. A card links to [Post Detail](../public/need-a-sub-post-detail.md) only while that detail is accessible.

## 4. Important Behavior & Decisions

### 4.1. Personal Eligibility

Only owned/hosted items and confirmed participation qualify. Pending, waitlisted, payment-failed, declined, guest-only, or other tentative relationships do not. Hidden qualifying items remain visible here; removed items do not. This personal view does not use the public Browse listing rules.

### 4.2. Upcoming and History

An active item stays Upcoming until its scheduled end, including while its game is in progress. A qualifying cancelled item moves to History immediately. History covers the last 60 days based on scheduled end, including a cancelled item's scheduled end rather than cancellation time. Cancelled-player history requires proof that the player was confirmed when the game or post was cancelled. The backend decides eligibility; the page preserves separate loading and pagination state for each view.

### 4.3. Loading and Access

Private activity requires sign-in. A suspended player can still find existing hosted and confirmed commitments here for permitted fulfillment or withdrawal; suspension alone does not move or cancel their cards. New participation restrictions are owned by [User Detail](../admin/user-detail.md#410-suspended-player-experience). Each view has its own loading, empty, error, and Load More states. A failed later batch leaves earlier cards visible for retry; late results from another view or account cannot replace the active view. An inaccessible Need a Sub historical detail remains visible as a non-link card.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open My Games with hosted, joined, owned-sub-post, and confirmed-sub activity. | Games/Upcoming opens first; switching areas and views shows only the matching personal items. |
| 2 | ☐ | Open a game or accessible Need a Sub card. | Its corresponding detail page opens; an inaccessible historical post card is not linked. |
| 3 | ☐ | View multiple dates and more than 40 items. | Cards group by scheduled date, follow each view's time order, and Load More appends later items without duplicates. |
| 4 | ☐ | View hosted and confirmed activity alongside pending or waitlisted activity. | Hosted/owned and confirmed items appear; tentative relationships alone do not. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 5 | ☐ | Keep an item open through its start and scheduled end. | It remains Upcoming while in progress and moves to History after its scheduled end. |
| 6 | ☐ | Cancel an upcoming game or post with confirmed participants. | The owner and qualifying confirmed participants see it in History immediately; waitlisted-only users do not. |
| 7 | ☐ | View a hidden, removed, or soft-deleted connected item. | A hidden qualifying item remains listed; a removed item is excluded. |
| 8 | ☐ | Cross the 60-day history boundary. | Items within the scheduled-end window remain; older ones are absent, including cancelled items. |
| 9 | ☐ | Switch areas or views while requests are pending. | The new view loads independently; late responses and old cursors do not contaminate its results. |
| 10 | ☐ | Fail an initial request, then retry. | A view-specific error appears and a successful retry shows that view's items or empty state. |
| 11 | ☐ | Fail Load More, then retry. | Existing cards stay visible and retry adds the next batch without duplicates. |
| 12 | ☐ | Open the page signed out or with another account after switching users. | Sign-in is required; the previous account's private cards are not shown to the next user. |
| 13 | ☐ | Open My Games after suspension with existing hosted and confirmed activity. | The same qualifying commitments remain accessible for permitted follow-up or withdrawal; no item moves to History solely because of suspension. |

## 6. Open Items to Resolve

**None**.
