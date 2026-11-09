# F44 — Payments

## 1. Existing Route(s)

- `/admin/money/payments`

The page accepts `user_id` in its link, for example from
[User Money](user-money.md).

## 2. Purpose

Payments is a read-only ledger of money Pickup Lane tried to collect. Staff use
it to find a payment, see who was charged and for what, and open
[Payment Detail](payment-detail.md). Refunds, credits, and staff follow-up are
handled on their own pages.

## 3. Main Functionality

### 3.1. Search and Filters

Staff can search by payment ID, Stripe payment or charge ID, user ID, payer name
or email, booking ID, game ID, or publish-fee ID, and filter by:

- **Status:** all, requires payment method, succeeded, processing, requires
  action, failed, or canceled.
- **Payment type:** any type, booking, community publish fee, or admin charge.

**Search** applies the search and filters. A user filter opened from another page
appears as a removable chip.

### 3.2. Payment Rows

Each row shows the collection status, amount, payer, game or record context,
payment type, and paid time (or creation time if not paid). Selecting a row opens
Payment Detail.

### 3.3. Load More

Payments load newest first in batches of 50. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. Collection Status Only

A payment's status describes collection only. A collected payment stays
**Succeeded** even after a partial or full refund; refunds are separate records.

### 4.2. Payment Types

Payments are bookings, community publish fees, or admin charges. The page offers
no action to create, change, or refund a payment.

### 4.3. Focused Search and Safe Data

Search uses exact identifiers or the payer's name or email; it does not search
amounts, failure text, game titles, or venues. The page never shows raw Stripe
data, customer or card identifiers, or secrets.

### 4.4. Recorded Viewing

Payment rows are recorded as sensitive admin views when shown. See
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Payments. | All payments appear newest first with status, amount, payer, context, type, and time. |
| 2 | ☐ | Filter by each status and payment type. | Only matching payments appear. |
| 3 | ☐ | Search by payment ID, Stripe charge ID, booking ID, and payer email. | The matching payments appear. |
| 4 | ☐ | Open the page from User Money's payments link, then remove the user chip. | Only that user's payments appear, then all payments return. |
| 5 | ☐ | View a payment that was fully refunded. | Its status remains Succeeded. |
| 6 | ☐ | Load more than 50 payments. | The next payments append without duplicates. |
| 7 | ☐ | Select a row. | Payment Detail opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 8 | ☐ | Search with no matches. | "No money payments found" appears. |
| 9 | ☐ | Search for a game title or amount. | No broad text match is performed. |
| 10 | ☐ | Inspect rows for restricted data. | No raw Stripe data, customer or card identifiers, or secrets appear. |
| 11 | ☐ | Fail the first load or Load More. | An error appears; loaded rows stay visible after a Load More failure. |
| 12 | ☐ | Open the page when the admin view cannot be recorded. | Payment rows are not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
