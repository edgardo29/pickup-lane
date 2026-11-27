# F18 — Edit Game Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F18-edit-game-spec.md`  
**Endpoints:** `GET /games/{game_id}`, `GET /venues/{venue_id}`, `GET /community-game-details/games/{game_id}/host-edit`, `PATCH /games/{game_id}/host-edit`, `PUT /community-game-details/games/{game_id}/host-edit`

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | The page loads the game, venue, and community details into the four-step form | Yes | — |
| R2 | 3.1 | The host can review the changes, move between steps, and save; a successful save returns to Game Details | Yes | — |
| R3 | 3.1 | Complete success only after both saves; a partial save names what saved and what did not, keeps the entered values, and retries only the failed part | Yes | — |
| R4 | 3.1 | Cancel, or Back from the first step, returns to Game Details; changed fields ask to keep editing or discard | Yes | — |
| R5 | 4.1 | Only the owner can edit an active, published community game before its start; an unrelated user, missing game, official game, or inactive game cannot be changed | Yes | — |
| R6 | 4.1 | A changed start stays within the 21-day local scheduling limit | Yes | — |
| R7 | 4.1 | A host who is suspended or restricted from publishing can still edit games they already host; new publication stays blocked | Yes | — |
| R8 | 4.2 | Before a non-host player has active participation, setup, location, price, and details can change under the creation rules | Yes | — |
| R9 | 4.2 | Once a player other than the host is confirmed or waitlisted, date, time, location, format, indoor/outdoor setting, and player price lock, and capacity can only increase; the host's own guests do not lock these fields, but capacity never drops below the places the host and their guests hold | Yes | — |
| R10 | 4.1 | Saving an edit requires a verified email; an owner whose email is not verified sees the email-verification requirement and Verify Email action instead of the form, and the link returns to this game's Edit Game page; a visitor who cannot edit sees only the access error | Yes | — |
| R11 | 4.2 | The backend rechecks these limits when saving | Yes | — |
| R12 | 4.3 | A location change reuses the existing venue record for the same facility or creates one only if none exists; the previous venue record stays intact; an address alone does not identify a facility | Yes | — |
| R13 | 4.3 | Editing charges no new publication fee; host payment methods save as community details | Yes | — |
| R14 | 4.3 | The general update and the community-detail update are separate; the page never reports complete success after only one; a retry does not replay the successful one; when a free game becomes paid, the payment methods save first, and the backend refuses to make a game paid without a host payment method | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F18-8` is scenario 8); "Section 4.2" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F18-1 | The owner loads the game's community details for editing | R1 | `test_owner_loads_the_community_details_for_editing` | The owner was refused their own community details | `community_game_detail_service.py` |
| 2 | F18-2, Section 4.3 | Permitted setup, notes, rules, and host payment changes save before players join | R8, R13 | `test_permitted_changes_save_before_players_join` | A permitted skill-level change was not saved | `community_game_edit_service.py` |
| 3 | F18-2, Section 4.3 | Saving creates no new game and no publish fee | R13 | `test_saving_creates_no_new_game_and_no_publish_fee` | Saving an edit created a publish fee | `community_game_edit_service.py` |
| 4 | F18-2, Section 4.2 | A free game can become paid once it has a host payment method, and back, before players join | R8, R14 | `test_a_free_game_can_become_paid_and_back_before_players_join` | A price change did not switch how players pay | `community_game_edit_service.py` |
| 5 | F18-3, Section 4.3 | Changing to an existing facility reuses its venue record | R12 | `test_changing_to_an_existing_facility_reuses_its_venue_record` | A facility written with different case and spacing was not matched to its venue | `venue_service.py` |
| 6 | F18-3, Section 4.3 | A distinct facility at a shared address gets a new venue record | R12 | `test_a_distinct_facility_at_a_shared_address_gets_a_new_venue_record` | A facility was matched by its address alone | `venue_service.py` |
| 7 | F18-3, Section 4.3 | Neither change alters the old venue or other games using it | R12 | `test_a_location_change_leaves_the_old_venue_and_its_other_games_alone` | A location change renamed the old venue | `community_game_edit_service.py` |
| 8 | F18-3, Section 4.3 | A changed neighborhood alone does not create another facility | R12 | `test_neighborhood_alone_does_not_create_another_facility` | An unchanged facility was treated as a location change | `community_game_edit_service.py` |
| 9 | F18-4 | Capacity can increase after a player joins or waitlists, and the roster stays intact | R9 | `test_capacity_can_increase_after_players_join_and_the_roster_stays` | Any capacity change was refused after players joined | `community_game_edit_service.py` |
| 10 | F18-4 | Notes save after a player joins | R9 | `test_notes_save_after_a_player_joins` | Game notes were locked after players joined | `game_rules.py` |
| 11 | F18-4, Section 4.2 | Player group and skill level, which are not locked, stay editable after players join | R9 | `test_player_group_and_skill_level_stay_editable_after_players_join` | Skill level was locked after players joined | `game_rules.py` |
| 12 | F18-6 | A signed-out visitor cannot load or save an edit | R5 | `test_signed_out_visitor_cannot_load_or_save_an_edit` | A signed-out request was refused as forbidden instead of asked to sign in | `auth_service.py` |
| 13 | F18-6 | A user who is not the owner cannot load or save an edit, and nothing changes | R5 | `test_another_user_cannot_load_or_save_the_game` | Any signed-in user could save the game | `community_game_edit_service.py` |
| 14 | F18-6 | A missing game cannot be edited through either save | R5 | `test_a_missing_game_cannot_be_edited` | A missing game was reported as a bad request instead of not found | `community_game_edit_service.py` |
| 15 | F18-6 | An official game cannot be edited through either save | R5 | `test_an_official_game_cannot_be_edited_here` | An official game could be edited, with the host check also off since an official game has no host | `community_game_edit_service.py` |
| 16 | F18-7 | A game that is no longer active (cancelled, completed, expired, or removed) rejects edits and stays unchanged | R5 | `test_a_game_that_is_no_longer_active_rejects_edits` | Cancelled, completed, expired, and removed games accepted edits | `game_rules.py` |
| 17 | F18-7 | An unpublished game (draft or archived) rejects edits and stays unchanged | R5 | `test_an_unpublished_game_rejects_edits` | Draft and archived games accepted edits | `community_game_edit_service.py`, `community_game_detail_service.py` |
| 18 | F18-7 | A game rejects edits from the moment it starts, and stays unchanged | R5 | `test_a_started_game_rejects_edits` | A game that had started accepted edits | `game_rules.py` |
| 19 | F18-8, Section 4.2 | Date, time, location, format, indoor/outdoor setting, and price are rejected once a non-host player is confirmed or waitlisted, checked when saving | R9, R11 | `test_protected_fields_lock_once_a_player_is_active` | Protected fields stayed editable after players joined | `community_game_edit_service.py` |
| 20 | F18-8, Section 4.2 | A player who has left (cancelled, late-cancelled, or removed) does not lock the game | R9 | `test_a_player_who_has_left_does_not_lock_the_game` | Players who had left still locked the game | `game_rules.py` |
| 21 | F18-9 | Capacity cannot drop after a non-host player joins, and the prior capacity stays | R9 | `test_capacity_cannot_drop_after_players_join` | Capacity could drop after players joined | `community_game_edit_service.py` |
| 22 | F18-16, Section 4.1 | An owner whose email is not verified cannot save an edit, and the game stays unchanged | R10 | `test_an_owner_whose_email_is_not_verified_cannot_save_an_edit` | An owner with an unverified email could save | `auth_service.py` |
| 23 | F18-10 | An invalid schedule, a start in the past, is not saved | R8 | `test_an_invalid_schedule_is_not_saved` | Both the edit check and the shared start check accepted a start in the past | `community_game_edit_service.py`, `game_rules.py` |
| 24 | F18-10 | An invalid capacity is not saved | R8 | `test_an_invalid_capacity_is_not_saved` | A capacity over 99 passed both the request check and the shared limit | `game_schema.py`, `game_rules.py` |
| 25 | F18-10 | An incomplete location is not saved | R8 | `test_incomplete_location_is_not_saved` | A location without a city was accepted | `community_game_edit_service.py` |
| 26 | F18-10 | A paid game without a host payment method is not saved | R8, R13 | `test_paid_game_needs_a_host_payment_method` | A paid game could save with no host payment method | `community_game_detail_service.py` |
| 27 | F18-10, Create Game 3.1 | More than two host payment methods are not saved | R8, R13 | `test_more_than_two_host_payment_methods_are_not_saved` | Three host payment methods were accepted | `community_game_detail_schema.py` |
| 28 | F18-10, Create Game 4.1 | Moving the game to a date the host already has another active game on is rejected | R8 | `test_moving_to_a_date_with_another_of_the_hosts_games_is_rejected` | A moved game kept its old local date, so the date clash went unnoticed | `community_game_edit_service.py` |
| 29 | F18-12 | A start exactly 21 days ahead saves | R6 | `test_a_start_exactly_21_days_ahead_saves` | A start exactly 21 days ahead was refused | `game_rules.py` |
| 30 | F18-12 | A start 22 days ahead is rejected without changing the game | R6 | `test_a_start_22_days_ahead_is_rejected` | A start 22 days ahead was accepted | `community_game_edit_service.py` |
| 31 | F18-13 | A suspended owner can still edit an existing hosted game | R7 | `test_suspended_owner_can_still_edit_an_existing_game` | The edit save required an active account | `game_routes.py` |
| 32 | F18-13 | A suspended owner still cannot publish a new game | R7 | `test_a_suspended_owner_still_cannot_publish_a_new_game` | A suspended host could publish a new game | `community_game_publish_routes.py`, `community_game_publish_service.py` |
| 33 | F18-13, Section 4.1 | A host restricted from publishing can still edit an existing hosted game | R7 | `test_a_host_restricted_from_publishing_can_still_edit_an_existing_game` | The edit save required permission to publish new games | `community_game_edit_service.py` |
| 34 | F18-17, Section 4.2 | The host's own guests do not lock date or location changes | R9 | `test_the_hosts_own_guests_do_not_lock_date_or_location_changes` | The host's own guests locked the game | `game_service.py` |
| 35 | F18-17, Section 4.2 | Capacity cannot drop below the places the host and their guests hold, and the prior capacity stays | R9 | `test_capacity_cannot_drop_below_the_places_the_host_and_their_guests_hold` | The capacity check left out the host's party | `community_game_edit_service.py` |
| 36 | F18-19, Section 4.3 | A free game cannot become paid while it has no host payment method, and stays free | R14 | `test_a_free_game_cannot_become_paid_without_a_host_payment_method` | A free game became paid with no host payment method | `community_game_edit_service.py` |
| 37 | F18-1, Section 3.1 | The owner loads their game with the host shown, whether staff have hidden it and whether the owner is suspended or unverified | R1, R7, R10 | `test_the_owner_loads_their_game_with_the_host_shown` | The game load hid its host from the owner | `game_service.py` |
| 38 | F18-2, Section 4.3 | Edited game notes appear on Game Details | R8, R13 | `test_edited_game_notes_appear_on_game_details` | Edited notes did not reach the description | `community_game_edit_service.py` |
| 39 | F18-10, Create Game 4.1 | A format outside 3v3–11v11 is not saved | R8 | `test_a_format_outside_3v3_to_11v11_is_not_saved` | The edit request accepted any format | `game_schema.py` |
| 40 | F18-18, Section 4.3 | When the payment methods save and the game update is then refused, the game stays free and keeps the payment methods | R14 | `test_a_refused_game_update_after_the_payment_methods_save_leaves_the_game_free` | A refused game update kept its price change | `community_game_edit_service.py` |

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F18-1 | Existing values load into the four-step form, including venue and community details | R1 | `F18-1: the existing game, venue, and community details load into the form` | The venue's ZIP code was not loaded into the form | `createGameMappers.js` |
| 2 | F18-1, Section 3.1 | The owner of a game staff have hidden can open it in the form | R1 | `F18-1: the owner of a game staff have hidden can open it in the form` | Failed before the change | — |
| 3 | F18-2, Section 3.1 | The host can move between the steps and review the proposed changes | R2 | `F18-2: the host can move between the steps and review the proposed changes` | Back skipped a step | `CreateGamePage.jsx` |
| 4 | F18-2 | A permitted save returns to Game Details | R2 | `F18-2: a permitted save returns to Game Details` | A save did not return to Game Details | `useCreateGamePublish.js` |
| 5 | F18-5 | Cancel without changes returns to Game Details | R4 | `F18-5: Cancel without changes returns to Game Details` | Cancel asked about changes when there were none | `CreateGamePage.jsx` |
| 6 | F18-5 | Cancel with changes asks to keep editing or discard the changes, in words that fit a game already published | R4 | `F18-5: Cancel with changes asks to keep editing or discard the changes` | Failed before the change | — |
| 7 | F18-5 | Discard returns to Game Details without saving | R4 | `F18-5: Discard returns to Game Details without saving` | Discard did not leave the form | `CreateGamePage.jsx` |
| 8 | F18-5 | Keep editing stays on the form with the changes | R4 | `F18-5: Keep editing stays on the form with the changes` | Keep editing dropped the changes | `CreateGamePage.jsx` |
| 9 | F18-5, Section 3.1 | Back from the first step returns to Game Details the same way | R4 | `F18-5: Back from the first step asks about changes, and returns to Game Details once there are none` | Failed before the change | — |
| 10 | F18-6 | A signed-out visitor is sent to sign in | R5 | `F18-6: a signed-out visitor is sent to sign in` | A signed-out visitor was not sent to sign in | `RouteGuards.jsx` |
| 11 | F18-6 | A visitor who is not the owner sees an error instead of the form | R5 | `F18-6: a visitor who is not the host sees an error instead of the form` | A visitor who is not the host got the form | `createGameApi.js` |
| 12 | F18-6 | An official game cannot be edited here | R5 | `F18-6: an official game cannot be edited here` | An official game opened in the form | `createGameApi.js` |
| 13 | F18-10 | An invalid schedule is identified on the Game step and not saved | R6, R8 | `F18-10: a date past the 21-day limit is reported on the Game step and not saved` | A date past 21 days moved on to Location | `createGameValidation.js` |
| 14 | F18-10 | A missing capacity is identified on the Game step and not saved (the list offers only counts the format allows) | R8 | `F18-10: a missing capacity is reported on the Game step and not saved` | A blank capacity moved on to Location, with the format's minimum check also off | `createGameValidation.js` |
| 15 | F18-10 | An incomplete location is identified on the Location step and not saved | R8 | `F18-10: an incomplete location is reported on the Location step and not saved` | A missing street address moved on to Notes | `createGameValidation.js` |
| 16 | F18-10 | A paid game without a host payment method is identified on the Notes step and not saved | R8, R13 | `F18-10: a paid game without host payment details is reported on the Notes step and not saved` | Missing payment details moved on to Review | `createGameValidation.js` |
| 17 | F18-11 | A failed game load shows an error instead of the form | R1 | `F18-11: a failed load shows the error without the form` | A failed load showed no error | `useCreateGameContext.js` |
| 18 | F18-11 | A failed venue load shows an error instead of a form missing its address | R1 | `F18-11: a failed venue load shows the error instead of a form missing its address` | A failed venue load opened the form without its address | `createGameApi.js` |
| 19 | F18-13 | A suspended host can still edit a game they host | R7 | `F18-13: a suspended host can still edit a game they host` | Editing loaded the publish fee history a suspended account is refused | `useCreateGameContext.js` |
| 20 | F18-14 | When only the community-detail update fails, the page names what saved and what did not | R3, R14 | `F18-14: the page names what saved and what did not` | The notice did not say which part saved | `useCreateGamePublish.js` |
| 21 | F18-14 | The entered community details are kept | R3 | `F18-14: the entered payment details are kept` | A failed save reset the entered payment details | `CreateGamePage.jsx` |
| 22 | F18-14 | A retry sends only the failed community-detail update | R3, R14 | `F18-14: a retry sends only the payment details` | A retry sent the game update again | `useCreateGamePublish.js` |
| 23 | F18-14 | Complete success comes only after both parts save | R3, R14 | `F18-14: the edit is reported complete only after both parts save` | A failed payment-details save reported complete success | `useCreateGamePublish.js` |
| 24 | F18-11, F18-15 | When the general update fails, the entered values are kept and the unsaved part is named | R3 | `F18-15: the entered values are kept and the unsaved part is named` | The notice did not name the unsaved game update | `useCreateGamePublish.js` |
| 25 | F18-11, F18-15 | A failed general update shows no complete success and sends no community-detail update | R3, R14 | `F18-15: no complete success is shown and the payment details are not sent` | The payment details were sent although the game update failed | `useCreateGamePublish.js` |
| 26 | F18-16, Section 4.1 | An owner whose email is not verified sees the email-verification requirement and Verify Email action instead of the form | R10 | `F18-16: an owner whose email is not verified sees the email-verification requirement instead of the form` | The requirement was not shown on Edit Game | `CreateGamePage.jsx` |
| 27 | F18-16, Section 4.1 | The verification email returns the owner to this game's Edit Game page | R10 | `F18-16: the verification email returns the owner to this game's Edit Game page` | The verification email returned to Create Game | `CreateGamePage.jsx` |
| 28 | F18-16, Section 4.1 | After verifying, the link continues to this game's Edit Game page | R10 | `F18-16: after verifying, the link continues to this game's Edit Game page` | The link continued to Create Game | `emailVerificationReturn.js` |
| 29 | F18-20, Section 4.1 | A visitor who cannot edit the game and has an unverified email sees the access error without the verification requirement | R10 | `F18-20: a visitor who cannot edit the game and has an unverified email sees only the access error` | The requirement showed beside the access error | `CreateGamePage.jsx` |
| 30 | F18-18, Section 4.3 | When a free game becomes paid, the payment methods save before the game update | R14 | `F18-18: the payment methods save before the game update` | The game update saved first | `useCreateGamePublish.js` |
| 31 | F18-18, Section 4.3 | When the game update then fails, the page names the saved and unsaved parts and shows no complete success | R3, R14 | `F18-18: when the game update then fails, the page names the saved and unsaved parts` | The notice did not say the payment details saved | `useCreateGamePublish.js` |
| 32 | F18-18, Section 4.3 | A retry then sends only the game update | R3, R14 | `F18-18: a retry then sends only the game update` | A retry sent the payment details again | `useCreateGamePublish.js` |
| 33 | F18-1, F18-2 | A free game opens with no player payment needed, so it saves without payment details | R1, R8 | `F18-1, F18-2: a free game opens with no player payment needed, so it saves without payment details` | A free game opened with Venmo | `createGameMappers.js` |

## 3. Work to do

None. All work is done.
