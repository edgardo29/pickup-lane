# Pickup Lane Page Inventory

This is the single index for Pickup Lane's 54 finalized page specifications.
Each row links to one distinct page experience, including views reached by an
in-page action or direct link. Redirects and aliases are listed below without
creating extra specifications. The page specifications define intended
functionality; their test scenarios are for future verification.

F01–F54 identify the feature passes and give a preferred work order. An earlier
ID is not automatically a prerequisite for a later pass.

## Public

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F01 | Landing | `/` | [pages/player-facing/F01-landing-spec.md](pages/player-facing/F01-landing-spec.md) |
| F15 | Browse Games | `/games/browse` | [pages/player-facing/F15-browse-games-spec.md](pages/player-facing/F15-browse-games-spec.md) |
| F16 | Game Details | `/games/:gameId` | [pages/player-facing/F16-game-details-spec.md](pages/player-facing/F16-game-details-spec.md) |
| F20 | Need a Sub browse | `/need-a-sub` (browse view) | [pages/player-facing/F20-need-a-sub-spec.md](pages/player-facing/F20-need-a-sub-spec.md) |
| F22 | Need a Sub Post Detail | `/need-a-sub/posts/:postId` | [pages/player-facing/F22-need-a-sub-post-detail-spec.md](pages/player-facing/F22-need-a-sub-post-detail-spec.md) |
| F02 | Terms of Service | `/terms` | [pages/player-facing/F02-terms-of-service-spec.md](pages/player-facing/F02-terms-of-service-spec.md) |
| F03 | Privacy Policy | `/privacy` | [pages/player-facing/F03-privacy-policy-spec.md](pages/player-facing/F03-privacy-policy-spec.md) |
| F04 | Cancellation & Refunds Policy | `/policies/cancellation-refunds` | [pages/player-facing/F04-cancellation-refunds-policy-spec.md](pages/player-facing/F04-cancellation-refunds-policy-spec.md) |

## Authentication

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F07 | Sign In | `/sign-in` | [pages/player-facing/F07-sign-in-spec.md](pages/player-facing/F07-sign-in-spec.md) |
| F05 | Create Account | `/create-account` | [pages/player-facing/F05-create-account-spec.md](pages/player-facing/F05-create-account-spec.md) |
| F06 | Finish Profile | `/finish-profile` | [pages/player-facing/F06-finish-profile-spec.md](pages/player-facing/F06-finish-profile-spec.md) |
| F08 | Forgot Password | `/forgot-password` | [pages/player-facing/F08-forgot-password-spec.md](pages/player-facing/F08-forgot-password-spec.md) |
| F09 | Check Email | `/check-email` | [pages/player-facing/F09-check-email-spec.md](pages/player-facing/F09-check-email-spec.md) |
| F10 | Reset Password | `/reset-password` (password reset mode) | [pages/player-facing/F10-reset-password-spec.md](pages/player-facing/F10-reset-password-spec.md) |
| F11 | Email Verification | `/reset-password?mode=verifyEmail` | [pages/player-facing/F11-email-verification-spec.md](pages/player-facing/F11-email-verification-spec.md) |
| F26 | Admin Sign In | `/admin/sign-in` | [pages/admin/F26-admin-sign-in-spec.md](pages/admin/F26-admin-sign-in-spec.md) |

## Player

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F17 | Game Checkout | `/games/:gameId/checkout` | [pages/player-facing/F17-game-checkout-spec.md](pages/player-facing/F17-game-checkout-spec.md) |
| F19 | My Games | `/my-games` | [pages/player-facing/F19-my-games-spec.md](pages/player-facing/F19-my-games-spec.md) |
| F25 | Inbox | `/inbox` | [pages/player-facing/F25-inbox-spec.md](pages/player-facing/F25-inbox-spec.md) |
| F12 | Profile and settings | `/profile`, `/profile/edit`; `/settings` redirects here | [pages/player-facing/F12-profile-spec.md](pages/player-facing/F12-profile-spec.md) |
| F13 | Payment Methods | `/profile/payment-methods`, `/settings/payment-methods` | [pages/player-facing/F13-payment-methods-spec.md](pages/player-facing/F13-payment-methods-spec.md) |

## Hosting

Hosting uses signed-in player routes; there is no separate organizer area.

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F14 | Create Game | `/create-game` | [pages/player-facing/F14-create-game-spec.md](pages/player-facing/F14-create-game-spec.md) |
| F18 | Edit Game | `/games/:gameId/edit` | [pages/player-facing/F18-edit-game-spec.md](pages/player-facing/F18-edit-game-spec.md) |
| F21 | Create Sub Post | `/need-a-sub` (create panel) | [pages/player-facing/F21-create-sub-post-spec.md](pages/player-facing/F21-create-sub-post-spec.md) |
| F24 | Edit Sub Post | `/need-a-sub/posts/:postId/edit` | [pages/player-facing/F24-edit-sub-post-spec.md](pages/player-facing/F24-edit-sub-post-spec.md) |
| F23 | Sub Post Published | `/need-a-sub/posts/:postId/published` | [pages/player-facing/F23-sub-post-published-spec.md](pages/player-facing/F23-sub-post-published-spec.md) |

## Admin Workspace

These routes require admin access; the sign-in page is listed under
Authentication.

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F37 | Review Cases | `/admin/review-cases` | [pages/admin/F37-review-cases-spec.md](pages/admin/F37-review-cases-spec.md) |
| F38 | Review Case Detail | `/admin/review-cases/:reviewCaseId` | [pages/admin/F38-review-case-detail-spec.md](pages/admin/F38-review-case-detail-spec.md) |
| F39 | User Directory | `/admin/users` | [pages/admin/F39-user-directory-spec.md](pages/admin/F39-user-directory-spec.md) |
| F40 | User Detail | `/admin/users/:userId` | [pages/admin/F40-user-detail-spec.md](pages/admin/F40-user-detail-spec.md) |
| F41 | User Game Activity | `/admin/users/:userId/game-activity` | [pages/admin/F41-user-game-activity-spec.md](pages/admin/F41-user-game-activity-spec.md) |
| F42 | User Need a Sub Activity | `/admin/users/:userId/need-a-sub-activity` | [pages/admin/F42-user-need-a-sub-activity-spec.md](pages/admin/F42-user-need-a-sub-activity-spec.md) |
| F32 | Community Games | `/admin/community-games` | [pages/admin/F32-community-games-spec.md](pages/admin/F32-community-games-spec.md) |
| F33 | Community Game Detail | `/admin/community-games/:gameId` | [pages/admin/F33-community-game-detail-spec.md](pages/admin/F33-community-game-detail-spec.md) |
| F34 | Need a Sub (Admin) | `/admin/need-a-sub` | [pages/admin/F34-need-a-sub-posts-spec.md](pages/admin/F34-need-a-sub-posts-spec.md) |
| F35 | Need a Sub Post (Admin) | `/admin/need-a-sub/:postId` | [pages/admin/F35-need-a-sub-post-detail-spec.md](pages/admin/F35-need-a-sub-post-detail-spec.md) |
| F36 | Need a Sub Request (Admin) | `/admin/need-a-sub/requests/:requestId` | [pages/admin/F36-need-a-sub-request-detail-spec.md](pages/admin/F36-need-a-sub-request-detail-spec.md) |
| F28 | Official Games | `/admin/official-games` | [pages/admin/F28-official-games-spec.md](pages/admin/F28-official-games-spec.md) |
| F29 | Create Official Game | `/admin/official-games/new` | [pages/admin/F29-create-official-game-spec.md](pages/admin/F29-create-official-game-spec.md) |
| F30 | Official Game Manage | `/admin/official-games/:gameId` | [pages/admin/F30-official-game-manage-spec.md](pages/admin/F30-official-game-manage-spec.md) |
| F31 | Edit Official Game | `/admin/official-games/:gameId/edit` | [pages/admin/F31-edit-official-game-spec.md](pages/admin/F31-edit-official-game-spec.md) |
| F50 | Money Issues | `/admin/money/issues` | [pages/admin/F50-money-issues-spec.md](pages/admin/F50-money-issues-spec.md) |
| F51 | Money Issue Detail | `/admin/money/issues/:moneyIssueId` | [pages/admin/F51-money-issue-detail-spec.md](pages/admin/F51-money-issue-detail-spec.md) |
| F43 | User Money | `/admin/money/users`, `/admin/money/users/:userId` | [pages/admin/F43-user-money-spec.md](pages/admin/F43-user-money-spec.md) |
| F44 | Payments | `/admin/money/payments` | [pages/admin/F44-payments-spec.md](pages/admin/F44-payments-spec.md) |
| F45 | Payment Detail | `/admin/money/payments/:paymentId` | [pages/admin/F45-payment-detail-spec.md](pages/admin/F45-payment-detail-spec.md) |
| F46 | Refunds | `/admin/money/refunds` | [pages/admin/F46-refunds-spec.md](pages/admin/F46-refunds-spec.md) |
| F47 | Refund Detail | `/admin/money/refunds/:refundId` | [pages/admin/F47-refund-detail-spec.md](pages/admin/F47-refund-detail-spec.md) |
| F48 | Credits | `/admin/money/credits` | [pages/admin/F48-credits-spec.md](pages/admin/F48-credits-spec.md) |
| F49 | Credit Detail | `/admin/money/credits/:creditId` | [pages/admin/F49-credit-detail-spec.md](pages/admin/F49-credit-detail-spec.md) |
| F52 | Financial Outcome Detail | `/admin/money/financial-outcomes/:financialOutcomeId` | [pages/admin/F52-financial-outcome-detail-spec.md](pages/admin/F52-financial-outcome-detail-spec.md) |
| F53 | Notification Lookup | `/admin/notifications`, `/admin/notifications/:notificationId` | [pages/admin/F53-notification-lookup-spec.md](pages/admin/F53-notification-lookup-spec.md) |
| F27 | Admin Action Log | `/admin/audit` | [pages/admin/F27-admin-action-log-spec.md](pages/admin/F27-admin-action-log-spec.md) |
| F54 | Platform Notices | `/admin/platform-notices`, `/admin/platform-notices/new`, `/admin/platform-notices/:noticeId` | [pages/admin/F54-platform-notices-spec.md](pages/admin/F54-platform-notices-spec.md) |

## Redirects, Aliases, and Shared Routes

These routes do not require an additional specification by themselves.

| Route or view | Relationship |
|---|---|
| `/games` | Redirects to Browse Games at `/games/browse`. |
| `/player-hub` | Redirects to Need a Sub at `/need-a-sub`. |
| `/need-a-sub/posts/:postId/manage` | Redirects to Need a Sub Post Detail. |
| `/settings` | Redirects to Profile, where settings content is shown. |
| `/profile/edit` | Opens Profile with its edit modal visible. |
| `/settings/payment-methods` | Renders the same Payment Methods page as `/profile/payment-methods`. |
| `/admin` | Redirects to the first available admin workspace page. |
| `/admin/staff` | Redirects to `/admin/users?role=admin`, a filtered User Directory. |
| `/need-a-sub` | Hosts both the browse view and the Create Sub Post panel. |
| `/reset-password` | Uses the `mode` query parameter for password reset or email verification. |
| `/create-game`, `/games/:gameId/edit` | Render the same community game form in create and edit modes. |

`NeedASubManagePage.jsx` is not routed or imported. Its former manage route
redirects to Post Detail, so it is not a separate accessible page experience.
