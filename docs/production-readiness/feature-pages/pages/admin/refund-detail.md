# F47 — Refund Detail

## 1. Existing Route(s)

- `/admin/money/refunds/:refundId`

## 2. Purpose

Refund Detail shows staff the current state and history of one refund, the
payment and purchase it belongs to, related credits, and any linked money issue.
When the backend allows it, staff can retry a failed refund or ask Pickup Lane to
check the refund's status with Stripe.

## 3. Main Functionality

### 3.1. Refund Summary

Shows the amount, status, reason, and Stripe status, plus the refund, payment,
booking, participant, publish-fee, Stripe refund, and Stripe charge references;
the origin; and request, approval, refund, latest event, attempt, creation, and
update times.

### 3.2. Context and Credits

Shows the related payment, booking, game, user, participant, and publish fee, and
any credits restored, released, or issued in connection with the refund.

### 3.3. Retry Refund

When the refund can be retried, staff enter a required reason of up to 1,000
characters and retry.

### 3.4. Check Stripe Status

When the refund's Stripe result may be outdated or unknown, staff enter a
required reason of up to 1,000 characters and ask Pickup Lane to check Stripe.
If no Stripe refund reference is recorded, staff can also enter one.

### 3.5. History and Follow-Up

- **Refund Events:** recent Stripe and refund status history.
- **Money Issues:** the linked money issue, if any, with a link to
  [Money Issue Detail](money-issue-detail.md).
- **Admin Actions:** broader admin actions on the refund, when any exist.

### 3.6. Navigation

**Back** returns to the refund's [Payment Detail](payment-detail.md) when the
refund has an associated payment, and to [Refunds](refunds.md) otherwise.
**Refresh** reloads the refund.

## 4. Important Behavior & Decisions

### 4.1. The Backend Decides Eligibility

The backend decides when each action is available, and the page shows only
available actions. Retry is generally available for failed or cancelled refunds
on a collected payment with a Stripe charge reference and a refundable amount
remaining, when Stripe's result is not still uncertain. Status checks are
generally available while a refund is processing or its result is unknown or
possibly outdated.

### 4.2. Recorded Results Only

A refund's status changes only after Pickup Lane records Stripe's result.
Resolving a money issue closes staff follow-up only and does not change the
refund.

### 4.3. Safe, Single Actions

Both actions require recent identity confirmation. The backend re-checks the
refund and payment before calling Stripe. Repeating the same request returns the
original result without calling Stripe again or recording duplicate events. Retry
is the same action offered on Money Issue Detail.

### 4.4. Retry Results

A successful retry marks the refund succeeded. A failed or cancelled retry
updates the refund and its money issue. A processing result keeps the refund
processing and keeps any open issue open while Stripe finishes.

### 4.5. Safe Data and Recorded Viewing

Raw Stripe data and secrets are never shown. Opening the refund and its event
history is recorded as a sensitive admin view; see
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a succeeded refund. | The summary, context, events, and credits appear, and no retry or status check is offered. |
| 2 | ☐ | Open a failed refund with a Stripe charge reference. | Retry Refund is offered. |
| 3 | ☐ | Retry it with a reason after confirming identity, and Stripe succeeds. | The refund becomes succeeded, a new event appears, and the linked issue stays open for staff resolution. |
| 4 | ☐ | Open a processing refund and check Stripe status. | The refund updates to Stripe's recorded result and the check appears in its history. |
| 5 | ☐ | Check status on a refund with no Stripe refund reference, entering one. | Pickup Lane checks Stripe using the entered reference. |
| 6 | ☐ | Select the linked money issue. | Money Issue Detail opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Open a failed refund missing its Stripe charge reference. | Retry Refund is not offered. |
| 8 | ☐ | Submit a retry or status check without a reason. | The action does not run. |
| 9 | ☐ | Retry a refund that fails again. | The refund stays failed and its money issue updates. |
| 10 | ☐ | Retry and receive a processing result. | The refund shows processing and no new money issue is created. |
| 11 | ☐ | Submit the same retry twice. | Stripe is called once. |
| 12 | ☐ | Decline identity confirmation. | Nothing changes. |
| 13 | ☐ | Open a refund that does not exist. | A not-found error appears. |
| 14 | ☐ | Open the page when the admin view cannot be recorded. | Refund details are not shown and an error appears. |
| 15 | ☐ | Select Back from a refund with an associated payment and from one without. | The first returns to that payment's Payment Detail; the second returns to Refunds. |

## 6. Open Items to Resolve

**None**.
