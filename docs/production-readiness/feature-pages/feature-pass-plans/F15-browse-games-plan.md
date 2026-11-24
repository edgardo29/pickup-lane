# F15 — Browse Games Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F15-browse-games-spec.md`  
**Endpoints:** `GET /games/browse`

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | 14 market dates in two sets of seven | Yes | — |
| R2 | 3.1 | Arrows change the visible set without selecting a date | Yes | — |
| R3 | 3.1 | Show the set containing the selected date | Yes | — |
| R4 | 3.1 | Open on today and keep the selected date in the link | Yes | — |
| R5 | 3.2 | Group games by start hour with complete hour totals | Yes | — |
| R6 | 3.2 | List official and community games together in start order | Yes | — |
| R7 | 3.2 | Load the day in batches of 40 | Yes | — |
| R8 | 3.3 | Show the game type | Yes | — |
| R9 | 3.3 | Show Full only when every spot is taken | Yes | — |
| R10 | 3.3 | Show game or venue media, with a default when absent | Yes | — |
| R11 | 3.3 | Use the venue title for official games and host title for community games | Yes | — |
| R12 | 3.3 | Show city and state | Yes | — |
| R13 | 3.3; 4.5 | Show start and end times in market time | Yes | — |
| R14 | 3.3 | Show player group, format, and environment | Yes | — |
| R15 | 3.3 | Show filled and total spots | Yes | — |
| R16 | 3.3 | Show the per-player price or Free | Yes | — |
| R17 | 3.4; Section 2 | Open Game Details without reserving spots or sending notifications | Yes | — |
| R18 | 4.1 | List only eligible games for the selected date | Yes | — |
| R19 | 4.2 | Remove games exactly five minutes after start | Yes | — |
| R20 | 4.3 | Keep full games listed, without a waitlist badge | Yes | — |
| R21 | 4.4 | Count confirmed roster places and valid checkout holds only | Yes | — |
| R22 | 4.5 | Use market dates and groups, and each game’s own local listing date | Yes | — |
| R23 | 4.5 | Move the window at market midnight and admit future games as their dates enter | Yes | — |
| R24 | 4.6 | Correct missing, invalid, and out-of-range date links with history replacement | Yes | — |
| R25 | 4.7 | Order equal start times by creation time | Yes | — |
| R26 | 4.8 | Refresh while visible about once a minute and once on return | Yes | — |
| R27 | 4.8 | Keep the current list visible during refresh | Yes | — |
| R28 | 4.8 | Replace an expanded list with the first batch after successful refresh | Yes | — |
| R29 | 4.8 | Preserve cards and pagination after a failed background refresh | Yes | — |
| R30 | 4.9 | Show an empty message suggesting another date | Yes | — |
| R31 | 4.9 | Show initial-load errors with a working retry | Yes | — |
| R32 | 4.9 | Preserve cards after Load More failure and allow retry | Yes | — |
| R33 | 4.10 | Show the same public cards without viewer participation or hosting state | Yes | — |
| R34 | 4.11 | Keep host payment instructions and skill level off cards | Yes | — |
| R35 | 3.1; 3.2; frontend-standards.md Section 9 | Give date, pagination, and retry controls accurate names, states, and keyboard operation | Yes | — |
| R36 | 3.2; backend-structure.md, Collections | Protect Browse pagination cursors against edits, malformed values, and reuse for another date | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F15-9` is scenario 9); "Section 4.1" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F15-1, Section 4.10 | Both visitors can see the same public games without signing in. | R33 | `test_signed_in_and_signed_out_visitors_get_the_same_games` | Omitted games from signed-in responses | `game_routes.py` |
| 2 | F15-1, Section 4.10 | Cards show no personal participation or hosting state. | R33 | `test_cards_omit_viewer_participation_and_hosting_state` | Included viewer hosting state in cards | `game_schema.py` |
| 3 | F15-2, Section 3.1 | Today’s results load when no date is selected. | R4 | `test_missing_date_returns_todays_games` | Returned the following date instead of today | `game_service.py` |
| 4 | F15-3, Section 3.1 | The chosen date’s games load. | R4 | `test_valid_date_returns_that_days_games` | Returned the following date instead of the selected date | `game_service.py` |
| 5 | F15-6, Section 3.2, Section 4.1 | Published, active, visible, join-open games for the selected date appear together. | R6, R18 | `test_official_and_community_games_for_the_date_appear_together` | Community games excluded | `game_service.py` |
| 6 | F15-6, Section 4.1 | Draft, hidden, paused, cancelled, completed, removed, deleted, and wrong-date games do not appear. | R18 | `test_ineligible_games_are_not_listed` | Removed the public listing filters | `game_service.py` |
| 7 | F15-6, Section 4.1 | Ineligible games do not count toward hour totals. | R5, R18 | `test_ineligible_games_are_not_counted_in_hour_totals` | Counted ineligible games in hour totals | `game_service.py` |
| 8 | F15-7, Section 4.2 | A game remains listed while registration is open. | R19 | `test_game_stays_listed_until_just_before_the_cutoff` | Excluded a game before its cutoff | `game_service.py` |
| 9 | F15-7, Section 4.2 | A game disappears when its cutoff is reached, exactly five minutes after start. | R19 | `test_game_disappears_exactly_at_the_registration_cutoff` | Included a game exactly at its cutoff | `game_service.py` |
| 10 | F15-7, Section 4.2 | After registration closes, the game is removed from Browse. | R19 | `test_game_is_absent_after_the_registration_cutoff` | Included a game after its cutoff | `game_service.py` |
| 11 | F15-8, Section 4.3 | Full games with and without an accepting waitlist remain listed before the cutoff. | R20 | `test_full_game_stays_listed_with_no_spots_remaining` | Full games excluded | `game_service.py` |
| 12 | F15-9, Section 4.4 | Each confirmed player occupies one displayed spot. | R15, R21 | `test_confirmed_player_fills_a_spot` | Stopped counting confirmed players | `game_service.py` |
| 13 | F15-9, Section 4.4 | Each confirmed guest occupies one displayed spot. | R15, R21 | `test_confirmed_guest_fills_a_spot` | Stopped counting confirmed players and guests | `game_service.py` |
| 14 | F15-9, Section 4.4 | Waitlisted, cancelled, removed, and refunded participants do not occupy displayed spots. | R21 | `test_participant_that_is_not_confirmed_does_not_fill_a_spot` | Counted participants regardless of status | `game_service.py` |
| 15 | F15-10, Section 4.4 | A valid temporary hold occupies its participant spots. | R21 | `test_unexpired_checkout_hold_fills_a_spot` | Checkout holds omitted | `game_service.py` |
| 16 | F15-10, Section 4.4 | At expiration those spots stop counting, even if cleanup has not run. | R21 | `test_expired_checkout_hold_stops_filling_a_spot_before_cleanup` | Counted expired checkout holds | `game_service.py` |
| 17 | F15-10, Section 4.4; F17 Section 4.2 | Only a valid temporary checkout hold counts toward filled spots. | R21 | `test_checkout_without_an_active_payment_does_not_fill_a_spot` | Counted pending checkout without an active payment | `game_service.py` |
| 18 | F15-10, Section 4.4 | A valid temporary hold for additional guests occupies their participant spots. | R21 | `test_unexpired_additional_guest_hold_fills_a_spot` | Additional guest holds omitted | `game_service.py` |
| 19 | F15-10, Section 4.4 | At expiration additional guest hold spots stop counting, even if cleanup has not run. | R21 | `test_expired_additional_guest_hold_stops_filling_a_spot` | Counted expired additional-guest holds | `game_service.py` |
| 20 | F15-11, Section 3.3 | Each card shows the correct game type. | R8 | `test_card_includes_its_game_type` | Returned the wrong game type | `game_service.py` |
| 21 | F15-11, Section 3.3 | The title is the venue name for official games. | R11 | `test_official_card_uses_venue_title` | Returned the wrong official title | `game_service.py` |
| 22 | F15-11, Section 3.3 | The title is the host’s game title for community games. | R11 | `test_community_card_uses_host_title` | Returned the wrong community title | `game_service.py` |
| 23 | F15-11, Section 3.3 | Each card shows city and state. | R12 | `test_card_includes_city_and_state` | Returned the wrong city and state | `game_service.py` |
| 24 | F15-11, Section 3.3 | Each card includes the correct start and end time. | R13 | `test_card_includes_start_and_end_time` | Shifted both game times by an hour | `game_service.py` |
| 25 | F15-11, Section 3.3 | Each card shows the player group. | R14 | `test_card_includes_player_group` | Returned the wrong player group | `game_service.py` |
| 26 | F15-11, Section 3.3 | Each card shows the format. | R14 | `test_card_includes_format` | Returned the wrong format | `game_service.py` |
| 27 | F15-11, Section 3.3 | Each card shows the indoor or outdoor setting. | R14 | `test_card_includes_environment` | Returned the wrong environment | `game_service.py` |
| 28 | F15-11, Section 3.3 | Each card includes the correct total number of spots. | R15 | `test_card_includes_total_capacity` | Returned the wrong capacity | `game_service.py` |
| 29 | F15-11, Section 3.3 | Each paid card shows the price per player. | R16 | `test_card_includes_per_player_price` | Returned the wrong per-player price | `game_service.py` |
| 30 | F15-11, Section 3.3 | A free card shows Free. | R16 | `test_free_card_includes_free_price` | Replaced Free with another price label | `game_service.py` |
| 31 | F15-12, Section 3.3 | Available game media is supplied for the card. | R10 | `test_card_includes_its_primary_game_image` | Discarded the game image URL | `game_service.py` |
| 32 | F15-12, Section 3.3 | Available venue media is supplied when the game has no image. | R10 | `test_card_uses_published_venue_image_when_game_image_is_absent` | Discarded the published venue image URL | `game_service.py` |
| 33 | F15-12, Section 3.3 | A missing image leaves the card able to use its default visual. | R10 | `test_card_without_media_has_no_image_url` | Returned an image URL when media was absent | `game_service.py` |
| 34 | F15-13, Section 4.11 | Host payment instructions are absent from Browse cards. | R34 | `test_card_omits_host_payment_instructions` | Included host payment instructions in cards | `game_schema.py` |
| 35 | F15-13, Section 4.11 | Skill level is absent from Browse cards. | R34 | `test_card_omits_skill_level` | Included skill level in cards | `game_schema.py` |
| 36 | F15-14, Section 3.4; Section 2 | Browse itself does not reserve a spot or send notifications. | R17 | `test_browsing_creates_no_booking_roster_or_notification` | Saved a notification during Browse | `game_service.py` |
| 37 | F15-15, Section 3.2 | Cards run earliest first. | R6 | `test_cards_run_earliest_first` | Card ordering reversed | `game_service.py` |
| 38 | F15-15, Section 4.7 | Games sharing a start time follow creation order. | R25 | `test_equal_start_times_follow_creation_order` | Card ordering reversed | `game_service.py` |
| 39 | F15-15, Section 3.2 | Hour sections run earliest first. | R5 | `test_hour_groups_run_earliest_first` | Hour ordering reversed | `game_service.py` |
| 40 | F15-16, Section 3.2 | Hour totals include all eligible games, not just the loaded cards. | R5 | `test_hour_total_counts_every_eligible_game_not_just_the_loaded_batch` | Hour totals limited to loaded cards | `game_service.py` |
| 41 | F15-17, Section 4.9 | A date with no eligible games returns no games. | R18, R30 | `test_day_without_eligible_games_returns_no_games` | Included games from another date | `game_service.py` |
| 42 | F15-18, Section 3.2 | The first 40 games appear. | R7 | `test_first_batch_contains_the_first_forty_games` | Default batch shortened | `game_service.py` |
| 43 | F15-18, Section 3.2 | Load More retrieves later games in order without duplicates. | R7 | `test_load_more_returns_later_games_in_order_without_duplicates` | Cursor position ignored | `game_service.py` |
| 44 | F15-18, Section 3.2 | After the last batch there are no more games to load. | R7 | `test_last_batch_has_no_more_games_to_load` | Last batch reports more games | `game_service.py` |
| 45 | F15-20, Section 4.6 | A date before today opens today. | R24 | `test_date_before_today_opens_today` | Date bounds ignored | `game_service.py` |
| 46 | F15-20, Section 4.6 | A date after the last available day opens the last available day. | R24 | `test_date_after_the_window_opens_the_last_available_day` | Date bounds ignored | `game_service.py` |
| 47 | F15-21, Section 4.5 | When the market day changes, the 14-day window moves forward and an out-of-range date normalizes. | R22, R23, R24 | `test_market_midnight_moves_the_window_and_normalizes_old_date` | Moved the date window at UTC midnight | `game_service.py` |
| 48 | F15-22, Section 4.5 | Today and the 14-day window use the market timezone. | R1, R22 | `test_window_uses_market_today_instead_of_utc_date` | Used UTC today instead of Chicago today | `game_service.py` |
| 49 | F15-22, Section 4.5 | Across daylight-saving changes the window still contains 14 consecutive market calendar dates. | R1, R22 | `test_window_keeps_fourteen_calendar_dates_across_daylight_saving` | Date window shortened | `game_service.py` |
| 50 | F15-22, Section 4.5 | Hour groups use the Browse market timezone. | R5, R22 | `test_hour_groups_use_market_time_across_daylight_saving` | Grouped games by UTC hour | `game_service.py` |
| 51 | F15-23, Section 3.2 | Exactly 40 games fit in one batch with no later batch. | R7 | `test_exactly_forty_games_fit_in_one_batch_with_nothing_more` | Default batch shortened | `game_service.py` |
| 52 | F15-26, Section 4.1; 4.2 | Load More excludes a game that became hidden, cancelled, deleted, or past cutoff. | R18, R19 | `test_load_more_excludes_a_game_that_became_ineligible` | Kept newly ineligible games on later pages | `game_service.py` |
| 53 | F15-26, Section 3.2; 4.1; 4.2 | The later request updates hour totals to the currently eligible set. | R5, R18, R19 | `test_load_more_updates_totals_after_a_game_became_ineligible` | Counted newly ineligible games in hour totals | `game_service.py` |
| 54 | F15-33, Section 4.5 | A game beyond the 14-day window is absent until its date enters the window. | R1, R23 | `test_game_beyond_the_window_is_not_listed` | Date bounds ignored | `game_service.py` |
| 55 | F15-33, Section 4.5 | Once its date enters the window, the game appears if it still meets the public listing rules. | R18, R23 | `test_future_game_appears_when_its_date_enters_the_window` | Date window shortened | `game_service.py` |
| 56 | F15-34, Section 4.4 | On the next read after a hold expires, the filled spot count drops. | R15, R21 | `test_full_game_count_drops_when_a_hold_expires` | Kept an expired hold in the filled count | `game_service.py` |
| 57 | F15-35, Section 4.5 | The game appears under its own local calendar date within the 14-day Browse window. | R22 | `test_game_is_listed_under_its_own_local_start_date` | Market date replaces game local date | `game_service.py` |
| 58 | F15-18, Section 3.2; backend-structure.md, Collections | An edited Browse pagination cursor is rejected. | R36 | `test_edited_cursor_is_rejected` | Accepted an edited cursor | `game_service.py` |
| 59 | F15-18, Section 3.2; backend-structure.md, Collections | A malformed Browse pagination cursor is rejected. | R36 | `test_made_up_cursor_is_rejected` | Accepted malformed cursors | `game_service.py` |
| 60 | F15-18, Section 3.2; backend-structure.md, Collections | A Browse pagination cursor from another date is rejected. | R36 | `test_cursor_from_another_date_is_rejected` | Accepted a cursor from another date | `game_service.py` |

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F15-1, Section 4.10 | Browse looks the same for guests and signed-in users. | R33 | `F15-1: guests and signed-in visitors see the same Browse cards` | Changed the card title for signed-in visitors | `BrowseGameCard.jsx` |
| 2 | F15-1, Section 4.10 | Cards show no personal participation or hosting state. | R33 | `F15-1: public cards display no personal participation or hosting state` | Displayed personal participation and hosting text | `BrowseGameCard.jsx` |
| 3 | F15-2, Section 3.1 | Today’s results load. | R4 | `F15-2: opening Browse without a date loads today` | Loaded date cards discarded | `useBrowseGamesPageModel.js` |
| 4 | F15-2, Section 4.6 | The page link is replaced with today’s date. | R4, R24 | `F15-2: opening Browse without a date replaces the link with today` | Pushed the corrected date into history | `useBrowseGamesPageModel.js` |
| 5 | F15-2, Section 3.1 | A loading state appears until the first result arrives. | R4 | `F15-2: the initial loading state lasts until the first response` | Loading state omitted | `BrowseGamesPage.jsx` |
| 6 | F15-3, Section 3.1 | The linked date is selected and its games load. | R4 | `F15-3: a valid linked date selects that date and loads its games` | Loaded date cards discarded | `useBrowseGamesPageModel.js` |
| 7 | F15-3, Section 3.1 | The seven-date set containing the linked date is visible. | R3 | `F15-3: the visible set contains the linked date` | Selected date set not updated | `useBrowseGamesPageModel.js` |
| 8 | F15-4, Section 3.1 | Exactly 14 dates are available in two sets of seven. | R1 | `F15-4: the strip offers exactly fourteen dates in two sets of seven` | Date strip shortened | `browseGamesSelectors.js` |
| 9 | F15-4, Section 3.1 | The arrows switch sets without changing the selected date. | R2 | `F15-4: arrows change sets without changing the selected date` | Arrows select a date | `useBrowseGamesPageModel.js` |
| 10 | F15-4, Section 3.1 | The arrows are disabled at the ends. | R2, R35 | `F15-4: arrows are disabled at the ends` | Arrows always enabled | `BrowseDateStrip.jsx` |
| 11 | F15-5, Section 3.1 | Selecting another date gives the link a normal history entry. | R4 | `F15-5: choosing a date adds a normal history entry` | Date selection replaces history | `useBrowseGamesPageModel.js` |
| 12 | F15-5, Section 3.1 | Old games clear while the new date loads. | R4 | `F15-5: old cards clear while the selected date loads` | Old cards visible during new date load | `useBrowseGamesPageModel.js` |
| 13 | F15-5, Section 3.2 | Old pagination clears while the new date loads. | R7 | `F15-5: old pagination clears on changing date` | Old pagination visible during new date load | `BrowseGamesPage.jsx` |
| 14 | F15-5, Section 4.9 | Old errors clear while the new date loads. | R31, R32 | `F15-5: an old %s error clears on changing date` | Old errors retained after date change | `useBrowseGamesPageModel.js`, `BrowseGamesPage.jsx` |
| 15 | F15-5, F15-27, Section 3.1 | Back returns to the prior selected date while the other date is loading, loaded, or failed. | R4 | `F15-5 F15-27: Back restores the prior date when the other request is %s` | Skipped reloading the previous date on Back | `useBrowseGamesPageModel.js` |
| 16 | F15-5, Section 3.1 | On selecting a date, the strip shows the set containing it. | R3 | `F15-5: selection shows the set containing the chosen date` | Selected date set not updated | `useBrowseGamesPageModel.js` |
| 17 | F15-6, Section 3.2 | Official and community games appear together in one list. | R6 | `F15-6: official and community games share the list` | Community cards filtered out | `useBrowseGamesPageModel.js` |
| 18 | F15-7, Section 4.2 | No closed card appears after a successful refresh reaches the cutoff. | R19 | `F15-7: a card disappears when the refreshed result reaches its cutoff` | Background results not applied | `useBrowseGamesPageModel.js` |
| 19 | F15-8, Section 3.3; 4.3 | Full games with and without an accepting waitlist show Full. | R9, R20 | `F15-8: a full game with availability %s shows Full` | Omitted Full from full cards | `BrowseGameCard.jsx` |
| 20 | F15-8, Section 4.3 | Neither full game gets a separate waitlist badge. | R20 | `F15-8: a full game with availability %s has no separate waitlist badge` | Added a separate waitlist badge | `BrowseGameCard.jsx` |
| 21 | F15-11, Section 3.3 | Each card shows the correct game type. | R8 | `F15-11: a %s card shows its game type` | Swapped Official and Community labels | `BrowseGameCard.jsx` |
| 22 | F15-11, Section 3.3 | The title is the venue name for official games. | R11 | `F15-11: an official card uses the venue title` | Card titles incorrect | `BrowseGameCard.jsx` |
| 23 | F15-11, Section 3.3 | The title is the host’s game title for community games. | R11 | `F15-11: a community card uses the host game title` | Card titles incorrect | `BrowseGameCard.jsx` |
| 24 | F15-11, Section 3.3 | Each card shows city and state. | R12 | `F15-11: a %s card shows city and state` | Displayed the wrong city and state | `BrowseGameCard.jsx` |
| 25 | F15-11, F15-22, Section 3.3; 4.5 | Card times use the market timezone regardless of device timezone. | R13, R22 | `F15-11 F15-22: %s card times use Chicago time on a Tokyo device in %s` | Replaced the market-time range with other text | `BrowseGameCard.jsx` |
| 26 | F15-11, Section 3.3 | Each card shows the player group. | R14 | `F15-11: a %s card shows player group %s` | Displayed the wrong player group | `BrowseGameCard.jsx` |
| 27 | F15-11, Section 3.3 | Each card shows the format. | R14 | `F15-11: a %s card shows format %s` | Displayed the wrong format | `BrowseGameCard.jsx` |
| 28 | F15-11, Section 3.3 | Each card shows the indoor or outdoor setting. | R14 | `F15-11: a %s card shows its %s setting` | Displayed the wrong environment | `BrowseGameCard.jsx` |
| 29 | F15-11, Section 3.3 | Each card shows filled spots out of total spots. | R15 | `F15-11: a %s card shows filled spots out of capacity` | Displayed zero spots instead of the API counts | `BrowseGameCard.jsx` |
| 30 | F15-11, Section 3.3 | Each paid card shows the price per player. | R16 | `F15-11: a paid %s card shows its per-player price` | Displayed the wrong per-player price | `BrowseGameCard.jsx` |
| 31 | F15-11, Section 3.3 | A free card shows Free. | R16 | `F15-11: a free %s card shows Free` | Replaced Free with another price label | `BrowseGameCard.jsx` |
| 32 | F15-11, Section 3.3 | A card with spots available does not show Full. | R9 | `F15-11: a game with an available spot has no Full badge` | Added Full when a spot was available | `BrowseGameCard.jsx` |
| 33 | F15-12, Section 3.3 | Available game or venue media is shown. | R10 | `F15-12: a %s card shows the API image` | Discarded the API image URL | `BrowseGameCard.jsx` |
| 34 | F15-12, Section 3.3 | A missing image leaves the card with its default visual. | R10 | `F15-12: a %s card without media keeps its default visual` | Used an unrelated image instead of the default visual | `BrowseGameCard.jsx` |
| 35 | F15-13, Section 4.11 | Host payment instructions are absent from Browse cards. | R34 | `F15-13: community cards do not show host payment instructions` | Displayed host payment instructions | `BrowseGameCard.jsx` |
| 36 | F15-13, Section 4.11 | Skill level is absent from Browse cards. | R34 | `F15-13: cards do not show skill level` | Displayed skill level | `BrowseGameCard.jsx` |
| 37 | F15-14, Section 3.4 | Selecting a card opens its Game Details page. | R17 | `F15-14: choosing a card opens its Game Details page` | Card opens incorrect route | `BrowseGameCard.jsx` |
| 38 | F15-14, Section 3.4; Section 2 | Browse itself does not reserve a spot. | R17 | `F15-14: choosing a card sends no reservation or notification request` | Card sends a reservation request | `BrowseGameCard.jsx` |
| 39 | F15-15, Section 3.2 | Hour sections run earliest first. | R5 | `F15-15: hour sections run from earliest to latest` | Hour order reversed | `browseGamesSelectors.js` |
| 40 | F15-15, Section 3.2 | Cards run earliest first. | R6 | `F15-15: games keep their chronological order within an hour` | Card order reversed | `browseGamesSelectors.js` |
| 41 | F15-15, Section 4.7 | Games sharing a start time follow creation order. | R25 | `F15-15: equal start times keep the API creation order` | Card order reversed | `browseGamesSelectors.js` |
| 42 | F15-16, Section 3.2 | An hour heading shows all eligible games for that hour, not just loaded cards. | R5 | `F15-16: an hour displays the total including unloaded games` | Hour total uses loaded count | `BrowseTimeSection.jsx` |
| 43 | F15-16, Section 3.2 | Hours with no loaded cards have no section yet. | R5 | `F15-16: hours without loaded cards have no section` | Unloaded hour section displayed | `browseGamesSelectors.js` |
| 44 | F15-17, Section 4.9 | A short empty message suggests another date. | R30 | `F15-17: an empty day suggests another date or checking back` | Removed the suggestion to try another date | `BrowseGamesPage.jsx` |
| 45 | F15-17, Section 4.9 | A day with no eligible games shows no game cards. | R30 | `F15-17: an empty day has no game cards` | Displayed a game on the empty day | `BrowseGamesPage.jsx` |
| 46 | F15-17, Section 4.9 | A day with no eligible games shows no Load More control. | R30 | `F15-17: an empty day has no Load More` | Displayed Load More on the empty day | `BrowseGamesPage.jsx` |
| 47 | F15-18, Section 3.2 | The first 40 games appear. | R7 | `F15-18: the first batch displays forty cards` | First batch truncated | `useBrowseGamesPageModel.js` |
| 48 | F15-18, Section 3.2 | Load More retrieves later games in order without duplicate cards. | R7 | `F15-18: Load More appends later games in order without duplicates` | Deduplication omitted | `useBrowseGamesPageModel.js` |
| 49 | F15-18, Section 3.2 | The control disappears after the last batch. | R7 | `F15-18: Load More disappears after the final batch` | Load more shown after last batch | `useBrowseGamesPageModel.js` |
| 50 | F15-19, Section 4.6 | An invalid or impossible date selects today and loads today’s games. | R24 | `F15-19: an invalid date %s loads today` | Loaded date cards discarded | `useBrowseGamesPageModel.js` |
| 51 | F15-19, Section 4.6 | The invalid link is replaced, so Back does not return to it. | R24 | `F15-19: an invalid date %s is corrected by replacing history` | Pushed the corrected invalid date into history | `useBrowseGamesPageModel.js` |
| 52 | F15-20, Section 4.6 | The selected date moves to the nearest available boundary. | R24 | `F15-20: date %s opens the nearest available date` | Out-of-range date not normalized | `useBrowseGamesPageModel.js` |
| 53 | F15-20, Section 4.6 | The out-of-range link is replaced. | R24 | `F15-20: correcting date %s replaces its history entry` | Pushed the corrected boundary date into history | `useBrowseGamesPageModel.js` |
| 54 | F15-21, Section 4.5 | On the next visible refresh, the 14-day window moves forward. | R1, R23 | `F15-21: market midnight moves the fourteen-date window` | Midnight window not updated | `useBrowseGamesPageModel.js` |
| 55 | F15-21, Section 4.5; 4.6 | An out-of-range selected date and link normalize to the new window. | R23, R24 | `F15-21: market midnight corrects the old selected date by replacing history` | Pushed the corrected midnight date into history | `useBrowseGamesPageModel.js` |
| 56 | F15-22, Section 4.5 | The strip still contains 14 consecutive market calendar dates across daylight-saving changes. | R1, R22 | `F15-22: fourteen consecutive market dates span the %s daylight-saving change` | Date strip shortened | `browseGamesSelectors.js` |
| 57 | F15-22, Section 4.5 | Hour groups use the market timezone regardless of device timezone. | R5, R22 | `F15-22: hour headings use market hours on a Tokyo device` | Hour label incorrect | `browseGameFormatters.js` |
| 58 | F15-23, Section 3.2 | Exactly 40 games all appear. | R7 | `F15-23: exactly forty games all appear` | First batch truncated | `useBrowseGamesPageModel.js` |
| 59 | F15-23, Section 3.2 | Exactly 40 games have no Load More control. | R7 | `F15-23: exactly forty games need no Load More` | Load more shown after last batch | `useBrowseGamesPageModel.js` |
| 60 | F15-24, Section 4.9 | An error with Retry replaces results after an initial failure. | R31 | `F15-24: a first-load failure displays an error with Retry` | First-load error omitted | `BrowseGamesPage.jsx` |
| 61 | F15-24, Section 4.9 | A successful retry shows the selected day’s games or its empty state. | R31 | `F15-24: first-load Retry recovers to %s` | First-load retry disabled | `BrowseGamesPage.jsx` |
| 62 | F15-25, Section 4.9 | Already loaded cards remain visible after Load More fails. | R32 | `F15-25: a failed Load More preserves the loaded cards` | Load more failure clears cards | `useBrowseGamesPageModel.js` |
| 63 | F15-25, Section 4.9 | An inline Retry appears after Load More fails. | R32 | `F15-25: a failed Load More offers an inline Retry` | Inline retry omitted | `BrowseGamesPage.jsx` |
| 64 | F15-25, Section 4.9 | A successful Load More retry adds the remaining games without duplicates. | R32 | `F15-25: Load More Retry uses the same cursor and appends the remainder` | Load more retry disabled | `BrowseGamesPage.jsx` |
| 65 | F15-27, Section 3.1 | A late response for the old date cannot replace the newly selected date’s results. | R4 | `F15-27: a late first-page result cannot replace a newer date` | Stale first-page result applied | `useBrowseGamesPageModel.js` |
| 66 | F15-27, Section 3.1; 3.2 | A late response for the old date cannot append to the newly selected date’s results. | R4, R7 | `F15-27: a late Load More result cannot append after a date change` | Stale load more result appended | `useBrowseGamesPageModel.js` |
| 67 | F15-28, Section 4.8 | A late Load More response cannot append cards after the refreshed first batch replaces the list. | R7, R28 | `F15-28: a late Load More result cannot append after refresh replacement` | Stale load more result appended | `useBrowseGamesPageModel.js` |
| 68 | F15-29, Section 4.8 | While visible, refresh occurs about once a minute. | R26 | `F15-29: a visible page refreshes once each minute` | Refresh interval incorrect | `useBrowseGamesPageModel.js` |
| 69 | F15-29, Section 4.8 | Returning to the visible page refreshes once. | R26 | `F15-29: returning to a visible page refreshes once` | Return events refresh more than once | `useBrowseGamesPageModel.js` |
| 70 | F15-29, Section 4.8 | Returning to a hidden tab refreshes once when it becomes visible. | R26 | `F15-29: returning from a hidden tab refreshes once when visible` | Return events refresh more than once | `useBrowseGamesPageModel.js` |
| 71 | F15-29, Section 4.8 | Focus followed by visibility on return starts only one refresh. | R26 | `F15-29: focus before visibility starts only one refresh on return` | Return events refresh more than once | `useBrowseGamesPageModel.js` |
| 72 | F15-29, Section 4.8 | The next successful result reflects current spot counts. | R15, R26 | `F15-29: a refresh shows the current spot count` | Background results not applied | `useBrowseGamesPageModel.js` |
| 73 | F15-29, Section 4.8 | The next successful result reflects current game availability. | R18, R26 | `F15-29: a refresh removes a game that is no longer available` | Background results not applied | `useBrowseGamesPageModel.js` |
| 74 | F15-29, Section 4.8 | Hidden tabs do not start interval refreshes. | R26 | `F15-29: a hidden tab does not start interval refreshes` | Hidden page refreshes | `useBrowseGamesPageModel.js` |
| 75 | F15-30, Section 4.8 | Existing cards stay visible while refreshing. | R27 | `F15-30: an expanded list remains visible while refresh is pending` | Background refresh clears cards | `useBrowseGamesPageModel.js` |
| 76 | F15-30, Section 4.8 | A successful refresh replaces the expanded list with the current first batch. | R28 | `F15-30: a successful refresh replaces the expanded list with the first batch` | Background results not applied | `useBrowseGamesPageModel.js` |
| 77 | F15-30, Section 4.8 | A successful refresh resets Load More. | R7, R28 | `F15-30: a successful refresh resets the Load More cursor` | Discarded the refreshed pagination cursor | `useBrowseGamesPageModel.js` |
| 78 | F15-31, Section 4.8 | Existing cards and pagination stay visible without a full-page error after a failed background refresh. | R29 | `F15-31: a failed refresh preserves cards and working pagination without a full-page error` | Background failure replaces list | `useBrowseGamesPageModel.js` |
| 79 | F15-31, Section 4.8 | A later successful refresh can update the list. | R29 | `F15-31: the next successful refresh recovers after a failed refresh` | Background results not applied | `useBrowseGamesPageModel.js` |
| 80 | F15-32, Section 3.1 | Dates and arrows have clear labels. | R35 | `F15-32: dates and arrows have clear accessible labels` | Date labels incorrect | `BrowseDateStrip.jsx` |
| 81 | F15-32, Section 3.1 | The selected date is identified to assistive technology. | R35 | `F15-32: assistive technology can identify the selected date` | Selected date state omitted | `BrowseDateStrip.jsx` |
| 82 | F15-32, Section 3.1 | Date navigation works with the keyboard. | R35 | `F15-32: the keyboard can select another date` | Keyboard date action disabled | `BrowseDateStrip.jsx` |
| 83 | F15-32, Section 3.2 | Load More works with the keyboard. | R35 | `F15-32: Load More works with the keyboard` | Load more action disabled | `BrowseGamesPage.jsx` |
| 84 | F15-32, Section 3.2 | Load More is disabled while loading. | R35 | `F15-32: Load More is disabled while its response is pending` | Pending load more enabled | `BrowseGamesPage.jsx` |
| 85 | F15-32, Section 4.9 | Retry remains operable with the keyboard. | R35 | `F15-32: Retry works with the keyboard` | First-load retry disabled | `BrowseGamesPage.jsx` |
| 86 | F15-34, Section 4.4; 4.8 | On the next successful refresh after hold expiry, the filled spot count drops. | R15, R21 | `F15-34: expired holds reduce the filled count on refresh` | Kept the old count after hold expiry | `useBrowseGamesPageModel.js` |
| 87 | F15-34, Section 3.3; 4.4 | The Full badge disappears when hold expiry makes a spot available. | R9, R21 | `F15-34: expired holds remove Full when a spot opens` | Kept Full after a hold expired | `useBrowseGamesPageModel.js` |
| 88 | F15-36, Section 4.6 | An invalid date keeps or reloads today’s games, including after another date’s pending or failed request. | R24 | `F15-36: an invalid link restores today when the other request is %s` | Loaded the last available date instead of today | `useBrowseGamesPageModel.js` |
| 89 | F15-36, Section 4.6 | An invalid date introduced while another date is open resets selection and results to today. | R24 | `F15-36: an invalid link on another date switches results and selection to today` | Invalid date does not retain or reload today | `useBrowseGamesPageModel.js` |
| 90 | F15-36, Section 4.6 | An invalid date introduced while Browse is open is corrected with history replacement. | R24 | `F15-36: an invalid link introduced while Browse is open is replaced` | Pushed the corrected invalid date into history | `useBrowseGamesPageModel.js` |

## 3. Work to do

None. All work is done.
