# F05 — Create Account

## 1. Existing Route(s)

- `/create-account`

## 2. Purpose

Create Account starts a player account with email/password or Google and sends new users to [Finish Profile](finish-profile.md).

## 3. Main Functionality

### 3.1. Start with Email

The visitor enters an email and password. The page checks email availability and the password rules, then advances to Finish Profile. It does not create an email/password identity at this first step.

### 3.2. Continue with Google

Google authentication can return an existing complete user to the requested destination or send a new/incomplete user to Finish Profile with that destination retained until completion.

### 3.3. Review Account Terms

The page links to Sign In and opens the current Terms of Service and Privacy Policy in dismissible modals. Policy content is owned by the corresponding public page specifications.

## 4. Important Behavior & Decisions

### 4.1. Deferred Email Account Creation

The email and password are held only during the active signup flow. The identity and app account are created when a valid, age-eligible profile is submitted on [Finish Profile](finish-profile.md). The minimum age is 18 and must be checked by the frontend and backend during registration. Abandoning this first step creates no account.

### 4.2. Existing Accounts and Failures

An already-used email gets clear feedback; an email-availability failure leaves the visitor on this page to retry. Google sign-in creates or accesses an identity before profile completion, so unfinished Google signup follows the cleanup behavior described in [Finish Profile](finish-profile.md).

### 4.3. Signed-In Access

An already signed-in app user is redirected away from Create Account. Authentication return context is retained when switching between Create Account and Sign In.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Enter an available email and valid password. | Finish Profile opens with the return context; no email/password identity or app account has yet been created, and registration cannot complete without an age-eligible profile. |
| 2 | ☐ | Complete Google sign-in with an existing complete account. | The user proceeds to the saved destination or game discovery. |
| 3 | ☐ | Complete Google sign-in with a new or incomplete account. | Finish Profile opens for the remaining details and preserves the requested destination. |
| 4 | ☐ | Open Terms, Privacy, and Sign In. | The selected policy appears in a dismissible modal; Sign In receives the return context. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 5 | ☐ | Submit an invalid email, blank password, or password shorter than eight characters without a number or symbol. | The page gives the relevant validation message and does not advance. |
| 6 | ☐ | Submit an email already in use. | The page explains that an account exists and does not start another account. |
| 7 | ☐ | Fail email availability or cancel Google sign-in. | A recoverable error appears; no success or unintended transition is shown. |
| 8 | ☐ | Refresh or leave before submitting Finish Profile after the email step. | The pending email/password does not create an identity or app account. |
| 9 | ☐ | Open Create Account while already signed in. | The user is redirected to the supplied destination or game discovery. |

## 6. Open Items to Resolve

**None**.
