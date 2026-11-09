# F39 — User Directory

## 1. Existing Route(s)

- `/admin/users`

`/admin/staff` redirects to `/admin/users?role=admin`, which opens the Admins
view of this page.

## 2. Purpose

User Directory lets staff find the right Pickup Lane account before opening its
support detail. It shows safe account facts only and is the starting point for
account, hosting, and staff-related support work.

## 3. Main Functionality

### 3.1. All Users and Admins Views

**All users** lists every non-deleted account. **Admins** shows only accounts
with the admin role. Switching views keeps the other filters.

### 3.2. Search and Filters

Staff can search by name, email, phone number, or user ID and filter by:

- **Account:** all accounts, active, suspended, pending deletion, or deleted.
- **Hosting:** all hosting, not eligible, eligible, or restricted.

**Search** applies the search text and filters. **Reset** clears them while
keeping the current view. The applied view, search, and filters are part of the
page link.

### 3.3. User Cards

Each card shows the full name, email, role, account status, hosting status, and
member-since date. Selecting a card opens [User Detail](user-detail.md).

### 3.4. Load More

Results load in batches of 50. **Load More** adds the next batch.

## 4. Important Behavior & Decisions

### 4.1. Safe Account Facts Only

The directory never shows sign-in provider identifiers, payment or card details,
full birth dates, private settings, profile photos, or money information.

### 4.2. Deleted Accounts

Deleted accounts are hidden unless the **Deleted** account filter is chosen.
Deleted accounts appear with their personal details removed.

### 4.3. Staff Are Users

There is no separate staff list. Staff are found through the Admins view of the
directory. Admin access itself follows
[Admin Sign In](../authentication/admin-sign-in.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open User Directory. | The All users view lists non-deleted accounts with name, email, role, account status, hosting status, and member-since date. |
| 2 | ☐ | Search by name, email, phone number, and user ID. | Each search returns the matching account. |
| 3 | ☐ | Filter by each account status and hosting status. | Only matching accounts appear. |
| 4 | ☐ | Switch to Admins. | Only admin accounts appear, and the link shows the admin role filter. |
| 5 | ☐ | Open `/admin/staff`. | The Admins view opens. |
| 6 | ☐ | Apply filters, then reload or share the link. | The same view, search, and filters are restored. |
| 7 | ☐ | Select Reset. | Search and filters clear; the current view stays selected. |
| 8 | ☐ | Load more than 50 accounts. | The next accounts append without duplicates. |
| 9 | ☐ | Select a user card. | That user's User Detail opens. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 10 | ☐ | Search for a deleted user without the Deleted filter. | The deleted user is not listed. |
| 11 | ☐ | Choose the Deleted filter. | Deleted accounts appear with personal details removed. |
| 12 | ☐ | Search with no matches. | "No users found" appears with no Load More control. |
| 13 | ☐ | Fail the first load or Load More. | An error appears; already loaded cards stay visible after a Load More failure. |
| 14 | ☐ | Inspect cards and responses for restricted data. | No provider IDs, payment details, full birth date, private settings, photos, or money data appear. |
| 15 | ☐ | Open the page as a player or suspended admin. | Accounts are not shown; access follows Admin Sign In. |

## 6. Open Items to Resolve

**None**.
