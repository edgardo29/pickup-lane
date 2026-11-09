# F38 — Review Case Detail

## 1. Existing Route(s)

- `/admin/review-cases/:reviewCaseId`

## 2. Purpose

Review Case Detail, titled **Manage Case**, lets staff inspect one internal
review case, record private notes, and close the case with an outcome after
any needed action has been taken on the content. Closing a case records the
review decision; it does not change the content or notify anyone.

## 3. Main Functionality

### 3.1. Case Summary

The summary shows the case type, case status, the target content's current
status, and the last update time. When the target can still be opened, an
**Open game** or **Open post** link goes to the matching admin page:
[Community Game Detail](community-game-detail.md),
[Need a Sub Post (Admin)](need-a-sub-post-detail.md), or
[Need a Sub Request (Admin)](need-a-sub-request-detail.md).

### 3.2. Findings

- **Current Findings** are detected issues that still match the latest saved
  content. Each shows the issue type, the evidence text taken from the user's
  content, and when it was last detected.
- **Previous Findings** were real when detected but no longer match the
  content. Their original evidence is kept.

Chat-moderation cases also show **Current Signals** and **Previous Signals**.

### 3.3. Internal Notes

Staff can add a private note of up to 1,000 characters while the case is open.
The panel shows the latest note and a note count; **View All Notes** opens
every note, newest first, with its author and time.

### 3.4. Close Review

While the case is open, staff choose a closure outcome and enter a required
reason of up to 1,000 characters. The outcomes are:

- **Enforcement applied**, only when a qualifying enforcement action is linked
- **No action needed**
- **Invalid signal**

A case without qualifying enforcement, including a chat-moderation case without such an action, offers only valid outcomes and does not default to **Enforcement applied**. A closed case shows its outcome, reason, and closing time instead of the form.

### 3.5. Timeline

The timeline lists case events: case opened, findings added or cleared,
signals added, enforcement actions linked, notes added, and case closed.

### 3.6. Back

**Back** returns to [Review Cases](review-cases.md).

## 4. Important Behavior & Decisions

### 4.1. Cases Do Not Enforce

Closing a case or adding a note never hides, removes, or changes the content
and never sends a user notification. Enforcement is done on the content's own
admin page.

### 4.2. Enforcement Links

When staff hide, pause, cancel, remove, or hide payment text on content that
has an open content-moderation case, that action is linked to the case
automatically and appears in the timeline. **Enforcement applied** can be
chosen only when a qualifying action has been linked to that case; the backend
also enforces this condition when closing it.

### 4.3. Notes Are Append-Only

Notes are private to admins, cannot be edited or deleted, and are stamped with
their author and server time. A case can hold at most 100 notes. Notes cannot be
added after the case is closed.

### 4.4. Findings Change With the Content

When the content is edited and a finding no longer matches, it moves to
Previous Findings. A clean edit does not close the case; staff still decide.
If the same issue appears again later, it is added as a new current finding.
New findings are never added to a closed case.

### 4.5. Automatic Closure

Content-moderation cases close automatically when the content becomes
non-actionable: owner or host cancellation, completion, or expiration closes
with **No action needed**; admin removal, moderation cancellation, or deletion
closes with **Enforcement applied**.

### 4.6. Concurrent Changes

If the case changed after the page loaded, closing is rejected, the page reloads
the current case, and staff review it before trying again. Repeating the same
submission does not create a duplicate note or closure.

### 4.7. Recorded Viewing

Opening a case is recorded as a sensitive admin view. See
[Admin Action Log](admin-action-log.md).

### 4.8. Unavailable Content

If the target content no longer exists or is deleted, the summary marks it
unavailable and no Open link is shown. The case and its history still display.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open an open content-moderation case. | The summary, current and previous findings, notes, close form, and timeline appear. |
| 2 | ☐ | Select the Open game or Open post link. | The matching admin page for the target content opens. |
| 3 | ☐ | View a current and a previous finding. | Each shows its issue type, evidence from the user's content, and detection time in the correct section. |
| 4 | ☐ | Add a note to an open case. | The note appears as the latest note with author and time, the count increases, and the timeline shows the note event. |
| 5 | ☐ | Open View All Notes. | All notes appear newest first. |
| 6 | ☐ | Close a case as No action needed with a reason. | The case becomes closed, the outcome, reason, and time appear in place of the form, and the content is unchanged. |
| 7 | ☐ | Hide the target content from its admin page, then close the case as Enforcement applied. | The linked action appears in the timeline, Enforcement applied becomes selectable, and the closure succeeds. |
| 8 | ☐ | View a chat-moderation case without qualifying enforcement. | Current and previous signals appear with their priority and state; Enforcement applied is absent and the default closure outcome is valid. |
| 9 | ☐ | View a closed case. | No note form or close form is offered; the closure details and full history remain visible. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 10 | ☐ | Try to close without a reason. | Closing is not allowed until a reason is entered. |
| 11 | ☐ | Enter a note or reason longer than 1,000 characters. | Input stops at 1,000 characters. |
| 12 | ☐ | Add a note when the case has 100 notes. | The limit message appears and no note is added. |
| 13 | ☐ | Try to close as Enforcement applied with no linked qualifying action, including through a bypassed form. | The outcome is not offered; the backend rejects a bypassed request and the case stays open. |
| 14 | ☐ | Close a case that another admin changed after the page loaded. | Closure is rejected, the current case reloads, and a message explains that it changed. |
| 15 | ☐ | Submit the same note or closure twice. | Only one note or closure is recorded. |
| 16 | ☐ | Edit the content so a current finding no longer matches. | The finding moves to Previous Findings with its original evidence, and the case stays open. |
| 17 | ☐ | Cancel the target as its owner, or remove it as an admin. | The case closes automatically with the matching outcome. |
| 18 | ☐ | Open a case whose target no longer exists. | The case loads, the target is marked unavailable, and no Open link appears. |
| 19 | ☐ | Open a case that does not exist. | A not-found error appears. |
| 20 | ☐ | Open a case when the admin view cannot be recorded. | Case details are not shown and an error appears. |

## 6. Open Items to Resolve

**None**.
