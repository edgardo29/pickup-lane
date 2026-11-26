# F20 — Need a Sub Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F20-need-a-sub-spec.md`  
**Endpoints:** `GET /need-a-sub/posts/cards`, `GET /need-a-sub/posts/{sub_post_id}`

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | Everyone can browse All Posts summary cards; signed-in users can switch to My Posts | Yes | — |
| R2 | 3.1 | A date strip offers 14 dates in two sets of seven; selecting a date shows that day's posts; switching sets selects the first date in the new set | Yes | — |
| R3 | 3.1 | Posts are grouped by start hour and ordered by start time | Yes | — |
| R4 | 3.1 | Cards show venue, city/state, time, player group, format, indoor/outdoor setting, exact types of subs needed, open counts, and confirmed spots | Yes | — |
| R5 | 3.1 | Selecting a card opens Post Detail for a signed-in visitor; a guest is directed to Sign In or Create Account with that post as the return destination | Yes | — |
| R6 | 3.1 | Load More appends later posts when available | Yes | — |
| R7 | 3.2 | Create Post switches to the create panel on the same URL | Yes | — |
| R8 | 3.3 | Signed-out visitors browse cards and dates but cannot use My Posts or create a post | Yes | — |
| R9 | 3.3 | An unverified signed-in account can browse public posts | Yes | — |
| R10 | 4.1 | The public list holds only summary cards for visible, active, future posts on the selected date | Yes | — |
| R11 | 4.1 | Full post details require sign-in, at the page and at the backend | Yes | — |
| R12 | 4.1 | After sign-in or account creation, a guest returns to the selected post if it is still available; otherwise the game-discovery fallback applies | Yes | — |
| R13 | 4.1 | My Posts shows only posts owned by the signed-in user | Yes | — |
| R14 | 4.1 | Cancelled, removed, expired, and past posts do not appear | Yes | — |
| R15 | 4.2 | Open counts drop only for confirmed subs, not pending requests; a full need stays on its card | Yes | — |
| R16 | 4.2 | Posts with the same start time follow creation order | Yes | — |
| R17 | 4.2 | The first batch holds up to 40 posts; later batches continue the same order | Yes | — |
| R18 | 4.3 | Changing tab or date starts a fresh first batch | Yes | — |
| R19 | 4.3 | The list refreshes when the browser regains focus or visibility | Yes | — |
| R20 | 4.3 | A loading skeleton, empty message, and error alert show the result state | Yes | — |
| R21 | 4.3 | A failed Load More keeps the shown posts, and Load More can be tried again | Yes | — |
| R22 | 4.4 | Need a Sub posts are outside games, separate from Pickup Lane game listings | Yes | — |
| R23 | 3.1 | Dates, card times, and hour groups use the market time zone (America/Chicago), not the device's | Yes | — |
| R24 | 4.3 | When the page is shown again after the market date changes, the strip starts at the new today and a passed selected date moves to today | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F20-5` is scenario 5); "Section 4.1" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F20-1, Section 3.3 | A signed-out visitor gets All Posts summary cards without signing in | R1, R8 | `test_signed_out_visitors_get_all_posts` | Signed-out visitors were refused All Posts | `need_a_sub_post_service.py` |
| 2 | F20-1, Section 3.3 | A signed-out visitor cannot open My Posts | R8 | `test_signed_out_visitors_cannot_open_my_posts` | My Posts let a signed-out visitor in | `need_a_sub_post_service.py` |
| 3 | F20-2, Section 3.3 | A signed-in account gets All Posts, whether active, unverified, or suspended (User Detail, Section 4.10) | R1, R9 | `test_signed_in_accounts_get_all_posts_including_unverified_and_suspended` | Signed-in accounts were refused All Posts | `need_a_sub_post_service.py` |
| 4 | F20-4 | A signed-in account opens My Posts, whether active, unverified, or suspended (User Detail, Section 4.10) | R1, R13 | `test_signed_in_accounts_open_my_posts_including_unverified_and_suspended` | Signed-in accounts were refused My Posts | `need_a_sub_post_service.py` |
| 5 | F20-4 | A deleted or deleting account cannot open My Posts | R13 | `test_a_deleted_or_deleting_account_cannot_open_my_posts` | Sign-in accepted deleted and deleting accounts | `auth_service.py` |
| 6 | F20-3 | A date returns the posts filed under that local calendar date | R2, R10 | `test_a_date_lists_the_posts_filed_under_that_chicago_date` | The list ignored the selected date | `need_a_sub_post_service.py` |
| 7 | F20-4, Section 4.1 | My Posts returns only the signed-in owner's eligible posts for that date | R13 | `test_my_posts_shows_only_the_owners_eligible_posts_that_day` | My Posts included other owners' posts | `need_a_sub_post_service.py` |
| 8 | F20-5, Section 4.1 | A post that is not active (cancelled, completed, expired, or removed) is absent | R10, R14 | `test_a_post_that_is_not_active_does_not_appear` | The list included posts that are not active | `need_a_sub_post_service.py` |
| 9 | F20-5 | A hidden post is absent | R10 | `test_a_hidden_post_does_not_appear` | The list included hidden posts | `need_a_sub_post_service.py` |
| 10 | F20-5 | A post on another date is absent | R10 | `test_a_post_on_another_date_does_not_appear` | The list ignored the selected date | `need_a_sub_post_service.py` |
| 11 | F20-5, Section 4.1 | A post that has started is absent | R10, R14 | `test_a_post_that_has_started_does_not_appear` | The list included posts that had started | `need_a_sub_post_service.py` |
| 12 | F20-5 | Posts are sorted by start time | R3 | `test_posts_are_sorted_by_start_time` | Posts were sorted latest start first | `need_a_sub_post_service.py` |
| 13 | F20-5, Section 4.2 | Posts with the same start time follow creation order | R16 | `test_posts_with_the_same_start_time_follow_creation_order` | Posts with the same start were sorted newest first | `need_a_sub_post_service.py` |
| 14 | F20-6 | Each card retains its configured need labels, including a full need | R4, R15 | `test_each_card_keeps_every_configured_need_including_a_full_one` | A full need was left off its card | `need_a_sub_post_service.py` |
| 15 | F20-6, Section 4.2 | Open and filled counts reflect confirmations rather than pending requests or any other request status | R15 | `test_only_a_confirmed_request_fills_a_spot` | Every request status filled a spot; separately, no request filled a spot | `need_a_sub_post_service.py` |
| 16 | F20-8, Section 4.2 | More than 40 posts come in batches of up to 40 that continue in order and end | R6, R17 | `test_more_than_40_posts_come_in_ordered_batches_that_end` | Load More ignored its position and started over | `need_a_sub_post_service.py` |
| 17 | F20-8 | Exactly 40 posts fit in one batch with no further batch | R17 | `test_exactly_40_posts_fit_in_one_batch` | Exactly 40 posts still offered a further batch | `need_a_sub_post_service.py` |
| 18 | F20-8 | An altered Load More position is refused | R17 | `test_a_changed_cursor_is_refused` | A Load More position's signature was not checked | `pagination_cursor.py` |
| 19 | F20-12 | A Load More position for another date is refused | R17, R18 | `test_a_cursor_does_not_work_for_another_date` | A Load More position was not tied to its date | `need_a_sub_post_service.py` |
| 20 | F20-12 | An All Posts Load More position is refused for My Posts | R17, R18 | `test_an_all_posts_cursor_does_not_work_for_my_posts` | A Load More position was not tied to its tab | `need_a_sub_post_service.py` |
| 21 | F20-9 | A date with no eligible posts returns no posts | R20 | `test_a_date_with_no_eligible_posts_returns_an_empty_list` | A cancelled post counted as eligible | `need_a_sub_post_service.py` |
| 22 | F20-9 | My Posts with no posts on that date returns no posts | R20 | `test_my_posts_is_empty_when_the_account_has_no_posts_that_day` | My Posts included other owners' posts | `need_a_sub_post_service.py` |
| 23 | F20-13 | A new first batch reflects a post's status change | R10, R14 | `test_a_new_first_batch_reflects_a_status_change` | A cancelled post stayed in the list | `need_a_sub_post_service.py` |
| 24 | F20-13 | A new first batch reflects a changed confirmed count | R15 | `test_a_new_first_batch_reflects_a_changed_confirmed_count` | Card counts ignored confirmations | `need_a_sub_post_service.py` |
| 25 | F20-14, Section 4.1 | A guest asking for a post gets only its public summary, not the full details | R11 | `test_a_guest_gets_only_the_public_summary_of_a_post` | A guest got the full post | `need_a_sub_post_service.py` |
| 26 | F20-14, Section 4.1 | A signed-in visitor gets the full post | R11 | `test_a_signed_in_visitor_gets_the_full_post` | A signed-in visitor got only the public summary | `need_a_sub_post_service.py` |
| 27 | F20-15 | A post that became unavailable (cancelled, removed, expired, completed, or hidden) is not shown | R12 | `test_a_post_that_became_unavailable_is_not_shown` | An unavailable post was still shown | `need_a_sub_post_service.py` |
| 28 | F20-15 | A post that has started is not shown to a visitor not connected to it | R12 | `test_a_post_that_started_is_not_shown_to_an_unconnected_visitor` | A started post was still shown to an unconnected visitor | `need_a_sub_post_service.py` |

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F20-1 | Public summary cards and date controls appear without signing in | R1, R8 | `F20-1: public summary cards and date controls appear without signing in` | Guests got no posts | `useNeedASubPostsData.js` |
| 2 | F20-1, Section 3.3 | My Posts is unavailable to a signed-out visitor | R8 | `F20-1: My Posts is unavailable to a signed-out visitor` | Signed-out visitors were shown the My Posts and Create Post controls | `NeedASubPage.jsx` |
| 3 | F20-1, Section 3.3 | Creation controls are unavailable to a signed-out visitor | R8 | `F20-1: creation controls are unavailable to a signed-out visitor` | Signed-out visitors were shown the My Posts and Create Post controls | `NeedASubPage.jsx` |
| 4 | F20-1, Section 3.3 | A sign-in without a finished account browses as a guest | R8 | `F20-1: a sign-in without a finished account browses as a guest` | A sign-in without a finished account was treated as signed in | `NeedASubPage.jsx` |
| 5 | F20-2 | A signed-in visitor gets All Posts for today with the date strip | R1, R2 | `F20-2: a signed-in visitor gets All Posts for today with the date strip` | The page opened on My Posts | `NeedASubPage.jsx` |
| 6 | F20-2 | A signed-in visitor gets the Create Post action | R7 | `F20-2: a signed-in visitor gets the Create Post action` | The Create Post action was missing | `NeedASubPage.jsx` |
| 7 | F20-2, Section 3.3 | An unverified email does not block public browsing | R9 | `F20-2: an unverified email does not block public browsing` | An unverified account was treated as a guest | `NeedASubPage.jsx` |
| 8 | F20-3 | Fourteen dates are offered in two sets of seven | R2 | `F20-3: fourteen dates are offered in two sets of seven` | The strip offered six dates per set | `NeedASubPage.jsx` |
| 9 | F20-3 | Changing the set selects its first date | R2 | `F20-3: changing the set selects its first date` | Changing the set kept the old selected date | `NeedASubPage.jsx` |
| 10 | F20-3, Section 4.3 | Selecting a date loads that day's posts from a fresh first batch | R2, R18 | `F20-3: selecting a date loads that day's posts from a fresh first batch` | Selecting a date did nothing | `NeedASubPage.jsx` |
| 11 | F20-4 | My Posts shows only the signed-in owner's posts for that date | R13 | `F20-4: My Posts shows only the signed-in owner's posts for that date` | My Posts asked for All Posts | `useNeedASubPostsData.js` |
| 12 | F20-4, Section 4.3 | Switching tab starts from its first batch | R18 | `F20-4: switching tab starts from its first batch` | A new tab's first request reused the previous tab's Load More position | `useNeedASubPostsData.js` |
| 13 | F20-5 | Posts are grouped by start hour | R3 | `F20-5: posts are grouped by start hour` | All posts were put under one hour | `NeedASubPostList.jsx` |
| 14 | F20-5 | Posts are shown in start-time order | R3 | `F20-5: posts are shown in start-time order` | Posts were shown latest first | `NeedASubPostList.jsx` |
| 15 | F20-6, Section 3.1 | A card shows venue, city/state, time, player group, format, and indoor/outdoor setting | R4 | `F20-6: a %s card shows venue, city/state, time, player group, format, and setting` (coed outdoor, men's indoor, women's outdoor) | The card left out the indoor/outdoor setting; separately, every card showed Coed | `NeedASubPostList.jsx` |
| 16 | F20-6 | Each card retains its configured need labels, including a full need | R4, R15 | `F20-6: each card retains its configured need labels, including a full need` | The card left out a full need; separately, goalkeeper needs; separately, men's and women's needs | `NeedASubPostList.jsx` |
| 17 | F20-6, Section 4.2 | Open and filled counts reflect confirmations rather than pending requests | R4, R15 | `F20-6: open and filled counts reflect confirmations rather than pending requests` | Pending requests reduced the open counts | `NeedASubPostList.jsx` |
| 18 | F20-7, Section 4.4 | A signed-in visitor's card opens its Need a Sub post detail | R5, R22 | `F20-7: a signed-in visitor's card opens its Need a Sub post detail` | A card opened game discovery instead of its post | `NeedASubPage.jsx` |
| 19 | F20-7 | Create Post opens the create panel on the same route | R7 | `F20-7: Create Post opens the create panel on the same route` | Create Post did not open the create panel | `NeedASubPage.jsx` |
| 20 | F20-8 | Load More appends later posts in order | R6, R17 | `F20-8: Load More appends later posts in order` | Load More put the new posts first | `useNeedASubPostsData.js` |
| 21 | F20-8 | Load More disappears when no further batch remains | R6 | `F20-8: Load More disappears when no further batch remains` | Load More stayed after the last batch | `useNeedASubPostsData.js` |
| 22 | F20-9 | A date with no eligible posts shows the empty message instead of cards or Load More | R20 | `F20-9: a date with no eligible posts shows the empty message instead of cards or Load More` | An empty date showed no empty message | `NeedASubPostList.jsx` |
| 23 | F20-9 | My Posts with no posts on that date shows its own empty message | R20 | `F20-9: My Posts with no posts on that date shows its own empty message` | My Posts showed the All Posts empty message | `NeedASubPostList.jsx` |
| 24 | F20-10 | A failed first request shows an error alert | R20 | `F20-10: a failed first request shows an error alert` | A failed first request showed no error alert | `useNeedASubPostsData.js` |
| 25 | F20-10 | No stale cards from the previous date remain after a failed request | R18, R20 | `F20-10: no stale cards from the previous date remain after a failed request` | A failed request kept the previous date's cards | `useNeedASubPostsData.js` |
| 26 | F20-11 | A failed Load More keeps the existing cards | R21 | `F20-11: a failed Load More keeps the existing cards` | A failed Load More cleared the cards | `useNeedASubPostsData.js` |
| 27 | F20-11 | A later successful Load More appends the next batch | R21 | `F20-11: a later successful Load More appends the next batch` | A successful Load More replaced the cards | `useNeedASubPostsData.js` |
| 28 | F20-12 | A late response for the previous date cannot replace the current results | R18 | `F20-12: a late response for the previous date cannot replace the current results` | Late answers were used whatever date or tab they were for | `useNeedASubPostsData.js` |
| 29 | F20-12 | A late response for the previous tab cannot replace the current results | R18 | `F20-12: a late response for the previous tab cannot replace the current results` | Late answers were used whatever date or tab they were for | `useNeedASubPostsData.js` |
| 30 | F20-12 | A late Load More response cannot append to another date's results | R18 | `F20-12: a late Load More response cannot append to another date's results` | Late Load More answers were used whatever date they were for | `useNeedASubPostsData.js` |
| 31 | F20-13, Section 4.3 | Regaining window focus refreshes the first batch with current posts and counts | R19 | `F20-13: regaining window focus refreshes the first batch with current posts and counts` | Regaining focus did not refresh | `useNeedASubPostsData.js` |
| 32 | F20-13, Section 4.3 | Becoming visible again refreshes the first batch with current posts and counts | R19 | `F20-13: becoming visible again refreshes the first batch with current posts and counts` | Becoming visible did not refresh | `useNeedASubPostsData.js` |
| 33 | F20-14 | A guest selecting a card is prompted for an account without seeing the post | R5, R11 | `F20-14: a guest selecting a card is sent to Sign In without seeing the post` | A guest's card opened the post | `NeedASubPage.jsx` |
| 34 | F20-14, Section 4.1 | After signing in, the guest returns to the selected post | R12 | `F20-14: after signing in, the guest returns to the selected post` | Sign-in dropped the saved destination | `authHelpers.js` |
| 35 | F20-14, Section 4.1 | After creating an account, the guest returns to the selected post | R5, R12 | `F20-14: after creating an account, the guest returns to the selected post` | Finish Profile dropped the saved destination | `useFinishProfileForm.js` |
| 36 | F20-15 | A post that became unavailable during sign-in is not exposed; the visitor reaches game discovery | R12 | `F20-15: a post that became unavailable during sign-in sends the visitor to game discovery` | Arriving from sign-in at an unavailable post showed its message instead of game discovery | `NeedASubDetailPage.jsx` |
| 37 | F20-15 | A post that became unavailable during account creation is not exposed; the visitor reaches game discovery | R12 | `F20-15: a post that became unavailable during account creation sends the visitor to game discovery` | Arriving from sign-in at an unavailable post showed its message instead of game discovery | `NeedASubDetailPage.jsx` |
| 38 | F20-15, Section 4.1 | Only an arrival from sign-in uses the fallback: an unavailable post opened directly shows its unavailable message | R12 | `F20-15: opening an unavailable post directly still shows its unavailable message` | Every unavailable post sent the visitor to game discovery | `NeedASubDetailPage.jsx` |
| 39 | F20-15, Section 4.1 | A post that becomes unavailable later in the same visit shows its unavailable message, not the fallback | R12 | `F20-15: a post that becomes unavailable later in the same visit shows its unavailable message` | The sign-in arrival mark stayed after the post showed | `NeedASubDetailPage.jsx` |
| 40 | F20-10, Section 4.3 | A loading skeleton shows while the first batch loads | R20 | `F20-10: a loading skeleton shows while the first batch loads` | No loading skeleton was shown | `NeedASubPostList.jsx` |
| 41 | F20-16, Section 3.1 | The date strip follows the market time zone; the device's time zone does not change it | R2, R23 | `F20-16: the date strip follows the market time zone on any device` | The date strip used the device's time zone | `NeedASubPage.jsx` |
| 42 | F20-16, Section 3.1 | Card times and hour groups follow the market time zone; the device's time zone does not change them | R3, R23 | `F20-16: card times and hour groups follow the market time zone on any device` | Card times used the device's time zone | `needASubData.js` |
| 43 | F20-17, Section 4.3 | After midnight in the market time zone, the date strip starts at the new today | R24 | `F20-17: after midnight in the market time zone, the date strip starts at the new today` | Returning after midnight kept the old dates | `NeedASubPage.jsx` |
| 44 | F20-17, Section 4.3 | A selected date that has passed moves to today | R24 | `F20-17: a selected date that has passed moves to today` | A passed selected date stayed selected | `NeedASubPage.jsx` |
| 45 | F20-14, Section 4.1 | After signing in with Google, the guest returns to the selected post | R12 | `F20-14: after signing in with Google, the guest returns to the selected post` | Google sign-in dropped the saved destination | `useSignInForm.js` |
| 46 | F20-14, Section 4.1 | A guest signing in with an unfinished profile completes Finish Profile first, then returns to the selected post (Sign In, Section 4.1; Finish Profile, scenario 10) | R12 | `F20-14: a guest signing in with an unfinished profile finishes it first, then returns to the selected post` | Failed before the change | — |
| 47 | F20-14, Section 4.1 | A guest creating an account with Google completes Finish Profile, then returns to the selected post (Create Account, scenario 3) | R12 | `F20-14: a guest creating an account with Google finishes the profile, then returns to the selected post` | Creating an account with Google dropped the saved destination | `useCreateAccountForm.js` |
| 48 | F20-7 | Selecting a card with the keyboard (Enter or Space) opens its post | R5 | `F20-7: pressing %s on a card opens its Need a Sub post detail` (Enter, Space) | Enter and Space on a card did nothing | `NeedASubPostList.jsx` |
| 49 | F20-17, Section 4.3 | After midnight, a selected date that has not passed stays selected, on its set of dates | R24 | `F20-17: a selected date that has not passed stays selected, on its set of dates` | Every selected date moved to today | `NeedASubPage.jsx` |

## 3. Work to do

None. All work is done.
