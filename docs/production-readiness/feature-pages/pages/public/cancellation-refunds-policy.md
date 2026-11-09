# F04 — Cancellation & Refunds Policy

## 1. Existing Route(s)

- `/policies/cancellation-refunds`

## 2. Purpose

This page explains the current published summary of cancellation, refund, credit, waitlist, guest, and weather rules for Pickup Lane games.

## 3. Main Functionality

### 3.1. Read the Policy

Visitors can read the policy by topic. The footer links here; [Game Details](game-details.md) shows a game-specific summary and opens the same policy content in a modal.

### 3.2. Leave the Page

The brand opens Landing. The Back control returns to a supplied origin when available, otherwise to Landing.

## 4. Important Behavior & Decisions

### 4.1. Public, Read-Only Policy

No account is required. This page explains rules; it does not cancel a booking, issue a refund, or change game status. Those actions and outcomes belong to the game and booking workflows.

### 4.2. Current Policy Summary

- Official game cancellation at least 24 hours before start can be eligible for a refund or game credit; later cancellation may not be refunded. A player for whom changed official-game details no longer work may request removal and choose a refund to the original payment method or game credit, including after that cutoff. The booking remains confirmed until the removal and corresponding request are processed; the edit or request alone issues no refund or credit.
- Pickup Lane cancellation of an official game returns eligible paid value through refund and/or restoration of used game credit.
- Community host payments occur outside Pickup Lane, directly between players and the organizer. A game's organizer-provided cancellation/refund terms apply when available; without them, players must confirm payment and refund arrangements with the organizer. Any payment dispute or refund remains between the players and the original organizer, including when a community game is cancelled because staff removed a suspended host. Pickup Lane does not process or guarantee those refunds.
- Waitlisted players pay only if confirmed; guest cancellation follows the relevant game policy.
- Unsafe weather or field conditions may cause an outdoor game to be cancelled.

### 4.3. Development Copy

The page explicitly states that the policy is a working development version awaiting final legal review.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open the policy directly while signed out or signed in. | Both viewers can read every current section without a sign-in gate. |
| 2 | ☐ | Open the full policy from the footer and the Game Details modal. | Both surfaces show the same cancellation and refund policy content. |
| 3 | ☐ | Read official, community, waitlist, guest, and weather sections. | Each topic appears with the current policy summary and development notice. |
| 4 | ☐ | Select the brand or Back control. | The brand opens Landing; Back returns to a supplied origin when present. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 5 | ☐ | Open the policy without origin state. | Back opens Landing. |
| 6 | ☐ | Read the policy without a game context. | The general policy remains readable; no booking or refund action is offered. |
| 7 | ☐ | Read the rule for a player unable to accept changed official-game details. | The policy explains the request-to-leave choice and original-method refund or game credit, including after the usual cutoff; value is returned when removal and the corresponding request are processed, not merely when the game is edited. |
| 8 | ☐ | Read the community-game payment and refund summary. | It identifies organizer-provided terms when available and does not promise a refund when none were provided; players are directed to confirm arrangements with the organizer. |
| 9 | ☐ | Read the community-game summary for a game cancelled after staff removed its suspended host. | The policy states that payment disputes and refunds remain between the players and the original organizer, and that Pickup Lane does not process or guarantee them. |

## 6. Open Items to Resolve

- **Launch cancellation policy — unresolved content:** The current wording explicitly awaits final legal review. Evidence: `frontend/src/features/legal/legalPolicies.js:88-89`.
