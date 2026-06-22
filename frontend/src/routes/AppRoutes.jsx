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
  AdminCreateOfficialGamePage,
  AdminMoneyCreditPage,
  AdminMoneyCreditsPage,
  AdminMoneyPaymentPage,
  AdminMoneyPaymentMethodsPage,
  AdminMoneyPaymentsPage,
  AdminMoneyRefundPage,
  AdminMoneyRefundsPage,
  AdminMoneySupportFlagPage,
  AdminMoneySupportFlagsPage,
  AdminMoneyUserPage,
  AdminOfficialGamePage,
  AdminOfficialGamesPage,
  AdminSignInPage,
  AdminStaffPage,
  AdminUserPage,
  AdminUsersPage,
} from '../pages/admin/index.js'
import { ADMIN_PERMISSIONS } from '../pages/admin/shared/adminWorkspaceData.js'
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
          <RequireAdmin>
            <Navigate to="/admin/action-center" replace />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/action-center"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.ACTION_CENTER_VIEW}>
            <AdminActionCenterPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/audit"
        element={
          <RequireAdmin
            permissions={[
              ADMIN_PERMISSIONS.AUDIT_READ,
              ADMIN_PERMISSIONS.AUDIT_SUPPORT_READ,
            ]}
          >
            <AdminAuditLogPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/users"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.USERS_READ}>
            <AdminUsersPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/users/staff"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.STAFF_MANAGE}>
            <AdminStaffPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/users/:userId"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.USERS_READ}>
            <AdminUserPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/payments"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyPaymentsPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/users"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyUserPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/users/:userId"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyUserPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/payment-methods"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyPaymentMethodsPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/credits"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyCreditsPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/credits/:creditId"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyCreditPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/support-flags"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneySupportFlagsPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/support-flags/:supportFlagId"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneySupportFlagPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/payments/:paymentId"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyPaymentPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/refunds"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyRefundsPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/money/refunds/:refundId"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
            <AdminMoneyRefundPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/official-games"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.OFFICIAL_GAMES_READ}>
            <AdminOfficialGamesPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/official-games/new"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.OFFICIAL_GAMES_WRITE}>
            <AdminCreateOfficialGamePage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/official-games/:gameId"
        element={
          <RequireAdmin permission={ADMIN_PERMISSIONS.OFFICIAL_GAMES_READ}>
            <AdminOfficialGamePage />
          </RequireAdmin>
        }
      />
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
