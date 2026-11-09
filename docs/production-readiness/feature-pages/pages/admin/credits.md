# F48 — Credits

## 1. Existing Route(s)

- `/admin/money/credits`

The page accepts user, source game, source booking, and source payment filters in
its link, for example from [User Money](user-money.md).

## 2. Purpose

Credits is a read-only ledger of Pickup Lane game credits. Staff use it to find a
credit grant, see who owns it and how much is available, and open
[Credit Detail](credit-detail.md). Failed credit work is handled in
[Money Issues](money-issues.md).

## 3. Main Functionality

### 3.1. Search and Status

Staff can search by credit ID, credit movement ID, user, source payment, booking,
or game, and filter by status: all, active, used, or reversed. **Search** applies
them. Filters opened from another page appear as removable chips.

### 3.2. Credit Rows

Each row shows the status, available amount, reserved amount when any, user,
game or record context, reason, and creation time. Selecting a row opens Credit
Detail.

### 3.3. Load More

Credits load in batches of 50. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. Credit Statuses

- **Active:** the credit still has available value, or value reserved by a
  checkout in progress.
- **Used:** the credit has been fully spent. A later restore can make it active
  again.
- **Reversed:** the credit was voided and cannot be used again.

### 4.2. Read-Only

The page has no actions to issue, change, or reverse credits.

### 4.3. Recorded Viewing

Credit rows are recorded as sensitive admin views when shown. See
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Credits. | Credits appear with status, available and reserved amounts, user, context, reason, and creation time. |
| 2 | ☐ | Filter by Active, Used, and Reversed. | Only credits in that status appear. |
| 3 | ☐ | Search by credit ID, user email, and source booking. | The matching credits appear. |
| 4 | ☐ | Open the page from User Money's credits link, then remove the chip. | Only that user's credits appear, then all credits return. |
| 5 | ☐ | View a credit partly reserved by a checkout in progress. | The row shows both the available and reserved amounts. |
| 6 | ☐ | Load more than 50 credits and select one. | The next credits append without duplicates, and Credit Detail opens for the selected credit. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Search with no matches. | "No money credits found" appears. |
| 8 | ☐ | Fail the first load or Load More. | An error appears; loaded rows stay visible after a Load More failure. |
| 9 | ☐ | Open the page when the admin view cannot be recorded. | Credit rows are not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
