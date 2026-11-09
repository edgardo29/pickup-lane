# F13 — Payment Methods

## 1. Existing Route(s)

- `/profile/payment-methods`
- `/settings/payment-methods` renders the same page for compatibility.

## 2. Purpose

Payment Methods lets a signed-in player save and manage cards for official-game checkout and community-game publish fees. [Game Checkout](game-checkout.md) uses an eligible card for payment or future paid-waitlist authorization; [Create Game](../hosting/create-game.md) uses the host's saved default card when a publish fee is due.

## 3. Main Functionality

### 3.1. View and Add Cards

- Show saved cards with brand, last four digits, expiration, and a Default badge. An empty state invites adding a card when card setup is available.
- **Add card** opens secure card setup. On success, the list refreshes; the first card becomes default. Up to five active cards may be saved.

### 3.2. Manage a Saved Card

- A nondefault card can be made default. Any saved card can be selected for removal through a confirmation modal. These sensitive actions can require recent account confirmation.
- Back normally returns to [Profile](profile.md). A valid in-app checkout return path can instead return the player to checkout after card management.

## 4. Important Behavior & Decisions

### 4.1. Card Ownership and Safety

Cards belong to the signed-in account. The app shows card summaries; secure card entry and authorization use the payment provider. Only active, nonexpired saved cards are eligible for checkout, future automatic charging, or a community publish fee. A detached card is not offered as a saved card. Backend ownership and provider state are checked before changes are accepted.

### 4.2. Defaults and Availability

There is at most one active default card. A successful change updates the list after confirmation. When payments or secure card setup are unavailable, the page explains that state and does not start setup. Provider or sync failures report an error rather than claiming the card was saved or removed.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open either Payment Methods route with saved cards. | Both routes show the same account's cards, brand, last four digits, expiry, and one default marker. |
| 2 | ☐ | Add a first card, then another card. | Successful setup refreshes the list; the first becomes default and adding another does not silently replace it. |
| 3 | ☐ | Make a different active card default. | After required account confirmation, exactly that card is marked default. |
| 4 | ☐ | Remove a card and confirm in the modal. | After required account confirmation, the card disappears from active cards and is no longer usable for checkout or a publish fee; removing the default promotes the oldest remaining active card. |
| 5 | ☐ | Open from checkout with a valid return path. | Back or the post-save return action goes to checkout; ordinary Profile entry goes back to Profile. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Reach five active cards. | Add card is unavailable and a sixth active card cannot be saved. |
| 7 | ☐ | Cancel card setup or removal. | No card is added or detached and the existing list remains intact. |
| 8 | ☐ | Fail provider setup, card synchronization, default change, or removal. | An error appears; the page does not claim the requested change succeeded and can be retried appropriately. |
| 9 | ☐ | Try another user's card, an inactive card, or fail recent account confirmation. | The change is rejected; no cross-account or ineligible card becomes available. |
| 10 | ☐ | Open when card payments or secure setup are unavailable. | The unavailable state is explained; card setup cannot proceed. |
| 11 | ☐ | Open signed out or with no saved cards. | Private access requires sign-in; an authorized empty account sees the empty-card state. |
| 12 | ☐ | Supply an invalid or external return destination. | The page falls back to Profile rather than navigating to that destination. |
| 13 | ☐ | Try to save an already active card again. | The duplicate is rejected without creating a second active card or changing the default. |
| 14 | ☐ | Re-add a previously removed card, first as the only active card and then while another default card exists. | The card returns once to the active list and counts toward the five-card limit; it becomes default when it is the only active card, while an existing default remains unchanged when another card is already active. |

## 6. Open Items to Resolve

**None**.
