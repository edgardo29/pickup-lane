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
| F01 | Landing | `/` | [pages/public/landing.md](pages/public/landing.md) |
| F15 | Browse Games | `/games/browse` | [pages/public/browse-games.md](pages/public/browse-games.md) |
| F16 | Game Details | `/games/:gameId` | [pages/public/game-details.md](pages/public/game-details.md) |
| F20 | Need a Sub browse | `/need-a-sub` (browse view) | [pages/public/need-a-sub.md](pages/public/need-a-sub.md) |
| F22 | Need a Sub Post Detail | `/need-a-sub/posts/:postId` | [pages/public/need-a-sub-post-detail.md](pages/public/need-a-sub-post-detail.md) |
| F02 | Terms of Service | `/terms` | [pages/public/terms-of-service.md](pages/public/terms-of-service.md) |
| F03 | Privacy Policy | `/privacy` | [pages/public/privacy-policy.md](pages/public/privacy-policy.md) |
| F04 | Cancellation & Refunds Policy | `/policies/cancellation-refunds` | [pages/public/cancellation-refunds-policy.md](pages/public/cancellation-refunds-policy.md) |

## Authentication

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F07 | Sign In | `/sign-in` | [pages/authentication/sign-in.md](pages/authentication/sign-in.md) |
| F05 | Create Account | `/create-account` | [pages/authentication/create-account.md](pages/authentication/create-account.md) |
| F06 | Finish Profile | `/finish-profile` | [pages/authentication/finish-profile.md](pages/authentication/finish-profile.md) |
| F08 | Forgot Password | `/forgot-password` | [pages/authentication/forgot-password.md](pages/authentication/forgot-password.md) |
| F09 | Check Email | `/check-email` | [pages/authentication/check-email.md](pages/authentication/check-email.md) |
| F10 | Reset Password | `/reset-password` (password reset mode) | [pages/authentication/reset-password.md](pages/authentication/reset-password.md) |
| F11 | Email Verification | `/reset-password?mode=verifyEmail` | [pages/authentication/email-verification.md](pages/authentication/email-verification.md) |
| F26 | Admin Sign In | `/admin/sign-in` | [pages/authentication/admin-sign-in.md](pages/authentication/admin-sign-in.md) |

## Player

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F17 | Game Checkout | `/games/:gameId/checkout` | [pages/player/game-checkout.md](pages/player/game-checkout.md) |
| F19 | My Games | `/my-games` | [pages/player/my-games.md](pages/player/my-games.md) |
| F25 | Inbox | `/inbox` | [pages/player/inbox.md](pages/player/inbox.md) |
| F12 | Profile and settings | `/profile`, `/profile/edit`; `/settings` redirects here | [pages/player/profile.md](pages/player/profile.md) |
| F13 | Payment Methods | `/profile/payment-methods`, `/settings/payment-methods` | [pages/player/payment-methods.md](pages/player/payment-methods.md) |

## Hosting

Hosting uses signed-in player routes; there is no separate organizer area.

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F14 | Create Game | `/create-game` | [pages/hosting/create-game.md](pages/hosting/create-game.md) |
| F18 | Edit Game | `/games/:gameId/edit` | [pages/hosting/edit-game.md](pages/hosting/edit-game.md) |
| F21 | Create Sub Post | `/need-a-sub` (create panel) | [pages/hosting/create-sub-post.md](pages/hosting/create-sub-post.md) |
| F24 | Edit Sub Post | `/need-a-sub/posts/:postId/edit` | [pages/hosting/edit-sub-post.md](pages/hosting/edit-sub-post.md) |
| F23 | Sub Post Published | `/need-a-sub/posts/:postId/published` | [pages/hosting/sub-post-published.md](pages/hosting/sub-post-published.md) |

## Admin Workspace

These routes require admin access; the sign-in page is listed under
Authentication.

| Feature pass | Page experience | Existing route(s) | Specification |
|---|---|---|---|
| F37 | Review Cases | `/admin/review-cases` | [pages/admin/review-cases.md](pages/admin/review-cases.md) |
| F38 | Review Case Detail | `/admin/review-cases/:reviewCaseId` | [pages/admin/review-case-detail.md](pages/admin/review-case-detail.md) |
| F39 | User Directory | `/admin/users` | [pages/admin/user-directory.md](pages/admin/user-directory.md) |
| F40 | User Detail | `/admin/users/:userId` | [pages/admin/user-detail.md](pages/admin/user-detail.md) |
| F41 | User Game Activity | `/admin/users/:userId/game-activity` | [pages/admin/user-game-activity.md](pages/admin/user-game-activity.md) |
| F42 | User Need a Sub Activity | `/admin/users/:userId/need-a-sub-activity` | [pages/admin/user-need-a-sub-activity.md](pages/admin/user-need-a-sub-activity.md) |
| F32 | Community Games | `/admin/community-games` | [pages/admin/community-games.md](pages/admin/community-games.md) |
| F33 | Community Game Detail | `/admin/community-games/:gameId` | [pages/admin/community-game-detail.md](pages/admin/community-game-detail.md) |
| F34 | Need a Sub (Admin) | `/admin/need-a-sub` | [pages/admin/need-a-sub-posts.md](pages/admin/need-a-sub-posts.md) |
| F35 | Need a Sub Post (Admin) | `/admin/need-a-sub/:postId` | [pages/admin/need-a-sub-post-detail.md](pages/admin/need-a-sub-post-detail.md) |
| F36 | Need a Sub Request (Admin) | `/admin/need-a-sub/requests/:requestId` | [pages/admin/need-a-sub-request-detail.md](pages/admin/need-a-sub-request-detail.md) |
| F28 | Official Games | `/admin/official-games` | [pages/admin/official-games.md](pages/admin/official-games.md) |
| F29 | Create Official Game | `/admin/official-games/new` | [pages/admin/create-official-game.md](pages/admin/create-official-game.md) |
| F30 | Official Game Manage | `/admin/official-games/:gameId` | [pages/admin/official-game-manage.md](pages/admin/official-game-manage.md) |
| F31 | Edit Official Game | `/admin/official-games/:gameId/edit` | [pages/admin/edit-official-game.md](pages/admin/edit-official-game.md) |
| F50 | Money Issues | `/admin/money/issues` | [pages/admin/money-issues.md](pages/admin/money-issues.md) |
| F51 | Money Issue Detail | `/admin/money/issues/:moneyIssueId` | [pages/admin/money-issue-detail.md](pages/admin/money-issue-detail.md) |
| F43 | User Money | `/admin/money/users`, `/admin/money/users/:userId` | [pages/admin/user-money.md](pages/admin/user-money.md) |
| F44 | Payments | `/admin/money/payments` | [pages/admin/payments.md](pages/admin/payments.md) |
| F45 | Payment Detail | `/admin/money/payments/:paymentId` | [pages/admin/payment-detail.md](pages/admin/payment-detail.md) |
| F46 | Refunds | `/admin/money/refunds` | [pages/admin/refunds.md](pages/admin/refunds.md) |
| F47 | Refund Detail | `/admin/money/refunds/:refundId` | [pages/admin/refund-detail.md](pages/admin/refund-detail.md) |
| F48 | Credits | `/admin/money/credits` | [pages/admin/credits.md](pages/admin/credits.md) |
| F49 | Credit Detail | `/admin/money/credits/:creditId` | [pages/admin/credit-detail.md](pages/admin/credit-detail.md) |
| F52 | Financial Outcome Detail | `/admin/money/financial-outcomes/:financialOutcomeId` | [pages/admin/financial-outcome-detail.md](pages/admin/financial-outcome-detail.md) |
| F53 | Notification Lookup | `/admin/notifications`, `/admin/notifications/:notificationId` | [pages/admin/notification-lookup.md](pages/admin/notification-lookup.md) |
| F27 | Admin Action Log | `/admin/audit` | [pages/admin/admin-action-log.md](pages/admin/admin-action-log.md) |
| F54 | Platform Notices | `/admin/platform-notices`, `/admin/platform-notices/new`, `/admin/platform-notices/:noticeId` | [pages/admin/platform-notices.md](pages/admin/platform-notices.md) |

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
