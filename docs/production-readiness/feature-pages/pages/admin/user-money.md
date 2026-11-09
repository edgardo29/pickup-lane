# F43 — User Money

## 1. Existing Route(s)

- `/admin/money/users` (find a user)
- `/admin/money/users/:userId` (user money snapshot)

## 2. Purpose

User Money is the starting point when money support begins with a person rather
than a payment or refund ID. Staff find the user, see their current credit and
open money issues, check saved cards, and jump to their recent payments, refunds,
and credits. It is read-only and summarizes other money pages instead of
replacing them.

## 3. Main Functionality

### 3.1. Find a User

Without a selected user, the page offers a user search. Results show up to five
users with name, email, account status, role, hosting status, and member-since
date. Selecting a user opens their snapshot. **More in User Directory** opens
[User Directory](user-directory.md) for wider searches.

### 3.2. User

Shows the user's name, email, account status, and user ID, with a link to
[User Detail](user-detail.md).

### 3.3. Snapshot

Shows available game credit in US dollars and the number of open money issues.

### 3.4. Open Money Issues

Shows up to five open issues, oldest first, with the problem, amount, and
recommended action, and links to [Money Issue Detail](money-issue-detail.md) and
the user's open issues in [Money Issues](money-issues.md).

### 3.5. Saved Cards

Shows active saved cards by default, up to ten at a time, with brand, last four
digits, expiration, status, default card, and created, updated, or detached
times. **Include inactive saved cards** adds inactive and detached cards after
active ones. **Load More Saved Cards** shows more.

### 3.6. Recent Payments, Refunds, and Credits

Each section shows up to five recent records with links to their detail pages
and a **View all** link to [Payments](payments.md), [Refunds](refunds.md), or
[Credits](credits.md) filtered to this user.

## 4. Important Behavior & Decisions

### 4.1. Read-Only Summary

User Money has no money actions and owns no money records. Work happens on the
detail pages it links to. There is no separate saved-card admin page.

### 4.2. Available Credit

Available credit is the total spendable value of the user's active credits.
Credit reserved by a checkout in progress is not counted as available.

### 4.3. Safe Card Data

Only safe card details are shown: brand, last four digits, expiration, status,
and default flag. Stripe customer and payment method identifiers and card
fingerprints are never shown.

### 4.4. Deleted Users and Recorded Viewing

A deleted user's money snapshot can still be opened for support history. Opening
a snapshot is recorded as a sensitive admin view; see
[Admin Action Log](admin-action-log.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open User Money and search for a user by email. | Up to five matching users appear; selecting one opens the snapshot. |
| 2 | ☐ | Open User Money from User Detail. | That user's snapshot opens directly. |
| 3 | ☐ | View a user with active credits and an open money issue. | The snapshot shows the available credit and one open issue, and the issue appears in Open Money Issues. |
| 4 | ☐ | Turn on Include inactive saved cards. | Inactive and detached cards appear after active cards. |
| 5 | ☐ | Select View all in each recent section. | The matching money list opens filtered to this user. |
| 6 | ☐ | Select User Detail. | The user's User Detail opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | View a user whose only credit is fully reserved by a checkout. | Available credit shows zero. |
| 8 | ☐ | View a user with more than ten saved cards. | Load More Saved Cards shows the remaining cards. |
| 9 | ☐ | View a user with no money history. | The snapshot shows zero values and each section shows an empty state. |
| 10 | ☐ | Search with no matching users. | "No users found" appears. |
| 11 | ☐ | Open the snapshot for a deleted user. | The snapshot loads for support history. |
| 12 | ☐ | Inspect saved cards for restricted data. | No Stripe identifiers or card fingerprints appear. |
| 13 | ☐ | Open a user that does not exist. | A not-found error appears. |
| 14 | ☐ | Open the page when the admin view cannot be recorded. | The snapshot is not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
