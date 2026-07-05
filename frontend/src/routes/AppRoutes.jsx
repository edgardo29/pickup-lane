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
  AdminNotificationsPage,
  AdminPlatformNoticesPage,
  AdminOfficialGamePage,
  AdminEditOfficialGamePage,
  AdminOfficialGamesPage,
  AdminSignInPage,
  AdminStaffPage,
  AdminUserPage,
  AdminUsersPage,
} from '../pages/admin/index.js'
import AdminWorkspaceShell from '../pages/admin/shared/AdminWorkspaceShell.jsx'
import AdminAccessProvider from '../pages/admin/shared/AdminAccessProvider.jsx'
import {
  ADMIN_PERMISSIONS,
  getDefaultAdminPath,
} from '../pages/admin/shared/adminWorkspaceData.js'
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
            <RequireAdmin permissions={Object.values(ADMIN_PERMISSIONS)}>
              <AdminWorkspaceShell />
            </RequireAdmin>
          </AdminAccessProvider>
        }
      >
        <Route index element={<AdminIndexRedirect />} />
        <Route
          path="action-center"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.ACTION_CENTER_VIEW}>
              <AdminActionCenterPage />
            </RequireAdmin>
          }
        />
        <Route
          path="audit"
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
          path="users"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.USERS_READ}>
              <AdminUsersPage />
            </RequireAdmin>
          }
        />
        <Route
          path="users/staff"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.STAFF_MANAGE}>
              <AdminStaffPage />
            </RequireAdmin>
          }
        />
        <Route
          path="users/:userId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.USERS_READ}>
              <AdminUserPage />
            </RequireAdmin>
          }
        />
        <Route
          path="community-games"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.COMMUNITY_GAMES_READ}>
              <AdminCommunityGamesPage />
            </RequireAdmin>
          }
        />
        <Route
          path="community-games/:gameId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.COMMUNITY_GAMES_READ}>
              <AdminCommunityGamePage />
            </RequireAdmin>
          }
        />
        <Route
          path="need-a-sub"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.NEED_A_SUB_MODERATE}>
              <AdminNeedASubPage />
            </RequireAdmin>
          }
        />
        <Route
          path="need-a-sub/:postId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.NEED_A_SUB_MODERATE}>
              <AdminNeedASubPostPage />
            </RequireAdmin>
          }
        />
        <Route
          path="notifications"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.NOTIFICATIONS_READ}>
              <AdminNotificationsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="platform-notices"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.NOTIFICATIONS_MANAGE}>
              <AdminPlatformNoticesPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/payments"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyPaymentsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/users"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyUserPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/users/:userId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyUserPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/payment-methods"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyPaymentMethodsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/credits"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyCreditsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/credits/:creditId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyCreditPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/support-flags"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneySupportFlagsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/support-flags/:supportFlagId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneySupportFlagPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/payments/:paymentId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyPaymentPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/refunds"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyRefundsPage />
            </RequireAdmin>
          }
        />
        <Route
          path="money/refunds/:refundId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.MONEY_READ}>
              <AdminMoneyRefundPage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.OFFICIAL_GAMES_READ}>
              <AdminOfficialGamesPage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games/new"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.OFFICIAL_GAMES_WRITE}>
              <AdminCreateOfficialGamePage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games/:gameId/edit"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.OFFICIAL_GAMES_WRITE}>
              <AdminEditOfficialGamePage />
            </RequireAdmin>
          }
        />
        <Route
          path="official-games/:gameId"
          element={
            <RequireAdmin permission={ADMIN_PERMISSIONS.OFFICIAL_GAMES_READ}>
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
