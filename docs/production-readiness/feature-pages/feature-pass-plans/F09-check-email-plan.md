# F09 — Check Email Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F09-check-email-spec.md`  
**Endpoints:** None. The page requests a password-reset email through the Firebase browser SDK.

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1, 4.2 | Non-disclosing confirmation for known and unknown emails | Yes | — |
| R2 | 3.1 | Show the submitted email when available | Yes | — |
| R3 | 3.1 | Inbox, spam, and reset-link instructions | Yes | — |
| R4 | 3.1 | State the 60-minute link expiry | Yes | — |
| R5 | 3.1, 4.1 | Return to Sign In or Forgot Password | Yes | — |
| R6 | 3.2 | Resend through Firebase using the retained email | Yes | — |
| R7 | 3.2; frontend-standards.md Section 9 | Report resend success accessibly | Yes | — |
| R8 | 3.2, 4.2 | Recoverable Firebase and network errors without false success | Yes | — |
| R9 | 5.1 scenario 2; 3.2 | Disable Resend while sending | Yes | — |
| R10 | 4.1 | General guidance and disabled Resend without retained email | Yes | — |
| R11 | 4.2 | Unknown-email resend uses the same success message | Yes | — |
| R12 | 4.2; F10 Section 4.1 | Use the existing Firebase reset-link flow without changing a password | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F09-1` is scenario 1); "Section 4.1" names a spec rule the result also comes from.
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
| 1 | F09-1, Section 3.1 | The page identifies the submitted email. | R2 | `guidance.test.jsx` — F09-1: the page identifies the submitted email | Replaced the displayed email with a different email | `CheckEmailPage.jsx` |
| 2 | F09-1, Section 4.2 | Known and unknown emails receive the same non-disclosing confirmation without asserting that an account exists. | R1 | `guidance.test.jsx` — F09-1: confirmation does not reveal account existence | Removed the conditional account-privacy wording | `CheckEmailPage.jsx` |
| 3 | F09-1, Section 3.1 | The instructions tell the visitor to check inbox and spam. | R3 | `guidance.test.jsx` — F09-1: instructions say to check inbox and spam | Removed the inbox and spam instructions | `CheckEmailPage.jsx` |
| 4 | F09-1, Section 3.1 | The instructions tell the visitor to open the link and reset the password. | R3 | `guidance.test.jsx` — F09-1: instructions say to open the email link and reset the password | Removed the reset-link instructions | `CheckEmailPage.jsx` |
| 5 | F09-1, Section 3.1 | The page states that the link expires in 60 minutes. | R4 | `guidance.test.jsx` — F09-1: instructions state the 60-minute link expiry | Changed the stated expiry to 30 minutes | `CheckEmailPage.jsx` |
| 6 | F09-2, Section 3.2 | Another reset request is made through Firebase using the retained email. | R6 | `resend.test.jsx` — F09-2: resend requests another link from Firebase using the retained email | Sent a different email to Firebase | `authProviderCredentialActions.js` |
| 7 | F09-2, Section 4.2 | The resend request uses the existing Reset Password link-handling route. | R12 | `resend.test.jsx` — F09-2: resend keeps the Reset Password link-handling route | Changed the reset-link destination and disabled in-app handling | `authProviderCredentialActions.js` |
| 8 | F09-2, Section 3.2 | A success message appears after a successful resend and is available to screen readers. | R7 | `resend.test.jsx` — F09-2: successful resend displays an announced success message | Success text appeared without a status announcement | `CheckEmailPage.jsx` (before the fix) |
| 9 | F09-2, Section 3.2 | The action is disabled while sending and becomes available when the request settles. | R9 | `resend.test.jsx` — F09-2: resend stays disabled until the request settles | Enabled Resend while the request was pending | `CheckEmailPage.jsx` |
| 10 | F09-3, F09-4, Sections 3.1, 4.1 | Following Forgot Password opens that page, with or without retained email. | R5, R10 | `navigation.test.jsx` — F09-3, F09-4: Forgot Password opens with or without retained email | Sent the Forgot Password link to Sign In | `CheckEmailPage.jsx` |
| 11 | F09-3, Section 3.1 | Following Back to Sign In opens Sign In. | R5 | `navigation.test.jsx` — F09-3: the Sign In link opens Sign In | Sent both Sign In links to Forgot Password | `CheckEmailPage.jsx` |
| 12 | F09-4, Section 4.1 | A direct visit without a submitted email still shows general guidance. | R10 | `guidance.test.jsx` — F09-4: a direct visit shows general reset guidance | Removed the guidance shown without an email | `CheckEmailPage.jsx` |
| 13 | F09-4, Section 4.1 | Without retained email, Resend is disabled and makes no reset request. | R10 | `resend.test.jsx` — F09-4: no retained email disables resend and makes no Firebase request | Enabled Resend without a retained email | `CheckEmailPage.jsx` |
| 14 | F09-5, Section 4.2 | An unknown-email response during resend shows the same success message as successful dispatch without exposing account existence. | R7, R11 | `resend.test.jsx` — F09-5: unknown-email resend shows the same success without revealing account existence | Showed an error instead of success for an unknown email | `CheckEmailPage.jsx` |
| 15 | F09-6, Section 3.2 | A network failure shows a recoverable error. | R8 | `failure_recovery.test.jsx` — F09-6: a network failure shows a recoverable error | Hid the resend error message | `CheckEmailPage.jsx` |
| 16 | F09-6, Section 3.2 | Another Firebase failure shows a recoverable error. | R8 | `failure_recovery.test.jsx` — F09-6: another Firebase failure shows a recoverable error | Hid the resend error message | `CheckEmailPage.jsx` |
| 17 | F09-6, Section 4.2 | A network failure does not show a false success message, including after an earlier successful resend. | R8 | `failure_recovery.test.jsx` — F09-6: a network failure shows no false success | Showed success after a failed resend | `CheckEmailPage.jsx` |
| 18 | F09-6, Section 4.2 | Another Firebase failure does not show a false success message, including after an earlier successful resend. | R8 | `failure_recovery.test.jsx` — F09-6: another Firebase failure shows no false success | Showed success after a failed resend | `CheckEmailPage.jsx` |
| 19 | F09-6, Section 3.2 | After a Firebase or network failure, the retained email can be retried successfully. | R6, R8 | `failure_recovery.test.jsx` — F09-6: a failed resend can be retried with the retained email | Kept Resend disabled after an error | `CheckEmailPage.jsx` |
| 20 | F09-2, Section 4.2 | Resending requests a link; it does not itself update a password. | R12 | `resend.test.jsx` — F09-2: resending a link does not update a password | Called Firebase password confirmation while resending | `authProviderCredentialActions.js` |

## 3. Work to do

None. All work is done.
