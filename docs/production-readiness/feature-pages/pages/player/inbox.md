# F25 — Inbox

## 1. Existing Route(s)

- `/inbox`

## 2. Purpose

Inbox lets a signed-in player read account and platform updates alongside game, roster, chat, and Need a Sub activity. It provides direct actions when the related destination is still available.

## 3. Main Functionality

### 3.1. Browse Two Feeds

- **App Updates** contains platform, account, and administrative notices. **Game Activity** contains game, roster, chat, and Need a Sub updates, including in-app notices that explain official-game changes to affected players and their choice to keep a booking or request removal. Email delivery is owned by [Edit Official Game](../admin/edit-official-game.md#47-player-notice-and-withdrawal).
- App Updates can show all or new items; Game Activity can show all, unread, or read items. Each feed shows its count and loads older items in batches.
- Rows show the source, title, subject when available, and event time. Opening a row displays its detail in a modal.

### 3.2. Read and Follow an Update

- Opening an individually tracked unread item marks it read and updates the count. A failed read save restores the prior unread state.
- The modal shows full text and an action only when supplied by the notification. A disabled action explains why its historical destination cannot be opened.
- Global platform notices use a feed-level new/seen marker when App Updates is viewed; opening one does not create a separate per-item read event.

## 4. Important Behavior & Decisions

### 4.1. Private, Source-Owned Feed

Only the signed-in user's updates appear. A suspension notice must also be accessible through the restricted account experience described in [User Detail](../admin/user-detail.md#410-suspended-player-experience), so it does not depend on Inbox access while suspended. Counts, current destination availability, and action links come from the notification display rules, rather than being guessed from message text. Shared notification behavior is owned by the local notification display contract; this page owns filtering, presentation, and read interaction.

### 4.2. Loading and Recovery

The two feeds maintain separate filters and batches. A failed initial feed load shows an error; a failed later batch keeps loaded rows and permits retry. A Load More response from an earlier filter or account is ignored, including after the current feed resets; displayed messages always belong to the current account and selected filter. Opening a modal does not leave Inbox until the user chooses an available action. Switching accounts clears prior private feed data.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Inbox with app and game activity. | The two tabs separate their sources, display current counts, and show each row's source, title, subject when available, and time. |
| 2 | ☐ | Change the status filter in each feed. | App Updates shows all/new; Game Activity shows all/unread/read, with results matching the selected feed and filter. |
| 3 | ☐ | Open an unread individual notification. | Its detail modal opens, read state and count update, and the row stays or leaves according to the active status filter. |
| 4 | ☐ | Open App Updates containing a new global notice. | The feed's global seen marker is saved and the new count clears without a separate item-read action. |
| 5 | ☐ | Follow an available modal action. | The named destination opens; closing the modal instead leaves the user in Inbox. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Open a notification whose target is removed or no longer accessible. | Its text remains readable; any action is absent or explicitly disabled with a reason and does not navigate to an inaccessible page. |
| 7 | ☐ | Fail saving an individual read state. | The optimistic read change and count are restored rather than claiming the item was read. |
| 8 | ☐ | Fail saving a global seen marker. | The notice is not falsely treated as durably seen; a later view can retry. |
| 9 | ☐ | Load more than one batch, including overlapping items. | Later items append in order without duplicate rows; Load More ends after the final batch. |
| 10 | ☐ | Fail a later batch or initial feed request. | Loaded rows stay visible on later-batch failure with retry; an initial failure shows the feed error state. |
| 11 | ☐ | Switch filters while Load More is pending. | The old batch is ignored; only messages matching the newly selected filter appear, and the new feed's pagination remains usable. |
| 12 | ☐ | Open Inbox signed out or with no updates. | Sign-in is required; an authorized empty feed shows its relevant empty message. |
| 13 | ☐ | Suspend an account while Inbox is unavailable to that account. | The suspension notice remains readable in the dedicated restricted-account experience; Inbox access is not required to learn the restriction. |
| 14 | ☐ | Receive an official-game change notice as an affected player. | Game Activity explains what changed, links to the game, and states that the player may keep the booking or request removal; the edit workflow separately sends email. The notice itself does not change the booking or issue money. |
| 15 | ☐ | Switch authenticated accounts while Load More is pending. | The old account's batch is ignored, no prior-account message appears, and the new account's feed and pagination work normally. |

## 6. Open Items to Resolve

**None**.
