# F45 — Payment Detail

## 1. Existing Route(s)

- `/admin/money/payments/:paymentId`

## 2. Purpose

Payment Detail shows staff everything Pickup Lane knows about one collected or
attempted payment: who paid, for what, its collection status, and the refunds,
credits, and money issues connected to it. It is read-only.

## 3. Main Functionality

### 3.1. Payment Summary

Shows the amount, collection status, payment type, and refund state (whether it
was fully refunded), plus the payment ID, payer name and email, payer, booking,
and game references, Stripe payment and charge references, payment service,
paid, created, and updated times, and any failure code or message.

### 3.2. Purchase Context

Shows what the payment was for: the booking, participant, and game for booking
payments; the publish fee, publish attempt, community game, and host for publish
fees; or the related admin action for admin charges. Context that does not apply
is not shown.

### 3.3. Refunds, Credits, and Money Issues

- **Refunds:** each related refund with amount, status, reason, date, and a link
  to [Refund Detail](refund-detail.md).
- **Credits:** credit reserved, redeemed, or released with this payment, and
  credits issued because of it, with links to
  [Credit Detail](credit-detail.md).
- **Money Issues:** linked issues with links to
  [Money Issue Detail](money-issue-detail.md).
- **Admin Actions:** related admin actions, when any exist.

### 3.4. Navigation

**Back** returns to [Official Game Manage](official-game-manage.md) when the
payment belongs to an official game, and to [Payments](payments.md) otherwise.
**Refresh** reloads the payment.

## 4. Important Behavior & Decisions

### 4.1. Read-Only

The page has no actions. Refund retries happen on Refund Detail or Money Issue
Detail.

### 4.2. Collection Status and Refunds

The status shows collection only and stays **Succeeded** after refunds. The
refund state shows whether succeeded refunds cover the full amount; partial
refund details are on the refunds themselves.

### 4.3. Safe Data and Recorded Viewing

Raw Stripe data, customer and card identifiers, and secrets are never shown.
Opening a payment is recorded as a sensitive admin view; see
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a succeeded booking payment. | The summary, booking and game context, and any refunds and credits appear. |
| 2 | ☐ | Open a community publish-fee payment. | The publish fee, community game, and host context appear instead of booking context. |
| 3 | ☐ | Open a fully refunded payment. | The status stays Succeeded and the refund state shows fully refunded. |
| 4 | ☐ | Open a partially refunded payment. | The refund state shows not fully refunded and the refunds section lists the partial refund. |
| 5 | ☐ | Open a payment paid partly with credit. | The credits section shows the credit reserved and redeemed. |
| 6 | ☐ | Select a refund, credit, or money issue link. | The matching detail page opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Open a failed payment. | The failure code or message appears and no paid time is shown. |
| 8 | ☐ | Open a payment with no refunds, credits, or issues. | Those sections show empty states without errors. |
| 9 | ☐ | Inspect the page for restricted data. | No raw Stripe data, customer or card identifiers, or secrets appear. |
| 10 | ☐ | Open a payment that does not exist. | A not-found error appears. |
| 11 | ☐ | Open the page when the admin view cannot be recorded. | Payment details are not shown and an error appears. |
| 12 | ☐ | Select Back from an official game payment and from a community publish-fee payment. | The first returns to that game's Official Game Manage; the second returns to Payments. |

## 6. Open Items to Resolve

**None**.
