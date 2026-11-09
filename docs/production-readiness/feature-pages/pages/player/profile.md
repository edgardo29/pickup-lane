# F12 — Profile and Settings

## 1. Existing Route(s)

- `/profile`
- `/profile/edit` opens this page with the edit modal visible.

`/settings` redirects to `/profile`; settings content is on this page.

## 2. Purpose

Profile lets a signed-in player review their account summary and manage profile details, notification preferences, account access, and account deletion from one page.

## 3. Main Functionality

### 3.1. Review and Edit the Profile

- Show name, location summary, member-since information, game credit balance, and activity stats.
- **Edit Profile** opens a modal to update first and last name, phone, and home city/state. Saving updates the overview without leaving Profile.

### 3.2. Manage Preferences and Access

- The Manage area opens notification email preference, [Payment Methods](payment-methods.md), eligible Google-account password setup, Terms, Privacy, and Log Out. Help & Support is currently an informational row.
- Password setup asks for a valid matching password and recent account confirmation. Log Out returns to Landing.
- Delete Account is a separate danger action. It requires typing `delete` and recent account confirmation before the account is deleted and the user is signed out.

## 4. Important Behavior & Decisions

### 4.1. Account Ownership and Defaults

Profile reads and changes only the authenticated user's account. Missing optional settings, stats, credits, or cards do not prevent the main profile from loading; they show their empty or zero state. A failure to load the user profile shows a page error.

### 4.2. Edit and Settings Boundaries

The edit modal may open in place or from `/profile/edit`; closing the direct-link modal returns to `/profile`. The modal does not offer a date-of-birth field, but any date-of-birth update through the authenticated profile path must enforce the [minimum account age of 18](../authentication/finish-profile.md#42-validation-and-recovery) in the backend and return clear validation feedback for underage input. Payment card management belongs to [Payment Methods](payment-methods.md), while account creation and recovery belong to the Authentication specifications. Terms and Privacy modals use the corresponding public policy content.

Profile edits may save account details and location preferences separately. The page reports complete success only after every requested change succeeds. If one save succeeds and another fails, it identifies the saved and unsaved changes, retains entered data, and lets the player retry only the failed operation without repeating successful updates.

### 4.3. Sensitive Actions

Only an eligible Google account without a password sees Add Password. Password linking and account deletion require account confirmation. Failed saves or account actions show feedback and do not claim success.

### 4.4. Account Deletion Consequences

Deleting the account removes the sign-in identity and personal details, detaches saved cards, and cancels the user's future bookings, guests, waitlist entries, hosted community games, and Need a Sub posts and requests. Released spots go to waitlisted players when available. Deletion itself issues no refund or game credit for cancelled bookings. The full cleanup is described in [User Detail](../admin/user-detail.md#46-account-deletion).

Self-service deletion differs from admin deletion:

- The last active admin cannot delete their own account; deletion is rejected and the account remains.
- A user assigned to host a future official game can still delete their account. The assignment is cleared and the game stays scheduled without a host. Admin deletion of that user is blocked until the assignment is removed.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Profile as a signed-in player. | The overview, credits, stats, Manage rows, and separate Delete Account action load for that account. |
| 2 | ☐ | Open Edit Profile from `/profile` and directly at `/profile/edit`. | The same modal appears over Profile; closing the direct-link view returns to `/profile`. |
| 3 | ☐ | Save valid profile details. | The modal closes, the overview reflects saved details, and the changes persist after reload. |
| 4 | ☐ | Change email-notification preference. | The saved preference updates the Manage summary and persists after reload. |
| 5 | ☐ | Open payment methods or a legal policy. | Payment Methods opens its own page; Terms and Privacy open their shared policy content in modals. |
| 6 | ☐ | Add a password from an eligible Google-only account. | Matching valid passwords and account confirmation allow linking; the page shows success. |
| 7 | ☐ | Log out or complete account deletion. | Log Out returns to Landing; deletion requires its confirmation and then signs the user out. |
| 8 | ☐ | Delete an account that has a future booking with a guest, a waitlist entry, and a Need a Sub post. | The booking and guest spots are released, the waitlist entry and post are cancelled, and the user is signed out. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 9 | ☐ | Open `/settings` or Profile while signed out. | The alias redirects to Profile; private access redirects the signed-out visitor to Sign In. |
| 10 | ☐ | Load a profile with absent optional settings, stats, credits, or cards. | Profile still renders with default/empty values rather than failing or showing stale data. |
| 11 | ☐ | Fail the main profile load or a preference/profile save. | Load failure shows a page error; save failure keeps the edit surface available with feedback. |
| 12 | ☐ | Submit missing required profile fields or an invalid password pair. | Validation blocks the change and shows the relevant field or password error. |
| 13 | ☐ | Try Add Password from an ineligible account, or fail account confirmation. | The option is absent when ineligible; a failed confirmation does not link a password. |
| 14 | ☐ | Attempt deletion without `delete`, cancel it, or fail account confirmation. | The account remains; the page does not show deletion success. |
| 15 | ☐ | Delete your own account as the last active admin. | Deletion is rejected, the account remains, and the page does not show deletion success. |
| 16 | ☐ | Delete your own account while assigned to host a future official game. | The account is deleted and the game stays scheduled with no host assigned. |
| 17 | ☐ | Submit a date-of-birth update directly through the authenticated profile path for an underage user, then for an exactly 18-year-old user. | The backend rejects the underage update with clear validation feedback and preserves the existing birthday; it accepts the age-eligible date. The edit modal gains no new birthday field. |
| 18 | ☐ | Save profile details and location preferences when one save succeeds and the other fails. | The page names which changes were saved and which were not, keeps all entered values, does not claim complete success, and retries only the failed save without repeating successful updates. |

## 6. Open Items to Resolve

**None**.
