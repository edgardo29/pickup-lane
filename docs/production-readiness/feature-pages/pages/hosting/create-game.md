# F14 — Create Game

## 1. Existing Route(s)

- `/create-game`

## 2. Purpose

Create Game lets an eligible signed-in player publish a community soccer game for others to discover and join. The host sets the game, venue, player price, and any off-app payment instructions. [Game Details](../public/game-details.md) owns the published game's attendance and host management.

## 3. Main Functionality

### 3.1. Build and Review a Game

- A four-step form collects game setup, location, notes and host payment methods, then presents a full review before publication. A live preview shows a shorter version while the host edits.
- Game setup includes date, start and end time, player group, format, skill level, indoor or outdoor setting, total spots, and player price.
- Location requires venue name, street, city, state, and ZIP; neighborhood and parking notes are optional. Game notes and host rules are optional.
- A paid community game needs at least one host payment method for players to pay outside Pickup Lane. A free game needs none. Up to two host payment methods can be listed.
- Back moves through the form. Cancel asks before discarding changes and returns to Browse Games when nothing needs saving. No draft is published or saved by leaving the form.

### 3.2. Verify and Publish

- An unverified host sees an email-verification blocker and a Verify Email action to request or resend a link. An expired or invalid link leads back to that resend path; a verified account returns to Create Game with entered form information where applicable and without unnecessary repeated sign-in.
- Review shows the player price, off-app host payment details, and a verified publish fee. The first published community game has its publish fee waived; later publications cost $4.99. If publication history cannot be checked, review shows an error and Retry instead of assuming a free publication.
- Publish can require saved-card payment authentication and may remain pending while the fee outcome is checked. A completed publish shows a success state linking to the new Game Details page.

## 4. Important Behavior & Decisions

### 4.1. Host and Schedule Eligibility

Only an active, email-verified account eligible to host can publish; verification is shared with Need a Sub post creation through [Email Verification](../authentication/email-verification.md). Suspension and an administrative hosting restriction block new publication. A suspended host may still manage games already hosted under [User Detail](../admin/user-detail.md#410-suspended-player-experience). A host may have only one active published community game on a local calendar date. The start must be in the future, no more than 21 days ahead in the game's local calendar, and the end after the start. This creation and editing limit is separate from Browse Games' 14-day display window. Formats run from 3v3 through 11v11; capacity must fit the selected format and cannot exceed 99.

### 4.2. Payment and Publication

The publish fee belongs to the host and is charged only when publishing. The fee must be verified from the host's publication history before it is shown or publication is enabled. If verification fails, the host can retry; the app does not infer a first-game waiver. The amount charged must match the verified amount shown to the host, including if eligibility changes before submission. A paid publish requires a usable saved card, using the host's default card when available. Player payments for paid community games remain between the host and players; Pickup Lane does not charge those players in-app. Publication creates the game, its venue association, host participation, and community details as one workflow. A failed or still-pending publish fee must not be presented as a published game. The verified-email return flow is described in [Email Verification](../authentication/email-verification.md), and saved-card management in [Payment Methods](../player/payment-methods.md).

### 4.3. Published Game Defaults

New community games allow guests and waitlisting. Host guest limits follow the format and available roster space; player guest and attendance actions belong to [Game Details](../public/game-details.md). Changes to an existing game belong to [Edit Game](edit-game.md).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Create Game as an eligible verified player. | The four-step form loads, with game, location, notes/payment, and review steps plus a live preview. |
| 2 | ☐ | Enter a valid free game and review it. | Review shows the full setup, venue, optional notes/rules, Free player price, and no required host payment method. |
| 3 | ☐ | Enter a paid community game with host payment methods. | Review shows the player price and up to two methods for off-app collection; publication requires at least one complete method. |
| 4 | ☐ | Publish the host's first and a later community game. | Verified publication history shows the first fee waived and a later $4.99 fee; the charged amount matches the amount shown, and success links to the new game. |
| 5 | ☐ | Move back through the form or cancel after editing. | Values stay available while navigating steps; Cancel offers keep editing or discard, and discarding returns to Browse Games without publishing. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Open signed out, unverified, or hosting-restricted. | Sign-in is required; unverified users see the verification path; restricted accounts cannot publish a new community game. |
| 7 | ☐ | Submit missing or invalid schedule, venue, format, capacity, price, or host payment details. | The relevant step reports validation and no game is published; start is future, end is later, capacity fits format, and paid games have a host payment method. |
| 8 | ☐ | Try to publish a second active community game on the same local date. | Publication is rejected with the existing-date message; the first game remains unchanged. |
| 9 | ☐ | Publish with a fee that needs card authentication or remains pending. | The page obtains the payment outcome before claiming publication; the new game link appears only after success. |
| 10 | ☐ | Publish a fee-bearing game without a usable saved card, or fail payment authentication or the publish request. | The error is shown and the form remains available for correction or retry without a false success. |
| 11 | ☐ | Fail to load the signed-in account context. | The page shows a load error and does not claim that publication is available. |
| 12 | ☐ | Submit Publish twice while payment or publication is pending. | Only one game and one applicable publish fee result from the attempt; the page does not offer a second concurrent submission. |
| 13 | ☐ | Schedule a community game exactly 21 days ahead, then one 22 days ahead. | The 21-day date is eligible when all other rules hold; the 22-day date is rejected even though Browse has a separate 14-day display window. |
| 14 | ☐ | Fail to verify the host's publication history before review, then retry. | The fee is not assumed free, review shows an error and Retry, publication remains unavailable, and a successful retry shows the verified waiver or $4.99 amount. |
| 15 | ☐ | Change fee eligibility after review but before publication. | Publication cannot charge an amount different from the verified amount shown; the host sees the corrected fee before any charge or completed publication. |
| 16 | ☐ | Return from email verification with an expired link, then resend and verify successfully. | The host can request another verification email; success returns to Create Game with entered information preserved where applicable and without unnecessary repeated sign-in. The verified account can also create a Need a Sub post. |

## 6. Open Items to Resolve

**None**.
