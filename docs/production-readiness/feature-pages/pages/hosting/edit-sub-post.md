# F24 — Edit Sub Post

## 1. Existing Route(s)

- `/need-a-sub/posts/:postId/edit`

## 2. Purpose

Edit Sub Post lets the owner correct an active, upcoming outside-game post while protecting players who have already requested a sub spot. It uses the form described in [Create Sub Post](create-sub-post.md). [Need a Sub Post Detail](../public/need-a-sub-post-detail.md) owns the edit entry and subsequent requests and management.

## 3. Main Functionality

### 3.1. Load and Edit the Post

- The existing game, sub needs, location, and notes fill the five-step form. The game date is locked.
- The form explains the same 14-day scheduling limit as Create Sub Post and validates any edited start time against it before saving.
- The owner can adjust eligible fields, review the revised post, and save. Successful saving returns to Post Detail with a confirmation notice.
- Cancel or Back leaves for Post Detail when unchanged. Unsaved changes trigger a keep-editing or discard choice.

## 4. Important Behavior & Decisions

### 4.1. Owner and Lifecycle Limits

Only the post owner can edit an active post before its start. A suspended owner may still manage a post created before suspension under the [suspension rule](../admin/user-detail.md#410-suspended-player-experience). A missing, inaccessible, cancelled, expired, or already-started post cannot be edited. The backend also requires verified email for the edit request. The date cannot be changed, including by changing the start time across the local calendar-day boundary.

### 4.2. Existing Requests

A sub requirement with an active request cannot be removed or changed to another position or player group. Its spots cannot be reduced below the number of pending plus confirmed requests. New or unrequested needs can be changed subject to the creation rules. Changes to key game facts notify active requesters; request handling itself belongs to [Need a Sub Post Detail](../public/need-a-sub-post-detail.md).

### 4.3. Save Boundaries

The edited post must still meet the schedule, including the 14-day maximum, location, and sub requirement rules in [Create Sub Post](create-sub-post.md). The frontend and backend both enforce the limit for relevant edits. The update is saved as one post change with its sub needs; a failed validation or authorization check leaves the prior post in effect.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Edit Sub Post as the owner of an active future post. | The five-step form shows saved details and a locked game date. |
| 2 | ☐ | Change eligible game facts and save. | Post Detail shows the revised content and a success notice; active requesters receive an update notice for changed key game facts. |
| 3 | ☐ | Add or change an unrequested sub need within posting limits. | The revised requirements and total spots save without changing other requests. |
| 4 | ☐ | Cancel with unsaved changes, keep editing, or discard. | The modal preserves the form when kept; discarding returns to Post Detail without saving. |
| 5 | ☐ | Change only optional notes and save. | The revised notes appear on Post Detail; no key-fact update notice is generated solely by a notes change. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Open as signed out, a non-owner, or with a missing post. | Sign-in, ownership, or not-found feedback prevents unauthorized editing. |
| 7 | ☐ | Open a cancelled, inactive, or started post. | The edit form is unavailable and no change can be submitted. |
| 8 | ☐ | Attempt to change the date or move the start across its local date boundary. | The date remains locked and a tampered cross-date save is rejected. |
| 9 | ☐ | Remove or repurpose a sub need with active requests. | The existing requirement and its requests remain intact. |
| 10 | ☐ | Reduce a requirement below its pending plus confirmed count. | The lower count is rejected; existing requests and spots remain valid. |
| 11 | ☐ | Change request state while the form is open, then save stale edits. | Backend restrictions are rechecked; a now-unsafe edit is rejected without losing the existing requests. |
| 12 | ☐ | Submit invalid content or experience a save/load failure. | The page shows the relevant error and does not claim a successful update. |
| 13 | ☐ | Edit an existing post as its suspended owner. | Permitted edits to the existing arrangement remain available; no new post or participation is created. |
| 14 | ☐ | Edit a post whose locked date or proposed time would place its start beyond the 14-day limit. | The form explains the limit and blocks save before submission; a bypassed save is rejected by the backend without changing the post. |

## 6. Open Items to Resolve

**None**.
