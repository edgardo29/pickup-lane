# F25 — Inbox Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F25-inbox-spec.md`  
**Endpoints:** `GET /inbox/app-updates`, `GET /inbox/game-activity`, `GET /inbox/counts`, `PUT /inbox/app-updates/global-seen`, `PUT /inbox/app-updates/platform-notices/{notice_id}/read`, `PATCH /notifications/{notification_id}/read`, `GET /account-suspended`

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | App Updates holds platform, account, and admin notices; Game Activity holds game, roster, chat, and Need a Sub updates | Yes | — |
| R2 | 3.1 | An official-game change notice in Game Activity explains what changed, links to the game, and states the choice to keep the booking or request removal, without changing the booking or issuing money | Yes | — |
| R3 | 3.1 | App Updates filters all or new; Game Activity filters all, unread, or read; results match the selected feed and filter | Yes | — |
| R4 | 3.1 | Each feed shows its count | Yes | — |
| R5 | 3.1 | Each feed loads older items in batches | Yes | — |
| R6 | 3.1 | Rows show the source, title, subject when available, and event time | Yes | — |
| R7 | 3.1 | Opening a row displays its detail in a modal | Yes | — |
| R8 | 3.2 | Opening an individually tracked unread item marks it read and updates the count | Yes | — |
| R9 | 3.2 | A failed read save restores the prior unread state and count | Yes | — |
| R10 | 3.2 | The modal shows the full text and an action only when the notification supplies one | Yes | — |
| R11 | 3.2 | A disabled action explains why its historical destination cannot be opened | Yes | — |
| R12 | 3.2 | Global notices use a feed-level new/seen marker saved when App Updates is viewed; opening one creates no item read | Yes | — |
| R13 | 4.1 | Only the signed-in user's updates, counts, and read changes appear | Yes | — |
| R14 | 4.1 | The suspension notice is readable in the restricted account experience without Inbox access | Yes | — |
| R15 | 4.1 | Counts, destination availability, and action links come from the notification display rules, not message text | Yes | — |
| R16 | 4.2 | The two feeds keep separate filters and batches | Yes | — |
| R17 | 4.2 | A failed initial load shows an error; a failed later batch keeps loaded rows and permits retry | Yes | — |
| R18 | 4.2 | A Load More response from an earlier filter or account is ignored, including after the feed resets | Yes | — |
| R19 | 4.2 | Opening a modal does not leave Inbox until the user chooses an available action | Yes | — |
| R20 | 4.2 | Switching accounts clears the prior account's feed data | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F25-9` is scenario 9); "Section 4.2" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F25-1, Section 3.1 | App Updates returns the user's global and selected platform notices and account and admin notices, and no game activity | R1 | `test_app_updates_returns_platform_notices_and_account_and_admin_notices` | Feeds stopped filtering by category, so game activity appeared in App Updates | `inbox_service.py` |
| 2 | F25-1, Section 3.1 | Game Activity returns the user's game and Need a Sub updates, and no app updates | R1 | `test_game_activity_returns_game_and_need_a_sub_updates` | Feeds stopped filtering by category, so app updates appeared in Game Activity | `inbox_service.py` |
| 3 | F25-1, Section 4.1 | Each feed returns only the signed-in user's items; another user's notifications and selected notices are absent | R13 | `test_each_feed_returns_only_the_signed_in_users_items` | Feeds stopped filtering notifications by user | `inbox_service.py` |
| 4 | F25-1 | The counts return the App Updates new count and the Game Activity unread count | R4 | `test_counts_return_the_app_updates_new_and_game_activity_unread_counts` | The App Updates count left out selected notices | `inbox_service.py` |
| 5 | F25-1 | Each item returns its source, title, subject when available, and event time | R6 | `test_an_item_returns_its_source_title_subject_and_event_time` | Items returned the source label as the subject | `inbox_service.py` |
| 6 | F25-2 | App Updates "new" returns only new items; "all" returns new and seen items | R3 | `test_app_updates_new_filter_returns_only_new_items` | The New filter kept global notices already seen | `inbox_service.py` |
| 7 | F25-2 | Game Activity "unread" returns only unread items | R3 | `test_game_activity_unread_filter_returns_only_unread_items` | The Unread filter also returned read items | `inbox_service.py` |
| 8 | F25-2 | Game Activity "read" returns only read items; "all" returns both | R3 | `test_game_activity_read_filter_returns_only_read_items` | The Read filter also returned unread items | `inbox_service.py` |
| 9 | F25-3 | Marking an unread notification read saves its read state and lowers the Game Activity unread count | R8 | `test_marking_a_notification_read_saves_it_and_lowers_the_unread_count` | Marking read returned the notification without saving it | `notification_service.py` |
| 10 | F25-3 | Marking a selected platform notice read saves its read state and lowers the App Updates new count | R8 | `test_marking_a_selected_notice_read_saves_it_and_lowers_the_new_count` | The selected notice's read was not saved | `inbox_service.py` |
| 11 | F25-3, F25-7, Section 4.1 | Another user cannot mark the notification read; it stays unread | R13 | `test_another_user_cannot_mark_the_notification_read` | Any user could mark a notification read | `notification_service.py` |
| 12 | F25-3, Section 4.1 | Another user cannot mark a selected platform notice read; it stays new for its recipient | R13 | `test_another_user_cannot_mark_a_selected_notice_read` | Marking a selected notice read no longer required being its recipient | `inbox_service.py` |
| 13 | F25-4 | Saving the global seen marker clears the global notices from the new count without creating an item read | R12 | `test_saving_the_global_seen_marker_clears_the_new_count_without_an_item_read` | The seen marker was not saved | `inbox_service.py` |
| 14 | F25-4, Section 4.1 | A global seen marker issued to another user is rejected and changes nothing | R12, R13 | `test_a_global_seen_marker_issued_to_another_user_is_rejected` | The seen marker's user was not checked | `inbox_service.py` |
| 15 | F25-8 | A rejected global seen marker leaves the notice new; a later valid save marks it seen | R12 | `test_a_rejected_global_seen_marker_leaves_the_notice_new_until_a_later_save` | A rejected marker still saved the seen position | `inbox_service.py` |
| 16 | F25-5 | A notification whose game is active or completed returns an enabled action to that game | R10, R15 | `test_a_notification_for_an_available_game_returns_an_action_to_that_game` | Available games returned no action; separately, completed games were treated as gone | `notification_display_service.py`, `game_rules.py` |
| 17 | F25-6 | A notification whose game was cancelled, expired, removed, deleted, left in draft, or archived keeps its text and returns no action | R10, R15 | `test_a_notification_for_a_game_that_is_gone_keeps_its_text_and_has_no_action` | Only a missing game lost its action | `notification_display_service.py` |
| 18 | F25-6 | A notification for a hidden game the user can no longer open returns a disabled action with its reason and no destination | R11, R15 | `test_a_hidden_game_the_user_can_no_longer_open_has_a_disabled_action` | Hidden-game access was not checked | `notification_display_service.py` |
| 19 | F25-6 | A Need a Sub chat notification after the user lost chat access returns a disabled action with its reason and no destination | R11, R15 | `test_a_need_a_sub_chat_notice_after_losing_chat_access_has_a_disabled_action` | Chat access was not checked | `notification_display_service.py` |
| 20 | F25-6, Section 4.1 | A policy notice's action is not chosen from its message text | R15 | `test_a_policy_notice_action_is_not_chosen_from_its_message_text` | Restored choosing the policy page from the message text | `notification_display_service.py` |
| 21 | F25-9 | Later batches continue newest first without duplicates, and the final batch reports no more items | R5 | `test_later_batches_continue_newest_first_without_duplicates_and_then_end` | The feed always reported more items | `inbox_service.py` |
| 22 | F25-9 | Items added after the first batch do not repeat or shift items in later batches | R5 | `test_items_added_after_the_first_batch_do_not_repeat_or_shift_later_batches` | Later batches used an offset with no snapshot time | `inbox_service.py` |
| 23 | F25-11, Section 4.2 | A cursor from another filter is rejected | R18 | `test_a_cursor_from_another_filter_is_rejected` | The cursor's filter was not checked | `inbox_service.py` |
| 24 | F25-15, Section 4.2 | A cursor from another account is rejected | R13, R18 | `test_a_cursor_from_another_account_is_rejected` | The cursor's user was not checked | `inbox_service.py` |
| 25 | F25-12 | Signed-out requests to each feed and to the counts are rejected | R13 | `test_signed_out_requests_to_the_feeds_and_counts_are_rejected` | The feeds and counts answered signed-out requests | `inbox_routes.py` |
| 26 | F25-12 | A signed-in user with no updates gets empty feeds and zero counts | R3, R4 | `test_a_user_with_no_updates_gets_empty_feeds_and_zero_counts` | An empty App Updates feed returned 404 | `inbox_service.py` |
| 27 | F25-13 | After a real suspension, the suspended user reads that suspension notice through the restricted account experience | R14 | `test_a_suspended_user_reads_the_suspension_notice_outside_inbox` | The notice lookup searched the wrong staff action | `account_suspension_service.py` |
| 28 | F25-13 | A suspended user's Inbox requests are refused; reading the notice does not depend on Inbox | R14 | `test_a_suspended_users_inbox_requests_are_refused` | Inbox accepted suspended accounts | `inbox_routes.py` |
| 29 | F25-14, Section 3.1 | Editing an official game through Edit Official Game gives each affected player a Game Activity notice that explains what changed, links to the game, and states that the player may keep the booking or request removal | R2 | `test_an_official_game_edit_sends_each_player_a_notice_explaining_the_change` | Removed the notice from the Edit Official Game save | `official_game_service.py` |
| 30 | F25-14, Section 3.1 | Changing only the price also sends the notice; no fixed list of fields applies | R2 | `test_changing_only_the_price_also_sends_the_notice` | Price changes had no notice label | `game_notification_service.py` |
| 31 | F25-14 | The notice itself does not change the booking or issue money | R2 | `test_the_change_notice_does_not_change_the_booking_or_issue_money` | The notice cancelled the player's booking | `game_notification_service.py` |
| 32 | F25-14 | A player whose booking is partly cancelled also gets the notice with the choice to keep the booking or request removal | R2 | `test_a_player_whose_booking_is_partly_cancelled_also_gets_the_choice` | Only fully confirmed bookings got the choice | `game_notification_service.py` |
| 33 | F25-5 | A notification for a hidden game the user can still open returns an enabled action to that game | R10, R15 | `test_a_hidden_game_the_user_can_still_open_keeps_its_action` | Every hidden game got a disabled action | `notification_display_service.py` |
| 34 | F25-5 | A Need a Sub notification for an active post that has not started returns an enabled action to the post | R10, R15 | `test_a_notification_for_an_active_upcoming_post_returns_an_action_to_that_post` | Active posts returned no action | `notification_display_service.py` |
| 35 | F25-6 | A Need a Sub notification for a post that was completed, cancelled, expired, or removed, or has started, keeps its text and returns no action | R10, R15 | `test_a_notification_for_a_post_that_is_gone_keeps_its_text_and_has_no_action` | Post status and start time were not checked | `notification_display_service.py` |
| 36 | F25-2 | Each feed rejects a filter it does not offer | R3 | `test_each_feed_rejects_a_filter_it_does_not_offer` | The feeds accepted any filter | `inbox_routes.py` |

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F25-1 | The App Updates and Game Activity tabs each show only their own feed's rows | R1 | `F25-1: each tab shows only its own feed's rows` | The Game Activity tab loaded App Updates | `inboxApi.js` |
| 2 | F25-1 | Each tab displays its current count | R4 | `F25-1: each tab displays its current count` | Tab counts always showed 0 | `InboxPage.jsx` |
| 3 | F25-1 | A row shows its source, title, subject when available, and time | R6 | `F25-1: a row shows its source, title, subject, and time` | Rows left out the subject | `InboxRow.jsx` |
| 4 | F25-2 | App Updates offers All and New and shows the results for the selected filter | R3 | `F25-2: App Updates offers All and New and shows the results for New` | Feed requests always asked for All | `inboxApi.js` |
| 5 | F25-2 | Game Activity offers All, Unread, and Read and shows the results for the selected filter | R3 | `F25-2: Game Activity offers All, Unread, and Read and shows the results for Read` | Feed requests always asked for All | `inboxApi.js` |
| 6 | F25-2, Section 4.2 | Each feed keeps its own filter and loaded rows when the user switches tabs | R16 | `F25-2: each feed keeps its own filter and loaded rows when the user switches tabs` | Switching tabs reset the feed's filter | `InboxPage.jsx` |
| 7 | F25-3 | Opening an unread row opens its detail modal with the full text | R7, R10 | `F25-3: opening an unread row opens its detail modal with the full text` | The modal showed the title in place of the message | `NotificationModal.jsx` |
| 8 | F25-3 | Opening an unread row saves its read state and lowers the count | R8 | `F25-3: opening an unread row saves its read state and lowers the count` | Opening a row skipped the read save | `useInboxPageModel.js` |
| 9 | F25-3 | Under New, the opened row leaves the list | R8 | `F25-3: under New, the opened row leaves the list` | Opened rows never left a filtered list | `useInboxPageModel.js` |
| 10 | F25-3 | Under All, the opened row stays and shows as read | R8 | `F25-3: under All, the opened row stays and shows as read` | The opened row stayed marked New | `useInboxPageModel.js` |
| 11 | F25-3 | Opening a selected platform notice saves its item read state | R8 | `F25-3: opening a selected platform notice saves its item read state` | Selected notices skipped their read save | `useInboxPageModel.js` |
| 12 | F25-4 | Viewing App Updates with a new global notice saves the feed's seen marker and clears the new count | R12 | `F25-4: viewing App Updates with a new global notice saves the seen marker and clears the count` | The seen marker was never sent | `useInboxPageModel.js` |
| 13 | F25-4 | Opening a global notice sends no item read | R12 | `F25-4: opening a global notice sends no item read` | Global notices were read one item at a time | `inboxData.js`, `useInboxPageModel.js` |
| 14 | F25-5 | Choosing an available action opens the named destination | R10, R19 | `F25-5: choosing an available action opens the named destination` | The action closed the modal without navigating | `useInboxPageModel.js` |
| 15 | F25-5 | Closing the modal instead leaves the user in Inbox | R19 | `F25-5: closing the modal instead leaves the user in Inbox` | Back followed the action | `NotificationModal.jsx` |
| 16 | F25-6 | A notification with no action shows its text and no action button | R10 | `F25-6: a notification with no action shows its text and no action button` | A notification with no action got an Open button | `inboxData.js` |
| 17 | F25-6 | A disabled action shows its reason and does not navigate | R11 | `F25-6: a disabled action shows its reason and does not navigate` | The disabled reason was hidden | `NotificationModal.jsx` |
| 18 | F25-7 | A failed read save restores the unread row and the count | R9 | `F25-7: a failed read save restores the unread row and the count` | A failed read save left the row read and the count lowered | `useInboxPageModel.js` |
| 19 | F25-7, Section 4.2 | A read save that fails after an account switch does not change the new account's count | R9, R20 | `F25-7: a read save that fails after an account switch does not change the new account's count` | A failed read save restored the count after an account switch | `useInboxPageModel.js` |
| 20 | F25-7, Section 4.2 | A read save that finishes after a switch to All leaves the opened row in the All list | R9, R16 | `F25-7: a read save that finishes after a filter switch does not change the new filter's list` | A finished read save used the filter from when the row was opened | `useInboxPageModel.js` |
| 21 | F25-8 | A failed global seen save keeps the notice new, and a later App Updates view retries the save | R12 | `F25-8: a failed global seen save keeps the notice new, and a later App Updates view retries` | A failed seen save was never retried | `useInboxPageModel.js` |
| 22 | F25-9 | Load More appends the later items in order, without duplicate rows | R5 | `F25-9: Load More appends the later items in order, without duplicate rows` | Later batches were not checked for duplicates | `useInboxPageModel.js` |
| 23 | F25-9 | Load More ends after the final batch | R5 | `F25-9: Load More ends after the final batch` | Load More kept the earlier batch's has-more flag | `useInboxPageModel.js` |
| 24 | F25-10 | A failed initial feed request shows the feed error | R17 | `F25-10: a failed initial feed request shows the feed error` | A failed initial load showed an empty feed | `useInboxPageModel.js` |
| 25 | F25-10 | A failed later batch keeps the loaded rows and offers retry | R17 | `F25-10: a failed later batch keeps the loaded rows and offers retry` | A failed later batch cleared the loaded rows | `useInboxPageModel.js` |
| 26 | F25-11 | A Load More from the old filter is ignored; only the new filter's rows appear and its Load More works | R16, R18 | `F25-11: a Load More from the old filter is ignored; only the new filter's rows appear and its Load More works` | Late batches were applied to whatever feed was showing | `useInboxPageModel.js` |
| 27 | F25-12 | A signed-out visitor is sent to Sign In | R13 | `F25-12: a signed-out visitor is sent to Sign In` | The Inbox guard let signed-out visitors in | `RouteGuards.jsx` |
| 28 | F25-12 | An empty feed shows its empty message, and an empty filter result shows the message for that filter: All and New in App Updates; All, Unread, and Read in Game Activity | R3 | `F25-12: an empty feed shows its empty message, and each empty filter result names its filter` | Empty results always showed the All message | `inboxSelectors.js` |
| 29 | F25-13 | A suspended user who opens Inbox reaches Account Suspended | R14 | `F25-13: a suspended user who opens Inbox reaches Account Suspended` | The Inbox guard let suspended accounts in | `RouteGuards.jsx` |
| 30 | F25-13 | Account Suspended shows the suspension notice and the restrictions from User Detail, Section 4.10 | R14 | `F25-13: Account Suspended shows the suspension notice and the restrictions` | The notice message was left out | `AccountSuspendedPage.jsx` |
| 31 | F25-14 | The official-game change notice shows what changed, the choice to keep the booking or request removal, and a View game action | R2 | `F25-14: the official-game change notice shows what changed, the choice to keep the booking or request removal, and View game` | The modal showed the summary in place of the message | `NotificationModal.jsx` |
| 32 | F25-15, Section 4.2 | After an account switch during Load More, the old batch is ignored, no prior-account row appears, and the new feed loads and paginates | R18, R20 | `F25-15: after an account switch during Load More, the old batch is ignored and the new feed loads and paginates` | Late batches were applied to whatever feed was showing | `useInboxPageModel.js` |
| 33 | F25-3, Section 4.2 | A read save that finishes after a switch to New removes the opened row from the New list | R8, R16 | `F25-3: a read save that finishes after a switch to New removes the row from the New list` | A finished read save used the filter from when the row was opened | `useInboxPageModel.js` |
| 34 | F25-3 | Opening an unread Game Activity row saves its read state and lowers the Game Activity count | R8 | `F25-3: opening an unread Game Activity row saves its read state and lowers its count` | The Game Activity count was not lowered | `useInboxPageModel.js` |
| 35 | F25-3 | Under Unread, the opened Game Activity row leaves the list | R8 | `F25-3: under Unread, the opened Game Activity row leaves the list` | Opened rows left only a New list | `useInboxPageModel.js` |

## 3. Work to do

None. All work is done.
