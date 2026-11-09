# F27 — Admin Action Log

## 1. Existing Route(s)

- `/admin/audit`

## 2. Purpose

Admin Action Log is the global history of what staff have done across Pickup
Lane. Staff use it to investigate support questions, mistakes, and sensitive
changes across users, games, posts, money records, and notices. It is
read-only.

## 3. Main Functionality

### 3.1. Recent Actions

The page opens with the most recent recorded admin actions, newest first, in
batches of 50. **Load More** adds the next batch. Each row shows:

- The action, in plain language.
- The admin who performed it and the main record it affected.
- A preview of the reason, when one was given.
- The time.

### 3.2. Filters

- **Admin:** type at least three characters to search current and former
  administrators with recorded actions by name or email, then choose one.
  Former administrators are clearly identified. Clearing the selection
  removes the filter.
- **Action type:** choose one action from a list of readable action names, or
  **All actions**.

Changing a filter reloads the list from the beginning.

### 3.3. Action Detail

Selecting a row opens a read-only detail window with the action name, admin,
admin email when available, time, reason when present, and the affected
record's type and name. When the record has an admin page, **Open admin page**
goes there. Closing the window returns to the same place in the list.

## 4. Important Behavior & Decisions

### 4.1. What the Log Contains

The log contains successful admin actions that were recorded. It includes
changes such as cancellations, refunds, suspensions, administrator access
changes, deletion-failure resolutions, and notice publication, and recorded
sensitive views such as opening review cases, money
records, and revealed chat messages. Rejected or failed attempts are not shown.

### 4.2. Sensitive Views Are Recorded First

Admin pages that show sensitive information record the view in this log before
the information is displayed. If the view cannot be recorded, the information
is not shown and the page reports an error. Pages that follow this rule
reference this section.

### 4.3. Operational Display

The log shows readable names instead of raw identifiers, technical keys, or raw
data. A former administrator remains identifiable in the filter and action
history without regaining administrative access. When the affected record no longer exists, the row still appears with a
fallback label of the record type and its identifier.

### 4.4. No Date Filter or Totals

There is no date filter, page-size choice, or total count. History is reached
by loading more rows.

### 4.5. Records Cannot Be Changed

Entries cannot be edited, deleted, or added from this page.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Admin Action Log. | Recent admin actions load newest first without a row being selected. |
| 2 | ☐ | View a row with and without a reason. | Each row shows the readable action, admin, affected record, and time; a reason preview appears only when a reason exists. |
| 3 | ☐ | Search for an admin with three or more characters and select one. | Only that admin's actions appear and the list restarts from the first batch. |
| 4 | ☐ | Clear the selected admin. | Actions from all admins appear again. |
| 5 | ☐ | Choose an action type. | Only that action type appears; the options use readable names sorted alphabetically. |
| 6 | ☐ | Load more than 50 actions. | The next actions append in order without duplicates. |
| 7 | ☐ | Select a row. | A read-only detail window shows only populated fields and offers a link to the affected record's admin page when one exists. |
| 8 | ☐ | Close the detail window. | The list remains at the same position. |
| 9 | ☐ | Open a sensitive admin record, then return to the log. | A matching recorded view appears for that admin and record. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 10 | ☐ | Type fewer than three characters in the Admin search. | No admin search runs. |
| 11 | ☐ | Search for an admin name with no current or former match among recorded actors. | "No matching admins found" appears and the filter is unchanged. |
| 12 | ☐ | View an action whose affected record was deleted. | The row and detail still appear with a fallback record label. |
| 13 | ☐ | Apply filters with no matching actions. | "No admin actions found" appears with no Load More control. |
| 14 | ☐ | Several actions share the same time. | Their order is stable across batches without duplicates or gaps. |
| 15 | ☐ | Change a filter while a request is pending. | A late response for the earlier filter does not change the list. |
| 16 | ☐ | Fail the list or detail request. | An error appears; the page does not show stale or partial detail. |
| 17 | ☐ | Attempt an admin action that is rejected. | No entry for the rejected attempt appears. |
| 18 | ☐ | Inspect rows and detail. | No raw identifiers, technical keys, or raw data are shown as primary content. |
| 19 | ☐ | Search for and select a former administrator with recorded actions. | The former administrator is labeled as former, their actions can be isolated, and the filter does not restore admin access. |
| 20 | ☐ | Grant or revoke administrator access, or resolve a deletion-failure issue, from User Detail. | Each completed action appears with its actor, affected account, decision or access change, reason where required, and time; rejected attempts do not appear as successful changes. |

## 6. Open Items to Resolve

**None**.
