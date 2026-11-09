# F16 — Game Details

## 1. Existing Route(s)

- `/games/:gameId`

## 2. Purpose

Game Details lets visitors review one official or community game before joining. Signed-in players can manage their participation; community hosts can manage guests and cancel their game. This page is the entry point to [Game Checkout](../player/game-checkout.md), which owns booking and payment confirmation.

## 3. Main Functionality

### 3.1. Review the Game

- Show the game title, official/community status, gallery, date and time, duration, format, player group, skill level, environment, price, and roster summary.
- Show optional description, host rules, community host payment instructions when available, game terms, venue address, parking note, map action, and sharing action.
- Signed-in visitors can open the player list. Signed-out visitors are prompted to create an account or sign in for the list and chat.

### 3.2. Join or Manage Attendance

- A visitor can start joining from this page; a signed-out visitor goes to account creation and an incomplete account goes to Finish Profile before checkout.
- A confirmed player sees **Joined** and can use **Edit Attendance** to leave, remove guests, or start add-guest checkout. A waitlisted player sees **Waitlisted** and can leave the waitlist.
- A player whose official-game details changed can review the changes and, if they no longer work, request removal with an original-method refund or game-credit choice. The booking stays confirmed until the request and removal are processed.
- A community host sees **Hosting**, **Edit Game**, **Manage Guests**, **Cancel Game**, and **Share Game** as applicable. Official game cancellation for staff opens the official game admin workflow.
- A paused community game shows **Joining Temporarily Paused**. New Join and Add Guest actions are unavailable, while existing participants can view their booking and leave. Resuming joining restores eligible participation actions.

### 3.3. Coordinate and Share

- Hosts and confirmed players can open game chat, read recent messages, and send text updates. Other visitors see the chat action unavailable.
- Share Game uses the device share action when available, otherwise copies the game link. Closing a share sheet without sharing is harmless.
- Game terms can open the relevant policy or conduct text in a modal. For community games, the cancellation summary uses organizer-provided terms when present; without them it points to the host payment note and promises no refund. The full [Cancellation & Refunds Policy](cancellation-refunds-policy.md) has its own route.

## 4. Important Behavior & Decisions

### 4.1. Visibility and Access

Publicly visible game details can be opened without signing in. Hidden games are available only to authorized connected users or staff; unrelated visitors receive a not-found result. The player list remains a signed-in page action. Game chat requires an active host or confirmed player, never a guest, waitlisted player, or unrelated user. A verified email is required to join or change attendance, make host changes, start game chat, or send chat messages; public game details remain viewable without verification. Suspended players cannot initiate new participation or add guests, but may access existing bookings, fulfill accepted commitments, manage games they already host, and withdraw; see [User Detail](../admin/user-detail.md#410-suspended-player-experience).

### 4.2. Joining Window

Joining, waitlisting, attendance changes, guest changes, and promotion close exactly five minutes after scheduled start. A nonparticipant then sees **Join Closed**. A full game can offer **Join Waitlist** only while that window is open and the waitlist accepts players. Joining, guest pricing, payment, and promotion rules are owned by [Game Checkout](../player/game-checkout.md) and the established game/booking notes.

### 4.3. Host and Player Changes

Community hosts can edit or cancel an active published game only before start. Host guest changes can continue until the roster window closes and cannot exceed the host guest limit or open capacity. Confirmed players use attendance controls; added guests pass through checkout, while removing guests or leaving follows the applicable cancellation terms. A player for whom changed official-game details no longer work may request removal and choose an original-method refund or game credit, including after the usual cutoff. The request alone does not end the booking or return value; [Edit Official Game](../admin/edit-official-game.md#47-player-notice-and-withdrawal) owns the change rule, and [Official Game Manage](../admin/official-game-manage.md#43-removing-players) owns staff processing.

### 4.4. Status and Failure States

A cancelled game remains available for history and displays **Cancelled** without joining or chat actions. A missing or inaccessible game shows **Game Not Found** with a link back to Browse Games and no protected game information; a technical or network failure shows a distinct load error. Failed participation changes leave the current game state in place and show an error.

### 4.5. Community-Game Payment Responsibility

Before a player joins a community game, the page states that payment happens
outside Pickup Lane, directly between players and the organizer, and that any
payment dispute or refund remains between the player and the original
organizer. Pickup Lane does not process or guarantee those refunds. This
applies however the game ends, including host cancellation and cancellation
after staff remove a suspended host. A community-game cancellation notice
repeats this responsibility. The published policy wording belongs to the
[Cancellation & Refunds Policy](cancellation-refunds-policy.md) and
[Terms of Service](terms-of-service.md).

### 4.6. Paused Community Games

A paused community game remains available at its direct detail link while it is absent from Browse. The page clearly shows **Joining Temporarily Paused** and suppresses Join and Add Guest until the pause is lifted. Existing booking and leave actions remain available subject to their ordinary rules. The backend rejects new participation while paused; see [Community Game Detail](../admin/community-game-detail.md#42-public-effect).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a visible official and community game signed out. | Each shows its game facts, gallery or fallback, venue information, price, terms, and available join action without requiring sign-in. |
| 2 | ☐ | Open a game with optional host notes, rules, parking, or payment information. | Available information appears in the appropriate section; absent optional content does not leave empty sections. Community payment instructions appear only when allowed and visible. |
| 3 | ☐ | Open the player list and chat as different viewers. | Signed-in viewers can inspect the player list; only the host and confirmed players can open chat; signed-out and waitlisted viewers cannot. |
| 4 | ☐ | Choose Join Game as a guest, an incomplete account, and a complete account. | The guest goes to account creation with the game return path, the incomplete user goes to Finish Profile, and the complete user opens checkout. |
| 5 | ☐ | View a full game with waitlist enabled or disabled. | The enabled game offers Join Waitlist; the disabled game cannot confirm a new party without capacity. |
| 6 | ☐ | View as host, confirmed player, and waitlisted player. | Each sees the correct Hosting, Joined, or Waitlisted state and only the actions for that relationship. |
| 7 | ☐ | Use Edit Attendance to leave, remove guests, or add guests. | Leaving or removal updates the roster after success; adding guests opens add-guest checkout and does not change the booking before confirmation and any required payment. |
| 8 | ☐ | Manage community host guests. | Saving an allowed count updates roster occupancy; cancelling the modal changes nothing; capacity and host guest limit prevent excess guests. |
| 9 | ☐ | Cancel a community game as its host. | Confirmation cancels the game and shows the cancelled state; connected players receive the established cancellation handling. |
| 10 | ☐ | Open game chat as an eligible member and send a message. | Recent messages appear; a valid text message is added, and opening the chat clears the viewer's unread state. |
| 11 | ☐ | Share a game or open a game policy. | Share opens native sharing or copies the link; the selected policy opens in a dismissible modal. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 12 | ☐ | Open a missing game or a hidden game without a qualifying relationship. | The page shows **Game Not Found** with a link to Browse Games and exposes no hidden detail or roster. |
| 13 | ☐ | Open a hidden game as its host, current participant, or authorized staff member. | Authorized detail is available; roster visibility still follows that viewer's relationship. |
| 14 | ☐ | Pass scheduled start and then the five-minute roster cutoff. | Editing/cancellation closes at start; joining and roster changes stay available only before the five-minute cutoff, then Join Closed replaces joining for nonparticipants. |
| 15 | ☐ | Attempt an attendance or host action after capacity, status, or time changes. | The backend rejects an ineligible stale action; the page shows an error and does not claim the change succeeded. |
| 16 | ☐ | Load a cancelled game. | Cancelled status remains visible for history; joining and chat are unavailable. |
| 17 | ☐ | Fail the detail request for a technical or network reason, or fail an action request. | A technical detail failure shows a load error rather than **Game Not Found**; an action failure retains the existing game and displays feedback. |
| 18 | ☐ | Send empty, oversized, or rapid repeated chat messages. | Invalid or rate-limited messages are rejected without appearing as successful sends. |
| 19 | ☐ | View a public game with a signed-in but unverified email, then try joining, changing attendance or host details, or starting or sending game chat. | The game remains readable, but protected actions require verified email; rejected attempts show an error and do not change the game, roster, or chat. |
| 20 | ☐ | Open an existing game as a suspended confirmed player or host, then attempt a new join or guest addition. | Existing booking and hosting actions needed for fulfillment or withdrawal remain available; new participation and added guests are blocked without changing the roster. |
| 21 | ☐ | Open an official game after staff change its details, then request to leave because the changes no longer work, including after the usual cutoff. | The player sees the changed details and can choose an original-method refund or game credit; the booking stays confirmed until removal and the corresponding request are processed. |
| 22 | ☐ | Attempt to add guests to a paid official game. | Guests are added only after a real Stripe charge for the applicable amount succeeds, with available game credit applied under checkout rules; failure leaves attendance and capacity unchanged. |
| 23 | ☐ | Review community-game cancellation terms with and without organizer-provided text. | Provided terms appear for that game; when absent, the summary points to the host payment note and does not promise a refund. |
| 24 | ☐ | Open a paused community game directly as a visitor and as an existing participant. | The page shows Joining Temporarily Paused; Join and Add Guest are unavailable, while the existing participant can view the booking and leave under the usual rules. |
| 25 | ☐ | Resume joining on a paused community game, or bypass its disabled controls while still paused. | Eligible participation actions return after resume; a bypassed join or guest change during pause is rejected by the backend without changing the roster. |
| 26 | ☐ | View an official-game edit without requesting removal. | The player's booking remains confirmed at its original paid price; no refund or game credit is issued solely because of the edit. |
| 27 | ☐ | Open a free and a paid community game before joining. | Before the join action, each states that payment happens outside Pickup Lane with the organizer and that disputes and refunds remain between the player and the original organizer; Pickup Lane does not promise a refund. |
| 28 | ☐ | Open a community game after staff removed its suspended host, as a registered player. | The game shows **Cancelled** without joining or chat actions; the player's cancellation notice states that payment disputes and refunds remain with the original organizer. |

## 6. Open Items to Resolve

**None**.
