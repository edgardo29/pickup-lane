# F37 — Review Cases

## 1. Existing Route(s)

- `/admin/review-cases`

`/admin` opens this page because Review Cases is the first admin workspace
page.

## 2. Purpose

Review Cases is the staff queue for internal moderation review work. Staff use
it to find open cases that still need a decision and to look back at closed
cases. A case is an internal work record; it does not change public content or
notify users by itself.

## 3. Main Functionality

### 3.1. Open and Closed Tabs

The page opens on **Open**. **Closed** shows cases that have already been
closed. Changing the tab reloads the list from the beginning.

### 3.2. Filters

Staff can narrow the list by:

- **Category:** all, content moderation, or chat moderation.
- **Target:** all, community games, or Need a Sub posts.

Changing a filter reloads the list from the beginning.

### 3.3. Case Cards

Each card shows:

- The target type, such as Community Game or Need a Sub Post, with the target's
  current status when it is not active.
- For open cases, the number of active findings and their issue labels. When
  a case has no current findings, earlier issue labels are shown as
  "Previously".
- For closed cases, the total number of findings and the closure outcome.
- The last update time for open cases, or the closing time for closed cases.

Selecting a card opens [Review Case Detail](review-case-detail.md).

### 3.4. Load More

The list loads in batches of 24, newest update first. **Load More** adds the
next batch.

## 4. Important Behavior & Decisions

### 4.1. Two Case States

A case is either open or closed. There is no assignment, claiming, merging, or
per-staff view. Every active admin sees the same queue. Workspace access follows
[Admin Sign In](../authentication/admin-sign-in.md).

### 4.2. Only Actionable Content in Open

Open content-moderation cases appear only while their community game or Need a
Sub post can still be acted on. When the content is cancelled, completed,
expired, removed, or deleted, the case leaves the Open list. Hidden content can
stay open because hiding can be undone. Chat-moderation cases are not filtered
by content state.

### 4.3. Case Creation

Content-moderation cases are created automatically when risky text is found.
There is at most one open content-moderation case per community game and per
Need a Sub post. Staff cannot create cases from this page.

### 4.4. Ordering

Cases are ordered by most recent update. Cases updated at the same time keep a
stable order across batches.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Review Cases as an active admin. | The Open tab is selected and the most recently updated open cases load. |
| 2 | ☐ | Switch to Closed, then back to Open. | Each tab shows only cases in that state, and the list restarts from the first batch. |
| 3 | ☐ | Filter by each category and target. | Only matching cases appear; the list restarts from the first batch. |
| 4 | ☐ | View an open case card with current findings. | The card shows the target type, active finding count, issue labels, and last update time. |
| 5 | ☐ | View an open case whose findings have all cleared. | The card shows earlier issue labels marked as previous. |
| 6 | ☐ | View a closed case card. | The card shows the total finding count, closure outcome, and closing time. |
| 7 | ☐ | Select a case card. | Review Case Detail opens for that case. |
| 8 | ☐ | Load a view with more than 24 cases. | The first 24 appear; Load More adds the next cases in order without duplicates and disappears after the last batch. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | Cancel, complete, expire, remove, or delete the content behind an open content case. | The case no longer appears under Open. |
| 10 | ☐ | Hide the content behind an open content case. | The case can remain under Open. |
| 11 | ☐ | Open a view with no matching cases. | A "No review cases" empty state appears with no Load More control. |
| 12 | ☐ | Fail the first load. | An error message appears and no stale cases are shown. |
| 13 | ☐ | Fail Load More. | Loaded cases stay visible and an error message appears. |
| 14 | ☐ | Change the tab or a filter while a request is pending. | A late response for the earlier view does not replace or extend the current list. |
| 15 | ☐ | Open the page as a player, suspended admin, or signed-out user. | Review cases are not shown; access follows Admin Sign In. |

## 6. Open Items to Resolve

**None**.
