# F11 — Email Verification Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F11-email-verification-spec.md`  
**Endpoints:** Account refresh uses `GET /auth/me` and `POST /auth/sync-user`. The directly connected creation actions are `POST /community-games/publish` and `POST /need-a-sub/posts`; public discovery uses `GET /games/browse` and `GET /need-a-sub/posts/cards`. Returning to Create Game also loads `GET /user-payment-methods` and `GET /host-publish-fees/me`. Firebase sends verification emails and applies verification codes directly from the browser.

## 1. Page requirements

| # | Spec section | Requirement | In the code? | What's missing |
|---|---|---|---|---|
| R1 | 3.1, 4.1 | Connect Firebase email generation to the application's verification route | Yes | — |
| R2 | 3.1 | Refresh the current account's verification state | Yes | — |
| R3 | 3.1 | Show checking, verified, invalid/expired, and not-confirmed outcomes | Yes | — |
| R4 | 3.2, 4.2 | Continue to the originating creation page | Yes | — |
| R5 | 3.2; F14 3.2; F21 4.1 | Preserve entered creation form information through verification | Yes | — |
| R6 | 3.2, 4.2 | Offer send/resend recovery at the originating entry point | Yes | — |
| R7 | 4.1 | Use one account verification state for both creation flows | Yes | — |
| R8 | 4.1; F15 4.10; F20 3.3 | Keep public discovery available without verification | Yes | — |
| R9 | 4.1 | Authorize creation from current Firebase identity, never client verification claims | Yes | — |
| R10 | 4.1 | Verification alone never publishes a game or post | Yes | — |
| R11 | 4.2 | Refuse unusable links unless refreshed account state confirms verification | Yes | — |
| R12 | 4.2 | Distinguish an applied link from confirmed account verification | Yes | — |
| R13 | 3.1, 4.2 | Let verified signed-in players continue without another sign-in | Yes | — |
| R14 | 4.1; scenario 2; F14 4.1; F21 4.1 | Preserve creation eligibility and form rules after verification | Yes | — |
| R15 | 3.1, 4.2; frontend-standards.md Sections 4, 6 | Keep verification results attached to the current link and account | Yes | — |
| R16 | 3.1; frontend-standards.md Section 9 | Announce verification progress and outcomes accessibly | Yes | — |
| R17 | 3.2; frontend-standards.md Sections 7, 8 | Keep return navigation local and preserved form information account-specific | Yes | — |

## 2. Test scenarios

One row per specified case from Sections 3–5 of the page specification.

- **Test #**: the row's number in its table.
- **Scenario**: the page's Section 5 scenario, written as the tests tag it (`F11-1` is scenario 1); "Section 4.1" names a spec rule the result also comes from.
- **Expected result**: the spec's own words for the part this test proves.
- **Requirements**: the Section 1 requirements the test proves.
- **Failure check** and **File broken**: the temporary break that made the test fail, and the file it was made in.

### 2.1 Backend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F11-1, Section 3.1 | Account state refreshes: the account endpoints return and persist the current Firebase verification state, including when the token's older claim is unverified. | R2, R7, R9 | `test_refresh_persists_current_firebase_verification` (`test_account_refresh.py`) | Used the older token verification claim instead of Firebase’s current account record. | `firebase_admin_client.py` |
| 2 | F11-3, Section 4.1 | The backend uses the current verified Firebase identity: an unverified Firebase record clears a stale local verification timestamp despite an older verified token claim. | R2, R9, R11 | `test_current_unverified_record_clears_stale_verification` (`test_account_refresh.py`) | Used the older token verification claim instead of Firebase’s current account record. | `firebase_admin_client.py` |
| 3 | F11-3, Section 4.1 | A client assertion cannot verify an account: supplied verification fields do not override Firebase during account refresh. | R9, R11 | `test_client_verification_assertion_cannot_verify_account` (`test_account_refresh.py`) | Trusted the request’s verification assertion when building the authenticated identity. | `auth_service.py` |
| 4 | F11-8, Section 4.1 | The verification requirement applies when attempting a protected creation action: both creation endpoints refuse an unverified account with 403 and create no game, post, or publishing records. | R9, R11 | `test_unverified_accounts_cannot_create` (`test_creation_gates.py`) | Removed the verified-email requirement; unverified creation requests succeeded. | `auth_service.py` |
| 5 | F11-6, Section 4.1 | The same account verification unlocks both creation flows: one verified account can explicitly publish a valid community game and a valid Sub Post without a second feature verification. | R7, R9 | `test_one_verification_unlocks_both_creation_actions` (`test_creation_gates.py`) | Required another feature verification before creating a Sub Post. | `sub_post_routes.py` |
| 6 | F11-5, Section 4.1 | Unavailable Firebase identity checks cannot grant hosting access: account refresh and both creation actions return 503 without changing the account or creating publishing records. | R9, R12 | `test_unavailable_firebase_cannot_grant_access` (`test_creation_gates.py`) | Granted verified access using a local account when Firebase was unavailable. | `auth_service.py` |
| 7 | F11-1, Section 4.1 | A verification result does not itself publish a game or post: refreshing verified account state creates no game, post, publish attempt, or publish fee. | R10 | `test_verification_refresh_never_publishes` (`test_account_refresh.py`) | Created a valid Sub Post while synchronizing email verification. | `auth_service.py` |
| 8 | F11-2, Section 4.1; F14 4.1; F21 4.1 | Publishing still follows eligibility rules: a verified account that is suspended, pending deletion, or deleted cannot create a game or Sub Post, and rejected requests create no publishing records. | R14 | `test_verification_does_not_override_account_status` (`test_creation_gates.py`) | Bypassed account-status and deletion checks so inactive accounts could create. | `auth_service.py`; `community_game_publish_service.py` |
| 9 | F11-2, Section 4.1; F14 4.1 | Publishing still follows hosting eligibility: verification does not clear a hosting restriction or permit a restricted host to publish a community game. | R14 | `test_verification_preserves_hosting_restriction` (`test_creation_gates.py`) | Allowed restricted hosts to publish community games. | `hosting_access_service.py` |
| 10 | F11-2, Section 4.1; F14 3.1; F21 3.1 | Publishing still follows form rules: a verified account's invalid creation payload is rejected and creates no publishing records. | R14 | `test_verification_does_not_bypass_form_validation` (`test_creation_gates.py`) | Silently replaced invalid zero spot counts with valid counts before validation. | `community_game_publish_schema.py`; `sub_post_schema.py` |
| 11 | F11-8, Section 4.1 | Public games remain available without verification, for signed-out and unverified signed-in visitors. | R8 | `test_public_games_do_not_require_verification` (`test_public_access.py`) | Required verification before returning public game cards. | `game_routes.py` |
| 12 | F11-8, Section 4.1; F20 3.3 | Public Need a Sub summary cards remain available without verification, for signed-out and unverified signed-in visitors. | R8 | `test_public_sub_posts_do_not_require_verification` (`test_public_access.py`) | Required verification before returning public Sub Post cards. | `sub_post_routes.py` |


### 2.2 Frontend tests

| Test # | Scenario | Expected result | Requirements | Test | Failure check | File broken |
|---|---|---|---|---|---|---|
| 1 | F11-1, Section 4.1 | Firebase link generation, the application route, and link handling work as one flow, with the originating creation destination carried through the email request. | R1, R4 | `F11-1: Firebase email settings preserve the originating creation destination (%s)` (`return_and_forms.test.jsx`) | Sent Firebase the wrong continuation URL. | `authProviderVerificationActions.js` |
| 2 | F11-3, Section 3.2 | The originating creation entry offers a way to request another verification email through its send/resend flow, including after a failed request. | R6 | `F11-3: the originating entry supports failure recovery and resend (%s)` (`return_and_forms.test.jsx`) | Prevented resending after the first email request failed. | `useEmailVerification.js` |
| 3 | F11-1, Section 3.1 | A pending verification shows checking feedback. | R3 | `F11-1: a pending verification shows checking feedback` (`link_outcomes.test.jsx`) | Replaced checking feedback with an unrelated heading. | `EmailVerificationAction.jsx` |
| 4 | F11-1, Section 3.1 | Firebase verification is processed through the application route using the code from the verification link. | R1 | `F11-1: the verification route sends its code to Firebase` (`link_outcomes.test.jsx`) | Sent Firebase a different verification code. | `EmailVerificationAction.jsx` |
| 5 | F11-1, Section 3.1 | Account state refreshes after applying the link: Firebase is reloaded, its token is refreshed, and Pickup Lane's current account response updates the application state. | R2, R7 | `F11-1: verification reloads Firebase and updates the current app account` (`link_outcomes.test.jsx`) | Kept the previous application account state after Firebase confirmed verification. | `authProviderVerificationActions.js` |
| 6 | F11-1, Section 3.1 | Confirmed current account verification shows success. | R3 | `F11-1: confirmed current account verification shows success` (`link_outcomes.test.jsx`) | Reported unconfirmed verification after the account was confirmed. | `EmailVerificationAction.jsx` |
| 7 | F11-1, Section 3.1 | A valid verified account can continue without another authentication step. | R13 | `F11-1: a verified signed-in account continues without authentication` (`link_outcomes.test.jsx`) | Sent Continue to Sign In instead of the creation form. | `EmailVerificationAction.jsx` |
| 8 | F11-2, F11-6, Section 3.2 | Continue opens the preserved creation destination, including the Create Sub Post panel rather than unconditionally opening Create Game. | R4 | `F11-2, F11-6: Continue opens the preserved creation destination (%s)` (`return_and_forms.test.jsx`) | Sent Continue to Sign In instead of the preserved creation destination. | `EmailVerificationAction.jsx` |
| 9 | F11-2, F11-6, Section 3.2; F14 3.2; F21 4.1 | Returning from verification preserves entered form information where applicable in each creation flow. | R5 | `F11-2, F11-6: verification preserves entered creation form values (%s)` (`return_and_forms.test.jsx`) | Discarded stored creation values when restoring the form. | `useVerificationFormState.js` |
| 10 | F11-3, Section 4.2 | A missing, invalid, or expired code explains the failure. | R3, R11 | `F11-3: an unusable link explains the failure (%s)` (`link_outcomes.test.jsx`) | Replaced missing and rejected-link explanations with unrelated feedback. | `EmailVerificationAction.jsx` |
| 11 | F11-3, Section 4.2 | An unusable link does not claim verification when refreshed account state is not verified. | R11 | `F11-3: an unusable unverified account never claims success (%s)` (`link_outcomes.test.jsx`) | Claimed success for missing and rejected links on an unverified account. | `EmailVerificationAction.jsx` |
| 12 | F11-3, Section 3.2 | An unavailable link offers a fresh-email path at its originating entry point. | R4, R6 | `F11-3: an unavailable link offers a fresh email at its origin (%s)` (`link_outcomes.test.jsx`) | Removed the fresh-email return action from unavailable outcomes. | `EmailVerificationAction.jsx` |
| 13 | F11-4, Section 4.2 | Refreshed verified account state shows success despite Firebase refusing a reused code. | R2, R11 | `F11-4: refreshed verification permits success for a reused code` (`link_outcomes.test.jsx`) | Rejected reused codes despite refreshed verified account state. | `EmailVerificationAction.jsx` |
| 14 | F11-7, Section 4.2 | An already verified signed-in account opening a used link can continue to the preserved destination without another sign-in. | R4, R13 | `F11-7: an already verified account continues from a used link without signing in (%s)` (`return_and_forms.test.jsx`) | Sent an already verified account to Sign In. | `EmailVerificationAction.jsx` |
| 15 | F11-5, Section 4.2 | A successfully applied link whose current account state cannot be confirmed shows verification not confirmed. | R3, R12 | `F11-5: an applied but unconfirmed link has a distinct outcome (%s)` (`link_outcomes.test.jsx`) | Reported an invalid link instead of the distinct unconfirmed outcome. | `EmailVerificationAction.jsx` |
| 16 | F11-5, Section 4.2 | Failure to confirm current account state does not claim verification or hosting access. | R12 | `F11-5: unconfirmed account state never claims hosting access` (`link_outcomes.test.jsx`) | Claimed success without confirming current account verification. | `EmailVerificationAction.jsx` |
| 17 | F11-5, Section 4.2 | Verification not confirmed offers a retry or fresh-email path at the originating entry. | R4, R6, R12 | `F11-5: unconfirmed verification offers a fresh email at its origin (%s)` (`link_outcomes.test.jsx`) | Removed the fresh-email return action from unconfirmed outcomes. | `EmailVerificationAction.jsx` |
| 18 | F11-6, Section 4.1 | The same account verification unlocks both creation flows without a second verification prompt for the other feature. | R7 | `F11-6: account verification unlocks both creation forms without a second verification` (`return_and_forms.test.jsx`) | Kept Create Game blocked after the shared account was verified. | `CreateGamePage.jsx` |
| 19 | F11-1, F11-6, Section 4.1 | Verification and returning to an entered form do not themselves publish a game or post. | R10 | `F11-1, F11-6: verification and return never publish automatically (%s)` (`return_and_forms.test.jsx`) | Sent a publishing request when verification succeeded. | `EmailVerificationAction.jsx` |
| 20 | F11-8, Section 4.1; F15 4.10 | Public game discovery remains available to signed-out and unverified signed-in visitors. | R8 | `F11-8: public game browsing does not require verification (signed in: %s)` (`public_access.test.jsx`) | Hid the public game cards while keeping the page heading visible. | `BrowseGamesPage.jsx` |
| 21 | F11-8, Section 4.1; F20 3.3 | An unverified signed-in account can browse public Need a Sub summary cards. | R8 | `F11-8: unverified signed-in accounts can browse public Sub Post cards` (`public_access.test.jsx`) | Replaced unverified accounts’ public Sub Post list with a verification blocker. | `NeedASubPage.jsx` |
| 22 | F11-8, Section 4.1; F20 3.3 | A signed-out visitor can browse public Need a Sub summary cards without verification. | R8 | `F11-8: signed-out visitors can browse public Sub Post cards` (`public_access.test.jsx`) | Sent signed-out visitors to the creation gate instead of showing public cards. | `NeedASubPage.jsx` |
| 23 | F11-1, Section 3.1; frontend-standards.md Sections 4, 6 | A new verification link checks its own code and ignores replies from an earlier link. | R15 | `F11-1: a new link ignores replies from the preceding link (%s)` (`link_changes.test.jsx`) | Reused the previous verification component and code result for another link. | `ResetPasswordPage.jsx` |
| 24 | F11-3, Section 4.2; frontend-standards.md Sections 4, 6 | Removing the current link's code shows the missing-link outcome instead of a previous checking or verified outcome. | R3, R11, R15 | `F11-3: removing the code replaces the preceding link result (%s)` (`link_changes.test.jsx`) | Kept the previous verification state when the URL code was removed. | `ResetPasswordPage.jsx` |
| 25 | F11-1, F11-7, Sections 3.1, 4.2; frontend-standards.md Sections 4, 6 | Updating authentication state for the same link preserves its pending work or confirmed success without repeatedly applying its code. | R13, R15 | `F11-1, F11-7: authentication updates preserve the same verification operation (%s)` (`link_changes.test.jsx`) | Remounted verification when authentication loading changed, applying the code again. | `ResetPasswordPage.jsx` |
| 26 | F11-1, F11-3, F11-5, Section 3.1; frontend-standards.md Section 9 | Checking and verification outcomes are available to screen readers. | R16 | `F11-1, F11-3, F11-5: verification feedback is announced (%s)` (`link_outcomes.test.jsx`) | Removed the status announcement from verification feedback. | `EmailVerificationAction.jsx` |
| 27 | F11-6, Section 3.2; frontend-standards.md Section 8 | Returning to a creation form does not restore another account's entered information. | R5, R17 | `F11-6: verification never restores another account form (%s)` (`return_and_forms.test.jsx`) | Shared stored form information between accounts and removed the account-owner check. | `useVerificationFormState.js` |
| 28 | F11-2, F11-6, Section 3.2; frontend-standards.md Section 8 | Verification return information cannot send the visitor to an external or unintended route. | R4, R17 | `F11-2, F11-6: unsafe or unsupported returns use the existing creation entry (%s)` (`return_and_forms.test.jsx`) | Accepted untrusted return values and used them directly as return links. | `emailVerificationReturn.js` |
| 29 | F11-1, Section 3.1; frontend-standards.md Sections 4, 6 | Restoring the signed-in account before processing a link applies its code once, without starting an earlier signed-out operation. | R13, R15 | `F11-1: restoring sign-in applies the verification code once` (`link_changes.test.jsx`) | Started applying the code before Firebase restored the signed-in account (before the fix). | `EmailVerificationAction.jsx` |
| 30 | F11-3, Section 3.2; frontend-standards.md Sections 4, 6 | Changing accounts clears the previous account's email-send result and restores only the new account's cooldown. | R6, R15, R17 | `F11-3: changing accounts clears the previous send feedback (%s)` (`account_changes.test.jsx`) | Kept the previous account's sent/error feedback after changing accounts (before the fix). | `useEmailVerification.js` |
| 31 | F11-3, Section 3.2; frontend-standards.md Sections 4, 6 | A previous account's pending email request cannot replace the current account's send result or disable its send action. | R6, R15, R17 | `F11-3: an earlier account request cannot replace the current send (%s)` (`account_changes.test.jsx`) | Allowed the previous account's email reply to update the current account's screen. | `useEmailVerification.js` |


## 3. Work to do

None. All work is done.
