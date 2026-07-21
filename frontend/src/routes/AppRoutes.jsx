import { Navigate, Route, Routes, useParams } from 'react-router-dom'
import {
  CheckEmailPage,
  CreateAccountPage,
  FinishProfilePage,
  ForgotPasswordPage,
  ResetPasswordPage,
  SignInPage,
} from '../pages/auth/index.js'
import {
  AdminActionCenterPage,
  AdminAuditLogPage,
  AdminCommunityGamePage,
  AdminCommunityGamesPage,
  AdminCreateOfficialGamePage,
  AdminMoneyCreditPage,
  AdminMoneyCreditsPage,
  AdminMoneyFinancialOutcomePage,
  AdminMoneyPaymentPage,
  AdminMoneyPaymentMethodsPage,
  AdminMoneyPaymentsPage,
  AdminMoneyRefundPage,
  AdminMoneyRefundsPage,
  AdminMoneySupportFlagPage,
  AdminMoneySupportFlagsPage,
  AdminMoneyUserPage,
  AdminNeedASubPage,
  AdminNeedASubPostPage,
  AdminNeedASubRequestPage,
  AdminNotificationsPage,
  AdminPlatformNoticesPage,
  AdminOfficialGamePage,
  AdminEditOfficialGamePage,
  AdminOfficialGamesPage,
  AdminReviewCasePage,
  AdminReviewCasesPage,
  AdminSignInPage,
  AdminUserGameActivityPage,
  AdminUserNeedASubActivityPage,
  AdminUserPage,
  AdminUsersPage,
} from '../pages/admin/index.js'
import AdminWorkspaceShell from '../pages/admin/shared/AdminWorkspaceShell.jsx'
import AdminAccessProvider from '../pages/admin/shared/AdminAccessProvider.jsx'
import { getDefaultAdminPath } from '../pages/admin/shared/adminWorkspaceData.js'
import { useAdminAccess } from '../pages/admin/shared/useAdminAccess.js'
import {
  BrowseGamesPage,
  GameCheckoutPage,
  GameDetailsPage,
} from '../pages/browse-games/index.js'
import { CreateGamePage } from '../pages/create-game/index.js'
import { InboxPage } from '../pages/inbox/index.js'
import { LandingPage } from '../pages/landing/index.js'
import { CancellationRefundPolicyPage, PrivacyPage, TermsPage } from '../pages/LegalPages.jsx'
import { MyGamesPage } from '../pages/my-games/index.js'
import {
  NeedASubDetailPage,
  NeedASubEditPage,
  NeedASubPage,
  NeedASubPublishSuccessPage,
} from '../pages/need-a-sub/index.js'
import {
  EditProfilePage,
  PaymentMethodsPage,
  ProfilePage,
  SettingsPage,
} from '../pages/profile/index.js'
import { RedirectSignedIn, RequireAdmin, RequireAppUser } from './RouteGuards.jsx'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route
        path="/sign-in"
        element={
          <RedirectSignedIn>
            <SignInPage />
          </RedirectSignedIn>
        }
      />
      <Route
        path="/create-account"
        element={
          <RedirectSignedIn>
            <CreateAccountPage />
          </RedirectSignedIn>
        }
      />
      <Route path="/finish-profile" element={<FinishProfilePage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/check-email" element={<CheckEmailPage />} />
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/policies/cancellation-refunds" element={<CancellationRefundPolicyPage />} />
      <Route path="/games" element={<BrowseGamesPage />} />
      <Route path="/games/:gameId" element={<GameDetailsPage />} />
      <Route
        path="/games/:gameId/checkout"
        element={
          <RequireAppUser>
            <GameCheckoutPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/games/:gameId/edit"
        element={
          <RequireAppUser>
            <CreateGamePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/my-games"
        element={
          <RequireAppUser>
            <MyGamesPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/inbox"
        element={
          <RequireAppUser>
            <InboxPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/admin/sign-in"
        element={<AdminSignInPage />}
      />
      <Route
        path="/admin"
        element={
          <AdminAccessProvider>
            <RequireAdmin>
              <AdminWorkspaceShell />
            </RequireAdmin>
          </AdminAccessProvider>
        }
      >
        <Route index element={<AdminIndexRedirect />} />
        <Route
          path="action-center"
          element={
            <RequireAdmin>
              <AdminActionCenterPage />
            </RequireAdmin>
          }
        />
        <Route
          path="audit"
          element={
            <RequireAdmin>
              <AdminAuditLogPage />
            </RequireAdmin>
          }
        />
        <Route
          path="review-cases"
          element={
            <RequireAdmin>
              <AdminReviewCasesPage />
            </RequireAdmin>
          }
        />
        <Route
          path="review-cases/:reviewCaseId"
          element={
            <RequireAdmin>
              <AdminReviewCasePage />
            </RequireAdmin>
          }
        />
        <Route
          path="users"
          element={
            <RequireAdmin>
              <AdminUsersPage />
            </RequireAdmin>
          }
        />
        <Route
          path="staff"
          element={<Navigate replace to="/admin/users?role=admin" />}
        />
        <Route
          path="users/:userId"
          element={
            <RequireAdmin>
              <AdminUserPage />
            </RequireAdmin>
          }
        />
        <Route
          path="users/:userId/game-activity"
          element={
            <RequireAdmin>
              <AdminUserGameActivityPage />
            </RequireAdmin>
          }
        />
        <Route
          path="users/:userId/need-a-sub-activity"
          element={
            <RequireAdmin>
              <AdminUserNeedASubActivityPage />
            </RequireAdmin>
          }
        />
        <Route
          path="community-games"
          element={
            <RequireAdmin>
              <AdminCommunityGamesPage />
            </RequireAdmin>
          }
        />
        <Route
          path="community-games/:gameId"
          element={
            <RequireAdmin>
              <AdminCommunityGamePage />
            </RequireAdmin>
          }
        />
        <Route
          path="need-a-sub"
          element={
            <RequireAdmin>
              <AdminNeedASubPage />
            </RequireAdmin>
          }
        />
        <Route
          path="need-a-sub/requests/:requestId"
          element={
            <RequireAdmin>
              <AdminNeedASubRequestPage />
            </RequireAdmin>
          }
        />
        <Route
          path="need-a-sub/:postId"
          element={
            <RequireAdmin>
              <AdminNeedASubPostPage />
            </RequireAdmin>
          }
        />
        <Route
          path="notifications"
          element={
            <RequireAdmin>
              <AdminNotificationsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="platform-notices"
          element={
            <RequireAdmin>
              <AdminPlatformNoticesPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/payments"
          element={
            <RequireAdmin>
              <AdminMoneyPaymentsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/users"
          element={
            <RequireAdmin>
              <AdminMoneyUserPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/users/:userId"
          element={
            <RequireAdmin>
              <AdminMoneyUserPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/payment-methods"
          element={
            <RequireAdmin>
              <AdminMoneyPaymentMethodsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/credits"
          element={
            <RequireAdmin>
              <AdminMoneyCreditsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/credits/:creditId"
          element={
            <RequireAdmin>
              <AdminMoneyCreditPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/support-flags"
          element={
            <RequireAdmin>
              <AdminMoneySupportFlagsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/support-flags/:supportFlagId"
          element={
            <RequireAdmin>
              <AdminMoneySupportFlagPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/payments/:paymentId"
          element={
            <RequireAdmin>
              <AdminMoneyPaymentPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/financial-outcomes/:financialOutcomeId"
          element={
            <RequireAdmin>
              <AdminMoneyFinancialOutcomePage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/refunds"
          element={
            <RequireAdmin>
              <AdminMoneyRefundsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/refunds/:refundId"
          element={
            <RequireAdmin>
              <AdminMoneyRefundPage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games"
          element={
            <RequireAdmin>
              <AdminOfficialGamesPage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games/new"
          element={
            <RequireAdmin>
              <AdminCreateOfficialGamePage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games/:gameId/edit"
          element={
            <RequireAdmin>
              <AdminEditOfficialGamePage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games/:gameId"
          element={
            <RequireAdmin>
              <AdminOfficialGamePage />
            </RequireAdmin>
          }
        />
      </Route>
      <Route path="/need-a-sub" element={<NeedASubPage />} />
      <Route path="/need-a-sub/posts/:postId" element={<NeedASubDetailPage />} />
      <Route
        path="/need-a-sub/posts/:postId/edit"
        element={
          <RequireAppUser>
            <NeedASubEditPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/need-a-sub/posts/:postId/published"
        element={
          <RequireAppUser>
            <NeedASubPublishSuccessPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/need-a-sub/posts/:postId/manage"
        element={<NeedASubManageRedirect />}
      />
      <Route path="/player-hub" element={<Navigate to="/need-a-sub" replace />} />
      <Route
        path="/create-game"
        element={
          <RequireAppUser>
            <CreateGamePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/profile"
        element={
          <RequireAppUser>
            <ProfilePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/profile/edit"
        element={
          <RequireAppUser>
            <EditProfilePage />
          </RequireAppUser>
        }
      />
      <Route
        path="/profile/payment-methods"
        element={
          <RequireAppUser>
            <PaymentMethodsPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/settings"
        element={
          <RequireAppUser>
            <SettingsPage />
          </RequireAppUser>
        }
      />
      <Route
        path="/settings/payment-methods"
        element={
          <RequireAppUser>
            <PaymentMethodsPage />
          </RequireAppUser>
        }
      />
    </Routes>
  )
}

function NeedASubManageRedirect() {
  const { postId } = useParams()

  return <Navigate to={`/need-a-sub/posts/${postId}`} replace />
}

function AdminIndexRedirect() {
  const { adminAccess } = useAdminAccess()

  return <Navigate to={getDefaultAdminPath(adminAccess)} replace />
}
