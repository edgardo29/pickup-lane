# F06 — Finish Profile

## 1. Existing Route(s)

- `/finish-profile`

## 2. Purpose

Finish Profile collects the remaining personal details required to complete a new or incomplete Pickup Lane account before the player continues into product actions.

## 3. Main Functionality

### 3.1. Provide Profile Details

The visitor enters first name, last name, and birthday. Existing provider name or saved profile values can prefill the form. The page explains the minimum age of 18.

### 3.2. Complete or Leave Signup

On valid submission, the account is created or synchronized as needed, profile details are saved, and the user continues to the original destination preserved through authentication when it remains available, or to game discovery when it does not. Back returns to Create Account; for an unfinished provider signup, it attempts to clean up the incomplete identity first.

## 4. Important Behavior & Decisions

### 4.1. Account Creation Boundary

Email/password signup creates the identity and app account only after valid profile submission. Google has already created a provider identity and may need incomplete-account cleanup if the user abandons the flow. The app profile update applies to the authenticated account.

### 4.2. Validation and Recovery

First and last names are required. Birthday must be a real date, not in the future, and meet the minimum account age of 18. Both the form and backend enforce this during registration and profile completion; direct underage requests receive clear validation feedback. The same age rule applies to later date-of-birth updates under [Profile](../player/profile.md#42-edit-and-settings-boundaries). A visitor without an active signup or signed-in identity returns to Create Account. A failed save leaves the form available with an error; a failed cleanup prevents Back from silently abandoning an incomplete account.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Finish a valid email/password signup. | The identity and app account are created once, profile details are saved, and the user continues to the preserved destination when available or game discovery otherwise. |
| 2 | ☐ | Finish a new Google signup. | The signed-in identity gains an app profile with the submitted details and continues to the destination. |
| 3 | ☐ | Open with an existing partial profile or provider display name. | Available name and birthday values prefill the fields without inventing missing values. |
| 4 | ☐ | Use Back during an email signup or unfinished Google signup. | Email signup returns to Create Account without creating an identity; unfinished Google signup attempts cleanup before returning. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 5 | ☐ | Submit missing names, missing/invalid birthday, a future birthday, or an age below 18. | The relevant field error appears and profile completion does not proceed; a direct underage profile-completion request is also rejected by the backend. |
| 6 | ☐ | Submit on the exact 18th birthday. | The age boundary is accepted by the form and backend. |
| 7 | ☐ | Open Finish Profile without a pending signup or signed-in identity. | The visitor returns to Create Account. |
| 8 | ☐ | Fail account creation, profile save, or unfinished-account cleanup. | An error is shown; the page does not claim completion or silently discard the unfinished provider account. |
| 9 | ☐ | Submit repeatedly while saving. | The form is disabled during the pending save and does not create duplicate profiles. |
| 10 | ☐ | Complete a previously incomplete profile after sign-in from a specific game or post. | The original destination survives both sign-in and profile completion; product access begins only after completion. |

## 6. Open Items to Resolve

**None**.
