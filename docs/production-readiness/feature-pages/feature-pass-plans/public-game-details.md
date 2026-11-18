# F16 — Game Details Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/public/game-details.md`  
**Endpoints:** `GET /games/{game_id}`, `GET /games/{game_id}/participants`, `GET /game-images`, `GET /venue-images`, `GET /venues/{venue_id}`, `GET /community-game-details`, `POST /games/{game_id}/leave`, `POST /games/{game_id}/guests/add`, `POST /games/{game_id}/guests/remove`, `POST /games/{game_id}/cancel`, `GET /games/{game_id}/change-review`, `POST /games/{game_id}/change-removal-requests`, `POST /game-chats/for-game/{game_id}`, `GET /game-chats/{game_chat_id}/read-state`, `POST /game-chats/{game_chat_id}/read`, `GET /chat-messages`, `POST /chat-messages`

## 1. Page requirements

| Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|
| 3.1 | Game facts, gallery, price, and roster summary | Yes | — |
| 3.1 | Optional notes, rules, payment instructions, terms, venue, parking, map, and share | Yes | — |
| 3.1 | Player list for signed-in visitors; sign-in prompt for list and chat | Yes | — |
| 3.2 | Join routes to account creation, Finish Profile, or checkout | Yes | — |
| 3.2 | Joined with Edit Attendance; Waitlisted with leave waitlist | Yes | — |
| 3.2 | Removal request after an official game changes, with refund or credit choice | Yes | — |
| 3.2 | Host actions and staff official cancellation route | Yes | — |
| 3.3 | Game chat for the host and confirmed players | Yes | — |
| 3.3 | Share through the device or by copying the link | Yes | — |
| 3.3 | Policy modal and community cancellation summary | Yes | — |
| 4.1 | Public details without sign-in; hidden games not found for unrelated visitors | Yes | — |
| 4.1 | Chat only for an active host or confirmed player | Yes | — |
| 4.1 | Verified email for joining, attendance, host changes, and chat | Yes | — |
| 4.1 | Suspended players keep existing bookings, hosted games, and withdrawal | Yes | — |
| 4.2 | Joining window closes five minutes after start; Join Closed; Join Waitlist | Yes | — |
| 4.3 | Host edit and cancel before start; guest limit and capacity | Yes | — |
| 4.3 | Change-related removal request after the usual cutoff | Yes | — |
| 4.4 | Cancelled game stays visible without joining or chat | Yes | — |
| 4.4 | Game Not Found with a link to Browse, distinct from a load error | Yes | — |
| 4.4 | Failed actions keep the game and show an error | Yes | — |
| 4.5 | Community payment responsibility before joining and in the cancellation notice | Yes | — |
| 4.6 | Paused community game shows Joining Temporarily Paused without Join or Add Guest | Yes | — |

## 2. Test scenarios

### 2.1 Backend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| 1 | Visible official and community game details without sign-in | Yes | Pass |
| 2 | Community payment instructions only when allowed | Yes | Pass |
| 3 | Player list for signed-in viewers; chat for host and confirmed players | Yes | Pass |
| 5 | Full game with waitlist enabled or disabled | Yes | Pass |
| 7 | Leave, remove guests, or start adding guests | Yes | Pass |
| 8 | Host guest changes within capacity and guest limit | Yes | Pass |
| 9 | Host cancels a community game | Yes | Pass |
| 10 | Chat message sent and unread state cleared | Yes | Pass |
| 12 | Missing game or unrelated viewer of a hidden game | Yes | Pass |
| 13 | Host, participant, or staff viewing a hidden game | Yes | Pass |
| 14 | Start and five-minute cutoff | Yes | Pass |
| 15 | Stale attendance or host action rejected | Yes | Pass |
| 16 | Cancelled game rejects joining and chat | Yes | Pass |
| 18 | Empty, oversized, or rapid chat messages | Yes | Pass |
| 19 | Unverified email rejected for protected actions | Yes | Pass |
| 20 | Suspended player keeps existing actions, blocked from new ones | Yes | Pass |
| 21 | Removal request after an official game changes | Yes | Pass |
| 22 | Added guests in a paid official game after a successful charge | Yes | Pass |
| 24 | Paused game rejects joins and added guests, allows leaving | Yes | Pass |
| 25 | Resumed game accepts joins; bypassed paused action rejected | Yes | Pass |
| 26 | Official game edit leaves the booking confirmed | Yes | Pass |
| 28 | Staff-removed suspended host: cancelled game and notice | No | |

### 2.2 Frontend tests

| # | Scenario | Test exists? | Result |
|---|---|---|---|
| 1 | Visible official and community game signed out | Yes | Pass |
| 2 | Optional sections shown or left out | Yes | Pass |
| 3 | Player list and chat for each viewer | Yes | Pass |
| 4 | Join as signed out, incomplete, and complete account | Yes | Pass |
| 5 | Full game with waitlist enabled or disabled | Yes | Pass |
| 6 | Hosting, Joined, and Waitlisted states | Yes | Pass |
| 7 | Edit Attendance leave, remove guests, and add guests | Yes | Pass |
| 8 | Manage Guests save and cancel | Yes | Pass |
| 9 | Cancel Game confirmation | Yes | Pass |
| 10 | Open chat and send a message | Yes | Pass |
| 11 | Share and policy modal | Yes | Pass |
| 12 | Game Not Found with a link to Browse | Yes | Pass |
| 14 | Join Closed after the cutoff | Yes | Pass |
| 15 | Rejected stale action shows an error | Yes | Pass |
| 16 | Cancelled game without joining or chat | Yes | Pass |
| 17 | Load error distinct from Game Not Found; failed action keeps the game | Yes | Pass |
| 18 | Empty, oversized, or rapid chat messages show rejection without a successful send | Yes | Pass |
| 19 | Unverified email error on protected actions | Yes | Pass |
| 20 | Suspended player sees existing actions only | Yes | Pass |
| 21 | Review changes and request removal | Yes | Pass |
| 23 | Community cancellation terms with and without organizer text | Yes | Pass |
| 24 | Joining Temporarily Paused for visitor and participant | Yes | Pass |
| 25 | Join and Add Guest return after resume | Yes | Pass |
| 27 | Payment responsibility text before joining | Yes | Pass |
| 28 | Cancelled game after staff removed the host | Yes | Pass |

## 3. Work to do

Items 1–10 are done. Items 12–20 were found in the 2026-11-18 review and are done. Item 11 remains, blocked as described below.

11. Implement the explicit staff action to remove a suspended community-game host for safety or misconduct, cancelling the game with no replacement and notifying every registered player through the community cancellation path. Re-check Community Game Detail and User Detail, which own this staff workflow; then verify F16 scenario 28 end to end.

12. Turn off guest removal in Edit Attendance while a community game is paused, matching Add Guest and Manage Guests, because the backend rejects guest changes on a paused game (Community Game Detail, Section 4.2). Extend the paused-player scenario 24 test to check it.
13. Add the changed-official-game removal request table to `docs/production-readiness/data-model-baseline.md`, with its inbound references from bookings and users, and update the document's schema counts.
14. Replace finished work in this section with a note that it is done, so only blocked work remains listed.
15. Add the frontend scenario 15 test: a host guest addition rejected after the last spot was taken shows the server's error and changes nothing.
16. Extend the frontend scenario 10 test to check that opening chat marks it read and clears the unread badge.
17. Remove the scenario 28 marker from the backend host-cancellation test, which proves scenario 9, and move the staff-cancellation notice test to `backend/tests/domains/notifications/`, citing Section 4.5, because neither test performs the blocked host-removal action.
18. Check exact status codes in the backend tests for chat on a cancelled game (400) and empty (400) or oversized (422) chat messages.
19. Use the server's real message, "Verified email required.", in the frontend unverified-email tests for scenario 19.
20. Build every community game in the backend tests with the host's confirmed roster place, as publishing creates it, and count only players in the tests' roster counts.

## Blocked

- **Scenario 28 (item 11):** blocked by the staff action that removes a suspended community host, owned by Community Game Detail and User Detail. Re-run scenario 28 when that action exists.
