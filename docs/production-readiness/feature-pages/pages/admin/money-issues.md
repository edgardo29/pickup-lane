# F50 — Money Issues

## 1. Existing Route(s)

- `/admin/money/issues`

The page accepts `status` and `user_id` in its link, for example from
[User Money](user-money.md).

## 2. Purpose

Money Issues is the staff queue for refunds and credit returns that Pickup Lane
could not complete or verify without staff review. Staff find an issue here and
work it on [Money Issue Detail](money-issue-detail.md). It is not a payment
ledger or a general support inbox.

## 3. Main Functionality

### 3.1. Status Views

- **Open:** issues still needing staff attention (default).
- **Resolved:** issues staff have closed.
- **All:** every issue.

### 3.2. Search and Filter

Staff can search by issue ID, operation key, user name, or user email, and filter
by issue type:

- Refund missing Stripe reference
- Refund processing overdue
- Refund failed
- Refund cancelled
- Refund outcome unknown
- Credit restore failed
- Credit release failed

**Search** applies the search and filter. A user filter opened from another page
appears as a removable chip.

### 3.3. Issue Rows

Each row shows the problem, affected amount, origin workflow, user, game or
record context, recommended action, and latest activity time. Selecting a row
opens Money Issue Detail.

### 3.4. Load More

Issues load in batches of 50. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. What Creates an Issue

Issues are created automatically when a refund fails, is cancelled, cannot be
sent because the Stripe charge reference is missing, stays processing too long,
or has an unknown outcome, and when restoring or releasing game credit fails.
Successful refunds and credit movements never create issues. Official game
cancellation creates one issue per unresolved refund or credit, not a combined
issue.

### 4.2. One Issue per Obligation

Each refund or credit movement has at most one issue. If a resolved problem
happens again, the same issue reopens instead of creating a new one.

### 4.3. Ordering

Open lists the oldest detected issues first. Resolved lists the most recently
resolved first. All lists the most recent activity first.

### 4.4. Focused Search

Search looks up issues by their identifiers or by user. It does not search
amounts, games, venues, or event history; related records are reached from
Payments, Refunds, Credits, or User Money.

### 4.5. Recorded Viewing

Issue rows are recorded as sensitive admin views when shown. See
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Money Issues. | Open issues appear, oldest detected first, with problem, amount, context, and recommended action. |
| 2 | ☐ | Switch to Resolved and All. | Resolved shows the most recently resolved first; All shows the most recent activity first. |
| 3 | ☐ | Filter by each issue type. | Only issues of that type appear. |
| 4 | ☐ | Search by issue ID, operation key, and user email. | The matching issues appear. |
| 5 | ☐ | Open the page from User Money's open-issue link. | Only that user's open issues appear, and the user filter shows as a removable chip. |
| 6 | ☐ | Remove the user chip. | Issues for all users appear. |
| 7 | ☐ | Load more than 50 issues. | The next issues append without duplicates. |
| 8 | ☐ | Fail a refund during an official game cancellation. | One open Refund failed issue appears for that refund. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | The same refund fails again after its issue was resolved. | The existing issue reopens; no second issue is created. |
| 10 | ☐ | Search for a game title or amount. | No broad text match is performed. |
| 11 | ☐ | Apply filters with no matches. | "No money issues found" appears. |
| 12 | ☐ | Fail the first load or Load More. | An error appears; loaded rows stay visible after a Load More failure. |
| 13 | ☐ | Open the page when the admin view cannot be recorded. | Issue rows are not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
