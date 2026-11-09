# F17 — Game Checkout

## 1. Existing Route(s)

- `/games/:gameId/checkout`

`?mode=add-guests` uses this page for a confirmed player's additional guests.

## 2. Purpose

Game Checkout lets a signed-in player review a game, their party, payment implications, and terms before confirming a spot, joining a waitlist, or adding guests. [Game Details](../public/game-details.md) owns discovery and attendance entry; [Payment Methods](payment-methods.md) owns saved-card management.

## 3. Main Functionality

### 3.1. Review and Configure the Party

- Show the game summary, player, guest count and limit, booking price, available and applied game credit for official games, any small balance covered by Pickup Lane, the amount due, cancellation information, and links to Terms and the Cancellation Policy.
- A player can adjust guests within the game's guest limit. Add-guest mode shows the proposed additional guests and resulting guest count for an existing confirmed booking.
- The player must accept the terms before confirming. Back returns to Game Details.

### 3.2. Confirm or Waitlist

- Community games confirm or waitlist the whole party without an in-app player charge. Paid community games show that host payment is handled outside Pickup Lane.
- Paid official games automatically apply available game credit before payment, including paid additional guests. A fully credit-covered booking or one with only a positive balance below Stripe's minimum after available credit is applied needs no card charge; Pickup Lane covers that small balance. A remaining balance at or above the minimum uses normal Stripe payment, with a usable saved card or card setup.
- If the whole party cannot fit, an enabled waitlist offers a waitlist confirmation. A paid official-game waitlist requires a saved card and explicit consent for a possible later automatic charge; joining the waitlist does not charge immediately. A player may leave before a spot is offered without a charge.
- Successful confirmation returns to Game Details. Payment processing can require card authentication or remain pending while the outcome is checked.

## 4. Important Behavior & Decisions

### 4.1. Eligibility and Capacity

Checkout requires a signed-in account with a complete profile; protected booking changes also require verified email. Suspension blocks new registration, waitlisting, and added guests; existing commitments and withdrawal remain available through [Game Details](../public/game-details.md), under the [suspension rule](../admin/user-detail.md#410-suspended-player-experience). The join and attendance window closes five minutes after game start. The entire player-and-guest party either fits, joins an enabled waitlist, or is blocked; it is never split. A confirmed player cannot create a second booking through ordinary checkout, and add-guest mode requires an existing confirmed booking and available guest capacity.

### 4.2. Payment and Confirmation

Only official in-app checkout charges a player's saved card. Available game credit is applied automatically and may be reserved during checkout, but is deducted only when the booking completes; failed or expired attempts release it. If the positive balance remaining after available credit is applied falls below Stripe's minimum, Pickup Lane absorbs that balance without reducing the credit applied or creating an artificial card charge. The booking and credit records reflect the applied credit and covered balance separately. A remaining balance at or above the minimum follows normal Stripe payment. Concurrent or repeated attempts cannot spend the same credit twice. A temporary paid-checkout hold lasts two minutes; payment processing alone is not a confirmed spot. Card authentication, payment failure, hold expiry, capacity conflict, and an unresolved result must be shown without claiming success. A later successful payment that cannot confirm the spot requires refund handling. Saved-card setup rules belong to [Payment Methods](payment-methods.md); refund terms belong to [Cancellation & Refunds Policy](../public/cancellation-refunds-policy.md).

### 4.3. Waitlist and Guest Boundaries

Paid official-game waitlist consent authorizes a future charge only if a spot opens for the full party. The booking is confirmed only after payment succeeds when a charge is required. Failed automatic payment does not register the player, and the spot may be offered to the next eligible person. A player leaving before an offer is not charged. Additional guests in a paid official game follow the same automatic-credit, minimum-balance, and payment rules before confirmation. A failed required charge adds no guests and reserves no spots; community guests do not create an in-app player payment.

### 4.4. Cancellation Information

Official checkout shows Pickup Lane's applicable cancellation and refund policy, including the [change-related removal request](../public/cancellation-refunds-policy.md#42-current-policy-summary). Community checkout shows the organizer's terms when provided. Without organizer terms, it does not promise a refund and tells the player to confirm payment and refund arrangements with the organizer. In either case, before confirmation, community checkout states that payment disputes and refunds remain between the player and the original organizer, under the [community payment responsibility](../public/game-details.md#45-community-game-payment-responsibility). The policy page owns the general policy; this page owns the game-specific checkout presentation.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open checkout for a joinable game with a complete signed-in account. | Game, player, party, price, policy, and terms appear; confirming remains unavailable until the agreement is accepted. |
| 2 | ☐ | Confirm a free or host-paid community game. | The whole eligible party joins and returns to Game Details without an in-app player charge. |
| 3 | ☐ | Confirm a paid official game whose balance after automatic credit meets Stripe's minimum. | The summary shows booking price, available and applied credit, and the amount due; only that remaining balance is charged through Stripe, and the page returns to Game Details only after confirmation. |
| 4 | ☐ | Add a card or choose another saved card during official checkout. | The selected usable card is used for that checkout; card setup follows the shared saved-card flow. |
| 5 | ☐ | Join an eligible waitlist with a party too large for current capacity. | The entire party becomes waitlisted and no immediate player charge is made; paid official entry requires a saved card and explicit future-charge consent. |
| 6 | ☐ | Open add-guest checkout from a confirmed booking. | The existing booking and projected guest count appear; available credit applies first, and permitted paid official guests are added only after any required Stripe payment succeeds or the remaining balance is covered under the minimum-balance rule. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 7 | ☐ | Open checkout signed out, with an incomplete profile, or with an unverified email. | Sign-in or profile completion is required as applicable; protected booking submission is rejected until email verification. |
| 8 | ☐ | Increase guests past the guest limit or remaining capacity. | The proposed party stays within the guest limit; if it cannot fit, it is waitlisted as a whole when allowed or cannot confirm. |
| 9 | ☐ | Attempt ordinary checkout with an active booking, or add-guest mode without a confirmed booking. | A second booking or ineligible guest addition is blocked without changing attendance. |
| 10 | ☐ | Reach the five-minute cutoff or have game status/capacity change before confirmation. | The stale request cannot confirm an ineligible party; the page reports failure without a false success. |
| 11 | ☐ | Join a paid official waitlist without a usable saved card or explicit future-charge consent. | Joining is blocked; with both supplied, the player is waitlisted without an immediate charge. |
| 12 | ☐ | Require card authentication, use an expired card, or fail card setup. | Authentication or recoverable card feedback appears; no spot is called confirmed before the payment outcome succeeds. |
| 13 | ☐ | Let a paid checkout hold expire, or receive a payment/capacity conflict. | The page does not claim a confirmed spot and communicates the pending, expired, or refund-required outcome. |
| 14 | ☐ | Fail the initial checkout load or submit twice while confirmation is pending. | Load failure shows an unavailable state with a route back to Game Details; duplicate submission does not create another booking. |
| 15 | ☐ | Open ordinary checkout or add-guest mode while suspended. | No new booking, waitlist entry, or guest is confirmed; existing participation remains intact and can be managed through Game Details. |
| 16 | ☐ | A paid official waitlist spot opens and automatic payment succeeds or fails. | Success confirms the booking only after payment; failure does not register the player and the spot can move to the next eligible person. |
| 17 | ☐ | Leave a paid official waitlist before receiving a spot. | The entry ends without a player charge. |
| 18 | ☐ | Add guests to a paid official game with a remaining balance at or above Stripe's minimum, then fail its charge. | Credit applies under checkout rules, but no guest is added or spot reserved unless the required charge succeeds; the failure is shown without claiming confirmation. |
| 19 | ☐ | Book an official game fully covered by available credit without a saved card. | The summary shows a zero remaining balance; confirmation succeeds without a card or Stripe charge, and credit is deducted once only after the booking completes. |
| 20 | ☐ | Start an official checkout with partial credit, then fail payment or let its hold expire. | Only the remaining balance is submitted for payment; no booking or credit deduction is finalized, and reserved credit becomes available again. |
| 21 | ☐ | Start overlapping or repeated official checkouts using the same available credit. | Credit cannot be applied or deducted twice; each completed booking reflects only the credit actually available to it. |
| 22 | ☐ | Review cancellation information for an official game and a community game with organizer terms. | The official policy explains the change-related removal request; the community checkout shows that organizer's terms rather than the official refund promise. |
| 23 | ☐ | Review community checkout when the organizer supplied no cancellation terms. | The page promises no refund and directs the player to confirm payment and refund arrangements with the organizer. |
| 24 | ☐ | Apply credit that leaves a positive official-checkout balance below Stripe's minimum, without a saved card. | All available credit is applied normally, Pickup Lane covers the small remainder, the amount due becomes zero, and the booking can confirm without a card charge; records distinguish credit used from the covered remainder. |
| 25 | ☐ | Apply credit that leaves an official-checkout balance exactly at Stripe's minimum. | The full available credit is applied, the remaining balance uses the normal Stripe payment flow, and no small-balance coverage is recorded. |
| 26 | ☐ | Check out a valid low-priced official game with no available credit and a positive total below Stripe's minimum. | Pickup Lane covers the small balance, the booking can confirm without a card charge, and no game credit is falsely recorded as applied. |
| 27 | ☐ | Review community checkout before confirming, with and without organizer terms. | Before confirmation, the page states that payment happens with the organizer outside Pickup Lane and that disputes and refunds remain between the player and the original organizer; Pickup Lane does not process or guarantee them. |

## 6. Open Items to Resolve

**None**.
