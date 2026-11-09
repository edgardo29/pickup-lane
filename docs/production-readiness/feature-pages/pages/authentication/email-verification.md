# F11 — Email Verification

## 1. Existing Route(s)

- `/reset-password?mode=verifyEmail` (email-verification action mode)

The same route in password-reset mode belongs to [Reset Password](reset-password.md).

## 2. Purpose

Email Verification processes the account-level email-verification link used by community-game and Need a Sub post creation.

## 3. Main Functionality

### 3.1. Confirm Email

The page processes the existing Firebase verification link and refreshes the current account's verification state. It shows checking, verified, invalid/expired, or not-yet-confirmed feedback. A valid verified account can continue without unnecessary repeated authentication.

### 3.2. Return to Hosting

Verification preserves the intended return destination, including [Create Game](../hosting/create-game.md) and [Create Sub Post](../hosting/create-sub-post.md), and entered form information where applicable. An expired or invalid link offers a way to request another verification email through the existing send/resend flow at the originating entry point.

## 4. Important Behavior & Decisions

### 4.1. Hosting Gate

One verified account state unlocks both community-game creation and Need a Sub post creation; there are no separate feature verification states. Public browsing is available without verification. Firebase link generation, the application route, and link handling must work as one flow. The backend uses the current verified provider identity, not a client assertion, to authorize protected actions. A verification result does not itself publish a game or post.

### 4.2. Unavailable or Reused Link

A missing, expired, or already-used code does not claim verification and offers a fresh verification-email path. If the current account is already confirmed after refresh, the page can show success even when applying a reused link did not succeed. A successful link application whose account state cannot be confirmed shows a separate unavailable outcome. A signed-in, verified player continues to the preserved destination without another sign-in.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a valid email-verification link while signed in. | Firebase verification is processed through the application route, account state refreshes, and success appears without another authentication step. |
| 2 | ☐ | Follow Continue after verification from Create Game. | The preserved Create Game destination opens; publishing still follows that page's eligibility and form rules. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 3 | ☐ | Open without a code or with an invalid/expired code. | The page explains the failure, does not claim verification, and offers a way to request another verification email. |
| 4 | ☐ | Open a reused code when the signed-in account is already verified. | Refreshed verified account state can show success despite the reused code. |
| 5 | ☐ | Apply a link but fail to confirm the current account state. | The page shows verification not confirmed and offers a retry or fresh-email path without claiming hosting access. |
| 6 | ☐ | Verify from Create Sub Post with entered information, then return. | The same account verification unlocks both creation flows; the user returns to the preserved destination with entered information where applicable rather than being sent unconditionally to Create Game. |
| 7 | ☐ | Return to an already verified signed-in account after opening a used link. | Refreshed account state permits continuation without unnecessary repeated authentication. |
| 8 | ☐ | Browse games or Need a Sub posts before verifying the account. | Public discovery remains available; the verification requirement applies when attempting a protected creation action. |

## 6. Open Items to Resolve

**None**.
