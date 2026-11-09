# F02 — Terms of Service

## 1. Existing Route(s)

- `/terms`

## 2. Purpose

Terms of Service gives visitors the current terms for using Pickup Lane, including player conduct, game and payment responsibilities, and account restrictions.

## 3. Main Functionality

### 3.1. Read the Terms

The page presents the Terms title and its sections in reading order. It is reachable from the footer; Create Account also opens the same terms in a modal.

### 3.2. Leave the Page

The brand opens Landing. The Back control returns to a supplied origin when one is available, otherwise to Landing.

## 4. Important Behavior & Decisions

### 4.1. Public, Read-Only Policy

No account is required. Reading this page does not create an account or record policy acceptance. Terms content is shared with the modal used in [Create Account](../authentication/create-account.md).

### 4.2. Development Copy

The current text explicitly identifies itself as a working placeholder pending final legal review. It must not be described here as final launch language.

### 4.3. Required Community-Game Payment Responsibility

The Terms must reflect that community-game payments occur outside Pickup Lane, directly between players and organizers, and that any payment dispute or refund remains between the players and the original organizer, including when a game is cancelled after staff remove a suspended host. Pickup Lane does not process or guarantee those refunds. This is a content requirement for the final Terms; their legal wording remains pending review. The player-facing presentation is described in [Game Details](game-details.md#45-community-game-payment-responsibility).

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Terms directly while signed out or signed in. | Both viewers can read the Terms title and all current sections without a sign-in gate. |
| 2 | ☐ | Open Terms from the footer and the Create Account modal. | Both surfaces show the same policy content. |
| 3 | ☐ | Select the brand or Back control. | The brand opens Landing; Back returns to the supplied origin when present. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 4 | ☐ | Open the route without origin state. | Back opens Landing. |
| 5 | ☐ | Read through the current policy. | Its development placeholder notice remains visible with the current copy. |
| 6 | ☐ | Read the Terms' community-game payment section. | It states that community-game payments occur directly between players and organizers outside Pickup Lane, that disputes and refunds remain between them, and that Pickup Lane does not process or guarantee those refunds. |

## 6. Open Items to Resolve

- **Launch terms — unresolved content:** Final legal language is explicitly pending review. Evidence: `frontend/src/features/legal/legalPolicies.js:28-29`; `docs/feature-notes/auth.md:128-131`.
