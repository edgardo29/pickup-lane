# F07 — Sign In

## 1. Existing Route(s)

- `/sign-in`

## 2. Purpose

Sign In returns an existing player to their account and, when appropriate, to the page where sign-in was requested.

## 3. Main Functionality

### 3.1. Choose a Sign-In Method

Visitors can enter email and password or use Google. The form has a password visibility control, a [Forgot Password](forgot-password.md) link, and a [Create Account](create-account.md) link.

### 3.2. Continue After Sign-In

An active account with a complete profile returns to its saved destination when supplied, otherwise to game discovery. An incomplete account continues to [Finish Profile](finish-profile.md) first, carrying the original destination through profile completion. A suspended account can authenticate and reaches `/account-suspended` for its restricted experience and notice; the suspended-account rules belong to [User Detail](../admin/user-detail.md#410-suspended-player-experience). A successful password reset can display confirmation on Sign In.

## 4. Important Behavior & Decisions

### 4.1. Access and Credentials

Signed-in users are redirected away from this page. Sign-in credentials are verified by the identity provider; Pickup Lane stores app profile data separately. Sign-in errors must not reveal whether an email exists. [Admin Sign In](admin-sign-in.md) separately checks staff access.

### 4.2. Return Context and Errors

Protected-page entry preserves a return destination through authentication and, for an incomplete profile, through Finish Profile. If that destination is no longer available, the established game-discovery fallback applies. Invalid email and missing password receive inline feedback before submission. Provider cancellation, incorrect credentials, and connection failures show a recoverable error without claiming sign-in succeeded.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Sign in with a valid email/password for an active, complete account. | The account opens at the saved destination, or game discovery when none was supplied. |
| 2 | ☐ | Sign in with Google using an active, complete account. | The account opens without creating another profile; the saved destination is used when available. |
| 3 | ☐ | Sign in with an incomplete account from a protected destination. | Finish Profile opens first with the original destination preserved; completing the profile then returns there if still available. |
| 4 | ☐ | Follow Forgot? or Create Account. | The relevant page opens; Create Account retains the return context. |
| 5 | ☐ | Open Sign In after a successful password reset. | The form can show the password-changed confirmation. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Submit an invalid email or empty password. | Inline validation appears and sign-in does not proceed. |
| 7 | ☐ | Use an unknown email or wrong password. | The same general incorrect-credentials message appears; account existence is not disclosed. |
| 8 | ☐ | Cancel Google sign-in or lose the connection. | The page stays available and shows a recoverable error. |
| 9 | ☐ | Open Sign In while already signed in. | An active, complete account goes to the available return destination or game discovery; an incomplete account goes to Finish Profile first with its destination retained; a suspended account reaches `/account-suspended`. |
| 10 | ☐ | Submit twice while a sign-in is pending. | The pending action is disabled and no duplicate user-facing success occurs. |
| 11 | ☐ | Complete authentication or Finish Profile after the saved destination becomes unavailable. | The user reaches the established game-discovery fallback rather than a broken or unauthorized destination. |
| 12 | ☐ | Sign in with a suspended account. | Authentication succeeds, and the user reaches `/account-suspended` to see the restriction and suspension notice without gaining access to prohibited new participation. |

## 6. Open Items to Resolve

**None**.
