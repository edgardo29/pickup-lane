# F08 — Forgot Password Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F08-forgot-password-spec.md`  
**Endpoints:** None. The page requests an authentication email through the Firebase browser SDK.

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1 | Submitting a valid email requests a reset link | Yes | — |
| R2 | 3.1 | An accepted request opens Check Email with the normalized submitted email | Yes | — |
| R3 | 3.1 | Back opens Sign In without changing a password | Yes | — |
| R4 | 4.1 | Known and unknown accounts receive the same non-disclosing confirmation | Yes | — |
| R5 | 4.1 | Firebase owns email dispatch; requesting a link does not itself update a password | Yes | — |
| R6 | 4.1 | The reset request uses the existing Reset Password link-handling route | Yes | — |
| R7 | 4.2 | Blank and malformed email receive inline validation before any reset request | Yes | — |
| R8 | 4.2 | Other Firebase and network failures stay on Forgot Password with error feedback and no false success | Yes | — |
| R9 | 4.2 | A failed request can be retried | Yes | — |
| R10 | 4.2 | Send is disabled while a request is pending | Yes | — |
| R11 | 4.2; frontend-standards.md Section 9 | Email validity is distinguished from service availability | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F08-1` is scenario 1); "Section 4.1" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|

No backend cases: the page calls Firebase directly and makes no Pickup Lane API request.

### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F08-1, Section 3.1, Section 4.1 | The app asks Firebase to send the password-reset email. | R1, R5 | `F08-1: submitting a valid email requests a reset through Firebase` | Skipped the Firebase reset-email call | `authProviderCredentialActions.js` |
| 2 | F08-1, Section 3.1 | Check Email opens with the normalized email. | R2 | `F08-1: an accepted request opens Check Email with normalized email` | Kept uppercase letters in the Check Email destination state | `ForgotPasswordPage.jsx` |
| 3 | F08-1, Section 4.1 | Check Email shows a non-disclosing confirmation for a known email. | R4 | `F08-1: an accepted request shows the non-disclosing confirmation` | Asserted that an account exists in the confirmation | `CheckEmailPage.jsx` |
| 4 | F08-2, Section 4.1 | Check Email opens with the same non-disclosing confirmation; account existence is not revealed. | R4 | `F08-2: an unknown account follows the same non-disclosing confirmation route` | Treated an unknown account as an error instead of confirming | `ForgotPasswordPage.jsx` |
| 5 | F08-3, Section 3.1 | Sign In opens without changing a password. | R3 | `F08-3: Back opens Sign In without requesting or changing a password` | Back stayed on Forgot Password instead of opening Sign In | `ForgotPasswordPage.jsx` |
| 6 | F08-1, Section 4.1 | This page does not reset the password itself when requesting a link. | R5 | `F08-1: requesting an email never updates the password` | Updated the password while requesting a reset email | `authProviderCredentialActions.js` |
| 7 | F08-1, Section 4.1 | The reset email request uses the Reset Password link-handling route. | R6 | `F08-1: the reset email uses the application Reset Password route` | Pointed the reset request at Sign In instead of Reset Password | `authProviderCredentialActions.js` |
| 8 | F08-4, Section 4.2 | Inline validation appears for a blank email. | R7 | `F08-4: a blank email shows associated inline validation` | Removed the inline invalid-email error | `ForgotPasswordPage.jsx` |
| 9 | F08-4, Section 4.2 | No reset request is sent for a blank email. | R7 | `F08-4: a blank email sends no reset request` | Allowed invalid email to reach Firebase | `ForgotPasswordPage.jsx` |
| 10 | F08-4, Section 4.2 | Inline validation appears for a malformed email. | R7 | `F08-4: a malformed email shows associated inline validation` | Removed the inline invalid-email error | `ForgotPasswordPage.jsx` |
| 11 | F08-4, Section 4.2 | No reset request is sent for a malformed email. | R7 | `F08-4: a malformed email sends no reset request` | Allowed invalid email to reach Firebase | `ForgotPasswordPage.jsx` |
| 12 | F08-5, Section 4.2 | A network error remains on this page with retry feedback. | R8 | `F08-5: a network failure shows recoverable feedback on Forgot Password` | Suppressed reset-request failure feedback | `ForgotPasswordPage.jsx` |
| 13 | F08-5, Section 4.2 | A non-account-related Firebase error remains on this page with retry feedback. | R8 | `F08-5: a Firebase failure shows recoverable feedback on Forgot Password` | Suppressed reset-request failure feedback | `ForgotPasswordPage.jsx` |
| 14 | F08-5, Section 4.2 | After a network error, the page does not claim an email was sent. | R8 | `F08-5: a network failure never claims reset-email success` | Opened reset-email confirmation after a failed request | `ForgotPasswordPage.jsx` |
| 15 | F08-5, Section 4.2 | After a non-account-related Firebase error, the page does not claim an email was sent. | R8 | `F08-5: a Firebase failure never claims reset-email success` | Opened reset-email confirmation after a failed request | `ForgotPasswordPage.jsx` |
| 16 | F08-5, Section 4.2 | After a network error, the request can be retried. | R9 | `F08-5: after a network failure the retained email can be retried successfully` | Left Send disabled after a failed request | `ForgotPasswordPage.jsx` |
| 17 | F08-5, Section 4.2 | After a non-account-related Firebase error, the request can be retried. | R9 | `F08-5: after a Firebase failure the retained email can be retried successfully` | Left Send disabled after a failed request | `ForgotPasswordPage.jsx` |
| 18 | F08-6, Section 4.2 | The send control remains disabled until the request settles. | R10 | `F08-6: a pending request disables duplicate submission until it settles` | Enabled Send while the reset request was pending | `ForgotPasswordPage.jsx` |
| 19 | F08-3, Section 3.1 | Sign In remains open after Back when the pending reset request succeeds. | R3 | `F08-3: Back stays on Sign In when the pending request succeeds` | Caught Firebase success reopening Check Email after Back; passed after the fix | `ForgotPasswordPage.jsx` |
| 20 | F08-3, Section 3.1, Section 4.1 | Sign In remains open after Back when the pending request reports an unknown account. | R3 | `F08-3: Back stays on Sign In when the pending request reports an unknown account` | Caught Firebase reporting an unknown account reopening Check Email after Back; passed after the fix | `ForgotPasswordPage.jsx` |
| 21 | F08-5, Section 4.2 | A network failure does not mark a valid email as invalid. | R11 | `F08-5: a network failure does not mark the valid email invalid` | Caught a network error marking a valid email as invalid; passed after the fix | `ForgotPasswordPage.jsx` |
| 22 | F08-5, Section 4.2 | A non-account-related Firebase failure does not mark a valid email as invalid. | R11 | `F08-5: a Firebase failure does not mark the valid email invalid` | Caught a Firebase error marking a valid email as invalid; passed after the fix | `ForgotPasswordPage.jsx` |

## 3. Work to do

None. All work is done.
