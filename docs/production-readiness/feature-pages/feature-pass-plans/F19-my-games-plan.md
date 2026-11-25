# F19 — My Games Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F19-my-games-spec.md`  
**Endpoints:** `GET /my-games`, `GET /my-games/need-a-sub`

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | Games and Need a Sub areas, each with Upcoming and History; Games/Upcoming opens first | Yes | — |
| R2 | 3.1 | Cards grouped by scheduled date; Upcoming earliest first, History newest first | Yes | — |
| R3 | 3.1 | Each view loads in batches with Load More | Yes | — |
| R4 | 3.2 | Game cards show type, venue, time, location, format, spots, price, and hosting or cancellation status, and open Game Details | Yes | — |
| R5 | 3.2 | Need a Sub cards show the outside game, sub needs, confirmed and open counts, and owner or cancellation status, and open Post Detail only while it is accessible | Yes | — |
| R6 | 4.1 | Only owned or hosted items and confirmed participation qualify; tentative relationships do not | Yes | — |
| R7 | 4.1 | Hidden qualifying items stay listed; removed items do not | Yes | — |
| R8 | 4.2 | An active item stays Upcoming until its scheduled end, including while in progress | Yes | — |
| R9 | 4.2 | A qualifying cancelled item moves to History immediately | Yes | — |
| R10 | 4.2 | History covers 60 days by scheduled end, including a cancelled item's scheduled end | Yes | — |
| R11 | 4.2 | Cancelled-player history requires proof the player was confirmed when the item was cancelled | Yes | — |
| R12 | 4.2 | The backend decides eligibility; each view keeps its own loading and pagination state, so returning to a view keeps its loaded cards and Load More position | Yes | — |
| R13 | 4.3 | Private activity requires sign-in | Yes | — |
| R14 | 4.3 | A suspended player still finds existing hosted and confirmed commitments; suspension alone does not move them | Yes | — |
| R15 | 4.3 | Each view has its own loading, empty, error, and Load More states; a failed later batch keeps earlier cards for retry | Yes | — |
| R16 | 4.3 | Late results from another view or account cannot replace the active view | Yes | — |
| R17 | 4.3 | An inaccessible historical Need a Sub post stays visible as a card without a link | Yes | — |
| R18 | 3.1 | Card dates, times, and date groups use each game's or post's local time zone, not the device's | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F19-6` is scenario 6); "Section 4.2" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F19-1, Section 4.1 | A hosted game is listed in Games/Upcoming | R1, R6 | `test_a_hosted_game_is_listed_in_upcoming` | Hosted games were left out of the list | `game_service.py` |
| 2 | F19-1, Section 4.1 | A confirmed game is listed in Games/Upcoming | R6 | `test_a_confirmed_game_is_listed_in_upcoming` | Confirmed games were left out of the list | `game_service.py` |
| 3 | F19-1 | Only the player's own games appear; another player's game is not listed | R6 | `test_another_players_game_is_not_listed` | The list included games other players had joined | `game_service.py` |
| 4 | F19-1, Section 3.2 | A game card shows the hosting or confirmed status | R4 | `test_a_game_card_shows_the_hosting_or_confirmed_status` | A hosted game was labelled Confirmed instead of Hosting | `game_service.py` |
| 5 | F19-4 | A tentative relationship alone does not qualify: pending payment, waitlisted, cancelled, late-cancelled, removed, or refunded | R6 | `test_a_game_the_player_is_not_confirmed_for_is_not_listed` | Every participant status counted as confirmed | `game_service.py` |
| 6 | F19-4 | A game the player only brought guests to is not listed | R6 | `test_a_game_the_player_only_brought_guests_to_is_not_listed` | A game counted when the player had only brought guests | `game_service.py` |
| 7 | F19-4, Section 4.1 | A game staff added the player to, as a confirmed player, is listed | R6 | `test_a_game_staff_added_the_player_to_is_listed` | Players added by staff were left out | `game_service.py` |
| 8 | F19-5 | A game remains Upcoming while in progress | R8 | `test_a_game_stays_upcoming_while_in_progress` | A game left Upcoming as soon as it started | `game_service.py` |
| 9 | F19-5 | A game moves to History after its scheduled end | R8 | `test_a_game_moves_to_history_at_its_scheduled_end` | A game reached History only after its scheduled end, not at it | `game_service.py` |
| 10 | F19-5, Section 4.2 | An ended game marked completed or expired is in History | R8 | `test_an_ended_completed_or_expired_game_is_in_history` | Completed and expired games were left out of History | `game_service.py` |
| 11 | F19-6 | A cancelled game moves to History immediately for its host | R9 | `test_a_cancelled_game_moves_to_history_for_its_host` | A cancelled game reached History only after its scheduled end | `game_service.py` |
| 12 | F19-6 | A cancelled game moves to History immediately for a confirmed player | R9, R11 | `test_a_cancelled_game_moves_to_history_for_a_confirmed_player` | A cancelled game reached History only after its scheduled end | `game_service.py` |
| 13 | F19-6 | A waitlisted-only player does not see the cancelled game | R11 | `test_a_waitlisted_only_player_does_not_see_the_cancelled_game` | Anyone with a roster place on a cancelled game saw it in History | `game_service.py` |
| 14 | F19-6, Section 4.2 | A player who left before the game was cancelled does not see it in History | R11 | `test_a_player_who_left_before_the_cancellation_does_not_see_the_game` | Anyone with a roster place on a cancelled game saw it in History | `game_service.py` |
| 15 | F19-6 | A game cancelled because its host deleted their account stays in the confirmed player's History | R9, R11 | `test_a_game_cancelled_because_the_host_deleted_their_account_stays_in_player_history` | A cancellation caused by account deletion did not count as proof the player was confirmed | `game_service.py` |
| 16 | F19-6, Section 3.2 | A cancelled game card shows the cancellation status | R4 | `test_a_cancelled_game_card_shows_the_cancellation_status` | A cancelled game was labelled Completed | `game_service.py` |
| 17 | F19-7 | A hidden qualifying game remains listed | R7 | `test_a_hidden_game_stays_listed` | Hidden games were left out | `game_service.py` |
| 18 | F19-7 | A removed game is excluded | R7 | `test_a_removed_game_is_not_listed` | Removed games were listed | `game_service.py` |
| 19 | F19-7 | A soft-deleted game is excluded | R7 | `test_a_deleted_game_is_not_listed` | Deleted games were listed | `game_service.py` |
| 20 | F19-8 | A game that ended within 60 days remains in History | R10 | `test_a_game_that_ended_within_60_days_stays_in_history` | History covered 59 days instead of 60 | `game_service.py` |
| 21 | F19-8 | A game that ended more than 60 days ago is absent | R10 | `test_a_game_that_ended_more_than_60_days_ago_is_not_in_history` | History covered 61 days instead of 60 | `game_service.py` |
| 22 | F19-8 | A cancelled game's 60 days count from its scheduled end, not its cancellation time | R10 | `test_a_cancelled_games_60_days_count_from_its_scheduled_end` | A cancelled game's 60 days counted from its cancellation time | `game_service.py` |
| 23 | F19-3 | Games/Upcoming runs earliest first | R2 | `test_upcoming_runs_earliest_first` | Upcoming and History orders were swapped | `game_service.py` |
| 24 | F19-3 | Games/History runs newest first | R2 | `test_history_runs_newest_first` | Upcoming and History orders were swapped | `game_service.py` |
| 25 | F19-3 | Games Load More appends later items without duplicates | R3 | `test_load_more_continues_games_without_duplicates` | Load More ignored its position and started over | `game_service.py` |
| 26 | F19-1, Section 4.1 | An owned post is listed in Need a Sub/Upcoming | R1, R6 | `test_an_owned_post_is_listed_in_upcoming` | Owned posts were left out of Upcoming | `need_a_sub_post_service.py` |
| 27 | F19-1, Section 4.1 | A post the player is confirmed for is listed in Need a Sub/Upcoming | R6 | `test_a_confirmed_post_is_listed_in_upcoming` | Posts the player is confirmed for were left out | `need_a_sub_post_service.py` |
| 28 | F19-1 | Only the player's own posts appear; another player's post is not listed | R6 | `test_another_players_post_is_not_listed` | The list included posts other players were confirmed for | `need_a_sub_post_service.py` |
| 29 | F19-1, Section 3.2 | A post card shows the owner or confirmed status | R5 | `test_a_post_card_shows_the_owner_or_confirmed_status` | An owned post was labelled Confirmed instead of Your Post | `need_a_sub_post_service.py` |
| 30 | F19-4 | A tentative request alone does not qualify: pending, declined, sub waitlist, cancelled by the player or owner, no-show reported, expired, or closed by staff | R6 | `test_a_post_the_player_is_not_confirmed_for_is_not_listed` | Every request status counted as confirmed | `need_a_sub_post_service.py` |
| 31 | F19-2 | An owner's post card can open its Post Detail while that detail is accessible | R5 | `test_an_owners_post_card_can_open_its_post_while_the_detail_is_accessible` | No post card could open its detail | `need_a_sub_post_service.py` |
| 32 | F19-2, Section 4.3 | An owner's historical post whose detail is no longer accessible cannot be opened | R5, R17 | `test_an_owners_historical_post_whose_detail_is_closed_cannot_be_opened` | Every post card could open its detail | `need_a_sub_post_service.py` |
| 33 | F19-5 | A post remains Upcoming while its game is in progress | R8 | `test_a_post_stays_upcoming_while_its_game_is_in_progress` | A post left Upcoming as soon as its game started | `need_a_sub_post_service.py` |
| 34 | F19-5 | A post moves to History after its scheduled end | R8 | `test_a_post_moves_to_history_at_its_scheduled_end` | A post reached History only after its scheduled end, not at it | `need_a_sub_post_service.py` |
| 35 | F19-5, Section 4.2 | An ended post marked completed or expired is in History | R8 | `test_an_ended_completed_or_expired_post_is_in_history` | Completed and expired posts were left out of History | `need_a_sub_post_service.py` |
| 36 | F19-6 | A cancelled post moves to History immediately for its owner | R9 | `test_a_cancelled_post_moves_to_history_for_its_owner` | A cancelled post reached History only after its scheduled end | `need_a_sub_post_service.py` |
| 37 | F19-6 | A cancelled post moves to History immediately for a confirmed sub | R9, R11 | `test_a_cancelled_post_moves_to_history_for_a_confirmed_sub` | A cancelled post reached History only after its scheduled end | `need_a_sub_post_service.py` |
| 38 | F19-6 | A sub-waitlisted-only player does not see the cancelled post | R11 | `test_a_sub_waitlisted_only_player_does_not_see_the_cancelled_post` | Anyone with a request on a cancelled post saw it in History | `need_a_sub_post_service.py` |
| 39 | F19-6, Section 4.2 | A sub who left before the post was cancelled does not see it in History | R11 | `test_a_sub_who_left_before_the_cancellation_does_not_see_the_post` | Anyone with a request on a cancelled post saw it in History | `need_a_sub_post_service.py` |
| 40 | F19-6 | A post cancelled because its owner deleted their account stays in the confirmed sub's History | R9, R11 | `test_a_post_cancelled_because_the_owner_deleted_their_account_stays_in_sub_history` | A cancellation caused by account deletion did not count as proof the sub was confirmed | `need_a_sub_post_service.py` |
| 41 | F19-6, Section 3.2 | A cancelled post card shows the cancellation status | R5 | `test_a_cancelled_post_card_shows_the_cancellation_status` | A cancelled post was labelled Ended | `need_a_sub_post_service.py` |
| 42 | F19-7 | A hidden qualifying post remains listed | R7 | `test_a_hidden_post_stays_listed` | Hidden posts were left out | `need_a_sub_post_service.py` |
| 43 | F19-7 | A removed post is excluded | R7 | `test_a_removed_post_is_not_listed` | Removed posts were listed | `need_a_sub_post_service.py` |
| 44 | F19-8 | A post that ended within 60 days remains in History | R10 | `test_a_post_that_ended_within_60_days_stays_in_history` | History covered 59 days instead of 60 | `need_a_sub_post_service.py` |
| 45 | F19-8 | A post that ended more than 60 days ago is absent | R10 | `test_a_post_that_ended_more_than_60_days_ago_is_not_in_history` | History covered 61 days instead of 60 | `need_a_sub_post_service.py` |
| 46 | F19-8 | A cancelled post's 60 days count from its scheduled end, not its cancellation time | R10 | `test_a_cancelled_posts_60_days_count_from_its_scheduled_end` | A cancelled post's 60 days counted from its cancellation time | `need_a_sub_post_service.py` |
| 47 | F19-3 | Need a Sub/Upcoming runs earliest first | R2 | `test_need_a_sub_upcoming_runs_earliest_first` | Upcoming and History orders were swapped | `need_a_sub_post_service.py` |
| 48 | F19-3 | Need a Sub/History runs newest first | R2 | `test_need_a_sub_history_runs_newest_first` | Upcoming and History orders were swapped | `need_a_sub_post_service.py` |
| 49 | F19-3 | Need a Sub Load More appends later items without duplicates | R3 | `test_load_more_continues_posts_without_duplicates` | Load More ignored its position and started over | `need_a_sub_post_service.py` |
| 50 | F19-12 | Sign-in is required for both lists | R13 | `test_signed_out_visitors_cannot_open_my_games` | The lists let signed-out requests in | `my_game_routes.py` |
| 51 | F19-12 | A deleted or deleting account cannot open either list | R13 | `test_a_deleted_or_deleting_account_cannot_open_my_games` | Sign-in accepted deleted and deleting accounts | `auth_service.py` |
| 52 | F19-12 | One account's Load More position cannot be used by another account | R16 | `test_one_accounts_cursor_cannot_be_used_by_another` | A Load More position was not tied to its account | `game_service.py` |
| 53 | F19-9 | A Load More position from another view is rejected | R12, R16 | `test_a_cursor_from_another_view_is_rejected` | A Load More position was not tied to its view | `game_service.py` |
| 54 | F19-9 | A Load More position from the other list is rejected | R12, R16 | `test_a_cursor_from_the_other_list_is_rejected` | The Need a Sub list accepted a Games Load More position | `need_a_sub_post_service.py` |
| 55 | F19-9 | An altered Load More position is rejected | R16 | `test_an_altered_cursor_is_rejected` | A Load More position's signature was not checked | `pagination_cursor.py` |
| 56 | F19-13 | A suspended player still finds their existing hosted and confirmed games | R14 | `test_a_suspended_player_still_finds_their_hosted_and_confirmed_games` | The lists accepted only active accounts | `my_game_routes.py` |
| 57 | F19-13 | A suspended player still finds their existing owned and confirmed posts | R14 | `test_a_suspended_player_still_finds_their_owned_and_confirmed_posts` | The lists accepted only active accounts | `my_game_routes.py` |
| 58 | F19-13 | No item moves to History solely because of suspension | R14 | `test_suspension_alone_does_not_move_anything_to_history` | A suspended player's History showed their upcoming items | `game_service.py` |
| 59 | F19-2 | A confirmed sub's post card can open its Post Detail while that detail is accessible | R5 | `test_a_confirmed_subs_post_card_can_open_its_post_while_the_detail_is_accessible` | A confirmed sub never kept a post's detail after public discovery closed | `need_a_sub_post_service.py` |
| 60 | F19-2, Section 4.3 | A confirmed sub's historical post whose detail is no longer accessible cannot be opened | R5, R17 | `test_a_confirmed_subs_historical_post_whose_detail_is_closed_cannot_be_opened` | A confirmed sub kept a post's detail after it closed | `need_a_sub_post_service.py` |
| 61 | F19-1, Section 3.2 | An owned post's card keeps its owner status in History | R5 | `test_an_owned_posts_history_card_shows_the_owner_status` | Failed before the change | — |
| 62 | F19-1, Section 3.2 | A hosted game's card shows the hosting status in History | R4 | `test_a_hosted_games_history_card_shows_the_hosting_status` | A hosted game in History was labelled Completed instead of Hosted | `game_service.py` |
| 63 | F19-6 | A game staff cancel moves to History immediately for a confirmed player | R9, R11 | `test_a_game_staff_cancel_stays_in_the_confirmed_players_history` | Staff were not counted as a canceller; separately, the staff-cancelled type did not count as proof the player was confirmed | `game_service.py` |

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F19-1 | Games/Upcoming opens first | R1 | `F19-1: Games/Upcoming opens first` | My Games opened on History instead of Upcoming | `useMyGamesPageModel.js` |
| 2 | F19-1 | Switching areas and views shows only the matching items | R1 | `F19-1: switching areas and views shows only the matching items` | Choosing another view left the previous view's items showing | `useMyGamesPageModel.js` |
| 3 | F19-1, Section 3.2 | A game card shows its type, venue, time, location, format, spots, price, and status | R4 | `F19-1: a game card shows its type, venue, time, location, format, spots, price, and status` | The game card left out the price | `MyGameCard.jsx` |
| 4 | F19-1, Section 3.2 | A Need a Sub card shows the outside game, sub needs, confirmed and open counts, and status | R5 | `F19-1: a Need a Sub card shows the outside game, sub needs, confirmed and open counts, and status` | The Need a Sub card left out the open-spot counts | `MyNeedASubCard.jsx` |
| 5 | F19-6, Section 3.2 | A cancelled card shows the cancellation status | R4, R5 | `F19-6: a cancelled card shows the cancellation status` | A cancelled game card hid its Cancelled status | `MyGameCard.jsx` |
| 6 | F19-2 | A game card opens Game Details | R4 | `F19-2: a game card opens Game Details` | The game card linked back to My Games instead of Game Details | `MyGameCard.jsx` |
| 7 | F19-2 | An accessible post card opens Post Detail | R5 | `F19-2: an accessible post card opens Post Detail` | An accessible post card linked back to My Games instead of Post Detail | `MyNeedASubCard.jsx` |
| 8 | F19-2, Section 4.3 | An inaccessible historical post card is shown but not linked | R5, R17 | `F19-2: an inaccessible historical post card is shown but not linked` | Every post card was a link, including inaccessible ones | `MyNeedASubCard.jsx` |
| 9 | F19-3 | Upcoming cards group by scheduled date | R2 | `F19-3: Upcoming cards group by scheduled date` | All cards were put under one date | `myGamesSelectors.js` |
| 10 | F19-3 | Upcoming cards within a date run earliest first | R2 | `F19-3: Upcoming cards within a date run earliest first` | Cards within a date were shown in reverse time order | `myGamesSelectors.js` |
| 11 | F19-3 | Load More appends later items without duplicates | R3 | `F19-3: Load More appends later items without duplicates` | Load More kept cards the page already had, showing them twice | `useMyGamesPageModel.js` |
| 12 | F19-9 | Late results from another view cannot replace the active view | R16 | `F19-9: a late answer for another view does not replace the active view` | Every answer was stored in the History view, whichever view it was for | `useMyGamesPageModel.js` |
| 13 | F19-15, Section 4.2 | Returning to a view shows the cards it already loaded, and Load More continues from where it left off | R12 | `F19-15: returning to a view shows the cards it already loaded, and Load More continues` | Failed before the change | — |
| 14 | F19-10 | A failed first load shows a view-specific error | R15 | `F19-10: a failed first load shows a view-specific error` | A failed first load was shown as an empty success; a failed view's error was also shown in the other views | `useMyGamesPageModel.js` |
| 15 | F19-10 | Retry shows the view's items or empty state | R15 | `F19-10: Retry shows the view's items or empty state` | Retry did nothing | `useMyGamesPageModel.js` |
| 16 | F19-11 | A failed Load More keeps existing cards visible | R15 | `F19-11: a failed Load More keeps the existing cards visible` | A failed Load More cleared the cards already shown | `useMyGamesPageModel.js` |
| 17 | F19-11 | Retry adds the next batch without duplicates | R15 | `F19-11: Retry adds the next batch without duplicates` | A successful Load More replaced the cards instead of adding to them | `useMyGamesPageModel.js` |
| 18 | F19-12 | A signed-out visitor is sent to sign in | R13 | `F19-12: a signed-out visitor is sent to sign in` | The sign-in guard let signed-out visitors through | `RouteGuards.jsx` |
| 19 | F19-12 | Switching accounts clears the previous account's cards | R16 | `F19-12: switching accounts clears the previous account's cards` | Switching accounts kept the previous account's cards | `useMyGamesPageModel.js` |
| 20 | F19-13 | A suspended player still sees their existing hosted and confirmed items | R14 | `F19-13: a suspended player still sees their existing hosted and confirmed items` | The page refused to load lists for a suspended player | `useMyGamesPageModel.js` |
| 21 | F19-14 | A game card's date, time, and date group follow the game's local time zone, not the device's | R18 | `F19-14: a game card's date, time, and date group follow the game's local time zone` | Failed before the change | — |
| 22 | F19-14 | A Need a Sub card's date, time, and date group follow the post's local time zone, not the device's | R18 | `F19-14: a Need a Sub card's date, time, and date group follow the post's local time zone` | Failed before the change | — |
| 23 | F19-1, Section 4.3 | Each view has its own empty state | R15 | `F19-1: each view shows its own empty message` | Every view showed the Games/Upcoming empty message | `MyGamesPage.jsx` |
| 24 | F19-9, Section 4.3 | Each view has its own loading state | R15 | `F19-9: a view shows its own loading state while it loads` | While one view loaded, every view showed the loading state | `useMyGamesPageModel.js` |
| 25 | F19-12, Section 4.3 | Late results from another account cannot replace the active view | R16 | `F19-12: a late answer for the previous account does not replace the next account's view` | Every answer was used, whichever account or request it was for | `useMyGamesPageModel.js` |
| 26 | F19-1, Section 3.2 | A hosted game card in History shows the Hosted status | R4 | `F19-1: a hosted game card in History shows the Hosted status` | The game card hid the Hosted status | `MyGameCard.jsx` |
| 27 | F19-3 | History cards group by scheduled date | R2 | `F19-3: History cards group by scheduled date` | All History cards were put under one date | `myGamesSelectors.js` |
| 28 | F19-3 | History cards within a date run newest first | R2 | `F19-3: History cards within a date run newest first` | History cards within a date were shown in reverse time order | `myGamesSelectors.js` |
| 29 | F19-1, Section 3.2 | An official game card shows the Official type | R4 | `F19-1: an official game card shows the Official type` | The card hid the Official type | `MyGameCard.jsx` |
| 30 | F19-1, Section 3.2 | A game card shows the men's and women's player groups | R4 | `F19-1: a game card shows the %s player group` (Men, Women) | Every game card showed Coed | `myGamesFormatters.js` |
| 31 | F19-1, Section 3.2 | A Need a Sub card shows goalkeeper needs and men's and women's needs | R5 | `F19-1: a Need a Sub card shows goalkeeper needs and men's and women's needs` | The card left out goalkeeper needs; separately, it left out men's and women's needs | `MyNeedASubCard.jsx` |

## 3. Work to do

None. All work is done.
