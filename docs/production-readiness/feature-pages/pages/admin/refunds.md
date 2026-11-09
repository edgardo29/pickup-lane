# F46 — Refunds

## 1. Existing Route(s)

- `/admin/money/refunds`

The page accepts `user_id` and `payment_id` in its link, for example from
[User Money](user-money.md).

## 2. Purpose

Refunds is the ledger of money Pickup Lane owes back or has returned. Staff use it
to find a refund and open [Refund Detail](refund-detail.md), where its Stripe
history and available actions live.

## 3. Main Functionality

### 3.1. Search and Status

Staff can search by refund ID, Stripe refund or charge ID, payment ID, booking
ID, participant ID, publish-fee ID, user ID, or user name or email, and filter by
status: all, pending, approved, processing, succeeded, failed, or cancelled.
**Search** applies them. User or payment filters opened from another page appear
as removable chips.

### 3.2. Refund Rows

Each row shows the refund's status, amount, user, and context. Selecting a row
opens Refund Detail.

### 3.3. Load More

Refunds load newest first in batches of 50. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. Refund Statuses

A refund is pending, approved, processing, succeeded, failed, or cancelled.
Failed means the refund could not complete, whether Stripe failed it or Pickup
Lane could not safely send it. Problems needing staff action appear in
[Money Issues](money-issues.md), not as separate refund statuses.

### 4.2. Focused Search and Safe Data

Search uses exact identifiers or the user's name or email; it does not search
reasons, amounts, games, venues, or event history. Raw Stripe data and secrets
are never shown.

### 4.3. Recorded Viewing

Refund rows are recorded as sensitive admin views when shown. See
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Refunds. | All refunds appear newest first with status, amount, user, and context. |
| 2 | ☐ | Filter by each status. | Only refunds in that status appear. |
| 3 | ☐ | Search by refund ID, Stripe refund ID, payment ID, and user email. | The matching refunds appear. |
| 4 | ☐ | Open the page with a payment filter, then remove the chip. | Only that payment's refunds appear, then all refunds return. |
| 5 | ☐ | Load more than 50 refunds. | The next refunds append without duplicates. |
| 6 | ☐ | Select a row. | Refund Detail opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Search with no matches. | "No money refunds found" appears. |
| 8 | ☐ | Search for a refund reason or amount. | No broad text match is performed. |
| 9 | ☐ | Fail the first load or Load More. | An error appears; loaded rows stay visible after a Load More failure. |
| 10 | ☐ | Open the page when the admin view cannot be recorded. | Refund rows are not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
