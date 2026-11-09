# F08 — Forgot Password

## 1. Existing Route(s)

- `/forgot-password`

## 2. Purpose

Forgot Password lets a visitor request a password reset link for an email account without revealing whether that account exists.

## 3. Main Functionality

### 3.1. Request a Link

The visitor enters an email and selects **Send Reset Link**. On an accepted request, [Check Email](check-email.md) opens with the submitted email for confirmation and possible resend. Back returns to [Sign In](sign-in.md).

## 4. Important Behavior & Decisions

### 4.1. Account Privacy

An unknown email follows the same confirmation route as a known email. The identity provider sends the reset email; this page does not reset the password itself. The link is handled by [Reset Password](reset-password.md).

### 4.2. Validation and Failure

Invalid email is rejected before requesting a link. A non-account-related provider or network error remains on this page with retry feedback. The send control is disabled while a request is pending.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Submit a valid email for an existing account. | The reset request is sent and Check Email opens with the normalized email. |
| 2 | ☐ | Submit a valid email that has no account. | Check Email opens with the same non-disclosing confirmation; account existence is not revealed. |
| 3 | ☐ | Select Back. | Sign In opens without changing a password. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 4 | ☐ | Submit a blank or malformed email. | Inline validation appears and no reset request is sent. |
| 5 | ☐ | Fail the reset request for a reason other than unknown account. | The page shows a recoverable error and does not claim an email was sent. |
| 6 | ☐ | Submit repeatedly while sending. | The send control remains disabled until the request settles. |

## 6. Open Items to Resolve

**None**.
