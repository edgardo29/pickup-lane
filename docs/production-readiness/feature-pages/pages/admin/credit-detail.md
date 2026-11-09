# F49 — Credit Detail

## 1. Existing Route(s)

- `/admin/money/credits/:creditId`

## 2. Purpose

Credit Detail shows staff one game credit grant: how much was issued, how much is
available or reserved, why it exists, and every movement of its value. It is
read-only.

## 3. Main Functionality

### 3.1. Credit Summary

Shows the original amount, available amount, reserved amount, status, and reason,
plus the credit, owner, source game, source booking, and source payment
references, who issued or reversed it, any note, and the reversal, creation, and
update times.

### 3.2. Usage Ledger

Lists each movement of the credit's value: reserved, redeemed, or released by a
checkout; restored after a cancellation or refund; or reversed.

### 3.3. Related Records

- **Payments** and **Refunds** connected to the credit, with links to
  [Payment Detail](payment-detail.md) and [Refund Detail](refund-detail.md).
- **Context:** the related booking and game.
- **Money Issues:** linked issues, with links to
  [Money Issue Detail](money-issue-detail.md).
- **Admin Actions:** related admin actions, when any exist.

## 4. Important Behavior & Decisions

### 4.1. Ledger Truth

The credit's balances and status come from its recorded movements. Failed
restores or releases do not appear here as movements; they appear as linked money
issues until a retry succeeds.

### 4.2. Read-Only

The page has no actions to issue, change, or reverse credit.

### 4.3. Recorded Viewing

Opening a credit is recorded as a sensitive admin view. See
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open an active credit partly used at checkout. | The summary shows original, available, and reserved amounts, and the ledger shows the reserve and redeem movements. |
| 2 | ☐ | Open a credit restored after an official game cancellation. | The ledger shows the restore and the source game and booking appear. |
| 3 | ☐ | Open a reversed credit. | The status is Reversed with who reversed it and when, and available value is zero. |
| 4 | ☐ | Open a credit with a failed restore. | The linked money issue appears and no restore movement is shown until a retry succeeds. |
| 5 | ☐ | Select a related payment, refund, or money issue. | The matching detail page opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Open a credit with no related payments, refunds, or issues. | Those sections show empty states without errors. |
| 7 | ☐ | Open a credit that does not exist. | A not-found error appears. |
| 8 | ☐ | Open the page when the admin view cannot be recorded. | Credit details are not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
