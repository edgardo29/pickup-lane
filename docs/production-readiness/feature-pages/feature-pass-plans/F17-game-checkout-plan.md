# F17 — Game Checkout Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F17-game-checkout-spec.md`  
**Endpoints:** `GET /games/{game_id}`, `GET /venues/{venue_id}`, `GET /game-images`, `GET /venue-images`, `GET /games/{game_id}/participants`, `GET /user-payment-methods`, `POST /user-payment-methods/setup-intent`, `POST /user-payment-methods/sync`, `POST /games/{game_id}/join`, `POST /games/{game_id}/booking-guests/add`, `POST /checkout/games/{game_id}/payment-intent`, `GET /checkout/bookings/{booking_id}/status`

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | Game summary, player, guest count and limit, booking price | Yes | — |
| R2 | 3.1 | Available and applied credit, covered small balance, and amount due | Yes | — |
| R3 | 3.1 | Cancellation information with Terms and Cancellation Policy links | Yes | — |
| R4 | 3.1 | Adjust guests within the limit; add-guest mode shows the proposed and resulting guest count | Yes | — |
| R5 | 3.1 | Terms must be accepted before confirming; Back returns to Game Details | Yes | — |
| R6 | 3.2 | Community games confirm or waitlist the whole party without an in-app charge; paid community games say payment happens outside Pickup Lane | Yes | — |
| R7 | 3.2 | Paid official games apply credit first; fully covered or below-minimum balances need no card | Yes | — |
| R8 | 3.2 | A remaining balance at or above the minimum uses Stripe with a saved card or card setup | Yes | — |
| R9 | 3.2 | Whole-party waitlist; paid official waitlist needs a saved card and explicit future-charge consent, with no immediate charge | Yes | — |
| R10 | 3.2 | Success returns to Game Details; authentication or a pending result is shown | Yes | — |
| R11 | 4.1 | Signed-in account with a complete profile; verified email for booking changes | Yes | — |
| R12 | 4.1 | Suspension blocks new booking, waitlisting, and added guests | Yes | — |
| R13 | 4.1 | Five-minute cutoff; whole party fits, waitlists, or is blocked; no second booking; add-guest needs a confirmed booking and capacity | Yes | — |
| R14 | 4.2 | Only official in-app checkout charges a card; credit reserved during checkout, deducted on completion, released on failure or expiry | Yes | — |
| R15 | 4.2 | Balance below Stripe's minimum covered by Pickup Lane; records keep applied credit and covered balance separate | Yes | — |
| R16 | 4.2 | Repeated or overlapping attempts cannot spend the same credit twice | Yes | — |
| R17 | 4.2 | Two-minute hold; authentication, failure, expiry, conflict, and unresolved results shown without claiming success; refund-required outcome | Yes | — |
| R18 | 4.3 | Paid waitlist charges only when a spot opens for the whole party; failure does not register the player; leaving before an offer is free | Yes | — |
| R19 | 4.3 | Added guests in a paid official game follow the credit, minimum-balance, and payment rules before confirmation | Yes | — |
| R20 | 4.3 | A failed required charge adds no guests; community guests create no in-app payment | Yes | — |
| R21 | 4.4 | Official checkout shows Pickup Lane's policy, including the change-related removal request | Yes | — |
| R22 | 4.4 | Community checkout shows the organizer's terms, or promises no refund and says to confirm arrangements with the organizer | Yes | — |
| R23 | 4.4 | Community checkout states that payment disputes and refunds remain between the player and the organizer | Yes | — |

## 2. Test scenarios

### 2.1 Backend tests

| # | Scenario | Requirements | Test exists? | Result |
|---|---|---|---|---|
| 2 | Free or host-paid community game confirms without an in-app charge | R6, R14 | Yes | Pass |
| 3 | Paid official balance at or above the minimum after credit is charged through Stripe | R7, R8, R14 | Yes | Pass |
| 4 | Selected saved card is used; another user's or unusable card is rejected | R8 | Yes | Pass |
| 5 | Whole party waitlisted with no immediate charge | R9 | Yes | Pass |
| 6 | Add-guest checkout for a confirmed booking | R13, R19 | Yes | Pass |
| 7 | Incomplete profile or unverified email rejected | R11 | Yes | Pass |
| 8 | Party over the guest limit or capacity | R4, R13 | Yes | Pass |
| 9 | Second booking or add-guest without a confirmed booking blocked | R13 | Yes | Pass |
| 10 | Cutoff or status or capacity change before confirmation | R13, R17 | Yes | Pass |
| 11 | Paid official waitlist without a saved card or consent | R9 | Yes | Pass |
| 12 | Card authentication required or card unusable | R17 | Yes | Pass |
| 13 | Hold expiry or payment and capacity conflict | R17 | Yes | Pass |
| 14 | Duplicate submission does not create another booking | R13 | Yes | Pass |
| 15 | Suspended player blocked from booking, waitlist, and guests | R12 | Yes | Pass |
| 16 | Paid waitlist spot opens; automatic payment succeeds or fails | R18 | Yes | Pass |
| 17 | Leaving a paid official waitlist before an offer | R18 | Yes | Pass |
| 18 | Paid official add-guest charge fails | R19, R20 | Yes | Pass |
| 19 | Official booking fully covered by credit without a card | R7, R14 | Yes | Pass |
| 20 | Partial credit, then failed payment or expired hold | R14, R17 | Yes | Pass |
| 21 | Overlapping checkouts using the same credit | R16 | Yes | Pass |
| 24 | Credit leaves a positive balance below the minimum | R7, R15 | Yes | Pass |
| 25 | Credit leaves a balance exactly at the minimum | R8, R15 | Yes | Pass |
| 26 | No credit and a positive total below the minimum | R7, R15 | Yes | Pass |

### 2.2 Frontend tests

| # | Scenario | Requirements | Test exists? | Result |
|---|---|---|---|---|
| 1 | Checkout shows game, player, party, price, policy, and terms; confirm waits for agreement | R1, R3, R5 | Yes | Pass |
| 2 | Community confirmation returns to Game Details | R6, R10 | Yes | Pass |
| 3 | Official summary shows price, credit, and amount due; returns only after confirmation | R2, R10 | Yes | Pass |
| 4 | Add a card or choose another saved card | R8 | Yes | Pass |
| 5 | Waitlist checkout shows no immediate charge; paid official asks for a card and consent | R9 | Yes | Pass |
| 6 | Add-guest checkout shows the booking and projected guest count | R4 | Yes | Pass |
| 7 | Signed out, incomplete profile, or unverified email | R11 | Yes | Pass |
| 8 | Guest count stays within the limit; party that cannot fit | R4, R13 | Yes | Pass |
| 9 | Existing booking or ineligible add-guest blocked | R13 | Yes | Pass |
| 10 | Cutoff or stale request reports failure | R13, R17 | Yes | Pass |
| 11 | Paid official waitlist blocked without card or consent | R9 | Yes | Pass |
| 12 | Card authentication or card failure feedback | R10, R17 | Yes | Pass |
| 13 | Hold expiry or conflict shown without claiming a spot | R17 | Yes | Pass |
| 14 | Load failure route back; duplicate submission | R5, R13 | Yes | Pass |
| 15 | Suspended player cannot confirm | R12 | Yes | Pass |
| 18 | Failed add-guest charge shown without claiming confirmation | R20 | Yes | Pass |
| 19 | Credit-covered booking shows zero due and confirms without a card | R2, R7 | Yes | Pass |
| 22 | Official and community-with-terms cancellation information | R3, R21, R22 | Yes | Pass |
| 23 | Community without organizer terms promises no refund | R22 | Yes | Pass |
| 24 | Small remaining balance covered; zero due without a card | R2, R7, R15 | Yes | Pass |
| 26 | Low-priced game with no credit confirms without a card | R7 | Yes | Pass |
| 27 | Community payment responsibility before confirming | R6, R23 | Yes | Pass |

## 3. Work to do

Items 1–5 were found in the 2026-11-18 review and are done.

1. Apply available game credit when a paid official waitlist offer is promoted. Record the credit and any covered small balance, charge only the remaining amount, and confirm without a Stripe charge when none is due. Re-check waitlist failure and notification behavior.
2. Release pending guest spots and their reserved credit when Stripe confirms the guest charge failed; retain holds only for unresolved payments. Re-check guest retry and late-payment compensation.
3. Recognize a completed paid guest addition on an eligible partially cancelled booking in checkout, and return to Game Details.
4. Report a saved-card list load failure as a checkout load error instead of an empty list.
5. Add focused F17 regression coverage for these paths and a genuinely overlapping credit-checkout test. Re-run affected backend and frontend verification, then review the corrected pass.
