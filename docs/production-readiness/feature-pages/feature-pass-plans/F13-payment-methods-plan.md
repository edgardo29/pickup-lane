# F13 — Payment Methods Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F13-payment-methods-spec.md`  
**Endpoints:** `GET /user-payment-methods`, `POST /user-payment-methods/setup-intent`, `POST /user-payment-methods/sync`, `PATCH /user-payment-methods/{payment_method_id}/default`, `DELETE /user-payment-methods/{payment_method_id}`

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | Saved cards show brand, last four digits, expiry, and a Default badge | Yes | — |
| R2 | 3.1 | An empty state invites adding a card when card setup is available | Yes | — |
| R3 | 3.1 | Add card opens secure setup; success refreshes the list; the first card becomes default; up to five active cards | Yes | — |
| R4 | 3.2 | A nondefault card can be made default; any card can be removed through a confirmation modal; both can require recent account confirmation | Yes | — |
| R5 | 3.2 | Back returns to Profile, or to checkout from a valid in-app checkout return path | Yes | — |
| R6 | 4.1 | Cards belong to the signed-in account; card entry uses the payment provider | Yes | — |
| R7 | 4.1 | Only active, unexpired cards can be used for checkout, automatic charges, or a publish fee; detached cards are not offered | Yes | — |
| R8 | 4.1 | The backend checks ownership and provider state before accepting changes | Yes | — |
| R9 | 4.2 | At most one active default card; the list updates after a confirmed change | Yes | — |
| R10 | 4.2 | When payments or secure setup are unavailable, the page explains it and does not start setup | Yes | — |
| R11 | 4.2 | Provider or sync failures report an error instead of claiming success | Yes | — |
| R12 | 4.3 | A suspended player can view and remove their saved cards; adding a card and changing the default stay blocked | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F13-9` is scenario 9); "Section 4.1" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F13-1 | Shows the same account's cards, and no other player's | R1, R6 | `test_a_player_sees_only_their_own_cards` | The card list returned every player's cards, not only the signed-in player's | `payment_method_service.py` |
| 2 | F13-1 | Shows each card's brand, last four digits, expiry, and default marker | R1 | `test_each_listed_card_includes_its_brand_last_four_expiry_and_default_flag` | A saved card stored the wrong expiry month | `payment_method_service.py` |
| 3 | F13-2 | The first card becomes default, even when setup did not ask for it | R3, R9 | `test_the_first_saved_card_becomes_the_default` | The first card became default only when the page asked for it | `payment_method_service.py` |
| 4 | F13-2 | Adding another card does not silently replace the default | R3, R9 | `test_saving_another_card_does_not_replace_the_default` | Every saved card became the default | `payment_method_service.py` |
| 5 | F13-3 | Exactly that card is marked default | R4, R9 | `test_making_another_card_default_leaves_exactly_that_card_default` | Make default never marked the chosen card as default | `payment_method_service.py` |
| 6 | F13-4 | The removed card disappears from active cards | R4 | `test_a_removed_card_is_detached_and_no_longer_listed` | The card list included removed cards | `payment_method_service.py` |
| 7 | F13-4 | Removing the default promotes the oldest remaining active card | R9 | `test_removing_the_default_card_promotes_the_oldest_remaining_card` | Removing the default promoted the newest remaining card instead of the oldest | `payment_method_service.py` |
| 8 | F13-4, Section 3.2 | Any saved card can be removed, including an expired one | R4 | `test_an_expired_card_can_be_removed` | Failed before the change | — |
| 9 | F13-4 | The removed card is no longer usable for checkout | R7 | `test_a_removed_card_cannot_be_used_for_checkout` | A removed card could pay at checkout or for a publish fee | `payment_method_service.py` |
| 10 | F13-4 | The removed card is no longer usable for a publish fee | R7 | `test_a_removed_card_cannot_pay_a_publish_fee` | A removed card could pay at checkout or for a publish fee | `payment_method_service.py` |
| 11 | F13-6 | A sixth active card cannot be saved | R3 | `test_a_sixth_active_card_cannot_be_saved` | A sixth card could be saved | `payment_method_service.py` |
| 12 | F13-6 | Card setup cannot start at five active cards | R3 | `test_card_setup_cannot_start_at_five_active_cards` | Card setup started at five cards | `payment_method_service.py` |
| 13 | F13-8 | Failed card setup start: an error appears and no card is saved | R11 | `test_a_failed_card_setup_start_reports_an_error_and_saves_nothing` | A failed card setup start was reported as success | `payment_method_service.py` |
| 14 | F13-8 | Failed card setup start: can be retried | R11 | `test_a_failed_card_setup_start_can_be_retried` | A failed card setup start was left unresolved, so it could not be retried | `payment_method_service.py` |
| 15 | F13-8 | Failed card save: an error appears and no card is saved | R11 | `test_a_failed_card_save_reports_an_error_and_saves_nothing` | A failed card save was reported as a success | `payment_method_service.py` |
| 16 | F13-8 | Failed card save: can be retried | R11 | `test_a_failed_card_save_can_be_retried` | A failed card save was left unresolved, so it could not be retried | `payment_method_service.py` |
| 17 | F13-8 | Failed default change: an error appears and the default does not change | R11 | `test_a_failed_default_change_reports_an_error_and_changes_nothing` | A failed default change at Stripe still changed the default | `payment_method_service.py` |
| 18 | F13-8 | Failed default change: can be retried | R11 | `test_a_failed_default_change_can_be_retried` | A failed default change was left unresolved, so it could not be retried | `payment_method_service.py` |
| 19 | F13-8 | Failed removal: an error appears and the card is not removed | R11 | `test_a_failed_removal_reports_an_error_and_changes_nothing` | A failed removal at Stripe still removed the card | `payment_method_service.py` |
| 20 | F13-8 | Failed removal: can be retried | R11 | `test_a_failed_removal_can_be_retried` | A failed removal was left unresolved, so it could not be retried | `payment_method_service.py` |
| 21 | F13-9 | Making another player's card default is rejected | R6, R8 | `test_another_players_card_cannot_be_made_default` | Another player's card could be changed or removed | `payment_method_service.py` |
| 22 | F13-9 | Removing another player's card is rejected | R6, R8 | `test_another_players_card_cannot_be_removed` | Another player's card could be changed or removed | `payment_method_service.py` |
| 23 | F13-9 | Making a removed card default is rejected | R4, R8 | `test_a_removed_card_cannot_be_made_default` | Make default reactivated a removed card instead of refusing it | `payment_method_service.py` |
| 24 | F13-9 | Making an expired card default is rejected | R4, R7, R8 | `test_an_expired_card_cannot_be_made_default` | A card whose expiry date had passed was still accepted after Stripe verification | `payment_method_service.py` |
| 25 | F13-9 | Making a card default without recent account confirmation is rejected | R4 | `test_making_a_card_default_without_recent_confirmation_is_refused` | Make default no longer needed a recent account confirmation | `user_payment_method_routes.py` |
| 26 | F13-9 | Removing a card without recent account confirmation is rejected | R4 | `test_removing_a_card_without_recent_confirmation_is_refused` | Removing a card no longer needed a recent account confirmation | `user_payment_method_routes.py` |
| 27 | F13-9, Section 4.1 | A removed card is not usable for a paid waitlist | R7 | `test_a_removed_card_cannot_be_chosen_for_a_paid_waitlist` | A removed card could be chosen for a paid waitlist | `game_waitlist_service.py` |
| 28 | F13-9, Section 4.1 | An expired card is not usable for a paid waitlist | R7 | `test_an_expired_card_cannot_be_chosen_for_a_paid_waitlist` | An expired card could be chosen for a paid waitlist | `game_waitlist_service.py` |
| 29 | F13-9, Section 4.1 | A card removed while on a paid waitlist is not used for automatic charging | R7 | `test_a_card_removed_while_on_a_paid_waitlist_is_not_charged_when_a_spot_opens` | A card removed while on a paid waitlist was still charged when a spot opened | `game_waitlist_service.py` |
| 30 | F13-9, Section 4.1 | A card that expires while on a paid waitlist is not used for automatic charging | R7 | `test_a_card_that_expires_while_on_a_paid_waitlist_is_not_charged_when_a_spot_opens` | A card whose expiry date had passed was still accepted after Stripe verification | `payment_method_service.py` |
| 31 | F13-9, Section 4.1 | An expired card is not usable for checkout | R7 | `test_an_expired_card_cannot_pay_at_checkout` | An expired card could pay at checkout or for a publish fee | `payment_method_service.py` |
| 32 | F13-9, Section 4.1 | An expired card is not usable for a publish fee | R7 | `test_an_expired_card_cannot_pay_a_publish_fee` | An expired card could pay at checkout or for a publish fee | `payment_method_service.py` |
| 33 | F13-9, Section 4.1 | A change is rejected when Stripe no longer links the card to the account | R8 | `test_a_card_change_is_refused_when_stripe_no_longer_links_the_card` | A card Stripe no longer linked to the player was still accepted | `payment_method_service.py` |
| 34 | F13-10 | Card payments off: card setup cannot proceed | R10 | `test_card_setup_is_refused_while_card_payments_are_off` | Card setup started while card payments were off | `payment_method_service.py` |
| 35 | F13-11 | Private access requires sign-in, for every card request | R6 | `test_signed_out_card_requests_are_refused` | A signed-out request got "User not found" instead of being asked to sign in | `auth_service.py` |
| 36 | F13-11 | A deleted or deleting account is refused, for every card request | R6 | `test_a_deleted_or_deleting_account_cannot_use_saved_cards` | Deleted and deleting accounts were treated as active accounts | `auth_service.py` |
| 37 | F13-11 | An authorized empty account gets an empty card list | R2 | `test_an_account_with_no_cards_gets_an_empty_list` | An account with no cards got an error instead of an empty list | `payment_method_service.py` |
| 38 | F13-13 | The duplicate is rejected without creating a second active card or changing the default | R8 | `test_saving_an_already_active_card_again_is_rejected` | An already saved card could be saved again | `payment_method_service.py` |
| 39 | F13-14 | A re-added card returns once to the active list | R3 | `test_a_re_added_removed_card_returns_as_the_same_card` | A removed card was refused as already saved when re-added | `payment_method_service.py` |
| 40 | F13-14 | A re-added card counts toward the five-card limit | R3 | `test_a_re_added_removed_card_counts_toward_the_five_card_limit` | A re-added card stayed removed, so it did not count toward the limit | `payment_method_service.py` |
| 41 | F13-14 | A re-added card becomes default when it is the only active card | R3, R9 | `test_a_re_added_card_becomes_default_when_it_is_the_only_active_card` | No saved card became the default, including the first | `payment_method_service.py` |
| 42 | F13-14 | An existing default remains unchanged when a card is re-added | R3, R9 | `test_a_re_added_card_leaves_an_existing_default_unchanged` | Every saved card became the default | `payment_method_service.py` |
| 43 | F13-15 | Suspended: saved cards appear | R12 | `test_a_suspended_player_still_sees_their_saved_cards` | A suspended player could no longer see their cards | `user_payment_method_routes.py` |
| 44 | F13-15 | Suspended: a card can be removed | R12 | `test_a_suspended_player_can_remove_a_card` | A suspended player could no longer remove a card | `user_payment_method_routes.py` |
| 45 | F13-15 | Suspended: removal still requires recent account confirmation | R4, R12 | `test_a_suspended_players_removal_still_needs_a_recent_confirmation` | Removing a card no longer needed a recent account confirmation | `user_payment_method_routes.py` |
| 46 | F13-15 | Suspended: card setup cannot start | R12 | `test_a_suspended_player_cannot_start_adding_a_card` | A suspended player could start card setup | `user_payment_method_routes.py` |
| 47 | F13-15 | Suspended: a card cannot be saved | R12 | `test_a_suspended_player_cannot_save_a_card_set_up_before_suspension` | A suspended player could save a card | `user_payment_method_routes.py` |
| 48 | F13-15 | Suspended: the default card cannot be changed | R12 | `test_a_suspended_player_cannot_change_the_default` | A suspended player could change the default card | `user_payment_method_routes.py` |

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F13-1 | `/profile/payment-methods` shows the account's cards, brand, last four digits, expiry, and one default marker | R1, R9 | `F13-1: /profile/payment-methods shows the cards with one Default badge` | Every card showed the Default badge | `PaymentMethodsPage.jsx` |
| 2 | F13-1 | `/settings/payment-methods` shows the same cards and details | R1 | `F13-1: /settings/payment-methods shows the cards with one Default badge` | Every card showed the Default badge | `PaymentMethodsPage.jsx` |
| 3 | F13-2 | Successful setup refreshes the list | R3 | `F13-2: after a card is saved, the list refreshes and shows it` | The list was not refreshed after a card was saved | `PaymentMethodsPage.jsx` |
| 4 | F13-2 | The first card becomes default | R3 | `F13-2: the first card is saved as default` | The first card was not saved as default | `PaymentMethodsPage.jsx` |
| 5 | F13-2 | Adding another card does not silently replace the default | R3 | `F13-2: adding another card does not ask for it to replace the default` | Every added card asked to become the default | `PaymentMethodsPage.jsx` |
| 6 | F13-3 | Make default requires account confirmation | R4 | `F13-3: Make default asks for account confirmation` | Make default skipped account confirmation | `PaymentMethodsPage.jsx` |
| 7 | F13-3 | Exactly that card is marked default | R4, R9 | `F13-3: after Make default, exactly that card shows the Default badge` | Every card showed the Default badge | `PaymentMethodsPage.jsx` |
| 8 | F13-4 | Removal requires account confirmation | R4 | `F13-4: Remove asks for account confirmation` | Removing a card skipped account confirmation | `PaymentMethodsPage.jsx` |
| 9 | F13-4 | The removed card disappears from the list | R4 | `F13-4: after removal, the card is no longer listed` | The list was not refreshed after a card was removed | `PaymentMethodsPage.jsx` |
| 10 | F13-5 | From checkout, Back goes to checkout | R5 | `F13-5: from checkout, Back returns to checkout` | Back always went to Profile, even from checkout | `PaymentMethodsPage.jsx` |
| 11 | F13-5 | From checkout, the post-save return action goes to checkout | R5 | `F13-5: from checkout, the link after saving a card returns to checkout` | No return-to-checkout link after saving a card | `PaymentMethodsPage.jsx` |
| 12 | F13-5 | Ordinary Profile entry goes back to Profile | R5 | `F13-5: opened from Profile, Back returns to Profile` | Back without a checkout return path did not go to Profile | `PaymentMethodsPage.jsx` |
| 13 | F13-6 | Add card is unavailable at five active cards | R3 | `F13-6: Add card is unavailable at five cards` | Add card stayed available at five cards | `PaymentMethodsPage.jsx` |
| 14 | F13-7 | Cancelling card setup adds no card and the list remains intact | R3 | `F13-7: cancelling card setup adds nothing and keeps the list` | Cancelling card setup cleared the saved card list | `PaymentMethodsPage.jsx` |
| 15 | F13-7 | Cancelling removal detaches no card and the list remains intact | R4 | `F13-7: backing out of removal keeps the card` | Backing out of removal removed the card | `PaymentMethodsPage.jsx` |
| 16 | F13-8 | Failed card setup start: an error appears and the page does not claim success | R11 | `F13-8: a failed card setup start shows the error without claiming success` | A failed card setup start showed no error | `PaymentMethodsPage.jsx` |
| 17 | F13-8 | Failed card setup start: can be retried | R11 | `F13-8: a failed card setup start can be tried again` | After a failed card setup start, Add card stayed stuck on Starting | `PaymentMethodsPage.jsx` |
| 18 | F13-8 | Failed card save: an error appears and the page does not claim the card was saved | R11 | `F13-8: a rejected card save shows the error without claiming the card was saved` | A rejected card save was reported as saved | `PaymentMethodsPage.jsx` |
| 19 | F13-8 | Failed card save: can be retried with another card | R11 | `F13-8: after a rejected card save, another card can be entered` | After a rejected card save, no fresh card setup was started | `PaymentMethodsPage.jsx` |
| 20 | F13-8 | Failed default change: an error appears and the old default stays | R11 | `F13-8: a failed default change shows the error and keeps the old default` | A failed default change was reported as success | `PaymentMethodsPage.jsx` |
| 21 | F13-8 | Failed default change: can be retried | R11 | `F13-8: a failed default change can be tried again` | After a failed default change, Make default did nothing | `PaymentMethodsPage.jsx` |
| 22 | F13-8 | Failed removal: an error appears and the card stays | R11 | `F13-8: a failed removal shows the error and keeps the card` | A failed removal was reported as success | `PaymentMethodsPage.jsx` |
| 23 | F13-8 | Failed removal: can be retried | R11 | `F13-8: a failed removal can be tried again` | After a failed removal, Remove card did nothing | `PaymentMethodsPage.jsx` |
| 24 | F13-10 | Card payments off: the unavailable state is explained | R10 | `F13-10: when card payments are off the page says so` | No message when card payments were off | `PaymentMethodsPage.jsx` |
| 25 | F13-10 | Card payments off: card setup cannot proceed | R10 | `F13-10: when card payments are off, card setup cannot start` | Add card stayed available when card setup was unavailable | `PaymentMethodsPage.jsx` |
| 26 | F13-10 | Secure setup unavailable: the unavailable state is explained | R10 | `F13-10: when card setup is unavailable the page explains it to the player` | No message when card setup was unavailable | `PaymentMethodsPage.jsx` |
| 27 | F13-10 | Secure setup unavailable: card setup cannot proceed | R10 | `F13-10: when card setup is unavailable, card setup cannot start` | Add card stayed available when card setup was unavailable | `PaymentMethodsPage.jsx` |
| 28 | F13-10, Section 3.1 | Secure setup unavailable: the empty state does not invite adding a card | R2 | `F13-10: when card setup is unavailable, the empty state does not invite adding a card` | The empty state invited adding a card when card setup was unavailable | `PaymentMethodsPage.jsx` |
| 29 | F13-11 | Private access requires sign-in | R6 | `F13-11: a signed-out visitor is sent to sign in` | A signed-out visitor was let onto the page | `RouteGuards.jsx` |
| 30 | F13-11 | An authorized empty account sees the empty-card state inviting a card | R2 | `F13-11: an account with no cards sees the empty state inviting a card` | The empty state did not invite adding a card | `PaymentMethodsPage.jsx` |
| 31 | F13-12 | An invalid or external return destination falls back to Profile | R5 | `F13-12: the return path %s falls back to Profile` | An external or relative return path was accepted; separately, a non-checkout in-app return path was accepted | `PaymentMethodsPage.jsx` |
| 32 | F13-15 | Suspended: saved cards appear | R12 | `F13-15: a suspended player sees their saved cards` | A suspended player's saved cards were hidden | `PaymentMethodsPage.jsx` |
| 33 | F13-15 | Suspended: the page explains why Add card and Make default are not offered | R12 | `F13-15: a suspended player sees why adding a card and changing the default are not offered` | A suspended player was treated as active | `PaymentMethodsPage.jsx` |
| 34 | F13-15 | Suspended: Add card is not offered | R12 | `F13-15: a suspended player is not offered Add card` | A suspended player was treated as active | `PaymentMethodsPage.jsx` |
| 35 | F13-15 | Suspended: Make default is not offered | R12 | `F13-15: a suspended player is not offered Make default` | A suspended player was treated as active | `PaymentMethodsPage.jsx` |
| 36 | F13-15 | Suspended: saved cards can be removed | R12 | `F13-15: a suspended player can remove a card` | The list was not refreshed after a card was removed | `PaymentMethodsPage.jsx` |
| 37 | F13-15 | Suspended: with no cards, the empty state does not invite adding a card | R2, R12 | `F13-15: a suspended player with no cards is not invited to add one` | A suspended player was treated as active | `PaymentMethodsPage.jsx` |

## 3. Work to do

None. All work is done.
