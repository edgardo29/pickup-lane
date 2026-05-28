import { Navigate, Route, Routes } from 'react-router-dom'
import {
  CheckEmailPage,
  CreateAccountPage,
  FinishProfilePage,
  ForgotPasswordPage,
  ResetPasswordPage,
  SignInPage,
} from '../pages/auth/index.js'
import {
  AdminCreateOfficialGamePage,
  AdminOfficialGamePage,
  AdminOfficialGamesPage,
  AdminSignInPage,
} from '../pages/admin/index.js'
import {
  BrowseGamesPage,
  GameCheckoutPage,
  GameDetailsPage,
} from '../pages/browse-games/index.js'
import { CreateGamePage } from '../pages/create-game/index.js'
import { InboxPage } from '../pages/inbox/index.js'
import LandingPage from '../pages/LandingPage.jsx'
import { CancellationRefundPolicyPage, PrivacyPage, TermsPage } from '../pages/LegalPages.jsx'
import { MyGamesPage } from '../pages/my-games/index.js'
import {
  NeedASubDetailPage,
  NeedASubManagePage,
  NeedASubPage,
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
            <Navigate to="/admin/official-games" replace />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/official-games"
        element={
          <RequireAdmin>
            <AdminOfficialGamesPage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/official-games/new"
        element={
          <RequireAdmin>
            <AdminCreateOfficialGamePage />
          </RequireAdmin>
        }
      />
      <Route
        path="/admin/official-games/:gameId"
        element={
          <RequireAdmin>
            <AdminOfficialGamePage />
          </RequireAdmin>
        }
      />
      <Route path="/need-a-sub" element={<NeedASubPage />} />
      <Route path="/need-a-sub/posts/:postId" element={<NeedASubDetailPage />} />
      <Route
        path="/need-a-sub/posts/:postId/manage"
        element={
          <RequireAppUser>
            <NeedASubManagePage />
          </RequireAppUser>
        }
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
