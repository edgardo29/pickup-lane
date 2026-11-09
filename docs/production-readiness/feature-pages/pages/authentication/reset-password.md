# F10 — Reset Password

## 1. Existing Route(s)

- `/reset-password` (password-reset mode, including `?mode=resetPassword`)

`?mode=verifyEmail` uses the separate [Email Verification](email-verification.md) experience.

## 2. Purpose

Reset Password lets a visitor with a valid password-reset email link choose a new password and return to Sign In.

## 3. Main Functionality

### 3.1. Check the Link

The page verifies the link before showing the password form. It can show a checking state, the account email, or an invalid/expired-link state with a **Request New Reset Link** action that opens the existing request flow.

### 3.2. Set a New Password

The visitor enters a new password, can reveal or hide it, and saves it. Success shows a confirmation and a link to [Sign In](sign-in.md).

## 4. Important Behavior & Decisions

### 4.1. Provider-Owned Reset

The email link and password update are handled by the identity provider. Pickup Lane does not store the password in its app database. The password must be at least eight characters and include a number or symbol.

### 4.2. Invalid Links and Modes

A missing, invalid, expired, or already-used reset link detected when the page checks it does not expose the password form and offers **Request New Reset Link** within the existing flow. A link can also expire or be used after that check but before the new password is saved; then the password stays unchanged, the entered replacement password is cleared, and the page explains the problem and offers the same new-link action without requiring a manual restart from Sign In. An unsupported action mode redirects to Sign In. Other failed saves report an error and leave the visitor able to recover.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open a valid reset link. | The link is checked, then the new-password form appears with the account email when available. |
| 2 | ☐ | Submit a valid new password. | The provider accepts the change, the form is replaced by a success message, and Sign In is available. |
| 3 | ☐ | Use the password visibility control. | The password alternates between concealed and visible without changing its value. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 4 | ☐ | Open with no code or an invalid, expired, or used code. | No password form appears; the visitor sees the link problem and a Request New Reset Link action leading to the existing request flow. |
| 5 | ☐ | Submit a short password or one without a number/symbol. | Validation appears and no password update is attempted. |
| 6 | ☐ | Fail the password update after link verification. | An error appears and the page does not claim the password changed. |
| 7 | ☐ | Open the route with an unsupported action mode. | The visitor is redirected to Sign In. |
| 8 | ☐ | Submit repeatedly while saving. | The save action is disabled until the request settles. |
| 9 | ☐ | Let a valid link expire or become used after its initial check, then submit a valid new password. | The password is not changed; the entered replacement password is cleared, the page explains the invalid link without claiming success, and Request New Reset Link opens the existing request flow. |

## 6. Open Items to Resolve

**None**.
