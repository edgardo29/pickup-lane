# F51 — Money Issue Detail

## 1. Existing Route(s)

- `/admin/money/issues/:moneyIssueId`

## 2. Purpose

Money Issue Detail lets staff understand one unresolved refund or credit problem,
retry it when it is safe, and close the issue with a documented resolution.
Resolving closes staff follow-up only; it never rewrites the payment, refund,
or credit records.

## 3. Main Functionality

### 3.1. Issue Summary

Shows the issue type, status, affected amount, recommended action, origin,
reason, summary, related user, game, booking, payment, refund, credit, and credit
movement, occurrence and reopen counts, detection and activity times, and the
resolution details once resolved. **Back** returns to
[Money Issues](money-issues.md); **Refresh** reloads the issue.

### 3.2. Related Records and History

Below the summary, the page shows the current refund, payment, credit, and credit
movements involved, the booking and game context, the refund's recent Stripe
events when the issue is refund-related, and the issue's own event history.

### 3.3. Retry

When the issue can be retried, a **Retry Refund** or **Retry Credit** form asks
for a required reason of up to 1,000 characters.

- **Retry Refund** appears for an open refund issue whose recommended action is
  retry, when the refund is failed or cancelled and Stripe's result is not still
  processing or unknown.
- **Retry Credit** appears for an open failed credit restore or release.

### 3.4. Resolve Issue

While the issue is open, staff choose a resolution:

- **Retried Successfully**
- **Stripe Completed**
- **Handled Externally:** requires a note and an external reference.
- **Invalid Issue:** requires a note.
- **Unable To Complete:** requires a note.

## 4. Important Behavior & Decisions

### 4.1. Resolution Must Match the Records

- **Retried Successfully** requires a refund that succeeded or a credit movement
  that succeeded after retry.
- **Stripe Completed** requires refund records confirming the payment obligation
  is satisfied.
- Other resolutions require the explanation described above.

Resolving does not change any payment, refund, or credit record.

### 4.2. Retry Safety

Retries require recent identity confirmation. The backend re-checks the current
refund or credit state before acting. A refund retry is the same action offered
on [Refund Detail](refund-detail.md). The backend decides whether a credit retry
restores or releases credit; staff cannot choose a different credit movement.

### 4.3. Retry Results

A successful retry updates the refund or credit record, but the issue stays open
until staff resolve it. A retry that fails again keeps the issue open with
updated details. A retry that returns processing keeps the issue open while
Stripe finishes.

### 4.4. Resolving and Reopening

Resolving requires recent identity confirmation and is only possible while the
issue is open. If the same problem is detected again later, the issue reopens,
its resolution is cleared, and its reopen count increases.

### 4.5. Repeated Requests and Recorded Viewing

Repeating the same retry or resolution does not call Stripe again, repeat a
credit movement, or record a duplicate event. Opening the issue is recorded as a
sensitive admin view; see [Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a failed refund issue. | The summary shows the problem, amount, related records, and recommended retry, and Retry Refund is offered. |
| 2 | ☐ | Retry the refund with a reason after confirming identity, and Stripe succeeds. | The refund becomes succeeded and the issue stays open. |
| 3 | ☐ | Resolve that issue as Retried Successfully. | The issue becomes resolved with the reason, resolver, and time. |
| 4 | ☐ | Retry a failed credit restore. | Credit is restored once and the issue can then be resolved as Retried Successfully. |
| 5 | ☐ | Resolve an issue as Handled Externally with a note and reference. | The issue is resolved and shows the note and reference; payment, refund, and credit records are unchanged. |
| 6 | ☐ | Resolve an issue as Stripe Completed after Stripe confirms the refund. | The issue is resolved. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Resolve as Handled Externally without a note or reference. | The form reports what is missing and nothing is resolved. |
| 8 | ☐ | Resolve as Invalid Issue or Unable To Complete without a note. | The form reports the missing note. |
| 9 | ☐ | Resolve as Retried Successfully when the refund or credit has not succeeded. | Resolution is rejected. |
| 10 | ☐ | Open a refund issue whose Stripe result is processing or unknown. | Retry Refund is not offered. |
| 11 | ☐ | Retry a refund that fails again. | The refund stays failed, the issue stays open, and its details update. |
| 12 | ☐ | Submit the same retry twice. | Stripe is called once and only one result is recorded. |
| 13 | ☐ | Open a resolved issue. | No retry or resolve form is offered. |
| 14 | ☐ | Decline identity confirmation when retrying or resolving. | Nothing changes. |
| 15 | ☐ | Open an issue that does not exist. | A not-found error appears. |
| 16 | ☐ | Open the page when the admin view cannot be recorded. | Issue details are not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
