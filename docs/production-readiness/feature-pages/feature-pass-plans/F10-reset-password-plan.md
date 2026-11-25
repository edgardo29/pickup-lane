# F10 — Reset Password Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F10-reset-password-spec.md`  
**Endpoints:** None. Firebase’s browser SDK checks the reset link and updates the password.

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | Check the current reset link before showing the password form | Yes | — |
| R2 | 3.1 | Show the account email when Firebase supplies it | Yes | — |
| R3 | 4.1 | Firebase handles the password update; no password is stored in the app database or browser storage | Yes | — |
| R4 | 4.1 | Require eight characters and a number or symbol | Yes | — |
| R5 | 3.2 | Reveal and hide the password without changing it | Yes | — |
| R6 | 3.2 | Replace the form with a success confirmation after Firebase accepts the change | Yes | — |
| R7 | 3.2 | Open Sign In from the success confirmation | Yes | — |
| R8 | 3.1, 4.2 | Explain unavailable links and offer Request New Reset Link | Yes | — |
| R9 | 4.2 | Redirect unsupported action modes to Sign In | Yes | — |
| R10 | 4.2 | Other failed saves show an error and allow recovery without claiming success | Yes | — |
| R11 | 5.2 scenario 8; 3.2 | Disable saving until the request settles | Yes | — |
| R12 | 4.2 | Clear the entered password and offer a new link if the checked link expires or is used before saving | Yes | — |
| R13 | 3.1, 4.2; frontend-standards.md Sections 4, 6 | Keep link validation and save results attached to the current URL | Yes | — |
| R14 | 4.1; frontend-standards.md Section 9 | Associate password instructions and validation errors with the input | Yes | — |
| R15 | 3.1, 3.2; frontend-standards.md Section 9 | Expose checking and success feedback to screen readers | Yes | — |
| R16 | 1; F11 Sections 1, 3.1 | Keep email-verification mode separate from password resetting | Yes | — |
| R17 | 3.2; frontend-standards.md Sections 4, 6 | Preserve pending saves and success when authentication state updates for the same reset link | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F10-1` is scenario 1); "Section 4.1" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|

No backend cases: Firebase checks reset codes and changes passwords directly; this page makes no Pickup Lane API request.

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F10-1, Section 3.1 | The link is checked through Firebase before the password form appears. | R1 | `F10-1: Firebase checks the URL code before the form opens (%s)` (`link_checks.test.jsx`) | Sent a different code to Firebase; the code-argument check failed. | `authProviderCredentialActions.js` |
| 2 | F10-1, Section 3.1 | A pending link check shows checking feedback without exposing the password form. | R1, R15 | `F10-1: a pending check announces progress without exposing the form` (`link_checks.test.jsx`) | Before fix: checking feedback had no status region; the accessibility check failed. | `PasswordResetPanel.jsx` |
| 3 | F10-1, Section 3.1 | After a valid link is checked, the new-password form appears. | R1 | `F10-1: a verified reset code opens the password form` (`link_checks.test.jsx`) | Kept a verified link unavailable; the password form did not appear. | `usePasswordResetForm.js` |
| 4 | F10-1, Section 3.1 | The form identifies the account email when available. | R2 | `F10-1: the form shows the email returned by Firebase` (`link_checks.test.jsx`) | Replaced the email returned by Firebase with another address. | `usePasswordResetForm.js` |
| 5 | F10-1, Section 3.1 | The form still opens when a valid link check supplies no account email. | R2 | `F10-1: a valid check without an email still opens the form` (`link_checks.test.jsx`) | Treated a successful check without an email as an invalid link. | `usePasswordResetForm.js` |
| 6 | F10-2, Section 4.1 | Saving a valid new password sends that password and the checked code to Firebase. | R3, R4 | `F10-2: a valid minimum-length password and checked code are sent to Firebase (%s)` (`saving.test.jsx`) | Sent the wrong code with the password; the Firebase-call check failed. | `authProviderCredentialActions.js` |
| 7 | F10-2, Section 3.2 | After Firebase accepts the change, a success confirmation appears and is available to screen readers. | R6, R15 | `F10-2: Firebase acceptance announces that the password changed` (`saving.test.jsx`) | Returned to the form after Firebase accepted the change; the success announcement was absent. | `usePasswordResetForm.js` |
| 8 | F10-2, Section 3.2 | After a successful save, the password form is replaced. | R6 | `F10-2: a successful save replaces the password form` (`saving.test.jsx`) | Returned to the form after Firebase accepted the change; the form remained visible. | `usePasswordResetForm.js` |
| 9 | F10-2, Section 3.2 | Following Sign In from the success confirmation opens Sign In. | R7 | `F10-2: Sign In from the success confirmation opens Sign In` (`saving.test.jsx`) | Sent the success link to Forgot Password instead of Sign In. | `PasswordResetPanel.jsx` |
| 10 | F10-3, Section 3.2 | The password alternates between concealed and visible without changing its value. | R5 | `F10-3: revealing and hiding preserves the entered password` (`password_input.test.jsx`) | Kept the input concealed after Show password was selected. | `PasswordResetPanel.jsx` |
| 11 | F10-4, Section 4.2 | A missing, invalid, expired, or already-used link does not expose the password form. | R8 | `F10-4: an unavailable link never exposes the form (%s)` (`link_checks.test.jsx`) | Exposed the password form for missing and rejected codes. | `usePasswordResetForm.js` |
| 12 | F10-4, Section 4.2 | The visitor sees the problem with a missing, invalid, expired, or already-used link. | R8 | `F10-4: the link problem is explained (%s)` (`link_checks.test.jsx`) | Replaced the missing/rejected-link explanation with unrelated text. | `usePasswordResetForm.js` |
| 13 | F10-4, Section 4.2 | Request New Reset Link opens the existing Forgot Password request flow. | R8 | `F10-4: Request New Reset Link opens Forgot Password (%s)` (`link_checks.test.jsx`) | Before fix: the action was labelled Send New Link; the specified action was absent. | `PasswordResetPanel.jsx` |
| 14 | F10-4, Section 3.1; frontend-standards.md Section 6 | A network or other failed link check gives recovery feedback without claiming that the link expired. | R1, R8 | `F10-4: a failed link check offers recovery without falsely calling the link expired (%s)` (`link_checks.test.jsx`) | Before fix: network and other check failures were labelled expired links. | `PasswordResetPanel.jsx` |
| 15 | F10-5, Section 4.1 | A short password or one without a number or symbol shows validation. | R4 | `F10-5: an invalid password shows its requirements (%s)` (`password_input.test.jsx`) | Bypassed password validation; the required validation message was absent. | `usePasswordResetForm.js` |
| 16 | F10-5, Section 4.1 | An invalid password does not attempt a Firebase password update. | R3, R4 | `F10-5: an invalid password never reaches Firebase (%s)` (`password_input.test.jsx`) | Bypassed password validation; invalid passwords reached Firebase. | `usePasswordResetForm.js` |
| 17 | F10-5, Section 4.1; frontend-standards.md Section 9 | Password validation identifies the input as invalid and associates its error with that input. | R4, R14 | `F10-5: validation marks the password invalid and associates its error` (`password_input.test.jsx`) | Before fix: validation supplied neither an invalid input state nor an associated error. | `PasswordResetPanel.jsx` |
| 18 | F10-1, Section 4.1; frontend-standards.md Section 9 | The password input is associated with its password requirements. | R14 | `F10-1: password requirements describe the input accessibly` (`password_input.test.jsx`) | Before fix: the password instructions were not associated with the input. | `PasswordResetPanel.jsx` |
| 19 | F10-6, Section 4.2 | Another Firebase or network save failure shows a recoverable error. | R10 | `F10-6: a failed save reports a recoverable error (%s)` (`saving.test.jsx`) | Removed failed-save error text; the recoverable error was absent. | `usePasswordResetForm.js` |
| 20 | F10-6, Section 4.2 | A failed save does not claim that the password changed. | R10 | `F10-6: a rejected save never claims the password changed (%s)` (`saving.test.jsx`) | Reported success after Firebase rejected the save. | `usePasswordResetForm.js` |
| 21 | F10-6, Section 4.2 | After a recoverable save failure, the visitor can retry successfully. | R3, R10 | `F10-6: a recoverable failure allows a successful retry (%s)` (`saving.test.jsx`) | Blocked another submission after a recoverable error. | `usePasswordResetForm.js` |
| 22 | F10-7, Section 4.2 | An unsupported action mode redirects to Sign In without attempting a password reset. | R9 | `F10-7: an unsupported mode redirects to Sign In without resetting (%s)` (`navigation.test.jsx`) | Redirected unsupported modes to Forgot Password instead of Sign In. | `ResetPasswordPage.jsx` |
| 23 | F10-8, Section 3.2 | The save action is disabled until the request settles, preventing repeated submission. | R11 | `F10-8: saving stays disabled until Firebase settles (%s)` (`saving.test.jsx`) | Enabled the save button while its request was still pending. | `PasswordResetPanel.jsx` |
| 24 | F10-9, Section 4.2 | When Firebase rejects a code that expired or was used after checking, the entered replacement password is cleared. | R12 | `F10-9: an expired or used code clears the entered replacement password (%s)` (`link_recovery.test.jsx`) | Before fix: Firebase rejected the expired/used code but the entered password remained. | `usePasswordResetForm.js` |
| 25 | F10-9, Section 4.2 | The page explains that the previously checked link is expired or already used. | R12 | `F10-9: a code rejected during saving explains the link problem (%s)` (`link_recovery.test.jsx`) | Removed the explanation when Firebase rejected an expired/used code during saving. | `usePasswordResetForm.js` |
| 26 | F10-9, Section 4.2 | Request New Reset Link opens the existing request flow after the link becomes unusable during saving. | R12 | `F10-9: Request New Reset Link opens the request flow after a rejected save (%s)` (`link_recovery.test.jsx`) | Before fix: a rejected expired/used code left no Request New Reset Link action. | `usePasswordResetForm.js`; `PasswordResetPanel.jsx` |
| 27 | F10-9, Section 4.2 | A rejected expired or used code produces no success claim or fallback password-change attempt. | R3, R12 | `F10-9: a rejected unusable code never claims success or tries a fallback password update (%s)` (`link_recovery.test.jsx`) | Reported success after Firebase rejected an expired/used code. | `usePasswordResetForm.js` |
| 28 | F10-1, Section 3.1; frontend-standards.md Sections 4, 6 | Changing to another reset code checks that code before showing its form; an earlier link check cannot replace the current result. | R1, R13 | `F10-1: a changed URL checks its own code and ignores earlier replies (%s)` (`navigation.test.jsx`) | Reused the old form and accepted obsolete link-check replies. | `ResetPasswordPage.jsx`; `usePasswordResetForm.js` |
| 29 | F10-4, Section 4.2; frontend-standards.md Sections 4, 6 | Removing the reset code from the current URL shows the missing-link outcome instead of a previous form or checking state. | R8, R13 | `F10-4: removing the URL code shows the missing-link result (%s)` (`navigation.test.jsx`) | Reused the previous form and accepted obsolete checks; removing the code left the wrong page state. | `ResetPasswordPage.jsx`; `usePasswordResetForm.js` |
| 30 | F10-2, F10-6, Section 3.2; frontend-standards.md Sections 4, 6 | A save completing for an earlier reset link cannot replace the current link’s checking, form, or error state. | R13 | `F10-2, F10-6: an earlier save cannot replace the current link state (%s, %s)` (`navigation.test.jsx`) | Reused the previous form; an earlier save replaced the current link’s checking, form, or error state. | `ResetPasswordPage.jsx`; `usePasswordResetForm.js` |
| 31 | F10-2, Section 4.1 | Resetting uses Firebase and does not send the replacement password to the app API or browser storage. | R3 | `F10-2: the password is sent only to Firebase, never the app API or browser storage` (`saving.test.jsx`) | Wrote the replacement password to localStorage and sessionStorage. | `authProviderCredentialActions.js` |
| 32 | F10-7, Section 1; F11 Sections 1, 3.1 | Email-verification mode opens its existing verification experience without checking or saving a password. | R16 | `F10-7: email-verification mode opens email verification without a password reset` (`navigation.test.jsx`) | Disabled email-verification dispatch; its verification experience did not open. | `ResetPasswordPage.jsx` |
| 33 | F10-8, Section 3.2; frontend-standards.md Sections 4, 6 | An authentication-state update keeps Save disabled until the current save settles. | R11, R17 | `F10-8: authentication updates keep saving disabled until its request settles (%s)` (`saving.test.jsx`) | Before fix: an authentication update re-enabled Save while the request was still pending; both settlement variations failed. | `usePasswordResetForm.js` |
| 34 | F10-2, Section 3.2; frontend-standards.md Sections 4, 6 | An authentication-state update preserves the successful password-change confirmation. | R6, R17 | `F10-2: authentication updates preserve the successful password-change confirmation` (`saving.test.jsx`) | Before fix: an authentication update rechecked the consumed code and replaced success with a link error. | `usePasswordResetForm.js` |

## 3. Work to do

None. All work is done.
