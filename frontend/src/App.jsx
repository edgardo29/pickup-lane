import { useEffect, useLayoutEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import {
  CheckEmailPage,
  CreateAccountPage,
  FinishProfilePage,
  ForgotPasswordPage,
  ResetPasswordPage,
  SignInPage,
} from './pages/auth/index.js'
import {
  BrowseGamesPage,
  GameCheckoutPage,
  GameDetailsPage,
} from './pages/browse-games/index.js'
import { CreateGamePage } from './pages/create-game/index.js'
import InboxPage from './pages/InboxPage.jsx'
import LandingPage from './pages/LandingPage.jsx'
import { PrivacyPage, TermsPage } from './pages/LegalPages.jsx'
import MyGamesPage from './pages/MyGamesPage.jsx'
import NeedASubManagePage from './pages/NeedASubManagePage.jsx'
import NeedASubDetailPage from './pages/NeedASubDetailPage.jsx'
import NeedASubPage from './pages/NeedASubPage.jsx'
import { EditProfilePage, ProfilePage, SettingsPage } from './pages/ProfilePages.jsx'
import { useAuth } from './hooks/useAuth.js'

function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/sign-in" element={<SignInPage />} />
        <Route path="/create-account" element={<CreateAccountPage />} />
        <Route path="/finish-profile" element={<FinishProfilePage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/check-email" element={<CheckEmailPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
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
          path="/need-a-sub"
          element={
            <RequireAppUser>
              <NeedASubPage />
            </RequireAppUser>
          }
        />
        <Route
          path="/need-a-sub/posts/:postId"
          element={
            <RequireAppUser>
              <NeedASubDetailPage />
            </RequireAppUser>
          }
        />
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
          path="/settings"
          element={
            <RequireAppUser>
              <SettingsPage />
            </RequireAppUser>
          }
        />
      </Routes>
    </>
  )
}

function ScrollToTop() {
  const location = useLocation()

  useEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual'
    }
  }, [])

  useLayoutEffect(() => {
    resetPageScroll()

    const firstFrame = window.requestAnimationFrame(() => {
      resetPageScroll()

      window.requestAnimationFrame(resetPageScroll)
    })

    return () => window.cancelAnimationFrame(firstFrame)
  }, [location.key, location.pathname, location.search])

  return null
}

function resetPageScroll() {
  window.scrollTo(0, 0)

  if (document.scrollingElement) {
    document.scrollingElement.scrollTop = 0
  }

  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
}

function RequireAppUser({ children }) {
  const { appUser, isLoading } = useAuth()

  if (isLoading) {
    return null
  }

  if (!appUser) {
    return <Navigate to="/" replace />
  }

  return children
}

export default App
