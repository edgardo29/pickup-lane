# F17 — Game Checkout Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player/game-checkout.md`  
**Endpoints:** `GET /games/{game_id}`, `GET /venues/{venue_id}`, `GET /game-images`, `GET /venue-images`, `GET /games/{game_id}/participants`, `GET /user-payment-methods`, `POST /user-payment-methods/setup-intent`, `POST /user-payment-methods/sync`, `POST /games/{game_id}/join`, `POST /games/{game_id}/booking-guests/add`, `POST /checkout/games/{game_id}/payment-intent`, `GET /checkout/bookings/{booking_id}/status`

## 1. Page requirements

| Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|
| 3.1 | Game summary, player, guest count and limit, booking price | Yes | — |
| 3.1 | Available and applied credit, covered small balance, and amount due | Yes | — |
| 3.1 | Cancellation information with Terms and Cancellation Policy links | Yes | — |
| 3.1 | Adjust guests within the limit; add-guest mode shows the proposed and resulting guest count | Yes | — |
| 3.1 | Terms must be accepted before confirming; Back returns to Game Details | Yes | — |
| 3.2 | Community games confirm or waitlist the whole party without an in-app charge; paid community games say payment happens outside Pickup Lane | Yes | — |
| 3.2 | Paid official games apply credit first; fully covered or below-minimum balances need no card | Yes | — |
| 3.2 | A remaining balance at or above the minimum uses Stripe with a saved card or card setup | Yes | — |
| 3.2 | Whole-party waitlist; paid official waitlist needs a saved card and explicit future-charge consent, with no immediate charge | Yes | — |
| 3.2 | Success returns to Game Details; authentication or a pending result is shown | Yes | — |
| 4.1 | Signed-in account with a complete profile; verified email for booking changes | Yes | — |
| 4.1 | Suspension blocks new booking, waitlisting, and added guests | Yes | — |
| 4.1 | Five-minute cutoff; whole party fits, waitlists, or is blocked; no second booking; add-guest needs a confirmed booking and capacity | Yes | — |
| 4.2 | Only official in-app checkout charges a card; credit reserved during checkout, deducted on completion, released on failure or expiry | Yes | — |
| 4.2 | Balance below Stripe's minimum covered by Pickup Lane; records keep applied credit and covered balance separate | Yes | — |
| 4.2 | Repeated or overlapping attempts cannot spend the same credit twice | Yes | — |
| 4.2 | Two-minute hold; authentication, failure, expiry, conflict, and unresolved results shown without claiming success; refund-required outcome | Yes | — |
| 4.3 | Paid waitlist charges only when a spot opens for the whole party; failure does not register the player; leaving before an offer is free | Yes | — |
| 4.3 | Added guests in a paid official game follow the credit, minimum-balance, and payment rules before confirmation | Yes | — |
| 4.3 | A failed required charge adds no guests; community guests create no in-app payment | Yes | — |
| 4.4 | Official checkout shows Pickup Lane's policy, including the change-related removal request | Yes | — |
| 4.4 | Community checkout shows the organizer's terms, or promises no refund and says to confirm arrangements with the organizer | Yes | — |
| 4.4 | Community checkout states that payment disputes and refunds remain between the player and the organizer | Yes | — |

## 2. Test scenarios

### 2.1 Backend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| 2 | Free or host-paid community game confirms without an in-app charge | Yes | Pass |
| 3 | Paid official balance at or above the minimum after credit is charged through Stripe | Yes | Pass |
| 4 | Selected saved card is used; another user's or unusable card is rejected | Yes | Pass |
| 5 | Whole party waitlisted with no immediate charge | Yes | Pass |
| 6 | Add-guest checkout for a confirmed booking | Yes | Pass |
| 7 | Incomplete profile or unverified email rejected | Yes | Pass |
| 8 | Party over the guest limit or capacity | Yes | Pass |
| 9 | Second booking or add-guest without a confirmed booking blocked | Yes | Pass |
| 10 | Cutoff or status or capacity change before confirmation | Yes | Pass |
| 11 | Paid official waitlist without a saved card or consent | Yes | Pass |
| 12 | Card authentication required or card unusable | Yes | Pass |
| 13 | Hold expiry or payment and capacity conflict | Yes | Pass |
| 14 | Duplicate submission does not create another booking | Yes | Pass |
| 15 | Suspended player blocked from booking, waitlist, and guests | Yes | Pass |
| 16 | Paid waitlist spot opens; automatic payment succeeds or fails | Yes | Pass |
| 17 | Leaving a paid official waitlist before an offer | Yes | Pass |
| 18 | Paid official add-guest charge fails | Yes | Pass |
| 19 | Official booking fully covered by credit without a card | Yes | Pass |
| 20 | Partial credit, then failed payment or expired hold | Yes | Pass |
| 21 | Overlapping checkouts using the same credit | Yes | Pass |
| 24 | Credit leaves a positive balance below the minimum | Yes | Pass |
| 25 | Credit leaves a balance exactly at the minimum | Yes | Pass |
| 26 | No credit and a positive total below the minimum | Yes | Pass |

### 2.2 Frontend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| 1 | Checkout shows game, player, party, price, policy, and terms; confirm waits for agreement | Yes | Pass |
| 2 | Community confirmation returns to Game Details | Yes | Pass |
| 3 | Official summary shows price, credit, and amount due; returns only after confirmation | Yes | Pass |
| 4 | Add a card or choose another saved card | Yes | Pass |
| 5 | Waitlist checkout shows no immediate charge; paid official asks for a card and consent | Yes | Pass |
| 6 | Add-guest checkout shows the booking and projected guest count | Yes | Pass |
| 7 | Signed out, incomplete profile, or unverified email | Yes | Pass |
| 8 | Guest count stays within the limit; party that cannot fit | Yes | Pass |
| 9 | Existing booking or ineligible add-guest blocked | Yes | Pass |
| 10 | Cutoff or stale request reports failure | Yes | Pass |
| 11 | Paid official waitlist blocked without card or consent | Yes | Pass |
| 12 | Card authentication or card failure feedback | Yes | Pass |
| 13 | Hold expiry or conflict shown without claiming a spot | Yes | Pass |
| 14 | Load failure route back; duplicate submission | Yes | Pass |
| 15 | Suspended player cannot confirm | Yes | Pass |
| 18 | Failed add-guest charge shown without claiming confirmation | Yes | Pass |
| 19 | Credit-covered booking shows zero due and confirms without a card | Yes | Pass |
| 22 | Official and community-with-terms cancellation information | Yes | Pass |
| 23 | Community without organizer terms promises no refund | Yes | Pass |
| 24 | Small remaining balance covered; zero due without a card | Yes | Pass |
| 26 | Low-priced game with no credit confirms without a card | Yes | Pass |
| 27 | Community payment responsibility before confirming | Yes | Pass |

## 3. Work to do

Items 1–5 were found in the 2026-11-18 review and are done.

1. Apply available game credit when a paid official waitlist offer is promoted. Record the credit and any covered small balance, charge only the remaining amount, and confirm without a Stripe charge when none is due. Re-check waitlist failure and notification behavior.
2. Release pending guest spots and their reserved credit when Stripe confirms the guest charge failed; retain holds only for unresolved payments. Re-check guest retry and late-payment compensation.
3. Recognize a completed paid guest addition on an eligible partially cancelled booking in checkout, and return to Game Details.
4. Report a saved-card list load failure as a checkout load error instead of an empty list.
5. Add focused F17 regression coverage for these paths and a genuinely overlapping credit-checkout test. Re-run affected backend and frontend verification, then review the corrected pass.
